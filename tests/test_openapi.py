import json
from pathlib import Path

from app.main import app

SNAPSHOT = Path(__file__).resolve().parent.parent / "docs" / "openapi-v1.json"


def test_api_v1_contract_is_frozen():
    """Fails when the API's shape changes. If the change is intended and compatible,
    regenerate with `uv run python scripts/export_openapi.py`; if it breaks clients,
    put it under /api/v2 instead."""
    current = json.loads(json.dumps(app.openapi()))
    frozen = json.loads(SNAPSHOT.read_text())
    assert current == frozen


def test_spec_lists_only_the_api():
    paths = set(app.openapi()["paths"])
    assert paths == {
        "/api/v1/links",
        "/api/v1/links/{code}",
        "/api/v1/links/{code}/stats",
        "/api/v1/links/{code}/qr",
    }
