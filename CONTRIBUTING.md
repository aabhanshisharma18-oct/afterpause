# Contributing to Afterpause

Use a small issue or pull request with one outcome a reviewer can verify. Start from an up-to-date `main`, work on a feature branch, and include the behavior change, relevant tests, and screenshots for visible changes. Ask the owner of an adjacent module to review any shared contract change.

| Module | Areas | Review partner |
| --- | --- | --- |
| D1 Accounts and publishing | `app/auth`, `app/exhibits`, config, media, migrations | D3 for permissions and transactions |
| D2 Exploration and presentation | `app/museum`, shared templates and CSS, demo content | D1 for publishing and visibility |
| D3 Continuations and moderation | `app/continuations`, `app/admin`, lifecycle and moderation tests | D2 for public timeline and attribution |

Run the SQLite and disposable MySQL checks in the [README](README.md) before submitting a change to permissions or state. D1 coordinates a single Alembic migration history; include and review a revision with every schema change. Do not commit real passwords, databases, uploads, or personal details.

The MIT license covers the Afterpause application. Exhibits may have their own terms. Keep original notices, credit the creator and contributor, and use only imagery you can share. Do not describe user-entered repository links as verified GitHub activity.
