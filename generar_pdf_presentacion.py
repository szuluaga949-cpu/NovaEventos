from pathlib import Path
import textwrap
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
PDF_PATH = DOCS_DIR / "Presentacion_Segundo_Corte.pdf"

# Colores del diseño oficial de la guía
NAVY = (16, 42, 76)
BLUE = (0, 119, 182)
CYAN_BG = (227, 244, 250)
CYAN_BORDER = (29, 169, 202)
BG_SLIDE = (248, 251, 253)
WHITE = (255, 255, 255)
CODE_BG = (16, 35, 63)
CODE_FG = (242, 247, 255)
BORDER_GRAY = (203, 220, 232)
MUTED = (100, 118, 139)


def cargar_fuente(tipo: str, tamano: int):
    rutas_windows = {
        "regular": ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"],
        "bold": ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf"],
        "mono": ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf"],
    }
    for ruta in rutas_windows.get(tipo, []):
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tamano)
    try:
        return ImageFont.load_default(size=tamano)
    except TypeError:
        return ImageFont.load_default()


F_EYEBROW = cargar_fuente("bold", 18)
F_H1 = cargar_fuente("bold", 46)
F_H2 = cargar_fuente("bold", 36)
F_H3 = cargar_fuente("bold", 24)
F_LEAD = cargar_fuente("regular", 24)
F_BODY = cargar_fuente("regular", 20)
F_BOLD = cargar_fuente("bold", 20)
F_SMALL = cargar_fuente("regular", 18)
F_CODE = cargar_fuente("mono", 17)


def base_slide(eyebrow: str, titulo: str, num_pag: int, total_pag: int = 8):
    img = Image.new("RGB", (1600, 900), color=BG_SLIDE)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (1600, 10)], fill=BLUE)
    draw.text((70, 42), eyebrow.upper(), fill=BLUE, font=F_EYEBROW)
    draw.text((70, 72), titulo, fill=NAVY, font=F_H2 if num_pag > 1 else F_H1)
    draw.text((1480, 845), f"{num_pag} / {total_pag}", fill=MUTED, font=F_SMALL)
    return img, draw


def dibujar_parrafo(draw, texto: str, x: int, y: int, ancho_chars: int, fuente=F_BODY, color=NAVY, interlineado: int = 30) -> int:
    for linea in textwrap.wrap(texto, width=ancho_chars):
        draw.text((x, y), linea, fill=color, font=fuente)
        y += interlineado
    return y


def dibujar_lista(draw, items: list, x: int, y: int, ancho_chars: int) -> int:
    for item in items:
        lineas = textwrap.wrap(item, width=ancho_chars)
        for i, linea in enumerate(lineas):
            prefijo = "•  " if i == 0 else "    "
            draw.text((x, y), prefijo + linea, fill=NAVY, font=F_BODY)
            y += 29
        y += 8
    return y


def dibujar_nota(draw, texto: str, x: int, y: int, w: int = 1460) -> int:
    lineas = textwrap.wrap(texto, width=int(w / 11.5))
    h = max(68, len(lineas) * 28 + 28)
    draw.rectangle([(x, y), (x + w, y + h)], fill=CYAN_BG)
    draw.rectangle([(x, y), (x + 7, y + h)], fill=CYAN_BORDER)
    ty = y + 14
    for l in lineas:
        draw.text((x + 24, ty), l, fill=NAVY, font=F_BODY)
        ty += 28
    return y + h + 16


def dibujar_tabla(draw, headers: list, filas: list, x: int, y: int, col_widths: list) -> int:
    total_w = sum(col_widths)
    draw.rectangle([(x, y), (x + total_w, y + 46)], fill=(235, 246, 252), outline=BORDER_GRAY)
    cx = x
    for h_txt, w in zip(headers, col_widths):
        draw.text((cx + 14, y + 12), h_txt, fill=BLUE, font=F_BOLD)
        cx += w
    y += 46

    for fila in filas:
        max_lines = 1
        celdas_envueltas = []
        for celda, w in zip(fila, col_widths):
            lineas = textwrap.wrap(str(celda), width=max(12, int((w - 24) / 10.5)))
            celdas_envueltas.append(lineas)
            max_lines = max(max_lines, len(lineas))
        row_h = max_lines * 26 + 20
        draw.rectangle([(x, y), (x + total_w, y + row_h)], fill=WHITE, outline=BORDER_GRAY)
        cx = x
        for lineas, w in zip(celdas_envueltas, col_widths):
            ty = y + 10
            for l in lineas:
                draw.text((cx + 14, ty), l, fill=NAVY, font=F_SMALL)
                ty += 26
            cx += w
        y += row_h
    return y + 16


def generar_presentacion():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    slides = []

    # SLIDE 1: Identificación y contexto
    img, d = base_slide("Creación de Chatbots · Entrega del Segundo Corte", "NovaEventos: Chatbot de Reservas con FastAPI y SQLite", 1)
    y = dibujar_parrafo(
        d,
        "Sistema conversacional completo para cotizar salones, verificar disponibilidad por bloques de duración, agendar, modificar y cancelar reservas persistidas en SQLite.",
        70, 145, 110, fuente=F_LEAD
    )
    # Tarjeta Izquierda
    d.rectangle([(70, 235), (770, 640)], fill=WHITE, outline=BORDER_GRAY, width=2)
    d.text((100, 260), "1. Identificación del Proyecto", fill=BLUE, font=F_H3)
    dibujar_lista(d, [
        "Proyecto: NovaEventos (Versión 2.0 - Segundo Corte).",
        "Integrante: Santiago Zuluaga, Jefrey Osorio, Juan Micanquer.",
        "Interfaz de usuario: Gradio (app_gradio.py - Puerto 7860).",
        "Agente y memoria: Python + Groq LLM (consulta_llm.py).",
        "API de negocio: FastAPI (main.py - Puerto 8011).",
        "Base de datos: SQLite transaccional (almacen_sqlite.py / reservas.db).",
    ], 100, 305, 58)
    # Tarjeta Derecha
    d.rectangle([(810, 235), (1530, 640)], fill=WHITE, outline=BORDER_GRAY, width=2)
    d.text((840, 260), "2. El Negocio y el Problema que Resuelve", fill=BLUE, font=F_H3)
    dibujar_lista(d, [
        "Negocio: Centro de convenciones con 4 espacios especializados para bodas, conferencias, cumpleaños y talleres ejecutivos.",
        "Problema previo: Cruces manuales de horarios, falta de cálculo automático de la hora de finalización y pérdida de contexto entre turnos.",
        "Solución: Validación matemática de intervalos en SQLite y confirmación obligatoria antes de guardar.",
    ], 840, 305, 60)
    dibujar_nota(d, "Este documento explica el funcionamiento completo de NovaEventos para cualquier lector, sin requerir haber asistido a las sesiones del curso.", 70, 680)
    slides.append(img)

    # SLIDE 2: Solución y alcance
    img, d = base_slide("1. Solución y Alcance", "Catálogo del Negocio, Usuarios, Tareas y Límites", 2)
    dibujar_parrafo(d, "Usuarios del sistema: Clientes organizadores de eventos (consulta y reservas en el chat) y coordinadores comerciales (control de agenda en SQLite). Horario de atención: 08:00 a 22:00.", 70, 130, 118)
    y = dibujar_tabla(
        d,
        ["Código ID", "Servicio / Evento", "Espacio Físico", "Duración", "Capacidad Máx.", "Precio Base"],
        [
            ["EVT-BODA", "Recepción de Boda / Gala Social", "Salón Imperial", "5 horas", "200 personas", "$4.500.000 COP"],
            ["EVT-CORP", "Conferencia Corporativa", "Auditorio Nova", "4 horas", "120 personas", "$2.800.000 COP"],
            ["EVT-CUMP", "Cumpleaños / Aniversario", "Terraza Cristal", "4 horas", "80 personas", "$2.200.000 COP"],
            ["EVT-WORK", "Taller Ejecutivo / Workshop", "Sala Innovación", "2 horas", "40 personas", "$950.000 COP"],
        ],
        70, 210, [160, 380, 260, 170, 220, 270]
    )
    dibujar_nota(d, "Alcance y límites: Soporta conversación en varios turnos, sesiones independientes, confirmación/descarte/reinicio y CRUD sobre SQLite. No incluye pasarela de cobros en línea ni fraccionamiento de horas sueltas.", 70, y + 20)
    slides.append(img)

    # SLIDE 3: Funcionamiento y arquitectura
    img, d = base_slide("2. Funcionamiento y Herramientas", "Relación entre Gradio, Python, el Modelo LLM, FastAPI y SQLite", 3)
    d.rectangle([(70, 140), (790, 690)], fill=WHITE, outline=BORDER_GRAY, width=2)
    d.text((95, 165), "Función de cada herramienta en el proyecto", fill=BLUE, font=F_H3)
    dibujar_lista(d, [
        "Gradio (app_gradio.py): Presenta la ventana de chat, el selector de sesiones (Sesion_1, Sesion_2, Sesion_3), los botones de confirmación/reinicio y la tabla SQLite en vivo.",
        "Python + LLM (consulta_llm.py): Construye el prompt con el catálogo, envía el historial a Groq (llama-3.3-70b-versatile) y extrae un JSON con los datos aportados.",
        "FastAPI (main.py): Recibe peticiones HTTP (GET, POST, PUT, DELETE) y aplica las reglas del negocio.",
        "SQLite (almacen_sqlite.py): Conserva las reservas en reservas.db.",
    ], 95, 210, 62)

    d.rectangle([(820, 140), (1530, 690)], fill=CODE_BG, outline=BORDER_GRAY, width=2)
    d.text((845, 165), "Flujo de una solicitud de principio a fin", fill=(102, 217, 239), font=F_H3)
    codigo_arq = (
        "[Persona en Navegador Web]\n"
        "        |\n"
        "        v\n"
        "[app_gradio.py] (Interfaz en Puerto 7860)\n"
        "        |\n"
        "        v\n"
        "[consulta_llm.py] (Estado por Sesion)\n"
        "   |-- 1. Consulta HTTPS JSON a Groq API\n"
        "   |-- 2. Acumula borrador entre turnos\n"
        "   +-- 3. Pide confirmacion al usuario\n"
        "        |\n"
        "        v  (Solo cuando el usuario confirma)\n"
        "[main.py] (FastAPI en Puerto 8011)\n"
        "   |-- GET    /disponibilidad\n"
        "   |-- POST   /reservas\n"
        "   |-- PUT    /reservas/{codigo}\n"
        "   +-- DELETE /reservas/{codigo}\n"
        "        |\n"
        "        v\n"
        "[almacen_sqlite.py] ---> [reservas.db]"
    )
    ty = 215
    for l in codigo_arq.splitlines():
        d.text((850, ty), l, fill=CODE_FG, font=F_CODE)
        ty += 24
    dibujar_nota(d, "Separación de responsabilidades: El chat nunca escribe directo en la base de datos; toda operación pasa por la API de FastAPI.", 70, 715)
    slides.append(img)

    # SLIDE 4: Recorrido de uso
    img, d = base_slide("3. Recorrido de Uso Completo", "Ejemplo Paso a Paso: Solicitud Multi-Turno, Confirmación y Registro", 4)
    d.rectangle([(70, 140), (800, 670)], fill=WHITE, outline=BORDER_GRAY, width=2)
    d.text((95, 165), "Diálogo en varios turnos (conservando contexto)", fill=BLUE, font=F_H3)
    dibujar_lista(d, [
        "Turno 1 (Cliente): 'Quiero reservar una Conferencia Corporativa para el 2026-12-01' -> El bot registra EVT-CORP y la fecha, y pide hora, asistentes y contacto.",
        "Turno 2 (Cliente): 'A las 10:00 para 60 asistentes' -> El bot conserva el salón y la fecha anteriores, suma hora_inicio=10:00 y asistentes=60, y pide nombre y teléfono.",
        "Turno 3 (Cliente): 'Me llamo Santiago Zuluaga y mi contacto es 3005551122' -> El bot muestra el resumen completo y activa esperando_confirmacion = True.",
        "Turno 4 (Cliente): 'Sí, confirmo' -> Se envía POST /reservas a FastAPI.",
    ], 95, 210, 62)

    d.rectangle([(830, 140), (1530, 670)], fill=WHITE, outline=BORDER_GRAY, width=2)
    d.text((855, 165), "Fila guardada en SQLite (reservas.db)", fill=BLUE, font=F_H3)
    dibujar_lista(d, [
        "codigo: NOVA-1004 (generado automáticamente)",
        "cliente_nombre: Santiago Zuluaga",
        "cliente_contacto: 3005551122",
        "servicio_id: EVT-CORP (Conferencia Corporativa)",
        "espacio: Auditorio Nova",
        "fecha: 2026-12-01",
        "hora_inicio: 10:00  |  duracion_horas: 4  |  hora_fin: 14:00",
        "asistentes: 60 (validado <= 120 máx.)",
        "estado: activa",
    ], 855, 210, 58)
    dibujar_nota(d, "Con el código devuelto (NOVA-1004), la persona puede consultar su reserva, cambiarla de fecha/hora o cancelarla en cualquier momento.", 70, 700)
    slides.append(img)

    # SLIDE 5: Reglas del negocio
    img, d = base_slide("4. Reglas del Negocio y Disponibilidad", "Horario de Atención, Duración por Servicio y Prevención de Cruces", 5)
    d.rectangle([(70, 140), (780, 685)], fill=WHITE, outline=BORDER_GRAY, width=2)
    d.text((95, 165), "Controles aplicados por almacen_sqlite.py", fill=BLUE, font=F_H3)
    dibujar_lista(d, [
        "1. Cálculo de hora_fin según catálogo: Se convierte hora_inicio a minutos y se suma duracion_horas * 60.",
        "2. Horario de operación (08:00 a 22:00): Si una Boda (5h) inicia a las 19:00, terminaría a las 24:00 y se rechaza.",
        "3. Capacidad máxima por salón: Rechaza solicitudes que superen el aforo del espacio.",
        "4. Rechazo de intervalos que se cruzan: Verifica reservas con estado = 'activa' en la misma fecha y salón.",
        "5. Transacción BEGIN IMMEDIATE: Impide que dos solicitudes simultáneas ocupen el mismo bloque.",
    ], 95, 210, 60)

    d.rectangle([(810, 140), (1530, 685)], fill=CODE_BG, outline=BORDER_GRAY, width=2)
    d.text((835, 165), "Verificación de cruces en SQLite", fill=(102, 217, 239), font=F_H3)
    codigo_cruce = (
        "# 1. Calculo del intervalo solicitado\n"
        "inicio_nuevo, fin_nuevo, hora_fin = calcular_intervalo(\n"
        "    hora_inicio, servicio['duracion_horas']\n"
        ")\n\n"
        "# 2. Consulta de reservas activas en ese salon y fecha\n"
        "SELECT codigo, hora_inicio, hora_fin\n"
        "FROM reservas\n"
        "WHERE fecha = ? AND espacio = ? AND estado = 'activa'\n\n"
        "# 3. Condicion matematica de traslape [A, B) vs [C, D)\n"
        "for fila in filas:\n"
        "    inicio_exist = _a_minutos(fila['hora_inicio'])\n"
        "    fin_exist = _a_minutos(fila['hora_fin'])\n"
        "    if inicio_nuevo < fin_exist and fin_nuevo > inicio_exist:\n"
        "        raise ValueError(\n"
        "            f\"Ocupado por reserva activa {fila['codigo']}\"\n"
        "        )"
    )
    ty = 215
    for l in codigo_cruce.splitlines():
        d.text((835, ty), l, fill=CODE_FG, font=F_CODE)
        ty += 24
    dibujar_nota(d, "Manejo de cancelaciones: Al cancelar una reserva su estado pasa a 'cancelada'. La fila permanece en SQLite como historial pero libera el horario.", 70, 710)
    slides.append(img)

    # SLIDE 6: Pruebas y resultados
    img, d = base_slide("5. Pruebas y Resultados Documentados", "Evidencias de los 6 Escenarios Evaluados en el Segundo Corte", 6)
    y = dibujar_tabla(
        d,
        ["Caso de Prueba", "Entrada / Acción Ejecutada", "Resultado Comprobado en Chat y SQLite", "Evidencia"],
        [
            ["1. Varios turnos", "Reserva en 4 mensajes separados para el 2026-12-01 a las 10:00.", "Conserva datos previos y crea la fila NOVA-1004 (10:00-14:00).", "evidencia_01_multiturno.png"],
            ["2. Dos sesiones y reinicio", "Boda en Sesion_1, Taller en Sesion_2 y reinicio de Sesion_1.", "Separa conversaciones; Sesion_1 queda limpia y Sesion_2 intacta.", "evidencia_02_sesiones_reinicio.png"],
            ["3. Crear, modificar, cancelar", "Modificar NOVA-1004 a las 15:00 (PUT) y luego cancelarla (DELETE).", "Actualiza horario a 15:00-19:00 y cambia estado a 'cancelada'.", "evidencia_03_crud_sqlite.png"],
            ["4. Intervalos ocupados", "Agendar en Auditorio Nova el 2026-11-15 a las 11:00.", "Rechaza con HTTP 409 por cruce con NOVA-1001 (09:00-13:00).", "evidencia_04_cruce_rechazado.png"],
            ["5. Cancelación y persistencia", "Cancelar NOVA-1001, reiniciar FastAPI y reservar a las 11:00.", "Libera disponibilidad, crea NOVA-1005 y conserva las filas.", "evidencia_05_cancelacion_persistencia.png"],
            ["6. Manejo de errores", "Solicitar Boda (5h) a las 19:00 (termina 24:00 > cierre 22:00).", "Informa el problema y permite corregir la hora en la misma sesión.", "evidencia_06_manejo_errores.png"],
        ],
        70, 145, [250, 430, 470, 310]
    )
    dibujar_nota(d, "Todas las pruebas cuentan con verificación automatizada en test_sistema_eventos.py (pytest) y capturas en docs/evidencias/.", 70, y + 10)
    slides.append(img)

    # SLIDE 7: Evolución frente a Flowise
    img, d = base_slide("6. Evolución del Proyecto", "Cambios frente a la Versión con Flowise y Archivos JSON", 7)
    y = dibujar_tabla(
        d,
        ["Dimensión", "Versión Anterior (Flowise + JSON)", "Versión Segundo Corte (Python + Gradio + FastAPI + SQLite)"],
        [
            ["Consumo del LLM", "Nodos visuales cerrados en Flowise.", "Petición HTTP directa en consulta_llm.py con headers, payload JSON y respaldo local."],
            ["Estado y Sesiones", "Memoria implícita difícil de depurar o reiniciar.", "Diccionario SESIONES[session_id] con historial, borrador y confirmación explícita."],
            ["Persistencia", "Archivo plano reservas.json sin transacciones.", "Tabla relacional reservas en SQLite (reservas.db) con semillas de prueba y transacciones."],
            ["Reglas de horario", "Sin validación matemática de duración ni cruces.", "Cálculo exacto de hora_fin y rechazo automático HTTP 409 ante traslapes."],
            ["Interfaz gráfica", "Chat básico sin vista del estado ni de la base.", "Gradio con selector de sesiones, visor de estado JSON y tabla SQLite en tiempo real."],
        ],
        70, 155, [260, 480, 720]
    )
    dibujar_nota(d, "Responsabilidad asumida en código: El equipo programó directamente el control de sesiones, la validación de cruces y la persistencia SQL.", 70, y + 20)
    slides.append(img)

    # SLIDE 8: Cierre y repositorio
    img, d = base_slide("7. Cierre, Limitaciones y Repositorio", "Conclusiones, Mejoras Pendientes y Estructura Entregada", 8)
    d.rectangle([(70, 145), (775, 650)], fill=WHITE, outline=BORDER_GRAY, width=2)
    d.text((95, 170), "Limitaciones Actuales y Mejoras Futuras", fill=BLUE, font=F_H3)
    dibujar_lista(d, [
        "Limitación 1: Duración fija por paquete según catalogo_eventos.json (2h, 4h o 5h).",
        "Limitación 2: El borrador no confirmado vive en memoria RAM hasta que el usuario confirma y pasa a SQLite.",
        "Mejora pendiente 1: Permitir contratar horas extra sobre la duración base de cada salón.",
        "Mejora pendiente 2: Envío de comprobante por correo electrónico al confirmar una reserva.",
    ], 95, 215, 58)

    d.rectangle([(805, 145), (1530, 650)], fill=WHITE, outline=BORDER_GRAY, width=2)
    d.text((830, 170), "Documentos y Archivos del Repositorio", fill=BLUE, font=F_H3)
    dibujar_lista(d, [
        "README.md: Guía paso a paso de instalación y ejecución en dos terminales (FastAPI 8011 y Gradio 7860).",
        "docs/Bitacora_Segundo_Corte.md: Documentación técnica completa, evolución y pruebas enlazadas.",
        "docs/Presentacion_Segundo_Corte.pdf: Presentación autónoma del proyecto.",
        "docs/evidencias/: Capturas de pantalla y registro de pruebas.",
        "Código fuente: main.py, app_gradio.py, consulta_llm.py, almacen_sqlite.py y test_sistema_eventos.py.",
    ], 830, 215, 58)
    dibujar_nota(d, "Ejecución rápida: Terminal 1 -> uvicorn main:app --reload --port 8011  |  Terminal 2 -> python app_gradio.py", 70, 685)
    slides.append(img)

    # Guardar todas las diapositivas en un único archivo PDF multipágina
    slides[0].save(
        PDF_PATH,
        "PDF",
        resolution=150.0,
        save_all=True,
        append_images=slides[1:],
    )
    print(f"[OK] PDF de 8 paginas generado exitosamente en: {PDF_PATH}")


if __name__ == "__main__":
    generar_presentacion()