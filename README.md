# Revision de guias docentes

Proyecto para revisar guias docentes en PDF desde la perspectiva de lenguaje inclusivo y perspectiva de genero.

El repositorio contiene:

1. Extraccion de texto desde los PDF originales.
2. Resultados de analisis guardados en JSON.
3. Informes HTML por guia.
4. Un visor web con todas las propuestas en una sola pagina.
5. Copias anotadas de los PDF con comentarios y resaltados.

## Estructura

- `guiadocentes/`: PDFs originales.
- `prompt.txt`: prompt base de revision.
- `salida/extracciones/`: texto extraido de cada PDF.
- `salida/analisis/`: JSON, HTML y `manifest.json` de los analisis.
- `salida/pdf_anotados/`: copias PDF con anotaciones.

## Requisitos

- Python 3.10+

## Instalacion

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para generar analisis con IA debes configurar OpenAI en entorno:

```bash
cp .env.example .env
# edita .env y pon tu OPENAI_API_KEY
```

## Flujo actual

### 1. Extraer el texto de las guias

```bash
python src/extract_guides.py
```

Genera:

- `salida/extracciones/*.txt`
- `salida/extracciones/manifest.json`

### 2. Refrescar el indice de analisis

```bash
python src/analyze_guides.py
```

Este script no llama a ningun modelo externo. Su funcion actual es:

- comprobar que existen las extracciones
- comprobar que existe `prompt.txt`
- detectar los JSON/HTML ya presentes en `salida/analisis/`
- regenerar `salida/analisis/manifest.json`

Genera o actualiza:

- `salida/analisis/manifest.json`

### 3. Generar analisis (JSON + HTML) en base a `prompt.txt`

```bash
# procesa solo guias pendientes
python src/generate_analysis.py --only-pending

# procesa todas las guias (rehace JSON/HTML)
python src/generate_analysis.py
```

Este script usa OpenAI y aplica las directrices de `prompt.txt` para generar:

- `salida/analisis/*.json`
- `salida/analisis/*.html`

Despues ejecuta de nuevo:

```bash
python src/analyze_guides.py
```

Opciones utiles:

```bash
# elegir modelo (por defecto gpt-4o-mini)
python src/generate_analysis.py --model gpt-4o-mini

# ajustar limites de salida
python src/generate_analysis.py --max-output-tokens 1800
```

## Resultados de analisis

Los analisis estructurados están en:

- `salida/analisis/*.json`

Y sus informes HTML asociados en:

- `salida/analisis/*.html`

Cada informe contiene estas columnas:

- `seccion`
- `texto_original`
- `texto_propuesto`
- `motivo`


## (Opción 1) App web de revision

```bash
python webapp.py
```

Abre en navegador:

- `http://127.0.0.1:8000`

La app muestra un informe en linea con todas las guias, ordenadas lexicograficamente por nombre, y solo las propuestas de cambio.

## (Opción 2) Anotar los PDF originales

Puedes generar una copia anotada de cada PDF con comentarios y marcado amarillo usando:

```bash
python src/annotate_pdfs.py
```

Modos disponibles:

```bash
# Resaltar texto exacto cuando se encuentra y, si no, anotar por seccion
python src/annotate_pdfs.py --mode hybrid

# Poner siempre la nota en la seccion
python src/annotate_pdfs.py --mode section

# Solo texto exacto
python src/annotate_pdfs.py --mode exact
```

Salida:

- `salida/pdf_anotados/*.pdf`
- `salida/pdf_anotados/resumen_anotacion.json`

Notas:

- En modo `section`, si no se localiza la seccion exacta, la nota se inserta en la primera pagina y queda contabilizada como `seccion_fallback`.
- En modo `hybrid`, primero se intenta marcar el texto exacto y, si no aparece, se deja la nota en la seccion.
