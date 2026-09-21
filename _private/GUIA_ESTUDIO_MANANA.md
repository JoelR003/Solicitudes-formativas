# Guía privada para la conversación con Santiago

> **No entregar:** borra la carpeta `_private/` antes de crear el zip final. Es una guía de preparación personal.

## 1. La idea central en 30 segundos

Construí un prototipo pequeño que automatiza los casos claros y devuelve a una persona los que requieren criterio. Lee el correo, el PDF y el listado de trabajadores; conserva el origen de los datos; consulta la API mock como fuente de verdad; aplica reglas explícitas; genera un borrador y simula el registro. El LLM es opcional y solo mejora la redacción después de tomar la decisión.

## 2. Demo: orden y comandos

### Antes de la reunión

1. Abre una terminal en el proyecto.
2. Comprueba las pruebas:

```powershell
uv run pytest tests
```

3. En otra terminal, inicia la API mock:

```powershell
uv run python ..\caso-solicitudes-documentales\mock_api\servidor.py
```

4. Opcional: abre LM Studio, carga `qwen/qwen3.5-9b`, activa el servidor local y deja **Enable Thinking** en `Off`.

### Durante los primeros 10 minutos

1. **Presenta el mapa del proyecto.**
   - `extractors/`: lee correo, PDF y Excel/Word.
   - `services/`: API, validación, decisión, respuesta, registro y LM Studio.
   - `request_extractor.py`: orquesta una solicitud.
   - `batch_processor.py`: procesa las 40 y genera el resumen.

2. **Caso aprobado: SOL-2026-0004.**

```powershell
uv run python -m awakelab_solicitudes.extract SOL-2026-0004 --brief
```

Di: “Es un caso sin incidencias. Se extraen los tres documentos, se consulta la empresa, la acción, las plazas y las inscripciones. La regla devuelve `approve` y la API valida el registro en simulación.”

3. **Caso que necesita persona: SOL-2026-0005.**

```powershell
uv run python -m awakelab_solicitudes.extract SOL-2026-0005 --brief
```

Di: “No monté OCR porque el enunciado no lo pedía. Si no puedo leer el PDF de forma fiable, no intento inferir datos: lo marco como `scanned` y lo derivo a revisión humana.”

4. **Contradicción documental: SOL-2026-0001.**

```powershell
uv run python -m awakelab_solicitudes.extract SOL-2026-0001 --brief
```

Di: “El CIF del correo y el formulario no coinciden. No elijo automáticamente uno de los dos porque podría registrar a la empresa equivocada.”

Si te pide un ejemplo de **documentación pendiente**, usa `SOL-2026-0003`: sus dos DNI no pasan la letra de control, por lo que el sistema pide un listado corregido y no intenta registrar.

```powershell
uv run python -m awakelab_solicitudes.extract SOL-2026-0003 --brief
```

Si te pide un ejemplo de **denegación objetiva**, usa `SOL-2026-0018`.

```powershell
uv run python -m awakelab_solicitudes.extract SOL-2026-0018 --brief
```

5. **Resumen del lote.**

```powershell
uv run python -m awakelab_solicitudes.batch
```

Resultado de referencia:

| Resultado | Número |
|---|---:|
| Total | 40 |
| Aprobadas | 13 |
| Documentación pendiente | 5 |
| Denegadas | 9 |
| Revisión humana | 13 |
| Registros simulados | 13 |
| Fallos de simulación | 0 |

No ejecutes `--register` en la demo salvo que te lo pidan: la simulación demuestra el payload sin modificar el estado de la API.

## 3. Flujo que debes poder explicar

```text
correo + PDF + Excel/Word
          ↓
datos con fuente y ubicación
          ↓
validaciones documentales
          ↓
consultas a API mock
          ↓
validaciones de negocio
          ↓
decisión determinista
          ↓
plantilla de respuesta → LM Studio opcional
          ↓
simulación o registro si se aprobó
```

## 4. Decisiones importantes y por qué

### Reglas, no LLM, para decidir

Las decisiones de negocio deben ser repetibles y auditables. La API es la fuente oficial para empresa, estado, plazas e inscripciones. Una respuesta probabilística no debe aprobar una inscripción.

### Fuentes de datos

| Dato | Fuente usada | Por qué |
|---|---|---|
| Contacto y contexto inicial | Correo | Es el canal de la solicitud. |
| CIF y acción para validar/registrar | PDF legible | Es el formulario presentado. |
| Trabajadores y DNI | Excel o Word | Es el listado real de participantes. |
| Empresa, acción, plazas, inscripción previa | API | Es la fuente de verdad operativa. |

### Prioridad de decisiones

1. `deny`: empresa no válida, acción no disponible, plazas insuficientes o inscripción previa.
2. `human_review`: PDF escaneado o contradicción entre documentos.
3. `request_documents`: listado ausente o DNI inválido.
4. `approve`: no hay incidencias.

Justificación de la prioridad: si una acción está cerrada, pedir otro documento no resolvería el problema; por eso prevalece una denegación objetiva.

### Escaneados

Se marcan como `scanned` y pasan a `human_review`. No hay OCR porque no era obligatorio y añadirlo habría incrementado dependencia, coste y superficie de error para un prototipo de cinco horas.

## 5. Uso del LLM

### Qué hace

Solo reescribe el asunto y cuerpo de un borrador ya creado. Recibe decisión, motivos y plantilla. Devuelve `subject` y `body`.

### Qué no hace

No extrae, no valida, no decide, no consulta la API, no registra y no envía correos.

### Conexión

- Local: `http://127.0.0.1:1234/v1`.
- `GET /models`: encuentra el modelo cargado.
- `POST /chat/completions`: envía el borrador.
- Streaming: acumula solo `content`, ignora `reasoning_content`.
- Qwen: desactivar **Enable Thinking** para respuestas breves; si no, puede gastar el límite en razonamiento interno.

### Si falla

Se conserva el borrador determinista y se guarda `refinement_error`. El caso no se bloquea y el LLM no puede alterar el resultado de negocio.

Comando opcional:

```powershell
uv run python -m awakelab_solicitudes.extract SOL-2026-0004 --brief --lm-studio
```

## 6. Preguntas probables y respuestas breves

### “¿Por qué no OCR?”

“El enunciado no lo exige. Preferí un comportamiento seguro: revisión humana. Antes de producción mediría volumen, calidad y coste de los escaneados para decidir si OCR compensa.”

### “¿Por qué no usas un LLM para extraer todo?”

“Los documentos entregados tienen estructuras conocidas. Con reglas simples consigo resultados trazables: cada valor conserva fuente y ubicación. En producción evaluaría OCR o extracción asistida para formatos nuevos, pero con validación humana y métricas de precisión.”

### “¿Por qué simulación por defecto?”

“Evita modificar estado durante pruebas y permite verificar exactamente el mismo payload. La escritura real existe tras `--register`, así que la decisión está explícita.”

### “¿Qué ocurre si cambia una plaza tras validarla?”

“El POST puede devolver un error; el resultado se guarda como `failed`. En producción añadiría idempotencia, reintentos controlados y una cola para resolver esa concurrencia.”

### “¿Qué pasa con un duplicado?”

“Antes de registrar consulto inscripciones previas. En un sistema concurrente esa comprobación no basta por sí sola: necesitaría una clave de idempotencia o una restricción transaccional en el sistema de gestión.”

### “¿Qué pasa si el PDF y el correo discrepan?”

“No selecciono una fuente arbitrariamente. Lo derivo a revisión humana. Antes de producción pediría la política de precedencia.”

### “¿Por qué hay una regla de DNI?”

“La API mock valida la letra de control al registrar. Añadí una comprobación previa para no clasificar como aprobada una solicitud que fallaría tarde durante el POST.”

## 7. AWS y 1 millón de registros

No propongas levantar todo a la vez. Explica una evolución por componentes:

1. Documentos en S3 y metadatos/resultados en una base de datos relacional.
2. Una cola (SQS) entre recepción, extracción, validación y registro.
3. Workers escalables, por ejemplo Lambda si cada tarea cabe en el límite, o ECS/Fargate si OCR o modelos requieren más recursos.
4. API de revisión humana y trazabilidad por solicitud.
5. Idempotencia, reintentos con backoff, límites de concurrencia y DLQ.
6. Secrets Manager, IAM mínimo, cifrado, retención y control de acceso por los DNI.
7. CloudWatch o equivalente para logs, métricas y alertas.

La frase importante: “Primero separaría el flujo por etapas e introduciría una cola. El objetivo no es procesar un millón simultáneamente, sino que cada solicitud sea trazable, reintentable e idempotente.”

### Preguntas de AWS y escala que pueden hacerte

#### “¿Por qué S3 y no guardar los PDF en la base de datos?”

“Guardaría los binarios en S3 porque es almacenamiento de objetos, escalable y económico para documentos. En la base de datos guardaría el identificador de la solicitud, las rutas de los objetos, los resultados extraídos, el estado, las decisiones y la auditoría. Así las consultas operativas no cargan documentos pesados.”

#### “¿Qué guardarías en la base de datos?”

“Una entidad solicitud con su estado y metadatos; una tabla de documentos con tipo, versión, hash y ruta S3; participantes asociados a la solicitud; validaciones; decisiones; intentos de registro; y eventos de auditoría. Separaría PII cuando haga falta y minimizaría los datos almacenados.”

#### “¿Por qué necesitas una cola?”

“La cola desacopla la entrada del trabajo pesado. Una solicitud puede entrar rápido, quedar persistida y procesarse después por workers. Permite absorber picos, controlar la concurrencia contra la API externa, reintentar fallos y no perder trabajo si un worker cae.”

#### “¿Lambda o ECS/Fargate?”

“Para extracción simple y trabajos cortos usaría Lambda por simplicidad y escalado automático. Para OCR, conversiones pesadas, dependencias nativas o cargas largas usaría ECS/Fargate. La elección depende de duración, memoria, dependencias y coste real medido, no del volumen por sí solo.”

#### “¿Cómo evitas duplicados si un mensaje se procesa dos veces?”

“Crearía una clave de idempotencia por solicitud y operación, por ejemplo usando el ID de correo, el hash de documentos y la acción. Guardaría el resultado del primer intento y el registro externo debería aceptar esa misma clave. También pondría una restricción única en base de datos para la combinación que define una inscripción.”

#### “La comprobación de plazas y el registro no son atómicos. ¿Qué haces?”

“La fuente de verdad debe resolverlo transaccionalmente al registrar o reservar la plaza. Mi comprobación previa es informativa; el POST final debe volver a validar. Si la plaza desaparece entre ambos pasos, marco el intento como fallido o pendiente de revisión. No intentaría resolver una carrera distribuida solo desde el worker.”

#### “¿Cómo manejas fallos de la API externa?”

“Clasificaría errores transitorios y de negocio. Para timeouts o 5xx usaría reintentos con backoff y límite; para un 4xx de negocio no reintentaría automáticamente, sino que guardaría el motivo. Tras varios intentos, enviaría el mensaje a una DLQ para revisión humana.”

#### “¿Cómo escalarías a un millón de solicitudes?”

“No cargaría un millón en memoria ni en un único proceso. Trabajaría por mensajes en cola, con workers horizontales. La base de datos tendría índices por estado, fecha, empresa y acción; las consultas por lote usarían paginación. Mediría throughput, latencia, saturación de la API y edad de los mensajes para ajustar la concurrencia.”

#### “¿Cómo harías la revisión humana?”

“Una interfaz mostraría el documento original, los valores extraídos con su fuente, las validaciones y la decisión propuesta. La persona podría confirmar, corregir campos o cambiar la decisión, y cada acción quedaría auditada. Los casos escaneados, contradictorios y los que llegan a DLQ entrarían en esa cola de revisión.”

#### “¿Dónde encajaría OCR o el LLM en producción?”

“Los trataría como servicios auxiliares detrás de una interfaz propia. OCR propondría campos, pero no aprobaría automáticamente datos inciertos; el LLM seguiría limitado a redacción o clasificación asistida con métricas y revisión. Para datos personales, evaluaría si deben ejecutarse en una red privada o con un proveedor aprobado.”

#### “¿Qué seguridad aplicarías al manejar DNI?”

“Cifrado en tránsito y en reposo, IAM de mínimo privilegio, acceso segregado por roles, secretos en Secrets Manager, logs sin DNI completos cuando no sean imprescindibles, política de retención y borrado, y auditoría de acceso. Antes de construirlo confirmaría la base legal, retención y responsabilidades RGPD.”

#### “¿Cómo desplegarías cambios sin romper solicitudes en curso?”

“Versionaría los workers y los schemas de resultado. Haría despliegues graduales, mantendría compatibilidad hacia atrás durante una migración, probaría con una muestra o entorno de staging y tendría rollback. Los mensajes deben incluir versión de esquema para poder reprocesarlos de forma controlada.”

#### “¿Qué observarías el primer día en producción?”

“Número de solicitudes recibidas y procesadas, edad de la cola, porcentaje de fallos y reintentos, tasa de revisión humana por motivo, latencia por etapa, errores de la API externa, duplicados evitados y porcentaje de decisiones corregidas por personas. Configuraría alarmas para DLQ, errores sostenidos y cola creciente.”

#### “¿Qué harías con los datos históricos y con reprocesamientos?”

“Mantendría el documento original y la versión de reglas que generó cada decisión. Reprocesar no debería sobrescribir silenciosamente el resultado anterior: crearía una nueva ejecución ligada a la solicitud, para poder comparar qué cambió y por qué.”

## 8. Métricas

- Porcentaje resuelto sin intervención.
- Revisión humana, separada por motivo.
- Falsas aprobaciones y falsas denegaciones detectadas en muestreo.
- Tiempo de tramitación extremo a extremo.
- Errores de extracción por formato y PDF escaneado.
- Fallos y latencia de API.
- Fallback del LLM y calidad de los borradores revisados.

## 9. Límites que debes decir tú primero

- No envía correos: entrega borradores revisables, que es lo solicitado.
- No OCR: deriva escaneados a persona.
- Formatos de parsing adaptados al material del caso, no documentos arbitrarios.
- API mock y clave ficticia: producción necesitaría autenticación, secretos y observabilidad.
- Procesamiento local secuencial: suficiente para prototipo; la evolución a escala está explicada.

## 10. Lista final antes de entregar

- [ ] `uv run pytest tests` pasa.
- [ ] API mock iniciada en una terminal distinta.
- [ ] `SOL-2026-0004 --brief` funciona.
- [ ] `SOL-2026-0005 --brief` funciona.
- [ ] `uv run python -m awakelab_solicitudes.batch` funciona.
- [ ] Si usarás LLM: servidor LM Studio iniciado, modelo cargado y **Enable Thinking = Off**.
- [ ] Borra `_private/`, `.venv/`, `__pycache__/`, `.pytest_cache/` y carpetas `pytest-cache-*` antes de comprimir.
- [ ] Incluye `src/`, `tests/`, `output/`, `README.md`, `DECISIONES.md`, `pyproject.toml` y `uv.lock`.

