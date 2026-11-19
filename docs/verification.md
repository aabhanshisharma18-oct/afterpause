# Afterpause verification

The first release supports the complete creator and contributor loop in the three module guides. The development SQLite mode is convenient for local setup; MySQL 8.4 is the acceptance database.

| Check | Evidence |
| --- | --- |
| Creator → contributor → approval | Integration suite registers separate accounts, saves and reopens a draft, publishes, proposes, accepts, submits and approves. A fresh Flask instance serves both credits and the uploaded image. |
| Permissions | Tests reject owner impersonation, self requests, contributor approval, unauthorised administration, public access to private media and direct access to drafts and hidden exhibits. |
| Transactions | A simulated failure after flush leaves the request, active slot, exhibit and timeline unchanged. Two concurrent MySQL acceptances yield one redirect, one conflict, and one continuation. |
| Moderation and recovery | A report is recorded, the administrator hides and restores public visibility, and approved work remains available. The backup and restore commands restore a separate MySQL database and its media directory. |
| Discovery | Browser checks cover shared filters, in-place updates, Back and Forward, full-page fallback, pagination, missing media, keyboard focus, comparison and narrow layouts. |
| Demo setup | Two seed runs on a fresh database leave one private BorrowBox draft. The browser walkthrough covers publishing, proposal revision, screenshot preview, approval, and hide and unhide. |

## Screenshots

All screenshots use labelled sample records.

- [Museum entrance](screenshots/entrance.jpg)
- [Filtered collection](screenshots/collection.jpg)
- [Mobile exhibit](screenshots/mobile-exhibit.jpg)
- [Approved timeline](screenshots/timeline.jpg)

## Known limitations

Afterpause accepts image uploads and external links. It does not execute project code, validate external commits, or send email. Local credential limits use process memory; production requires shared storage. Account recovery, multi-contributor work, live chat, and OAuth are deferred. The browser check is not a substitute for a classroom usability session with actual participants.

## Presentation demo update (20 November 2026)

Browser verification on Chrome exercised: homepage navigation → demo entry →
populated dashboard → accept Campus Guide proposal → switch to contributor →
upload screenshot progress → switch to creator → approve → public resurrection
log → flower → guest-book note → publish BorrowBox draft. Search/cause filters,
Back navigation, collection, statistics, gift shop, and the 390 px mobile layout
also passed. A separate account was registered, signed out, and signed back in to
verify the standard password-based flow. No browser JavaScript errors occurred.

Regression tests cover demo CSRF, disabling entry, two-browser workspace and media
isolation, member-only roles, bundled fixtures, duplicate flower prevention,
comment escaping and removal permissions, date validation, visibility of metadata,
and public-IP pinning/private-network rejection for demo-link checks.
