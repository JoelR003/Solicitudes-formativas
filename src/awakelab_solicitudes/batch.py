import argparse
from pathlib import Path

from .batch_processor import BatchProcessor
from .request_extractor import RequestExtractor
from .services import LmStudioClient, RegistrationService, ResponseRefiner, TrainingApiClient


SOLICITUDES_DIR = Path(__file__).resolve().parents[2].parent / "caso-solicitudes-documentales" / "solicitudes"


def main() -> None:
    parser = argparse.ArgumentParser(description="Process all requests.")
    parser.add_argument("--output", default="output", help="Folder for JSON results.")
    parser.add_argument("--lm-studio", action="store_true", help="Refine response drafts with LM Studio.")
    parser.add_argument("--model", help="Optional LM Studio model identifier.")
    parser.add_argument("--register", action="store_true", help="Create approved registrations in the mock API.")
    args = parser.parse_args()

    refiner = ResponseRefiner(LmStudioClient(model=args.model)) if args.lm_studio else None
    api_client = TrainingApiClient()
    extractor = RequestExtractor(
        api_client,
        refiner,
        RegistrationService(api_client),
        simulate_registration=not args.register,
    )
    try:
        summary = BatchProcessor(extractor).process(SOLICITUDES_DIR, Path(args.output))
    except (FileNotFoundError, RuntimeError) as error:
        parser.error(str(error))
    print(summary)


if __name__ == "__main__":
    main()
