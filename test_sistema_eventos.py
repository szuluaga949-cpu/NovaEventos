import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

import almacen_sqlite
import main
import consulta_llm


def configurar_entorno_pruebas():
    temp_dir = tempfile.mkdtemp()
    test_db = Path(temp_dir) / "test_reservas.db"
    almacen_sqlite.DB_PATH = test_db
    almacen_sqlite.inicializar_bd(test_db, poblar_semilla=True)
    client = TestClient(main.app)

    def mock_llamar_api(metodo, ruta, params=None, json_body=None):
        resp = client.request(metodo, ruta, params=params, json=json_body)
        datos = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return {"ok": False, "status": resp.status_code, "error": datos.get("detail", "Error")}
        return {"ok": True, "status": resp.status_code, "data": datos}

    consulta_llm._llamar_api = mock_llamar_api
    consulta_llm.GROQ_API_KEY = ""
    return client, test_db


def test_1_conversacion_varios_turnos_y_creacion():
    _, _ = configurar_entorno_pruebas()
    sid = "test_multi_turno"
    consulta_llm.reiniciar_sesion(sid)

    r1 = consulta_llm.procesar_mensaje(sid, "Quiero reservar una Conferencia Corporativa para el 2026-12-01")
    assert "hora" in r1.lower()

    r2 = consulta_llm.procesar_mensaje(sid, "A las 10:00 para 60 asistentes")
    assert "nombre" in r2.lower()

    r3 = consulta_llm.procesar_mensaje(sid, "Me llamo Santiago Zuluaga y mi contacto es 3005551122")
    assert "confirmas" in r3.lower()

    r4 = consulta_llm.procesar_mensaje(sid, "Sí, confirmo")
    assert "NOVA-1004" in r4


def test_2_dos_sesiones_y_reinicio():
    _, _ = configurar_entorno_pruebas()
    consulta_llm.reiniciar_sesion("S1")
    consulta_llm.reiniciar_sesion("S2")

    consulta_llm.procesar_mensaje("S1", "Quiero reservar una boda para el 2026-12-10")
    consulta_llm.procesar_mensaje("S2", "Quiero un taller para el 2026-12-12")

    assert consulta_llm.obtener_sesion("S1")["borrador"]["servicio_id"] == "EVT-BODA"
    assert consulta_llm.obtener_sesion("S2")["borrador"]["servicio_id"] == "EVT-WORK"

    consulta_llm.reiniciar_sesion("S1")
    assert consulta_llm.obtener_sesion("S1")["borrador"]["servicio_id"] is None
    assert consulta_llm.obtener_sesion("S2")["borrador"]["servicio_id"] == "EVT-WORK"


def test_3_rechazo_intervalos_ocupados_y_cancelacion():
    client, _ = configurar_entorno_pruebas()

    cruce = client.post(
        "/reservas",
        json={
            "cliente_nombre": "Pedro Pérez",
            "cliente_contacto": "3100001122",
            "servicio_id": "EVT-CORP",
            "fecha": "2026-11-15",
            "hora_inicio": "11:00",
            "asistentes": 50,
        },
    )
    assert cruce.status_code == 409
    assert "NOVA-1001" in cruce.json()["detail"]

    canc = client.delete("/reservas/NOVA-1001")
    assert canc.status_code == 200
    assert canc.json()["reserva"]["estado"] == "cancelada"

    exito = client.post(
        "/reservas",
        json={
            "cliente_nombre": "Pedro Pérez",
            "cliente_contacto": "3100001122",
            "servicio_id": "EVT-CORP",
            "fecha": "2026-11-15",
            "hora_inicio": "11:00",
            "asistentes": 50,
        },
    )
    assert exito.status_code == 201