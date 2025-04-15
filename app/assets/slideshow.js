// slideshow-touch.js - Place this in your assets folder to add touch support
// This will be loaded automatically without needing to register additional callbacks

document.addEventListener('DOMContentLoaded', function() {
    // Function to initialize touch events on slideshow
    function initSlideshowTouch() {
        // Find all slideshow containers
        const slideshows = document.querySelectorAll('.slideshow-container');
        
        slideshows.forEach(slideshow => {
            // Skip if already initialized
            if (slideshow.getAttribute('data-touch-initialized') === 'true') return;
            
            let startX, startY;
            const threshold = 50; // Minimum distance for swipe
            
            slideshow.addEventListener('touchstart', function(e) {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
            }, { passive: true });
            
            slideshow.addEventListener('touchend', function(e) {
                if (!startX) return;
                
                const endX = e.changedTouches[0].clientX;
                const endY = e.changedTouches[0].clientY;
                
                // Calculate distance
                const diffX = startX - endX;
                const diffY = startY - endY;
                
                // Check if horizontal swipe (not vertical scrolling)
                if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > threshold) {
                    if (diffX > 0) {
                        // Swipe left - next image
                        const nextBtn = slideshow.querySelector('.slideshow-nav-btn--next');
                        if (nextBtn) nextBtn.click();
                    } else {
                        // Swipe right - previous image
                        const prevBtn = slideshow.querySelector('.slideshow-nav-btn--prev');
                        if (prevBtn) prevBtn.click();
                    }
                }
                
                // Reset
                startX = null;
                startY = null;
            }, { passive: true });
            
            // Mark as initialized
            slideshow.setAttribute('data-touch-initialized', 'true');
        });
    }
    
    // Initialize immediately for any existing slideshows
    setTimeout(initSlideshowTouch, 500);
    
    // Setup MutationObserver to watch for when the details panel becomes visible
    const detailsPanel = document.getElementById('apartment-details-panel');
    if (detailsPanel) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'class') {
                    if (!detailsPanel.classList.contains('details-panel--hidden')) {
                        // Panel became visible - initialize touch events
                        setTimeout(initSlideshowTouch, 100);
                    }
                } else if (mutation.type === 'childList') {
                    // Check if new slideshow was added
                    setTimeout(initSlideshowTouch, 100);
                }
            });
        });
        
        // Start observing panel for attribute changes and child additions
        observer.observe(detailsPanel, { 
            attributes: true, 
            attributeFilter: ['class'],
            childList: true,
            subtree: true 
        });
    }
});