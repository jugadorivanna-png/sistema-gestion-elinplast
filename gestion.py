import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import requests 
from fpdf import FPDF

# --- CONFIGURACIÓN ---
USUARIOS_PERMITIDOS = {
    "ElinplastRD": {"clave": "elinplast001", "rol": "super"},
    "JOR": {"clave": "jor123", "rol": "restringido"},
    "JR": {"clave": "jr123", "rol": "restringido"},
    "FR": {"clave": "FR123", "rol": "restringido"},
    "AA": {"clave": "AA123", "rol": "restringido"}
}

def crear_db():
    conn = sqlite3.connect('gestion_pasantias.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ordenes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, empresa_entrega TEXT, persona_recibe TEXT, 
        equipo TEXT, modelo TEXT, serial TEXT, estado TEXT, tecnico TEXT, fecha_salida TEXT, 
        observaciones TEXT, nro_orden TEXT, prioridad TEXT)''')
    conn.commit()
    conn.close()

def obtener_datos():
    conn = sqlite3.connect('gestion_pasantias.db')
    df = pd.read_sql_query('SELECT * FROM ordenes ORDER BY id DESC', conn)
    conn.close()
    return df

def disparar_alerta_api(nro, eq, tec, est):
    TOKEN = "8977110110:AAEyRn6N_G63isqG9gOhdjnzLp0bPKphoQM"
    CHAT = "549012168"
    msg = f"ACTUALIZACIÓN DE TALLER\n\nOrden: {nro}\nEquipo: {eq}\nTécnico: {tec}\nEstado: *{est}*"
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={'chat_id': CHAT, 'text': msg, 'parse_mode': 'Markdown'})
    except: pass

def generar_pdf(info):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "PRESUPUESTO ELINPLAST", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Orden: {info['nro_orden']} | Cliente: {info['empresa_entrega']}", ln=True)
    pdf.cell(0, 10, f"Equipo: {info['equipo']} | Serial: {info['serial']}", ln=True)
    pdf.output("presupuesto.pdf")
    with open("presupuesto.pdf", "rb") as f: return f.read()

def main():
    st.set_page_config(page_title="Elinplast - Control", layout="wide")
    crear_db()
    
    archivos = os.listdir(".")
    logo = next((f for f in archivos if f.lower().startswith("logo_elinplast")), None)

    if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

    if not st.session_state['autenticado']:
        if logo: st.image(logo, width=200)
        st.title("Control de Acceso")
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if user in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[user]["clave"] == pw:
                st.session_state['autenticado'] = True
                st.session_state['usuario_activo'] = user
                st.rerun()
            else: st.error("Acceso denegado")
    else:
        user = st.session_state['usuario_activo']
        rol = USUARIOS_PERMITIDOS[user]['rol']
        
        with st.sidebar:
            if logo: st.image(logo, use_container_width=True)
            st.markdown("### Panel Administrativo")
            st.info(f"Usuario: {user}\nRol: {rol.upper()}")
            
            # Lógica forzada para el superusuario
            if user == "ElinplastRD":
                menu = ["Panel de Control", "Registrar Entrada", "Asignar y Priorizar", "Registrar Salida", "Generar Presupuesto", "Historial Corporativo"]
            else:
                menu = ["Panel de Control", "Registrar Salida", "Historial Corporativo"]
                
            opcion = st.radio("Navegación", menu)
            
            if st.button("Cerrar Sesión"):
                st.session_state['autenticado'] = False
                st.rerun()

        st.title("SISTEMA DE GESTIÓN DE SERVICIOS")
        
        if opcion == "Panel de Control":
            d = obtener_datos()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Órdenes Totales", len(d))
            c2.metric("Espera Repuestos", len(d[d['estado'] == 'En Espera de Repuestos']))
            c3.metric("Equipos en Taller", len(d[d['fecha_salida'] == '']))
            c4.metric("Entregados", len(d[d['fecha_salida'] != '']))
            
            st.markdown("### Leyenda de Prioridades (Semáforo de Alertas)")
            st.markdown("""<div style="display: flex; justify-content: space-between; background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #ddd;">
                <div>🔴 <b>Emergencia</b></div><div>🟠 <b>Garantía</b></div><div>🟡 <b>Solo revisión</b></div><div>🟢 <b>Estándar</b></div></div>""", unsafe_allow_html=True)

        elif opcion == "Registrar Entrada":
            with st.form("ent"):
                nro = st.text_input("Número de Orden")
                cl = st.text_input("Cliente")
                eq = st.text_input("Equipo")
                pr = st.selectbox("Prioridad", ["🟢 Estándar", "🔴 Emergencia", "🟠 Garantía", "🟡 Solo revisión"])
                ser = st.text_input("Serial")
                if st.form_submit_button("Guardar"):
                    conn = sqlite3.connect('gestion_pasantias.db')
                    c = conn.cursor()
                    c.execute('INSERT INTO ordenes (nro_orden, empresa_entrega, equipo, serial, prioridad, estado) VALUES (?,?,?,?,?,?)', (nro, cl, eq, ser, pr, "Recibido"))
                    conn.commit()
                    conn.close()
                    st.success("Guardado correctamente.")
        
        elif opcion == "Asignar y Priorizar":
            d = obtener_datos()
            id_sel = st.selectbox("Seleccionar Orden", d['id'].tolist())
            te = st.selectbox("Técnico", ["JOR", "JR", "FR", "AA"])
            pr = st.selectbox("Prioridad", ["🟢 Estándar", "🔴 Emergencia", "🟠 Garantía", "🟡 Solo revisión"])
            if st.button("Actualizar Asignación"):
                conn = sqlite3.connect('gestion_pasantias.db')
                c = conn.cursor()
                c.execute("UPDATE ordenes SET tecnico=?, prioridad=? WHERE id=?", (te, pr, id_sel))
                conn.commit()
                conn.close()
                disparar_alerta_api(d[d['id']==id_sel]['nro_orden'].values[0], d[d['id']==id_sel]['equipo'].values[0], te, f"Asignación: {pr}")
                st.success("Actualizado y notificado.")

        elif opcion == "Registrar Salida":
            d = obtener_datos()
            d = d[d['fecha_salida'] == '']
            if not d.empty:
                id_sel = st.selectbox("Seleccionar Orden", d['id'].tolist())
                te = st.text_input("Técnico", value=user)
                est = st.selectbox("Estado Final", ["Reparado", "Entregado", "No Reparable"])
                ob = st.text_area("Observaciones")
                if st.button("Guardar Salida"):
                    conn = sqlite3.connect('gestion_pasantias.db')
                    c = conn.cursor()
                    c.execute("UPDATE ordenes SET tecnico=?, fecha_salida=?, observaciones=?, estado=? WHERE id=?", (te, str(datetime.now().date()), ob, est, id_sel))
                    conn.commit()
                    conn.close()
                    info = d[d['id'] == id_sel].iloc[0]
                    disparar_alerta_api(info['nro_orden'], info['equipo'], te, est)
                    st.success("Cierre almacenado y notificación enviada.")
                    st.rerun()
            else: st.info("No hay órdenes pendientes.")
            
        elif opcion == "Generar Presupuesto":
            d = obtener_datos()
            sel = st.selectbox("Seleccionar orden", d['id'].tolist())
            info = d[d['id'] == sel].iloc[0]
            if st.button("Generar PDF"):
                bytes_pdf = generar_pdf(info)
                st.download_button("Descargar PDF", bytes_pdf, "presupuesto.pdf")

        elif opcion == "Historial Corporativo":
            st.dataframe(obtener_datos(), use_container_width=True, height=500)

if __name__ == "__main__":
    main()