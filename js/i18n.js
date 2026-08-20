(function () {
  const supportedLocales = ['en', 'nl', 'es', 'fr', 'de'];
  const defaultLocale = 'en';

  function getCurrentLocale() {
    const path = window.location.pathname;
    const match = path.match(/^\/([a-z]{2})\//) || path.match(/^\/([a-z]{2})$/);
    const locale = match ? match[1] : defaultLocale;
    return supportedLocales.includes(locale) ? locale : defaultLocale;
  }

  async function loadLocale(locale) {
    const response = await fetch(`/locales/${locale}.json`, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Missing locale file for ${locale}`);
    }
    return response.json();
  }

  function applyText(node, value) {
    if (!node || value == null) return;
    node.textContent = value;
  }

  async function init() {
    const locale = getCurrentLocale();
    const translations = await loadLocale(locale).catch(() => loadLocale(defaultLocale));

    document.documentElement.lang = locale;

    document.querySelectorAll('[data-i18n]').forEach((node) => {
      const path = node.dataset.i18n.split('.');
      let value = translations;
      for (const key of path) {
        if (value && Object.prototype.hasOwnProperty.call(value, key)) {
          value = value[key];
        } else {
          value = null;
          break;
        }
      }
      applyText(node, value);
    });

    document.querySelectorAll('[data-i18n-attr]').forEach((node) => {
      const parts = node.dataset.i18nAttr.split(':');
      const key = parts[0];
      const attr = parts[1];
      const value = key.split('.').reduce((obj, part) => obj && obj[part], translations);
      if (value != null) {
        node.setAttribute(attr, value);
      }
    });
  }

  init();
})();
