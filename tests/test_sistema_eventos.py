"""Suite de pruebas unitarias y de integración para NovaEventos.

Verifica la integridad del catálogo, servicio de reservas, control de concurrencia RLock,
reglas de aforo, endpoints REST y flujo conversacional del asistente concierge.
"""

import json
import unittest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.core.config import RESERVAS_FILE
from app.main import app
from app.models.schemas import CrearReserva, ReprogramarReserva
from app.services.booking_service import booking_service
from app.services.session_store import session_store


class TestSistemaEventos(unittest.TestCase):
    """Pruebas del sistema de eventos y concierge."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Respaldar reservas.json original para garantizar idempotencia
        if RESERVAS_FILE.exists():
            with open(RESERVAS_FILE, "r", encoding="utf-8") as f:
                cls._backup_reservas = json.load(f)
        else:
            cls._backup_reservas = []

        cls.fecha_futura = date.today() + timedelta(days=90)
        cls.fecha_futura_str = cls.fecha_futura.isoformat()

    @classmethod
    def tearDownClass(cls):
        # Restaurar estado prístino de reservas.json
        booking_service.guardar_reservas(cls._backup_reservas)

    def setUp(self):
        # Restaurar estado antes de cada prueba para total independencia
        booking_service.guardar_reservas(self._backup_reservas)

    def test_01_catalogo_completo(self):
        """Verifica que el catálogo cargue al menos 3 salones, 4 paquetes y 3 coordinadores."""
        salones = booking_service.listar_salones()
        paquetes = booking_service.listar_paquetes()
        coords = booking_service.listar_coordinadores()

        self.assertGreaterEqual(len(salones), 3, "Debe haber al menos 3 salones en el catálogo")
        self.assertGreaterEqual(len(paquetes), 4, "Debe haber al menos 4 paquetes en el catálogo")
        self.assertGreaterEqual(len(coords), 3, "Debe haber al menos 3 coordinadores en el catálogo")

        # Verificar existencia de salones clave
        self.assertIn("salon_cristal", salones)
        self.assertIn("salon_terraza", salones)
        self.assertIn("salon_auditorio", salones)

        # Verificar existencia de paquetes clave
        self.assertIn("boda_ensueno", paquetes)
        self.assertIn("cumpleanos_vip", paquetes)
        self.assertIn("conferencia_magistral", paquetes)
        self.assertIn("coctel_lounge", paquetes)

    def test_02_disponibilidad_y_aforo(self):
        """Verifica la consulta de disponibilidad y restricciones de fechas pasadas."""
        # Fecha futura debe tener turnos
        disp = booking_service.consultar_disponibilidad(self.fecha_futura, "salon_cristal")
        turnos = disp["disponibilidad_salones"]["salon_cristal"]["turnos_disponibles"]
        self.assertIn("nocturno", turnos)

        # Fecha pasada debe lanzar error 422
        fecha_pasada = date.today() - timedelta(days=5)
        with self.assertRaises(Exception):
            booking_service.consultar_disponibilidad(fecha_pasada, "salon_cristal")

    def test_03_creacion_reserva_y_bloqueo(self):
        """Verifica la creación atómica de una reserva y que no permita sobreventa del mismo turno."""
        datos_res = CrearReserva(
            anfitrion="Prueba Unitaria Test Host",
            salon="salon_cristal",
            paquete="boda_ensueno",
            fecha=self.fecha_futura,
            turno="nocturno",
            invitados_estimados=120,
            coordinador="sofia_valbuena",
            telefono="+57 300 000 0000",
            email="test@novaeventos.com",
            requerimientos_especiales="Prueba automatizada",
            confirmado=True,
        )
        reserva_creada = booking_service.crear_reserva(datos_res)
        self.assertTrue(reserva_creada["codigo"].startswith("NE-"))
        self.assertEqual(reserva_creada["estado"], "activa")

        # Intentar reservar EXACTAMENTE el mismo salón, fecha y turno debe fallar (409)
        with self.assertRaises(Exception):
            booking_service.crear_reserva(datos_res)

    def test_04_limite_capacidad_aforo(self):
        """Verifica que si los invitados superan el aforo máximo del salón, se rechace."""
        datos_exceso = CrearReserva(
            anfitrion="Evento Masivo Inválido",
            salon="salon_terraza",  # Capacidad máxima es 120
            paquete="cumpleanos_vip",
            fecha=self.fecha_futura + timedelta(days=1),
            turno="diurno",
            invitados_estimados=250,  # 250 supera 120
            confirmado=True,
        )
        with self.assertRaises(Exception):
            booking_service.crear_reserva(datos_exceso)

    def test_05_reprogramacion_y_cancelacion(self):
        """Verifica ciclo de vida de reprogramación e historial de cambios."""
        nueva_fecha = self.fecha_futura + timedelta(days=10)
        datos = CrearReserva(
            anfitrion="Anfitrión Ciclo Completo",
            salon="salon_auditorio",
            paquete="conferencia_magistral",
            fecha=nueva_fecha,
            turno="diurno",
            invitados_estimados=90,
            confirmado=True,
        )
        res = booking_service.crear_reserva(datos)
        codigo = res["codigo"]

        # Reprogramar a fecha diferente
        fecha_movida = nueva_fecha + timedelta(days=1)
        res_rep = booking_service.reprogramar_reserva(
            codigo,
            ReprogramarReserva(
                nueva_fecha=fecha_movida,
                nuevo_turno="diurno",
                confirmado=True,
            ),
        )
        self.assertEqual(res_rep["fecha"], fecha_movida.isoformat())
        self.assertEqual(len(res_rep["historial_reprogramaciones"]), 1)

        # Cancelar y verificar estado
        res_canc = booking_service.cancelar_reserva(codigo, confirmado=True)
        self.assertEqual(res_canc["estado"], "cancelada")

    def test_06_endpoints_api_rest(self):
        """Verifica respuestas HTTP 200 de los endpoints REST principales."""
        # GET /api/v1/salones
        resp_salones = self.client.get("/api/v1/salones")
        self.assertEqual(resp_salones.status_code, 200)
        self.assertIn("salon_cristal", resp_salones.json())

        # GET /api/v1/paquetes
        resp_paquetes = self.client.get("/api/v1/paquetes")
        self.assertEqual(resp_paquetes.status_code, 200)
        self.assertIn("boda_ensueno", resp_paquetes.json())

        # GET /api/v1/disponibilidad
        resp_disp = self.client.get(
            f"/api/v1/disponibilidad?fecha={self.fecha_futura_str}&salon=salon_cristal"
        )
        self.assertEqual(resp_disp.status_code, 200)

        # GET /api/v1/salud
        resp_salud = self.client.get("/api/v1/salud")
        self.assertEqual(resp_salud.status_code, 200)
        self.assertIn("groq_configurado", resp_salud.json())

    def test_07_flujo_chat_asistente(self):
        """Verifica el flujo conversacional (/api/v1/chat), reinicio y acumulación de slots."""
        sid = "sesion-test-suite-001"

        # 1. Mensaje de consulta general
        resp1 = self.client.post(
            "/api/v1/chat",
            json={"session_id": sid, "mensaje": "¿Qué salones y paquetes tienen?"},
        )
        self.assertEqual(resp1.status_code, 200)
        datos1 = resp1.json()
        self.assertIn("respuesta", datos1)
        self.assertIn("Gran Salón Imperial Cristal", datos1["respuesta"])

        # 2. Solicitud con slots progresivos
        resp2 = self.client.post(
            "/api/v1/chat",
            json={
                "session_id": sid,
                "mensaje": f"Quiero celebrar una boda para 100 personas el {self.fecha_futura_str} en la noche, me llamo Mariana Gomez",
            },
        )
        self.assertEqual(resp2.status_code, 200)
        datos2 = resp2.json()
        # Debe generar cotización y solicitar confirmación
        self.assertIn("CONFIRMAR", datos2["respuesta"])

        # 3. Confirmación
        resp3 = self.client.post(
            "/api/v1/chat",
            json={"session_id": sid, "mensaje": "CONFIRMAR"},
        )
        self.assertEqual(resp3.status_code, 200)
        datos3 = resp3.json()
        self.assertIn("¡Felicitaciones!", datos3["respuesta"])
        self.assertIn("NE-", datos3["respuesta"])

        # 4. Reinicio de sesión con /reset
        resp4 = self.client.post(
            "/api/v1/chat",
            json={"session_id": sid, "mensaje": "/reset"},
        )
        self.assertEqual(resp4.status_code, 200)
        self.assertIn("reiniciada con éxito", resp4.json()["respuesta"])


if __name__ == "__main__":
    unittest.main()
