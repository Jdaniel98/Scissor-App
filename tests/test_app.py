"""The server-rendered pages and the redirect."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import URL, Click
from app.services import links as link_service
from app.services.links import CODE_LENGTH, generate_code, is_valid_custom_code
from app.templates import format_utc


def shorten(client, long_url="https://example.com/a/long/path", custom_url=None):
    data = {"long_url": long_url}
    if custom_url is not None:
        data["custom_url"] = custom_url
    return client.post("/shorten", data=data)


def test_pages_render(client):
    for path in ["/", "/url", "/download-qrcode"]:
        assert client.get(path).status_code == 200, path


def test_link_list_is_offline(client):
    shorten(client, custom_url="private-one")
    response = client.get("/urls")
    assert response.status_code == 404
    assert "example.com" not in response.text


def test_custom_link_redirects_and_counts_clicks(client):
    response = shorten(client, custom_url="docs-link")
    assert response.status_code == 200
    assert "http://testserver/docs-link" in response.text
    assert "Your edit key" in response.text

    redirect = client.get("/docs-link")
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/a/long/path"

    analytics = client.get("/analytics/docs-link")
    assert "Total clicks: 1" in analytics.text
    assert " UTC</li>" in analytics.text


def test_generated_code_shape(client):
    code = generate_code()
    assert len(code) == CODE_LENGTH and code.isalnum()
    assert shorten(client).status_code == 200


def test_generated_code_retries_on_collision(client, monkeypatch):
    shorten(client, custom_url="abcdef")
    codes = iter(["abcdef", "ghijkl"])
    monkeypatch.setattr(link_service, "generate_code", lambda: next(codes))

    response = shorten(client)
    assert response.status_code == 200
    assert "http://testserver/ghijkl" in response.text


def test_gives_up_when_no_free_code(client, monkeypatch):
    shorten(client, custom_url="same00")
    monkeypatch.setattr(link_service, "generate_code", lambda: "same00")
    response = client.post("/api/v1/links", json={"url": "https://example.com"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "no_free_code"


def test_form_errors_render_on_the_form(client):
    response = shorten(client, long_url="not a url")
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert 'role="alert"' in response.text
    assert 'value="not a url"' in response.text


def test_duplicate_custom_link_rejected(client):
    assert shorten(client, custom_url="taken").status_code == 200
    response = shorten(client, custom_url="taken")
    assert response.status_code == 409
    assert "already in use" in response.text


def test_reserved_and_malformed_custom_links_rejected(client):
    for bad in ["urls", "analytics", "api", "a", "has/slash", "x" * 33]:
        assert shorten(client, custom_url=bad).status_code == 400, bad
    assert not is_valid_custom_code("URLS")
    assert is_valid_custom_code("my_link-1")


def test_analytics_only_counts_its_own_clicks(client):
    shorten(client, long_url="https://example.com/one", custom_url="one")
    shorten(client, long_url="https://example.com/two", custom_url="two")
    for _ in range(3):
        client.get("/one")
    client.get("/two")

    assert client.get("/analytics/one").text.count("Clicked at") == 3
    assert client.get("/analytics/two").text.count("Clicked at") == 1


def test_concurrent_clicks_are_all_counted(client, sync_engine):
    shorten(client, custom_url="busy")
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda _: client.get("/busy").status_code, range(40)))
    assert statuses == [302] * 40

    with Session(sync_engine) as db:
        link = db.scalars(select(URL).where(URL.short_url == "busy")).one()
        events = db.scalar(select(func.count()).select_from(Click).where(Click.url_id == link.id))
    assert link.clicks == 40
    assert events == 40


def test_head_redirects_without_counting(client):
    shorten(client, custom_url="peek")
    response = client.head("/peek")
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/a/long/path"
    assert "Total clicks: 0" in client.get("/analytics/peek").text


def test_unknown_link_is_404(client):
    assert client.get("/nope123").status_code == 404
    assert client.head("/nope123").status_code == 404
    assert client.get("/analytics/nope123").status_code == 404


def test_qr_code_is_png_for_valid_url_only(client):
    ok = client.get("/qrcode", params={"url": "https://example.com"})
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "image/png"
    assert ok.content.startswith(b"\x89PNG")
    assert client.get("/qrcode", params={"url": "nonsense"}).status_code == 400


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2026, 11, 12, 9, 30, 5), "2026-11-12 09:30:05 UTC"),
        (datetime(2026, 11, 12, 9, 30, 5, tzinfo=timezone.utc), "2026-11-12 09:30:05 UTC"),
        (datetime.fromisoformat("2026-11-12T10:30:05+01:00"), "2026-11-12 09:30:05 UTC"),
        (None, ""),
    ],
)
def test_timestamps_render_in_utc(value, expected):
    assert format_utc(value) == expected
