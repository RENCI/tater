/**
 * Span annotation support for Tater.
 *
 * Provides:
 *  - window.dash_clientside.tater.captureSelection  (clientside callback)
 *    Called when an entity-type button is clicked; captures the current text
 *    selection and returns {text, start, end, tag, ts} to the selection store.
 *
 *  - window.dash_clientside.tater.captureDelete  (clientside callback)
 *    Fired by the hidden proxy button; returns window._taterDeletePending
 *    to the delete store so the server callback can remove the span.
 *
 *  - Floating tooltip: a single <div id="tater-span-tooltip"> appended to
 *    <body> (outside document-content) that shows the entity label and a
 *    × delete button when the mouse enters a <mark data-start> element.
 *
 *  - Active-entity highlighting: the most recently clicked entity type button
 *    (per widget) has its spans shown filled; other entity types' spans in the
 *    same widget are shown outlined.  Other widgets are unaffected.
 */


// ---------- inject CSS for outlined (inactive) spans ----------
// Using a CSS class with !important ensures the outline state survives React
// reconciliation, which sets inline background-color on <mark> elements.

(function () {
    var s = document.createElement('style');
    s.textContent =
        'mark[data-start].tater-span-outlined {' +
        '  background-color: transparent !important;' +
        '  outline: 2px solid var(--tater-mark-color, #888);' +
        '  outline-offset: -1px;' +
        '  border-radius: 2px;' +
        '}' +
        '[data-tater-field].tater-widget-outlined button {' +
        '  background-color: transparent !important;' +
        '}';
    document.head.appendChild(s);
})();


// ---------- active-entity tracking + span styling ----------
// component_id of the most recently clicked SpanAnnotationWidget, or null.

window._taterActiveWidget = window._taterActiveWidget || null;

/**
 * Apply filled or outlined styling to every <mark data-start> in the document.
 *
 * For each mark:
 *   - If no active entity is recorded for its widget, OR its tag matches the
 *     active entity → filled (remove class).
 *   - Otherwise → outlined (add class + set --tater-mark-color).
 *
 * Widgets without a recorded active entity are unaffected (all filled).
 */
function applySpanStyles() {
    var active = window._taterActiveWidget;

    // Collect all button containers and build their keys.
    var containers = document.querySelectorAll('[data-tater-field]');
    var containerKeys = [];
    for (var j = 0; j < containers.length; j++) {
        var c  = containers[j];
        var cf = c.getAttribute('data-tater-field');
        var ci = c.getAttribute('data-tater-index');
        containerKeys.push(ci !== null ? cf + '|' + ci : cf);
    }

    // If the active key no longer exists (e.g. after navigating to a document
    // with fewer list items), reset to the first available container.
    if (active && containerKeys.length > 0 && containerKeys.indexOf(active) === -1) {
        active = containerKeys[0];
        window._taterActiveWidget = active;
    }

    var marks = document.querySelectorAll('mark[data-start]');
    for (var i = 0; i < marks.length; i++) {
        var mark      = marks[i];
        var field     = mark.getAttribute('data-field');
        var indexAttr = mark.getAttribute('data-index');
        var color     = mark.getAttribute('data-color') || '#ffe066';
        var key = indexAttr !== null ? field + '|' + indexAttr : field;

        if (!active || key === active) {
            mark.classList.remove('tater-span-outlined');
        } else {
            mark.style.setProperty('--tater-mark-color', color);
            mark.classList.add('tater-span-outlined');
        }
    }

    for (var k = 0; k < containers.length; k++) {
        if (!active || containerKeys[k] === active) {
            containers[k].classList.remove('tater-widget-outlined');
        } else {
            containers[k].classList.add('tater-widget-outlined');
        }
    }
}


// ---------- initialise active widget on page load + watch for new ones ----------
// On page load: poll until the first [data-tater-field] button container is in
// the DOM, then activate it.
// After that: a body-level MutationObserver fires applySpanStyles() whenever a
// new [data-tater-field] element is added (e.g. a new list item), so newly
// rendered button groups get the correct outlined/filled state immediately.

(function () {
    var debounceTimer = null;

    function activate() {
        if (!window._taterActiveWidget) {
            var first = document.querySelector('[data-tater-field]');
            if (first) {
                var f = first.getAttribute('data-tater-field');
                var i = first.getAttribute('data-tater-index');
                window._taterActiveWidget = i !== null ? f + '|' + i : f;
            }
        }
        applySpanStyles();
    }

    function tryInit() {
        if (document.querySelector('[data-tater-field]')) {
            activate();
            // Watch for future additions (new list items, etc.)
            new MutationObserver(function (mutations) {
                for (var m = 0; m < mutations.length; m++) {
                    var added = mutations[m].addedNodes;
                    for (var n = 0; n < added.length; n++) {
                        var node = added[n];
                        if (node.nodeType === 1 && node.querySelector &&
                                node.querySelector('[data-tater-field]')) {
                            clearTimeout(debounceTimer);
                            debounceTimer = setTimeout(applySpanStyles, 50);
                            return;
                        }
                    }
                }
            }).observe(document.body, { childList: true, subtree: true });
        } else {
            setTimeout(tryInit, 200);
        }
    }
    tryInit();
})();


// ---------- click listener for entity buttons ----------
// Each button group is wrapped in an html.Div with data-tater-field (and
// data-tater-index for list items).  We detect clicks via these attributes,
// independent of the Dash callback chain, so the active widget is updated
// even when no text is selected.

document.addEventListener('click', function (e) {
    var container = e.target.closest('[data-tater-field]');
    if (!container) { return; }
    var field     = container.getAttribute('data-tater-field');
    var indexAttr = container.getAttribute('data-tater-index');
    // List button groups carry data-tater-index; non-list groups do not.
    var activeKey = indexAttr !== null ? field + '|' + indexAttr : field;
    if (activeKey) {
        window._taterActiveWidget = activeKey;
        applySpanStyles();
    }
}, true);


// ---------- scroll preservation ----------
// Saves document-content scrollTop before a server round-trip and restores it
// after Dash replaces the element's children.  Also re-applies span styles.

var _savedDocScroll = null;

(function () {
    function restoreScroll() {
        if (_savedDocScroll === null) { return; }
        var el = document.getElementById('document-content');
        if (el) { el.scrollTop = _savedDocScroll; }
        _savedDocScroll = null;
    }

    function afterDocUpdate() {
        restoreScroll();
        applySpanStyles();
    }

    function setupObserver() {
        var el = document.getElementById('document-content');
        if (!el) { setTimeout(setupObserver, 200); return; }
        new MutationObserver(function () {
            requestAnimationFrame(afterDocUpdate);
        }).observe(el, { childList: true, subtree: false });
    }
    setupObserver();
})();


// ---------- clientside callbacks ----------

window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.tater = Object.assign({}, window.dash_clientside.tater || {}, {

    captureSelection: function (n_clicks_list) {
        var ctx = window.dash_clientside.callback_context;
        if (!ctx || !ctx.triggered || !ctx.triggered.length) {
            return window.dash_clientside.no_update;
        }

        // prop_id format: '{"field":"...","tag":"...","type":"..."}.n_clicks'
        //             or: '{"type":"...","ld":"...","cid":"...","tag":"...","index":N}.n_clicks'
        var propId = ctx.triggered[0].prop_id;
        var btnId;
        try {
            btnId = JSON.parse(propId.split('.n_clicks')[0]);
        } catch (e) {
            return window.dash_clientside.no_update;
        }
        var tag = btnId.tag;
        if (!tag) {
            return window.dash_clientside.no_update;
        }

        var selection = window.getSelection();
        if (!selection || selection.rangeCount === 0 || selection.toString().trim() === '') {
            return window.dash_clientside.no_update;
        }

        var selectedText = selection.toString();
        var range = selection.getRangeAt(0);
        var docEl = document.getElementById('document-content');
        if (!docEl || !docEl.contains(range.commonAncestorContainer)) {
            return window.dash_clientside.no_update;
        }

        var preRange = range.cloneRange();
        preRange.selectNodeContents(docEl);
        preRange.setEnd(range.startContainer, range.startOffset);
        var start = preRange.toString().length;
        var end = start + selectedText.length;

        _savedDocScroll = docEl.scrollTop;
        selection.removeAllRanges();
        return { text: selectedText, start: start, end: end, tag: tag, ts: Date.now() };
    },

    captureDelete: function (n_clicks) {
        var d = window._taterDeletePending;
        if (!d) { return window.dash_clientside.no_update; }
        window._taterDeletePending = null;
        return d;
    }

});


// ---------- floating tooltip ----------

(function () {
    var tooltip = null;
    var hideTimer = null;

    function ensureTooltip() {
        if (tooltip) { return tooltip; }
        tooltip = document.createElement('div');
        tooltip.id = 'tater-span-tooltip';
        document.body.appendChild(tooltip);

        tooltip.addEventListener('mouseenter', function () {
            clearTimeout(hideTimer);
        });
        tooltip.addEventListener('mouseleave', function () {
            scheduleHide();
        });
        return tooltip;
    }

    function scheduleHide() {
        clearTimeout(hideTimer);
        hideTimer = setTimeout(function () {
            if (tooltip) { tooltip.style.display = 'none'; }
        }, 150);
    }

    function showTooltip(mark) {
        clearTimeout(hideTimer);
        var t = ensureTooltip();

        var tag   = mark.getAttribute('data-tag')   || '';
        var field = mark.getAttribute('data-field') || '';
        var start = mark.getAttribute('data-start') || '';
        var end   = mark.getAttribute('data-end')   || '';
        var color = mark.getAttribute('data-color') || '#ffe066';

        // Rebuild tooltip contents — the entire popup IS the colored label
        t.innerHTML = '';
        t.style.backgroundColor = color;
        t.appendChild(document.createTextNode(tag));

        var btn = document.createElement('button');
        btn.className = 'tater-tooltip-delete';
        btn.textContent = 'x';
        btn.addEventListener('click', function () {
            var indexAttr = mark.getAttribute('data-index');
            window._taterDeletePending = {
                field: field,
                index: indexAttr !== null ? parseInt(indexAttr, 10) : -1,
                start: parseInt(start, 10),
                end:   parseInt(end,   10),
                ts:    Date.now()
            };
            var docEl = document.getElementById('document-content');
            if (docEl) { _savedDocScroll = docEl.scrollTop; }
            var proxy = document.getElementById('span-delete-proxy-' + field);
            if (proxy) { proxy.click(); }
            t.style.display = 'none';
        });
        t.appendChild(btn);

        // Show first so getBoundingClientRect is meaningful
        t.style.display = 'inline-flex';

        requestAnimationFrame(function () {
            var margin   = 8;
            var markRect = mark.getBoundingClientRect();
            var tRect    = t.getBoundingClientRect();

            var left = markRect.left + markRect.width / 2 - tRect.width / 2;
            left = Math.max(margin, Math.min(window.innerWidth - tRect.width - margin, left));

            var top = markRect.top - tRect.height - 4;
            if (top < margin) { top = markRect.bottom + 4; }

            t.style.left = left + 'px';
            t.style.top  = top  + 'px';
        });
    }

    document.addEventListener('mouseover', function (e) {
        var mark = e.target.closest('mark[data-start]');
        if (mark) { showTooltip(mark); }
    }, true);

    document.addEventListener('mouseout', function (e) {
        var mark = e.target.closest('mark[data-start]');
        if (mark) { scheduleHide(); }
    }, true);
})();
