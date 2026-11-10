# D2 Museum exploration and presentation

D2 owns the public entrance, collection query, shared design and exhibit presentation. The homepage restores the original plum and ivory palette, workspace image, and featured project layout. Its primary actions are Explore projects and Share your project.

`/explore` supports `room`, `q`, `category`, `skill`, `state` and `page` parameters. Room tabs retain current search filters. Search matches titles, intentions, stories and tags, treating SQL wildcards as literal input. Skill filtering matches the creator’s skill list. The database paginates the collection at nine exhibits per page.

`/exhibits/<slug>` only reads published, visible records. It shows the intention, creator credit, story, current work, next step, materials and permissions, and original repository. The timeline queries public event snapshots and orders them by time and ID. Approved contribution links are explicitly user-supplied. No public template uses proposal fields, private review notes or pending screenshots.

Shared pieces live in `app/templates/base.html`, `_components.html`, `_timeline.html` and `app/static/museum.css`. Layout and forms work without JavaScript; JavaScript adds failed-image replacement, comparison tabs, and ticket link copying. Both comparison images remain readable without JavaScript. Small screens use one-column cards and a stacked timeline.

The separate demo seed provides ten labelled exhibits across four rooms. See the [manifest](demo.md) and [verification](verification.md). Signed-in visitors can save public exhibits; public tickets expose only a public title, link, exhibit number and credit.
