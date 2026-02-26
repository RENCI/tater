/**
 * Keyboard navigation for Tater annotation tool
 */

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    tater: {
        setupKeyboardNav: function(current_index) {
            // Set up keyboard listener once
            if (!window.tater_kbd_setup) {
                window.tater_kbd_setup = true;
                
                document.addEventListener('keydown', function(e) {
                    // Left/Right arrows: Navigate between documents
                    if (e.key === 'ArrowLeft') {
                        e.preventDefault();
                        const prevBtn = document.getElementById('prev-button');
                        if (prevBtn && !prevBtn.disabled) {
                            prevBtn.click();
                        }
                    } else if (e.key === 'ArrowRight') {
                        e.preventDefault();
                        const nextBtn = document.getElementById('next-button');
                        if (nextBtn && !nextBtn.disabled) {
                            nextBtn.click();
                        }
                    }
                    // Up/Down arrows: Scroll within document
                    else if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        const docViewer = document.getElementById('document-viewer');
                        if (docViewer) {
                            // Find the scrollable Paper element (first child)
                            const scrollable = docViewer.querySelector('[style*="overflow"]');
                            if (scrollable) {
                                scrollable.scrollBy({ top: -120, behavior: 'smooth' });
                            }
                        }
                    } else if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        const docViewer = document.getElementById('document-viewer');
                        if (docViewer) {
                            // Find the scrollable Paper element (first child)
                            const scrollable = docViewer.querySelector('[style*="overflow"]');
                            if (scrollable) {
                                scrollable.scrollBy({ top: 120, behavior: 'smooth' });
                            }
                        }
                    }
                });
            }

            // Reset scroll to top when document changes
            const docViewer = document.getElementById('document-viewer');
            if (docViewer) {
                const scrollable = docViewer.querySelector('[style*="overflow"]');
                if (scrollable) {
                    scrollable.scrollTop = 0;
                }
            }
            
            // Don't update the output
            return window.dash_clientside.no_update;
        }
    }
});
