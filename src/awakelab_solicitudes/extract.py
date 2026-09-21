import argparse
import json
from pathlib import Path

from .demo_view import brief_result
from .request_extractor import RequestExtractor
from .services import LmStudioClient, RegistrationService, ResponseRefiner, TrainingApiClient


SOLICITUDES_DIR = Path(__file__).resolve().parents[2].parent / "caso-solicitudes-documentales" / "solicitudes"

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract one request."
    )
    parser.add_argument(
        "request_id",
        help="For example: SOL-2026-0001",
    )
    parser.add_argument("--brief", action="store_true", help="Show the decision-focused view for a terminal demo.")
    parser.add_argument("--lm-studio", action="store_true", help="Refine the response draft with LM Studio.")
    parser.add_argument("--model", help="Optional LM Studio model identifier.")
    parser.add_argument("--register", action="store_true", help="Create the approved registration in the mock API.")
    args = parser.parse_args()

    refiner = ResponseRefiner(LmStudioClient(model=args.model)) if args.lm_studio else None
    api_client = TrainingApiClient()
    try:
        result = RequestExtractor(
            api_client,
            refiner,
            RegistrationService(api_client),
            simulate_registration=not args.register,
        ).extract(SOLICITUDES_DIR / args.request_id)
    except (FileNotFoundError, RuntimeError) as error:
        parser.error(str(error))

    print(
        json.dumps(
            brief_result(result) if args.brief else result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
