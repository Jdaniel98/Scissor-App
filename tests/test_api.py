"""The /api/v1 endpoints."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.models import URL, Click


def create(client, url="https://example.com/page", code=None):
    body = {"url": url}
    if code is not None:
        body["code"] = code
    return client.post("/api/v1/links", json=body)


def auth(key):
    return {"Authorization": f"Bearer {key}"}


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    return body["error"]


# -- create and read -----------------------------------------------------------------------


def test_create_returns_link_and_edit_key(client, sync_engine):
    response = create(client, code="hello")
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "hello"
    assert body["short_url"] == "http://testserver/hello"
    assert body["url"] == "https://example.com/page"
    assert len(body["edit_key"]) >= 32

    # Only a hash of the key is stored.
    with Session(sync_engine) as db:
        stored = db.scalars(select(URL).where(URL.short_url == "hello")).one()
    assert stored.edit_key_hash and body["edit_key"] not in stored.edit_key_hash


def test_create_with_random_code(client):
    body = create(client).json()
    assert len(body["code"]) == 6


def test_get_link_is_public_and_hides_edit_key(client):
    create(client, code="lookup")
    body = client.get("/api/v1/links/lookup").json()
    assert body["url"] == "https://example.com/page"
    assert "edit_key" not in body


def test_missing_link_is_404(client):
    assert_error(client.get("/api/v1/links/nope"), 404, "not_found")


# -- errors share one shape ----------------------------------------------------------------


def test_validation_errors_name_the_field(client):
    error = assert_error(client.post("/api/v1/links", json={}), 422, "validation_error")
    assert error["fields"][0]["field"] == "url"


def test_taken_and_bad_codes(client):
    create(client, code="dupe")
    assert_error(create(client, code="dupe"), 409, "code_taken")
    assert_error(create(client, code="no spaces"), 400, "invalid_code")
    assert_error(create(client, code="api"), 400, "invalid_code")


def test_unknown_api_route_uses_error_format(client):
    assert_error(client.get("/api/v1/nothing-here/at-all"), 404, "not_found")


# -- destination policy --------------------------------------------------------------------


def test_unsafe_destinations_refused(client):
    for url in [
        "ftp://example.com/file",
        "javascript:alert(1)",
        "http://10.0.0.1/admin",
        "http://127.0.0.1:8000/",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost/",
        "http://printer.local/",
        "http://intranet/",
        "https://user:pass@example.com/",
        "http://testserver/loop",  # the app's own host
        "https://example.com/" + "a" * 2100,
    ]:
        assert_error(create(client, url=url), 400, "invalid_url")


def test_public_hosts_setting_is_refused(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "public_hosts", "sciss.or, www.sciss.or")
    assert_error(create(client, url="https://sciss.or/abc"), 400, "invalid_url")
    assert create(client, url="https://example.org/").status_code == 201


# -- edit keys -----------------------------------------------------------------------------


def test_update_needs_the_right_key(client):
    key = create(client, code="move").json()["edit_key"]
    body = {"url": "https://example.org/new"}

    assert_error(client.patch("/api/v1/links/move", json=body), 401, "edit_key_required")
    assert_error(
        client.patch("/api/v1/links/move", json=body, headers=auth("wrong")),
        403,
        "edit_key_invalid",
    )
    response = client.patch("/api/v1/links/move", json=body, headers=auth(key))
    assert response.status_code == 200
    assert response.json()["url"] == "https://example.org/new"


def test_update_takes_effect_despite_the_cache(client):
    key = create(client, code="cached").json()["edit_key"]
    assert client.get("/cached").headers["location"] == "https://example.com/page"  # cached now

    client.patch(
        "/api/v1/links/cached", json={"url": "https://example.org/next"}, headers=auth(key)
    )
    assert client.get("/cached").headers["location"] == "https://example.org/next"


def test_update_checks_the_new_destination(client):
    key = create(client, code="guard").json()["edit_key"]
    response = client.patch(
        "/api/v1/links/guard", json={"url": "http://192.168.1.1/"}, headers=auth(key)
    )
    assert_error(response, 400, "invalid_url")


def test_delete_removes_link_clicks_and_cache(client, sync_engine):
    key = create(client, code="gone").json()["edit_key"]
    client.get("/gone")  # a click, and a cache entry

    assert_error(client.delete("/api/v1/links/gone"), 401, "edit_key_required")
    assert client.delete("/api/v1/links/gone", headers=auth(key)).status_code == 204

    assert client.get("/gone").status_code == 404
    assert_error(client.get("/api/v1/links/gone"), 404, "not_found")
    with Session(sync_engine) as db:
        assert db.scalar(select(func.count()).select_from(Click)) == 0


def test_links_without_a_key_cannot_be_changed(client, sync_engine):
    # Links made before edit keys existed have no hash.
    with Session(sync_engine) as db:
        db.add(URL(long_url="https://example.com/old", short_url="legacy", clicks=0))
        db.commit()
    response = client.delete("/api/v1/links/legacy", headers=auth("anything"))
    assert_error(response, 403, "edit_key_invalid")


# -- stats ---------------------------------------------------------------------------------


def test_stats_count_clicks_per_day(client):
    key = create(client, code="counted").json()["edit_key"]
    for _ in range(3):
        client.get("/counted")
    client.head("/counted")  # not a click

    assert_error(client.get("/api/v1/links/counted/stats"), 401, "edit_key_required")
    stats = client.get("/api/v1/links/counted/stats", headers=auth(key)).json()
    assert stats["total_clicks"] == 3
    assert len(stats["daily"]) == 30
    today = datetime.now(timezone.utc).date().isoformat()
    assert stats["daily"][-1] == {"date": today, "clicks": 3}
    assert sum(day["clicks"] for day in stats["daily"]) == 3
    assert stats["last_clicked_at"] is not None


def test_stats_for_unclicked_link(client):
    key = create(client, code="quiet").json()["edit_key"]
    stats = client.get("/api/v1/links/quiet/stats", headers=auth(key)).json()
    assert stats["total_clicks"] == 0
    assert stats["last_clicked_at"] is None


# -- QR codes ------------------------------------------------------------------------------


def test_qr_png_and_svg(client):
    create(client, code="scan")
    png = client.get("/api/v1/links/scan/qr")
    assert png.headers["content-type"] == "image/png"
    assert png.content.startswith(b"\x89PNG")

    svg = client.get("/api/v1/links/scan/qr", params={"format": "svg"})
    assert svg.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in svg.content

    assert_error(
        client.get("/api/v1/links/scan/qr", params={"format": "gif"}), 422, "validation_error"
    )
    assert_error(client.get("/api/v1/links/nope/qr"), 404, "not_found")


# -- rate limits ---------------------------------------------------------------------------


def test_create_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_create", "3/minute")
    for i in range(3):
        assert create(client, code=f"burst{i}").status_code == 201
    response = create(client, code="burst3")
    assert_error(response, 429, "rate_limited")
    assert int(response.headers["Retry-After"]) >= 1

    # The HTML form shares the same budget.
    assert client.post("/shorten", data={"long_url": "https://example.com"}).status_code == 429


def test_qr_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_qr", "2/minute")
    create(client, code="qrs")
    assert client.get("/api/v1/links/qrs/qr").status_code == 200
    assert client.get("/qrcode", params={"url": "https://example.com"}).status_code == 200
    assert_error(client.get("/api/v1/links/qrs/qr"), 429, "rate_limited")
