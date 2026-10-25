"""Writes the OpenAPI schema for the web client generator (no server needed).

uv run python -m app.openapi_export
"""

import json
import sys

from app.core.config import REPO_ROOT, Settings
from app.main import create_app

OPENAPI_PATH = REPO_ROOT / "apps" / "web" / "lib" / "api" / "openapi.json"


def render_openapi() -> str:
    app = create_app(Settings(app_env="test", sentry_dsn=None))
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_bytes(render_openapi().encode("utf-8"))
    print(f"wrote {OPENAPI_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
