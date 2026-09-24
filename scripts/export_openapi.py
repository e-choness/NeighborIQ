"""
Regenerate services/<name>/openapi.json from the live FastAPI apps.

    python scripts/export_openapi.py            # write all specs
    python scripts/export_openapi.py --check    # exit 1 if any committed spec is stale (CI)

Each service is imported in a fresh interpreter because every service ships an
`app` package and they would shadow each other in one process.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ["api"]

_DUMP = "import json, app.main as m; print(json.dumps(m.app.openapi(), indent=2, sort_keys=True))"


def spec_for(service: str) -> str:
    env_path = f"{ROOT}:{ROOT / 'services' / service}"
    out = subprocess.run(
        [sys.executable, "-c", _DUMP],
        cwd=ROOT / "services" / service,
        # Fixed hash seed: multi-method routes list their operations in set order
        env={"PYTHONPATH": env_path, "PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0"},
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for service in SERVICES:
        path = ROOT / "services" / service / "openapi.json"
        spec = spec_for(service)
        if check:
            current = path.read_text() if path.exists() else ""
            if json.loads(current or "{}") != json.loads(spec):
                stale.append(service)
        else:
            path.write_text(spec)
            print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print("stale openapi.json:", ", ".join(stale), "— run python scripts/export_openapi.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
