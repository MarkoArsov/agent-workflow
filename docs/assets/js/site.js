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

  const menus = [...document.querySelectorAll('[data-menu]')];
  const closeMenus = (except = null) => menus.forEach((menu) => {
    if (menu === except) return;
    menu.classList.remove('is-open');
    const toggle = menu.querySelector('[data-menu-toggle]');
    const panel = menu.querySelector('[data-menu-panel]');
    toggle?.setAttribute('aria-expanded', 'false'); panel?.setAttribute('aria-hidden', 'true');
    panel?.querySelectorAll('a').forEach((link) => link.tabIndex = -1);
  });
  const openMenu = (menu, focusFirst = false) => {
    closeMenus(menu); menu.classList.add('is-open');
    const toggle = menu.querySelector('[data-menu-toggle]');
    const panel = menu.querySelector('[data-menu-panel]');
    toggle?.setAttribute('aria-expanded', 'true'); panel?.setAttribute('aria-hidden', 'false');
    const links = [...(panel?.querySelectorAll('a') || [])];
    links.forEach((link) => link.tabIndex = 0);
    if (focusFirst) links[0]?.focus();
  };
  menus.forEach((menu) => {
    const toggle = menu.querySelector('[data-menu-toggle]');
    const panel = menu.querySelector('[data-menu-panel]');
    let openTimer = null;
    let closeTimer = null;
    toggle?.addEventListener('click', () => menu.classList.contains('is-open') ? closeMenus() : openMenu(menu));
    toggle?.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openMenu(menu, true); }
    });
    panel?.addEventListener('keydown', (event) => {
      const links = [...panel.querySelectorAll('a')];
      const index = links.indexOf(document.activeElement);
      if (event.key === 'Escape') { event.preventDefault(); closeMenus(); toggle?.focus(); }
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); links[(index + (event.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length]?.focus(); }
      if (event.key === 'Home') { event.preventDefault(); links[0]?.focus(); }
      if (event.key === 'End') { event.preventDefault(); links.at(-1)?.focus(); }
    });
    menu.addEventListener('pointerenter', () => {
      if (!matchMedia('(hover: hover) and (pointer: fine)').matches) return;
      clearTimeout(closeTimer);
      openTimer = window.setTimeout(() => openMenu(menu), 160);
    });
    menu.addEventListener('pointerleave', () => {
      if (!matchMedia('(hover: hover) and (pointer: fine)').matches) return;
      clearTimeout(openTimer);
      closeTimer = window.setTimeout(() => closeMenus(), 100);
    });
  });
  document.addEventListener('pointerdown', (event) => { if (!event.target.closest('[data-menu]')) closeMenus(); });
  document.addEventListener('focusin', (event) => { if (!event.target.closest('[data-menu]')) closeMenus(); });

  document.querySelectorAll('.prose h2, .prose h3').forEach((heading) => {
    if (!heading.id || heading.querySelector('.heading-anchor')) return;
    const link = document.createElement('a');
    link.className = 'heading-anchor';
    link.href = `#${heading.id}`;
    link.setAttribute('aria-label', `Link to ${heading.textContent}`);
    link.textContent = '#';
    heading.prepend(link);
  });

  document.querySelectorAll('.prose pre, .install-command pre, .code-card pre, .tree-card pre').forEach((block) => {
    const button = document.createElement('button');
    button.className = 'copy-code';
    button.type = 'button';
    button.textContent = 'Copy';
    button.setAttribute('aria-live', 'polite');
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

  const skillsFilter = document.querySelector('[data-skills-filter]');
  const skillsInput = skillsFilter?.querySelector('[data-skills-filter-input]');
  if (skillsFilter && skillsInput) {
    const entries = [...document.querySelectorAll('.prose h3.skill-entry')].map((heading) => {
      const nodes = [heading];
      let sibling = heading.nextElementSibling;
      while (sibling && !sibling.matches('h2, h3')) { nodes.push(sibling); sibling = sibling.nextElementSibling; }
      let category = heading.previousElementSibling;
      while (category && !category.matches('h2')) category = category.previousElementSibling;
      return { heading, nodes, category, text: heading.dataset.skill || heading.textContent || '' };
    });
    const chips = [...skillsFilter.querySelectorAll('[data-skills-chip]')];
    const empty = skillsFilter.querySelector('[data-skills-empty]');
    const update = () => {
      const query = skillsInput.value.trim().toLowerCase();
      let visible = 0;
      entries.forEach((entry) => {
        const matches = !query || entry.text.toLowerCase().includes(query);
        entry.nodes.forEach((node) => { node.hidden = !matches; });
        if (matches) visible += 1;
      });
      chips.forEach((chip) => { chip.hidden = Boolean(query) && !chip.dataset.skillChipName.includes(query); });
      [...new Set(entries.map((entry) => entry.category).filter(Boolean))].forEach((category) => {
        category.hidden = !entries.some((entry) => entry.category === category && !entry.heading.hidden);
      });
      if (empty) empty.hidden = visible !== 0;
    };
    skillsInput.addEventListener('input', update);
  }

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
