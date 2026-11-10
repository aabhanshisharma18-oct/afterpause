// Each button shows only cards matching its category.
const filterGroup = document.querySelector('.project-filters');
const filterButtons = document.querySelectorAll('[data-filter]');
const projectCards = document.querySelectorAll('.project-card');
const resultCount = document.querySelector('.result-count');

filterButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const category = button.dataset.filter;
    let visibleCount = 0;

    filterButtons.forEach((filterButton) => {
      filterButton.setAttribute('aria-pressed', String(filterButton === button));
    });

    projectCards.forEach((card) => {
      const categories = card.dataset.category.split(' ');
      const matches = category === 'all' || categories.includes(category);
      card.hidden = !matches;
      if (matches) visibleCount += 1;
    });

    resultCount.textContent = `${visibleCount} ${visibleCount === 1 ? 'project' : 'projects'}`;
  });
});

// Without JavaScript, all projects and their expandable details remain available.
filterGroup.hidden = false;

// Switch between the original concept and its proposed next chapter.
const chapterControls = document.querySelector('.comparison-controls');
const chapterButtons = document.querySelectorAll('[data-chapter]');
const chapters = document.querySelectorAll('.chapter');

function showChapter(chapterName) {
  chapterButtons.forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.chapter === chapterName));
  });
  chapters.forEach((chapter) => {
    chapter.hidden = chapter.id !== `chapter-${chapterName}`;
  });
}

chapterButtons.forEach((button) => {
  button.addEventListener('click', () => showChapter(button.dataset.chapter));
});

// Without JavaScript, both examples stay visible.
showChapter('original');
chapterControls.hidden = false;

// These actions explain preview availability until accounts are introduced.
const accountDialog = document.querySelector('#account-dialog');
document.querySelectorAll('[data-account]').forEach((button) => {
  button.addEventListener('click', () => {
    document.querySelector('#account-title').textContent = button.dataset.account;
    accountDialog.showModal();
  });
});
