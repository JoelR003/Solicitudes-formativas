from pathlib import Path

import pytest

from awakelab_solicitudes.extractors import EmailExtractor, PdfExtractor, WorkerListExtractor
from awakelab_solicitudes.batch_processor import BatchProcessor
from awakelab_solicitudes.demo_view import brief_result
from awakelab_solicitudes.services import (
    BusinessValidator,
    DecisionService,
    LmStudioClient,
    RegistrationService,
    RequestValidator,
    ResponseDrafter,
    ResponseRefiner,
    TrainingApiClient,
)
from awakelab_solicitudes.request_extractor import RequestExtractor
from awakelab_solicitudes.web import render_page

def test_parse_email_extracts_the_main_values() -> None:
    result = EmailExtractor().extract_text(
        """De: Ana Pérez <ana@example.com>
Fecha: Mon, 14 Sep 2026 09:00:00 +0200
Asunto: Solicitud inscripción – Empresa Demo SL – AF-0008

Os remito la solicitud de inscripción de Empresa Demo SL (CIF B12345678)
en la acción AF-0008. Queremos inscribir a 4 trabajadores.
"""
    )["fields"]

    assert result["empresa"]["value"] == "Empresa Demo SL"
    assert result["cif"]["value"] == "B12345678"
    assert result["accion"]["value"] == "AF-0008"
    assert result["trabajadores_declarados"]["value"] == 4
    assert result["email_contacto"]["value"] == "ana@example.com"


def test_web_page_renders_decision_and_escapes_content() -> None:
    page = render_page(
        "SOL-2026-0004",
        {
            "solicitud_id": "SOL-2026-0004",
            "files": ["solicitud.pdf", "listado.xlsx"],
            "pdf": {"file": "solicitud.pdf", "status": "text"},
            "worker_list": {"file": "listado.xlsx", "workers": []},
            "decision": {"status": "approve", "reasons": ["Todo correcto"]},
            "validations": [],
            "response_draft": {"body": "Hola <empresa>"},
            "registration": {"status": "simulated", "mode": "simulation"},
        },
    )

    assert "SOL-2026-0004" in page
    assert "simulated" in page
    assert "Hola &lt;empresa&gt;" in page
    assert "/file?request_id=SOL-2026-0004&name=solicitud.pdf" in page
    assert "Mejorar respuesta con LM Studio" in page


def test_parse_email_extracts_people_declared_in_the_second_template() -> None:
    result = EmailExtractor().extract_text(
        """De: Irene Suárez <irene.suarez87@example.net>
Fecha: Mon, 14 Sep 2026 11:18:00 +0200
Asunto: Solicitud inscripción – Óptica Central SL – AF-0001

Desde Óptica Central SL queremos inscribir a 6 personas de nuestra plantilla
en la acción AF-0001.

Saludos,
Óptica Central SL · CIF B27041177
"""
    )["fields"]

    assert result["empresa"]["value"] == "Óptica Central SL"
    assert result["cif"]["value"] == "B27041177"
    assert result["accion"]["value"] == "AF-0001"
    assert result["trabajadores_declarados"]["value"] == 6


def test_parse_email_leaves_declared_people_empty_when_not_in_the_email() -> None:
    result = EmailExtractor().extract_text(
        """De: Leo Vázquez <leo.vazquez39@example.com>
Fecha: Mon, 14 Sep 2026 09:00:00 +0200
Asunto: Solicitud inscripción – Carpintería Imaginaria SA – AF-0008

Os remito la solicitud de inscripción de Carpintería Imaginaria SA
(CIF G32364358) en la acción formativa AF-0008.
"""
    )["fields"]

    assert result["empresa"]["value"] == "Carpintería Imaginaria SA"
    assert result["trabajadores_declarados"] is None


def test_parse_pdf_extracts_the_fixed_form_fields() -> None:
    result = PdfExtractor().extract_text(
        """Nº de solicitud: SOL-2026-0001
Fecha de solicitud: 14/09/2026
Razón social: Carpintería Imaginaria SA
CIF: A15413040
Persona de contacto: Leo Vázquez Molina
Correo electrónico: leo.vazquez39@example.com
Teléfono: 600 000 012
Acción formativa: AF-0008 · Liderazgo de equipos
Modalidad: teleformación
Nº de trabajadores a inscribir: 7
Fecha de inicio prevista: 21/10/2026
""",
        "solicitud.pdf",
    )["fields"]

    assert result["empresa"]["value"] == "Carpintería Imaginaria SA"
    assert result["accion"]["value"] == "AF-0008"
    assert result["curso"]["value"] == "Liderazgo de equipos"
    assert result["trabajadores_declarados"]["value"] == 7


def test_pdf_extractor_uses_ocr_for_a_scanned_pdf(monkeypatch, tmp_path: Path) -> None:
    import awakelab_solicitudes.extractors.pdf as pdf_module

    class EmptyReader:
        pages = []

    monkeypatch.setattr(pdf_module, "PdfReader", lambda path: EmptyReader())

    class FakeOcr:
        def extract(self, path: Path) -> str:
            return """Razón social: Demo SL
CIF: B12345678
Acción formativa: AF-0008 · Liderazgo de equipos
Nº de trabajadores a inscribir: 1
"""

    result = PdfExtractor(FakeOcr()).extract(tmp_path / "escaneado.pdf")

    assert result["status"] == "ocr"
    assert result["fields"]["cif"]["value"] == "B12345678"


def test_pdf_extractor_keeps_human_review_when_ocr_fails(monkeypatch, tmp_path: Path) -> None:
    import awakelab_solicitudes.extractors.pdf as pdf_module

    class EmptyReader:
        pages = []

    monkeypatch.setattr(pdf_module, "PdfReader", lambda path: EmptyReader())

    class BrokenOcr:
        def extract(self, path: Path) -> str:
            raise RuntimeError("Tesseract no disponible")

    extractor = PdfExtractor(BrokenOcr())
    result = extractor.extract(tmp_path / "escaneado.pdf")

    assert result["status"] == "scanned"
    assert result["fields"] == {}
    assert result["ocr_error"] == "Tesseract no disponible"


def test_worker_list_uses_the_five_columns_in_the_supplied_lists() -> None:
    result = WorkerListExtractor().from_rows(
        [
            ("DNI", "Nombre", "Apellidos", "Categoría profesional", "Horas"),
            ("10606068D", "Bruno", "Martínez Ortega", "Operario/a", 40),
        ],
        "excel",
        "listado_trabajadores.xlsx",
    )

    assert result["source"] == "excel"
    assert result["workers"] == [
        {
            "dni": "10606068D",
            "nombre": "Bruno Martínez Ortega",
            "categoria": "Operario/a",
            "horas": 40,
        }
    ]


def test_validator_reports_the_two_counted_discrepancies() -> None:
    request = {
        "email": {
            "fields": {
                "empresa": {"value": "Empresa Demo SL"},
                "cif": {"value": "B12345678"},
                "accion": {"value": "AF-0008"},
                "trabajadores_declarados": {"value": 4},
            }
        },
        "pdf": {
            "status": "text",
            "fields": {
                "empresa": {"value": "Empresa Demo SL"},
                "cif": {"value": "A12345678"},
                "accion": {"value": "AF-0008"},
                "trabajadores_declarados": {"value": 7},
            },
        },
        "worker_list": {
            "status": "found",
            "workers": [{}, {}, {}, {}, {}],
        },
    }

    validations = RequestValidator().validate(request)

    assert [validation["code"] for validation in validations] == [
        "email_pdf_cif_mismatch",
        "email_pdf_trabajadores_declarados_mismatch",
        "pdf_worker_count_mismatch",
    ]


def test_api_client_uses_the_three_read_only_routes() -> None:
    client = TrainingApiClient()
    calls = []

    def fake_get(path: str) -> dict | None:
        calls.append(path)
        if path.startswith("/empresas"):
            return {"cif": "B12345678", "al_corriente": True}
        if path.startswith("/acciones"):
            return {"codigo": "AF-0008", "plazas_libres": 12}
        return {"total": 0, "items": []}

    client._get = fake_get

    assert client.get_company("B12345678")["al_corriente"] is True
    assert client.get_action("AF-0008")["plazas_libres"] == 12
    assert client.get_enrollments("B12345678", "AF-0008") == []
    assert calls == [
        "/empresas/B12345678",
        "/acciones/AF-0008",
        "/inscripciones?cif=B12345678&accion=AF-0008",
    ]


def test_business_validator_checks_capacity_and_existing_enrollment() -> None:
    class FakeApi:
        def get_company(self, cif: str) -> dict:
            return {"cif": cif, "al_corriente": True}

        def get_action(self, code: str) -> dict:
            return {"codigo": code, "estado": "abierta", "plazas_libres": 2}

        def get_enrollments(self, cif: str, code: str) -> list[dict]:
            return [{"cif": cif, "accion": code}]

    request = {
        "pdf": {
            "status": "text",
            "fields": {
                "cif": {"value": "B12345678"},
                "accion": {"value": "AF-0008"},
            },
        },
        "worker_list": {"status": "found", "workers": [{}, {}, {}]},
    }

    validations = BusinessValidator(FakeApi()).validate(request)

    assert [validation["code"] for validation in validations] == [
        "insufficient_seats",
        "existing_enrollment",
    ]


def test_business_validator_stops_after_company_or_action_is_not_eligible() -> None:
    class FakeApi:
        def get_company(self, cif: str) -> None:
            return None

        def get_action(self, code: str) -> dict:
            return {"codigo": code, "estado": "cerrada", "plazas_libres": 2}

        def get_enrollments(self, cif: str, code: str) -> list[dict]:
            raise AssertionError("This request should not be made")

    request = {
        "pdf": {
            "status": "text",
            "fields": {
                "cif": {"value": "B12345678"},
                "accion": {"value": "AF-0008"},
            },
        },
        "worker_list": {"status": "found", "workers": []},
    }

    validations = BusinessValidator(FakeApi()).validate(request)

    assert [validation["code"] for validation in validations] == [
        "company_not_registered",
        "action_not_open",
    ]


def test_decision_service_uses_the_document_routes() -> None:
    service = DecisionService()

    assert service.decide([])["status"] == "approve"
    assert service.decide(
        [{"code": "worker_list_missing", "message": "No se adjuntó un listado."}]
    )["status"] == "request_documents"
    assert service.decide(
        [{"code": "pdf_scanned", "message": "El PDF está escaneado."}]
    )["status"] == "human_review"
    assert service.decide(
        [{"code": "invalid_worker_dni", "message": "Hay DNI inválidos."}]
    )["status"] == "request_documents"


def test_decision_service_denies_before_requesting_documents() -> None:
    decision = DecisionService().decide(
        [
            {"code": "worker_list_missing", "message": "No se adjuntó un listado."},
            {"code": "action_not_open", "message": "La acción está cerrada."},
        ]
    )

    assert decision == {
        "status": "deny",
        "reasons": ["La acción está cerrada."],
    }


def test_response_drafter_creates_an_approval_draft() -> None:
    request = {
        "solicitud_id": "SOL-2026-0003",
        "email": {"fields": {"empresa": None, "contacto": None, "accion": None}},
        "pdf": {
            "fields": {
                "empresa": {"value": "Óptica Central SL"},
                "contacto": {"value": "Irene Suárez Navarro"},
                "accion": {"value": "AF-0001"},
            }
        },
        "worker_list": {"workers": [{}, {}, {}, {}, {}, {}]},
        "decision": {"status": "approve", "reasons": ["La solicitud supera todas las comprobaciones."]},
    }

    draft = ResponseDrafter().draft(request)

    assert draft["subject"] == "Solicitud SOL-2026-0003 – aprobada"
    assert "Óptica Central SL" in draft["body"]
    assert "6 trabajadores" in draft["body"]


def test_response_drafter_includes_the_denial_reason() -> None:
    request = {
        "solicitud_id": "SOL-2026-0004",
        "email": {"fields": {"empresa": {"value": "Empresa Demo"}, "contacto": None, "accion": None}},
        "pdf": {"fields": {}},
        "worker_list": {"workers": []},
        "decision": {"status": "deny", "reasons": ["La acción formativa no admite inscripciones."]},
    }

    draft = ResponseDrafter().draft(request)

    assert draft["subject"] == "Solicitud SOL-2026-0004 – no aprobada"
    assert "La acción formativa no admite inscripciones." in draft["body"]


def test_response_refiner_uses_lm_studio_output_when_valid() -> None:
    class FakeClient:
        def rewrite(self, prompt: str) -> dict:
            assert "action_not_open" in prompt
            assert "Puedes cambiar el saludo" in prompt
            assert "No inventes información" in prompt
            return {"subject": "Solicitud no aprobada", "body": "Hola, la acción está cerrada."}

    request = {"decision": {"status": "deny", "reasons": ["La acción está cerrada."], "code": "action_not_open"}}
    draft = {"subject": "Plantilla", "body": "Texto", "source": "template"}

    refined = ResponseRefiner(FakeClient()).refine(request, draft)

    assert refined == {
        "subject": "Solicitud no aprobada",
        "body": "Hola, la acción está cerrada.",
        "source": "lm_studio",
    }


def test_response_refiner_keeps_the_template_when_lm_studio_fails() -> None:
    class FakeClient:
        def rewrite(self, prompt: str) -> dict:
            raise RuntimeError("LM Studio is not running")

    draft = {"subject": "Plantilla", "body": "Texto", "source": "template"}
    refined = ResponseRefiner(FakeClient()).refine({"decision": {}}, draft)

    assert refined["subject"] == "Plantilla"
    assert refined["source"] == "template"
    assert "LM Studio is not running" in refined["refinement_error"]


def test_response_refiner_keeps_the_template_when_lm_studio_times_out() -> None:
    class SlowClient:
        def rewrite(self, prompt: str) -> dict:
            raise TimeoutError("LM Studio took too long")

    draft = {"subject": "Plantilla", "body": "Texto", "source": "template"}

    refined = ResponseRefiner(SlowClient()).refine({"decision": {}}, draft)

    assert refined["subject"] == "Plantilla"
    assert refined["source"] == "template"
    assert "took too long" in refined["refinement_error"]


def test_lm_studio_stream_keeps_content_and_ignores_reasoning() -> None:
    lines = [
        b'data: {"choices":[{"delta":{"reasoning_content":"Thinking"}}]}\n',
        b'data: {"choices":[{"delta":{"content":"{\\"subject\\": \\"Hola\\","}}]}\n',
        b'data: {"choices":[{"delta":{"content":" \\"body\\": \\"Texto\\"}"}}]}\n',
        b"data: [DONE]\n",
    ]

    content = LmStudioClient._content_from_stream(lines)

    assert content == '{"subject": "Hola", "body": "Texto"}'


def test_batch_processor_summarises_decisions_and_manual_reviews() -> None:
    requests = [
        {
            "solicitud_id": "SOL-2026-0001",
            "validations": [],
            "decision": {"status": "approve", "reasons": ["Correcta."]},
        },
        {
            "solicitud_id": "SOL-2026-0002",
            "validations": [{"code": "pdf_scanned"}],
            "decision": {"status": "human_review", "reasons": ["PDF escaneado."]},
        },
    ]

    summary = BatchProcessor._summary(requests)

    assert summary["decisions"] == {"approve": 1, "human_review": 1}
    assert summary["validation_codes"] == {"pdf_scanned": 1}
    assert summary["needs_human_review"] == [
        {"solicitud_id": "SOL-2026-0002", "reasons": ["PDF escaneado."]}
    ]


def test_api_client_sends_the_registration_payload() -> None:
    client = TrainingApiClient()
    calls = []

    def fake_post(path: str, data: dict) -> dict:
        calls.append((path, data))
        return {"ok": True, "simulado": True}

    client._post = fake_post

    result = client.register_enrollment(
        "B12345678",
        "AF-0008",
        ["12345678Z"],
        simulate=True,
    )

    assert result == {"ok": True, "simulado": True}
    assert calls == [
        (
            "/inscripciones?simular=1",
            {
                "cif": "B12345678",
                "accion": "AF-0008",
                "trabajadores": ["12345678Z"],
            },
        )
    ]


def test_registration_service_simulates_or_registers_only_approved_requests() -> None:
    class FakeApi:
        def __init__(self) -> None:
            self.calls = []

        def register_enrollment(self, cif, action, dnis, simulate) -> dict:
            self.calls.append((cif, action, dnis, simulate))
            return {"id": 1}

    request = {
        "decision": {"status": "approve"},
        "pdf": {
            "fields": {
                "cif": {"value": "B12345678"},
                "accion": {"value": "AF-0008"},
            }
        },
        "worker_list": {"workers": [{"dni": "12345678Z"}]},
    }
    api = FakeApi()
    service = RegistrationService(api)

    simulated = service.register(request, simulate=True)
    registered = service.register(request, simulate=False)
    skipped = service.register({"decision": {"status": "deny"}}, simulate=False)

    assert simulated["status"] == "simulated"
    assert registered["status"] == "registered"
    assert skipped["status"] == "skipped"
    assert api.calls == [
        ("B12345678", "AF-0008", ["12345678Z"], True),
        ("B12345678", "AF-0008", ["12345678Z"], False),
    ]


def test_validator_reports_invalid_worker_dnis() -> None:
    request = {
        "email": {"fields": {"empresa": None, "cif": None, "accion": None, "trabajadores_declarados": None}},
        "pdf": {
            "status": "text",
            "fields": {
                "empresa": {"value": "Empresa Demo"},
                "cif": {"value": "B12345678"},
                "accion": {"value": "AF-0008"},
                "trabajadores_declarados": {"value": 1},
            },
        },
        "worker_list": {"status": "found", "workers": [{"dni": "12345678A"}]},
    }

    validations = RequestValidator().validate(request)

    assert validations[-1]["code"] == "invalid_worker_dni"


def test_brief_result_keeps_the_information_needed_for_a_demo() -> None:
    request = {
        "solicitud_id": "SOL-2026-0001",
        "pdf": {"file": "solicitud.pdf"},
        "worker_list": {"file": "listado.xlsx", "workers": [{}, {}]},
        "validations": [{"code": "pdf_scanned"}],
        "decision": {"status": "human_review"},
        "response_draft": {"subject": "En revisión"},
        "registration": {"status": "skipped"},
    }

    result = brief_result(request)

    assert result["inputs"] == {
        "pdf": "solicitud.pdf",
        "worker_list": "listado.xlsx",
        "worker_count": 2,
    }
    assert "email" not in result
    assert result["decision"] == {"status": "human_review"}


def test_request_extractor_explains_when_a_request_folder_is_missing() -> None:
    with pytest.raises(FileNotFoundError, match="No existe la solicitud: SOL-2026-9999"):
        RequestExtractor().extract(Path("SOL-2026-9999"))
