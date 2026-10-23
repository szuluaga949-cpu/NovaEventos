import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("SQLITE_DB_PATH", BASE_DIR / "reservas.db"))
CATALOG_PATH = BASE_DIR / "catalogo_eventos.json"

def cargar_catalogo() -> Dict[str, Any]:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def obtener_servicio(servicio_identificador: str) -> Optional[Dict[str, Any]]:
    catalogo = cargar_catalogo()
    texto = (servicio_identificador or "").strip().lower()
    for s in catalogo.get("servicios", []):
        if (
            s["id"].lower() == texto
            or s["nombre"].lower() == texto
            or texto in s["id"].lower()
            or texto in s["nombre"].lower()
            or texto in s["espacio"].lower()
        ):
            return s
    return None

def _a_minutos(hora_str: str) -> int:
    partes = hora_str.strip().split(":")
    if len(partes) != 2:
        raise ValueError(f"Formato de hora inválido: {hora_str}. Use HH:MM.")
    horas, minutos = int(partes[0]), int(partes[1])
    if not (0 <= horas <= 23 and 0 <= minutos <= 59):
        raise ValueError(f"Hora fuera de rango: {hora_str}.")
    return horas * 60 + minutos

def _a_hora_str(minutos_totales: int) -> str:
    horas = minutos_totales // 60
    minutos = minutos_totales % 60
    return f"{horas:02d}:{minutos:02d}"

def calcular_intervalo(hora_inicio: str, duracion_horas: int) -> Tuple[int, int, str]:
    inicio_min = _a_minutos(hora_inicio)
    fin_min = inicio_min + (duracion_horas * 60)
    return inicio_min, fin_min, _a_hora_str(fin_min)

def validar_dentro_de_horario(hora_inicio: str, duracion_horas: int) -> Tuple[bool, str, str]:
    catalogo = cargar_catalogo()
    apertura_min = _a_minutos(catalogo.get("horario_apertura", "08:00"))
    cierre_min = _a_minutos(catalogo.get("horario_cierre", "22:00"))
    try:
        inicio_min, fin_min, hora_fin = calcular_intervalo(hora_inicio, duracion_horas)
    except ValueError as e:
        return False, "", str(e)

    if inicio_min < apertura_min or fin_min > cierre_min:
        return (
            False,
            hora_fin,
            f"El intervalo solicitado ({hora_inicio} a {hora_fin}) está fuera del horario de atención "
            f"({catalogo['horario_apertura']} a {catalogo['horario_cierre']}).",
        )
    return True, hora_fin, "OK"

def obtener_conexion(db_path: Optional[Path] = None) -> sqlite3.Connection:
    ruta = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(str(ruta), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_bd(db_path: Optional[Path] = None, poblar_semilla: bool = True) -> None:
    conn = obtener_conexion(db_path)
    try:
        with conn:
            conn.execute(
                """
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
                )
                """
            )
            if poblar_semilla:
                cursor = conn.execute("SELECT COUNT(*) AS total FROM reservas")
                total = cursor.fetchone()["total"]
                if total == 0:
                    ahora = datetime.now().isoformat(timespec="seconds")
                    semillas = [
                        (
                            "NOVA-1001",
                            "Camila Restrepo",
                            "3001234567",
                            "EVT-CORP",
                            "Conferencia Corporativa",
                            "Auditorio Nova",
                            "2026-11-15",
                            "09:00",
                            4,
                            "13:00",
                            90,
                            "activa",
                            "Requiere 2 micrófonos de solapa adicionales.",
                            ahora,
                            ahora,
                        ),
                        (
                            "NOVA-1002",
                            "Andrés Mejía",
                            "andres.mejia@correo.co",
                            "EVT-BODA",
                            "Recepción de Boda / Gala Social",
                            "Salón Imperial",
                            "2026-11-20",
                            "16:00",
                            5,
                            "21:00",
                            150,
                            "activa",
                            "Montaje imperial en tonos blancos.",
                            ahora,
                            ahora,
                        ),
                        (
                            "NOVA-1003",
                            "Laura Gómez",
                            "3159876543",
                            "EVT-WORK",
                            "Taller Ejecutivo / Workshop",
                            "Sala Innovación",
                            "2026-11-15",
                            "14:00",
                            2,
                            "16:00",
                            25,
                            "cancelada",
                            "Reserva cancelada de prueba.",
                            ahora,
                            ahora,
                        ),
                    ]
                    conn.executemany(
                        """
                        INSERT INTO reservas (
                            codigo, cliente_nombre, cliente_contacto, servicio_id,
                            servicio_nombre, espacio, fecha, hora_inicio,
                            duracion_horas, hora_fin, asistentes, estado,
                            notas, creado_en, actualizado_en
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        semillas,
                    )
    finally:
        conn.close()

def _generar_codigo(conn: sqlite3.Connection) -> str:
    cursor = conn.execute("SELECT codigo FROM reservas ORDER BY codigo DESC LIMIT 1")
    fila = cursor.fetchone()
    if not fila:
        return "NOVA-1001"
    try:
        numero = int(fila["codigo"].split("-")[1]) + 1
    except (IndexError, ValueError):
        cursor_count = conn.execute("SELECT COUNT(*) AS c FROM reservas")
        numero = 1001 + cursor_count.fetchone()["c"]
    return f"NOVA-{numero}"

def verificar_disponibilidad(
    servicio_identificador: str,
    fecha: str,
    hora_inicio: str,
    excluir_codigo: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    servicio = obtener_servicio(servicio_identificador)
    if not servicio:
        return {
            "disponible": False,
            "motivo": f"No existe un servicio o salón identificado como '{servicio_identificador}'.",
        }

    try:
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return {
            "disponible": False,
            "motivo": f"La fecha '{fecha}' no tiene el formato válido YYYY-MM-DD.",
        }

    ok_horario, hora_fin, msg_horario = validar_dentro_de_horario(
        hora_inicio, servicio["duracion_horas"]
    )
    if not ok_horario:
        return {"disponible": False, "motivo": msg_horario}

    inicio_nuevo, fin_nuevo, _ = calcular_intervalo(hora_inicio, servicio["duracion_horas"])

    conn = obtener_conexion(db_path)
    try:
        query = """
            SELECT codigo, cliente_nombre, servicio_nombre, espacio, fecha, hora_inicio, hora_fin
            FROM reservas
            WHERE fecha = ? AND espacio = ? AND estado = 'activa'
        """
        params: List[Any] = [fecha, servicio["espacio"]]
        if excluir_codigo:
            query += " AND codigo != ?"
            params.append(excluir_codigo)

        filas = conn.execute(query, params).fetchall()
        for fila in filas:
            inicio_exist = _a_minutos(fila["hora_inicio"])
            fin_exist = _a_minutos(fila["hora_fin"])
            if inicio_nuevo < fin_exist and fin_nuevo > inicio_exist:
                return {
                    "disponible": False,
                    "motivo": (
                        f"El espacio '{servicio['espacio']}' ya está ocupado el {fecha} "
                        f"de {fila['hora_inicio']} a {fila['hora_fin']} "
                        f"(Reserva activa {fila['codigo']})."
                    ),
                    "conflicto": dict(fila),
                }

        return {
            "disponible": True,
            "servicio_id": servicio["id"],
            "servicio_nombre": servicio["nombre"],
            "espacio": servicio["espacio"],
            "fecha": fecha,
            "hora_inicio": _a_hora_str(inicio_nuevo),
            "hora_fin": hora_fin,
            "duracion_horas": servicio["duracion_horas"],
            "motivo": (
                f"Espacio '{servicio['espacio']}' disponible el {fecha} "
                f"de {_a_hora_str(inicio_nuevo)} a {hora_fin}."
            ),
        }
    finally:
        conn.close()

def crear_reserva_db(datos: Dict[str, Any], db_path: Optional[Path] = None) -> Dict[str, Any]:
    servicio = obtener_servicio(datos.get("servicio_id", ""))
    if not servicio:
        raise ValueError(f"Servicio no encontrado: {datos.get('servicio_id')}")

    asistentes = int(datos.get("asistentes", 1))
    if asistentes <= 0:
        raise ValueError("La cantidad de asistentes debe ser mayor a cero.")
    if asistentes > servicio["capacidad_maxima"]:
        raise ValueError(
            f"El espacio '{servicio['espacio']}' tiene capacidad máxima de "
            f"{servicio['capacidad_maxima']} personas (solicitado: {asistentes})."
        )

    conn = obtener_conexion(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        disp = verificar_disponibilidad(
            servicio_identificador=servicio["id"],
            fecha=datos["fecha"],
            hora_inicio=datos["hora_inicio"],
            db_path=db_path,
        )
        if not disp["disponible"]:
            conn.rollback()
            raise ValueError(disp["motivo"])

        codigo = _generar_codigo(conn)
        ahora = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            """
            INSERT INTO reservas (
                codigo, cliente_nombre, cliente_contacto, servicio_id,
                servicio_nombre, espacio, fecha, hora_inicio,
                duracion_horas, hora_fin, asistentes, estado,
                notas, creado_en, actualizado_en
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'activa', ?, ?, ?)
            """,
            (
                codigo,
                datos["cliente_nombre"].strip(),
                datos["cliente_contacto"].strip(),
                servicio["id"],
                servicio["nombre"],
                servicio["espacio"],
                datos["fecha"].strip(),
                disp["hora_inicio"],
                servicio["duracion_horas"],
                disp["hora_fin"],
                asistentes,
                (datos.get("notas") or "").strip(),
                ahora,
                ahora,
            ),
        )
        conn.commit()
        fila = conn.execute("SELECT * FROM reservas WHERE codigo = ?", (codigo,)).fetchone()
        return dict(fila)
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()

def listar_reservas_db(
    fecha: Optional[str] = None,
    estado: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    conn = obtener_conexion(db_path)
    try:
        query = "SELECT * FROM reservas WHERE 1=1"
        params: List[Any] = []
        if fecha:
            query += " AND fecha = ?"
            params.append(fecha)
        if estado:
            query += " AND estado = ?"
            params.append(estado)
        query += " ORDER BY fecha ASC, hora_inicio ASC"
        filas = conn.execute(query, params).fetchall()
        return [dict(r) for r in filas]
    finally:
        conn.close()

def obtener_reserva_por_codigo_db(
    codigo: str, db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    conn = obtener_conexion(db_path)
    try:
        fila = conn.execute(
            "SELECT * FROM reservas WHERE UPPER(codigo) = UPPER(?)", (codigo.strip(),)
        ).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()

def modificar_reserva_db(
    codigo: str, cambios: Dict[str, Any], db_path: Optional[Path] = None
) -> Dict[str, Any]:
    actual = obtener_reserva_por_codigo_db(codigo, db_path=db_path)
    if not actual:
        raise LookupError(f"No existe la reserva con código '{codigo}'.")
    if actual["estado"] == "cancelada":
        raise ValueError(f"La reserva '{codigo}' está cancelada y no puede modificarse.")

    nuevo_servicio_id = cambios.get("servicio_id") or actual["servicio_id"]
    servicio = obtener_servicio(nuevo_servicio_id)
    if not servicio:
        raise ValueError(f"Servicio inválido: {nuevo_servicio_id}")

    nueva_fecha = (cambios.get("fecha") or actual["fecha"]).strip()
    nueva_hora = (cambios.get("hora_inicio") or actual["hora_inicio"]).strip()
    nuevos_asistentes = int(cambios.get("asistentes") or actual["asistentes"])
    nuevo_nombre = (cambios.get("cliente_nombre") or actual["cliente_nombre"]).strip()
    nuevo_contacto = (cambios.get("cliente_contacto") or actual["cliente_contacto"]).strip()
    nuevas_notas = (
        cambios["notas"].strip()
        if cambios.get("notas") is not None
        else actual["notas"]
    )

    if nuevos_asistentes <= 0 or nuevos_asistentes > servicio["capacidad_maxima"]:
        raise ValueError(
            f"Capacidad inválida ({nuevos_asistentes}). El espacio '{servicio['espacio']}' "
            f"admite hasta {servicio['capacidad_maxima']} asistentes."
        )

    conn = obtener_conexion(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        disp = verificar_disponibilidad(
            servicio_identificador=servicio["id"],
            fecha=nueva_fecha,
            hora_inicio=nueva_hora,
            excluir_codigo=actual["codigo"],
            db_path=db_path,
        )
        if not disp["disponible"]:
            conn.rollback()
            raise ValueError(disp["motivo"])

        ahora = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            """
            UPDATE reservas
            SET cliente_nombre = ?,
                cliente_contacto = ?,
                servicio_id = ?,
                servicio_nombre = ?,
                espacio = ?,
                fecha = ?,
                hora_inicio = ?,
                duracion_horas = ?,
                hora_fin = ?,
                asistentes = ?,
                notas = ?,
                actualizado_en = ?
            WHERE codigo = ?
            """,
            (
                nuevo_nombre,
                nuevo_contacto,
                servicio["id"],
                servicio["nombre"],
                servicio["espacio"],
                nueva_fecha,
                disp["hora_inicio"],
                servicio["duracion_horas"],
                disp["hora_fin"],
                nuevos_asistentes,
                nuevas_notas,
                ahora,
                actual["codigo"],
            ),
        )
        conn.commit()
        actualizada = conn.execute(
            "SELECT * FROM reservas WHERE codigo = ?", (actual["codigo"],)
        ).fetchone()
        return dict(actualizada)
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()

def cancelar_reserva_db(codigo: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    actual = obtener_reserva_por_codigo_db(codigo, db_path=db_path)
    if not actual:
        raise LookupError(f"No existe la reserva con código '{codigo}'.")
    if actual["estado"] == "cancelada":
        return actual

    conn = obtener_conexion(db_path)
    try:
        ahora = datetime.now().isoformat(timespec="seconds")
        with conn:
            conn.execute(
                "UPDATE reservas SET estado = 'cancelada', actualizado_en = ? WHERE codigo = ?",
                (ahora, actual["codigo"]),
            )
        fila = conn.execute(
            "SELECT * FROM reservas WHERE codigo = ?", (actual["codigo"],)
        ).fetchone()
        return dict(fila)
    finally:
        conn.close()
