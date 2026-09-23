import argparse
import html
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .request_extractor import RequestExtractor
from .services import (
    LmStudioClient,
    RegistrationService,
    ResponseRefiner,
    TrainingApiClient,
)


SOLICITUDES_DIR = (
    Path(__file__).resolve().parents[2].parent
    / "caso-solicitudes-documentales"
    / "solicitudes"
)


def available_requests() -> list[str]:
    if not SOLICITUDES_DIR.is_dir():
        return []
    return sorted(
        folder.name for folder in SOLICITUDES_DIR.iterdir() if folder.is_dir()
    )


def process_request(request_id: str, register: bool, use_lm: bool) -> dict:
    api = TrainingApiClient()
    refiner = ResponseRefiner(LmStudioClient()) if use_lm else None
    extractor = RequestExtractor(
        api_client=api,
        response_refiner=refiner,
        registration_service=RegistrationService(api),
        simulate_registration=not register,
    )
    return extractor.extract(SOLICITUDES_DIR / request_id)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_page(
    request_id: str,
    result: dict | None = None,
    error: str | None = None,
    use_lm: bool = False,
) -> str:
    request_ids = available_requests()
    options = "".join(
        f'<option value="{esc(item)}" {"selected" if item == request_id else ""}>'
        f"{esc(item)}</option>"
        for item in request_ids
    )
    content = render_result(result) if result else render_empty(error)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Awakelab · Tramitación</title>
  <style>
    :root {{
      --ink: #17211f; --muted: #65736e; --paper: #f4f6f1;
      --card: #ffffff; --line: #dbe3dc; --mint: #b9f3d0;
      --green: #147d58; --navy: #193936; --coral: #f08d70;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--paper); color: var(--ink);
      font: 15px/1.5 Inter, ui-sans-serif, system-ui, sans-serif; }}
    header {{ background: var(--navy); color: white; padding: 30px max(22px, calc((100vw - 1120px)/2)); }}
    .eyebrow {{ color: var(--mint); text-transform: uppercase; letter-spacing: .13em;
      font-size: 11px; font-weight: 800; }}
    h1 {{ margin: 8px 0 4px; font-size: clamp(28px, 4vw, 44px); letter-spacing: -.04em; }}
    header p {{ margin: 0; color: #c6d8d0; max-width: 650px; }}
    main {{ max-width: 1120px; margin: 24px auto 60px; padding: 0 22px; }}
    .toolbar, .card {{ background: var(--card); border: 1px solid var(--line);
      border-radius: 16px; box-shadow: 0 8px 26px #1939360b; }}
    .toolbar {{ padding: 16px; display: flex; gap: 12px; align-items: end; flex-wrap: wrap; }}
    label {{ display: grid; gap: 5px; color: var(--muted); font-size: 12px; font-weight: 700; }}
    select {{ min-width: 260px; border: 1px solid var(--line); border-radius: 9px;
      padding: 10px; color: var(--ink); background: white; font: inherit; }}
    button, .button {{ border: 0; border-radius: 9px; padding: 10px 15px; cursor: pointer;
      font: 700 14px inherit; text-decoration: none; display: inline-block; }}
    button.primary, .button.primary {{ background: var(--green); color: white; }}
    button.secondary, .button.secondary {{ background: #e7f5ec; color: var(--green); }}
    .actions {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .intro {{ margin: 24px 0 16px; display: flex; align-items: end; justify-content: space-between; gap: 16px; }}
    h2, h3 {{ margin: 0; letter-spacing: -.025em; }}
    h2 {{ font-size: 25px; }} h3 {{ font-size: 16px; }}
    .muted {{ color: var(--muted); }}
    .grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; }}
    .card {{ padding: 18px; grid-column: span 4; }}
    .card.wide {{ grid-column: span 8; }} .card.full {{ grid-column: 1 / -1; }}
    .metric {{ font-size: 30px; font-weight: 800; margin-top: 4px; }}
    .pill {{ display: inline-flex; border-radius: 99px; padding: 5px 10px; font-weight: 800;
      font-size: 12px; background: #e7f5ec; color: var(--green); }}
    .pill.deny {{ background: #fff0ed; color: #bd4d39; }}
    .pill.review {{ background: #fff6d8; color: #876514; }}
    .pill.docs {{ background: #edf0ff; color: #4b5e9c; }}
    .facts {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 14px; }}
    .fact span {{ display: block; color: var(--muted); font-size: 12px; }}
    .fact strong {{ display: block; margin-top: 2px; overflow-wrap: anywhere; }}
    ul {{ margin: 12px 0 0; padding-left: 20px; }}
    li + li {{ margin-top: 7px; }}
    .files {{ margin-top: 18px; border-top: 1px solid var(--line); padding-top: 14px; }}
    .section-label {{ display: block; color: var(--muted); font-size: 12px; font-weight: 800; margin-bottom: 8px; }}
    .file-list {{ display: grid; gap: 7px; }}
    .file-link {{ display: flex; justify-content: space-between; gap: 10px; padding: 9px 10px;
      border: 1px solid var(--line); border-radius: 9px; color: var(--ink); text-decoration: none; }}
    .file-link:hover {{ border-color: var(--green); background: #f2fbf5; }}
    .file-link b {{ color: var(--green); font-size: 12px; white-space: nowrap; }}
    .preview {{ margin-top: 10px; }}
    .preview summary {{ cursor: pointer; color: var(--green); font-weight: 800; font-size: 12px; }}
    .preview iframe {{ width: 100%; height: 420px; border: 1px solid var(--line); border-radius: 9px; margin-top: 8px; }}
    .card-heading {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
    pre {{ margin: 12px 0 0; padding: 14px; background: #17211f; color: #e7f5ec;
      border-radius: 10px; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 13px; }}
    .notice {{ padding: 17px; border-radius: 12px; background: #fff6d8; color: #725711; }}
    .error {{ background: #fff0ed; color: #8f3525; }}
    footer {{ max-width: 1120px; margin: 0 auto; padding: 0 22px 40px; color: var(--muted); font-size: 12px; }}
    @media (max-width: 780px) {{ .card, .card.wide {{ grid-column: 1 / -1; }} .toolbar {{ align-items: stretch; }} select {{ width: 100%; }} }}
  </style>
</head>
<body>
  <header><div class="eyebrow">Awakelab · prototipo local</div>
    <h1>Tramitación de solicitudes</h1>
    <p>Una vista rápida para probar extracción, validaciones, decisiones y registro.</p>
  </header>
  <main>
    <form class="toolbar" method="get">
      <label>Solicitud<select name="request_id">{options}</select></label>
      <div class="actions"><button class="primary" type="submit">Simular solicitud</button>
        <button class="secondary" type="submit" name="lm" value="1">Mejorar respuesta con LM Studio</button>
        <button class="secondary" type="submit" name="register" value="1">Registrar aprobada</button></div>
    </form>
    {content}
  </main>
  <footer>La simulación no escribe en la API mock. El registro real solo se ejecuta con el botón explícito.</footer>
</body></html>"""


def render_empty(error: str | None) -> str:
    if error:
        return f'<div class="notice error" style="margin-top:18px"><strong>No se pudo procesar la solicitud.</strong><br>{esc(error)}</div>'
    return '<div class="notice" style="margin-top:18px">Elige una solicitud para ver el resultado.</div>'


def render_result(request: dict) -> str:
    decision = request["decision"]
    status = decision["status"]
    pill_class = {"deny": "deny", "human_review": "review", "request_documents": "docs"}.get(status, "")
    validations = request.get("validations", [])
    validation_html = "".join(
        f"<li><strong>{esc(item.get('code'))}</strong>: {esc(item.get('message'))}</li>"
        for item in validations
    ) or "<li>No se han encontrado incidencias.</li>"
    draft = request.get("response_draft", {})
    registration = request.get("registration") or {}
    workers = request.get("worker_list", {})
    return f"""
    <div class="intro"><div><div class="eyebrow" style="color:var(--green)">Resultado</div>
      <h2>{esc(request['solicitud_id'])}</h2></div>
      <span class="pill {pill_class}">{esc(status)}</span></div>
    <section class="grid">
      <article class="card"><h3>Entrada</h3><div class="facts">
        <div class="fact"><span>PDF</span><strong>{esc(request['pdf'].get('file'))}</strong></div>
        <div class="fact"><span>Listado</span><strong>{esc(workers.get('file') or 'No encontrado')}</strong></div>
        <div class="fact"><span>Trabajadores</span><strong>{len(workers.get('workers', []))}</strong></div>
        <div class="fact"><span>PDF</span><strong>{esc(request['pdf'].get('status'))}</strong></div>
      </div><div class="files">{render_files(request)}</div></article>
      <article class="card wide"><h3>Por qué</h3><ul>{''.join(f'<li>{esc(reason)}</li>' for reason in decision.get('reasons', []))}</ul></article>
      <article class="card wide"><h3>Incidencias</h3><ul>{validation_html}</ul></article>
      <article class="card"><h3>Registro</h3><div class="metric">{esc(registration.get('status', 'n/a'))}</div><div class="muted">modo: {esc(registration.get('mode', 'n/a'))}</div></article>
      <article class="card full"><div class="card-heading"><h3>Borrador de respuesta</h3><span class="pill">{esc(draft.get('source', 'template'))}</span></div><pre>{esc(draft.get('body', ''))}</pre>{render_lm_note(draft)}</article>
    </section>"""


def render_files(request: dict) -> str:
    request_id = request["solicitud_id"]
    names = [name for name in request.get("files", []) if name != "mensaje.txt"]
    links = []
    for name in names:
        url = f"/file?request_id={esc(request_id)}&name={esc(name)}"
        label = "Abrir PDF" if name.lower().endswith(".pdf") else "Abrir archivo"
        links.append(f'<a class="file-link" href="{url}" target="_blank" rel="noreferrer"><span>{esc(name)}</span><b>{label} ↗</b></a>')
    preview = ""
    pdf = next((name for name in names if name.lower().endswith(".pdf")), None)
    if pdf:
        preview_url = f"/file?request_id={esc(request_id)}&name={esc(pdf)}"
        preview = f'<details class="preview"><summary>Vista previa del PDF</summary><iframe src="{preview_url}" title="Vista previa de {esc(pdf)}"></iframe></details>'
    return f'<div class="file-list"><span class="section-label">Archivos de esta solicitud</span>{"".join(links)}{preview}</div>'


def render_lm_note(draft: dict) -> str:
    if draft.get("refinement_error"):
        return f'<div class="notice" style="margin-top:12px">LM Studio no respondió. Se conserva la plantilla.<br><small>{esc(draft["refinement_error"])}</small></div>'
    if draft.get("source") == "lm_studio":
        return '<div class="muted" style="margin-top:10px">Texto refinado por LM Studio. La decisión no la toma el modelo.</div>'
    return '<div class="muted" style="margin-top:10px">Plantilla determinista. Usa el botón de LM Studio para probar el refinamiento local.</div>'


class UiHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/file":
            self.serve_file(parse_qs(urlparse(self.path).query))
            return
        query = parse_qs(urlparse(self.path).query)
        request_id = query.get("request_id", [available_requests()[0] if available_requests() else ""])[0]
        register = query.get("register", ["0"])[0] == "1"
        use_lm = query.get("lm", ["0"])[0] == "1"
        try:
            result = process_request(request_id, register, use_lm) if request_id else None
            page = render_page(request_id, result, use_lm=use_lm)
        except (FileNotFoundError, RuntimeError, KeyError) as error:
            page = render_page(request_id, error=str(error))
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, query: dict[str, list[str]]) -> None:
        request_id = query.get("request_id", [""])[0]
        filename = query.get("name", [""])[0]
        if not request_id or not filename or Path(filename).name != filename:
            self.send_error(400, "Archivo no válido")
            return
        path = (SOLICITUDES_DIR / request_id / filename).resolve()
        if not path.is_file() or SOLICITUDES_DIR.resolve() not in path.parents:
            self.send_error(404, "Archivo no encontrado")
            return
        content = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        disposition = "inline" if content_type == "application/pdf" else "attachment"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'{disposition}; filename="{path.name}"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Open the local visual test interface.")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), UiHandler)
    print(f"Interfaz local en http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
