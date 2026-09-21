from .api import TrainingApiClient


class BusinessValidator:
    """Check the extracted PDF data against the training system."""

    def __init__(self, api_client: TrainingApiClient) -> None:
        self.api_client = api_client

    def validate(self, request: dict) -> list[dict]:
        pdf = request["pdf"]
        if pdf["status"] == "scanned":
            return []

        fields = pdf["fields"]
        cif = fields["cif"]["value"]
        action_code = fields["accion"]["value"]
        company = self.api_client.get_company(cif)
        action = self.api_client.get_action(action_code)
        validations = []

        if company is None:
            validations.append(self._validation("company_not_registered", "La empresa no está registrada en el sistema."))
        elif not company["al_corriente"]:
            validations.append(self._validation("company_not_current", "La empresa no está al corriente de obligaciones."))

        if action is None:
            validations.append(self._validation("action_not_found", "La acción formativa no existe en el sistema."))
        elif action["estado"] != "abierta":
            validations.append(self._validation("action_not_open", "La acción formativa no admite inscripciones."))

        if company is None or not company["al_corriente"] or action is None or action["estado"] != "abierta":
            return validations

        worker_list = request["worker_list"]
        if worker_list["status"] == "found":
            requested = len(worker_list["workers"])
            available = action["plazas_libres"]
            if requested > available:
                validations.append(
                    self._validation(
                        "insufficient_seats",
                        f"La solicitud incluye {requested} trabajadores y quedan {available} plazas.",
                    )
                )

        enrollments = self.api_client.get_enrollments(cif, action_code)
        if enrollments:
            validations.append(
                self._validation(
                    "existing_enrollment",
                    "La empresa ya tiene una inscripción en esta acción.",
                )
            )

        return validations

    @staticmethod
    def _validation(code: str, message: str) -> dict:
        return {"code": code, "severity": "blocking", "message": message}
