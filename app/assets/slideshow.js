// Improved slideshow touch support with better initialization
// Place this in your assets folder to add touch support to slideshows

document.addEventListener('DOMContentLoaded', function() {
    // Track initialized slideshows to prevent duplication
    window.initializedSlideshows = new Set();
    
    // Reset click counters when details panel closes
    function resetSlideshowState() {
        window.prevButtonClicks = 0;
        window.nextButtonClicks = 0;
        window.initializedSlideshows.clear();
    }
    
    // Initialize touch events on slideshow - improved version
    function initSlideshowTouch() {
        // Find all slideshow containers
        const slideshows = document.querySelectorAll('.slideshow-container');
        
        slideshows.forEach(slideshow => {
            // Get the offer ID from the closest parent with data-offer-id
            const parentCard = slideshow.closest('[data-offer-id]');
            const offerId = parentCard ? parentCard.dataset.offerId : null;
            
            // Skip if already initialized using our tracking Set
            if (offerId && window.initializedSlideshows.has(offerId)) {
                return;
            }
            
            // Add to initialized set
            if (offerId) {
                window.initializedSlideshows.add(offerId);
            }
            
            // Mark with data attribute as well
            slideshow.setAttribute('data-touch-initialized', 'true');
            
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
            
            console.log('Touch events initialized for slideshow', offerId || 'unknown');
        });
    }
    
    // Initialize immediately for any existing slideshows
    setTimeout(initSlideshowTouch, 500);
    
    // Watch for the close button click to reset state
    const closeButton = document.getElementById('close-details-button');
    if (closeButton) {
        closeButton.addEventListener('click', resetSlideshowState);
    }
    
    // Setup MutationObserver to watch for when the details panel becomes visible or changes
    const detailsPanel = document.getElementById('apartment-details-panel');
    if (detailsPanel) {
        const observer = new MutationObserver(function(mutations) {
            let shouldInit = false;
            let isPanelHidden = false;
            
            mutations.forEach(function(mutation) {
                // Check if panel visibility changed
                if (mutation.attributeName === 'class') {
                    if (detailsPanel.classList.contains('details-panel--hidden')) {
                        // Panel is now hidden - reset our state
                        resetSlideshowState();
                        isPanelHidden = true;
                    } else if (!detailsPanel.classList.contains('details-panel--hidden')) {
                        // Panel became visible
                        shouldInit = true;
                    }
                }
                
                // Check if content changed (new apartment loaded)
                if (mutation.type === 'childList' && !isPanelHidden) {
                    const wasSlideShowAdded = Array.from(mutation.addedNodes).some(node => 
                        node.querySelector && node.querySelector('.slideshow-container')
                    );
                    
                    if (wasSlideShowAdded) {
                        shouldInit = true;
                        // Wait slightly longer for content to fully render
                        setTimeout(initSlideshowTouch, 200);
                    }
                }
            });
            
            if (shouldInit) {
                setTimeout(initSlideshowTouch, 100);
            }
        });
        
        // Start observing panel for attribute changes and child additions
        observer.observe(detailsPanel, { 
            attributes: true, 
            attributeFilter: ['class'],
            childList: true,
            subtree: true 
        });
    }
    
    // Also watch the apartment-details-card element specifically
    const detailsCard = document.getElementById('apartment-details-card');
    if (detailsCard) {
        const cardObserver = new MutationObserver(function(mutations) {
            // Run initialization when card content changes
            setTimeout(initSlideshowTouch, 100);
        });
        
        cardObserver.observe(detailsCard, {
            childList: true,
            subtree: false
        });
    }
});