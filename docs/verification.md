# Afterpause verification

The first release supports the complete creator and contributor loop in the three module guides. The development SQLite mode is convenient for local setup; MySQL 8.4 is the acceptance database.

| Check | Evidence |
| --- | --- |
| Creator → contributor → approval | Integration suite registers separate accounts, saves and reopens a draft, publishes, proposes, accepts, submits and approves. A fresh Flask instance serves both credits and the uploaded image. |
| Permissions | Tests reject owner impersonation, self requests, contributor approval, unauthorised administration, public access to private media and direct access to drafts and hidden exhibits. |
| Transactions | A simulated failure after flush leaves the request, active slot, exhibit and timeline unchanged. Two concurrent MySQL acceptances yield one redirect, one conflict, and one continuation. |
| Moderation and recovery | A report is recorded, the administrator hides and restores public visibility, and approved work remains available. The backup and restore commands restore a separate MySQL database and its media directory. |
| Discovery | Browser checks cover shared filters, pagination, missing media, keyboard focus, comparison and narrow layouts. |

## Screenshots

All screenshots use labelled sample records.

- [Museum entrance](screenshots/entrance.jpg)
- [Filtered collection](screenshots/collection.jpg)
- [Mobile exhibit](screenshots/mobile-exhibit.jpg)
- [Approved timeline](screenshots/timeline.jpg)

## Known limitations

Afterpause accepts image uploads and external links. It does not execute project code, validate external commits, or send email. Local credential limits use process memory; production requires shared storage. Account recovery, multi-contributor work, live chat, and OAuth are deferred. The browser check is not a substitute for a classroom usability session with actual participants.
