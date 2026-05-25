import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import requests 

# --- CONTROL DE DEFENSA: Importación segura de la librería de PDFs ---
try:
    from fpdf import FPDF
    PDF_DISPONIBLE = True
except ImportError:
    PDF_DISPONIBLE = False

# --- CREDENCIALES DE ACCESO Y MATRIZ DE ROLES ---
USUARIOS_PERMITIDOS = {
    "ElinplastRD": {"clave": "elinplast001", "rol": "super"},
    "JOR": {"clave": "jor123", "rol": "restringido"},
    "JR": {"clave": "jr123", "rol": "restringido"},
    "FR": {"clave": "FR123", "rol": "restringido"},
    "AA": {"clave": "AA123", "rol": "restringido"}
}

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
def crear_db():
    conn = sqlite3.connect('gestion_pasantias.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS ordenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            empresa_entrega TEXT,
            persona_recibe TEXT,
            equipo TEXT,
            modelo TEXT,
            serial TEXT,
            estado TEXT
        )
    ''')
    try: c.execute("ALTER TABLE ordenes ADD COLUMN tecnico TEXT")
    except sqlite3.OperationalError: pass
    try: c.execute("ALTER TABLE ordenes ADD COLUMN fecha_salida TEXT")
    except sqlite3.OperationalError: pass
    try: c.execute("ALTER TABLE ordenes ADD COLUMN observaciones TEXT")
    except sqlite3.OperationalError: pass
    try: c.execute("ALTER TABLE ordenes ADD COLUMN nro_orden TEXT")
    except sqlite3.OperationalError: pass
    try: c.execute("ALTER TABLE ordenes ADD COLUMN prioridad TEXT")
    except sqlite3.OperationalError: pass
    
    conn.commit()
    conn.close()

def guardar_datos(nro_orden, empresa, recibe, equipo, modelo, serial, estado, prioridad):
    conn = sqlite3.connect('gestion_pasantias.db')
    c = conn.cursor()
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO ordenes (fecha, nro_orden, empresa_entrega, persona_recibe, equipo, modelo, serial, estado, tecnico, fecha_salida, observaciones, prioridad)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', '', '', ?)
    ''', (fecha_actual, nro_orden, empresa, recibe, equipo, modelo, serial, estado, prioridad))
    conn.commit()
    conn.close()

def asignar_tecnico_y_prioridad(id_orden, tecnico, prioridad):
    conn = sqlite3.connect('gestion_pasantias.db')
    c = conn.cursor()
    c.execute('''
        UPDATE ordenes 
        SET tecnico = ?, prioridad = ?
        WHERE id = ?
    ''', (tecnico, prioridad, id_orden))
    
    # Obtener info para alerta
    c.execute("SELECT nro_orden, equipo FROM ordenes WHERE id = ?", (id_orden,))
    datos_orden = c.fetchone()
    conn.commit()
    conn.close()
    
    if datos_orden:
        disparar_alerta_api(datos_orden[0], datos_orden[1], tecnico, f"Asignación: {prioridad}")

def actualizar_salida(id_orden, tecnico, fecha_salida, observaciones, nuevo_estado):
    conn = sqlite3.connect('gestion_pasantias.db')
    c = conn.cursor()
    c.execute('''
        UPDATE ordenes 
        SET tecnico = ?, fecha_salida = ?, observaciones = ?, estado = ?
        WHERE id = ?
    ''', (tecnico, fecha_salida, observaciones, nuevo_estado, id_orden))
    conn.commit()
    conn.close()

def eliminar_orden(id_orden):
    conn = sqlite3.connect('gestion_pasantias.db')
    c = conn.cursor()
    c.execute("DELETE FROM ordenes WHERE id = ?", (id_orden,))
    conn.commit()
    conn.close()

def obtener_datos():
    conn = sqlite3.connect('gestion_pasantias.db')
    df = pd.read_sql_query('''
        SELECT id, prioridad, nro_orden, fecha, empresa_entrega, persona_recibe, equipo, modelo, serial, estado, tecnico, fecha_salida, observaciones 
        FROM ordenes 
        ORDER BY id DESC
    ''', conn)
    conn.close()
    if 'prioridad' in df.columns: df['prioridad'] = df['prioridad'].fillna('🟢 Estándar')
    return df

# --- API DE NOTIFICACIONES ---
def disparar_alerta_api(nro_orden, equipo, tecnico, nuevo_estado):
    TOKEN_BOT = "8977110110:AAEyRn6N_G63isqG9gOhdjnzLp0bPKphoQM" 
    CHAT_ID_ADMIN = "549012168"
    url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
    mensaje = f"ACTUALIZACIÓN DE TALLER\n\nOrden Nro: {nro_orden}\nEquipo: {equipo}\nTécnico: {tecnico}\nNuevo Estado: *{nuevo_estado}*"
    try:
        requests.post(url, data={'chat_id': CHAT_ID_ADMIN, 'text': mensaje, 'parse_mode': 'Markdown'})
    except: pass 

# --- MOTOR DE GENERACIÓN DE PDF ---
def fabricar_pdf_cotizacion(datos_orden, mano_obra, repuestos, detalles_factura, validez):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 7, "ELINPLAST AUTOMATISMOS, C.A.", ln=1, align="R")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "PRESUPUESTO DE SERVICIO TECNICO", ln=1, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Cliente: {datos_orden['empresa_entrega']}", ln=1)
    pdf.cell(0, 6, f"Equipo: {datos_orden['equipo']}", ln=1)
    pdf.ln(5)
    pdf.cell(0, 6, f"Detalles: {detalles_factura}", ln=1)
    pdf.cell(0, 6, f"Total a Facturar: ${mano_obra + repuestos:,.2f}", ln=1)
    
    nombre_archivo = "temp_cotizacion.pdf"
    pdf.output(nombre_archivo)
    with open(nombre_archivo, "rb") as f:
        bytes_pdf = f.read()
    os.remove(nombre_archivo)
    return bytes_pdf

# --- INTERFAZ ---
def main():
    st.set_page_config(page_title="Elinplast - Control", layout="wide")
    crear_db()

    if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

    if not st.session_state['autenticado']:
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
            st.markdown("### Panel Administrativo")
            st.info(f"Usuario: {user}\nRol: {rol.upper()}")
            menu = ["Panel de Control", "Registrar Entrada", "Asignar y Priorizar", "Registrar Salida", "Generar Presupuesto", "Historial Corporativo"] if rol == "super" else ["Panel de Control", "Registrar Salida", "Historial Corporativo"]
            opcion = st.radio("Navegación", menu)
            if st.button("Cerrar Sesión"):
                st.session_state['autenticado'] = False
                st.rerun()

        if opcion == "Panel de Control":
            d = obtener_datos()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Órdenes Totales", len(d))
            c2.metric("Espera Repuestos", len(d[d['estado'] == 'En Espera de Repuestos']))
            c3.metric("Equipos en Taller", len(d[d['fecha_salida'] == '']))
            c4.metric("Entregados", len(d[d['fecha_salida'] != '']))
            
        elif opcion == "Registrar Entrada" and rol == "super":
            with st.form("ent"):
                no = st.text_input("Número de Orden")
                cl = st.text_input("Cliente")
                eq = st.text_input("Equipo")
                pr = st.selectbox("Prioridad", ["🟢 Estándar", "🔴 Emergencia", "🟠 Garantía", "🟡 Solo revisión"])
                st.form_submit_button("Guardar").__setattr__("on_click", lambda: guardar_datos(no, cl, "Admin", eq, "N/A", "N/A", "Recibido", pr))
        
        elif opcion == "Registrar Salida":
            d = obtener_datos()
            id_sel = st.selectbox("Seleccionar Orden", d['id'].tolist())
            te = st.text_input("Técnico", value=user)
            ob = st.text_area("Observaciones")
            if st.button("Guardar Salida"):
                actualizar_salida(id_sel, te, str(datetime.now().date()), ob, "Reparado")
                info = d[d['id'] == id_sel].iloc[0]
                disparar_alerta_api(info['nro_orden'], info['equipo'], te, "Reparado")
                st.success("Notificación enviada.")

        elif opcion == "Historial Corporativo":
            st.dataframe(obtener_datos(), use_container_width=True)

if __name__ == "__main__":
    main()