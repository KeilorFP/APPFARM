import streamlit as st
import folium
import json 
from streamlit_folium import st_folium
from database import get_fincas_full_data, get_estado_lote
from utils import check_login

OWNER = check_login()


st.title("🗺️ Visión Satelital de Lotes")

# 1. Cargar datos completos
lotes_data = get_fincas_full_data(OWNER)

# Filtrar solo los que tienen dibujo (polígono) guardado
lotes_dibujados = [l for l in lotes_data if l[3] is not None]

if not lotes_dibujados:
    st.warning("⚠️ No ha dibujado ningún lote aún.")
    st.info("Vaya a 'Ajustes' > 'Fincas', seleccione un lote y use la herramienta de dibujo (⬠) en el mapa.")
    st.stop()

# --- SELECTOR DE FINCA (AQUÍ ESTÁ LA SOLUCIÓN) ---
col_sel, col_info = st.columns([1, 3])

with col_sel:
    st.markdown("### 🎯 Seleccione Lote")
    # Creamos una lista solo con los nombres
    nombres_lotes = [l[0] for l in lotes_dibujados]
    nombre_seleccionado = st.selectbox("Ver mapa de:", nombres_lotes)

# Buscar los datos del lote seleccionado
lote_actual = next((l for l in lotes_dibujados if l[0] == nombre_seleccionado), None)

if lote_actual:
    nombre = lote_actual[0]
    geojson_str = lote_actual[3]
    
    # Intentamos usar las coordenadas guardadas, si no hay, usamos un default
    lat_center = float(lote_actual[1]) if lote_actual[1] else 9.65
    lon_center = float(lote_actual[2]) if lote_actual[2] else -84.02

    # Obtener estado para el color
    color, estado = get_estado_lote(nombre, OWNER)

    # 2. Configurar Mapa (Centrado en el lote seleccionado)
    m = folium.Map(location=[lat_center, lon_center], zoom_start=17, control_scale=True)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Satélite'
    ).add_to(m)

    # 3. Dibujar SOLO el polígono seleccionado (o resaltarlo)
    try:
        geojson_data = json.loads(geojson_str)
        
        # Estilo del polígono
        def style_function(feature):
            return {
                'fillColor': color,
                'color': 'white',      # Borde blanco para que resalte en el satélite
                'weight': 3,
                'fillOpacity': 0.45,
                'dashArray': '5, 5'    # Borde punteado estilo técnico
            }

        folium.GeoJson(
            geojson_data,
            name=nombre,
            style_function=style_function,
            tooltip=f"<b>{nombre}</b><br>{estado}"
        ).add_to(m)
        
        # Agregamos un marcador en el centro también
        folium.Marker(
            [lat_center, lon_center],
            tooltip=f"{nombre}",
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)

    except Exception as e:
        st.error(f"Error mostrando el mapa: {e}")

    # 4. Mostrar Mapa
    with col_info:
        st_folium(m, width="100%", height=600) # st_folium usa int o string %, no usa el parametro que daba error

    # 5. Leyenda / Info (Corregido el error use_container_width)
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.success("✅ Verde: Recién Abonado")
    c2.error("⚠️ Rojo: Baja Producción")
    c3.info("🔵 Azul: Estado Normal")
