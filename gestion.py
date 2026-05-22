import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- CONTROL DE DEFENSA: Importación segura de la librería de PDFs ---
try:
    from fpdf import FPDF
    PDF_DISPONIBLE = True
except ImportError:
    PDF_DISPONIBLE = False

# --- CREDENCIALES DE ACCESO MULTIUSUARIO ---
# Diccionario de usuarios: "Nombre de Usuario": "Contraseña"
USUARIOS_PERMITIDOS = {
    "Taller": "claveTaller1",
    "Proyectos": "claveProyectos2",
    "Administracion": "claveAdmin3"
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
    conn.commit()
    conn.close()

def guardar_datos(nro_orden, empresa, recibe, equipo, modelo, serial, estado):
    conn = sqlite3.connect('gestion_pasantias.db')
    c = conn.cursor()
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO ordenes (fecha, nro_orden, empresa_entrega, persona_recibe, equipo, modelo, serial, estado, tecnico, fecha_salida, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', '', '')
    ''', (fecha_actual, nro_orden, empresa, recibe, equipo, modelo, serial, estado))
    conn.commit()
    conn.close()

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
        SELECT id, nro_orden, fecha, empresa_entrega, persona_recibe, equipo, modelo, serial, estado, tecnico, fecha_salida, observaciones 
        FROM ordenes 
        ORDER BY id DESC
    ''', conn)
    conn.close()
    return df

# --- MOTOR DE GENERACIÓN DE PDF ---
def fabricar_pdf_cotizacion(datos_orden, mano_obra, repuestos, detalles_factura, validez):
    pdf = FPDF()
    pdf.add_page()
    
    archivos_locales = os.listdir(".")
    logo_detectado = None
    for archivo in archivos_locales:
        if archivo.lower().startswith("logo_elinplast"):
            logo_detectado = archivo
            break
    
    if logo_detectado:
        try: pdf.image(logo_detectado, 12, 10, 45)
        except: pass
        
    pdf.set_font("Arial", "B", 14)
    pdf.cell(55) 
    pdf.cell(0, 7, "ELINPLAST AUTOMATISMOS, C.A.", ln=1, align="R")
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 4, "RIF: J-31245678-0", ln=1, align="R")
    pdf.cell(0, 4, "Maracay, Estado Aragua, Venezuela", ln=1, align="R")
    pdf.ln(15)
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "PRESUPUESTO DE SERVICIO TECNICO", ln=1, align="C")
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 5, f"Orden de Referencia: {datos_orden['nro_orden']}", ln=1, align="C")
    pdf.ln(6)
    
    pdf.set_fill_color(230, 235, 245)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, " 1. DATOS DE IDENTIFICACION", border=1, ln=1, fill=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(45, 6, " Empresa Cliente:", border=1)
    pdf.cell(0, 6, f" {datos_orden['empresa_entrega']}", border=1, ln=1)
    pdf.cell(45, 6, " Equipo Evaluado:", border=1)
    pdf.cell(0, 6, f" {datos_orden['equipo']}", border=1, ln=1)
    pdf.cell(45, 6, " Modelo / Nro Serial:", border=1)
    pdf.cell(0, 6, f" {datos_orden['modelo']} / {datos_orden['serial']}", border=1, ln=1)
    pdf.cell(45, 6, " Fecha de Registro:", border=1)
    pdf.cell(0, 6, f" {datos_orden['fecha']}", border=1, ln=1)
    pdf.cell(45, 6, " Estatus en Sistema:", border=1)
    pdf.cell(0, 6, f" {datos_orden['estado']}", border=1, ln=1)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, " 2. DETALLES DEL INFORME TECNICO Y DIAGNOSTICO", border=1, ln=1, fill=True)
    pdf.set_font("Arial", "", 10)
    obs_taller = datos_orden['observaciones'] if datos_orden['observaciones'] else "Equipo en fase de revision."
    texto_informe = f"Descripcion de trabajos / Repuestos requeridos:\n{detalles_factura}\n\nHistorial de observaciones en Taller:\n{obs_taller}"
    pdf.multi_cell(0, 6, texto_informe, border=1)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, " 3. BALANCE ECONOMICO ESTIMADO", border=1, ln=1, fill=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(130, 6, " Concepto / Descripcion del Servicio", border=1, align="C")
    pdf.cell(60, 6, "Monto (USD)", border=1, ln=1, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(130, 6, " Servicio Técnico Especializado e Ingeniería de Laboratorio", border=1)
    pdf.cell(60, 6, f" ${mano_obra:,.2f}", border=1, ln=1, align="R")
    pdf.cell(130, 6, " Materiales, Componentes Electrónicos y Repuestos integrados", border=1)
    pdf.cell(60, 6, f" ${repuestos:,.2f}", border=1, ln=1, align="R")
    total_general = mano_obra + repuestos
    pdf.set_font("Arial", "B", 11)
    pdf.cell(130, 6, " TOTAL NETO A FACTURAR:", border=1)
    pdf.cell(60, 6, f" ${total_general:,.2f}", border=1, ln=1, align="R")
    pdf.ln(6)
    
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 5, f"(*) Validez de la Oferta: {validez}.", ln=1)
    pdf.cell(0, 5, "(*) Precios expresados en divisas extranjeras (USD) de acuerdo a las normativas de intercambio.", ln=1)
    pdf.cell(0, 5, "Documento digitalizado generado por el Sistema Computarizado de Gestion de Elinplast Automatismos.", ln=1)
    
    nombre_archivo = "temp_cotizacion_elinplast.pdf"
    pdf.output(nombre_archivo)
    with open(nombre_archivo, "rb") as f:
        bytes_pdf = f.read()
    os.remove(nombre_archivo)
    return bytes_pdf


# --- MÓDULO 1: PANTALLA DE SEGURIDAD (LOGIN) ---
def mostrar_pantalla_login(logo_detectado):
    st.write("")
    st.write("")
    col_espacio1, col_login, col_espacio2 = st.columns([1, 2, 1])
    
    with col_login:
        if logo_detectado:
            st.image(logo_detectado, use_container_width=True)
            
        st.markdown("<h3 style='text-align: center; color: #0b2545;'>🔒 Control de Acceso Institucional</h3>", unsafe_allow_html=True)
        st.write("---")
        
        with st.form("formulario_login"):
            usuario = st.text_input("👤 Usuario", placeholder="Ingrese su usuario asignado")
            clave = st.text_input("🔑 Contraseña", type="password", placeholder="Ingrese su contraseña")
            st.write("")
            ingresar = st.form_submit_button("Entrar al Sistema ➔")
            
            if ingresar:
                # LÓGICA MULTIUSUARIO: Comprueba si el usuario existe y si la clave es la correcta
                if usuario in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario] == clave:
                    st.session_state['autenticado'] = True
                    st.session_state['usuario_activo'] = usuario # Guardamos quién entró
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos. Acceso denegado.")


# --- MÓDULO 2: APLICACIÓN PRINCIPAL (EL SISTEMA) ---
def mostrar_aplicacion_principal(logo_detectado):
    crear_db()

    # --- BARRA LATERAL (CERRAR SESIÓN) ---
    with st.sidebar:
        if logo_detectado:
            st.image(logo_detectado, use_container_width=True)
        st.markdown("### 🟢 Panel Administrativo")
        
        # Recuperamos el nombre del usuario que inició sesión
        usuario_actual = st.session_state.get('usuario_activo', 'Desconocido')
        st.info(f"Usuario activo: **{usuario_actual}**")
        
        st.write("---")
        if st.button("🚪 Cerrar Sesión Segura"):
            st.session_state['autenticado'] = False
            st.session_state['usuario_activo'] = ""
            st.rerun()

    # --- ENCABEZADO NORMAL ---
    if logo_detectado:
        col_espacio1, col_logo, col_espacio2 = st.columns([1, 2, 1])
        with col_logo:
            st.image(logo_detectado, use_container_width=True)
    else:
        st.title("🏭 ELINPLAST AUTOMATISMOS, C.A.")
    
    st.markdown("<h1>SISTEMA DE GESTIÓN DE SERVICIOS</h1>", unsafe_allow_html=True)
    st.write("---")

    pestaña_registro, pestaña_salida, pestaña_documentos, pestaña_historial = st.tabs([
        "📝 Registrar Entrada", 
        "📤 Registrar Salida", 
        "🧾 Generar Presupuesto", 
        "📊 Historial Corporativo"
    ])

    # --- PESTAÑA 1: FORMULARIO DE ENTRADA ---
    with pestaña_registro:
        st.subheader("📥 Recolección de Datos de Entrada")
        with st.form("formulario_entrada"):
            nro_orden = st.text_input("🔢 Número de Orden Asignado (Interno Elinplast)", placeholder="Ej: OPT-045-2026")
            st.write("---")
            col1, col2 = st.columns(2)
            with col1:
                empresa = st.text_input("Empresa que entrega", placeholder="Ej: Cliente / Proveedor")
                recibe = st.text_input("¿Quién recibe?", placeholder="Nombre del receptor")
            with col2:
                equipo = st.text_input("Equipo", placeholder="Ej: VFD Yaskawa, PLC, Motor")
                modelo = st.text_input("Modelo", placeholder="Código de modelo")
            serial = st.text_input("Número de Serial / Serie")
            estado = st.selectbox("Estado inicial del equipo", ["Recibido (Por evaluar)", "En Revisión", "En Espera de Repuestos"])
            enviar = st.form_submit_button("💾 Guardar y Procesar Entrada")

        if enviar:
            if nro_orden and empresa and recibe and equipo and serial:
                guardar_datos(nro_orden, empresa, recibe, equipo, modelo, serial, estado)
                st.success(f"✅ Entrada registrada bajo la Orden Nro: '{nro_orden}' con éxito.")
                st.rerun()
            else:
                st.warning("⚠️ Campos obligatorios faltantes.")

    # --- PESTAÑA 2: FORMULARIO DE SALIDA ---
    with pestaña_salida:
        st.subheader("📤 Cierre Técnico y Datos de Salida")
        datos_originales = obtener_datos()
        if not datos_originales.empty:
            datos_originales['nro_orden'] = datos_originales['nro_orden'].fillna('S/N')
            opciones_equipos = [
                f"ID Sistema: {row['id']} | Orden: {row['nro_orden']} - {row['equipo']}" 
                for _, row in datos_originales.iterrows()
            ]
            seleccion = st.selectbox("Seleccione la orden que va a egresar / ser entregada:", opciones_equipos)
            id_seleccionado = int(seleccion.split(" | ")[0].replace("ID Sistema: ", ""))
            
            with st.form("formulario_salida"):
                tecnico = st.text_input("¿Quién trabajó / reparó el equipo?", placeholder="Nombre del técnico")
                col_fechas = st.columns(2)
                with col_fechas[0]:
                    fecha_salida = st.date_input("Fecha de salida", datetime.now())
                with col_fechas[1]:
                    nuevo_estado = st.selectbox("Actualizar Estado Final", ["Reparado", "Entregado", "No Reparable"])
                observaciones = st.text_area("Observaciones de reparación / Diagnóstico técnico")
                enviar_salida = st.form_submit_button("📤 Registrar Salida y Actualizar Orden")
                
            if enviar_salida:
                if tecnico and observaciones:
                    actualizar_salida(id_seleccionado, tecnico, str(fecha_salida), observaciones, nuevo_estado)
                    st.success("✅ Cierre de orden almacenado correctamente.")
                    st.rerun()
                else:
                    st.warning("⚠️ Por favor, rellene los campos obligatorios.")
        else:
            st.info("No hay equipos en la base de datos para registrar una salida.")

    # --- PESTAÑA 3: PDF ---
    with pestaña_documentos:
        st.subheader("🧾 Facturación Estructurada y Notas de Presupuesto")
        if not PDF_DISPONIBLE:
            st.error("❌ Módulo Inactivo: La librería 'fpdf2' no está instalada.")
        else:
            datos_db = obtener_datos()
            if not datos_db.empty:
                datos_db['nro_orden'] = datos_db['nro_orden'].fillna('S/N')
                opciones_pdf = [
                    f"{row['id']} | Orden: {row['nro_orden']} - Cliente: {row['empresa_entrega']} ({row['equipo']})"
                    for _, row in datos_db.iterrows()
                ]
                seleccion_pdf = st.selectbox("Seleccione la orden para confeccionar el PDF:", opciones_pdf)
                id_pdf = int(seleccion_pdf.split(" | ")[0])
                fila_seleccionada = datos_db[datos_db['id'] == id_pdf].iloc[0]
                
                st.write("---")
                st.markdown("#### 💰 Configuración Financiera del Presupuesto")
                with st.form("formulario_pdf"):
                    col_costos = st.columns(2)
                    with col_costos[0]:
                        mano_obra = st.number_input("Costo de Mano de Obra (USD)", min_value=0.0, value=50.0, step=5.0)
                    with col_costos[1]:
                        repuestos = st.number_input("Costo de Repuestos (USD)", min_value=0.0, value=0.0, step=5.0)
                    
                    validez = st.text_input("Validez del Presupuesto", value="5 días hábiles a partir de la fecha")
                    detalles_factura = st.text_area("Detalle de Trabajos y Repuestos:")
                    hacer_pdf = st.form_submit_button("⚙️ Procesar y Preparar Documento PDF")
                
                if hacer_pdf:
                    if detalles_factura:
                        pdf_bloque_bytes = fabricar_pdf_cotizacion(fila_seleccionada, mano_obra, repuestos, detalles_factura, validez)
                        st.success("🎉 ¡El documento PDF ha sido estructurado con éxito!")
                        st.download_button(
                            label="📥 Descargar Documento Oficial en PDF",
                            data=pdf_bloque_bytes,
                            file_name=f"Presupuesto_Elinplast_Orden_{fila_seleccionada['nro_orden']}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.warning("⚠️ Describa los trabajos o repuestos para armar el presupuesto.")
            else:
                st.info("No hay registros disponibles para facturar.")

    # --- PESTAÑA 4: HISTORIAL ---
    with pestaña_historial:
        st.subheader("📋 Registros Almacenados en la Base de Datos")
        datos = obtener_datos()
        if not datos.empty:
            datos.columns = [
                "ID Sistema", "Nro Orden Empresa", "Fecha Entrada", "Empresa Emisora", "Recibido Por", 
                "Equipo Electrónico", "Modelo", "Nro Serial", "Estado Actual",
                "Técnico Asignado", "Fecha Salida", "Observaciones de Reparación"
            ]
            busqueda = st.text_input("🔍 Filtro dinámico: Buscar por Nro de Orden, Equipo, Serial o Empresa", "")
            if busqueda:
                datos_busqueda = datos.fillna('')
                datos_filtrados = datos[
                    datos_busqueda["Nro Orden Empresa"].astype(str).str.contains(busqueda, case=False, na=False) |
                    datos_busqueda["Equipo Electrónico"].str.contains(busqueda, case=False, na=False) |
                    datos_busqueda["Nro Serial"].str.contains(busqueda, case=False, na=False) |
                    datos_busqueda["Empresa Emisora"].str.contains(busqueda, case=False, na=False)
                ]
            else:
                datos_filtrados = datos

            st.dataframe(datos_filtrados, use_container_width=True)
            st.write("")
            
            csv_data = datos_filtrados.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(
                label="📥 Descargar Tabla Actual a Excel (.csv)",
                data=csv_data,
                file_name=f"reporte_elinplast_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            st.write("---")
            with st.expander("🗑️ Zona de Corrección Administrativa"):
                st.warning("⚠️ Atención: La eliminación de registros es permanente e irreversible.")
                datos_filtrados['Nro Orden Empresa'] = datos_filtrados['Nro Orden Empresa'].fillna('S/N')
                opciones_eliminar = [
                    f"ID: {row['ID Sistema']} | Orden: {row['Nro Orden Empresa']} | {row['Equipo Electrónico']}"
                    for _, row in datos_filtrados.iterrows()
                ]
                seleccion_eliminar = st.selectbox("Seleccione el registro exacto que desea remover:", opciones_eliminar)
                if seleccion_eliminar:
                    id_a_eliminar = int(seleccion_eliminar.split(" | ")[0].replace("ID: ", ""))
                    confirmar_borrado = st.button("🚨 Eliminar Registro Permanentemente")
                    if confirmar_borrado:
                        eliminar_orden(id_a_eliminar)
                        st.success(f"💥 El registro con ID {id_a_eliminar} ha sido removido.")
                        st.rerun()
        else:
            st.info("No se han encontrado registros en la base de datos local.")

# --- NÚCLEO DEL PROGRAMA ---
def main():
    st.set_page_config(page_title="Elinplast - Control de Órdenes", layout="centered")

    st.markdown("""
        <style>
        .main { background-color: #f8f9fa; }
        h1 { color: #0b2545; text-align: center; font-family: 'Segoe UI', sans-serif; }
        .stButton>button { background-color: #134074; color: white; border-radius: 5px; width: 100%; font-weight: bold; }
        .stButton>button:hover { background-color: #8da9c4; color: #0b2545; }
        </style>
    """, unsafe_allow_html=True)

    archivos_locales = os.listdir(".")
    logo_detectado = None
    for archivo in archivos_locales:
        if archivo.lower().startswith("logo_elinplast"):
            logo_detectado = archivo
            break

    if 'autenticado' not in st.session_state:
        st.session_state['autenticado'] = False
        st.session_state['usuario_activo'] = "" # Inicializamos la memoria del usuario

    if not st.session_state['autenticado']:
        mostrar_pantalla_login(logo_detectado)
    else:
        mostrar_aplicacion_principal(logo_detectado)

if __name__ == "__main__":
    main()