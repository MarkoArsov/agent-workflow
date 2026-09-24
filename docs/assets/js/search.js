(() => {
  const dialog = document.querySelector('[data-search-dialog]');
  const input = document.querySelector('[data-search-input]');
  const results = document.querySelector('[data-search-results]');
  const status = document.querySelector('[data-search-status]');
  if (!dialog || !input || !results || !status) return;
  let opener = null;
  let index = null;
  let active = -1;
  const root = new URL(document.querySelector('meta[name="site-root"]')?.content || '/', document.baseURI);
  const focusable = () => [...dialog.querySelectorAll('a, button, input, [tabindex]:not([tabindex="-1"])')].filter((item) => !item.hasAttribute('disabled'));
  const open = (trigger) => { opener = trigger || document.activeElement; dialog.hidden = false; document.body.style.overflow = 'hidden'; input.focus(); };
  const close = () => { dialog.hidden = true; document.body.style.overflow = ''; if (opener && opener.focus) opener.focus(); };
  document.querySelectorAll('[data-search-open]').forEach((button) => button.addEventListener('click', () => open(button)));
  dialog.querySelectorAll('[data-search-close]').forEach((button) => button.addEventListener('click', close));
  document.addEventListener('keydown', (event) => {
    const inField = /input|textarea|select/i.test(document.activeElement?.tagName || '');
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); open(document.activeElement); }
    if (!dialog.hidden && event.key === 'Escape') { event.preventDefault(); close(); }
    if (!inField && dialog.hidden && (event.key === '/' || event.key.toLowerCase() === 's')) { event.preventDefault(); open(document.activeElement); }
  });
  const load = async () => {
    if (index) return index;
    status.textContent = 'Loading search index…';
    const response = await fetch(new URL('search/search_index.json', root));
    index = (await response.json()).docs || [];
    return index;
  };
  const escape = (value) => value.replace(/[&<>\"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[character]);
  const highlight = (value, query) => escape(value).replace(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'ig'), '<mark>$1</mark>');
  const render = async () => {
    const query = input.value.trim();
    results.innerHTML = ''; active = -1;
    if (query.length < 2) { status.textContent = 'Type at least two characters to search the documentation.'; return; }
    try {
      const docs = await load();
      const matches = docs.filter((doc) => `${doc.title} ${doc.text}`.toLowerCase().includes(query.toLowerCase())).slice(0, 8);
      if (!matches.length) { status.textContent = 'No results found.'; return; }
      status.textContent = `${matches.length} result${matches.length === 1 ? '' : 's'}.`;
      results.innerHTML = matches.map((doc, position) => {
        const text = doc.text.replace(/\s+/g, ' ');
        const found = text.toLowerCase().indexOf(query.toLowerCase());
        const snippet = text.slice(Math.max(0, found - 64), found + query.length + 116);
        return `<li><a class="search-result" data-search-result href="${escape(new URL(doc.location, root).href)}" data-index="${position}"><span>${highlight(doc.title, query)}</span><small>${highlight(snippet, query)}…</small></a></li>`;
      }).join('');
    } catch (_) { status.textContent = 'Search is unavailable right now.'; }
  };
  input.addEventListener('input', render);
  input.addEventListener('keydown', (event) => {
    const links = [...results.querySelectorAll('[data-search-result]')];
    if (!links.length) return;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); active = (active + (event.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length; links[active].focus(); }
    if (event.key === 'Enter' && active >= 0) links[active].click();
  });
  results.addEventListener('keydown', (event) => {
    const links = [...results.querySelectorAll('[data-search-result]')];
    const position = links.indexOf(document.activeElement);
    if (position < 0) return;
    if (event.key === 'ArrowDown') { event.preventDefault(); links[(position + 1) % links.length]?.focus(); }
    if (event.key === 'ArrowUp') { event.preventDefault(); (position ? links[position - 1] : input).focus(); }
  });
  dialog.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab') return;
    const items = focusable();
    if (!items.length) return;
    const first = items[0], last = items.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
})();
