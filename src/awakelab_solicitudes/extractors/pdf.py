import re
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

    def extract(self, path: Path) -> dict:
        text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
        return self.extract_text(text, path.name)

    def extract_text(self, text: str, filename: str) -> dict:
        if not text.strip():
            return {"status": "scanned", "file": filename, "fields": {}}

        action_line = self._value(text, "Acción formativa")
        action, course = action_line.split(" · ", 1) if action_line else (None, None)
        fields = {
            name: field(value, "pdf", label)
            for name, label in self.labels.items()
            if (value := self._value(text, label)) is not None
        }
        fields["accion"] = field(action, "pdf", "Acción formativa")
        fields["curso"] = field(course, "pdf", "Acción formativa")
        fields["trabajadores_declarados"]["value"] = int(fields["trabajadores_declarados"]["value"])
        return {"status": "text", "file": filename, "fields": fields}

    @staticmethod
    def _value(text: str, label: str) -> str | None:
        match = re.search(rf"^{re.escape(label)}:\s*(.+)$", text, re.MULTILINE)
        return match.group(1).strip() if match else None
