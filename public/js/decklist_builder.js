/**
 * Decklist Builder — static JS loaded once at page startup.
 * All _cdb logic lives here so HTMX never needs to re-execute it
 * inside swapped content (avoids normalizeScriptTags SyntaxErrors).
 *
 * The HTMX-swapped builder fragment only contains a tiny inline script:
 *   window._cdbInit = {...data...};
 *   if (typeof window._cdbSetup === 'function') window._cdbSetup();
 */
(function () {
  'use strict';

  /* ── Color-filter helper ────────────────────────────────────────────── */

  function setColorFilters(colors) {
    var el = document.getElementById('cdb-color-filters');
    if (!el) return;
    el.innerHTML = '';
    (colors || []).forEach(function (color) {
      var inp = document.createElement('input');
      inp.type = 'hidden';
      inp.name = 'card_colors';
      inp.value = color;
      el.appendChild(inp);
    });
  }

  /* ── Leader-select handler ──────────────────────────────────────────── */

  window._cdbLeaderChange = function (sel) {
    var opt = sel.options[sel.selectedIndex];
    if (!opt || !opt.value) return;
    var colors = [];
    try { colors = JSON.parse(opt.dataset.leaderColors || '[]'); } catch (e) {}
    if (window._cdb) {
      window._cdb.setLeader(opt.value, opt.dataset.leaderName || opt.value, opt.dataset.leaderImg || '', colors);
    }
  };

  /* ── Import-select handler ─────────────────────────────────────────── */

  window._cdbImportChange = function (sel) {
    var opt = sel.options[sel.selectedIndex];
    var url = opt ? opt.dataset.importUrl : null;
    if (!url) return;
    htmx.ajax('GET', url, { target: '#decklist-builder-wrapper', swap: 'innerHTML' });
  };

  /* ── Clipboard import handler ──────────────────────────────────────── */

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
          cdb.cards[c.id] = { count: c.count, name: c.name || c.id, img: c.img || '', is_leader: false };
        }
      });
      cdb.render();
    }).catch(function () {
      alert('Failed to import decklist. Please check the format and try again.');
    });
  }

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

  /* ── Builder setup — called by the inline prefill script ───────────── */

  window._cdbSetup = function () {
    var init = window._cdbInit || {
      cards: {}, leaderId: '', leaderName: '', leaderImg: '', leaderColors: [], customId: null
    };
    window._cdbInit = null;

    window._cdb = {
      cards: JSON.parse(JSON.stringify(init.cards)),
      leaderId: init.leaderId,
      leaderName: init.leaderName,
      leaderImg: init.leaderImg,
      leaderColors: init.leaderColors || [],
      customId: init.customId,

      addFromBtn: function (btn) {
        var id = btn.dataset.cardId;
        var name = btn.dataset.cardName;
        var img = btn.dataset.cardImg;
        var isLeader = btn.dataset.isLeader === '1';
        if (isLeader) { this.setLeader(id, name, img, []); }
        else { this.addCard(id, name, img); }
      },

      addCard: function (id, name, img) {
        if (!(id in this.cards)) {
          this.cards[id] = { count: 0, name: name, img: img, is_leader: false };
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
        this.leaderId = id;
        this.leaderName = name;
        this.leaderImg = img;
        this.leaderColors = colors || [];
        this.cards[id] = { count: 1, name: name, img: img, is_leader: true };
        setColorFilters(this.leaderColors);
        this.renderLeader();
        this.render();
      },

      renderLeader: function () {
        var el = document.getElementById('cdb-leader-display');
        if (!el) return;
        if (this.leaderId) {
          el.innerHTML =
            '<img src="' + this.leaderImg + '" class="w-10 h-auto rounded" alt="">' +
            '<span class="text-white text-sm font-medium">' + this.leaderName + '</span>' +
            '<span class="text-xs text-gray-400 ml-1">(' + this.leaderId + ')</span>';
        } else {
          el.innerHTML =
            '<span class="text-gray-400 text-sm">No leader selected — use the dropdown above</span>';
        }
      },

      render: function () {
        var panel = document.getElementById('cdb-decklist-panel');
        var countEl = document.getElementById('cdb-deck-count');
        var hidden = document.getElementById('cdb-decklist-json');
        var cards = this.cards;
        var totalCards = Object.values(cards).reduce(function (s, c) { return s + c.count; }, 0);
        if (countEl) countEl.textContent = totalCards + ' cards';

        var decklistOut = {};
        Object.entries(cards).forEach(function (e) { decklistOut[e[0]] = e[1].count; });
        if (hidden) hidden.value = JSON.stringify(decklistOut);
        if (!panel) return;

        if (Object.keys(cards).length === 0) {
          panel.innerHTML = '<p class="text-gray-500 text-sm text-center py-2">No cards yet.</p>';
          return;
        }

        panel.innerHTML = '';
        Object.entries(cards).forEach(function (entry) {
          var id = entry[0];
          var data = entry[1];
          var row = document.createElement('div');
          row.className = 'flex items-center justify-between py-1 border-b border-gray-700/30 last:border-0';

          /* Escape single quotes so onclick strings stay valid */
          var safeId   = id.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
          var safeName = (data.name || id).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
          var safeImg  = (data.img || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");

          row.innerHTML =
            '<div class="flex items-center flex-1 min-w-0 mr-2">' +
              '<img src="' + (data.img || '') + '" class="w-7 h-auto rounded mr-2 flex-shrink-0" alt="">' +
              '<span class="text-white text-xs truncate">' + (data.name || id) + '</span>' +
              (data.is_leader ? '<span class="ml-1 text-xs text-yellow-400">(Leader)</span>' : '') +
            '</div>' +
            '<div class="flex items-center flex-shrink-0">' +
              '<button onclick="window._cdb.removeCard(\'' + safeId + '\')" ' +
                'class="w-6 h-6 bg-gray-600 hover:bg-gray-500 text-white rounded-l text-sm leading-none flex items-center justify-center">' +
                '\u2212</button>' +
              '<span class="w-7 text-center text-white text-xs bg-gray-700 h-6 flex items-center justify-center">' +
                data.count + '</span>' +
              '<button onclick="window._cdb.addCard(\'' + safeId + '\',\'' + safeName + '\',\'' + safeImg + '\')" ' +
                'class="w-6 h-6 bg-gray-600 hover:bg-gray-500 text-white rounded-r text-sm leading-none flex items-center justify-center">' +
                '+</button>' +
            '</div>';
          panel.appendChild(row);
        });
      },

      save: function () {
        var cdb = this;
        var nameEl = document.getElementById('cdb-name');
        var name = nameEl ? nameEl.value.trim() : '';
        if (!name) { alert('Please enter a decklist name.'); return; }
        if (!cdb.leaderId) { alert('Please select a leader card.'); return; }
        var jsonEl = document.getElementById('cdb-decklist-json');
        var decklistJson = jsonEl ? jsonEl.value : '{}';
        var btn = document.getElementById('cdb-save-btn');
        if (btn) {
          btn.disabled = true;
          btn.querySelector('i').className = 'fas fa-spinner fa-spin mr-2';
        }
        fetch('/api/watchlist/custom-decklist/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: name,
            leader_id: cdb.leaderId,
            decklist: JSON.parse(decklistJson),
            custom_id: cdb.customId || null
          })
        }).then(function (r) {
          if (r.ok) {
            window.location.href = '?section=decklists';
          } else {
            alert('Failed to save. Please try again.');
            if (btn) {
              btn.disabled = false;
              btn.querySelector('i').className = 'fas fa-save mr-2';
            }
          }
        }).catch(function () {
          alert('Error saving decklist.');
          if (btn) {
            btn.disabled = false;
            btn.querySelector('i').className = 'fas fa-save mr-2';
          }
        });
      }
    };

    /* Apply prefill color filters and render */
    setColorFilters(window._cdb.leaderColors);
    window._cdb.renderLeader();
    window._cdb.render();
  };
})();
