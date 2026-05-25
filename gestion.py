import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import requests 

# --- CONTROL DE DEFENSA ---
try:
    from fpdf import FPDF
    PDF_DISPONIBLE = True
except ImportError:
    PDF_DISPONIBLE = False

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
    c.execute('CREATE TABLE IF NOT EXISTS ordenes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, empresa_entrega TEXT, persona_recibe TEXT, equipo TEXT, modelo TEXT, serial TEXT, estado TEXT, tecnico TEXT, fecha_salida TEXT, observaciones TEXT, nro_orden TEXT, prioridad TEXT)')
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

# --- INTERFAZ ---
def main():
    st.set_page_config(page_title="Elinplast - Control", layout="wide")
    crear_db()

    # Detectar Logo
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
            menu = ["Panel de Control", "Registrar Entrada", "Asignar y Priorizar", "Registrar Salida", "Generar Presupuesto", "Historial Corporativo"] if rol == "super" else ["Panel de Control", "Registrar Salida", "Historial Corporativo"]
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
            
        elif opcion == "Registrar Salida":
            d = obtener_datos()
            d = d[d['fecha_salida'] == ''] # Solo mostrar pendientes
            if not d.empty:
                id_sel = st.selectbox("Seleccionar Orden", d['id'].tolist(), format_func=lambda x: f"Orden: {d[d['id']==x]['nro_orden'].values[0]} - {d[d['id']==x]['equipo'].values[0]}")
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

        elif opcion == "Historial Corporativo":
            st.dataframe(obtener_datos(), use_container_width=True, height=500)

if __name__ == "__main__":
    main()