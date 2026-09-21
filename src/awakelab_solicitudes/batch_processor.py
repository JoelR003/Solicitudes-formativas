import json
from collections import Counter
from pathlib import Path

from .request_extractor import RequestExtractor


class BatchProcessor:
    def __init__(self, request_extractor: RequestExtractor) -> None:
        self.request_extractor = request_extractor

    def process(self, requests_dir: Path, output_dir: Path) -> dict:
        output_dir.mkdir(exist_ok=True)
        requests = []

        for folder in sorted(requests_dir.iterdir()):
            if not folder.is_dir():
                continue
            request = self.request_extractor.extract(folder)
            requests.append(request)
            self._write_json(output_dir / f"{folder.name}.json", request)

        summary = self._summary(requests)
        self._write_json(output_dir / "summary.json", summary)
        return summary

    @staticmethod
    def _summary(requests: list[dict]) -> dict:
        decisions = Counter(request["decision"]["status"] for request in requests)
        validation_codes = Counter(
            validation["code"]
            for request in requests
            for validation in request["validations"]
        )
        registrations = Counter(
            request["registration"]["status"]
            for request in requests
            if "registration" in request
        )
        needs_human_review = [
            {
                "solicitud_id": request["solicitud_id"],
                "reasons": request["decision"]["reasons"],
            }
            for request in requests
            if request["decision"]["status"] == "human_review"
        ]

        return {
            "total_requests": len(requests),
            "decisions": dict(decisions),
            "validation_codes": dict(validation_codes),
            "registrations": dict(registrations),
            "needs_human_review": needs_human_review,
        }

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
