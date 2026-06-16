"""
Orquestador local del flujo de analisis de guias docentes.

No llama a APIs externas. Su funcion es:
- validar que existen las extracciones y el prompt base
- construir o refrescar salida/analisis/manifest.json
- detectar analisis ya generados en JSON/HTML
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTRACTIONS_DIR = ROOT / "salida" / "extracciones"
DEFAULT_ANALYSIS_DIR = ROOT / "salida" / "analisis"
DEFAULT_PROMPT_PATH = ROOT / "prompt.txt"


def load_extractions(extractions_dir: Path) -> list[dict[str, Any]]:
    manifest_path = extractions_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"No existe {manifest_path}. Ejecuta primero: python src/extract_guides.py"
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def ensure_prompt_exists(prompt_path: Path) -> None:
    if not prompt_path.exists():
        raise FileNotFoundError(f"No existe el archivo de prompt: {prompt_path}")


def load_existing_analysis(json_path: Path) -> dict[str, Any] | None:
    if not json_path.exists():
        return None

    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def summarize_entry(extraction: dict[str, Any], analysis_dir: Path) -> dict[str, Any]:
    slug = extraction["slug"]
    json_name = f"{slug}.json"
    html_name = f"{slug}.html"
    json_path = analysis_dir / json_name
    html_path = analysis_dir / html_name

    existing = load_existing_analysis(json_path)
    hallazgos = 0
    status = "pendiente"

    if existing is not None:
        hallazgos = len(existing.get("propuestas_de_cambio", []))
        status = "analizado"
    elif html_path.exists():
        status = "html_sin_json"

    return {
        "pdf": extraction["pdf"],
        "slug": slug,
        "txt": extraction["txt"],
        "chars": extraction["chars"],
        "json": json_name,
        "html": html_name,
        "hallazgos": hallazgos,
        "status": status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresca el manifest del analisis sin usar APIs externas"
    )
    parser.add_argument("--extractions-dir", type=Path, default=DEFAULT_EXTRACTIONS_DIR)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPT_PATH)
    args = parser.parse_args()

    try:
        extractions = load_extractions(args.extractions_dir)
        ensure_prompt_exists(args.prompt_file)
    except FileNotFoundError as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    if not extractions:
        print("Error: No hay guias extraidas.", file=sys.stderr)
        sys.exit(1)

    args.analysis_dir.mkdir(parents=True, exist_ok=True)

    summary = [summarize_entry(extraction, args.analysis_dir) for extraction in extractions]
    manifest_path = args.analysis_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total_hallazgos = sum(item["hallazgos"] for item in summary)
    total_analizadas = sum(1 for item in summary if item["status"] == "analizado")

    print("\n" + "=" * 80)
    print("ANALISIS DE GUIAS DOCENTES")
    print("=" * 80)
    print(f"Guias detectadas: {len(summary)}")
    print(f"Guias con JSON analizado: {total_analizadas}")
    print(f"Total hallazgos: {total_hallazgos}")
    print(f"Manifest actualizado: {manifest_path}\n")

    pendientes = [item for item in summary if item["status"] != "analizado"]
    if pendientes:
        print("Pendientes de generar analisis:")
        for item in pendientes:
            print(f"- {item['pdf']} ({item['status']})")
        print()


if __name__ == "__main__":
    main()
