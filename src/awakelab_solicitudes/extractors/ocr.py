from pathlib import Path


class OcrError(RuntimeError):
    """Indica que no se puede ejecutar el OCR local."""


class TesseractOcr:
    """Convierte las páginas y las pasa al Tesseract instalado localmente."""

    def extract(self, path: Path) -> str:
        try:
            from pdf2image import convert_from_path
            import pytesseract
        except ImportError as error:
            raise OcrError(
                "OCR necesita las dependencias opcionales pdf2image y pytesseract."
            ) from error

        # Windows may install Tesseract without refreshing the current shell PATH.
        default_windows_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if default_windows_path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(default_windows_path)

        try:
            pages = convert_from_path(path, dpi=200)
            return "\n".join(
                pytesseract.image_to_string(page, lang="spa+eng") for page in pages
            )
        except Exception as error:
            raise OcrError(f"No se pudo ejecutar Tesseract: {error}") from error
