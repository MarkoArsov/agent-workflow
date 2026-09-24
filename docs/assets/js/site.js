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

  document.querySelectorAll('.prose h2, .prose h3').forEach((heading) => {
    if (!heading.id || heading.querySelector('.heading-anchor')) return;
    const link = document.createElement('a');
    link.className = 'heading-anchor';
    link.href = `#${heading.id}`;
    link.setAttribute('aria-label', `Link to ${heading.textContent}`);
    link.textContent = '#';
    heading.prepend(link);
  });

  document.querySelectorAll('.prose pre').forEach((block) => {
    const button = document.createElement('button');
    button.className = 'copy-code';
    button.type = 'button';
    button.textContent = 'Copy';
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(block.querySelector('code')?.textContent || block.textContent || '');
        button.textContent = 'Copied'; button.classList.add('is-copied');
        window.setTimeout(() => { button.textContent = 'Copy'; button.classList.remove('is-copied'); }, 1500);
      } catch (_) { button.textContent = 'Copy failed'; }
    });
    block.append(button);
  });

  document.querySelectorAll('.prose table').forEach((table) => {
    if (table.parentElement?.classList.contains('table-wrap')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'table-wrap';
    table.before(wrapper); wrapper.append(table);
  });

  const tocLinks = [...document.querySelectorAll('[data-page-toc] a')];
  const headingById = tocLinks.map((link) => document.getElementById(link.getAttribute('href')?.slice(1))).filter(Boolean);
  if (headingById.length) {
    const activate = (id) => tocLinks.forEach((link) => link.classList.toggle('is-active', link.getAttribute('href') === `#${id}`));
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (visible) activate(visible.target.id);
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) activate(headingById.at(-1).id);
    }, { rootMargin: '-25% 0px -65% 0px' });
    headingById.forEach((heading) => observer.observe(heading));
  }

  const drawer = document.querySelector('[data-drawer]');
  const drawerOpener = document.querySelector('[data-drawer-open]');
  const drawerClosers = drawer?.querySelectorAll('[data-drawer-close]') || [];
  let previousFocus = null;
  const closeDrawer = () => {
    if (!drawer || drawer.hidden) return;
    drawer.classList.remove('is-open'); drawer.hidden = true; document.body.style.overflow = '';
    drawerOpener?.setAttribute('aria-expanded', 'false'); previousFocus?.focus?.();
  };
  const openDrawer = () => {
    if (!drawer) return;
    previousFocus = document.activeElement; drawer.hidden = false; document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => drawer.classList.add('is-open'));
    drawerOpener?.setAttribute('aria-expanded', 'true'); drawer.querySelector('button, a')?.focus();
  };
  drawerOpener?.addEventListener('click', openDrawer);
  drawerClosers.forEach((button) => button.addEventListener('click', closeDrawer));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && drawer && !drawer.hidden) { event.preventDefault(); closeDrawer(); }
    if (event.key !== 'Tab' || !drawer || drawer.hidden) return;
    const focusable = [...drawer.querySelectorAll('a, button, input, [tabindex]:not([tabindex="-1"])')].filter((item) => !item.hasAttribute('disabled'));
    if (!focusable.length) return;
    const first = focusable[0], last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
})();
