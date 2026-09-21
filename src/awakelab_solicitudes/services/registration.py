from .api import ApiError, TrainingApiClient


class RegistrationService:
    """Register approved requests in simulation or explicit write mode."""

    def __init__(self, api_client: TrainingApiClient) -> None:
        self.api_client = api_client

    def register(self, request: dict, simulate: bool) -> dict:
        mode = "simulation" if simulate else "register"
        if request["decision"]["status"] != "approve":
            return {
                "mode": mode,
                "status": "skipped",
                "reason": "Only approved requests are registered.",
            }

        fields = request["pdf"]["fields"]
        worker_dnis = [worker["dni"] for worker in request["worker_list"]["workers"]]
        try:
            result = self.api_client.register_enrollment(
                fields["cif"]["value"],
                fields["accion"]["value"],
                worker_dnis,
                simulate,
            )
        except ApiError as error:
            return {
                "mode": mode,
                "status": "failed",
                "error": error.detail,
            }

        return {
            "mode": mode,
            "status": "simulated" if simulate else "registered",
            "result": result,
        }
