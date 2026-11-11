# Production deployment

Deploy the repository root using the Dockerfile. Provision MySQL 8.4, Redis,
and a persistent volume mounted at `/data`. The container runs as UID/GID 10001;
the volume must be writable by this user. Do not use ephemeral storage for uploads.

## Service environment

| Variable | Value |
| --- | --- |
| APP_ENV | production (also enforced by startup) |
| SECRET_KEY | Generate once with `python3 -c 'import secrets; print(secrets.token_hex(32))'`; keep stable and private |
| DATABASE_URL | `mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE?charset=utf8mb4` |
| RATELIMIT_STORAGE_URI | Private Redis URL, `redis://...` or TLS `rediss://...` |
| UPLOAD_DIR | `/data/uploads` |
| PORT | Hosting-injected port, defaults to 8000 |
| PROXY_HOPS | 1 only when behind one trusted proxy that overwrites X-Forwarded-For/Proto; otherwise 0 |
| WEB_CONCURRENCY | 2 initially |
| RUN_MIGRATIONS | 1 for a single instance; 0 when using a separate migration job |

URL-encode special characters in database credentials. Keep database and Redis
private. Configure HTTPS at the hosting proxy and preserve the public Host header.
Never expose the Gunicorn port directly when PROXY_HOPS=1.

## Release

1. Run the existing SQLite and MySQL CI checks before deployment.
2. Build the Dockerfile from the repository root.
3. Attach the volume, set the environment, then start one instance. Startup runs
   Alembic migrations before accepting traffic; a migration failure stops startup.
4. Set the hosting readiness check to `/readyz` (database schema and Redis).
   `/healthz` checks process liveness only. Review logs if readiness returns 503.
5. Register two test accounts and verify publish, proposal, approval, credited
   timeline, logout/login, and screenshot persistence across a service restart.
6. Promote an existing account using `flask --app app make-admin EMAIL` in the
   service shell. Do not seed demo users in production.

For multiple replicas, provide shared upload storage, run `flask --app app db upgrade`
once as a release job, and set RUN_MIGRATIONS=0 on every replica. A volume local to
one container is insufficient. Back up database and uploads together before schema
changes; follow the existing backup/restore documentation. Roll back application
images only when compatible with the current schema; do not blindly downgrade data.

Hosting resources have not been provisioned by this configuration.
