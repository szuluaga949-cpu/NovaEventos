import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
import httpx

API_URL = os.getenv("CHATBOT_API_URL", "http://127.0.0.1:8011")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

_sesiones: Dict[str, Dict[str, Any]] = {}
CATALOG_PATH = Path(__file__).resolve().parent / "catalogo_eventos.json"


def _cargar_catalogo_local() -> Dict[str, Any]:
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def obtener_info_servicio(servicio_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not servicio_id:
        return None
    # Intento 1: Por API si está disponible
    res = _llamar_api("GET", "/catalogo")
    if res.get("ok"):
        for s in res["data"].get("servicios", []):
            if s["id"].lower() == servicio_id.lower() or s["nombre"].lower() == servicio_id.lower():
                return s
    # Intento 2: Por archivo local
    cat = _cargar_catalogo_local()
    for s in cat.get("servicios", []):
        if s["id"].lower() == servicio_id.lower() or s["nombre"].lower() == servicio_id.lower():
            return s
    return None


def obtener_sesion(session_id: str) -> Dict[str, Any]:
    if session_id not in _sesiones:
        sesion: Dict[str, Any] = {
            "servicio_id": None,
            "fecha": None,
            "hora_inicio": None,
            "asistentes": None,
            "cliente_nombre": None,
            "cliente_contacto": None,
            "notas": "",
        }
        sesion["borrador"] = sesion  # Compatibilidad con tests
        _sesiones[session_id] = sesion
    return _sesiones[session_id]


def reiniciar_sesion(session_id: str) -> None:
    if session_id in _sesiones:
        del _sesiones[session_id]
    obtener_sesion(session_id)


def _llamar_api(metodo: str, ruta: str, params: Optional[Dict] = None, json_body: Optional[Dict] = None) -> Dict[str, Any]:
    url = f"{API_URL}{ruta}"
    try:
        with httpx.Client(timeout=10.0) as client:
            metodo_upper = metodo.upper()
            if metodo_upper == "GET":
                resp = client.get(url, params=params)
            elif metodo_upper == "POST":
                resp = client.post(url, json=json_body)
            elif metodo_upper == "DELETE":
                resp = client.delete(url)
            else:
                return {"ok": False, "error": "Método no soportado"}
            datos = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                return {"ok": False, "status": resp.status_code, "error": datos.get("detail", "Error en API")}
            return {"ok": True, "status": resp.status_code, "data": datos}
    except Exception as e:
        return {"ok": False, "error": f"No se pudo conectar con la API: {str(e)}"}


def consultar_disponibilidad_servicio(servicio_id: str, fecha: str, hora_inicio: str) -> Dict[str, Any]:
    res = _llamar_api("GET", "/disponibilidad", params={
        "servicio_id": servicio_id,
        "fecha": fecha,
        "hora_inicio": hora_inicio
    })
    if res.get("ok"):
        return res.get("data", {})
    try:
        import almacen_sqlite
        return almacen_sqlite.verificar_disponibilidad(
            servicio_identificador=servicio_id,
            fecha=fecha,
            hora_inicio=hora_inicio
        )
    except Exception:
        return {"disponible": True}


def _formatear_resumen_confirmacion(sesion: Dict[str, Any]) -> str:
    info_s = obtener_info_servicio(sesion.get("servicio_id"))
    nombre_serv = info_s.get("nombre", sesion["servicio_id"]) if info_s else sesion["servicio_id"]
    espacio = f" ({info_s.get('espacio')})" if info_s and info_s.get("espacio") else ""
    return (
        f"¿Confirmas los datos de tu reserva?\n"
        f"- **Servicio:** {nombre_serv}{espacio}\n"
        f"- **Fecha:** {sesion['fecha']}\n"
        f"- **Hora:** {sesion['hora_inicio']}\n"
        f"- **Asistentes:** {sesion['asistentes']}\n"
        f"- **Cliente:** {sesion['cliente_nombre']} ({sesion['cliente_contacto']})\n\n"
        f"Responde **'Sí, confirmo'** para procesar tu reserva o **'Cancelar'** para empezar de nuevo."
    )


def procesar_mensaje(session_id: str, mensaje_usuario: str) -> str:
    sesion = obtener_sesion(session_id)
    texto = mensaje_usuario.strip()
    texto_lower = texto.lower()

    # 0. Comandos explícitos de reinicio y cancelación
    if any(k == texto_lower or k in texto_lower.split() for k in ["reiniciar", "empezar", "reset", "menu", "menú"]):
        reiniciar_sesion(session_id)
        return "¡Hola! Bienvenido a **NovaEventos**. ¿Qué servicio deseas reservar?\n- 🎤 **Conferencia**\n- 💍 **Boda**\n- 🎂 **Cumpleaños**\n- 📚 **Taller**\n\nIndícame cuál te interesa para comenzar."

    if any(k == texto_lower for k in ["cancelar", "anular"]):
        reiniciar_sesion(session_id)
        return "Operación cancelada. ¿Qué servicio deseas reservar?\n- 🎤 **Conferencia**\n- 💍 **Boda**\n- 🎂 **Cumpleaños**\n- 📚 **Taller**"

    # Saludo inicial si la sesión está totalmente vacía
    if not sesion.get("servicio_id") and any(k in texto_lower for k in ["hola", "buenos dias", "buenas tardes", "buenas"]):
        if not any(k in texto_lower for k in ["boda", "conferencia", "taller", "cumpleaños", "cumple", "corp"]):
            return "¡Hola! Bienvenido a **NovaEventos**. ¿Qué servicio deseas reservar?\n- 🎤 **Conferencia**\n- 💍 **Boda**\n- 🎂 **Cumpleaños**\n- 📚 **Taller**\n\nIndícame cuál te interesa para comenzar."

    # 1. Extracción de Servicio
    if not sesion["servicio_id"]:
        if any(k in texto_lower for k in ["conferencia", "corp", "auditorio"]):
            sesion["servicio_id"] = "EVT-CORP"
        elif any(k in texto_lower for k in ["boda", "matrimonio", "gala", "imperial"]):
            sesion["servicio_id"] = "EVT-BODA"
        elif any(k in texto_lower for k in ["cumpleaños", "cumpleanos", "cumple", "fiesta"]):
            sesion["servicio_id"] = "EVT-CUMP"
        elif any(k in texto_lower for k in ["taller", "workshop", "capacitacion", "ejecutivo"]):
            sesion["servicio_id"] = "EVT-WORK"

    # 2. Extracción de Fecha (YYYY-MM-DD)
    m_fecha = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", texto)
    if m_fecha and (not sesion["fecha"] or "cambiar fecha" in texto_lower or "fecha" in texto_lower):
        sesion["fecha"] = m_fecha.group(1)

    # 3. Extracción de Hora (HH:MM)
    m_hora = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", texto)
    if m_hora and (not sesion["hora_inicio"] or "cambiar hora" in texto_lower or "hora" in texto_lower):
        h, m = int(m_hora.group(1)), int(m_hora.group(2))
        sesion["hora_inicio"] = f"{h:02d}:{m:02d}"

    # 3.1 Validación de Disponibilidad Inmediata si ya tenemos servicio, fecha y hora
    if sesion["servicio_id"] and sesion["fecha"] and sesion["hora_inicio"]:
        disp = consultar_disponibilidad_servicio(sesion["servicio_id"], sesion["fecha"], sesion["hora_inicio"])
        if not disp.get("disponible", True):
            motivo = disp.get("motivo", "El horario seleccionado no está disponible.")
            sesion["hora_inicio"] = None  # Permitir al usuario reintentar la hora o la fecha
            return (
                f"⚠️ **Horario no disponible:** {motivo}\n\n"
                f"Ya existe una reserva guardada para este salón en ese horario. "
                f"Por favor, **indícame otra hora de inicio u otra fecha** para tu evento."
            )

    # 4. Extracción de Asistentes
    nuevo_asistentes = None
    m_asist = re.search(r"\b(\d{1,4})\s*(?:asistentes|personas|invitados|cupos)\b", texto, re.I)
    if m_asist:
        nuevo_asistentes = int(m_asist.group(1))
    elif texto.strip().isdigit() and len(texto.strip()) <= 4:
        # Texto contiene únicamente dígitos (ej. "200")
        nuevo_asistentes = int(texto.strip())
    elif not sesion["asistentes"] and sesion["hora_inicio"]:
        # Si ya tenemos la hora y esperamos asistentes, buscar un número aislado o "para X"
        m_num = re.search(r"\b(?:para\s+)?(\d{1,4})\b", texto, re.I)
        if m_num:
            val = int(m_num.group(1))
            es_fecha = m_fecha and str(val) in m_fecha.group(1)
            es_hora = m_hora and str(val) in m_hora.group(0)
            if not es_fecha and not es_hora:
                nuevo_asistentes = val

    # Si se detectó un número de asistentes, procesarlo
    if nuevo_asistentes is not None:
        if nuevo_asistentes <= 0:
            return "Por favor ingresa un número de asistentes mayor a cero."
        
        info_s = obtener_info_servicio(sesion.get("servicio_id"))
        if info_s:
            cap_max = info_s.get("capacidad_maxima", 0)
            espacio_nombre = info_s.get("espacio", "el espacio")
            if cap_max > 0 and nuevo_asistentes > cap_max:
                # No guardamos el número inválido; dejamos que el usuario lo intente de nuevo sin resetear otros datos
                return (
                    f"No se pudo completar la reserva: El espacio '{espacio_nombre}' tiene capacidad máxima de {cap_max} personas (solicitado: {nuevo_asistentes}).\n\n"
                    f"Por favor, **indícame un nuevo número menor de asistentes** para continuar."
                )

        # Asignar los asistentes válidos
        sesion["asistentes"] = nuevo_asistentes

        # Si el usuario ya tenía ingresado su nombre/contacto (caso corrección/reintento):
        # NO volvemos a pedirle los datos, vamos directo a confirmación.
        if sesion.get("cliente_nombre"):
            return (
                f"Número de asistentes actualizado a **{sesion['asistentes']}**.\n\n"
                f"{_formatear_resumen_confirmacion(sesion)}"
            )
        else:
            return "Perfecto. Por favor, indícame tu **nombre completo** y tu **contacto** (ej. Juan Pérez, juan@mail.com)."

    # Verificación de datos faltantes paso a paso:
    if not sesion["servicio_id"]:
        return "No alcancé a identificar el servicio. Por favor, indícame si deseas una **Conferencia**, **Boda**, **Cumpleaños** o **Taller**."

    if not sesion["fecha"]:
        return f"Perfecto, servicio seleccionado (**{sesion['servicio_id']}**). ¿Para qué fecha deseas agendarlo? (Formato YYYY-MM-DD, ej: 2026-12-12)."

    if not sesion["hora_inicio"]:
        return f"Entendido, fecha {sesion['fecha']}. ¿A qué hora deseas iniciar? (Atendemos de 08:00 a 22:00, formato HH:MM, ej: 20:00)."

    if not sesion["asistentes"]:
        return f"Registrado a las {sesion['hora_inicio']}. ¿Cuántos asistentes participarán en el evento?"

    # 5. Extracción de Cliente (Nombre y Contacto)
    if not sesion["cliente_nombre"]:
        m_name = re.search(r"(?:me llamo|mi nombre es)\s+([^,]+?)(?:\s+y\s+mi|\s*,|\s*$)", texto, re.I)
        m_contact = re.search(r"(?:contacto|tel[eé]fono|correo|celular|mail)(?:\s+es)?\s*:?\s*([^\s,]+@[^\s,]+|\d[\d\s-]{6,14})", texto, re.I)

        if m_name and m_contact:
            sesion["cliente_nombre"] = m_name.group(1).strip()
            sesion["cliente_contacto"] = m_contact.group(1).strip()
        elif "," in texto:
            partes = texto.split(",", 1)
            sesion["cliente_nombre"] = partes[0].strip()
            sesion["cliente_contacto"] = partes[1].strip()
        else:
            m_phone = re.search(r"\b(3\d{9}|\d{7,10})\b", texto)
            m_email = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", texto)
            if m_phone or m_email:
                contacto = m_phone.group(1) if m_phone else m_email.group(0)
                limpio = texto.replace(contacto, "")
                for pref in ["me llamo", "mi nombre es", "y mi contacto es", "contacto", "telefono", "teléfono"]:
                    limpio = re.sub(pref, "", limpio, flags=re.I)
                sesion["cliente_nombre"] = limpio.strip(" ,.-:") or "Cliente"
                sesion["cliente_contacto"] = contacto
            else:
                sesion["cliente_nombre"] = texto.strip()
                sesion["cliente_contacto"] = "3000000000"

        return _formatear_resumen_confirmacion(sesion)

    # 6. Confirmación final
    if any(k in texto_lower for k in ["si", "sí", "confirmo", "correcto", "de acuerdo", "ok", "condirmo", "dale", "proceder"]):
        payload = {
            "cliente_nombre": sesion["cliente_nombre"],
            "cliente_contacto": sesion["cliente_contacto"],
            "servicio_id": sesion["servicio_id"],
            "fecha": sesion["fecha"],
            "hora_inicio": sesion["hora_inicio"],
            "asistentes": sesion["asistentes"],
            "notas": sesion.get("notas", "")
        }
        res = _llamar_api("POST", "/reservas", json_body=payload)
        if res.get("ok"):
            datos_reserva = res["data"].get("reserva", {})
            codigo = datos_reserva.get("codigo", "EXITOSO")
            espacio = datos_reserva.get("espacio", "salón")
            reiniciar_sesion(session_id)
            return f"¡Reserva creada con éxito! Tu código de confirmación es **{codigo}**. Espacio asignado: {espacio}."
        else:
            error_msg = res.get("error", "Error al procesar la reserva.")
            if "capacidad" in error_msg.lower():
                # Si la API reporta exceso de capacidad, se anula únicamente asistentes manteniendo intacto nombre, contacto, etc.
                sesion["asistentes"] = None
                return f"No se pudo completar la reserva: {error_msg}\n\nPor favor, **indícame un nuevo número menor de asistentes** para continuar."
            elif "ocupado" in error_msg.lower() or "disponible" in error_msg.lower() or "horario" in error_msg.lower():
                sesion["hora_inicio"] = None
                return f"No se pudo completar la reserva: {error_msg}\n\nPor favor, **indícame otra hora o fecha** para tu evento (mantendremos tus datos de cliente y asistentes)."
            else:
                return f"No se pudo completar la reserva: {error_msg}.\n\nIndícame el nuevo dato a corregir o escribe **'cancelar'** para reiniciar la sesión."

    # Si el usuario responde algo que no es confirmación, permitir cambiar campos
    if "cambiar" in texto_lower or "modificar" in texto_lower:
        if "asistente" in texto_lower or "persona" in texto_lower:
            sesion["asistentes"] = None
            return "¿Cuántos asistentes participarán en el evento?"
        if "fecha" in texto_lower:
            sesion["fecha"] = None
            return "¿Para qué fecha deseas agendarlo? (YYYY-MM-DD)."
        if "hora" in texto_lower:
            sesion["hora_inicio"] = None
            return "¿A qué hora deseas iniciar? (HH:MM)."

    # Por defecto volver a mostrar confirmación
    return _formatear_resumen_confirmacion(sesion)
