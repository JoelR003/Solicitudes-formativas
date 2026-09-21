class DecisionService:
    deny_codes = {
        "company_not_registered",
        "company_not_current",
        "action_not_found",
        "action_not_open",
        "insufficient_seats",
        "existing_enrollment",
    }
    review_codes = {
        "pdf_scanned",
        "email_pdf_empresa_mismatch",
        "email_pdf_cif_mismatch",
        "email_pdf_accion_mismatch",
        "email_pdf_trabajadores_declarados_mismatch",
        "pdf_worker_count_mismatch",
    }

    def decide(self, validations: list[dict]) -> dict:
        denied = self._with_codes(validations, self.deny_codes)
        if denied:
            return self._decision("deny", denied)

        review = self._with_codes(validations, self.review_codes)
        if review:
            return self._decision("human_review", review)

        documents_needed = self._with_codes(
            validations,
            {"worker_list_missing", "invalid_worker_dni"},
        )
        if documents_needed:
            return self._decision("request_documents", documents_needed)

        return {"status": "approve", "reasons": ["La solicitud supera todas las comprobaciones."]}

    @staticmethod
    def _with_codes(validations: list[dict], codes: set[str]) -> list[str]:
        return [validation["message"] for validation in validations if validation["code"] in codes]

    @staticmethod
    def _decision(status: str, reasons: list[str]) -> dict:
        return {"status": status, "reasons": reasons}
