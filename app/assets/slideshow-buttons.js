// assets/slideshow.js
window.dash_clientside = Object.assign({}, window.dash_clientside, {
  // namespace “slideshow”
  slideshow: {
    // function “nav”
    nav: function(prev_clicks, next_clicks, slideshow_data) {
      console.log('Slideshow callback triggered with:', { prev_clicks, next_clicks, slideshow_data });

      if (!slideshow_data || !slideshow_data.image_paths || slideshow_data.image_paths.length === 0) {
        return [slideshow_data, "", ""];
      }

      let currentIndex = slideshow_data.current_index || 0;
      const imagePaths = slideshow_data.image_paths;
      const totalImages = imagePaths.length;

      const ctx = dash_clientside.callback_context;
      if (!ctx.triggered.length) {
        return [slideshow_data, imagePaths[currentIndex], `${currentIndex + 1}/${totalImages}`];
      }

      const triggerId = ctx.triggered[0].prop_id;
      let offerId = 'unknown';
      try {
        const jsonMatch = triggerId.match(/\{.*?\}/);
        if (jsonMatch) {
          const jsonPart = JSON.parse(jsonMatch[0]);
          if (jsonPart && jsonPart.offer_id) offerId = jsonPart.offer_id;
        }
      } catch (e) {
        console.error('Error parsing offer ID:', e);
      }

      // maintain per-offer state
      const stateKey = `slideshow_${offerId}`;
      if (window[stateKey] === undefined) {
        window[stateKey] = { prevClicks: 0, nextClicks: 0 };
      }

      console.log('Before:', window[stateKey], 'received:', { prev_clicks, next_clicks });
      let didChange = false;

      if (prev_clicks > window[stateKey].prevClicks) {
        currentIndex = (currentIndex - 1 + totalImages) % totalImages;
        window[stateKey].prevClicks = prev_clicks;
        didChange = true;
      } else if (next_clicks > window[stateKey].nextClicks) {
        currentIndex = (currentIndex + 1) % totalImages;
        window[stateKey].nextClicks = next_clicks;
        didChange = true;
      }

      console.log('After:', currentIndex, didChange);
      return [
        { current_index: currentIndex, image_paths: imagePaths },
        imagePaths[currentIndex],
        `${currentIndex + 1}/${totalImages}`
      ];
    }
  }
});
