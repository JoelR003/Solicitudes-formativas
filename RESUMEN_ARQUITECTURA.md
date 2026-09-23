# Resumen rápido de la arquitectura

La aplicación sigue este flujo:

```text
correo + PDF + Excel/Word
          ↓
      extracción
          ↓
    validaciones
          ↓
       decisión
          ↓
    borrador + registro
```

## Archivos importantes

| Archivo | Qué hace |
|---|---|
| `extract.py` | Punto de entrada para procesar una solicitud desde la terminal. |
| `request_extractor.py` | Coordina todo el flujo de una solicitud. |
| `extractors/email.py` | Extrae datos de `mensaje.txt`. |
| `extractors/pdf.py` | Extrae datos del PDF y coordina el OCR si está escaneado. |
| `extractors/ocr.py` | Adaptador opcional para Tesseract; si falla, mantiene la revisión humana. |
| `extractors/worker_list.py` | Lee el listado de trabajadores en Excel o Word. |
| `services/validation.py` | Compara los documentos y valida los DNI. |
| `services/business_validator.py` | Consulta empresa, acción, plazas e inscripciones en la API. |
| `services/decision.py` | Convierte las incidencias en `approve`, `deny`, `request_documents` o `human_review`. |
| `services/responses.py` | Genera el borrador y llama opcionalmente a LM Studio. |
| `services/registration.py` | Simula o crea el registro de las solicitudes aprobadas. |
| `services/api.py` | Encapsula las llamadas HTTP a la API mock. |
| `batch_processor.py` | Repite el mismo flujo para las 40 solicitudes y crea `summary.json`. |
| `demo_view.py` | Reduce la salida de la terminal cuando se usa `--brief`. |
| `web.py` | Sirve la interfaz local para probar solicitudes desde el navegador. |
| `tests/test_extract.py` | Comprueba extractores, validaciones, decisiones, API simulada y fallback del LLM. |

## Cómo se conectan

`RequestExtractor` es el coordinador. Llama a los tres extractores, reúne los datos, ejecuta los validadores, pasa las incidencias a `DecisionService`, genera el borrador y termina con `RegistrationService`.

`TrainingApiClient` es la única clase que habla directamente con la API mock. Así las validaciones y el registro no tienen que construir URLs ni gestionar cabeceras HTTP.

## Decisiones

La prioridad es:

1. Bloqueo de negocio → `deny`.
2. Contradicción o PDF escaneado → `human_review`.
3. Falta de documentación o DNI inválido → `request_documents`.
4. Sin incidencias → `approve`.

Las decisiones son deterministas. LM Studio solo mejora el texto del borrador y tiene fallback a la plantilla si falla.

## Registro

Las solicitudes no aprobadas nunca se registran. Las aprobadas usan simulación por defecto:

```powershell
uv run python -m awakelab_solicitudes.extract SOL-2026-0004 --brief
```

El registro real requiere `--register`:

```powershell
uv run python -m awakelab_solicitudes.extract SOL-2026-0004 --register --brief
```

## Frase para explicarlo

> “Separé la aplicación en extractores, validadores y servicios. Los extractores normalizan la información; los validadores comparan documentos y consultan la API; una clase central convierte las incidencias en una decisión; y solo las solicitudes aprobadas llegan al registro. LM Studio es opcional y únicamente mejora el borrador de respuesta.”
