(() => {
  const header = document.querySelector('[data-site-header]');
  if (header) {
    const sentinel = document.createElement('div');
    sentinel.setAttribute('aria-hidden', 'true');
    header.before(sentinel);
    new IntersectionObserver(([entry]) => header.classList.toggle('is-scrolled', !entry.isIntersecting)).observe(sentinel);
  }
  const keyHint = document.querySelector('[data-key-hint]');
  if (keyHint && !navigator.platform.includes('Mac')) keyHint.textContent = 'Ctrl K';
})();
