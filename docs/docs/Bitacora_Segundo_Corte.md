# 📘 Bitácora Principal del Segundo Corte · Proyecto NovaEventos

**Asignatura:** Creación de Chatbots · Segundo Corte  
**Proyecto:** NovaEventos — Sistema Conversacional de Reservas para Salones y Eventos  
**Integrantes:** Santiago Zuluaga, Jefrey Osorio, Juan Micanquer
**Versión documentada:** 2.0.0 (Python + Gradio + FastAPI + SQLite)  
**Enlaces rápidos del repositorio:**
- [Instrucciones de instalación y ejecución (`README.md`)](../README.md)
- [Presentación ejecutiva (`Presentacion_Segundo_Corte.pdf`)](./Presentacion_Segundo_Corte.pdf)
- [Carpeta de capturas y pruebas (`./evidencias/`)](./evidencias/)

---

## 1. Contexto, Problema y Alcance del Sistema

### 1.1 Descripción del negocio
**NovaEventos** es un centro de convenciones y eventos sociales, corporativos y académicos que administra cuatro espacios físicos con reglas estrictas de horario de operación (**08:00 a 22:00**), duración fija por bloque de servicio y aforo máximo por salón:

| ID de Servicio | Nombre del Servicio | Espacio Físico | Duración | Capacidad Máxima | Precio Base (COP) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `EVT-BODA` | Recepción de Boda / Gala Social | Salón Imperial | 5 horas | 200 personas | $4.500.000 |
| `EVT-CORP` | Conferencia Corporativa | Auditorio Nova | 4 horas | 120 personas | $2.800.000 |
| `EVT-CUMP` | Celebración de Cumpleaños / Aniversario | Terraza Cristal | 4 horas | 80 personas | $2.200.000 |
| `EVT-WORK` | Taller Ejecutivo / Workshop | Sala Innovación | 2 horas | 40 personas | $950.000 |

### 1.2 Problema que resuelve
Durante la gestión tradicional de reservas y en el prototipo inicial del primer corte (basado en archivos planos `.json` y flujos rígidos), se presentaban cuatro problemas críticos:
1. **Cruces de horarios (sobreasignación):** Al no calcular automáticamente la hora de finalización según la duración del servicio, se agendaban eventos que se pisaban parcialmente en el mismo salón (por ejemplo, una conferencia de 09:00 a 13:00 y otra a las 11:00).
2. **Pérdida de contexto entre turnos:** Si el cliente entregaba los datos en tres o cuatro mensajes separados, el bot olvidaba la fecha o el salón mencionados al inicio.
3. **Ausencia de confirmación previa:** Las operaciones se ejecutaban sin pedir validación explícita al usuario, impidiendo corregir o descartar un borrador antes de escribir en la base de datos.
4. **Falta de persistencia transaccional e historial de cancelaciones:** Al cancelar una reserva se requería liberar el horario para nuevos clientes sin borrar el registro histórico de la base de datos.

### 1.3 Usuarios del sistema
- **Clientes externos (organizadores de eventos, empresas y particulares):** Utilizan la interfaz conversacional en Gradio para consultar el catálogo, verificar disponibilidad de fechas, crear reservas, reprogramarlas o cancelarlas usando su código (`NOVA-XXXX`).
- **Coordinadores de NovaEventos:** Revisan en tiempo real la tabla conectada a SQLite y auditan los registros activos y cancelados a través de la API en FastAPI.

### 1.4 Alcance funcional y limitaciones actuales
- **Lo que el sistema hace (Alcance):**
  - Conversación natural en varios turnos recolectando progresivamente los 6 datos obligatorios de una reserva (`servicio_id`, `fecha`, `hora_inicio`, `asistentes`, `cliente_nombre`, `cliente_contacto`).
  - Manejo de múltiples sesiones independientes en paralelo (`Sesion_1`, `Sesion_2`, `Sesion_3`), con botones y comandos de **confirmación**, **descarte de borrador** y **reinicio de conversación**.
  - Validación matemática de horario de apertura/cierre (`08:00` a `22:00`), aforo máximo por salón y rechazo de intervalos traslapados sobre SQLite.
  - Operaciones completas de consulta, creación (`POST`), modificación (`PUT`) y cancelación lógica (`DELETE`) mediante FastAPI.
- **Limitaciones actuales del sistema:**
  - **Sin pasarela de pagos:** El sistema informa los precios del catálogo pero no procesa cobros en línea.
  - **Duración fija por paquete:** Cada servicio tiene una duración predefinida en `catalogo_eventos.json` (2, 4 o 5 horas); no se fraccionan horas sueltas fuera del paquete.
  - **Sesiones de chat en RAM:** Mientras que las reservas persisten de forma permanente en disco dentro de `reservas.db` (SQLite), el historial de conversación de un borrador no confirmado vive en la memoria del proceso de Python.

---

## 2. Arquitectura del Sistema y Organización de Archivos

### 2.1 Diagrama de arquitectura e interacción de componentes

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN (Puerto 7860)                   │
│  app_gradio.py (Gradio Blocks)                                          │
│  - Selector de sesión (Sesion_1, Sesion_2, Sesion_3)                    │
│  - Chat interactivo + Botones (Confirmar / Descartar / Reiniciar)       │
│  - Inspector JSON de memoria y Tabla Dataframe sincronizada con SQLite  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ Llamada directa en Python
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                CAPA DE CONVERSACIÓN E IA (consulta_llm.py)              │
│  - Administra SESIONES[session_id] (historial, borrador, confirmación)  │
│  - Construye System Prompt dinámico desde catalogo_eventos.json         │
│  - Consume API REST de Groq (POST /openai/v1/chat/completions)          │
│  - Extractor determinista de respaldo si falla la red o falta API Key   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ Peticiones HTTP REST (requests)
                                    │ GET / POST / PUT / DELETE
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  CAPA DE NEGOCIO API REST (Puerto 8011)                 │
│  main.py (FastAPI + Pydantic)                                           │
│  - Endpoints: /catalogo, /disponibilidad, /reservas, /reservas/{codigo} │
│  - Traduce errores de negocio en códigos HTTP 404 y HTTP 409 Conflict   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ Llamada a funciones de persistencia
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│             CAPA DE PERSISTENCIA Y REGLAS (almacen_sqlite.py)           │
│  - Calcula hora_fin = hora_inicio + duracion_horas                      │
│  - Valida horario (08:00-22:00), aforo máximo y cruces de intervalos    │
│  - Ejecuta transacciones BEGIN IMMEDIATE sobre SQLite (reservas.db)     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Responsabilidad de cada archivo del repositorio
- **`catalogo_eventos.json`**: Fuente de verdad estática con el horario del centro de eventos y los 4 servicios (ID, nombre, salón, duración en horas, capacidad máxima y precio).
- **`almacen_sqlite.py`**: Módulo de acceso a datos y reglas de negocio. Crea la tabla `reservas` en `reservas.db`, inserta los datos ficticios iniciales (`NOVA-1001`, `NOVA-1002`, `NOVA-1003`), calcula intervalos en minutos y ejecuta las consultas y transacciones SQLite.
- **`main.py`**: Servidor FastAPI que expone los endpoints del negocio, valida esquemas de entrada con `ReservaCrearInput` y `ReservaModificarInput`, e inicializa la base de datos mediante su `lifespan`.
- **`consulta_llm.py`**: Motor conversacional. Gestiona el diccionario `SESIONES`, construye el prompt con contexto, consume el endpoint de Groq y coordina cuándo pedir más datos, cuándo solicitar confirmación y cuándo invocar a FastAPI.
- **`app_gradio.py`**: Interfaz gráfica web en Gradio que conecta los eventos del usuario con `consulta_llm.py` y refresca la tabla de reservas consultando `GET /reservas`.
- **`test_sistema_eventos.py`**: Suite de pruebas automatizadas en `pytest` que verifica los 6 escenarios exigidos en la rúbrica.

---

## 3. Consumo del Modelo de Lenguaje (LLM)

### 3.1 Endpoint, Headers y Credenciales
El módulo `consulta_llm.py` se comunica con la API de **Groq** mediante la librería `requests`:
- **Endpoint HTTP:** `POST https://api.groq.com/openai/v1/chat/completions`
- **Credenciales y variables de entorno:** Se cargan con `load_dotenv()` desde el entorno o archivo `.env` local (excluido de Git mediante `.gitignore`):
  - `GROQ_API_KEY`: Token privado de autenticación.
  - `GROQ_MODEL`: `llama-3.3-70b-versatile`.
  - `CHATBOT_API_URL`: `http://127.0.0.1:8011`.
- **Headers enviados en cada petición:**
```json
{
  "Authorization": "Bearer gsk_********************************",
  "Content-Type": "application/json"
}
```

### 3.2 Estructura exacta del Payload enviado al modelo
En cada turno, `consultar_modelo_llm()` inyecta dos mensajes `system` (el catálogo del negocio + el estado actual del borrador de esa sesión), seguidos de los últimos 6 mensajes del historial (`user` / `assistant`) y el mensaje nuevo del usuario. Además, fuerza la salida estructurada con `"response_format": {"type": "json_object"}` y `"temperature": 0.1`:

```json
{
  "model": "llama-3.3-70b-versatile",
  "temperature": 0.1,
  "response_format": {
    "type": "json_object"
  },
  "messages": [
    {
      "role": "system",
      "content": "Eres el asistente virtual de reservas de NovaEventos. Horario de atención: 08:00 a 22:00. Catálogo de servicios: - ID: EVT-BODA | Nombre: Recepción de Boda / Gala Social | Espacio: Salón Imperial | Duración: 5h | Capacidad máx: 200... Devuelve EXCLUSIVAMENTE un objeto JSON válido..."
    },
    {
      "role": "system",
      "content": "Estado actual del borrador de la sesión 'Sesion_1': {\"accion\": \"crear\", \"codigo\": null, \"cliente_nombre\": null, \"cliente_contacto\": null, \"servicio_id\": \"EVT-CORP\", \"fecha\": \"2026-12-01\", \"hora_inicio\": null, \"asistentes\": null, \"notas\": null} | esperando_confirmacion=False"
    },
    {
      "role": "user",
      "content": "Quiero reservar una Conferencia Corporativa para el 2026-12-01"
    },
    {
      "role": "assistant",
      "content": "Para completar tu reserva en NovaEventos, aún necesito: hora de inicio (HH:MM), cantidad de asistentes, nombre completo y contacto."
    },
    {
      "role": "user",
      "content": "Sería a las 10:00 para 60 personas"
    }
  ]
}
```

### 3.3 Respuesta JSON recibida del modelo
El modelo procesa el contexto multi-turno y responde con un objeto JSON estricto que conserva los campos anteriores (`servicio_id: "EVT-CORP"`, `fecha: "2026-12-01"`) y agrega los nuevos (`hora_inicio: "10:00"`, `asistentes: 60`):

```json
{
  "accion": "crear",
  "codigo": null,
  "cliente_nombre": null,
  "cliente_contacto": null,
  "servicio_id": "EVT-CORP",
  "fecha": "2026-12-01",
  "hora_inicio": "10:00",
  "asistentes": 60,
  "notas": null,
  "confirmacion": "ninguna",
  "respuesta_asistente": "Excelente, he registrado la hora 10:00 y 60 asistentes. Por favor indícame tu nombre completo y un teléfono o correo de contacto."
}
```

---

## 4. Manejo de la Conversación, Sesiones y Confirmación

### 4.1 Estructura de estado por sesión
En `consulta_llm.py`, el diccionario global `SESIONES` indexa cada conversación por su `session_id` (`Sesion_1`, `Sesion_2`, `Sesion_3`), garantizando aislamiento total:

```python
SESIONES["Sesion_1"] = {
    "historial": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "borrador": {
        "accion": "crear",
        "codigo": None,
        "cliente_nombre": "Santiago Zuluaga",
        "cliente_contacto": "3005551122",
        "servicio_id": "EVT-CORP",
        "fecha": "2026-12-01",
        "hora_inicio": "10:00",
        "asistentes": 60,
        "notas": None
    },
    "esperando_confirmacion": True
}
```

### 4.2 Ciclo de confirmación, descarte y reinicio
1. **Recolección multi-turno (`_faltantes_para_crear`)**: Mientras falte alguno de los 6 campos obligatorios para crear una reserva, el bot no llama a FastAPI; enumera únicamente los campos que faltan.
2. **Paso a estado de confirmación (`esperando_confirmacion = True`)**: Cuando los 6 campos están completos (o cuando se tiene el código y los cambios para modificar/cancelar), el bot presenta un resumen detallado y activa `esperando_confirmacion = True`.
3. **Ejecución tras confirmar (`confirmacion == "confirmar"`)**: Solo cuando el usuario responde `"Sí, confirmo"` o presiona el botón **✅ Confirmar operación**, `procesar_mensaje()` invoca el endpoint correspondiente de FastAPI (`POST /reservas`, `PUT /reservas/{codigo}` o `DELETE /reservas/{codigo}`).
4. **Descarte (`descartar_borrador`)**: Si el usuario escribe `"descartar"` o pulsa **🗑️ Descartar borrador**, se limpia el diccionario `borrador` y `esperando_confirmacion` pasa a `False`, manteniendo el historial de la sesión.
5. **Reinicio (`reiniciar_sesion`)**: Si el usuario escribe `"/reiniciar"` o pulsa **🔄 Reiniciar sesión**, se borran tanto el `historial` como el `borrador` de esa sesión específica sin alterar las demás sesiones.

---

## 5. API REST en FastAPI y Persistencia en SQLite

### 5.1 Especificación de Endpoints (`main.py`)

| Método y Ruta | Parámetros / Cuerpo JSON | Códigos HTTP | Operación en `almacen_sqlite.py` |
| :--- | :--- | :---: | :--- |
| `GET /health` | Ninguno | `200 OK` | Verifica estado activo de la API y motor SQLite. |
| `GET /catalogo` | Ninguno | `200 OK` | Carga `catalogo_eventos.json` con horarios y precios. |
| `GET /disponibilidad` | Query: `servicio_id`, `fecha`, `hora_inicio` | `200 OK` | Llama a `verificar_disponibilidad()` y devuelve si el salón está libre o con qué reserva choca. |
| `GET /reservas` | Query opcional: `fecha`, `estado` | `200 OK` | Llama a `listar_reservas_db()` ordenando por fecha y hora. |
| `GET /reservas/{codigo}` | Path: `codigo` (ej. `NOVA-1001`) | `200 OK` / `404` | Llama a `obtener_reserva_por_codigo_db()`. |
| `POST /reservas` | Body JSON (`ReservaCrearInput`) | `201 Created` / `409` | Ejecuta `crear_reserva_db()` en transacción `BEGIN IMMEDIATE`. |
| `PUT /reservas/{codigo}` | Path: `codigo` + Body (`ReservaModificarInput`) | `200 OK` / `404` / `409` | Ejecuta `modificar_reserva_db()` excluyendo el propio código al validar cruces. |
| `DELETE /reservas/{codigo}` | Path: `codigo` | `200 OK` / `404` | Ejecuta `cancelar_reserva_db()`, cambiando `estado` a `'cancelada'`. |

### 5.2 Esquema relacional en SQLite (`reservas.db`)
```sql
CREATE TABLE IF NOT EXISTS reservas (
    codigo TEXT PRIMARY KEY,
    cliente_nombre TEXT NOT NULL,
    cliente_contacto TEXT NOT NULL,
    servicio_id TEXT NOT NULL,
    servicio_nombre TEXT NOT NULL,
    espacio TEXT NOT NULL,
    fecha TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    duracion_horas INTEGER NOT NULL,
    hora_fin TEXT NOT NULL,
    asistentes INTEGER NOT NULL,
    estado TEXT NOT NULL CHECK(estado IN ('activa', 'cancelada')),
    notas TEXT DEFAULT '',
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);
```

---

## 6. Reglas de Disponibilidad, Duración y Prevención de Cruces

1. **Conversión a minutos y cálculo automático de `hora_fin`**:
   Cada hora `HH:MM` se transforma a minutos desde las `00:00` ($\text{minutos\_totales} = H \times 60 + M$). La hora de salida nunca la inventa el usuario: se calcula sumando la duración oficial del servicio en `catalogo_eventos.json`:
   $$\text{fin\_nuevo} = \text{inicio\_nuevo} + (\text{duracion\_horas} \times 60)$$
2. **Cumplimiento del horario del negocio (`08:00` a `22:00`)**:
   Se exige que $\text{inicio\_nuevo} \ge 480$ (`08:00`) y $\text{fin\_nuevo} \le 1320$ (`22:00`). Por ejemplo, una *Recepción de Boda* (`5 horas`) que inicie a las `18:00` terminaría a las `23:00` (`1380 > 1320`), por lo que es rechazada automáticamente.
3. **Condición matemática de cruce de intervalos**:
   Para una misma `fecha`, un mismo `espacio` y únicamente sobre filas con `estado = 'activa'`, dos intervalos $[\text{inicio\_nuevo}, \text{fin\_nuevo})$ y $[\text{inicio\_exist}, \text{fin\_exist})$ se cruzan si y solo si:
   $$\text{inicio\_nuevo} < \text{fin\_exist} \quad \land \quad \text{fin\_nuevo} > \text{inicio\_exist}$$
   - *Nota sobre límites contiguos:* Si una reserva termina exactamente a las `13:00` y otra empieza a las `13:00`, no hay cruce ($780 < 780$ es falso), permitiendo aprovechar el salón en bloques consecutivos.
4. **Control transaccional (`BEGIN IMMEDIATE`)**:
   Tanto en `crear_reserva_db` como en `modificar_reserva_db`, la conexión abre una transacción inmediata antes de verificar disponibilidad y hacer el `INSERT`/`UPDATE`. Si ocurre una excepción de cruce o aforo, se ejecuta `conn.rollback()`; si todo es válido, se confirma con `conn.commit()`.

---

## 7. Evolución del Proyecto en el Segundo Corte y Decisiones de Diseño

### 7.1 Cronología de avances
1. **Avance 1 — Primera llamada al modelo LLM y extracción estructurada (2026-10-02):**
   - *Participante:* Santiago Zuluaga.
   - *Cambio realizado:* Creación del cliente HTTP hacia Groq en Python pasando el catálogo de `NovaEventos` en el prompt de sistema.
   - *Dificultad encontrada:* El modelo ocasionalmente envolvía el JSON en bloques ```` ```json ```` o omitía llaves cuando el mensaje del usuario era muy corto (ej. `"60 personas"`).
   - *Solución y comprobación:* Se activó `"response_format": {"type": "json_object"}` en el payload de Groq y se programó la función `_extraccion_local_respaldo()` con expresiones regulares para garantizar respuestas consistentes incluso sin conexión.
2. **Avance 2 — Conversación con historial, sesiones y confirmación (2026-10-09):**
   - *Participante:* Santiago Zuluaga.
   - *Cambio realizado:* Implementación de `SESIONES[session_id]` con historial multi-turno y máquina de estados para confirmación, descarte y reinicio.
   - *Dificultad encontrada:* Cuando el modelo respondía `null` en campos que el usuario había dado dos turnos atrás, se borraban del borrador.
   - *Solución y comprobación:* Se modificó la fusión del borrador (`if extraido.get(k) not in (None, ""): borrador[k] = extraido[k]`), preservando los valores ya capturados hasta que la reserva se confirme o descarte.
3. **Avance 3 — Migración de JSON a FastAPI + SQLite con control de cruces (2026-10-15):**
   - *Participante:* Santiago Zuluaga.
   - *Cambio realizado:* Reemplazo definitivo de `reservas.json` por `almacen_sqlite.py` y `reservas.db`, exponiendo las reglas de negocio en `main.py` (FastAPI).
   - *Dificultad encontrada:* Al modificar una reserva existente (por ejemplo, cambiar la hora de `NOVA-1001` de `09:00` a `10:00`), el validador de disponibilidad detectaba erróneamente un choque consigo misma.
   - *Solución y comprobación:* Se añadió el parámetro `excluir_codigo` en `verificar_disponibilidad()` (`AND codigo != ?`) para ignorar la propia reserva durante una reprogramación `PUT`.
4. **Avance 4 — Interfaz en Gradio y suite de pruebas integrales (2026-10-21):**
   - *Participante:* Santiago Zuluaga.
   - *Cambio realizado:* Construcción de `app_gradio.py` con selector de sesiones, inspector de estado JSON en vivo y tabla `gr.Dataframe` conectada a SQLite, junto con `test_sistema_eventos.py`.
   - *Dificultad encontrada:* Refrescar automáticamente la tabla inferior de SQLite cada vez que el usuario confirmaba desde el cuadro de texto o desde el botón.
   - *Solución y comprobación:* Todos los callbacks de Gradio (`enviar_mensaje`, `accion_confirmar`, `accion_descartar`, `accion_reiniciar`) devuelven en su cuarto canal de salida la invocación fresca a `obtener_tabla_reservas()`.

### 7.2 Decisiones clave de arquitectura
- **Separación estricta entre conversación y negocio:** `consulta_llm.py` nunca escribe directamente en `reservas.db`; toda operación pasa por los endpoints HTTP de `main.py` (FastAPI), asegurando que las reglas de negocio se cumplan sin importar qué interfaz consuma la API.
- **Cancelación lógica (`estado = 'cancelada'`) en lugar de `DELETE FROM`:** Conservar la fila con estado `'cancelada'` permite auditar el historial en la tabla de Gradio y en SQLite, mientras que el filtro `WHERE estado = 'activa'` en `verificar_disponibilidad()` libera de inmediato el salón para nuevas reservas.

---

## 8. Pruebas Documentadas y Evidencias del Sistema

A continuación se documentan los 6 escenarios obligatorios probados sobre el sistema, incluyendo los errores detectados durante el desarrollo y las capturas de respaldo alojadas en `./evidencias/`:

### Resumen de matriz de pruebas
| ID | Caso de Prueba | Entrada / Acción Ejecutada | Resultado Esperado | Resultado Obtenido | Evidencia |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **P1** | Conversación en varios turnos | Enviar datos en 4 mensajes separados para una Conferencia el `2026-12-01` a las `10:00` (60 personas) y confirmar. | Acumula los datos sin perder contexto y crea `NOVA-1004` en SQLite. | Reserva `NOVA-1004` creada de `10:00` a `14:00` en `Auditorio Nova`. | `evidencia_01_multiturno.png` |
| **P2** | Dos sesiones y reinicio | Iniciar solicitud de Boda en `Sesion_1`, cambiar a `Sesion_2` para un Taller y pulsar **Reiniciar sesión** en `Sesion_1`. | Las sesiones no se mezclan y el reinicio limpia solo `Sesion_1`. | `Sesion_1` quedó en blanco y `Sesion_2` conservó su borrador `EVT-WORK`. | `evidencia_02_sesiones_reinicio.png` |
| **P3** | Crear, modificar y cancelar | Consultar `NOVA-1004`, modificar su hora a `15:00` (`PUT`) y posteriormente cancelarla (`DELETE`). | Actualiza el horario a `15:00-19:00` y luego cambia `estado` a `cancelada`. | Cambios reflejados en `reservas.db` y en la tabla inferior de Gradio. | `evidencia_03_crud_sqlite.png` |
| **P4** | Rechazo de intervalos ocupados | Solicitar `Conferencia Corporativa` (`Auditorio Nova`) el `2026-11-15` a las `11:00` cuando `NOVA-1001` ocupa `09:00-13:00`. | Rechaza con HTTP 409 indicando el conflicto con `NOVA-1001`. | Rechazo exacto en el chat indicando que el salón está ocupado de `09:00` a `13:00`. | `evidencia_04_cruce_rechazado.png` |
| **P5** | Cancelación y persistencia tras reinicio | Cancelar `NOVA-1001`, reiniciar el servidor `uvicorn` y agendar el `2026-11-15` a las `11:00`. | Libera el horario, permite agendar y conserva todas las filas al reiniciar FastAPI. | Nueva reserva guardada en el bloque liberado; `NOVA-1001` persiste como `cancelada`. | `evidencia_05_cancelacion_persistencia.png` |
| **P6** | Manejo de errores (horario y aforo) | Pedir un evento de 5h a las `19:00` (termina `24:00`) o para `350 personas` (máximo 200). | Informa el motivo del rechazo y permite corregir el dato en la misma sesión. | El bot informó el límite violado y permitió ajustar la hora a las `16:00`. | `evidencia_06_manejo_errores.png` |

### Detalle de las evidencias y pies de imagen

1. **Evidencia 1 — Conversación multi-turno y creación en SQLite:**  
   ![Evidencia 1: Conversación en varios turnos](./evidencias/evidencia_01_multiturno.png)  
   *Pie de evidencia:* **Qué se probó:** Completar una solicitud de reserva a lo largo de cuatro turnos consecutivos entregando primero el evento y fecha, luego la hora y asistentes, después los datos del cliente y finalmente la confirmación. **Qué ocurrió:** El panel derecho (`Estado en memoria de la sesión actual`) conservó cada campo entre mensajes y, tras confirmar, FastAPI insertó la fila `NOVA-1004` en `reservas.db`. **Qué demuestra:** El funcionamiento correcto del historial, la fusión incremental del borrador y la persistencia en SQLite.

2. **Evidencia 2 — Aislamiento de dos sesiones y reinicio:**  
   ![Evidencia 2: Dos sesiones y reinicio](./evidencias/evidencia_02_sesiones_reinicio.png)  
   *Pie de evidencia:* **Qué se probó:** Alternar entre `Sesion_1` y `Sesion_2` en el desplegable de Gradio con solicitudes distintas y ejecutar el botón **🔄 Reiniciar sesión** sobre `Sesion_1`. **Qué ocurrió:** `Sesion_1` limpió su historial y borrador a valores nulos, mientras que al volver a seleccionar `Sesion_2` su conversación y su borrador permanecieron intactos. **Qué demuestra:** El aislamiento de estado por sesión en `SESIONES[session_id]`.

3. **Evidencia 3 — Ciclo completo de creación, modificación y cancelación en SQLite:**  
   ![Evidencia 3: Crear, modificar y cancelar](./evidencias/evidencia_03_crud_sqlite.png)  
   *Pie de evidencia:* **Qué se probó:** Modificar el horario de una reserva activa mediante conversación (`PUT /reservas/{codigo}`) y luego solicitar su cancelación (`DELETE /reservas/{codigo}`). **Qué ocurrió:** La tabla inferior de SQLite actualizó primero el intervalo horario recalculando `hora_fin` y luego cambió la columna `Estado` a `cancelada`. **Qué demuestra:** La integración completa de las operaciones CRUD del negocio entre Gradio, FastAPI y SQLite.

4. **Evidencia 4 — Rechazo de intervalos que se cruzan:**  
   ![Evidencia 4: Rechazo de cruce de horario](./evidencias/evidencia_04_cruce_rechazado.png)  
   *Pie de evidencia:* **Qué se probó:** Intentar confirmar una Conferencia en el `Auditorio Nova` el `2026-11-15` a las `11:00`, cruzándose con la reserva semilla `NOVA-1001` (`09:00` a `13:00`). **Qué ocurrió:** FastAPI devolvió `HTTP 409 Conflict` y el chatbot mostró la alerta indicando el choque con `NOVA-1001` sin insertar registros duplicados en `reservas.db`. **Qué demuestra:** El cumplimiento estricto de la validación de cruces según la duración del servicio.

5. **Evidencia 5 — Liberación de disponibilidad al cancelar y persistencia tras reiniciar la API:**  
   ![Evidencia 5: Cancelación y persistencia](./evidencias/evidencia_05_cancelacion_persistencia.png)  
   *Pie de evidencia:* **Qué se probó:** Cancelar la reserva `NOVA-1001`, detener y volver a iniciar `uvicorn main:app --port 8011`, y reservar nuevamente el `2026-11-15` a las `11:00`. **Qué ocurrió:** Al reiniciar FastAPI todas las filas permanecieron en `reservas.db`; dado que `NOVA-1001` pasó a estado `cancelada`, el horario `09:00-13:00` quedó libre y permitió crear la nueva reserva activa. **Qué demuestra:** La persistencia real en disco de SQLite y la liberación efectiva de intervalos cancelados.

6. **Evidencia 6 — Manejo de errores de horario, capacidad y conexión:**  
   ![Evidencia 6: Manejo de errores](./evidencias/evidencia_06_manejo_errores.png)  
   *Pie de evidencia:* **Qué se probó:** Ingresar un horario que excede el cierre de las `22:00` y un número de asistentes mayor al aforo del salón. **Qué ocurrió:** El sistema informó con claridad la regla infringida, mantuvo los demás datos del borrador en la sesión y permitió al usuario proporcionar una nueva hora válida para completar el proceso. **Qué demuestra:** La tolerancia a fallos y el manejo amigable de errores hacia el usuario final.

---

## 9. Comparación Técnica: Versión Primer Corte (Flowise + JSON) vs. Segundo Corte (Python + Gradio + FastAPI + SQLite)

| Criterio | Primer Corte (Flowise / Archivos JSON) | Segundo Corte (Python + Gradio + FastAPI + SQLite) | Responsabilidad asumida por el equipo en código |
| :--- | :--- | :--- | :--- |
| **Consumo del LLM** | Oculto detrás de bloques visuales de Flowise. | Petición HTTP explícita en `consulta_llm.py` hacia el endpoint de Groq. | Construcción manual de `headers`, lectura segura de `GROQ_API_KEY`, armado del `payload` JSON y manejo de excepciones HTTP. |
| **Memoria y Sesiones** | Memoria general del chat difícil de reiniciar o aislar por estructura de datos. | Diccionario estructurado `SESIONES[session_id]` con `historial`, `borrador` y `esperando_confirmacion`. | Programación de la fusión incremental de ranuras (*slots*) entre turnos y funciones explícitas de confirmación, descarte y reinicio. |
| **Persistencia de Datos** | Escritura directa sobre `reservas.json` propensa a corrupción y sobrescritura. | Base de datos relacional `reservas.db` en **SQLite** administrada por `almacen_sqlite.py`. | Diseño del esquema SQL, generación de códigos secuenciales (`NOVA-XXXX`), datos semilla y transacciones `BEGIN IMMEDIATE`. |
| **Reglas de Disponibilidad** | Validación básica por texto o coincidencia exacta de hora de inicio. | Cálculo matemático de intervalos $[\text{inicio}, \text{fin})$ según `duracion_horas` del catálogo. | Algoritmo de detección de traslapes ($\text{inicio\_nuevo} < \text{fin\_exist} \land \text{fin\_nuevo} > \text{inicio\_exist}$) y validación de horario de apertura/cierre. |
| **Interfaz de Usuario** | Chat embebido genérico sin visibilidad de la base de datos. | Aplicación interactiva en **Gradio (`app_gradio.py`)**. | Diseño de paneles combinados: selector de sesiones, botones de acción rápida, visor del borrador JSON y tabla de SQLite en vivo. |