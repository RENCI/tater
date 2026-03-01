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
 */

// ---------- clientside callbacks ----------

window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.tater = Object.assign({}, window.dash_clientside.tater || {}, {

    captureSelection: function (n_clicks_list) {
        var ctx = window.dash_clientside.callback_context;
        if (!ctx || !ctx.triggered || !ctx.triggered.length) {
            return window.dash_clientside.no_update;
        }

        // prop_id format: '{"field":"...","tag":"...","type":"..."}.n_clicks'
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
        var color = mark.style.backgroundColor      || '#ffe066';

        // Rebuild tooltip contents — the entire popup IS the colored label
        t.innerHTML = '';
        t.style.backgroundColor = color;
        t.appendChild(document.createTextNode(tag));

        var btn = document.createElement('button');
        btn.className = 'tater-tooltip-delete';
        btn.textContent = 'x';
        btn.addEventListener('click', function () {
            window._taterDeletePending = {
                field: field,
                start: parseInt(start, 10),
                end:   parseInt(end,   10),
                ts:    Date.now()
            };
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
