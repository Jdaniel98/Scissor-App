# Scissor

A small URL shortener built with FastAPI, SQLAlchemy and server-rendered Jinja2 pages.

## What it does

- Shortens a URL to a random 6-character code, or to a custom link you choose
- Redirects short links and counts every click
- Shows per-link analytics: total clicks and when each click happened (in UTC)
- Generates a QR code for any URL, including the short link it just made (PNG or SVG)
- A JSON API (`/api/v1`) to create, look up, edit and delete links and read their stats
- Refuses unsafe destinations, rate-limits by IP, and serves redirects from a Redis cache

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
| `REDIS_URL` | empty | Redis for the redirect cache and rate limits; empty keeps both in memory (one process only) |
| `RATE_LIMIT_CREATE` | `20/minute` | Links one IP can create |
| `RATE_LIMIT_MANAGE` | `60/minute` | Edits, deletes and stats requests per IP |
| `RATE_LIMIT_QR` | `60/minute` | QR codes per IP |
| `REDIRECT_CACHE_TTL` | `86400` | Seconds a code stays in the redirect cache |
| `PUBLIC_HOSTS` | empty | Other hostnames the app is served on, comma-separated; links to them are refused |

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

## API

Interactive docs are at `/docs`; the frozen contract is `docs/openapi-v1.json`.

| Method | Path | Edit key | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/links` | | Create a link (`url`, optional `code`); returns its `edit_key` once |
| GET | `/api/v1/links/{code}` | | Where a link points |
| PATCH | `/api/v1/links/{code}` | yes | Change the destination (`url`) |
| DELETE | `/api/v1/links/{code}` | yes | Delete the link and its click history |
| GET | `/api/v1/links/{code}/stats` | yes | Total clicks, last click, clicks per day for 30 days |
| GET | `/api/v1/links/{code}/qr?format=png\|svg` | | QR code for the short link |

```bash
curl -s -X POST localhost:8000/api/v1/links \
  -H 'Content-Type: application/json' -d '{"url": "https://example.com", "code": "demo"}'
# {"code": "demo", "short_url": "http://localhost:8000/demo", ..., "edit_key": "..."}

curl -s localhost:8000/api/v1/links/demo/stats -H "Authorization: Bearer $EDIT_KEY"
```

The edit key is shown once and stored only as a hash. Every error has the same shape:
`{"error": {"code": "invalid_url", "message": "..."}}`, plus `fields` on validation errors.
Destinations must be public `http` or `https` URLs: private and local addresses, URLs with a
username or password, and the app's own host are refused.

## Pages

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Landing page |
| GET | `/url` | Form to shorten a URL |
| POST | `/shorten` | Create a short link (`long_url`, optional `custom_url`) and show its edit key |
| GET | `/analytics/{code}` | Clicks for one link |
| GET | `/qrcode?url=...` | QR code PNG for a URL |
| GET, HEAD | `/{code}` | 302 redirect to the destination (`HEAD` isn't counted as a click) |

Custom links must be 3 to 32 letters, digits, hyphens or underscores, and can't reuse a name
the app already serves (such as `api` or `analytics`).

## Development

```bash
uv sync
uv run pre-commit install   # ruff, mypy and file checks on every commit
uv run pytest
```

The tests build their database with the migrations, so they also check that migrations and
models agree. Set `TEST_DATABASE_URL` to run them against Postgres. CI runs lint, format and
strict type checks, the tests on Python 3.10 and 3.12 with SQLite, and the tests on Postgres 16
with Redis (also set `TEST_REDIS_URL` to run those locally), failing under 90% coverage.

## Limitations

- No accounts yet: links are managed with their edit key, there's no list of your links, and
  the HTML analytics page is reachable by anyone who knows the code. Accounts come next.
- Links made before edit keys existed can't be edited through the API until accounts can
  claim them.

## License

MIT
