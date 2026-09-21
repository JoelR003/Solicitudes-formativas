import json

from .lm_studio import LmStudioClient


class ResponseDrafter:
    """Create review-ready response drafts from a decision."""

    def draft(self, request: dict) -> dict:
        company = self._value(request, "empresa") or "su empresa"
        contact = self._value(request, "contacto") or "equipo de formación"
        action = self._value(request, "accion") or "la acción solicitada"
        decision = request["decision"]
        reasons = "\n".join(f"- {reason}" for reason in decision["reasons"])
        subject = f"Solicitud {request['solicitud_id']} – "

        if decision["status"] == "approve":
            worker_count = len(request["worker_list"]["workers"])
            return {
                "subject": subject + "aprobada",
                "body": (
                    f"Hola {contact},\n\n"
                    f"Hemos aprobado la solicitud de {company} para {action}. "
                    f"La inscripción incluye {worker_count} trabajadores.\n\n"
                    "Un saludo,\nEquipo de Gestión de la Formación"
                ),
                "source": "template",
            }

        if decision["status"] == "request_documents":
            return {
                "subject": subject + "documentación pendiente",
                "body": (
                    f"Hola {contact},\n\n"
                    f"Hemos recibido la solicitud de {company} para {action}. "
                    "Para poder tramitarla necesitamos la siguiente documentación:\n"
                    f"{reasons}\n\n"
                    "Cuando la recibamos, continuaremos con la revisión.\n\n"
                    "Un saludo,\nEquipo de Gestión de la Formación"
                ),
                "source": "template",
            }

        if decision["status"] == "deny":
            return {
                "subject": subject + "no aprobada",
                "body": (
                    f"Hola {contact},\n\n"
                    f"No es posible tramitar la solicitud de {company} para {action} por los siguientes motivos:\n"
                    f"{reasons}\n\n"
                    "Un saludo,\nEquipo de Gestión de la Formación"
                ),
                "source": "template",
            }

        return {
            "subject": subject + "en revisión",
            "body": (
                f"Hola {contact},\n\n"
                f"Hemos recibido la solicitud de {company} para {action}. "
                "Hemos detectado una incidencia que requiere revisión manual:\n"
                f"{reasons}\n\n"
                "Nos pondremos en contacto cuando finalice la revisión.\n\n"
                "Un saludo,\nEquipo de Gestión de la Formación"
            ),
            "source": "template",
        }

    @staticmethod
    def _value(request: dict, field_name: str) -> str | None:
        pdf_field = request["pdf"]["fields"].get(field_name)
        if pdf_field:
            return pdf_field["value"]
        email_field = request["email"]["fields"].get(field_name)
        return email_field["value"] if email_field else None
class ResponseRefiner:
    """Optionally improve a template without changing the decision."""

    def __init__(self, client: LmStudioClient) -> None:
        self.client = client

    def refine(self, request: dict, draft: dict) -> dict:
        prompt = (
            "Rewrite this email draft in Spanish. Keep the decision and every factual reason exactly "
            "as provided. Do not add facts, promises, dates, requirements, or policy. Return only a "
            "JSON object with string keys subject and body.\n\n"
            + json.dumps(
                {"decision": request["decision"], "draft": draft},
                ensure_ascii=False,
            )
        )
        try:
            refined = self.client.rewrite(prompt)
            if not isinstance(refined.get("subject"), str) or not isinstance(refined.get("body"), str):
                raise ValueError("LM Studio did not return subject and body strings.")
            return {"subject": refined["subject"], "body": refined["body"], "source": "lm_studio"}
        except (RuntimeError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            return {**draft, "refinement_error": str(error)}
