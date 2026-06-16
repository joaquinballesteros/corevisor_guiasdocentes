"""
Extractor de guias docentes en PDF.
Prepara los textos para analisis por GitHub Copilot (runSubagent).
No requiere claves API externas.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GUIDES_DIR = ROOT / "guiadocentes"
DEFAULT_OUTPUT_DIR = ROOT / "salida" / "extracciones"


def slugify(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9._-]+", "-", name)
    return clean.strip("-")


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages: List[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages).strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrae texto de guias docentes PDF para analizar con Copilot"
    )
    parser.add_argument("--guides-dir", type=Path, default=DEFAULT_GUIDES_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    guides_dir = args.guides_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(guides_dir.glob("*.pdf"))
    if not pdf_files:
        raise RuntimeError(f"No se encontraron PDFs en {guides_dir}")

    manifest: List[Dict[str, Any]] = []
    for pdf_file in pdf_files:
        print(f"Extrayendo: {pdf_file.name}")
        guide_text = extract_pdf_text(pdf_file)
        if not guide_text:
            print(f"  Aviso: texto vacio en {pdf_file.name}, se omite")
            continue

        slug = slugify(pdf_file.stem)
        txt_path = output_dir / f"{slug}.txt"
        txt_path.write_text(guide_text, encoding="utf-8")

        manifest_item = {
            "pdf": pdf_file.name,
            "slug": slug,
            "txt": txt_path.name,
            "chars": len(guide_text),
        }
        manifest.append(manifest_item)
        print(f"  OK -> {txt_path.name} ({len(guide_text)} chars)")

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nExtracciones listas en: {output_dir}")
    print(f"Proximamente: leer el archivo ANALIZAR_CON_COPILOT.md para el flujo de analisis")


if __name__ == "__main__":
    main()
