// Improved Basic Apartment Card Swipe Navigation
// Add this to your assets folder (e.g., assets/js/apartment-swipe.js)

document.addEventListener('DOMContentLoaded', function() {
    // Declare all variables at the top of the scope
    let startX = null;
    let startY = null;
    let startTime = null;
    let isDragging = false;
    let leftIndicator = null;
    let rightIndicator = null;
    console.log('Apartment swipe script loaded');
    console.log('Initializing improved basic apartment card swipe navigation');
    
    // Add simple indicators
    if (!document.getElementById('swipe-styles')) {
        const styleEl = document.createElement('style');
        styleEl.id = 'swipe-styles';
        styleEl.textContent = `
            .swipe-indicator {
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 12px 8px;
                border-radius: 6px;
                z-index: 100;
                opacity: 0;
                transition: opacity 0.2s ease;
                pointer-events: none;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            
            .swipe-indicator--left {
                left: 15px;
            }
            
            .swipe-indicator--right {
                right: 15px;
            }
            
            .swipe-indicator.active {
                opacity: 0.9;
            }
            
            .swipe-arrow {
                font-size: 24px;
                margin-bottom: 3px;
            }
            
            .swipe-text {
                font-size: 12px;
            }
        `;
        document.head.appendChild(styleEl);
    }
    
    // Function to reset any ongoing swipe effects
    function resetSwipeEffects() {
        // Hide indicators if they exist
        if (leftIndicator) leftIndicator.classList.remove('active');
        if (rightIndicator) rightIndicator.classList.remove('active');
    }
    
    function initApartmentSwipe() {
        // Target the details panel which contains the entire apartment card
        const detailsPanel = document.getElementById('apartment-details-panel');
        
        if (!detailsPanel) {
            console.warn('Details panel not found for swipe navigation');
            return;
        }
        
        console.log('Setting up improved basic apartment card swipe navigation');
        
        // Get navigation buttons
        const prevButton = document.getElementById('prev-apartment-button');
        const nextButton = document.getElementById('next-apartment-button');
        
        if (!prevButton || !nextButton) {
            console.warn('Navigation buttons not found, aborting swipe setup');
            return;
        }
        
        // Create indicators if they don't exist
        if (!leftIndicator) {
            leftIndicator = document.createElement('div');
            leftIndicator.className = 'swipe-indicator swipe-indicator--left';
            leftIndicator.innerHTML = '<div class="swipe-arrow">←</div><div class="swipe-text">Previous</div>';
        }
        
        if (!rightIndicator) {
            rightIndicator = document.createElement('div');
            rightIndicator.className = 'swipe-indicator swipe-indicator--right';
            rightIndicator.innerHTML = '<div class="swipe-arrow">→</div><div class="swipe-text">Next</div>';
        }
        
        // Add indicators to the panel if not already there
        if (!detailsPanel.querySelector('.swipe-indicator--left')) {
            detailsPanel.appendChild(leftIndicator);
        }
        
        if (!detailsPanel.querySelector('.swipe-indicator--right')) {
            detailsPanel.appendChild(rightIndicator);
        }
        
        const minSwipeDistance = 80;   // Slightly reduced minimum distance
        const maxSwipeTime = 600;      // Slightly increased maximum time
        const maxVerticalDeviation = 100;
        
        // Mark panel to avoid duplicate initialization
        if (detailsPanel.getAttribute('data-swipe-nav-initialized') === 'true') {
            console.log('Apartment card swipe navigation already initialized');
            return;
        }
        
        detailsPanel.setAttribute('data-swipe-nav-initialized', 'true');
        
        // Touch events for mobile devices
        detailsPanel.addEventListener('touchstart', function(e) {
            // Skip if touch started in slideshow to avoid conflict
            if (e.target.closest('.slideshow-container') || e.target.closest('button') || 
                e.target.closest('[data-touch-initialized="true"]')) {
                console.log('Touch start in slideshow or button, ignoring for card swipe');
                return;
            }
            
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            startTime = new Date().getTime();
            
            console.log('Touch start:', { x: startX, y: startY, time: startTime });
            
            // Reset indicators
            resetSwipeEffects();
        }, { passive: true });
        
        detailsPanel.addEventListener('touchmove', function(e) {
            // Skip if touch started in slideshow to avoid conflict
            if (!startX || !startTime || e.target.closest('.slideshow-container') || 
                e.target.closest('[data-touch-initialized="true"]')) {
                return;
            }
            
            const currentX = e.touches[0].clientX;
            const currentY = e.touches[0].clientY;
            
            // Calculate distances
            const distanceX = currentX - startX;
            const distanceY = Math.abs(currentY - startY);
            
            console.log('Touch move:', { 
                distX: distanceX, 
                distY: distanceY, 
                threshold: maxVerticalDeviation 
            });
            
            // Show indicators during swipe to provide visual feedback
            if (Math.abs(distanceX) > 30 && distanceY < maxVerticalDeviation) {
                if (distanceX > 0) {
                    // Right movement = previous
                    leftIndicator.classList.add('active');
                    rightIndicator.classList.remove('active');
                } else {
                    // Left movement = next
                    rightIndicator.classList.add('active');
                    leftIndicator.classList.remove('active');
                }
            } else {
                // Reset if not a clear horizontal movement
                resetSwipeEffects();
            }
        }, { passive: true });
        
        detailsPanel.addEventListener('touchend', function(e) {
            // Skip if touch started in slideshow to avoid conflict
            if (!startX || !startTime || e.target.closest('.slideshow-container') || 
                e.target.closest('[data-touch-initialized="true"]')) {
                return;
            }
            
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const endTime = new Date().getTime();
            const elapsedTime = endTime - startTime;
            
            // Calculate distances
            const distanceX = startX - endX;
            const distanceY = Math.abs(startY - endY);
            
            console.log('Apartment card swipe detected:', {
                distanceX,
                distanceY,
                elapsedTime,
                isQuickSwipe: elapsedTime < maxSwipeTime,
                isLongEnough: Math.abs(distanceX) > minSwipeDistance,
                isHorizontal: distanceY < maxVerticalDeviation
            });
            
            // Hide indicators
            resetSwipeEffects();
            
            // Validate swipe - must be quick, long enough, and primarily horizontal
            if (elapsedTime < maxSwipeTime && 
                Math.abs(distanceX) > minSwipeDistance && 
                distanceY < maxVerticalDeviation) {
                
                if (distanceX > 0) {
                    // Left swipe - next apartment
                    console.log('LEFT swipe detected - going to next apartment');
                    // Force focus on the button before clicking to ensure event triggers
                    nextButton.focus();
                    nextButton.click();
                    console.log('Next button clicked');
                } else {
                    // Right swipe - previous apartment
                    console.log('RIGHT swipe detected - going to previous apartment');
                    // Force focus on the button before clicking to ensure event triggers
                    prevButton.focus();
                    prevButton.click();
                    console.log('Previous button clicked');
                }
                
                // Create a direct event as a fallback
                if (distanceX > 0) {
                    // Fallback event for next button
                    setTimeout(function() {
                        const event = new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        nextButton.dispatchEvent(event);
                        console.log('Dispatched fallback event for next button');
                    }, 50);
                } else {
                    // Fallback event for previous button
                    setTimeout(function() {
                        const event = new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        prevButton.dispatchEvent(event);
                        console.log('Dispatched fallback event for previous button');
                    }, 50);
                }
            }
            
            // Reset
            startX = null;
            startY = null;
            startTime = null;
        }, { passive: true });
        
        // For desktop testing - using Shift+Mouse for simulation
        detailsPanel.addEventListener('mousedown', function(e) {
            // Skip if in slideshow to avoid conflict
            if (e.target.closest('.slideshow-container') || e.target.closest('[data-touch-initialized="true"]')) {
                return; 
            }
            
            if (e.shiftKey && !e.target.closest('button')) {
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
                startTime = new Date().getTime();
                e.preventDefault();
                console.log('Starting apartment card swipe simulation at', startX, startY);
                
                // Reset indicators
                resetSwipeEffects();
            }
        });
        
        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            
            const currentX = e.clientX;
            const currentY = e.clientY;
            
            // Calculate distances
            const distanceX = currentX - startX;
            const distanceY = Math.abs(currentY - startY);
            
            // Show indicators during swipe
            if (Math.abs(distanceX) > 30 && distanceY < maxVerticalDeviation) {
                if (distanceX > 0) {
                    // Right movement = previous
                    leftIndicator.classList.add('active');
                    rightIndicator.classList.remove('active');
                } else {
                    // Left movement = next
                    rightIndicator.classList.add('active');
                    leftIndicator.classList.remove('active');
                }
            } else {
                // Reset if not a clear horizontal movement
                resetSwipeEffects();
            }
            
            e.preventDefault();
        });
        
        document.addEventListener('mouseup', function(e) {
            if (!isDragging) return;
            
            const endX = e.clientX;
            const endY = e.clientY;
            const endTime = new Date().getTime();
            const elapsedTime = endTime - startTime;
            
            // Calculate distances
            const distanceX = startX - endX;
            const distanceY = Math.abs(startY - endY);
            
            console.log('Apartment card swipe simulation ended:', {
                distanceX,
                distanceY,
                elapsedTime,
                isQuickSwipe: elapsedTime < maxSwipeTime,
                isLongEnough: Math.abs(distanceX) > minSwipeDistance,
                isHorizontal: distanceY < maxVerticalDeviation
            });
            
            // Hide indicators
            resetSwipeEffects();
            
            // Validate swipe
            if (elapsedTime < maxSwipeTime && 
                Math.abs(distanceX) > minSwipeDistance && 
                distanceY < maxVerticalDeviation) {
                
                if (distanceX > 0) {
                    // Left swipe - next apartment
                    console.log('LEFT swipe detected - going to next apartment');
                    nextButton.focus();
                    nextButton.click();
                    console.log('Next button clicked');
                } else {
                    // Right swipe - previous apartment
                    console.log('RIGHT swipe detected - going to previous apartment');
                    prevButton.focus();
                    prevButton.click();
                    console.log('Previous button clicked');
                }
                
                // Create a direct event as a fallback
                if (distanceX > 0) {
                    // Fallback event for next button
                    setTimeout(function() {
                        const event = new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        nextButton.dispatchEvent(event);
                        console.log('Dispatched fallback event for next button');
                    }, 50);
                } else {
                    // Fallback event for previous button
                    setTimeout(function() {
                        const event = new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        prevButton.dispatchEvent(event);
                        console.log('Dispatched fallback event for previous button');
                    }, 50);
                }
            }
            
            isDragging = false;
            e.preventDefault();
        });
        
        console.log('Improved basic apartment card swipe navigation initialized');
    }
    
    // Initialize swipe on load and when content changes
    setTimeout(initApartmentSwipe, 1000);
    
    // Set up mutation observer to initialize swipe when panel becomes visible
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === 'class') {
                const detailsPanel = document.getElementById('apartment-details-panel');
                if (detailsPanel && !detailsPanel.classList.contains('details-panel--hidden')) {
                    setTimeout(initApartmentSwipe, 300);
                }
            }
        });
    });
    
    // Look for details panel
    const detailsPanel = document.getElementById('apartment-details-panel');
    if (detailsPanel) {
        observer.observe(detailsPanel, { 
            attributes: true, 
            attributeFilter: ['class'] 
        });
    } else {
        // Try again later, might not be in DOM yet
        setTimeout(function() {
            const retryPanel = document.getElementById('apartment-details-panel');
            if (retryPanel) {
                observer.observe(retryPanel, { 
                    attributes: true, 
                    attributeFilter: ['class'] 
                });
            }
        }, 2000);
    }
    
    // Make sure we reset swipe effects when needed
    document.addEventListener('click', function(e) {
        if (e.target.closest('#apartment-table') || e.target.id === 'close-details-button') {
            resetSwipeEffects();
        }
    });
});