from pathlib import Path
import json

from flask import Flask, render_template

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "salida" / "analisis"
MANIFEST_PATH = REPORTS_DIR / "manifest.json"

app = Flask(__name__, template_folder="templates")


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def load_inline_reports() -> list[dict]:
    reports = load_manifest()
    reports = sorted(reports, key=lambda x: x.get("pdf", "").lower())

    inline_reports: list[dict] = []
    for report in reports:
        json_name = report.get("json", "")
        if not json_name:
            continue

        json_path = REPORTS_DIR / json_name
        if not json_path.exists():
            continue

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        inline_reports.append(
            {
                "pdf": report.get("pdf", ""),
                "slug": report.get("slug", ""),
                "propuestas": data.get("propuestas_de_cambio", []),
            }
        )

    return inline_reports


@app.get("/")
def home():
    reports = load_inline_reports()
    return render_template("index.html", reports=reports)


@app.get("/health")
def health():
    return {"status": "ok", "reports_dir": str(REPORTS_DIR)}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
