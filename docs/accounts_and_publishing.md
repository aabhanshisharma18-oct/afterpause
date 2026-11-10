# D1 Accounts and exhibit publishing

D1 owns the Flask application factory, authentication, the exhibit write path, uploads and the migration chain. See [setup](../README.md) for environment configuration.

| Contract | Behavior |
| --- | --- |
| Identity | `g.user` is a server-loaded user with a stable ID, display name and role. Only the user sees their own email in the app. |
| Auth | `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/profile`. Passwords use Werkzeug's scrypt hash. Forms use CSRF protection. Credential checks are rate limited by source IP. |
| Exhibit identity | `id` is stable from draft creation; a public slug is frozen after first publication. `owner_id` controls all write and preview access. |
| Visibility | `publication_state`: draft, published, hidden. `review_state`: clear or flagged. `moderation_hidden` independently gates public visibility. `continuation_state` belongs to D3. |
| Media | Private directory, 4 MB and 20 megapixel limits, actual PNG/JPEG/WebP decode and WebP re-encode, descriptive alt text, random storage keys. `/media/<key>` checks the parent exhibit or update before serving. |

Start a draft from the dashboard. The three steps save the idea, current work and invitation independently. Return to a saved draft, preview it, and publish once the required fields, material confirmation and cover are present. Additional images can be appended, up to four in total. The pause reason and explanation are optional. Uploaded files must be reselected after a validation error; browsers do not restore file inputs.

Archive hides the public exhibit and its public media. The creator can reopen and republish it unless an administrator has separately restricted it. The first chapter and approved contributions are retained. Edits to a published exhibit appear immediately; its original timeline entry remains a snapshot.

The integration suite tests registration, permissions, draft URL and media isolation, invalid uploads, CSRF, repeated submissions, archive and republish. To hand off an example, run the demo seed and open Campus Guide or Private demo draft as the demo creator.
