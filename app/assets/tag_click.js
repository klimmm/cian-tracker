// tag_click.js - Optimized
(function() {
  function updateHeaderFontSize() {
    document.querySelectorAll('th[data-dash-column] .column-header-name').forEach(el => {
      el.style.fontSize = window.innerWidth < 480 ? '11px' : window.innerWidth < 768 ? '12px' : '13px';
    });
  }
  window.addEventListener('resize', updateHeaderFontSize);
  window.addEventListener('load', updateHeaderFontSize);
  setTimeout(updateHeaderFontSize, 200);
})();