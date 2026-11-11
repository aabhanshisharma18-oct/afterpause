# D1 Accounts and exhibit publishing

D1 owns the Flask application factory, authentication, the exhibit write path, uploads and the migration chain. See [setup](../README.md) for environment configuration.

| Contract | Behavior |
| --- | --- |
| Identity | `g.user` is a server-loaded user with a stable ID, display name and role. Only the user sees their own email in the app. |
| Auth | `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/account`, `/auth/profile`. Passwords use Werkzeug's scrypt hash. Forms use CSRF protection. Credential checks are rate limited by source IP. |
| Exhibit identity | `id` is stable from draft creation; a public slug is frozen after first publication. `owner_id` controls all write and preview access. |
| Visibility | `publication_state`: draft, published, hidden. `review_state`: clear or flagged. `moderation_hidden` independently gates public visibility. `continuation_state` belongs to D3. |
| Media | Private directory, 4 MB and 20 megapixel limits, actual PNG/JPEG/WebP decode and WebP re-encode, descriptive alt text, random storage keys. `/media/<key>` checks the parent exhibit or update before serving. |

Start a draft from the dashboard. The three steps save the idea, current work and invitation independently. Return to a saved draft, preview it, and publish once the required fields, material confirmation and cover are present. Additional images can be appended, up to four in total. The pause reason and explanation are optional. Uploaded files must be reselected after a validation error; browsers do not restore file inputs.

In an unpublished draft, **Save draft and exit** accepts an incomplete section.
Entered values still pass length, option, link, and image validation. The
**Save and continue** action requires the current section's required fields.
Published and archived exhibits retain their full edit validation.

**My exhibits** shows how many of the three sections are ready to publish and
the last saved date. **Reopen draft** opens the first unfinished section. The
preview links to incomplete sections and enables publication once the idea,
current work with a cover, and invitation with permissions are ready. Readiness
is derived from the saved exhibit and also applies to existing drafts.

Archive hides the public exhibit and its public media. The creator can reopen and republish it unless an administrator has separately restricted it. The first chapter and approved contributions are retained. Edits to a published exhibit appear immediately; its original timeline entry remains a snapshot.

The integration suite tests registration, permissions, draft URL and media isolation, invalid uploads, CSRF, repeated submissions, archive and republish. To hand off an example, run the demo seed and open Campus Guide or Private demo draft as the demo creator.

Registration requires a display name of 2 to 70 characters, a password of 12 to
128 characters, and matching password confirmation. Existing accounts with
shorter passwords can still sign in. Email lookup accepts older mixed-case
records, and duplicate registrations preserve the entered text if another
request claims the address first. Password fields are cleared on errors.

After signing in, the dashboard remains the starting point for creator and
contributor workflows. **My account** in the header opens the private account
page, with a link to edit the profile. Sign-out requires a signed-in session
and a CSRF-protected POST.

Login attempts are limited to 5 per minute and 30 per hour per source IP;
registration has a separate limit of 5 per hour. Production requires shared
rate-limit storage through `RATELIMIT_STORAGE_URI`, while local development uses
memory. The two Flask entry points share this identity, schema, and session setup.
