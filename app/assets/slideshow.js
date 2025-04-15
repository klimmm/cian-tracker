javascript// slideshow.js
function initializeSlideshow() {
    // Get all slideshows on the page
    const slideshows = document.querySelectorAll('.slideshow-container');
    
    slideshows.forEach(slideshow => {
        let startX;
        let endX;
        
        // Add touch event listeners for swipe functionality
        slideshow.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
        }, false);
        
        slideshow.addEventListener('touchend', (e) => {
            endX = e.changedTouches[0].clientX;
            handleSwipe();
        }, false);
        
        function handleSwipe() {
            const threshold = 50; // Minimum swipe distance
            
            if (startX - endX > threshold) {
                // Swipe left - go to next slide
                const nextBtn = slideshow.querySelector('.slideshow-nav-btn--next');
                if (nextBtn) nextBtn.click();
            }
            
            if (endX - startX > threshold) {
                // Swipe right - go to previous slide
                const prevBtn = slideshow.querySelector('.slideshow-nav-btn--prev');
                if (prevBtn) prevBtn.click();
            }
        }
    });
}

// Initialize after DOM has loaded
document.addEventListener('DOMContentLoaded', initializeSlideshow);

// Also reinitialize when the details panel becomes visible
function setupDetailsPanel() {
    const detailsPanel = document.getElementById('apartment-details-panel');
    
    // Create a MutationObserver to watch for visibility changes
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'class') {
                if (!detailsPanel.classList.contains('details-panel--hidden')) {
                    // Panel became visible, initialize the slideshow
                    setTimeout(initializeSlideshow, 100);
                }
            }
        });
    });
    
    // Start observing
    if (detailsPanel) {
        observer.observe(detailsPanel, { attributes: true });
    }
}

// Set up the observer when the page loads
document.addEventListener('DOMContentLoaded', setupDetailsPanel);