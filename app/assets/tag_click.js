// Enhanced user interaction for apartment panel
window.addEventListener('DOMContentLoaded', function() {
    // Keyboard navigation for the details panel
    document.addEventListener('keydown', function(e) {
        if (isDetailsPanelVisible()) {
            if (e.key === 'Escape') {
                closeDetailsPanel();
            } else if (e.key === 'ArrowLeft') {
                document.getElementById('prev-apartment-button').click();
            } else if (e.key === 'ArrowRight') {
                document.getElementById('next-apartment-button').click();
            }
        }
    });

    // Close panel when clicking on overlay
    document.addEventListener('click', function(e) {
        if (e.target.id === 'details-overlay' && isDetailsPanelVisible()) {
            closeDetailsPanel();
        }
    });

    // Disable body scroll when panel is open
    function isDetailsPanelVisible() {
        const panel = document.getElementById('apartment-details-panel');
        return panel && !panel.classList.contains('details-panel--hidden');
    }

    function closeDetailsPanel() {
        // This function will be called by Dash callbacks
        // It's defined here for the keydown event handler
    }

    // Animation for panel transitions
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === 'class') {
                const panel = mutation.target;
                if (panel.classList.contains('details-panel--visible')) {
                    document.body.classList.add('no-scroll');
                    document.getElementById('details-overlay').classList.remove('details-panel--hidden');
                    
                    // Focus trap for accessibility
                    setTimeout(() => {
                        const closeBtn = document.getElementById('close-details-button');
                        if (closeBtn) closeBtn.focus();
                    }, 100);
                } else if (panel.classList.contains('details-panel--hidden')) {
                    document.body.classList.remove('no-scroll');
                    document.getElementById('details-overlay').classList.add('details-panel--hidden');
                }
            }
        });
    });

    const panel = document.getElementById('apartment-details-panel');
    if (panel) {
        observer.observe(panel, { attributes: true });
    }

    // Enhanced slideshow interaction
    document.addEventListener('click', function(e) {
        // Detect clicks on slideshow navigation buttons
        if (e.target.classList.contains('slideshow-nav-btn')) {
            // Add transition effect to image
            const slideshowContainer = e.target.closest('.slideshow-container');
            if (slideshowContainer) {
                const img = slideshowContainer.querySelector('.slideshow-img');
                if (img) {
                    img.classList.add('transitioning');
                    setTimeout(() => {
                        img.classList.remove('transitioning');
                    }, 300);
                }
            }
        }
    });
});

// Add custom CSS for interactions
const style = document.createElement('style');
style.textContent = `
    body.no-scroll {
        overflow: hidden;
    }
    
    .slideshow-img.transitioning {
        opacity: 0.7;
        transition: opacity 0.3s ease;
    }
    
    .details-nav-button:focus,
    .details-close-x:focus {
        outline: 2px solid var(--color-primary);
        outline-offset: 2px;
    }
    
    @media (hover: hover) {
        .slideshow-nav-btn {
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .slideshow-container:hover .slideshow-nav-btn {
            opacity: 0.7;
        }
        
        .slideshow-container:hover .slideshow-nav-btn:hover {
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);