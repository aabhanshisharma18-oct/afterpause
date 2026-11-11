# Free demo: Render + Supabase

This path keeps MySQL support but adds PostgreSQL and private Supabase media.
Free services have quotas, sleeping/pausing behavior and no production uptime
promise. Keep exports of important data and media. Never put secrets in git.

## Supabase

1. Use the existing Free project and private `afterpause-media` bucket.
   Do not enable public access or add anonymous storage policies.
2. Connect > Direct > Session pooler: copy the URI. Replace the password placeholder
   with your URL-encoded database password. Use `postgresql+psycopg://` and append
   `?sslmode=require`. Session pooler port 5432 supports IPv4.
3. Obtain the server-only service role/secret key from project API settings.
   Keep it exclusively in Render environment variables, never browser code.
4. Migrations create the tables. PostgreSQL migrations enable RLS with no browser
   policies so application records cannot be read through the public Data API.
   Flask uses the owner database connection for its authorised server operations.

## Render

1. Create a Free Key Value instance in the same region as the web service. Use
   its internal Redis-compatible URL for RATELIMIT_STORAGE_URI; do not expose it
   externally. Free Key Value is transient: counters can reset on datastore restart.
2. New > Web Service > connect the GitHub repository, branch main, repository root.
   Select Docker and Free compute. Do not attach a paid disk or select paid resources.
3. Set these variables privately in the dashboard:

| Variable | Value |
| --- | --- |
| APP_ENV | production |
| SECRET_KEY | Generate a random 64-character hex value once; keep stable |
| DATABASE_URL | Supabase session pooler URI with psycopg driver and sslmode=require |
| MEDIA_STORAGE | supabase |
| SUPABASE_URL | Your project's HTTPS URL |
| SUPABASE_SERVICE_KEY | Server-only secret/service-role key |
| SUPABASE_BUCKET | afterpause-media |
| RATELIMIT_STORAGE_URI | Render Key Value internal URL |
| UPLOAD_DIR | /tmp/afterpause-uploads (not used for cloud media) |
| PROXY_HOPS | 1 behind Render's trusted proxy |
| WEB_CONCURRENCY | 1 for free compute |
| RUN_MIGRATIONS | 1 (single application instance) |

4. Set health check `/readyz`. Keep the Docker CMD; startup runs migrations.
5. Deploy only after SQLite, MySQL, PostgreSQL and Docker CI jobs pass.
6. Verify registration, private drafts, publication, contribution approval and
   image retrieval. Restart the service and confirm records and images survive.

Existing local uploads are not automatically migrated. Start with a fresh demo
collection or transfer files into the private bucket with matching storage keys
before switching an existing database. Do not run backup.sh/restore.sh against
PostgreSQL: those scripts are MySQL-specific. Use PostgreSQL pg_dump/pg_restore
and separately export the private media bucket for recovery.
