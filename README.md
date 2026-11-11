# Afterpause

**Someone paused. Someone else begins.** Afterpause is a digital museum for unfinished software and design projects. Visitors browse without an account. Creators save and preview private exhibits, contributors propose a continuation, and the public timeline shows approved work with both credits.

## Start locally

Use Python 3.12 or newer. From the repository root:

```bash
bash scripts/setup.sh
bash scripts/dev.sh
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). A fresh install starts with an empty collection. The quick start uses SQLite; the project stack and concurrency acceptance target use **MySQL 8.4**, Flask, Jinja, SQLAlchemy and Alembic.

The original `python -m flask --app afterpause run --debug` command also starts
this integrated application on port 5000. Both entry points use the same models,
templates, and migration history. Use a random `SECRET_KEY` of at least 32
characters in `.env` so sessions can be verified across restarts. The setup
script creates one on a fresh installation. Sessions expire after 12 hours of
inactivity.

For a separate labelled classroom demo:

```bash
bash scripts/demo.sh
APP_ENV=demo bash scripts/dev.sh
```

The seed asks for a password for `creator@example.test`, `contributor@example.test`, and `admin@example.test`. Rerunning it refreshes the demo passwords and fills missing fixtures without replacing existing exhibits. Demo mode uses a separate database and upload directory. Do not point it at a live database.

## Linux and MySQL setup

Install Python 3.12+, the matching venv package, and either MySQL 8.4 with client tools or Docker with the Compose plugin. Copy `.env.example` to `.env`, set a random `SECRET_KEY` (for example, `python3 -c 'import secrets; print(secrets.token_hex(32))'`), and replace the database passwords. Match the database URL ports to `MYSQL_PORT`. URL-encode any reserved characters in passwords embedded in database URLs.

With Compose:

```bash
docker compose up -d --wait mysql
bash scripts/setup.sh
bash scripts/dev.sh
```

Compose keeps the database in a volume and binds it to localhost. On a native MySQL server, create the `afterpause` database account and run [the initialization SQL](scripts/init-mysql.sql) as a database administrator instead of starting Compose. The grants in that file use `'afterpause'@'%'` for the Compose network; use a local account host when configuring a native server and match the grant statements to it. The application account only needs access to the named Afterpause databases.

Use `.venv/bin/flask --app app db upgrade` after pulling migration changes. To grant an existing account moderator access, run `.venv/bin/flask --app app make-admin admin@example.test` with the correct database configuration. Registration cannot grant this role.

## Verification

```bash
# SQLite, even if a MySQL test URL is exported in the shell:
TEST_DATABASE_URL= .venv/bin/python -m pytest -q
# MySQL: supply a disposable, empty database ending in _test:
TEST_DATABASE_URL='mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/afterpause_test?charset=utf8mb4' \
  .venv/bin/python -m pytest -q
```

The tests run migrations and clear records in the test database. They exercise the two account lifecycle, concurrent acceptance, rollback, draft and media privacy, authorisation, form validation, and moderation. GitHub Actions runs the checks on both engines. See [verification notes and screenshots](docs/verification.md) for the browser and recovery checks.

## Deployment and recovery

Use a persistent MySQL database and writable upload directory outside the application source. Set `APP_ENV=production`, a strong `SECRET_KEY`, and `DATABASE_URL` in the service environment. Run migrations before starting `.venv/bin/gunicorn --bind 127.0.0.1:8000 'app:create_app()'` behind an HTTPS reverse proxy. Configure the proxy to preserve the public host and to forward the HTTPS scheme from a trusted address. Do not enable Flask debug mode on a deployed instance. Rate limiting is local to each application process; use a shared edge limit if running multiple workers publicly.

Pause application writes before backing up the database and media together. Set `MYSQL_OPTION_FILE` to a private MySQL client option file (chmod 600) with `[client]`, `host`, `port`, `user` and `password` entries. With MySQL client tools on PATH:

```bash
bash scripts/backup.sh afterpause_demo instance/demo-uploads museum-demo.tar.gz
bash scripts/restore.sh afterpause_restore /path/to/empty/uploads museum-demo.tar.gz --confirm-restore
```

The destination database must already exist, be empty, and end in `_restore`. Use a trusted backup. See [recovery notes](docs/verification.md) for the restore check.

## Team handoffs

- [D1: Accounts and exhibit publishing](docs/accounts_and_publishing.md)
- [D2: Museum exploration and presentation](docs/museum_and_exploration.md)
- [D3: Continuations and moderation](docs/continuations_and_moderation.md)
- [Demo content and walkthrough](docs/demo.md)
- [Contributing](CONTRIBUTING.md) and [application license](LICENSE)

The original static concept is preserved under `prototype/`. Its sample features are illustrative; start the Flask application for the working museum.
