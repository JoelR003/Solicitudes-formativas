import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .fields import field


class PdfExtractor:
    labels = {
        "solicitud_id": "Nº de solicitud",
        "fecha_solicitud": "Fecha de solicitud",
        "empresa": "Razón social",
        "cif": "CIF",
        "contacto": "Persona de contacto",
        "email_contacto": "Correo electrónico",
        "telefono": "Teléfono",
        "modalidad": "Modalidad",
        "trabajadores_declarados": "Nº de trabajadores a inscribir",
        "fecha_inicio": "Fecha de inicio prevista",
    }

    def __init__(self, ocr=None) -> None:
        self.ocr = ocr

    def extract(self, path: Path) -> dict:
        text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
        if not text.strip() and self.ocr:
            try:
                text = self.ocr.extract(path)
            except Exception as error:
                return {
                    "status": "scanned",
                    "file": path.name,
                    "fields": {},
                    "ocr_error": str(error),
                }
            if text.strip():
                result = self.extract_text(text, path.name, status="ocr")
                required = ("empresa", "cif", "accion", "trabajadores_declarados")
                if all(result["fields"].get(name) for name in required):
                    return result
                result["status"] = "scanned"
                result["ocr_error"] = "OCR no extrajo todos los campos necesarios."
                return result
        return self.extract_text(text, path.name)

    def extract_text(self, text: str, filename: str, status: str = "text") -> dict:
        if not text.strip():
            return {"status": "scanned", "file": filename, "fields": {}}

        action_line = self._value(text, "Acción formativa")
        action, course = re.split(r"\s+[·-]\s+", action_line, maxsplit=1) if action_line and re.search(r"\s+[·-]\s+", action_line) else (action_line, None)
        fields = {
            name: field(value, "pdf", label)
            for name, label in self.labels.items()
            if (value := self._value(text, label)) is not None
        }
        fields["accion"] = field(action, "pdf", "Acción formativa")
        fields["curso"] = field(course, "pdf", "Acción formativa")
        if fields.get("trabajadores_declarados"):
            fields["trabajadores_declarados"]["value"] = int(fields["trabajadores_declarados"]["value"])
        return {"status": status, "file": filename, "fields": fields}

    @staticmethod
    def _value(text: str, label: str) -> str | None:
        expected = PdfExtractor._normalise(label)
        for line in text.splitlines():
            if ":" not in line:
                continue
            candidate, value = line.split(":", 1)
            normalised = PdfExtractor._normalise(candidate)
            fuzzy_match = (
                ("solicitud" in expected and "solicitud" in normalised)
                or ("trabajadores" in expected and "trabajadores" in normalised)
                or ("correo" in expected and "correo" in normalised and "electron" in normalised)
                or ("accion" in expected and normalised.startswith("acci") and "formativa" in normalised)
            )
            if normalised == expected or fuzzy_match:
                return value.strip()
        return None

    @staticmethod
    def _normalise(value: str) -> str:
        value = value.replace("�", "º")
        value = unicodedata.normalize("NFKD", value)
        return "".join(char for char in value if not unicodedata.combining(char)).lower().strip()
