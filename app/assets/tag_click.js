(function() {
    function updateHeaderFontSize() {
        let size = window.innerWidth < 480 ? '11px'
                 : window.innerWidth < 768 ? '12px'
                 : '13px';
        document.querySelectorAll('th[data-dash-column] .column-header-name').forEach(el => {
            el.style.fontSize = size;
        });
    }
    window.addEventListener('resize', updateHeaderFontSize);
    window.addEventListener('load', updateHeaderFontSize);
    setTimeout(updateHeaderFontSize, 200);
})();