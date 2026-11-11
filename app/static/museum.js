// Reading, navigation and forms work without JavaScript. Replace failed images
// with the same label used by exhibits that have no preview.
function bindImageFallbacks(container) {
  for (const image of container.querySelectorAll('[data-fallback]')) {
    const showFallback = () => {
      image.hidden = true;
      const frame = image.closest('.picture');
      frame.classList.add('is-empty');
      frame.querySelector('.picture-fallback').hidden = false;
    };
    image.addEventListener('error', showFallback, { once: true });
    if (image.complete && !image.naturalWidth) showFallback();
  }
}

bindImageFallbacks(document);

const gallery = document.querySelector('[data-gallery]');
if (gallery) {
  const content = gallery.querySelector('[data-gallery-content]');
  const status = gallery.querySelector('[data-gallery-status]');
  let activeRequest;

  async function loadGallery(url, { fromHistory = false, focusResults = true, scrollResults = false } = {}) {
    activeRequest?.abort();
    const controller = new AbortController();
    activeRequest = controller;
    content.setAttribute('aria-busy', 'true');
    status.textContent = 'Loading exhibits…';
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error('Could not load exhibits');
      const html = new DOMParser().parseFromString(await response.text(), 'text/html');
      const incoming = html.querySelector('[data-gallery-content]');
      if (!incoming) throw new Error('Exhibit results missing');
      if (controller.signal.aborted) return;

      content.replaceChildren(...incoming.children);
      bindImageFallbacks(content);
      if (!fromHistory && url.href !== location.href) history.pushState(null, '', url);
      const count = content.querySelector('[data-gallery-count]');
      status.textContent = count.textContent.trim();
      if (focusResults) count.focus({ preventScroll: !scrollResults });
    } catch (error) {
      if (!controller.signal.aborted) {
        if (fromHistory) location.replace(url);
        else location.assign(url);
      }
    } finally {
      if (activeRequest === controller) content.removeAttribute('aria-busy');
    }
  }

  gallery.addEventListener('submit', event => {
    if (!event.target.matches('.filters')) return;
    event.preventDefault();
    const url = new URL(event.target.action);
    url.search = new URLSearchParams(new FormData(event.target)).toString();
    loadGallery(url);
  });

  gallery.addEventListener('click', event => {
    const link = event.target.closest('a[data-gallery-link], [data-gallery-nav] a');
    if (!link || event.defaultPrevented || event.button !== 0 ||
        event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const url = new URL(link.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname) return;
    event.preventDefault();
    loadGallery(url, { scrollResults: Boolean(link.closest('[data-gallery-pages]')) });
  });

  window.addEventListener('popstate', () => {
    loadGallery(new URL(location.href), { fromHistory: true, focusResults: false });
  });
}

for (const input of document.querySelectorAll('[data-upload-limit]')) {
  const preview = input.nextElementSibling;
  const image = preview.querySelector('img');
  const caption = preview.querySelector('figcaption');
  let objectUrl;

  input.addEventListener('change', () => {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = undefined;
    image.removeAttribute('src');
    image.hidden = true;
    input.setCustomValidity('');
    caption.classList.remove('field-error');

    const file = input.files[0];
    preview.hidden = !file;
    caption.textContent = '';
    if (!file) return;

    if (file.size > Number(input.dataset.uploadLimit)) {
      const message = 'Use an image of 4 MB or less.';
      input.setCustomValidity(message);
      caption.textContent = message;
      caption.classList.add('field-error');
      return;
    }

    caption.textContent = 'Selected: ' + file.name;
    if (file.type && !input.accept.split(',').includes(file.type)) return;
    const url = URL.createObjectURL(file);
    objectUrl = url;
    image.src = url;
    image.decode().then(() => {
      if (objectUrl === url) image.hidden = false;
    }).catch(() => {
      if (objectUrl === url) caption.textContent = 'Preview unavailable for ' + file.name;
    });
  });
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
