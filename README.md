# Scissor

A small URL shortener built with FastAPI, SQLAlchemy and server-rendered Jinja2 pages.

## What it does

- Shortens a URL to a random 6-character code, or to a custom link you choose
- Redirects short links and counts every click
- Shows per-link analytics: total clicks and when each click happened (in UTC)
- Generates a QR code for any URL, including the short link it just made

## Run it with Docker

```bash
git clone https://github.com/Jdaniel98/Scissor-App.git
cd Scissor-App
docker compose up --build
```

This starts the app on Postgres 16 with Redis 7 alongside it, and applies database migrations
on startup. Open http://127.0.0.1:8000. The interactive API docs are at
http://127.0.0.1:8000/docs.

## Run it locally

Requires Python 3.10 or later and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Data is stored in SQLite by default (`scissors.sqlite` in the working directory). Settings come
from environment variables or a `.env` file; see `.env.example`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./scissors.sqlite` | Any SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@host:5432/db` |
| `REDIS_URL` | `redis://localhost:6379/0` | Not used yet; caching and rate limits arrive next |

### Upgrading a database from an earlier version

Earlier versions created tables on startup without migrations. Mark such a database as being at
the baseline, then upgrade it:

```bash
uv run alembic stamp 0001
uv run alembic upgrade head
```

## Deploy to Render

`render.yaml` describes the whole stack: the web service (built from the Dockerfile),
Postgres 16 and a Key Value (Redis) instance, all in Frankfurt. In Render, choose
**New > Blueprint** and pick this repository. Migrations run on every deploy.

Everything starts on Render's free plans, which suit a demo but not real traffic: free web
services sleep after 15 idle minutes and take about a minute to wake, and free Postgres
expires 30 days after it is created. Before launch, move the web service to `starter` and
the database to a paid plan in `render.yaml`.

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Landing page |
| GET | `/url` | Form to shorten a URL |
| POST | `/shorten` | Create a short link (`long_url`, optional `custom_url`) |
| GET | `/analytics/{code}` | Clicks for one link |
| GET | `/qrcode?url=...` | QR code PNG for a URL |
| GET, HEAD | `/{code}` | Redirect to the original URL (`HEAD` isn't counted as a click) |

Custom links must be 3 to 32 letters, digits, hyphens or underscores, and can't reuse a name
the app already serves (such as `urls` or `analytics`).

## Development

```bash
uv sync
uv run pre-commit install   # ruff, mypy and file checks on every commit
uv run pytest
```

The tests build their database with the migrations, so they also check that migrations and
models agree. Set `TEST_DATABASE_URL` to run them against Postgres. CI runs lint, format and
strict type checks, the tests on Python 3.10 and 3.12 with SQLite, and the tests on Postgres 16.

## Limitations

- No accounts yet, so the list of all links is switched off; analytics pages are reachable by
  anyone who knows the code.
- No rate limiting, so it isn't ready to expose to the public internet as is.

## License

MIT
