"""Write docs/openapi-v1.json, the frozen contract for /api/v1.

Run after an intentional, backwards-compatible API change:
    uv run python scripts/export_openapi.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402

SNAPSHOT = ROOT / "docs" / "openapi-v1.json"


def current_spec() -> dict[str, object]:
    return json.loads(json.dumps(app.openapi()))


if __name__ == "__main__":
    SNAPSHOT.write_text(json.dumps(current_spec(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {SNAPSHOT.relative_to(ROOT)}")
