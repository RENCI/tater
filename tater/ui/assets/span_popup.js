/**
 * Popup UI for SpanPopupWidget.
 *
 * When the user selects text in the document viewer and the active widget is a
 * SpanPopupWidget (identified by data-tater-entities on its container), a floating
 * popup appears near the selection showing entity type buttons.  Clicking a button
 * sets window._taterPopupPending and clicks span-popup-proxy to trigger the Dash
 * callback (addSpanFromPopup, defined in span_annotations.js).
 *
 * No Dash functions are defined here — they live in span_annotations.js so they are
 * guaranteed to be loaded before any callbacks fire.
 */

(function () {
    var popup = null;
    var pendingSelection = null; // { text, start, end }

    function getPopup() {
        if (popup) { return popup; }
        popup = document.createElement('div');
        popup.id = 'tater-span-popup';
        popup.style.cssText = [
            'position:absolute',
            'z-index:9000',
            'display:none',
            'background:var(--mantine-color-body)',
            'border:1px solid var(--mantine-color-gray-3)',
            'border-radius:4px',
            'padding:4px 6px',
            'box-shadow:0 2px 8px rgba(0,0,0,0.18)',
            'white-space:nowrap',
        ].join(';');
        document.body.appendChild(popup);
        return popup;
    }

    function hidePopup() {
        var p = getPopup();
        p.style.display = 'none';
        pendingSelection = null;
    }

    function showPopup(range, container) {
        var p = getPopup();

        var entities;
        try {
            entities = JSON.parse(container.getAttribute('data-tater-entities') || '[]');
        } catch (e) { return; }
        var field = container.getAttribute('data-tater-field');
        if (!entities.length || !field) { return; }

        // Build entity buttons
        p.innerHTML = '';
        for (var i = 0; i < entities.length; i++) {
            (function (et, f) {
                var btn = document.createElement('button');
                btn.textContent = et.name;
                btn.style.cssText = [
                    'border:1px solid ' + et.color,
                    'background:' + et.lightColor,
                    'color:var(--mantine-color-gray-9)',
                    'padding:2px 8px',
                    'border-radius:3px',
                    'font-size:0.75rem',
                    'font-weight:600',
                    'cursor:pointer',
                    'margin:2px',
                ].join(';');

                // Prevent mousedown from collapsing the text selection before click fires
                btn.addEventListener('mousedown', function (e) { e.preventDefault(); });

                btn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    if (!pendingSelection) { hidePopup(); return; }

                    // Save scroll position so renderDocumentSpans can restore it
                    var docEl = document.getElementById('document-content');
                    if (docEl) { window._savedDocScroll = docEl.scrollTop; }
                    window.getSelection().removeAllRanges();

                    // Store for addSpanFromPopup (defined in span_annotations.js)
                    window._taterPopupPending = Object.assign({}, pendingSelection, {
                        tag: et.name,
                        field: f,
                    });
                    var proxy = document.getElementById('span-popup-proxy');
                    if (proxy) { proxy.click(); }

                    hidePopup();
                });
                p.appendChild(btn);
            })(entities[i], field);
        }

        // Display first so we can measure popup dimensions for positioning
        p.style.display = 'block';

        // Use the overall bounding rect of the selection to centre horizontally
        // and position above the top of the selection
        var bRect = range.getBoundingClientRect();
        var scrollX = window.pageXOffset || 0;
        var scrollY = window.pageYOffset || 0;
        var vw = document.documentElement.clientWidth;
        var margin = 6;

        // Centre over selection; clamp so it stays within the viewport horizontally
        var leftPx = (bRect.left + bRect.right) / 2 + scrollX - p.offsetWidth / 2;
        leftPx = Math.max(scrollX + margin, leftPx);
        leftPx = Math.min(scrollX + vw - p.offsetWidth - margin, leftPx);

        var topPx = bRect.top + scrollY - p.offsetHeight - 6;

        p.style.left = leftPx + 'px';
        p.style.top  = topPx  + 'px';
    }

    // ---- Close popup when clicking outside ----
    document.addEventListener('mousedown', function (e) {
        if (!popup || popup.style.display === 'none') { return; }
        if (!popup.contains(e.target)) { hidePopup(); }
    });

    // ---- Show popup on text selection in document-content ----
    document.addEventListener('mouseup', function () {
        // Small delay so the browser fully settles the selection
        setTimeout(function () {
            var sel = window.getSelection();
            if (!sel || sel.rangeCount === 0 || sel.toString().trim() === '') {
                hidePopup();
                return;
            }

            var range = sel.getRangeAt(0);
            var docEl = document.getElementById('document-content');
            if (!docEl || !docEl.contains(range.commonAncestorContainer)) {
                hidePopup();
                return;
            }

            // Only show popup when the active widget is a SpanPopupWidget
            // (identified by having a data-tater-entities attribute)
            var active = window._taterActiveWidget;
            var containers = document.querySelectorAll('[data-tater-entities]');
            if (!containers.length) { return; }

            var container = null;
            for (var i = 0; i < containers.length; i++) {
                if (containers[i].getAttribute('data-tater-field') === active) {
                    container = containers[i];
                    break;
                }
            }
            if (!container) {
                // Active widget is a SpanAnnotationWidget (no popup for it)
                return;
            }

            // Compute character offsets from the start of document-content
            var preRange = range.cloneRange();
            preRange.selectNodeContents(docEl);
            preRange.setEnd(range.startContainer, range.startOffset);
            var start = preRange.toString().length;
            var text  = sel.toString();
            var end   = start + text.length;

            pendingSelection = { text: text, start: start, end: end };
            showPopup(range, container);
        }, 20);
    });

})();
