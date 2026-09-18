(() => {
  const initializeNavigation = () => {
    const toggle = document.querySelector('.nav-toggle');
    const nav = document.querySelector('#primary-nav');

    if (!toggle || !nav || toggle.dataset.navInitialized === 'true') return;

    toggle.dataset.navInitialized = 'true';

    const closeNavigation = () => {
      nav.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open navigation');
    };

    toggle.addEventListener('click', () => {
      const isOpen = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(isOpen));
      toggle.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
    });

    nav.addEventListener('click', (event) => {
      if (event.target instanceof Element && event.target.closest('a')) {
        closeNavigation();
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeNavigation();
    });

    window.addEventListener('resize', () => {
      if (window.matchMedia('(min-width: 721px)').matches) closeNavigation();
    }, { passive: true });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeNavigation, { once: true });
  } else {
    initializeNavigation();
  }
})();
