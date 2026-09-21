import re
from pathlib import Path

from .fields import field


class EmailExtractor:
    cif_re = re.compile(r"\b([ABCDEFGHJNPQRSUVW]\d{8})\b", re.IGNORECASE)
    workers_re = re.compile(r"inscribir a (\d+) (?:personas|trabajadores)", re.IGNORECASE)

    def extract(self, path: Path) -> dict:
        return self.extract_text(path.read_text(encoding="utf-8"))

    def extract_text(self, message: str) -> dict:
        sender = self._header(message, "De") or ""
        subject = self._header(message, "Asunto") or ""
        body = message.split("\n\n", 1)[-1]
        sender_match = re.match(r"(.+?)\s*<([^>]+)>", sender)
        subject_match = re.match(r"Solicitud inscripción\s*[–-]\s*(.+?)\s*[–-]\s*(AF-\d{4})$", subject, re.IGNORECASE)
        cif_match = self.cif_re.search(body)
        workers_match = self.workers_re.search(body)
        company = subject_match.group(1).strip() if subject_match else None
        action = subject_match.group(2) if subject_match else None

        return {
            "subject": subject or None,
            "sent_at": self._header(message, "Fecha"),
            "fields": {
                "empresa": field(company, "email", "header: Asunto") if company else None,
                "cif": field(cif_match.group(1).upper(), "email", "body") if cif_match else None,
                "accion": field(action, "email", "header: Asunto") if action else None,
                "contacto": field(sender_match.group(1).strip(), "email", "header: De") if sender_match else None,
                "email_contacto": field(sender_match.group(2).strip(), "email", "header: De") if sender_match else None,
                "trabajadores_declarados": field(int(workers_match.group(1)), "email", "body") if workers_match else None,
            },
        }

    @staticmethod
    def _header(message: str, name: str) -> str | None:
        match = re.search(rf"^{name}:\s*(.+)$", message, re.MULTILINE)
        return match.group(1).strip() if match else None
