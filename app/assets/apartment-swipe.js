// High Sensitivity Apartment Card Swipe Navigation
// Add this to your assets folder (e.g., assets/js/apartment-swipe.js)

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing high-sensitivity apartment card swipe navigation');
    
    // Create swipe indicators outside the initialization function to avoid recreating them
    let leftIndicator, rightIndicator;
    
    // Add styles only once
    if (!document.getElementById('swipe-styles')) {
        const styleEl = document.createElement('style');
        styleEl.id = 'swipe-styles';
        styleEl.textContent = `
            .swipe-indicator {
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                background-color: rgba(0, 0, 0, 0.6);
                color: white;
                padding: 15px 10px;
                border-radius: 8px;
                z-index: 100;
                opacity: 0;
                transition: opacity 0.2s ease, transform 0.2s ease;
                pointer-events: none;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            
            .swipe-indicator--left {
                left: 10px;
                transform: translateY(-50%) translateX(-20px);
            }
            
            .swipe-indicator--right {
                right: 10px;
                transform: translateY(-50%) translateX(20px);
            }
            
            .swipe-indicator.active {
                opacity: 0.9;
                transform: translateY(-50%) translateX(0);
            }
            
            .swipe-arrow {
                font-size: 28px;
                margin-bottom: 5px;
            }
            
            .swipe-text {
                font-size: 14px;
                font-weight: bold;
            }
            
            /* First-time hint */
            .swipe-tutorial {
                position: absolute;
                top: 10px;
                left: 50%;
                transform: translateX(-50%);
                background-color: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                font-size: 14px;
                text-align: center;
                z-index: 101;
                animation: fadeOut 5s forwards;
                pointer-events: none;
            }
            
            @keyframes fadeOut {
                0% { opacity: 0; }
                10% { opacity: 1; }
                80% { opacity: 1; }
                100% { opacity: 0; }
            }
            
            /* This class is added temporarily during swipe and removed afterward */
            .apartment-card-swiping {
                transition: transform 0.2s ease;
            }
        `;
        document.head.appendChild(styleEl);
    }
    
    // Function to reset any ongoing swipe effects
    function resetSwipeEffects() {
        // Find card content
        const contentCard = document.getElementById('apartment-details-card');
        if (contentCard) {
            // Reset any transforms and remove swiping class
            contentCard.style.transform = '';
            contentCard.classList.remove('apartment-card-swiping');
        }
        
        // Hide indicators if they exist
        if (leftIndicator) leftIndicator.classList.remove('active');
        if (rightIndicator) rightIndicator.classList.remove('active');
    }
    
    function initApartmentSwipe() {
        // Target the details panel which contains the entire apartment card
        const detailsPanel = document.getElementById('apartment-details-panel');
        const contentCard = document.getElementById('apartment-details-card');
        
        if (!detailsPanel || !contentCard) {
            console.warn('Details panel or content card not found for swipe navigation');
            return;
        }
        
        // Make sure we don't interfere with Dash's rendering
        resetSwipeEffects();
        
        console.log('Setting up high-sensitivity apartment card swipe navigation');
        
        // Get navigation buttons
        const prevButton = document.getElementById('prev-apartment-button');
        const nextButton = document.getElementById('next-apartment-button');
        
        if (!prevButton || !nextButton) {
            console.warn('Navigation buttons not found, aborting swipe setup');
            return;
        }
        
        // Mark panel to avoid duplicate initialization
        if (detailsPanel.getAttribute('data-swipe-nav-initialized') === 'true') {
            console.log('Apartment card swipe navigation already initialized');
            return;
        }
        
        detailsPanel.setAttribute('data-swipe-nav-initialized', 'true');
        
        // Create swipe indicators if they don't exist
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
        
        // Add a tutorial hint the first time
        if (!localStorage.getItem('apartment-swipe-tutorial-shown')) {
            const tutorial = document.createElement('div');
            tutorial.className = 'swipe-tutorial';
            tutorial.textContent = 'Swipe left or right to navigate between apartments';
            detailsPanel.appendChild(tutorial);
            
            // Mark as shown
            localStorage.setItem('apartment-swipe-tutorial-shown', 'true');
            
            // Remove after animation
            setTimeout(() => {
                if (tutorial.parentNode) {
                    tutorial.parentNode.removeChild(tutorial);
                }
            }, 5100);
        }
        
        let startX, startY, startTime, currentTranslateX = 0;
        const minSwipeDistance = 50;  // MUCH lower for higher sensitivity
        const maxSwipeTime = 800;     // MUCH more forgiving timing
        const maxVerticalDeviation = 150; // More forgiving for vertical movement
        let isCurrentlySwiping = false;
        let swipeIntention = null; // Track which direction user is intending to swipe
        
        // Touch events for mobile devices
        detailsPanel.addEventListener('touchstart', function(e) {
            if (e.target.closest('.slideshow-container') || 
                e.target.closest('button') ||
                isCurrentlySwiping) {
                // Skip if touch started in slideshow, on a button, or during an ongoing swipe
                return;
            }
            
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            startTime = new Date().getTime();
            currentTranslateX = 0;
            swipeIntention = null;
            isCurrentlySwiping = true;
            
            // Add the swiping class to enable transitions
            contentCard.classList.add('apartment-card-swiping');
        }, { passive: true });
        
        detailsPanel.addEventListener('touchmove', function(e) {
            if (!startX || !startTime || !isCurrentlySwiping) {
                return;
            }
            
            const currentX = e.touches[0].clientX;
            const currentY = e.touches[0].clientY;
            
            // Calculate distances
            const distanceX = currentX - startX;
            const distanceY = Math.abs(currentY - startY);
            
            // Only process horizontal movement if not too vertical
            if (distanceY < maxVerticalDeviation) {
                // Move the card with the finger (with LOWER resistance for easier movement)
                const resistance = 0.5; // HIGHER value = LESS resistance
                currentTranslateX = distanceX * resistance;
                contentCard.style.transform = `translateX(${currentTranslateX}px)`;
                
                // Show appropriate indicator based on swipe direction
                // Much more sensitive indicators
                if (distanceX > 10) { // Only 10px needed now
                    // Going right (previous)
                    leftIndicator.classList.add('active');
                    rightIndicator.classList.remove('active');
                    swipeIntention = 'prev';
                } else if (distanceX < -10) { // Only 10px needed now
                    // Going left (next)
                    rightIndicator.classList.add('active');
                    leftIndicator.classList.remove('active');
                    swipeIntention = 'next';
                } else {
                    // Not enough movement yet
                    leftIndicator.classList.remove('active');
                    rightIndicator.classList.remove('active');
                    swipeIntention = null;
                }
            }
        }, { passive: true });
        
        detailsPanel.addEventListener('touchend', function(e) {
            if (!startX || !startTime || !isCurrentlySwiping) {
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
                swipeIntention,
                isQuickSwipe: elapsedTime < maxSwipeTime,
                isLongEnough: Math.abs(distanceX) > minSwipeDistance,
                isHorizontal: distanceY < maxVerticalDeviation
            });
            
            // Hide indicators
            leftIndicator.classList.remove('active');
            rightIndicator.classList.remove('active');
            
            // Use a combination of methods to determine swipe:
            // 1. Traditional distance/time check
            // 2. OR check for clear swipe intention combined with some movement
            const traditionalSwipe = Math.abs(distanceX) > minSwipeDistance && 
                                     distanceY < maxVerticalDeviation &&
                                     elapsedTime < maxSwipeTime;
                                     
            const intentionalSwipe = swipeIntention !== null && 
                                    Math.abs(distanceX) > 25; // Even lower threshold if we detected intention
            
            if (traditionalSwipe || intentionalSwipe) {
                if ((distanceX > 0 && !swipeIntention) || swipeIntention === 'next') {
                    // Left swipe - next apartment
                    console.log('LEFT swipe detected - going to next apartment');
                    
                    // Animate slide out to left
                    contentCard.style.transform = 'translateX(-50px)';
                    setTimeout(() => {
                        resetSwipeEffects();
                        nextButton.click();
                    }, 100);
                    
                } else if ((distanceX <= 0 && !swipeIntention) || swipeIntention === 'prev') {
                    // Right swipe - previous apartment
                    console.log('RIGHT swipe detected - going to previous apartment');
                    
                    // Animate slide out to right
                    contentCard.style.transform = 'translateX(50px)';
                    setTimeout(() => {
                        resetSwipeEffects();
                        prevButton.click();
                    }, 100);
                }
            } else {
                // Not a valid swipe, animate back to center
                contentCard.style.transform = 'translateX(0)';
                
                // Remove the swiping class after the transition is complete
                setTimeout(() => {
                    resetSwipeEffects();
                }, 300);
            }
            
            // Reset
            startX = null;
            startY = null;
            startTime = null;
            swipeIntention = null;
            isCurrentlySwiping = false;
        }, { passive: true });
        
        // For desktop testing - using Shift+Mouse for simulation
        let isDragging = false;
        
        detailsPanel.addEventListener('mousedown', function(e) {
            if (e.shiftKey && 
                !e.target.closest('.slideshow-container') && 
                !e.target.closest('button') &&
                !isCurrentlySwiping) {
                
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
                startTime = new Date().getTime();
                currentTranslateX = 0;
                swipeIntention = null;
                isCurrentlySwiping = true;
                e.preventDefault();
                
                // Add the swiping class to enable transitions
                contentCard.classList.add('apartment-card-swiping');
                
                console.log('Starting apartment card swipe simulation at', startX, startY);
            }
        });
        
        document.addEventListener('mousemove', function(e) {
            if (!isDragging || !isCurrentlySwiping) return;
            
            const currentX = e.clientX;
            const currentY = e.clientY;
            
            // Calculate distances
            const distanceX = currentX - startX;
            const distanceY = Math.abs(currentY - startY);
            
            // Only process horizontal movement if not too vertical
            if (distanceY < maxVerticalDeviation) {
                // Move the card with the mouse (with LOWER resistance)
                const resistance = 0.5; // HIGHER value = LESS resistance
                currentTranslateX = distanceX * resistance;
                contentCard.style.transform = `translateX(${currentTranslateX}px)`;
                
                // Show appropriate indicator based on swipe direction
                if (distanceX > 10) {
                    // Going right (previous)
                    leftIndicator.classList.add('active');
                    rightIndicator.classList.remove('active');
                    swipeIntention = 'prev';
                } else if (distanceX < -10) {
                    // Going left (next)
                    rightIndicator.classList.add('active');
                    leftIndicator.classList.remove('active');
                    swipeIntention = 'next';
                } else {
                    // Not enough movement yet
                    leftIndicator.classList.remove('active');
                    rightIndicator.classList.remove('active');
                    swipeIntention = null;
                }
            }
            
            e.preventDefault();
        });
        
        document.addEventListener('mouseup', function(e) {
            if (!isDragging || !isCurrentlySwiping) return;
            
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
                swipeIntention,
                isQuickSwipe: elapsedTime < maxSwipeTime,
                isLongEnough: Math.abs(distanceX) > minSwipeDistance,
                isHorizontal: distanceY < maxVerticalDeviation
            });
            
            // Hide indicators
            leftIndicator.classList.remove('active');
            rightIndicator.classList.remove('active');
            
            // Use a combination of methods to determine swipe:
            // 1. Traditional distance/time check
            // 2. OR check for clear swipe intention combined with some movement
            const traditionalSwipe = Math.abs(distanceX) > minSwipeDistance && 
                                     distanceY < maxVerticalDeviation &&
                                     elapsedTime < maxSwipeTime;
                                     
            const intentionalSwipe = swipeIntention !== null && 
                                    Math.abs(distanceX) > 25; // Even lower threshold if we detected intention
            
            if (traditionalSwipe || intentionalSwipe) {
                if ((distanceX > 0 && !swipeIntention) || swipeIntention === 'next') {
                    // Left swipe - next apartment
                    console.log('LEFT swipe detected - going to next apartment');
                    
                    // Animate slide out to left
                    contentCard.style.transform = 'translateX(-50px)';
                    setTimeout(() => {
                        resetSwipeEffects();
                        nextButton.click();
                    }, 100);
                    
                } else if ((distanceX <= 0 && !swipeIntention) || swipeIntention === 'prev') {
                    // Right swipe - previous apartment
                    console.log('RIGHT swipe detected - going to previous apartment');
                    
                    // Animate slide out to right
                    contentCard.style.transform = 'translateX(50px)';
                    setTimeout(() => {
                        resetSwipeEffects();
                        prevButton.click();
                    }, 100);
                }
            } else {
                // Not a valid swipe, animate back to center
                contentCard.style.transform = 'translateX(0)';
                
                // Remove the swiping class after the transition is complete
                setTimeout(() => {
                    resetSwipeEffects();
                }, 300);
            }
            
            isDragging = false;
            isCurrentlySwiping = false;
            swipeIntention = null;
            e.preventDefault();
        });
        
        console.log('High-sensitivity apartment card swipe navigation initialized');
        
        // Listen for Dash updates that might reset our card
        const closeButton = document.getElementById('close-details-button');
        if (closeButton) {
            closeButton.addEventListener('click', resetSwipeEffects);
        }
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
            } else if (mutation.type === 'childList') {
                // If the content changed, wait a bit and re-initialize
                setTimeout(initApartmentSwipe, 300);
            }
        });
    });
    
    // Watch for all changes to the apartment-details-card
    const detailsCard = document.getElementById('apartment-details-card');
    if (detailsCard) {
        console.log('Setting up mutation observer for details card');
        observer.observe(detailsCard, {
            childList: true
        });
    }
    
    // Watch for class changes on the details panel
    const detailsPanel = document.getElementById('apartment-details-panel');
    if (detailsPanel) {
        console.log('Setting up mutation observer for details panel');
        observer.observe(detailsPanel, { 
            attributes: true, 
            attributeFilter: ['class'] 
        });
    }
    
    // Make sure we reset swipe effects when needed
    document.addEventListener('click', function(e) {
        if (e.target.closest('#apartment-table') || e.target.id === 'close-details-button') {
            resetSwipeEffects();
        }
    });
});