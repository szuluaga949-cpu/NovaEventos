import os
import gradio as gr
import pandas as pd
from consulta_llm import procesar_mensaje, reiniciar_sesion
import almacen_sqlite

API_URL = os.getenv("CHATBOT_API_URL", "http://127.0.0.1:8011")


def responder(mensaje, historial, session_id):
    if not session_id:
        session_id = "default"
    
    if not mensaje.strip():
        return historial, session_id, ""
    
    respuesta_bot = procesar_mensaje(session_id, mensaje)
    
    historial = historial or []
    historial.append({"role": "user", "content": mensaje})
    historial.append({"role": "assistant", "content": respuesta_bot})
    
    return historial, session_id, ""


def limpiar_chat(session_id):
    if not session_id:
        session_id = "default"
    reiniciar_sesion(session_id)
    return [], f"Sesión '{session_id}' reiniciada correctamente."


def obtener_tabla_reservas(filtro_estado="Todas"):
    try:
        estado = None
        if filtro_estado == "Solo Activas":
            estado = "activa"
        elif filtro_estado == "Canceladas":
            estado = "cancelada"
        
        filas = almacen_sqlite.listar_reservas_db(estado=estado)
        if not filas:
            return pd.DataFrame(columns=[
                "Código", "Estado", "Cliente", "Contacto", "Servicio", 
                "Espacio", "Fecha", "Horario", "Asistentes", "Notas"
            ])
        
        data = []
        for r in filas:
            icono_estado = "🟢 Activa" if r["estado"] == "activa" else "🔴 Cancelada"
            data.append({
                "Código": r["codigo"],
                "Estado": icono_estado,
                "Cliente": r["cliente_nombre"],
                "Contacto": r["cliente_contacto"],
                "Servicio": r["servicio_nombre"],
                "Espacio": r["espacio"],
                "Fecha": r["fecha"],
                "Horario": f"{r['hora_inicio']} - {r['hora_fin']}",
                "Asistentes": r["asistentes"],
                "Notas": r.get("notas", "")
            })
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame([{"Error": f"No se pudo cargar la base de datos: {str(e)}"}])


def cancelar_reserva_ui(codigo, filtro_actual):
    codigo_limpio = (codigo or "").strip().upper()
    if not codigo_limpio:
        return (
            obtener_tabla_reservas(filtro_actual),
            "⚠️ **Atención:** Por favor ingresa el código de la reserva que deseas cancelar (ej: `NOVA-1001`).",
            ""
        )
    
    try:
        reserva = almacen_sqlite.obtener_reserva_por_codigo_db(codigo_limpio)
        if not reserva:
            return (
                obtener_tabla_reservas(filtro_actual),
                f"❌ **Error:** No existe ninguna reserva registrada con el código `{codigo_limpio}`.",
                ""
            )
        
        if reserva["estado"] == "cancelada":
            return (
                obtener_tabla_reservas(filtro_actual),
                f"ℹ️ **Información:** La reserva `{codigo_limpio}` ya se encuentra cancelada.",
                ""
            )
        
        cancelada = almacen_sqlite.cancelar_reserva_db(codigo_limpio)
        nueva_tabla = obtener_tabla_reservas(filtro_actual)
        msg_exito = (
            f"✅ **¡Reserva `{cancelada['codigo']}` cancelada exitosamente!**\n\n"
            f"- **Cliente:** {cancelada['cliente_nombre']}\n"
            f"- **Espacio liberado:** {cancelada['espacio']}\n"
            f"- **Horario liberado:** {cancelada['fecha']} de {cancelada['hora_inicio']} a {cancelada['hora_fin']}\n\n"
            f"🎉 El espacio y horario han quedado liberados inmediatamente para nuevas reservas en el asistente."
        )
        return nueva_tabla, msg_exito, ""
    except Exception as e:
        return (
            obtener_tabla_reservas(filtro_actual),
            f"❌ **Error al procesar cancelación:** {str(e)}",
            ""
        )


with gr.Blocks(title="NovaEventos - Asistente & Gestión de Reservas") as demo:
    gr.Markdown("# 🎪 NovaEventos - Plataforma de Gestión de Eventos y Reservas")
    
    with gr.Tabs():
        with gr.Tab("💬 Asistente IA de Reservas"):
            gr.Markdown("Chatea con nuestro asistente para cotizar, verificar disponibilidad y gestionar reservas en tiempo real.")
            
            with gr.Row():
                session_input = gr.Textbox(value="usuario_principal", label="ID de Sesión (para múltiples usuarios)", scale=3)
                btn_reiniciar = gr.Button("Reiniciar Sesión", scale=1)
            
            chatbot = gr.Chatbot(label="Conversación con NovaEventos", height=420)
            
            with gr.Row():
                msg_input = gr.Textbox(placeholder="Escribe tu mensaje aquí (ej. Quiero reservar una conferencia para el 2026-11-15)...", label="Tu mensaje", scale=4)
                btn_enviar = gr.Button("Enviar", variant="primary", scale=1)
            
            status_box = gr.Textbox(label="Estado del sistema", interactive=False)

            msg_input.submit(responder, [msg_input, chatbot, session_input], [chatbot, session_input, msg_input])
            btn_enviar.click(responder, [msg_input, chatbot, session_input], [chatbot, session_input, msg_input])
            btn_reiniciar.click(limpiar_chat, [session_input], [chatbot, status_box])

        with gr.Tab("📋 Panel y Tabla de Reservas"):
            gr.Markdown("### 📅 Registro General de Reservas (SQLite en Vivo)")
            gr.Markdown(
                "Consulta todas las reservas guardadas en el sistema. "
                "Si un usuario intenta reservar un espacio y horario que ya esté aquí como **🟢 Activa**, "
                "el asistente le avisará inmediatamente que está ocupado y le pedirá cambiar la fecha u hora."
            )
            
            with gr.Row():
                filtro_estado = gr.Radio(["Todas", "Solo Activas", "Canceladas"], value="Todas", label="Filtrar reservas por estado", scale=3)
                btn_refrescar = gr.Button("🔄 Actualizar Tabla", variant="secondary", scale=1)
            
            tabla_reservas = gr.Dataframe(
                value=obtener_tabla_reservas,
                interactive=False,
                wrap=True,
                label="Reservas Registradas en Base de Datos"
            )
            
            gr.Markdown("---")
            gr.Markdown("### ❌ Cancelar una Reserva")
            gr.Markdown("Ingresa el código de la reserva que deseas cancelar. El horario se liberará inmediatamente para nuevas reservas.")
            
            with gr.Row():
                codigo_cancelar_input = gr.Textbox(
                    placeholder="Ej. NOVA-1001",
                    label="Código de la Reserva a Cancelar",
                    scale=3
                )
                btn_cancelar = gr.Button("Cancelar Reserva", variant="stop", scale=1)
            
            cancelar_status = gr.Markdown()

            # Eventos del panel de reservas
            filtro_estado.change(obtener_tabla_reservas, [filtro_estado], [tabla_reservas])
            btn_refrescar.click(obtener_tabla_reservas, [filtro_estado], [tabla_reservas])
            btn_cancelar.click(
                cancelar_reserva_ui,
                [codigo_cancelar_input, filtro_estado],
                [tabla_reservas, cancelar_status, codigo_cancelar_input]
            )
            codigo_cancelar_input.submit(
                cancelar_reserva_ui,
                [codigo_cancelar_input, filtro_estado],
                [tabla_reservas, cancelar_status, codigo_cancelar_input]
            )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False, theme=gr.themes.Soft())
