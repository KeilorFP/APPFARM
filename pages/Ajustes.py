import streamlit as st
import pandas as pd
import json 
import time  # <--- ESTO FALTABA
from io import BytesIO
import folium
from folium.plugins import Draw 
from streamlit_folium import st_folium 

from database import (
    add_finca, delete_finca, add_trabajador, 
    add_catalogo_producto, delete_catalogo_producto,
    add_catalogo_labor, delete_catalogo_labor, set_tarifas, get_tarifas,
    get_export_jornadas, get_export_recolecciones, get_export_insumos,
    update_finca_coords, update_finca_polygon
)
from utils import check_login, cargar_fincas, cargar_personal, cargar_productos, cargar_labores, limpiar_cache

OWNER = check_login()
st.title("⚙️ Ajustes & Configuración")

tab = st.segmented_control("Sección", ["Fincas", "Personal", "Listas", "Tarifas", "Respaldo"])

if tab == "Fincas":
    st.markdown("### 🚜 Gestión de Lotes y Mapas")
    
    col_gestion, col_mapa = st.columns([1, 2])
    
    # --- COLUMNA IZQUIERDA: GESTIÓN BÁSICA ---
    with col_gestion:
        with st.container(border=True):
            st.caption("Crear / Borrar Lotes")
            nf = st.text_input("Nuevo Nombre de Lote")
            if st.button("➕ Crear"): add_finca(nf, OWNER); limpiar_cache(); st.rerun()
            
            fincas_disp = cargar_fincas(OWNER)
            df = st.selectbox("Eliminar", ["..."] + fincas_disp)
            if df != "..." and st.button("🗑️ Borrar"): delete_finca(df, OWNER); limpiar_cache(); st.rerun()

    # --- COLUMNA DERECHA: EDITOR DE MAPAS ---
    with col_mapa:
        st.info("🗺️ Dibujar Finca en el Mapa")
        if fincas_disp:
            lote_target = st.selectbox("Seleccionar Lote para Dibujar:", fincas_disp)
            
            st.caption("Instrucciones: Use las herramientas del mapa para dibujar el contorno exacto de su finca.")
            
            # 1. Crear Mapa Satelital Base
            m_draw = folium.Map(location=[9.65, -84.02], zoom_start=14)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri World Imagery', name='Satélite'
            ).add_to(m_draw)

            # 2. Agregar Herramientas de Dibujo
            draw = Draw(
                export=False,
                position='topleft',
                draw_options={'polyline': False, 'rectangle': False, 'circle': False, 'marker': False, 'circlemarker': False},
                edit_options={'edit': True, 'remove': True}
            )
            draw.add_to(m_draw)

            # 3. Mostrar Mapa
            output = st_folium(m_draw, width="100%", height=500, key="draw_map")

            # 4. Lógica de Guardado
            poly_data = None
            if output and output.get('all_drawings'):
                last_drawing = output['all_drawings'][-1]
                poly_data = last_drawing.get('geometry')
            
            if poly_data:
                st.success("✅ ¡Forma detectada!")
                if st.button(f"💾 GUARDAR DIBUJO PARA: {lote_target.upper()}", type="primary", width="stretch"): # width='stretch' corrige la advertencia amarilla
                    geojson_string = json.dumps(poly_data)
                    update_finca_polygon(lote_target, geojson_string, OWNER)
                    
                    st.toast("¡Polígono guardado exitosamente!")
                    time.sleep(1) # Ahora sí funcionará
                    st.rerun()
        else:
            st.warning("Cree un lote primero.")

elif tab == "Personal":
    n = st.text_input("Nombre"); a = st.text_input("Apellido"); t = st.radio("Rol", ["Jornalero", "Recolector"])
    if st.button("➕ Crear Trabajador"): add_trabajador(n, a, t, OWNER); limpiar_cache(); st.success("Listo")

elif tab == "Listas":
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Productos**")
        np = st.text_input("Nuevo Prod.")
        if st.button("Guardar Prod"): add_catalogo_producto(np, OWNER); limpiar_cache(); st.rerun()
        dp = st.selectbox("Borrar Prod", ["..."]+cargar_productos(OWNER))
        if dp != "..." and st.button("Borrar P"): delete_catalogo_producto(dp, OWNER); limpiar_cache(); st.rerun()
    with c2:
        st.markdown("**Labores**")
        nl = st.text_input("Nueva Labor")
        if st.button("Guardar Lab"): add_catalogo_labor(nl, OWNER); limpiar_cache(); st.rerun()
        dl = st.selectbox("Borrar Lab", ["..."]+cargar_labores(OWNER))
        if dl != "..." and st.button("Borrar L"): delete_catalogo_labor(dl, OWNER); limpiar_cache(); st.rerun()

elif tab == "Tarifas":
    td, th = get_tarifas(OWNER)
    d = st.number_input("Día ₡", value=td)
    h = st.number_input("Extra ₡", value=th)
    if st.button("Actualizar Tarifas"): set_tarifas(OWNER, d, h); st.success("Actualizado")

elif tab == "Respaldo":
    st.info("Descarga tus datos a Excel")
    c1, c2, c3 = st.columns(3)
    
    # Jornadas
    jor = get_export_jornadas(OWNER)
    if jor:
        df = pd.DataFrame(jor, columns=["ID","Fecha","Trab","Lote","Act","Días","Ext"])
        b = BytesIO()
        with pd.ExcelWriter(b, engine="xlsxwriter") as w: df.to_excel(w, index=False)
        c1.download_button("📥 Jornadas", b.getvalue(), "jornadas.xlsx")
        
    # Cosecha
    cos = get_export_recolecciones(OWNER)
    if cos:
        df = pd.DataFrame(cos, columns=["ID","Fecha","Trab","Lote","Caj","$$","Total"])
        b = BytesIO()
        with pd.ExcelWriter(b, engine="xlsxwriter") as w: df.to_excel(w, index=False)
        c2.download_button("📥 Cosecha", b.getvalue(), "cosecha.xlsx")
        
    # Insumos
    ins = get_export_insumos(OWNER)
    if ins:
        df = pd.DataFrame(ins, columns=["ID","Fecha","Lote","Tipo","Prod","Dosis","Cant","$$","Total"])
        b = BytesIO()
        with pd.ExcelWriter(b, engine="xlsxwriter") as w: df.to_excel(w, index=False)
        c3.download_button("📥 Insumos", b.getvalue(), "insumos.xlsx")