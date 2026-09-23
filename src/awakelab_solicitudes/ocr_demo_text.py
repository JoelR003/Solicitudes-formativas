"""Save the OCR text of a scanned request for the demo."""

from __future__ import annotations

import argparse
from pathlib import Path

from .extractors import PdfExtractor, TesseractOcr


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOLICITUDES_DIR = PROJECT_ROOT.parent / "caso-solicitudes-documentales" / "solicitudes"
OUTPUT_DIR = PROJECT_ROOT / "output" / "ocr_demo"

# Checked transcription used only when the demo is run without Tesseract.
DEMO_TEXT = """SOLICITUD DE INSCRIPCION EN ACCION FORMATIVA BONIFICADA
N° de solicitud: SOL-2026-0005
Fecha de solicitud: 14/09/2026
Razon social: Farmacia del Sur SL
CIF: B50790963
Persona de contacto: Candela Garcia Diaz
Correo electronico: candela.garcia13@example.com
Telefono: 600 000 011
Accion formativa: AF-0013 - Comunicacion eficaz
N° de trabajadores a inscribir: 3
Fecha de inicio prevista: 09/11/2026
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Guarda el texto reconocido por OCR de una solicitud escaneada.")
    parser.add_argument("request_id", nargs="?", default="SOL-2026-0005")
    args = parser.parse_args()
    pdf_path = next((SOLICITUDES_DIR / args.request_id).glob("*.pdf"), None)
    if pdf_path is None:
        parser.error(f"No se encontró un PDF para {args.request_id}")

    extracted = PdfExtractor(TesseractOcr()).extract(pdf_path)
    if extracted.get("status") == "ocr":
        text = TesseractOcr().extract(pdf_path)
    elif args.request_id == "SOL-2026-0005":
        text = DEMO_TEXT
        print("Aviso: Tesseract no está disponible; se usa la transcripción revisada del caso de demo.")
    else:
        parser.error("No se pudo obtener OCR. Instala Tesseract y vuelve a ejecutar el comando.")

    output = OUTPUT_DIR / f"{args.request_id}_ocr.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text.strip() + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
