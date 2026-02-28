/**
 * Keyboard navigation for Tater annotation tool.
 *
 * Arrow left/right: navigate to previous/next document.
 * Arrow up/down: scroll the document viewer.
 * Scroll resets to top whenever document content changes.
 */

document.addEventListener('DOMContentLoaded', function () {

    // Arrow key handler
    document.addEventListener('keydown', function (e) {
        // Don't intercept when the user is typing in an input or textarea
        const tag = document.activeElement && document.activeElement.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || (document.activeElement && document.activeElement.isContentEditable)) {
            return;
        }

        if (e.key === 'f') {
            e.preventDefault();
            const cb = document.getElementById('flag-document');
            if (cb) cb.click();
        } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            const btn = document.getElementById('btn-prev');
            if (btn) btn.click();
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            const btn = document.getElementById('btn-next');
            if (btn) btn.click();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const el = document.getElementById('document-content');
            if (el) el.scrollBy({ top: -120, behavior: 'smooth' });
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            const el = document.getElementById('document-content');
            if (el) el.scrollBy({ top: 120, behavior: 'smooth' });
        }
    });

    // Reset scroll to top whenever the document content changes (i.e. user navigates)
    function attachScrollReset() {
        const el = document.getElementById('document-content');
        if (!el) {
            setTimeout(attachScrollReset, 100);
            return;
        }
        const observer = new MutationObserver(function () {
            el.scrollTop = 0;
        });
        observer.observe(el, { childList: true, subtree: true, characterData: true });
    }
    attachScrollReset();
});
