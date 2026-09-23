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
            "Reescribe este correo en español con un tono claro, profesional y natural.\n"
            "Conserva exactamente la decisión, la empresa, la acción, las cifras, las fechas, "
            "los motivos y los requisitos. Puedes cambiar el saludo, el orden de las frases, "
            "la estructura de los párrafos, el tono y el asunto. No inventes información, "
            "no añadas promesas y no cambies el resultado de la solicitud.\n"
            "Devuelve únicamente un objeto JSON con las claves string subject y body.\n\n"
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
