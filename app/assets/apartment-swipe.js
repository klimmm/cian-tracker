// Apartment Card Swipe Navigation
// Add this to your assets folder (e.g., assets/js/apartment-swipe.js)

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing apartment card swipe navigation');
    
    function initApartmentSwipe() {
        // Target the details panel which contains the entire apartment card
        const detailsPanel = document.getElementById('apartment-details-panel');
        
        if (!detailsPanel) {
            console.warn('Details panel not found for swipe navigation');
            return;
        }
        
        console.log('Setting up apartment card swipe navigation');
        
        // Get navigation buttons
        const prevButton = document.getElementById('prev-apartment-button');
        const nextButton = document.getElementById('next-apartment-button');
        
        if (!prevButton || !nextButton) {
            console.warn('Navigation buttons not found, aborting swipe setup');
            return;
        }
        
        let startX, startY, startTime;
        const minSwipeDistance = 100;  // Minimum distance for a swipe to register
        const maxSwipeTime = 500;      // Maximum time in ms for a swipe to register
        const maxVerticalDeviation = 100; // Maximum vertical movement allowed for horizontal swipe
        
        // Mark panel to avoid duplicate initialization
        if (detailsPanel.getAttribute('data-swipe-nav-initialized') === 'true') {
            console.log('Apartment card swipe navigation already initialized');
            return;
        }
        
        detailsPanel.setAttribute('data-swipe-nav-initialized', 'true');
        
        // Touch events for mobile devices
        detailsPanel.addEventListener('touchstart', function(e) {
            if (e.target.closest('.slideshow-container')) {
                // Skip if touch started in slideshow to avoid conflict
                return;
            }
            
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            startTime = new Date().getTime();
        }, { passive: true });
        
        detailsPanel.addEventListener('touchend', function(e) {
            if (!startX || !startTime || e.target.closest('.slideshow-container')) {
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
            
            // Validate swipe - must be quick, long enough, and primarily horizontal
            if (elapsedTime < maxSwipeTime && 
                Math.abs(distanceX) > minSwipeDistance && 
                distanceY < maxVerticalDeviation) {
                
                if (distanceX > 0) {
                    // Left swipe - next apartment
                    console.log('LEFT swipe detected - going to next apartment');
                    nextButton.click();
                } else {
                    // Right swipe - previous apartment
                    console.log('RIGHT swipe detected - going to previous apartment');
                    prevButton.click();
                }
            }
            
            // Reset
            startX = null;
            startY = null;
            startTime = null;
        }, { passive: true });
        
        // For desktop testing - using Shift+Mouse for simulation
        let isDragging = false;
        
        detailsPanel.addEventListener('mousedown', function(e) {
            if (e.shiftKey && !e.target.closest('.slideshow-container')) {
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
                startTime = new Date().getTime();
                e.preventDefault();
                console.log('Starting apartment card swipe simulation at', startX, startY);
            }
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
            
            // Validate swipe
            if (elapsedTime < maxSwipeTime && 
                Math.abs(distanceX) > minSwipeDistance && 
                distanceY < maxVerticalDeviation) {
                
                if (distanceX > 0) {
                    // Left swipe - next apartment
                    console.log('LEFT swipe detected - going to next apartment');
                    nextButton.click();
                } else {
                    // Right swipe - previous apartment
                    console.log('RIGHT swipe detected - going to previous apartment');
                    prevButton.click();
                }
            }
            
            isDragging = false;
            e.preventDefault();
        });
        
        console.log('Apartment card swipe navigation initialized');
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
});