"""Regenerate docs/openapi.json (English) and docs/pt-BR/openapi.json from the FastAPI app. Run from the repo root:

    python scripts/export_openapi.py
"""
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("API_KEY", "export-only")

from api.main import app  # noqa: E402
from openapi_pt import PT  # noqa: E402

TEXT_KEYS = {"summary", "description"}


def servers(instance: str, host_description: str) -> list:
    return [
        {
            "url": "https://{host}",
            "description": instance,
            "variables": {"host": {"default": "api.seudominio.com", "description": host_description}},
        },
        {"url": "http://localhost:8000", "description": "Local"},
    ]


def translate(node, missing: set):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in TEXT_KEYS and isinstance(value, str):
                node[key] = PT.get(value, value)
                if value not in PT:
                    missing.add(value)
            elif key == "tags" and isinstance(value, list):
                node[key] = [PT.get(t, t) for t in value]
            else:
                translate(value, missing)
    elif isinstance(node, list):
        for value in node:
            translate(value, missing)


def write(spec: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


spec = app.openapi()
spec["security"] = [{"APIKeyHeader": []}]
spec["paths"]["/health"]["get"]["security"] = []

en = copy.deepcopy(spec)
en["servers"] = servers("Your instance", "Domain where the API is hosted")
write(en, ROOT / "docs" / "openapi.json")

pt = copy.deepcopy(spec)
missing: set = set()
translate(pt, missing)
pt["servers"] = servers("Sua instância", "Domínio onde a API está hospedada")
write(pt, ROOT / "docs" / "pt-BR" / "openapi.json")

# words that are the same in both languages
missing -= {"Health check", "Locker"}
for text in sorted(missing):
    print(f"Missing Portuguese translation in scripts/openapi_pt.py: {text!r}")
