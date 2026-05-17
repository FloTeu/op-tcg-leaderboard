/**
 * Deck Builder page — static JS loaded once at startup.
 * The page only emits a tiny inline init script; all logic lives here.
 *
 * Depends on: decklist_builder.js (must load first, defines _cdbSetup)
 */
(function () {
  'use strict';

  var CIRC = 2 * Math.PI * 36; // SVG progress ring circumference (r=36)

  /* ── Deck panel renderer (grouped by type) ───────────────────────────── */
  function renderDeckPanel(cdb) {
    var panel = document.getElementById('cdb-decklist-panel');
    if (!panel) return;

    var cards = cdb.cards;
    var nonLeader = Object.values(cards).filter(function (c) { return !c.is_leader; });
    if (!nonLeader.length) {
      panel.innerHTML = '<p style="color:#1e2d45;font-family:Barlow,sans-serif;font-size:.8rem;text-align:center;padding:24px 0;">Add cards from the browser</p>';
      return;
    }

    var groups = { Character: [], Event: [], Stage: [] };
    Object.entries(cards).forEach(function (e) {
      var id = e[0]; var d = e[1];
      if (d.is_leader) return;
      var t = d.type || 'Character';
      if (groups[t]) groups[t].push([id, d]);
      else groups['Character'].push([id, d]);
    });

    panel.innerHTML = '';
    ['Character', 'Event', 'Stage'].forEach(function (type) {
      var group = groups[type];
      if (!group.length) return;
      group.sort(function (a, b) { return (a[1].cost || 0) - (b[1].cost || 0); });

      var sec = document.createElement('div');
      sec.style.marginBottom = '10px';

      var cnt = group.reduce(function (s, e) { return s + e[1].count; }, 0);
      var hdr = document.createElement('div');
      hdr.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;';
      hdr.innerHTML =
        '<span style="font-family:\'Bebas Neue\',sans-serif;letter-spacing:.1em;font-size:.6rem;color:#334155;">' + type.toUpperCase() + 'S</span>' +
        '<span style="font-family:\'Share Tech Mono\',monospace;font-size:.65rem;color:#334155;">' + cnt + '</span>';
      sec.appendChild(hdr);

      group.forEach(function (e) {
        var id = e[0]; var d = e[1];
        // Safe versions for inline onclick strings
        var safeId   = id.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        var safeName = (d.name || id).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        var safeImg  = (d.img || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        var safeCost = d.cost || 0;
        var safeType = (d.type || '').replace(/'/g, "\\'");

        var row = document.createElement('div');
        row.className = 'db-deck-row';
        row.innerHTML =
          '<img src="' + (d.img || '') + '" style="width:28px;height:auto;border-radius:3px;flex-shrink:0;" alt="">' +
          '<div style="flex:1;min-width:0;">' +
            '<div style="font-family:Barlow,sans-serif;font-size:.72rem;color:#cbd5e1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + (d.name || id) + '</div>' +
            (d.cost ? '<div style="font-family:\'Share Tech Mono\',monospace;font-size:.6rem;color:#334155;">cost ' + d.cost + '</div>' : '') +
          '</div>' +
          '<div style="display:flex;align-items:center;gap:4px;flex-shrink:0;">' +
            '<button onclick="window._cdb.removeCard(\'' + safeId + '\')" class="db-qty-btn">\u2212</button>' +
            '<span style="font-family:\'Share Tech Mono\',monospace;font-size:.7rem;color:#f1f5f9;width:14px;text-align:center;">' + d.count + '</span>' +
            '<button onclick="window._cdb.addCard(\'' + safeId + '\',\'' + safeName + '\',\'' + safeImg + '\',' + safeCost + ',\'' + safeType + '\')" class="db-qty-btn">+</button>' +
          '</div>';
        sec.appendChild(row);
      });

      panel.appendChild(sec);
    });
  }

  /* ── Stats: ring + type counts + cost curve ──────────────────────────── */
  function updateStats(cdb) {
    var cards = cdb.cards;
    var total = 0;
    var costMap = {};
    var typeCounts = { Character: 0, Event: 0, Stage: 0 };

    Object.values(cards).forEach(function (c) {
      if (c.is_leader) return;
      total += c.count;
      var cost = Math.min(c.cost || 0, 10);
      costMap[cost] = (costMap[cost] || 0) + c.count;
      if (typeCounts[c.type] !== undefined) typeCounts[c.type] += c.count;
    });

    // Progress ring
    var ring = document.getElementById('db-ring');
    var ringNum = document.getElementById('db-ring-num');
    if (ring) {
      var offset = CIRC - Math.min(total / 50, 1) * CIRC;
      ring.style.strokeDashoffset = offset;
      var col = total === 50 ? '#10b981' : total > 50 ? '#ef4444' : '#f59e0b';
      ring.style.stroke = col;
      if (ringNum) { ringNum.textContent = total; ringNum.style.color = col; }
    }

    // Type badges
    ['Character', 'Event', 'Stage'].forEach(function (t) {
      var el = document.getElementById('db-tc-' + t.toLowerCase());
      if (el) el.textContent = typeCounts[t] || 0;
    });

    // Cost curve bars
    var maxBar = Math.max.apply(null, Object.values(costMap).concat([1]));
    for (var i = 0; i <= 10; i++) {
      var bar = document.getElementById('db-bar-' + i);
      if (!bar) continue;
      var cnt = costMap[i] || 0;
      var h = cnt > 0 ? Math.max(3, Math.round((cnt / maxBar) * 34)) : 2;
      bar.style.height = h + 'px';
      bar.title = 'Cost ' + (i === 10 ? '10+' : i) + ': ' + cnt;
    }

    // Leader frame glow
    var frame = document.getElementById('cdb-leader-display');
    if (frame) {
      if (cdb.leaderId) frame.classList.add('has-leader');
      else frame.classList.remove('has-leader');
    }
  }

  /* ── Card browser badge sync ─────────────────────────────────────────── */
  function updateCardBadges(cdb) {
    var results = document.getElementById('cdb-search-results');
    if (!results) return;
    results.querySelectorAll('.db-card-item').forEach(function (el) {
      var id = el.dataset.cardId;
      var badge = el.querySelector('.db-card-count');
      if (!badge) return;
      var card = cdb.cards[id];
      var count = card ? card.count : 0;
      var isLeader = el.dataset.isLeader === '1';
      var maxCount = isLeader ? 1 : 4;
      if (count > 0) {
        badge.textContent = count;
        badge.classList.add('visible');
      } else {
        badge.textContent = '';
        badge.classList.remove('visible');
      }
      if (count >= maxCount) {
        el.classList.add('is-maxed');
      } else {
        el.classList.remove('is-maxed');
      }
    });
  }

  /* ── Card flash on add ───────────────────────────────────────────────── */
  window._dbCardFlash = function (el) {
    var cls = el.dataset.isLeader === '1' ? 'db-card-flash-gold' : 'db-card-flash-blue';
    el.classList.remove('db-card-flash-blue', 'db-card-flash-gold');
    void el.offsetWidth; // force reflow
    el.classList.add(cls);
    setTimeout(function () { el.classList.remove(cls); }, 420);
  };

  /* ── Color chip sync ─────────────────────────────────────────────────── */
  function syncColorChips(colors) {
    document.querySelectorAll('.db-chip-color').forEach(function (btn) {
      btn.classList.toggle('active', (colors || []).indexOf(btn.dataset.color) !== -1);
    });
    _updateColorFilters();
  }

  function _updateColorFilters() {
    var container = document.getElementById('cdb-color-filters');
    if (!container) return;
    container.innerHTML = '';
    document.querySelectorAll('.db-chip-color.active').forEach(function (btn) {
      var inp = document.createElement('input');
      inp.type = 'hidden'; inp.name = 'card_colors'; inp.value = btn.dataset.color;
      container.appendChild(inp);
    });
  }

  function _updateCatFilters() {
    var container = document.getElementById('cdb-category-filters');
    if (!container) return;
    container.innerHTML = '';
    document.querySelectorAll('.db-chip-cat.active').forEach(function (btn) {
      var inp = document.createElement('input');
      inp.type = 'hidden'; inp.name = 'card_category'; inp.value = btn.dataset.cat;
      container.appendChild(inp);
    });
  }

  function _triggerSearch() {
    var inp = document.getElementById('cdb-search');
    if (inp && typeof htmx !== 'undefined') htmx.trigger(inp, 'keyup');
  }

  /* ── Public handlers ─────────────────────────────────────────────────── */
  window._dbToggleColor = function (btn) {
    btn.classList.toggle('active');
    _updateColorFilters();
    _triggerSearch();
  };

  window._dbToggleCat = function (btn) {
    btn.classList.toggle('active');
    _updateCatFilters();
    _triggerSearch();
  };

  window._dbExport = function () {
    if (!window._cdb) return;
    var lines = [];
    Object.entries(window._cdb.cards).forEach(function (e) {
      lines.push(e[1].count + 'x' + e[0]);
    });
    navigator.clipboard.writeText(lines.join('\n')).then(function () {
      var btn = document.getElementById('db-export-btn');
      if (btn) { btn.textContent = 'Copied!'; setTimeout(function () { btn.textContent = 'Export'; }, 2000); }
    });
  };

  window._switchBuilderTab = function (tab) {
    if (window.innerWidth >= 1280) return;
    var browse = document.getElementById('db-browse-panel');
    var deck   = document.getElementById('db-deck-panel');
    var tBrowse = document.getElementById('db-tab-browse');
    var tDeck   = document.getElementById('db-tab-deck');
    if (!browse || !deck) return;
    if (tab === 'browse') {
      browse.style.display = ''; deck.style.display = 'none';
      if (tBrowse) tBrowse.classList.add('active-tab');
      if (tDeck)   tDeck.classList.remove('active-tab');
    } else {
      browse.style.display = 'none'; deck.style.display = 'block';
      if (tBrowse) tBrowse.classList.remove('active-tab');
      if (tDeck)   tDeck.classList.add('active-tab');
    }
  };

  /* ── Page setup — called by the inline init script ───────────────────── */
  window._dbSetup = function () {
    if (typeof window._cdbSetup !== 'function') return;

    // Run the base builder setup (creates window._cdb)
    window._cdbSetup();

    var cdb = window._cdb;
    if (!cdb) return;

    // Replace render with grouped version
    cdb.render = function () {
      var cards = this.cards;
      var out = {};
      Object.entries(cards).forEach(function (e) { out[e[0]] = e[1].count; });
      var hidden = document.getElementById('cdb-decklist-json');
      if (hidden) hidden.value = JSON.stringify(out);
      renderDeckPanel(this);
      updateStats(this);
      updateCardBadges(this);
    };

    // Replace save to redirect to /watchlist
    cdb.save = function () {
      var nameEl = document.getElementById('cdb-name');
      var name = nameEl ? nameEl.value.trim() : '';
      if (!name) { alert('Please name your deck.'); if (nameEl) nameEl.focus(); return; }
      if (!this.leaderId) { alert('Please select a leader.'); return; }
      var hidden = document.getElementById('cdb-decklist-json');
      var deck = JSON.parse(hidden ? hidden.value : '{}');
      var nonLeader = 0;
      var self = this;
      Object.entries(deck).forEach(function (e) {
        if (!(self.cards[e[0]] && self.cards[e[0]].is_leader)) nonLeader += e[1];
      });
      if (nonLeader < 50 && !confirm('Deck has ' + nonLeader + '/50 cards. Save anyway?')) return;
      var btn = document.getElementById('cdb-save-btn');
      if (btn) { btn.disabled = true; btn.textContent = 'Saving\u2026'; }
      var self = this;
      fetch('/api/watchlist/custom-decklist/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, leader_id: self.leaderId, decklist: deck, custom_id: self.customId || null })
      }).then(function (r) {
        if (r.ok) {
          window.location.href = '/watchlist?section=decklists';
        } else {
          alert('Failed to save. Please try again.');
          if (btn) { btn.disabled = false; btn.textContent = 'SAVE DECK'; }
        }
      }).catch(function () {
        alert('Error saving.');
        if (btn) { btn.disabled = false; btn.textContent = 'SAVE DECK'; }
      });
    };

    // Wrap leader change to also sync color chips
    var origLeaderChange = window._cdbLeaderChange;
    window._cdbLeaderChange = function (sel) {
      origLeaderChange(sel);
      if (window._cdb) syncColorChips(window._cdb.leaderColors || []);
      _triggerSearch();
    };

    // Initial state
    cdb.render();
    syncColorChips(cdb.leaderColors || []);
    updateCardBadges(cdb);
  };

})();
