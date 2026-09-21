class RequestValidator:
    dni_letters = "TRWAGMYFPDXBNJZSQVHLCKE"

    def validate(self, request: dict) -> list[dict]:
        validations = []
        pdf = request["pdf"]
        worker_list = request["worker_list"]

        if pdf["status"] == "scanned":
            validations.append(
                self._validation(
                    "pdf_scanned",
                    "warning",
                    "El PDF está escaneado y no se ha podido comparar.",
                )
            )
        else:
            self._compare_email_and_pdf(request["email"], pdf, validations)
            if worker_list["status"] == "found":
                declared = pdf["fields"]["trabajadores_declarados"]["value"]
                actual = len(worker_list["workers"])
                if declared != actual:
                    validations.append(
                        self._validation(
                            "pdf_worker_count_mismatch",
                            "blocking",
                            f"El PDF declara {declared} trabajadores y el listado contiene {actual}.",
                        )
                    )

        if worker_list["status"] == "missing":
            validations.append(
                self._validation(
                    "worker_list_missing",
                    "blocking",
                    "No se adjuntó un listado de trabajadores.",
                )
            )
        elif worker_list["status"] == "found":
            invalid_dnis = [
                worker["dni"]
                for worker in worker_list["workers"]
                if worker.get("dni") and not self._dni_is_valid(worker["dni"])
            ]
            if invalid_dnis:
                validations.append(
                    self._validation(
                        "invalid_worker_dni",
                        "blocking",
                        "Hay DNI con letra de control incorrecta: " + ", ".join(invalid_dnis) + ".",
                    )
                )

        return validations

    def _compare_email_and_pdf(self, email: dict, pdf: dict, validations: list[dict]) -> None:
        for name in ("empresa", "cif", "accion", "trabajadores_declarados"):
            email_field = email["fields"][name]
            pdf_field = pdf["fields"][name]
            if email_field and email_field["value"] != pdf_field["value"]:
                validations.append(
                    self._validation(
                        f"email_pdf_{name}_mismatch",
                        "blocking",
                        f"{name} no coincide entre el correo y el PDF.",
                    )
                )

    @staticmethod
    def _validation(code: str, severity: str, message: str) -> dict:
        return {"code": code, "severity": severity, "message": message}

    def _dni_is_valid(self, dni: str) -> bool:
        return (
            len(dni) == 9
            and dni[:8].isdigit()
            and dni[8].isalpha()
            and dni[8].upper() == self.dni_letters[int(dni[:8]) % 23]
        )
