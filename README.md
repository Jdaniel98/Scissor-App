# Scissor

A small URL shortener built with FastAPI, SQLAlchemy and server-rendered Jinja2 pages.

## What it does

- Shortens a URL to a random 6-character code, or to a custom link you choose
- Redirects short links and counts every click
- Shows per-link analytics: total clicks and when each click happened
- Generates a QR code for any URL, including the short link it just made
- Lists every link created, with its click count

Data is stored in SQLite by default (`scissors.sqlite` in the working directory). Set
`DATABASE_URL` to any SQLAlchemy URL to use another database.

## Run it

Requires Python 3.10 or later.

```bash
git clone https://github.com/Jdaniel98/Scissor-App.git
cd Scissor-App
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. The interactive API docs are at http://127.0.0.1:8000/docs.

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Landing page |
| GET | `/url` | Form to shorten a URL |
| POST | `/shorten` | Create a short link (`long_url`, optional `custom_url`) |
| GET | `/urls` | All links with click counts |
| GET | `/analytics/{code}` | Clicks for one link |
| GET | `/qrcode?url=...` | QR code PNG for a URL |
| GET | `/{code}` | Redirect to the original URL |

Custom links must be 3 to 32 letters, digits, hyphens or underscores, and can't reuse a name
the app already serves (such as `urls` or `analytics`).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests run against a throwaway SQLite database and cover shortening, redirects, click
counting, per-link analytics, validation and QR generation. CI runs them on Python 3.10 and
3.12.

## Limitations

- No accounts: every link is visible on `/urls` to anyone who can reach the app.
- No rate limiting, so it isn't ready to expose to the public internet as is.

## License

MIT
