/**
 * Deck Builder — single JS file, no external dependencies.
 * The page emits only a tiny inline init script that sets window._cdbInit
 * and calls window._dbSetup().
 */
(function () {
  'use strict';

  var CIRC = 2 * Math.PI * 36; // SVG ring circumference (r=36)
  var _counterFilter = null;   // null | 0 | 1000 | 2000
  var _costFilter    = null;   // null | 0..10
  var _triggerFilter = false;  // show only trigger cards

  /* ── Hidden-input helpers ────────────────────────────────────────────── */

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
    if (inp && typeof htmx !== 'undefined') htmx.trigger(inp, 'db-search');
  }

  /* ── Color chip sync ─────────────────────────────────────────────────── */

  function syncColorChips(colors) {
    document.querySelectorAll('.db-chip-color').forEach(function (btn) {
      btn.classList.toggle('active', (colors || []).indexOf(btn.dataset.color) !== -1);
    });
    _updateColorFilters();
  }

  /* ── Deck panel renderer (grouped by type, grid) ─────────────────────── */

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

      // Build filtered grid first to skip empty sections
      var grid = document.createElement('div');
      grid.className = 'db-deck-grid';
      var rendered = 0;

      group.forEach(function (e) {
        var id = e[0]; var d = e[1];
        if (_counterFilter !== null && (d.counter || 0) !== _counterFilter) return;
        if (_costFilter !== null && Math.min(d.cost || 0, 10) !== _costFilter) return;
        if (_triggerFilter && !d.has_trigger) return;
        var card = document.createElement('div');
        card.className = 'db-deck-card';
        card.dataset.cardId = id;
        card.title = (d.name || id) + ' — click to remove · ⌘/Ctrl+click to add';
        card.innerHTML =
          '<img src="' + (d.img || '') + '" style="width:100%;height:auto;display:block;" alt="">' +
          '<span class="db-deck-card-count">' + d.count + '</span>' +
          '<div class="db-deck-card-strip">' +
            '<span style="font-family:Barlow,sans-serif;font-size:.55rem;font-weight:600;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;">' +
              (d.name || id) +
            '</span>' +
          '</div>';
        card.addEventListener('click', function (e) {
          var cid = this.dataset.cardId;
          if (e.metaKey || e.ctrlKey) {
            var d = window._cdb.cards[cid];
            if (d) window._cdb.addCard(cid, d.name, d.img, d.cost, d.type, d.counter, d.has_trigger);
          } else {
            window._cdb.removeCard(cid);
          }
        });
        grid.appendChild(card);
        rendered++;
      });

      if (!rendered) return; // skip section when filter hides all its cards

      var cnt = group.reduce(function (s, e) { return s + e[1].count; }, 0);
      var sec = document.createElement('div');
      sec.style.marginBottom = '12px';
      var hdr = document.createElement('div');
      hdr.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;';
      hdr.innerHTML =
        '<span style="font-family:\'Bebas Neue\',sans-serif;letter-spacing:.1em;font-size:.6rem;color:#475569;">' + type.toUpperCase() + 'S</span>' +
        '<span style="font-family:\'Share Tech Mono\',monospace;font-size:.65rem;color:#475569;">' + cnt + '</span>';
      sec.appendChild(hdr);
      sec.appendChild(grid);
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

    var ring = document.getElementById('db-ring');
    var ringNum = document.getElementById('db-ring-num');
    if (ring) {
      var offset = CIRC - Math.min(total / 50, 1) * CIRC;
      ring.style.strokeDashoffset = offset;
      var col = total === 50 ? '#10b981' : total > 50 ? '#ef4444' : '#f59e0b';
      ring.style.stroke = col;
      if (ringNum) { ringNum.textContent = total; ringNum.style.color = col; }
    }

    ['Character', 'Event', 'Stage'].forEach(function (t) {
      var el = document.getElementById('db-tc-' + t.toLowerCase());
      if (el) el.textContent = typeCounts[t] || 0;
    });

    var maxBar = Math.max.apply(null, Object.values(costMap).concat([1]));
    for (var i = 0; i <= 10; i++) {
      var bar = document.getElementById('db-bar-' + i);
      if (!bar) continue;
      var cnt = costMap[i] || 0;
      var h = cnt > 0 ? Math.max(3, Math.round((cnt / maxBar) * 34)) : 2;
      bar.style.height = h + 'px';
      var col = document.getElementById('db-cost-col-' + i);
      if (col) col.title = 'Cost ' + (i === 10 ? '10+' : i) + ': ' + cnt + ' — click to filter';
    }
  }

  /* ── Counter analytics ───────────────────────────────────────────────── */

  function updateCounterStats(cdb) {
    var counts = { 0: 0, 1000: 0, 2000: 0 };
    var triggerCount = 0;
    Object.values(cdb.cards).forEach(function (c) {
      if (c.is_leader) return;
      var cv = c.counter || 0;
      if (cv === 1000) counts[1000] += c.count;
      else if (cv === 2000) counts[2000] += c.count;
      else counts[0] += c.count;
      if (c.has_trigger) triggerCount += c.count;
    });
    var map = { 'none': 0, '1k': 1000, '2k': 2000 };
    Object.keys(map).forEach(function (key) {
      var el = document.getElementById('db-cn-' + key);
      if (el) el.textContent = counts[map[key]];
    });
    var trigEl = document.getElementById('db-cn-trigger');
    if (trigEl) trigEl.textContent = triggerCount;
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
      var maxCount = el.dataset.isLeader === '1' ? 1 : 4;
      badge.textContent = count > 0 ? count : '';
      badge.classList.toggle('visible', count > 0);
      el.classList.toggle('is-maxed', count >= maxCount);
    });
  }

  /* ── Clipboard import ────────────────────────────────────────────────── */

  function _importCards(text) {
    if (!window._cdb) return;
    fetch('/api/decklist-builder/import-text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text })
    }).then(function (r) { return r.json(); })
    .then(function (cards) {
      if (!Array.isArray(cards) || cards.length === 0) {
        alert('No matching cards found. Check the format: 4xOP01-001');
        return;
      }
      var cdb = window._cdb;
      Object.keys(cdb.cards).forEach(function (k) {
        if (!cdb.cards[k].is_leader) delete cdb.cards[k];
      });
      cards.forEach(function (c) {
        if (c.is_leader) {
          cdb.setLeader(c.id, c.name || c.id, c.img || '', c.colors || []);
        } else {
          cdb.cards[c.id] = { count: c.count, name: c.name || c.id, img: c.img || '', is_leader: false, cost: c.cost || 0, type: c.type || '', counter: c.counter || 0, has_trigger: !!c.has_trigger };
        }
      });
      cdb.render();
    }).catch(function () {
      alert('Failed to import decklist. Please check the format and try again.');
    });
  }

  /* ── Public handlers ─────────────────────────────────────────────────── */

  window._cdbLeaderChange = function (sel) {
    var opt = sel.options[sel.selectedIndex];
    if (!opt || !opt.value) return;
    var colors = [];
    try { colors = JSON.parse(opt.dataset.leaderColors || '[]'); } catch (e) {}
    if (window._cdb) {
      window._cdb.setLeader(opt.value, opt.dataset.leaderName || opt.value, opt.dataset.leaderImg || '', colors);
    }
    _triggerSearch();
  };

  window._cdbImportChange = function (sel) {
    var opt = sel.options[sel.selectedIndex];
    var url = opt ? opt.dataset.importUrl : null;
    if (!url) return;
    // Preserve current mobile tab across the page reload triggered by import
    var deckPanel = document.getElementById('db-deck-panel');
    if (deckPanel && deckPanel.style.display !== 'none') {
      sessionStorage.setItem('db-tab', 'deck');
    }
    window.location.href = url;
  };

  window._cdbPasteImport = function () {
    if (!window._cdb) return;
    navigator.clipboard.readText().then(function (text) {
      text = text.trim();
      if (!text) { alert('Clipboard is empty.'); return; }
      _importCards(text);
    }).catch(function () {
      alert('Could not read clipboard. Please allow clipboard access and try again.');
    });
  };

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

  window._dbCardFlash = function (el) {
    var cls = el.dataset.isLeader === '1' ? 'db-card-flash-gold' : 'db-card-flash-blue';
    el.classList.remove('db-card-flash-blue', 'db-card-flash-gold');
    void el.offsetWidth;
    el.classList.add(cls);
    setTimeout(function () { el.classList.remove(cls); }, 420);
  };

  window._dbToggleCounterFilter = function (val) {
    var parsed = (val === null || val === undefined) ? 0 : parseInt(val, 10);
    _counterFilter = (_counterFilter === parsed) ? null : parsed;
    var map = { 'none': 0, '1k': 1000, '2k': 2000 };
    Object.keys(map).forEach(function (key) {
      var el = document.getElementById('db-counter-' + key);
      if (el) el.classList.toggle('active', _counterFilter === map[key]);
      var fsEl = document.getElementById('db-fs-counter-' + key);
      if (fsEl) fsEl.classList.toggle('active', _counterFilter === map[key]);
    });
    if (window._cdb) window._cdb.render();
  };

  window._dbToggleTriggerFilter = function () {
    _triggerFilter = !_triggerFilter;
    var chip = document.getElementById('db-counter-trigger');
    if (chip) chip.classList.toggle('active', _triggerFilter);
    var fsChip = document.getElementById('db-fs-counter-trigger');
    if (fsChip) fsChip.classList.toggle('active', _triggerFilter);
    if (window._cdb) window._cdb.render();
  };

  window._dbToggleCostFilter = function (cost) {
    var parsed = parseInt(cost, 10);
    _costFilter = (_costFilter === parsed) ? null : parsed;
    for (var i = 0; i <= 10; i++) {
      var col = document.getElementById('db-cost-col-' + i);
      if (col) col.classList.toggle('active', _costFilter === i);
      var fsCol = document.getElementById('db-fs-cost-col-' + i);
      if (fsCol) fsCol.classList.toggle('active', _costFilter === i);
    }
    if (window._cdb) window._cdb.render();
  };

  /* ── Fullscreen deck view ────────────────────────────────────────────── */

  function renderFsGrid(cdb) {
    var body = document.getElementById('db-fs-body');
    if (!body) return;
    var cards = cdb.cards;
    var groups = { Character: [], Event: [], Stage: [] };
    Object.entries(cards).forEach(function (e) {
      var id = e[0]; var d = e[1];
      if (d.is_leader) return;
      var t = d.type || 'Character';
      if (groups[t]) groups[t].push([id, d]); else groups['Character'].push([id, d]);
    });
    body.innerHTML = '';
    var anyRendered = false;
    ['Character', 'Event', 'Stage'].forEach(function (type) {
      var group = groups[type] || [];
      if (!group.length) return;
      group.sort(function (a, b) { return (a[1].cost || 0) - (b[1].cost || 0); });
      var grid = document.createElement('div');
      grid.className = 'db-fs-grid';
      var rendered = 0;
      group.forEach(function (e) {
        var id = e[0]; var d = e[1];
        if (_counterFilter !== null && (d.counter || 0) !== _counterFilter) return;
        if (_costFilter !== null && Math.min(d.cost || 0, 10) !== _costFilter) return;
        if (_triggerFilter && !d.has_trigger) return;
        var card = document.createElement('div');
        card.className = 'db-fs-card';
        card.dataset.cardId = id;
        card.title = (d.name || id) + ' — click to view card details';
        card.innerHTML =
          '<img src="' + (d.img || '') + '" alt="">' +
          '<span class="db-fs-card-cnt">' + d.count + '</span>' +
          '<div class="db-fs-card-strip"><span>' + (d.name || id) + '</span></div>';
        card.addEventListener('click', function () {
          var cid = this.dataset.cardId;
          var urlParams = new URLSearchParams(window.location.search);
          var metaFormat = urlParams.get('meta_format') || 'latest';
          var currency = urlParams.get('currency') || 'eur';
          var url = '/api/card-modal?card_id=' + encodeURIComponent(cid) +
                    '&meta_format=' + encodeURIComponent(metaFormat) +
                    '&currency=' + encodeURIComponent(currency);
          if (window.htmx) {
            htmx.ajax('GET', url, { target: 'body', swap: 'beforeend' });
          } else {
            fetch(url).then(function (r) { return r.text(); }).then(function (html) {
              var div = document.createElement('div');
              div.innerHTML = html;
              if (div.firstElementChild) document.body.appendChild(div.firstElementChild);
            });
          }
        });
        grid.appendChild(card);
        rendered++;
        anyRendered = true;
      });
      if (!rendered) return;
      var cnt = group.reduce(function (s, e) { return s + e[1].count; }, 0);
      var sec = document.createElement('div');
      sec.className = 'db-fs-section';
      var hdr = document.createElement('div');
      hdr.className = 'db-fs-section-hdr';
      hdr.innerHTML = type.toUpperCase() + 'S <span style="font-family:\'Share Tech Mono\',monospace;font-size:.55rem;color:#475569;">' + cnt + '</span>';
      sec.appendChild(hdr);
      sec.appendChild(grid);
      body.appendChild(sec);
    });
    if (!anyRendered) {
      body.innerHTML = '<p style="color:#1e2d45;font-family:Barlow,sans-serif;font-size:.8rem;text-align:center;padding:60px 0;">No cards match the current filter.</p>';
    }
  }

  function updateFsStats(cdb) {
    var bg = document.getElementById('db-fs-bg');
    var nameEl = document.getElementById('db-fs-leader-name');
    if (bg) bg.style.backgroundImage = cdb.leaderImg ? 'url(' + cdb.leaderImg + ')' : '';
    if (nameEl) nameEl.textContent = cdb.leaderName || cdb.leaderId || 'SELECT A LEADER';

    var total = 0;
    var typeCounts = { Character: 0, Event: 0, Stage: 0 };
    var costMap = {};
    var counterCounts = { 0: 0, 1000: 0, 2000: 0 };
    var fsTriggerCount = 0;
    Object.values(cdb.cards).forEach(function (c) {
      if (c.is_leader) return;
      total += c.count;
      costMap[Math.min(c.cost || 0, 10)] = (costMap[Math.min(c.cost || 0, 10)] || 0) + c.count;
      if (typeCounts[c.type] !== undefined) typeCounts[c.type] += c.count;
      var cv = c.counter || 0;
      if (cv === 1000) counterCounts[1000] += c.count;
      else if (cv === 2000) counterCounts[2000] += c.count;
      else counterCounts[0] += c.count;
      if (c.has_trigger) fsTriggerCount += c.count;
    });

    var totalEl = document.getElementById('db-fs-total');
    if (totalEl) {
      var col = total === 50 ? '#10b981' : total > 50 ? '#ef4444' : '#f59e0b';
      totalEl.innerHTML = '<span style="color:' + col + '">' + total + '</span><span style="color:#1e2d45;font-size:.65rem;">/50</span>';
    }

    ['Character', 'Event', 'Stage'].forEach(function (t) {
      var el = document.getElementById('db-fs-tc-' + t.toLowerCase());
      if (el) el.textContent = typeCounts[t] || 0;
    });

    var maxBar = Math.max.apply(null, Object.values(costMap).concat([1]));
    for (var i = 0; i <= 10; i++) {
      var bar = document.getElementById('db-fs-bar-' + i);
      if (bar) bar.style.height = (costMap[i] ? Math.max(2, Math.round((costMap[i] / maxBar) * 20)) : 2) + 'px';
      var fsCol = document.getElementById('db-fs-cost-col-' + i);
      if (fsCol) fsCol.classList.toggle('active', _costFilter === i);
    }

    var cmap = { 'none': 0, '1k': 1000, '2k': 2000 };
    Object.keys(cmap).forEach(function (key) {
      var valEl = document.getElementById('db-fs-cn-' + key);
      if (valEl) valEl.textContent = counterCounts[cmap[key]];
      var chip = document.getElementById('db-fs-counter-' + key);
      if (chip) chip.classList.toggle('active', _counterFilter === cmap[key]);
    });
    var fsTrigEl = document.getElementById('db-fs-cn-trigger');
    if (fsTrigEl) fsTrigEl.textContent = fsTriggerCount;
    var fsTrigChip = document.getElementById('db-fs-counter-trigger');
    if (fsTrigChip) fsTrigChip.classList.toggle('active', _triggerFilter);
  }

  window._dbOpenFullscreen = function () {
    var overlay = document.getElementById('db-fs-overlay');
    if (!overlay) return;
    if (window._cdb) { updateFsStats(window._cdb); renderFsGrid(window._cdb); }
    overlay.classList.add('open');
    var sweep = document.createElement('div');
    sweep.className = 'db-fs-sweep';
    overlay.appendChild(sweep);
    setTimeout(function () { if (sweep.parentNode) sweep.parentNode.removeChild(sweep); }, 800);
    document.body.style.overflow = 'hidden';
  };

  window._dbCloseFullscreen = function () {
    var overlay = document.getElementById('db-fs-overlay');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
  };

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      window._dbCloseHand();
      window._dbCloseFullscreen();
    }
  });

  /* ── Starting Hand ───────────────────────────────────────────────── */

  window._dbDrawHand = function () {
    var cdb = window._cdb;
    if (!cdb) return;

    // Build weighted pool (one entry per copy of each card)
    var pool = [];
    Object.entries(cdb.cards).forEach(function (e) {
      var id = e[0]; var d = e[1];
      if (d.is_leader) return;
      for (var i = 0; i < d.count; i++) {
        pool.push({ id: id, img: d.img || '', name: d.name || id });
      }
    });

    if (pool.length < 5) {
      alert('Need at least 5 cards in the deck to draw a starting hand.');
      return;
    }

    // Fisher-Yates shuffle
    for (var i = pool.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = pool[i]; pool[i] = pool[j]; pool[j] = tmp;
    }
    var hand = pool.slice(0, 5);

    // Fan arc: rotations and vertical offsets for each of the 5 cards
    var rots = [-16, -8, 0, 8, 16];
    var tys  = [18,   7,  0, 7, 18];

    var container = document.getElementById('db-hand-cards');
    if (!container) return;
    container.innerHTML = '';

    hand.forEach(function (card, i) {
      var outer = document.createElement('div');
      outer.className = 'db-hand-card-outer';
      outer.style.transform = 'rotate(' + rots[i] + 'deg) translateY(' + tys[i] + 'px)';

      var inner = document.createElement('div');
      inner.className = 'db-hand-card-inner';
      inner.style.animationDelay = (i * 0.07) + 's';
      inner.innerHTML = '<img src="' + card.img + '" alt="' + card.name + '" style="width:100%;display:block;">';

      outer.appendChild(inner);
      container.appendChild(outer);
    });

    var overlay = document.getElementById('db-hand-overlay');
    if (overlay) overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  };

  window._dbCloseHand = function () {
    var overlay = document.getElementById('db-hand-overlay');
    if (overlay) overlay.classList.remove('open');
    // Only restore scroll if fullscreen is also closed
    var fs = document.getElementById('db-fs-overlay');
    if (!fs || !fs.classList.contains('open')) {
      document.body.style.overflow = '';
    }
  };

  /* ── Main entry point — called by the inline init script ─────────────── */

  window._dbSetup = function () {
    var init = window._cdbInit || {
      cards: {}, leaderId: '', leaderName: '', leaderImg: '', leaderColors: [], customId: null
    };
    window._cdbInit = null;

    window._cdb = {
      cards:        JSON.parse(JSON.stringify(init.cards)),
      leaderId:     init.leaderId,
      leaderName:   init.leaderName,
      leaderImg:    init.leaderImg,
      leaderColors: init.leaderColors || [],
      customId:     init.customId,

      addFromBtn: function (btn) {
        var id      = btn.dataset.cardId;
        var name    = btn.dataset.cardName;
        var img     = btn.dataset.cardImg;
        var isLeader = btn.dataset.isLeader === '1';
        var cost    = parseInt(btn.dataset.cardCost    || '0', 10);
        var type    = btn.dataset.cardType  || '';
        var counter = parseInt(btn.dataset.cardCounter || '0', 10);
        var has_trigger = btn.dataset.cardTrigger === '1';
        if (isLeader) { this.setLeader(id, name, img, []); }
        else          { this.addCard(id, name, img, cost, type, counter, has_trigger); }
      },

      addCard: function (id, name, img, cost, type, counter, has_trigger) {
        if (!(id in this.cards)) {
          this.cards[id] = { count: 0, name: name, img: img, is_leader: false, cost: cost || 0, type: type || '', counter: counter || 0, has_trigger: !!has_trigger };
        }
        if (this.cards[id].count < 4) this.cards[id].count++;
        this.render();
      },

      removeCard: function (id) {
        if (!(id in this.cards)) return;
        this.cards[id].count--;
        if (this.cards[id].count <= 0) delete this.cards[id];
        this.render();
      },

      setLeader: function (id, name, img, colors) {
        var cdb = this;
        Object.keys(this.cards).forEach(function (k) {
          if (cdb.cards[k].is_leader) delete cdb.cards[k];
        });
        this.leaderId     = id;
        this.leaderName   = name;
        this.leaderImg    = img;
        this.leaderColors = colors || [];
        this.cards[id]    = { count: 1, name: name, img: img, is_leader: true };
        syncColorChips(this.leaderColors);
        this.renderLeader();
        this.render();
      },

      renderLeader: function () {
        var heroBg   = document.getElementById('cdb-leader-hero-bg');
        var heroName = document.getElementById('cdb-leader-hero-name');
        var heroEl   = document.getElementById('cdb-leader-hero');
        var sel      = document.getElementById('cdb-leader-select');
        if (heroBg)   heroBg.style.backgroundImage = this.leaderImg ? 'url(' + this.leaderImg + ')' : '';
        if (heroName) heroName.textContent = this.leaderId ? (this.leaderName || this.leaderId) : 'SELECT A LEADER';
        if (heroEl)   heroEl.classList.toggle('has-leader', !!this.leaderId);
        if (sel && this.leaderId) sel.value = this.leaderId;
      },

      render: function () {
        var out = {};
        Object.entries(this.cards).forEach(function (e) { out[e[0]] = e[1].count; });
        var hidden = document.getElementById('cdb-decklist-json');
        if (hidden) hidden.value = JSON.stringify(out);
        renderDeckPanel(this);
        updateStats(this);
        updateCounterStats(this);
        updateCardBadges(this);
        var fsOverlay = document.getElementById('db-fs-overlay');
        if (fsOverlay && fsOverlay.classList.contains('open')) {
          renderFsGrid(this);
          updateFsStats(this);
        }
      },

      save: function () {
        var btn = document.getElementById('cdb-save-btn');
        if (btn && btn.dataset.loggedIn !== 'true') {
          window.location.href = '/login?next=/deckbuilder';
          return;
        }
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
        if (btn) { btn.disabled = true; btn.textContent = 'Saving\u2026'; }
        fetch('/api/watchlist/custom-decklist/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name, leader_id: self.leaderId, decklist: deck, custom_id: self.customId || null })
        }).then(function (r) {
          if (r.ok) {
            window.location.href = '/watchlist?section=decklists';
          } else if (r.status === 401) {
            window.location.href = '/login?next=/deckbuilder';
          } else {
            alert('Failed to save. Please try again.');
            if (btn) { btn.disabled = false; btn.textContent = 'SAVE DECK'; }
          }
        }).catch(function () {
          alert('Error saving.');
          if (btn) { btn.disabled = false; btn.textContent = 'SAVE DECK'; }
        });
      }
    };

    syncColorChips(window._cdb.leaderColors);
    window._cdb.renderLeader();
    window._cdb.render();
    updateCardBadges(window._cdb);

    // Restore mobile tab after import-triggered page reload
    var savedTab = sessionStorage.getItem('db-tab');
    if (savedTab) {
      sessionStorage.removeItem('db-tab');
      window._switchBuilderTab(savedTab);
    }
  };

})();
