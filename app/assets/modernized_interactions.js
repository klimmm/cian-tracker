// modernized_interactions.js - Enhanced interactions for Cian Apartment Dashboard

(function() {
  /**
   * Dashboard enhancement module
   * Adds modern UI interactions to the Cian Apartment Dashboard
   */
  const CianDashboardEnhancer = {
    // Configuration
    config: {
      // CSS class names and selectors
      selectors: {
        tableContainer: '#table-container',
        table: '.dash-spreadsheet-container',
        tableRow: '.dash-spreadsheet tr',
        detailsButton: 'td[data-dash-column="details"]',
        filterButtons: 'button[id^="btn-"]',
        activeFilterClass: 'filter-active',
        tagClass: 'span[style*="border-radius"]',
        detailsPanel: '#apartment-details-panel',
        slideShowContainer: '[id^="slideshow-img-"]',
        highlightedRow: 'highlighted-row'
      },
      
      // Animation durations
      animationDurations: {
        hover: 200,
        highlight: 300,
        fadeIn: 250
      },
      
      // Visual enhancement options
      visualOptions: {
        enableRowHover: true,
        enableTagHover: true,
        enableSmoothScrolling: true,
        enableButtonFeedback: true,
        enableCardAnimations: true,
        responsiveTextSize: true
      }
    },
    
    /**
     * Initialize dashboard enhancements
     */
    initialize: function() {
      // Safety check for browser environment
      if (typeof window === 'undefined') return;
      
      // Add event listeners and enhancements
      document.addEventListener('DOMContentLoaded', () => {
        this.setupFontLoading();
        this.setupTableInteractions();
        this.setupFilterButtonInteractions();
        this.setupDetailsPanel();
        this.setupResponsiveBehavior();
        this.setupAccessibilityImprovements();
      });
      
      // Some enhancements need to run immediately
      this.setupStyles();
      
      // Set up a mutation observer to handle dynamic content
      this.setupMutationObserver();
      
      console.log("Cian Dashboard Enhancer initialized");
    },
    
    /**
     * Load custom fonts
     */
    setupFontLoading: function() {
      // Add Inter font for better typography
      const fontLink = document.createElement('link');
      fontLink.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap';
      fontLink.rel = 'stylesheet';
      document.head.appendChild(fontLink);
    },
    
    /**
     * Add core styles dynamically
     */
    setupStyles: function() {
      // Add critical styles immediately
      const styleElement = document.createElement('style');
      styleElement.textContent = `
        /* Critical path styles */
        @keyframes pulseButtonFeedback {
          0% { transform: scale(1); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
          50% { transform: scale(1.05); box-shadow: 0 3px 6px rgba(0,0,0,0.15); }
          100% { transform: scale(1); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        /* Improved scrollbar */
        ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        
        ::-webkit-scrollbar-track {
          background: #f1f1f1;
          border-radius: 8px;
        }
        
        ::-webkit-scrollbar-thumb {
          background: #c1c1c1;
          border-radius: 8px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
          background: #a1a1a1;
        }
        
        /* Smooth scrolling */
        html {
          scroll-behavior: smooth;
        }
      `;
      document.head.appendChild(styleElement);
    },
    
    /**
     * Set up interactive behaviors for the data table
     */
    setupTableInteractions: function() {
      // Apply event delegation to handle table interactions
      document.addEventListener('click', (e) => {
        // Handle details button clicks
        if (e.target.closest(this.config.selectors.detailsButton)) {
          const row = e.target.closest('tr');
          this.highlightRow(row);
        }
      });
      
      // Add hover effects
      if (this.config.visualOptions.enableRowHover) {
        this.addHoverEffectsToTable();
      }
    },
    
    /**
     * Add hover interactions to table rows
     */
    addHoverEffectsToTable: function() {
      // Use event delegation for better performance
      document.addEventListener('mouseover', (e) => {
        const row = e.target.closest(this.config.selectors.tableRow);
        if (row && !row.classList.contains('dash-header-row')) {
          row.style.transition = `transform ${this.config.animationDurations.hover}ms ease, 
                                   box-shadow ${this.config.animationDurations.hover}ms ease`;
          row.style.transform = 'translateY(-2px)';
          row.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
          row.style.zIndex = '2';
          row.style.position = 'relative';
        }
      });
      
      document.addEventListener('mouseout', (e) => {
        const row = e.target.closest(this.config.selectors.tableRow);
        if (row && !row.classList.contains('dash-header-row')) {
          row.style.transform = 'translateY(0)';
          row.style.boxShadow = 'none';
          row.style.zIndex = '1';
        }
      });
    },
    
    /**
     * Highlight the selected row
     */
    highlightRow: function(row) {
      // Remove highlight from any previously highlighted row
      const highlighted = document.querySelectorAll(`.${this.config.selectors.highlightedRow}`);
      highlighted.forEach(el => el.classList.remove(this.config.selectors.highlightedRow));
      
      // Add highlight to the clicked row
      if (row) {
        row.classList.add(this.config.selectors.highlightedRow);
        
        // Ensure row is visible
        if (this.config.visualOptions.enableSmoothScrolling) {
          row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
    },
    
    /**
     * Set up interactive behaviors for filter buttons
     */
    setupFilterButtonInteractions: function() {
      // Add visual feedback for button clicks
      if (this.config.visualOptions.enableButtonFeedback) {
        document.addEventListener('click', (e) => {
          const button = e.target.closest(this.config.selectors.filterButtons);
          if (button) {
            // Add animation class
            button.style.animation = `pulseButtonFeedback ${this.config.animationDurations.hover}ms ease`;
            
            // Remove animation class after it completes
            setTimeout(() => {
              button.style.animation = '';
            }, this.config.animationDurations.hover);
          }
        });
      }
    },
    
    /**
     * Enhance details panel interactions
     */
    setupDetailsPanel: function() {
      if (this.config.visualOptions.enableCardAnimations) {
        // Improve animation for details panel
        const observer = new MutationObserver((mutations) => {
          mutations.forEach((mutation) => {
            if (mutation.attributeName === 'style') {
              const panel = mutation.target;
              const isVisible = panel.style.visibility === 'visible' || 
                               panel.style.display === 'block';
              
              if (isVisible) {
                // Add entrance animation
                panel.style.animation = `fadeIn ${this.config.animationDurations.fadeIn}ms ease-out`;
                
                // Set up tag hover effects in the panel
                if (this.config.visualOptions.enableTagHover) {
                  this.setupTagHoverEffects(panel);
                }
              }
            }
          });
        });
        
        // Start observing details panel
        const detailsPanel = document.querySelector(this.config.selectors.detailsPanel);
        if (detailsPanel) {
          observer.observe(detailsPanel, { attributes: true });
        }
      }
    },
    
    /**
     * Add hover effects to tags/pills
     */
    setupTagHoverEffects: function(container = document) {
      const tags = container.querySelectorAll(this.config.selectors.tagClass);
      
      tags.forEach(tag => {
        tag.style.transition = 'transform 0.15s ease, box-shadow 0.15s ease';
        
        tag.addEventListener('mouseover', () => {
          tag.style.transform = 'translateY(-1px)';
          tag.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
        });
        
        tag.addEventListener('mouseout', () => {
          tag.style.transform = 'translateY(0)';
          tag.style.boxShadow = '0 1px 2px rgba(0,0,0,0.05)';
        });
      });
    },
    
    /**
     * Set up responsive behaviors
     */
    setupResponsiveBehavior: function() {
      // Update text size based on viewport width
      if (this.config.visualOptions.responsiveTextSize) {
        this.updateResponsiveText();
        window.addEventListener('resize', this.debounce(() => {
          this.updateResponsiveText();
        }, 150));
      }
    },
    
    /**
     * Update text sizes responsively
     */
    updateResponsiveText: function() {
      const width = window.innerWidth;
      
      // Define multipliers for different screen sizes
      let fontMultiplier = 1;
      let spacingMultiplier = 1;
      
      if (width < 480) {
        fontMultiplier = 0.85;
        spacingMultiplier = 0.85;
      } else if (width < 768) {
        fontMultiplier = 0.9;
        spacingMultiplier = 0.9;
      } else if (width < 1024) {
        fontMultiplier = 0.95;
        spacingMultiplier = 0.95;
      }
      
      // Apply multipliers to CSS variables
      document.documentElement.style.setProperty('--font-multiplier', fontMultiplier);
      document.documentElement.style.setProperty('--spacing-multiplier', spacingMultiplier);
    },
    
    /**
     * Add accessibility improvements
     */
    setupAccessibilityImprovements: function() {
      // Add better keyboard navigation
      document.addEventListener('keydown', (e) => {
        // Handle ESC key for closing details panel
        if (e.key === 'Escape') {
          const closeButton = document.querySelector('#close-details-button');
          if (closeButton) {
            closeButton.click();
          }
        }
        
        // Handle arrow keys for navigating through table rows
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          const table = document.querySelector(this.config.selectors.table);
          if (table && document.activeElement.tagName !== 'INPUT') {
            e.preventDefault();
            
            const rows = Array.from(table.querySelectorAll('tr:not(.dash-header-row)'));
            const currentRow = document.querySelector(`.${this.config.selectors.highlightedRow}`);
            let index = currentRow ? rows.indexOf(currentRow) : -1;
            
            if (e.key === 'ArrowDown') {
              index = Math.min(index + 1, rows.length - 1);
            } else {
              index = Math.max(index - 1, 0);
            }
            
            if (index >= 0) {
              this.highlightRow(rows[index]);
              
              // Simulate click on details button
              const detailsButton = rows[index].querySelector(this.config.selectors.detailsButton);
              if (detailsButton) {
                detailsButton.click();
              }
            }
          }
        }
      });
    },
    
    /**
     * Set up mutation observer to handle dynamic content
     */
    setupMutationObserver: function() {
      // Create a mutation observer to watch for dynamically added content
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.addedNodes.length) {
            mutation.addedNodes.forEach((node) => {
              // If the table is added to the DOM
              if (node.nodeType === 1 && 
                  node.matches && 
                  (node.matches(this.config.selectors.table) || 
                   node.querySelector(this.config.selectors.table))) {
                
                // Set up interactions for the newly added table
                if (this.config.visualOptions.enableTagHover) {
                  this.setupTagHoverEffects(node);
                }
              }
            });
          }
        });
      });
      
      // Start observing the document with the configured parameters
      observer.observe(document.body, { childList: true, subtree: true });
    },
    
    /**
     * Simple debounce function for rate-limiting event handlers
     */
    debounce: function(func, wait) {
      let timeout;
      return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          func.apply(context, args);
        }, wait);
      };
    }
  };
  
  // Initialize the enhancer
  CianDashboardEnhancer.initialize();
})();