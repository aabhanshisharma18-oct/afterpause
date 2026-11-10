// Reading, navigation and forms work without JavaScript. Replace failed images
// with the same label used by exhibits that have no preview.
for (const image of document.querySelectorAll('[data-fallback]')) {
  const showFallback = () => {
    image.hidden = true;
    const frame = image.closest('.picture');
    frame.classList.add('is-empty');
    frame.querySelector('.picture-fallback').hidden = false;
  };
  image.addEventListener('error', showFallback, { once: true });
  if (image.complete && !image.naturalWidth) showFallback();
}

for (const comparison of document.querySelectorAll('[data-comparison]')) {
  const tablist = comparison.querySelector('[role=tablist]');
  const tabs = [...tablist.querySelectorAll('[role=tab]')];
  function selectTab(index) {
    tabs.forEach((tab, position) => {
      const active = position === index;
      const panel = document.getElementById(tab.getAttribute('aria-controls'));
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', tab.id);
      panel.tabIndex = 0;
      panel.hidden = !active;
    });
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(index));
    tab.addEventListener('keydown', (event) => {
      const directions = { ArrowLeft: (index + tabs.length - 1) % tabs.length,
        ArrowRight: (index + 1) % tabs.length, Home: 0, End: tabs.length - 1 };
      if (!Object.hasOwn(directions, event.key)) return;
      event.preventDefault();
      selectTab(directions[event.key]);
      tabs[directions[event.key]].focus();
    });
  });
  selectTab(0);
  tablist.hidden = false;
}

const copyButton = document.querySelector('[data-copy-link]');
if (copyButton && navigator.clipboard) {
  copyButton.hidden = false;
  copyButton.addEventListener('click', async () => {
    const field = document.getElementById('share-link');
    const status = document.querySelector('[data-copy-status]');
    try {
      await navigator.clipboard.writeText(field.value);
      status.textContent = 'Exhibit link copied.';
    } catch {
      field.select();
      status.textContent = 'Link selected. Use your keyboard to copy it.';
    }
  });
}
