import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

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
    
    # Migraciones seguras para nuevas columnas
    try:
        c.execute("ALTER TABLE ordenes ADD COLUMN tecnico TEXT")
    except sqlite3.OperationalError: pass
    try:
        c.execute("ALTER TABLE ordenes ADD COLUMN fecha_salida TEXT")
    except sqlite3.OperationalError: pass
    try:
        c.execute("ALTER TABLE ordenes ADD COLUMN observaciones TEXT")
    except sqlite3.OperationalError: pass
    try:
        c.execute("ALTER TABLE ordenes ADD COLUMN nro_orden TEXT")
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
    # Forzamos un orden específico de columnas para evitar problemas de visualización
    df = pd.read_sql_query('''
        SELECT id, nro_orden, fecha, empresa_entrega, persona_recibe, equipo, modelo, serial, estado, tecnico, fecha_salida, observaciones 
        FROM ordenes 
        ORDER BY id DESC
    ''', conn)
    conn.close()
    return df

# --- INTERFAZ DE USUARIO (STREAMLIT) ---
def main():
    st.set_page_config(page_title="Elinplast - Control de Órdenes", layout="centered")
    crear_db()

    # --- ESTILOS CSS PERSONALIZADOS ---
    st.markdown("""
        <style>
        .main { background-color: #f8f9fa; }
        h1 { color: #0b2545; text-align: center; font-family: 'Segoe UI', sans-serif; }
        .stButton>button { background-color: #134074; color: white; border-radius: 5px; width: 100%; font-weight: bold; }
        .stButton>button:hover { background-color: #8da9c4; color: #0b2545; }
        </style>
    """, unsafe_allow_html=True)

    # --- ENCABEZADO CON LOGO ---
    archivos_locales = os.listdir(".")
    logo_detectado = None
    for archivo in archivos_locales:
        if archivo.lower().startswith("logo_elinplast"):
            logo_detectado = archivo
            break

    if logo_detectado:
        col_espacio1, col_logo, col_espacio2 = st.columns([1, 2, 1])
        with col_logo:
            st.image(logo_detectado, use_container_width=True)
    else:
        st.title("🏭 ELINPLAST AUTOMATISMOS, C.A.")
    
    st.markdown("<h1>SISTEMA DE GESTIÓN DE SERVICIOS</h1>", unsafe_allow_html=True)
    st.write("---")

    pestaña_registro, pestaña_salida, pestaña_historial = st.tabs(["📝 Registrar Entrada", "📤 Registrar Salida", "📊 Historial Corporativo"])

    # --- PESTAÑA 1: FORMULARIO DE ENTRADA ---
    with pestaña_registro:
        st.subheader("📥 Recolección de Datos de Entrada")
        with st.form("formulario_entrada"):
            
            # Campo principal para el número correlativo de la empresa
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
                st.warning("⚠️ Campos obligatorios faltantes. Asegúrese de rellenar el Número de Orden, Empresa, Receptor, Equipo y Serial.")

    # --- PESTAÑA 2: FORMULARIO DE SALIDA ---
    with pestaña_salida:
        st.subheader("📤 Cierre Técnico y Datos de Salida")
        datos_originales = obtener_datos()
        
        if not datos_originales.empty:
            # Reemplazamos los valores nulos antiguos por un texto amigable para que no falle al mostrar las opciones
            datos_originales['nro_orden'] = datos_originales['nro_orden'].fillna('S/N')
            
            opciones_equipos = [
                f"ID Sistema: {row['id']} | Nro Orden: {row['nro_orden']} - {row['equipo']} (Serial: {row['serial']})" 
                for _, row in datos_originales.iterrows()
            ]
            
            seleccion = st.selectbox("Seleccione la orden que va a egresar / ser entregada:", opciones_equipos)
            id_seleccionado = int(seleccion.split(" | ")[0].replace("ID Sistema: ", ""))
            
            with st.form("formulario_salida"):
                tecnico = st.text_input("¿Quién trabajó / reparó el equipo?", placeholder="Nombre del técnico o ingeniero")
                
                col_fechas = st.columns(2)
                with col_fechas[0]:
                    fecha_salida = st.date_input("Fecha de salida del equipo", datetime.now())
                with col_fechas[1]:
                    nuevo_estado = st.selectbox("Actualizar Estado Final", ["Reparado", "Entregado", "No Reparable"])
                
                observaciones = st.text_area("Observaciones de reparación / Diagnóstico técnico", placeholder="Detalles del trabajo realizado...")
                
                enviar_salida = st.form_submit_button("📤 Registrar Salida y Actualizar Orden")
                
            if enviar_salida:
                if tecnico and observaciones:
                    actualizar_salida(id_seleccionado, tecnico, str(fecha_salida), observaciones, nuevo_estado)
                    st.success("✅ Cierre de orden almacenado correctamente.")
                    st.rerun()
                else:
                    st.warning("⚠️ Por favor, rellene los campos de técnico y observaciones.")
        else:
            st.info("No hay equipos en la base de datos para registrar una salida.")

    # --- PESTAÑA 3: HISTORIAL, BUSCADOR, EXPORTACIÓN Y ELIMINACIÓN ---
    with pestaña_historial:
        st.subheader("📋 Registros Almacenados en la Base de Datos")
        datos = obtener_datos()
        
        if not datos.empty:
            # Mapeo exacto de los nombres visuales de las columnas
            datos.columns = [
                "ID Sistema", "Nro Orden Empresa", "Fecha Entrada", "Empresa Emisora", "Recibido Por", 
                "Equipo Electrónico", "Modelo", "Nro Serial", "Estado Actual",
                "Técnico Asignado", "Fecha Salida", "Observaciones de Reparación"
            ]
            
            busqueda = st.text_input("🔍 Filtro dinámico: Buscar por Nro de Orden, Equipo, Serial o Empresa", "")
            
            if busqueda:
                # Nos aseguramos de rellenar vacíos antes de buscar con str.contains
                datos_busqueda = datos.fillna('')
                datos_filtrados = datos[
                    datos_busqueda["Nro Orden Empresa"].astype(st).str.contains(busqueda, case=False, na=False) |
                    datos_busqueda["Equipo Electrónico"].str.contains(busqueda, case=False, na=False) |
                    datos_busqueda["Nro Serial"].str.contains(busqueda, case=False, na=False) |
                    datos_busqueda["Empresa Emisora"].str.contains(busqueda, case=False, na=False)
                ]
            else:
                datos_filtrados = datos

            st.dataframe(datos_filtrados, use_container_width=True)
            st.write("")
            
            csv_data = datos_filtrados.to_csv(index=False, sep=';').encode('utf-8-sig')
            fecha_reporte = datetime.now().strftime("%Y%m%d")
            
            st.download_button(
                label="📥 Descargar Tabla Actual a Excel (.csv)",
                data=csv_data,
                file_name=f"reporte_elinplast_{fecha_reporte}.csv",
                mime="text/csv"
            )
            
            st.write("---")
            with st.expander("🗑️ Zona de Corrección Administrativa"):
                st.warning("⚠️ Atención: La eliminación de registros es permanente e irreversible.")
                
                datos_filtrados['Nro Orden Empresa'] = datos_filtrados['Nro Orden Empresa'].fillna('S/N')
                opciones_eliminar = [
                    f"ID: {row['ID Sistema']} | Orden: {row['Nro Orden Empresa']} | {row['Equipo Electrónico']} (Serial: {row['Nro Serial']})"
                    for _, row in datos_filtrados.iterrows()
                ]
                
                seleccion_eliminar = st.selectbox("Seleccione el registro exacto que desea remover:", opciones_eliminar)
                
                if seleccion_eliminar:
                    id_a_eliminar = int(seleccion_eliminar.split(" | ")[0].replace("ID: ", ""))
                    confirmar_borrado = st.button("🚨 Eliminar Registro Permanentemente")
                    
                    if confirmar_borrado:
                        eliminar_orden(id_a_eliminar)
                        st.success(f"💥 El registro con ID {id_a_eliminar} ha sido removido con éxito.")
                        st.rerun()
        else:
            st.info("No se han encontrado registros en la base de datos local.")

if __name__ == "__main__":
    main()