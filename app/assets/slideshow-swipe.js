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
        const slideshows = document.querySelectorAll('.slideshow-container, .card-hero__slideshow');
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
            
            // Mark with data attribute as well - add multiple selectors to ensure we mark the right element
            slideshow.setAttribute('data-touch-initialized', 'true');
            
            // Also mark all parent elements up to the details panel to ensure card swipe sees them
            let parent = slideshow.parentElement;
            while (parent && !parent.classList.contains('details-panel')) {
                parent.setAttribute('data-contains-slideshow', 'true');
                parent = parent.parentElement;
            }
            
            // Mark all images and buttons inside slideshow
            slideshow.querySelectorAll('img, button').forEach(el => {
                el.setAttribute('data-slideshow-element', 'true');
            });
            
            let startX, startY;
            const threshold = 50; // Minimum distance for swipe
            
            // Add touchstart listener directly to slideshow and all its children
            function addTouchStartListener(element) {
                element.addEventListener('touchstart', function(e) {
                    // Mark the event to prevent it from triggering apartment card swipe
                    console.log('Slideshow touchstart captured');
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
                    startX = e.touches[0].clientX;
                    startY = e.touches[0].clientY;
                    console.log('Touch start detected at', startX, startY, 'for offer ID:', offerId);
                }, { passive: false, capture: true }); // Use capture phase to ensure we get the event first
            }
            
            // Add touchend listener directly to slideshow and all its children
            function addTouchEndListener(element) {
                element.addEventListener('touchend', function(e) {
                    // Stop propagation to prevent apartment card swipe
                    console.log('Slideshow touchend captured');
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
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
                        // Important: First try to find buttons by ID pattern, then by class
                        if (diffX > 0) {
                            // Swipe left - next image
                            console.log('Swipe LEFT detected - trying to click next button');
                            
                            // Try multiple selector approaches to find the next button
                            const nextBtn = 
                                // Look for pattern-matched ID button
                                slideshow.querySelector('[id*="next-btn"]') || 
                                slideshow.querySelector('[id*="{\\"type\\":\\"next-btn\\"]') ||
                                // Fall back to class selector
                                slideshow.querySelector('.slideshow-nav-btn--next');
                                
                            if (nextBtn) {
                                console.log('Next button found, clicking for offer ID:', offerId);
                                nextBtn.click();
                                
                                // Create and dispatch a direct click event as a backup
                                setTimeout(function() {
                                    const event = new MouseEvent('click', {
                                        bubbles: true,
                                        cancelable: true,
                                        view: window
                                    });
                                    nextBtn.dispatchEvent(event);
                                    console.log('Dispatched direct event to next button');
                                }, 50);
                            } else {
                                console.warn('Next button not found for slideshow');
                                // Log all available buttons for debugging
                                console.log('Available buttons:', 
                                    Array.from(slideshow.querySelectorAll('button'))
                                        .map(b => ({id: b.id, class: b.className}))
                                );
                            }
                        } else {
                            // Swipe right - previous image
                            console.log('Swipe RIGHT detected - trying to click prev button');
                            
                            // Try multiple selector approaches to find the prev button
                            const prevBtn = 
                                // Look for pattern-matched ID button
                                slideshow.querySelector('[id*="prev-btn"]') || 
                                slideshow.querySelector('[id*="{\\"type\\":\\"prev-btn\\"]') ||
                                // Fall back to class selector
                                slideshow.querySelector('.slideshow-nav-btn--prev');
                                
                            if (prevBtn) {
                                console.log('Prev button found, clicking for offer ID:', offerId);
                                prevBtn.click();
                                
                                // Create and dispatch a direct click event as a backup
                                setTimeout(function() {
                                    const event = new MouseEvent('click', {
                                        bubbles: true,
                                        cancelable: true,
                                        view: window
                                    });
                                    prevBtn.dispatchEvent(event);
                                    console.log('Dispatched direct event to prev button');
                                }, 50);
                            } else {
                                console.warn('Prev button not found for slideshow');
                                // Log all available buttons for debugging
                                console.log('Available buttons:', 
                                    Array.from(slideshow.querySelectorAll('button'))
                                        .map(b => ({id: b.id, class: b.className}))
                                );
                            }
                        }
                    }
                    
                    // Reset
                    startX = null;
                    startY = null;
                }, { passive: false, capture: true }); // Use capture phase to ensure we get the event first
            }
            
            // Add touchmove listener to prevent default scrolling behavior if needed
            function addTouchMoveListener(element) {
                element.addEventListener('touchmove', function(e) {
                    // Only prevent default if we're in a horizontal swipe to avoid disrupting vertical scrolling
                    if (startX) {
                        const moveX = e.touches[0].clientX;
                        const moveY = e.touches[0].clientY;
                        
                        const diffX = startX - moveX;
                        const diffY = startY - moveY;
                        
                        // If horizontal movement is greater than vertical, prevent default to avoid page scrolling
                        if (Math.abs(diffX) > Math.abs(diffY)) {
                            e.stopPropagation();
                            e.stopImmediatePropagation();
                        }
                    }
                }, { passive: false, capture: true });
            }

            // Add event listeners to the slideshow and all its children
            addTouchStartListener(slideshow);
            addTouchEndListener(slideshow);
            addTouchMoveListener(slideshow);
            
            // Also add to all direct children to ensure event capture
            slideshow.querySelectorAll('*').forEach(child => {
                addTouchStartListener(child);
                addTouchEndListener(child);
                addTouchMoveListener(child);
            });
            
            console.log('Touch events fully initialized for slideshow', offerId || 'unknown');
        });
    }
    
    // Function to check if slideshow is fully rendered before initializing
    function checkAndInitSlideshowTouch() {
        const slideshows = document.querySelectorAll('.slideshow-container, .card-hero__slideshow');
        if (slideshows.length > 0) {
            console.log('Found slideshows, initializing touch support');
            initSlideshowTouch();
        } else {
            console.log('No slideshows found yet, will retry');
            setTimeout(checkAndInitSlideshowTouch, 500);
        }
    }
    
    // Initialize with check and retry logic instead of fixed timeout
    checkAndInitSlideshowTouch();
    
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
                        node.querySelector && (
                            node.querySelector('.slideshow-container') || 
                            node.querySelector('.card-hero__slideshow')
                        )
                    );
                    
                    if (wasSlideShowAdded) {
                        console.log('Slideshow container added to DOM');
                        shouldInit = true;
                        // Wait slightly longer for content to fully render
                        setTimeout(checkAndInitSlideshowTouch, 300);
                    }
                }
            });
            
            if (shouldInit) {
                console.log('Should initialize slideshows based on DOM changes');
                setTimeout(checkAndInitSlideshowTouch, 200);
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
                    setTimeout(checkAndInitSlideshowTouch, 200);
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
            setTimeout(checkAndInitSlideshowTouch, 200);
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
                    setTimeout(checkAndInitSlideshowTouch, 200);
                });
                
                cardObserver.observe(retryDetailsCard, {
                    childList: true,
                    subtree: false
                });
            }
        }, 2000);
    }
});