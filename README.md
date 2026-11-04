# Afterpause

Someone paused. Someone else begins.

A place for unfinished projects and the people who see what they could become.
This college project starts with a plain HTML, CSS, and JavaScript homepage.
No framework, package installation, or build command is needed.

## Homepage features

- Plum and ivory theme with a softly faded workspace background.
- Featured Campus Guide concept and three sample project cards.
- Category filters, visible project counts, and expandable project details.
- An original/new-contribution switch with credit for both contributors.
- Mobile layouts, keyboard controls, a skip link, and reduced-motion support.

All projects are clearly labelled samples. The Campus Guide and Reading Room
screens are generated concept images, not functioning apps. The before/after
search field illustrates a proposed contribution; it does not search books.
Login, project publishing, contribution requests, and database storage are the
next development stages and are not implemented yet.

## Run locally

Open a terminal in this repository folder and run:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Visit http://127.0.0.1:8000. Press Ctrl+C to stop the server.
You can also open `index.html` directly in a browser.

## Files

- `index.html`: homepage sections and sample project content.
- `style.css`: shared colours, layout, hover effects, and mobile styles.
- `script.js`: category filters and chapter switching.
- `images/`: local background, sample project previews, and site icon.

## Change the content

Edit a card in `index.html` to change its title, next step, or details. Its
`data-category` value decides which filters it matches. Shared theme colours
are at the top of `style.css`. The hero's gradient controls the background fade
without changing the opacity of its text.

## Image assets

The four PNG files were made with the built-in image generation tool as
illustrative demo assets. They are stored locally; no external image service
is needed. The SVG favicon is a simple code-drawn site icon.

- `creative-workspace.png`: overhead cream desk with notebook wireframes,
  plum pencil, camera, and cropped laptop; the centre stays empty for copy.
- `campus-guide.png`: campus map UI with a blue route, plum destination,
  location sidebar, and university building preview.
- `reading-room.png`: cream and terracotta book tracker with fictional book
  covers and reading progress.
- `one-more-level.png`: pixel game concept with a plum-cloaked adventurer,
  lavender mountains, and stone platforms.

Replace these sample project images with actual screenshots when real exhibits
are available. Keep attribution and material permissions with future exhibits.
