import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class ApiError(RuntimeError):
    def __init__(self, status: int, detail: dict) -> None:
        self.status = status
        self.detail = detail
        super().__init__(detail.get("error", "API request failed"))


class TrainingApiClient:
    """Small client for the training management mock API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8092",
        api_key: str = "boxes-demo-2026",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.last_request_at = 0.0

    def get_company(self, cif: str) -> dict | None:
        return self._get(f"/empresas/{quote(cif)}")

    def get_action(self, code: str) -> dict | None:
        """Return the action together with plazas_ocupadas and plazas_libres."""

        return self._get(f"/acciones/{quote(code)}")

    def get_enrollments(self, cif: str, action_code: str) -> list[dict]:
        query = urlencode({"cif": cif, "accion": action_code})
        response = self._get(f"/inscripciones?{query}")
        return response["items"]

    def register_enrollment(
        self,
        cif: str,
        action_code: str,
        worker_dnis: list[str],
        simulate: bool,
    ) -> dict:
        path = "/inscripciones?simular=1" if simulate else "/inscripciones"
        return self._post(
            path,
            {"cif": cif, "accion": action_code, "trabajadores": worker_dnis},
        )

    def _get(self, path: str) -> dict | None:
        self._wait_for_rate_limit()
        request = Request(
            f"{self.base_url}{path}",
            headers={"X-Api-Key": self.api_key},
        )
        try:
            with urlopen(request, timeout=5) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 404:
                return None
            detail = error.read().decode("utf-8")
            raise RuntimeError(f"API request failed: {error.code} {detail}") from error
        except URLError as error:
            raise RuntimeError(
                "No se puede conectar con la API mock. Iníciala con: "
                "uv run python ..\\caso-solicitudes-documentales\\mock_api\\servidor.py"
            ) from error

    def _post(self, path: str, data: dict) -> dict:
        self._wait_for_rate_limit()
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(data).encode("utf-8"),
            headers={
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=5) as response:
                return json.load(response)
        except HTTPError as error:
            detail = json.loads(error.read().decode("utf-8"))
            raise ApiError(error.code, detail) from error
        except URLError as error:
            raise RuntimeError(
                "No se puede conectar con la API mock. Iníciala con: "
                "uv run python ..\\caso-solicitudes-documentales\\mock_api\\servidor.py"
            ) from error

    def _wait_for_rate_limit(self) -> None:
        wait = 0.11 - (time.monotonic() - self.last_request_at)
        if wait > 0:
            time.sleep(wait)
        self.last_request_at = time.monotonic()
