# Decisiones de automatización

Estas son las reglas que escogí para el prototipo. Quería automatizar lo que se puede comprobar con seguridad y dejar a una persona los casos en los que falta información o hay que interpretar documentos.

No quise que un modelo de lenguaje decidiera sobre una inscripción. Las decisiones salen de los datos extraídos y de reglas sencillas; el LLM, si se activa, solo reescribe el correo después de que la decisión esté tomada.

## Qué hace el programa en cada situación

| Situación | Decisión | Por qué |
|---|---|---|
| Los documentos cuadran, la empresa es válida, la acción está abierta, hay plazas y no hay inscripciones previas | `approve` | Se cumplen todas las comprobaciones disponibles. |
| Falta el listado de trabajadores | `request_documents` | Sin los DNI no se puede comprobar ni registrar a los participantes. |
| Un DNI tiene la letra de control inválida | `request_documents` | Pido corregir el listado antes de intentar el registro. |
| La empresa no está registrada o no está al corriente | `deny` | La API lo devuelve como un bloqueo objetivo. |
| La acción no existe, está cerrada, no tiene plazas o hay una inscripción previa | `deny` | No se podría tramitar aunque llegasen documentos adicionales. |
| El PDF está escaneado y OCR no obtiene datos suficientes | `human_review` | No tengo texto fiable que comparar con el correo y el listado. |
| Hay diferencias entre correo, PDF y listado | `human_review` | Prefiero que una persona decida qué dato es correcto antes que escoger uno automáticamente. |

Los bloqueos de negocio tienen prioridad. Si una acción ya está cerrada, no pido antes el documento que falta: esa solicitud no se puede aprobar de todas formas.

## De dónde salen los datos

- **Correo:** contexto inicial y contacto de la empresa.
- **PDF:** formulario presentado. Si es legible, de aquí tomo el CIF y la acción.
- **Excel o Word:** trabajadores, DNI, categoría y horas.
- **API mock:** confirma empresa, obligaciones, estado de la acción, plazas e inscripciones previas.

Guardo también la fuente y la ubicación de cada campo extraído. Si aparece una contradicción, el resultado indica dónde se encontró cada valor y no queda como una decisión opaca.

## PDF escaneados

Cuando el PDF no contiene texto, intento una lectura OCR local con Tesseract. Si obtiene los campos mínimos —empresa, CIF, acción y número de trabajadores—, el documento queda marcado como `ocr` y pasa por el mismo parser que un PDF normal. Si Tesseract no está instalado, falla o no obtiene datos suficientes, el resultado queda como `scanned` y la solicitud pasa a `human_review`.

La integración está aislada en `extractors/ocr.py`. Así puedo probar el flujo sin instalar el ejecutable en el entorno de tests y un fallo de OCR no bloquea el lote. Antes de producción mediría su precisión y revisaría los campos críticos antes de automatizar un registro.

## Uso de LM Studio

LM Studio aparece al final del flujo:

```text
datos y reglas -> decisión -> borrador de plantilla -> LM Studio opcional
```

El prompt recibe la decisión, los motivos y el borrador. Le permito cambiar el tono, el saludo, el orden de las frases y el asunto, pero debe conservar los hechos, las fechas, los requisitos y la decisión. Solo devuelve `subject` y `body` en español.

Si LM Studio no está disponible, tarda demasiado o devuelve algo que no se puede leer, conservo el borrador de plantilla y guardo el problema en `refinement_error`. El expediente no se queda bloqueado por el modelo.

## Registro y efectos externos

Solo intento registrar solicitudes aprobadas. El modo normal llama a `POST /inscripciones?simular=1`: la API revisa CIF, acción y DNI, pero no guarda nada. Para escribir en la API mock hay que añadir `--register`.

Las solicitudes no aprobadas aparecen como `skipped` y no hacen un POST de registro. Si la API rechaza una inscripción porque algo cambió entre la validación y el envío, el resultado queda como `failed` con el detalle que devuelve la API.

Tampoco envío correos: genero un borrador que una persona puede revisar. Antes de llevarlo a producción habría que decidir cómo evitar duplicados con varios procesos y qué hacer si el registro funciona pero el envío del correo falla, o al revés.
