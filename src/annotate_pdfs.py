import argparse
import json
import re
from pathlib import Path
from typing import Any

import fitz


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "guiadocentes"
DEFAULT_ANALYSIS_DIR = ROOT / "salida" / "analisis"
DEFAULT_OUTPUT_DIR = ROOT / "salida" / "pdf_anotados"

SECTION_ALIASES: dict[str, list[str]] = {
    "recomendaciones generales": ["recomendaciones generales"],
    "contexto": ["contexto"],
    "contenidos de la asignatura": ["contenidos de la asignatura", "contenidos"],
    "resultados especificos de aprendizaje": [
        "resultados especificos de aprendizaje",
        "resultados de aprendizaje",
    ],
    "sistema de evaluacion": ["sistema de evaluacion", "evaluacion"],
    "biografia y otros recursos": ["bibliografia y otros recursos", "bibliografia", "referencias"],
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def crop_candidate(texto_original: str, max_len: int) -> str:
    cleaned = normalize_text(texto_original)
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rsplit(" ", 1)[0].strip()


def load_manifest(analysis_dir: Path) -> list[dict[str, Any]]:
    manifest_path = analysis_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No existe {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def find_matches(doc: fitz.Document, raw_text: str) -> list[tuple[int, fitz.Rect, str]]:
    candidates = []
    for max_len in (220, 170, 120, 90, 65):
        candidate = crop_candidate(raw_text, max_len)
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    for candidate in candidates:
        for page_index, page in enumerate(doc):
            matches = page.search_for(candidate)
            if matches:
                return [(page_index, rect, candidate) for rect in matches]

    return []


def section_terms(seccion: str) -> list[str]:
    key = normalize_text(seccion).lower()
    terms = SECTION_ALIASES.get(key)
    if terms:
        return terms
    return [key] if key else []


def locate_section_anchor(doc: fitz.Document, seccion: str) -> tuple[int, fitz.Rect] | None:
    terms = section_terms(seccion)
    for term in terms:
        if not term:
            continue
        for page_index, page in enumerate(doc):
            matches = page.search_for(term)
            if matches:
                return page_index, matches[0]
    return None


def add_section_note(doc: fitz.Document, seccion: str, comment: str) -> bool:
    anchor = locate_section_anchor(doc, seccion)
    if anchor is not None:
        page_index, rect = anchor
        page = doc[page_index]
        highlight = page.add_highlight_annot(rect)
        highlight.set_colors(stroke=(1, 1, 0))
        highlight.set_info(title="Revision inclusiva", content=comment)
        highlight.update()

        note_point = fitz.Point(min(rect.x1 + 12, page.rect.width - 40), max(rect.y0 - 4, 16))
        note = page.add_text_annot(note_point, comment)
        note.set_info(title="Revision inclusiva", content=comment)
        note.update()
        return True

    first_page = doc[0]
    fallback = first_page.add_text_annot(
        fitz.Point(24, 24),
        f"[Seccion no localizada automaticamente: {seccion}]\n{comment}",
    )
    fallback.set_info(title="Revision inclusiva", content=comment)
    fallback.update()
    return False


def annotate_pdf(
    source_pdf: Path,
    output_pdf: Path,
    proposals: list[dict[str, Any]],
    mode: str,
) -> dict[str, int]:
    doc = fitz.open(source_pdf)
    total_marked = 0
    total_unmatched = 0
    total_section_notes = 0
    total_section_fallback = 0

    for proposal in proposals:
        texto_original = str(proposal.get("texto_original", ""))
        texto_propuesto = str(proposal.get("texto_propuesto", ""))
        motivo = str(proposal.get("motivo", ""))
        seccion = str(proposal.get("seccion", ""))

        comment = (
            f"Seccion: {seccion}\n"
            f"Texto propuesto: {texto_propuesto}\n"
            f"Motivo: {motivo}"
        )

        if mode in {"exact", "hybrid"} and normalize_text(texto_original):
            matches = find_matches(doc, texto_original)
            if matches:
                for page_index, rect, _ in matches:
                    page = doc[page_index]
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=(1, 1, 0))
                    annot.set_info(title="Revision inclusiva", content=comment)
                    annot.update()
                    total_marked += 1
                continue

        if mode in {"section", "hybrid"}:
            anchored = add_section_note(doc, seccion, comment)
            total_section_notes += 1
            if not anchored:
                total_section_fallback += 1
            continue

        total_unmatched += 1

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_pdf)
    doc.close()
    return {
        "marcados": total_marked,
        "sin_encontrar": total_unmatched,
        "notas_seccion": total_section_notes,
        "seccion_fallback": total_section_fallback,
    }


def run(source_dir: Path, analysis_dir: Path, output_dir: Path, mode: str) -> None:
    manifest = load_manifest(analysis_dir)

    summary: list[dict[str, Any]] = []
    for item in manifest:
        pdf_name = item.get("pdf", "")
        json_name = item.get("json", "")
        if not pdf_name or not json_name:
            continue

        source_pdf = source_dir / pdf_name
        json_path = analysis_dir / json_name
        output_pdf = output_dir / pdf_name

        if not source_pdf.exists() or not json_path.exists():
            print(f"Saltando: faltan archivos para {pdf_name}")
            continue

        analysis = json.loads(json_path.read_text(encoding="utf-8"))
        proposals = analysis.get("propuestas_de_cambio", [])
        if not isinstance(proposals, list):
            proposals = []

        stats = annotate_pdf(source_pdf, output_pdf, proposals, mode)
        summary_item = {
            "pdf": pdf_name,
            "output": str(output_pdf.relative_to(ROOT)),
            "propuestas": len(proposals),
            "marcados": stats["marcados"],
            "sin_encontrar": stats["sin_encontrar"],
            "notas_seccion": stats["notas_seccion"],
            "seccion_fallback": stats["seccion_fallback"],
        }
        summary.append(summary_item)
        print(
            f"OK {pdf_name} -> marcados={summary_item['marcados']} "
            f"notas_seccion={summary_item['notas_seccion']} "
            f"sin_encontrar={summary_item['sin_encontrar']}"
        )

    summary_path = output_dir / "resumen_anotacion.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResumen: {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copia guias PDF y anota en amarillo los textos a mejorar"
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--mode",
        choices=["exact", "section", "hybrid"],
        default="hybrid",
        help="exact: solo texto exacto, section: nota por seccion, hybrid: exacto y fallback por seccion",
    )
    args = parser.parse_args()

    run(args.source_dir, args.analysis_dir, args.output_dir, args.mode)


if __name__ == "__main__":
    main()
