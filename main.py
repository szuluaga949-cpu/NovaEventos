from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from almacen_sqlite import (
    cancelar_reserva_db,
    cargar_catalogo,
    crear_reserva_db,
    inicializar_bd,
    listar_reservas_db,
    modificar_reserva_db,
    obtener_reserva_por_codigo_db,
    verificar_disponibilidad,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar_bd()
    yield


app = FastAPI(
    title="NovaEventos API",
    description="API REST para gestión de reservas de salones y eventos con persistencia en SQLite.",
    version="2.0.0",
    lifespan=lifespan,
)


class ReservaCrearInput(BaseModel):
    cliente_nombre: str = Field(..., min_length=2, description="Nombre completo del cliente")
    cliente_contacto: str = Field(..., min_length=5, description="Teléfono o correo del cliente")
    servicio_id: str = Field(..., description="ID o nombre del servicio/salón")
    fecha: str = Field(..., description="Fecha en formato YYYY-MM-DD")
    hora_inicio: str = Field(..., description="Hora de inicio en formato HH:MM")
    asistentes: int = Field(..., gt=0, description="Número de asistentes")
    notas: Optional[str] = Field(default="", description="Observaciones adicionales")


class ReservaModificarInput(BaseModel):
    cliente_nombre: Optional[str] = None
    cliente_contacto: Optional[str] = None
    servicio_id: Optional[str] = None
    fecha: Optional[str] = None
    hora_inicio: Optional[str] = None
    asistentes: Optional[int] = Field(default=None, gt=0)
    notas: Optional[str] = None


@app.get("/health")
def health_check():
    return {"status": "ok", "servicio": "NovaEventos API", "motor_bd": "SQLite"}


@app.get("/catalogo")
def obtener_catalogo():
    return cargar_catalogo()


@app.get("/disponibilidad")
def consultar_disponibilidad(
    servicio_id: str = Query(..., description="ID o nombre del servicio"),
    fecha: str = Query(..., description="Fecha YYYY-MM-DD"),
    hora_inicio: str = Query(..., description="Hora HH:MM"),
):
    return verificar_disponibilidad(
        servicio_identificador=servicio_id,
        fecha=fecha,
        hora_inicio=hora_inicio,
    )


@app.get("/reservas")
def listar_reservas(
    fecha: Optional[str] = Query(default=None),
    estado: Optional[str] = Query(default=None),
):
    return {"reservas": listar_reservas_db(fecha=fecha, estado=estado)}


@app.get("/reservas/{codigo}")
def consultar_reserva(codigo: str):
    reserva = obtener_reserva_por_codigo_db(codigo)
    if not reserva:
        raise HTTPException(status_code=404, detail=f"Reserva '{codigo}' no encontrada.")
    return reserva


@app.post("/reservas", status_code=201)
def crear_reserva(payload: ReservaCrearInput):
    try:
        creada = crear_reserva_db(payload.model_dump())
        return {
            "mensaje": f"Reserva creada exitosamente con código {creada['codigo']}.",
            "reserva": creada,
        }
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.put("/reservas/{codigo}")
def modificar_reserva(codigo: str, payload: ReservaModificarInput):
    try:
        actualizada = modificar_reserva_db(
            codigo, payload.model_dump(exclude_none=True)
        )
        return {
            "mensaje": f"Reserva {actualizada['codigo']} modificada correctamente.",
            "reserva": actualizada,
        }
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.delete("/reservas/{codigo}")
def cancelar_reserva(codigo: str):
    try:
        cancelada = cancelar_reserva_db(codigo)
        return {
            "mensaje": (
                f"Reserva {cancelada['codigo']} cancelada. "
                f"El horario {cancelada['hora_inicio']}-{cancelada['hora_fin']} "
                f"del {cancelada['fecha']} en {cancelada['espacio']} ha quedado libre."
            ),
            "reserva": cancelada,
        }
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))