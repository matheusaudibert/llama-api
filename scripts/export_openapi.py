"""Regenerate docs/openapi.json from the FastAPI app. Run from the repo root:

    python scripts/export_openapi.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("API_KEY", "export-only")

from api.main import app  # noqa: E402

spec = app.openapi()
spec["servers"] = [
    {
        "url": "https://{host}",
        "description": "Sua instância",
        "variables": {"host": {"default": "api.seudominio.com", "description": "Domínio onde a API está hospedada"}},
    },
    {"url": "http://localhost:8000", "description": "Local"},
]
spec["security"] = [{"APIKeyHeader": []}]
spec["paths"]["/health"]["get"]["security"] = []

out = ROOT / "docs" / "openapi.json"
out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {out}")
