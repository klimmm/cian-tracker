/**
 * dashboard.js - Consolidated JavaScript for Cian Apartment Dashboard
 * Combines functionality from tag_click.js and modernized_interactions.js with reduced code size
 */

(function() {
  // Dashboard interaction handler
  const CianDashboard = {
    // Configuration with selector constants
    selectors: {
      tableContainer: '#table-container',
      table: '.dash-spreadsheet-container',
      tableRow: '.dash-spreadsheet tr',
      detailsButton: 'td[data-dash-column="details"]',
      detailsPanel: '#apartment-details-panel',
      detailsOverlay: '#details-overlay',
      closeButton: '#close-details-button',
      prevButton: '#prev-apartment-button',
      nextButton: '#next-apartment-button',
      slideshowContainer: '.slideshow-container',
      slideshowImg: '.slideshow-img',
      slideshowBtn: '.slideshow-nav-btn',
      highlightedClass: 'highlighted-row'
    },
    
    // Initialize the dashboard
    init: function() {
      this.setupEventListeners();
      this.observePanelChanges();
    },
    
    // Set up event listeners
    setupEventListeners: function() {
      // Keyboard navigation
      document.addEventListener('keydown', e => {
        if (this.isPanelVisible()) {
          if (e.key === 'Escape') this.closePanel();
          else if (e.key === 'ArrowLeft') this.clickButton(this.selectors.prevButton);
          else if (e.key === 'ArrowRight') this.clickButton(this.selectors.nextButton);
        }
      });
      
      // Click handlers with event delegation
      document.addEventListener('click', e => {
        // Close panel when clicking overlay
        if (e.target.id === 'details-overlay' && this.isPanelVisible()) {
          this.closePanel();
        }
        
        // Row selection in table
        if (e.target.closest(this.selectors.detailsButton)) {
          this.highlightRow(e.target.closest('tr'));
        }
        
        // Slideshow transitions
        if (e.target.classList.contains('slideshow-nav-btn')) {
          this.addTransitionEffect(e.target.closest('.slideshow-container'));
        }
      });
      
      // Add hover effects to buttons and rows
      this.setupHoverEffects();
    },
    
    // Check if details panel is visible
    isPanelVisible: function() {
      const panel = document.getElementById('apartment-details-panel');
      return panel && !panel.classList.contains('details-panel--hidden');
    },
    
    // Close the details panel
    closePanel: function() {
      this.clickButton(this.selectors.closeButton);
    },
    
    // Click a button by selector
    clickButton: function(selector) {
      const button = document.querySelector(selector);
      if (button) button.click();
    },
    
    // Highlight a table row
    highlightRow: function(row) {
      if (!row) return;
      
      // Remove existing highlights
      document.querySelectorAll('.' + this.selectors.highlightedClass)
        .forEach(el => el.classList.remove(this.selectors.highlightedClass));
      
      // Add highlight to current row
      row.classList.add(this.selectors.highlightedClass);
      
      // Scroll into view
      row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },
    
    // Add transition effect to slideshow images
    addTransitionEffect: function(container) {
      if (!container) return;
      
      const img = container.querySelector('.slideshow-img');
      if (img) {
        img.classList.add('transitioning');
        setTimeout(() => img.classList.remove('transitioning'), 300);
      }
    },
    
    // Set up hover effects for interactive elements
    setupHoverEffects: function() {
      // Using event delegation for better performance
      document.addEventListener('mouseover', e => {
        // Row hover effect
        const row = e.target.closest(this.selectors.tableRow);
        if (row && !row.classList.contains('dash-header-row')) {
          row.style.transition = 'transform 0.2s ease, box-shadow 0.2s ease';
          row.style.transform = 'translateY(-2px)';
          row.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
          row.style.zIndex = '2';
          row.style.position = 'relative';
        }
        
        // Button hover effect
        const button = e.target.closest('button');
        if (button) {
          button.style.transition = 'transform 0.2s ease, box-shadow 0.2s ease';
          button.style.transform = 'translateY(-1px)';
          button.style.boxShadow = '0 3px 6px rgba(0,0,0,0.15)';
        }
      });
      
      document.addEventListener('mouseout', e => {
        // Reset row hover effect
        const row = e.target.closest(this.selectors.tableRow);
        if (row && !row.classList.contains('dash-header-row')) {
          row.style.transform = '';
          row.style.boxShadow = '';
          row.style.zIndex = '';
        }
        
        // Reset button hover effect
        const button = e.target.closest('button');
        if (button) {
          button.style.transform = '';
          button.style.boxShadow = '';
        }
      });
    },
    
    // Observe panel state changes
    observePanelChanges: function() {
      const observer = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
          if (mutation.attributeName === 'class') {
            const panel = mutation.target;
            
            // When panel becomes visible
            if (panel.classList.contains('details-panel--visible')) {
              document.body.classList.add('no-scroll');
              const overlay = document.getElementById('details-overlay');
              if (overlay) overlay.classList.remove('details-panel--hidden');
              
              // Focus trap for accessibility
              setTimeout(() => {
                const closeBtn = document.getElementById('close-details-button');
                if (closeBtn) closeBtn.focus();
              }, 100);
            } 
            // When panel is hidden
            else if (panel.classList.contains('details-panel--hidden')) {
              document.body.classList.remove('no-scroll');
              const overlay = document.getElementById('details-overlay');
              if (overlay) overlay.classList.add('details-panel--hidden');
            }
          }
        });
      });
      
      // Start observing the details panel
      const panel = document.getElementById('apartment-details-panel');
      if (panel) {
        observer.observe(panel, { attributes: true });
      }
    }
  };
  
  // Initialize when DOM is loaded
  document.addEventListener('DOMContentLoaded', function() {
    CianDashboard.init();
  });
})();