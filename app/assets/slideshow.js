// Enhanced slideshow touch support with debugging
// Place this in your assets folder to add touch support to slideshows

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - initializing slideshow touch support');
    
    // Track initialized slideshows to prevent duplication
    window.initializedSlideshows = new Set();
    
    // Reset click counters when details panel closes
    function resetSlideshowState() {
        console.log('Resetting slideshow state');
        // Don't use global variables, reset each specific slideshow state
        for (const key in window) {
            if (key.startsWith('slideshow_')) {
                console.log('Resetting state for', key);
                delete window[key];
            }
        }
        window.initializedSlideshows.clear();
    }
    
    // Initialize touch events on slideshow - improved version
    function initSlideshowTouch() {
        // Find all slideshow containers
        const slideshows = document.querySelectorAll('.slideshow-container');
        console.log('Found', slideshows.length, 'slideshows to initialize');
        
        slideshows.forEach(slideshow => {
            // Get the offer ID from the closest parent with data-offer-id
            const parentCard = slideshow.closest('[data-offer-id]');
            const offerId = parentCard ? parentCard.dataset.offerId : null;
            
            // Skip if already initialized using our tracking Set
            if (offerId && window.initializedSlideshows.has(offerId)) {
                console.log('Slideshow already initialized for offer ID:', offerId);
                return;
            }
            
            // Add to initialized set
            if (offerId) {
                window.initializedSlideshows.add(offerId);
                console.log('Initializing touch events for slideshow offer ID:', offerId);
            } else {
                console.warn('Could not find offer ID for slideshow', slideshow);
            }
            
            // Mark with data attribute as well
            slideshow.setAttribute('data-touch-initialized', 'true');
            
            let startX, startY;
            const threshold = 50; // Minimum distance for swipe
            
            slideshow.addEventListener('touchstart', function(e) {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
                console.log('Touch start detected at', startX, startY, 'for offer ID:', offerId);
            }, { passive: true });
            
            slideshow.addEventListener('touchend', function(e) {
                if (!startX) return;
                
                const endX = e.changedTouches[0].clientX;
                const endY = e.changedTouches[0].clientY;
                
                // Calculate distance
                const diffX = startX - endX;
                const diffY = startY - endY;
                
                console.log('Touch end detected:', {
                    diffX,
                    diffY,
                    isHorizontalSwipe: Math.abs(diffX) > Math.abs(diffY),
                    exceedsThreshold: Math.abs(diffX) > threshold,
                    offerId
                });
                
                // Check if horizontal swipe (not vertical scrolling)
                if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > threshold) {
                    if (diffX > 0) {
                        // Swipe left - next image
                        console.log('Swipe LEFT detected - trying to click next button');
                        const nextBtn = slideshow.querySelector('.slideshow-nav-btn--next');
                        if (nextBtn) {
                            console.log('Next button found, clicking for offer ID:', offerId);
                            nextBtn.click();
                        } else {
                            console.warn('Next button not found');
                        }
                    } else {
                        // Swipe right - previous image
                        console.log('Swipe RIGHT detected - trying to click prev button');
                        const prevBtn = slideshow.querySelector('.slideshow-nav-btn--prev');
                        if (prevBtn) {
                            console.log('Prev button found, clicking for offer ID:', offerId);
                            prevBtn.click();
                        } else {
                            console.warn('Prev button not found');
                        }
                    }
                }
                
                // Reset
                startX = null;
                startY = null;
            }, { passive: true });
            
            console.log('Touch events fully initialized for slideshow', offerId || 'unknown');
        });
    }
    
    // Initialize with a longer delay to ensure DOM is fully loaded
    setTimeout(initSlideshowTouch, 800);
    
    // Watch for the close button click to reset state
    const closeButton = document.getElementById('close-details-button');
    if (closeButton) {
        console.log('Found close button, adding reset listener');
        closeButton.addEventListener('click', resetSlideshowState);
    } else {
        console.warn('Close button not found on initial load');
        
        // Try to find it again later - it might be added dynamically
        setTimeout(function() {
            const retryCloseButton = document.getElementById('close-details-button');
            if (retryCloseButton) {
                console.log('Found close button on retry, adding reset listener');
                retryCloseButton.addEventListener('click', resetSlideshowState);
            }
        }, 2000);
    }
    
    // Setup MutationObserver to watch for when the details panel becomes visible or changes
    const detailsPanel = document.getElementById('apartment-details-panel');
    if (detailsPanel) {
        console.log('Found details panel, setting up observer');
        const observer = new MutationObserver(function(mutations) {
            let shouldInit = false;
            let isPanelHidden = false;
            
            mutations.forEach(function(mutation) {
                // Check if panel visibility changed
                if (mutation.attributeName === 'class') {
                    console.log('Panel class changed:', detailsPanel.className);
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
                        console.log('Slideshow container added to DOM');
                        shouldInit = true;
                        // Wait slightly longer for content to fully render
                        setTimeout(initSlideshowTouch, 300);
                    }
                }
            });
            
            if (shouldInit) {
                console.log('Should initialize slideshows based on DOM changes');
                setTimeout(initSlideshowTouch, 200);
            }
        });
        
        // Start observing panel for attribute changes and child additions
        observer.observe(detailsPanel, { 
            attributes: true, 
            attributeFilter: ['class'],
            childList: true,
            subtree: true 
        });
        console.log('Observer set up for details panel');
    } else {
        console.warn('Details panel not found on initial load');
        
        // Try to find it again later - it might be added dynamically
        setTimeout(function() {
            const retryDetailsPanel = document.getElementById('apartment-details-panel');
            if (retryDetailsPanel) {
                console.log('Found details panel on retry, setting up observer');
                const observer = new MutationObserver(function() {
                    console.log('Details panel changed, initializing slideshows');
                    setTimeout(initSlideshowTouch, 200);
                });
                
                observer.observe(retryDetailsPanel, { 
                    attributes: true, 
                    attributeFilter: ['class'],
                    childList: true,
                    subtree: true 
                });
            }
        }, 2000);
    }
    
    // Also watch the apartment-details-card element specifically
    const detailsCard = document.getElementById('apartment-details-card');
    if (detailsCard) {
        console.log('Found details card, setting up observer');
        const cardObserver = new MutationObserver(function(mutations) {
            // Run initialization when card content changes
            console.log('Details card content changed, initializing slideshows');
            setTimeout(initSlideshowTouch, 200);
        });
        
        cardObserver.observe(detailsCard, {
            childList: true,
            subtree: false
        });
        console.log('Observer set up for details card');
    } else {
        console.warn('Details card not found on initial load');
        
        // Try to find it again later - it might be added dynamically
        setTimeout(function() {
            const retryDetailsCard = document.getElementById('apartment-details-card');
            if (retryDetailsCard) {
                console.log('Found details card on retry, setting up observer');
                const cardObserver = new MutationObserver(function() {
                    console.log('Details card content changed, initializing slideshows');
                    setTimeout(initSlideshowTouch, 200);
                });
                
                cardObserver.observe(retryDetailsCard, {
                    childList: true,
                    subtree: false
                });
            }
        }, 2000);
    }
});