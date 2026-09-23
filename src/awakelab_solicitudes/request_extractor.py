from pathlib import Path

from .extractors import EmailExtractor, PdfExtractor, TesseractOcr, WorkerListExtractor
from .services import (
    BusinessValidator,
    DecisionService,
    RegistrationService,
    RequestValidator,
    ResponseDrafter,
    ResponseRefiner,
    TrainingApiClient,
)


class RequestExtractor:
    def __init__(
        self,
        api_client: TrainingApiClient | None = None,
        response_refiner: ResponseRefiner | None = None,
        registration_service: RegistrationService | None = None,
        simulate_registration: bool = True,
    ) -> None:
        self.email_extractor = EmailExtractor()
        self.pdf_extractor = PdfExtractor(TesseractOcr())
        self.worker_list_extractor = WorkerListExtractor()
        self.validator = RequestValidator()
        self.decision_service = DecisionService()
        self.response_drafter = ResponseDrafter()
        self.response_refiner = response_refiner
        self.business_validator = BusinessValidator(api_client) if api_client else None
        self.registration_service = registration_service
        self.simulate_registration = simulate_registration

    def extract(self, folder: Path) -> dict:
        if not folder.is_dir():
            raise FileNotFoundError(f"No existe la solicitud: {folder.name}")

        pdf_files = list(folder.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"La solicitud {folder.name} no contiene un PDF.")

        request = {
            "solicitud_id": folder.name,
            "files": [
                file.name
                for file in sorted(folder.iterdir())
                if file.is_file() and not file.name.startswith("~$")
            ],
            "email": self.email_extractor.extract(folder / "mensaje.txt"),
            "pdf": self.pdf_extractor.extract(pdf_files[0]),
            "worker_list": self.worker_list_extractor.extract(folder),
        }
        request["validations"] = self.validator.validate(request)
        if self.business_validator:
            request["validations"].extend(self.business_validator.validate(request))
        request["decision"] = self.decision_service.decide(request["validations"])
        request["response_draft"] = self.response_drafter.draft(request)
        if self.response_refiner:
            request["response_draft"] = self.response_refiner.refine(
                request,
                request["response_draft"],
            )
        if self.registration_service:
            request["registration"] = self.registration_service.register(
                request,
                self.simulate_registration,
            )
        return request
