document.addEventListener('DOMContentLoaded', function () {
  // Apply fade-in to elements with the fade-in class
  const fadeElements = document.querySelectorAll('.fade-in');
  fadeElements.forEach((el) => {
    el.style.opacity = '0';
    setTimeout(() => {
      el.style.opacity = '1';
    }, 100);
  });

  // Handle link clicks for fade-out transition
  const links = document.querySelectorAll(
    'a:not([href^="#"]), a[href^="https"]',
  );

  links.forEach((link) => {
    if (link.href && !link.href.includes('javascript') && link.href !== '#') {
      link.addEventListener('click', function (e) {
        // Don't intercept anchor links or links that open in new tab
        if (this.target === '_blank' || this.getAttribute('download')) {
          return;
        }

        e.preventDefault();
        const href = this.href;

        // Apply fade-out to the entire page
        document.body.classList.add('fade-out');

        // Wait for animation to complete before navigating
        setTimeout(() => {
          window.location.href = href;
        }, 500);
      });
    }
  });

  // Special handling for browser back/forward buttons
  window.addEventListener('pageshow', function (event) {
    // If page is loaded from cache, trigger fade-in again
    if (event.persisted) {
      document.body.classList.remove('fade-out');
      const fadeElements = document.querySelectorAll('.fade-in');
      fadeElements.forEach((el) => {
        el.style.opacity = '0';
        setTimeout(() => {
          el.style.opacity = '1';
        }, 100);
      });
    }
  });
});
