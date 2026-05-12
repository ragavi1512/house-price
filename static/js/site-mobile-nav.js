(function () {
  'use strict';

  var mqApp = window.matchMedia('(max-width: 1100px)');

  function closeAppNav() {
    document.querySelectorAll('.layout.nav-open').forEach(function (layout) {
      layout.classList.remove('nav-open');
    });
    document.querySelectorAll('.nav-toggle').forEach(function (btn) {
      btn.setAttribute('aria-expanded', 'false');
      btn.setAttribute('aria-label', 'Open menu');
    });
    document.body.classList.remove('nav-drawer-open');
  }

  function toggleAppNav(button) {
    var layout = button.closest('.layout');
    if (!layout) return;
    var open = layout.classList.toggle('nav-open');
    button.setAttribute('aria-expanded', open ? 'true' : 'false');
    button.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    document.body.classList.toggle('nav-drawer-open', open && mqApp.matches);
  }

  function closeMarketingNav() {
    var h = document.querySelector('header.marketing-header');
    if (!h) return;
    h.classList.remove('nav-open');
    var b = h.querySelector('.marketing-nav-toggle');
    if (b) {
      b.setAttribute('aria-expanded', 'false');
      b.setAttribute('aria-label', 'Open menu');
    }
  }

  mqApp.addEventListener('change', function (e) {
    if (!e.matches) closeAppNav();
  });

  window.matchMedia('(max-width: 720px)').addEventListener('change', function (e) {
    if (!e.matches) closeMarketingNav();
  });

  document.addEventListener('click', function (e) {
    var el = e.target;
    if (el.closest && el.closest('.marketing-nav-toggle')) {
      e.preventDefault();
      var header = document.querySelector('header.marketing-header');
      if (!header) return;
      var next = !header.classList.contains('nav-open');
      header.classList.toggle('nav-open', next);
      var btn = header.querySelector('.marketing-nav-toggle');
      if (btn) {
        btn.setAttribute('aria-expanded', next ? 'true' : 'false');
        btn.setAttribute('aria-label', next ? 'Close menu' : 'Open menu');
      }
      return;
    }
    if (el.closest && el.closest('.nav-toggle')) {
      e.preventDefault();
      toggleAppNav(el.closest('.nav-toggle'));
      return;
    }
    if (el.classList && el.classList.contains('js-nav-backdrop')) {
      closeAppNav();
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      closeAppNav();
      closeMarketingNav();
    }
  });

  document.querySelectorAll('.layout .sidebar a.nav-item').forEach(function (a) {
    a.addEventListener('click', function () {
      if (mqApp.matches) closeAppNav();
    });
  });
})();
