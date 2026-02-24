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
                });
            }
            
            // Don't update the output
            return window.dash_clientside.no_update;
        }
    }
});
