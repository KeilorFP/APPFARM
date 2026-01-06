import streamlit as st
import pandas as pd
import json 
import time 
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
# IMPORTANTE: Agregamos mostrar_encabezado para el botón de volver
from utils import (
    check_login, cargar_fincas, cargar_personal, 
    cargar_productos, cargar_labores, limpiar_cache, mostrar_encabezado
)

# 1. VERIFICACIÓN DE SESIÓN
OWNER = check_login()

# 2. ENCABEZADO CON BOTÓN DE RETROCESO
mostrar_encabezado("⚙️ Configuración")

# 3. NAVEGACIÓN INTERNA (Tabs)
# Usamos st.pills o st.radio horizontal que son muy cómodos en móvil
# (Si tu Streamlit es antiguo y falla 'pills', cámbialo por st.radio(..., horizontal=True))
opciones = ["Fincas", "Personal", "Listas", "Tarifas", "Respaldo"]
tab = st.pills("Seleccione una opción:", opciones, default="Fincas")

st.divider()

# --- SECCIÓN 1: FINCAS Y MAPAS ---
if tab == "Fincas":
    st.markdown("#### 🚜 Gestión de Lotes")
    
    # En móvil, mejor apilar que usar columnas estrechas. 
    # Usamos un expander para la gestión básica para ahorrar espacio.
    with st.expander("➕ Crear o Borrar Lotes", expanded=False):
        c1, c2 = st.columns(2)
        nf = c1.text_input("Nuevo Nombre de Lote")
        if c1.button("Crear Lote"): 
            add_finca(nf, OWNER); limpiar_cache(); st.rerun()
            
        fincas_disp = cargar_fincas(OWNER)
        df = c2.selectbox("Eliminar Lote", ["..."] + fincas_disp)
        if df != "..." and c2.button("Borrar Lote"): 
            delete_finca(df, OWNER); limpiar_cache(); st.rerun()

    st.markdown("#### 🗺️ Dibujar Mapa Satelital")
    if fincas_disp:
        lote_target = st.selectbox("📍 ¿Qué lote vamos a dibujar?", fincas_disp)
        st.caption("Use el pentágono ⬠ en el mapa para dibujar los límites.")
        
        # 1. Crear Mapa
        m_draw = folium.Map(location=[9.65, -84.02], zoom_start=15)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Satélite'
        ).add_to(m_draw)

        # 2. Herramientas de Dibujo
        draw = Draw(
            export=False,
            position='topleft',
            draw_options={'polyline': False, 'rectangle': False, 'circle': False, 'marker': False, 'circlemarker': False, 'polygon': True},
            edit_options={'edit': True, 'remove': True}
        )
        draw.add_to(m_draw)

        # 3. Renderizar
        output = st_folium(m_draw, width="100%", height=450, key="draw_map")

        # 4. Guardar
        if output and output.get('all_drawings'):
            last_drawing = output['all_drawings'][-1]
            poly_data = last_drawing.get('geometry')
            
            if poly_data:
                st.success("✅ Polígono detectado")
                if st.button(f"💾 Guardar Mapa de: {lote_target}", type="primary", use_container_width=True):
                    geojson_string = json.dumps(poly_data)
                    update_finca_polygon(lote_target, geojson_string, OWNER)
                    st.toast("¡Mapa guardado exitosamente!", icon="🗺️")
                    time.sleep(1)
                    st.rerun()
    else:
        st.warning("Primero cree un lote en la sección de arriba.")

# --- SECCIÓN 2: PERSONAL ---
elif tab == "Personal":
    st.markdown("#### 👥 Equipo de Trabajo")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombre")
        a = c2.text_input("Apellido")
        t = st.radio("Rol", ["Jornalero", "Recolector"], horizontal=True)
        
        if st.button("➕ Agregar Trabajador", type="primary", use_container_width=True):
            if n and a:
                add_trabajador(n, a, t, OWNER)
                limpiar_cache()
                st.success(f"Agregado: {n} {a}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Faltan datos")
    
    st.markdown("##### Lista Actual")
    st.dataframe(cargar_personal(OWNER), use_container_width=True, hide_index=True)

# --- SECCIÓN 3: LISTAS (CATÁLOGOS) ---
elif tab == "Listas":
    c1, c2 = st.columns(2)
    with c1:
        st.info("📦 Productos")
        np = st.text_input("Nuevo Insumo/Producto")
        if st.button("Guardar Prod"): add_catalogo_producto(np, OWNER); limpiar_cache(); st.rerun()
        
        dp = st.selectbox("Borrar", ["..."]+cargar_productos(OWNER), key="del_prod")
        if dp != "..." and st.button("🗑️ Eliminar Prod"): delete_catalogo_producto(dp, OWNER); limpiar_cache(); st.rerun()
        
    with c2:
        st.info("🛠️ Labores")
        nl = st.text_input("Nueva Labor")
        if st.button("Guardar Labor"): add_catalogo_labor(nl, OWNER); limpiar_cache(); st.rerun()
        
        dl = st.selectbox("Borrar", ["..."]+cargar_labores(OWNER), key="del_lab")
        if dl != "..." and st.button("🗑️ Eliminar Lab"): delete_catalogo_labor(dl, OWNER); limpiar_cache(); st.rerun()

# --- SECCIÓN 4: TARIFAS ---
elif tab == "Tarifas":
    st.markdown("#### 💰 Configuración de Pagos")
    td, th = get_tarifas(OWNER)
    
    with st.container(border=True):
        st.caption("Estos valores se usarán por defecto en los jornales.")
        d = st.number_input("Pago por Día (Jornal) ₡", value=td, step=500.0)
        h = st.number_input("Pago por Hora Extra ₡", value=th, step=100.0)
        
        if st.button("💾 Actualizar Tarifas Globales", type="primary", use_container_width=True):
            set_tarifas(OWNER, d, h)
            st.toast("Tarifas actualizadas")

# --- SECCIÓN 5: RESPALDO ---
elif tab == "Respaldo":
    st.markdown("#### 📥 Descargar Datos")
    st.caption("Descarga toda tu información a Excel para tener copias de seguridad.")
    
    # Generamos los archivos
    jor = get_export_jornadas(OWNER)
    cos = get_export_recolecciones(OWNER)
    ins = get_export_insumos(OWNER)

    c1, c2, c3 = st.columns(3)
    
    if jor:
        df_j = pd.DataFrame(jor, columns=["ID","Fecha","Trabajador","Lote","Actividad","Días","Extras"])
        b_j = BytesIO()
        with pd.ExcelWriter(b_j, engine="xlsxwriter") as w: df_j.to_excel(w, index=False)
        c1.download_button("📥 Jornadas", b_j.getvalue(), "jornadas.xlsx", use_container_width=True)
    
    if cos:
        df_c = pd.DataFrame(cos, columns=["ID","Fecha","Recolector","Lote","Cajuelas","Precio","Total"])
        b_c = BytesIO()
        with pd.ExcelWriter(b_c, engine="xlsxwriter") as w: df_c.to_excel(w, index=False)
        c2.download_button("📥 Cosecha", b_c.getvalue(), "cosecha.xlsx", use_container_width=True)
        
    if ins:
        df_i = pd.DataFrame(ins, columns=["ID","Fecha","Lote","Tipo","Prod","Dosis","Cant","Precio","Total"])
        b_i = BytesIO()
        with pd.ExcelWriter(b_i, engine="xlsxwriter") as w: df_i.to_excel(w, index=False)
        c3.download_button("📥 Insumos", b_i.getvalue(), "insumos.xlsx", use_container_width=True)