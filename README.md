# 🏛️ NovaEventos · Chatbot de Gestión de Reservas (Segundo Corte)

Sistema conversacional para la cotización, verificación de disponibilidad, agendamiento, modificación y cancelación de espacios para eventos sociales, empresariales y académicos. El proyecto integra **Python** para el consumo del modelo LLM, **Gradio** para la interfaz de usuario, **FastAPI** para las reglas del negocio y **SQLite** (`reservas.db`) para la persistencia transaccional de reservas.

## 👥 Identificación e Integrantes
- **Proyecto:** NovaEventos
- **Asignatura:** Creación de Chatbots · Entrega del Segundo Corte
- **Integrantes:** Santiago Zuluaga, Jefrey Osorio, Juan Micanquer
- **Documentación del corte:**
  - 📘 [Bitácora del Segundo Corte](./docs/Bitacora_Segundo_Corte.md)
  - 📊 [Presentación del Segundo Corte (PDF)](./docs/Presentacion_Segundo_Corte.pdf)
  - 🖼️ [Carpeta de Evidencias](./docs/evidencias/)

---

## 📂 Organización del Repositorio

```text
NovaEventos/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── main.py                       # API REST de negocio en FastAPI
├── app_gradio.py                 # Interfaz conversacional en Gradio
├── consulta_llm.py               # Cliente LLM, historial y estado por sesión
├── almacen_sqlite.py             # Persistencia SQLite, semilla y validación de cruces
├── catalogo_eventos.json         # Catálogo de salones, duraciones y horarios
├── reservas.db                   # Base de datos SQLite (se genera automáticamente)
├── test_sistema_eventos.py       # Pruebas automatizadas del sistema
└── docs/
    ├── Bitacora_Segundo_Corte.md
    ├── Presentacion_Segundo_Corte.pdf
    └── evidencias/
```

---

## ⚙️ Requisitos e Instalación (desde una copia nueva)

1. **Requisitos previos:** Python **3.11 o superior** instalado en Windows, macOS o Linux.
2. **Clonar o descargar el repositorio** y abrir una terminal en la carpeta raíz `NovaEventos/`:

```powershell
# Crear el entorno virtual
python -m venv .venv

# Instalar las dependencias del segundo corte
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 🔐 Configuración de Variables de Entorno

La aplicación utiliza las siguientes variables de entorno (puedes definirlas en la terminal o copiando `.env.example` a `.env` sin subir tu clave real al repositorio):

| Variable | Descripción | Valor por defecto |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | Clave de API de Groq para consultar el LLM | *(Requerida para llamadas al LLM)* |
| `GROQ_MODEL` | Modelo de lenguaje utilizado | `llama-3.3-70b-versatile` |
| `CHATBOT_API_URL` | Dirección local donde corre FastAPI | `http://127.0.0.1:8011` |
| `SQLITE_DB_PATH` | Ruta del archivo de base de datos SQLite | `reservas.db` |

---

## 🗄️ Preparación de SQLite y Ejecución en Dos Terminales

Al iniciar `main.py`, el módulo `almacen_sqlite.py` crea automáticamente el archivo `reservas.db` y carga **3 reservas ficticias de prueba** (`NOVA-1001`, `NOVA-1002` activas y `NOVA-1003` cancelada) si la tabla está vacía.

### Terminal 1 · Iniciar la API del negocio (FastAPI)
Desde la carpeta raíz `NovaEventos/`:

```powershell
# .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8011

# $env:CHATBOT_API_URL = "http://127.0.0.1:8011"
# .\.venv\Scripts\python.exe app_gradio.py
```
- **Documentación interactiva Swagger UI:** `http://127.0.0.1:8011/docs`

### Terminal 2 · Iniciar la interfaz conversacional (Gradio)
Abre una segunda terminal en la carpeta raíz `NovaEventos/`:

```powershell
$env:CHATBOT_API_URL = "[http://127.0.0.1:8011](http://127.0.0.1:8011)"
$env:GROQ_API_KEY = "tu_clave_de_groq_aqui"
$env:GROQ_MODEL = "llama-3.3-70b-versatile"
.\.venv\Scripts\python.exe app_gradio.py
```
- **Interfaz del Chatbot en Gradio:** `http://127.0.0.1:7860`

---

## ✅ Comprobación Inicial y Errores Frecuentes

### Prueba rápida paso a paso
1. Abre `http://127.0.0.1:7860`. Verás en la tabla inferior las reservas iniciales de prueba (`NOVA-1001` el `2026-11-15` de `09:00` a `13:00` en `Auditorio Nova`).
2. Escribe en el chat: `"Quiero reservar una Conferencia Corporativa para el 2026-11-15 a las 11:00 para 50 personas"`.
3. Completa tu nombre y contacto cuando el bot los solicite y presiona **Confirmar operación**.
4. **Resultado esperado:** La API rechazará la reserva indicando que el `Auditorio Nova` ya está ocupado de `09:00` a `13:00` por la reserva activa `NOVA-1001`.
5. Ahora escribe `"Cambia la hora a las 14:00"` y confirma. **Resultado esperado:** Se guarda la reserva `NOVA-1004` de `14:00` a `18:00` y aparece inmediatamente en la tabla de SQLite.

### Ejecución de pruebas automatizadas
```powershell
.\.venv\Scripts\python.exe -m pytest test_sistema_eventos.py -v
```

### Errores frecuentes y solución
- **`No fue posible conectar con FastAPI en http://127.0.0.1:8011`**: Verifica que la Terminal 1 con `uvicorn main:app --port 8011` esté encendida antes de confirmar operaciones en Gradio.
- **Intervalo fuera del horario de atención**: El centro de eventos opera de `08:00` a `22:00`. Si reservas una Recepción de Boda (5 horas) a las `19:00`, terminaría a las `24:00` y será rechazada automáticamente.