(function() {
  function getActiveLanguage() {
    return localStorage.getItem('soundwave_idioma') || 'es';
  }

  function translateDOM() {
    const lang = getActiveLanguage();
    const dictionary = soundwaveTranslations[lang];
    if (!dictionary) return;

    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (dictionary[key]) {
        el.innerHTML = dictionary[key];
      }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (dictionary[key]) {
        el.setAttribute('placeholder', dictionary[key]);
      }
    });

    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      if (dictionary[key]) {
        el.setAttribute('title', dictionary[key]);
      }
    });

    document.querySelectorAll('.lang-select-option-item').forEach(el => {
      const elLang = el.getAttribute('data-lang');
      if (elLang === lang) {
        el.classList.add('active-lang');
      } else {
        el.classList.remove('active-lang');
      }
    });
  }

  window.changeLanguage = function(langCode) {
    if (soundwaveTranslations[langCode]) {
      localStorage.setItem('soundwave_idioma', langCode);
      translateDOM();
    }
  };

  document.addEventListener('DOMContentLoaded', translateDOM);
  window.addEventListener('load', translateDOM);
})();
