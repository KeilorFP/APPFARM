import streamlit as st
import folium
import json 
from streamlit_folium import st_folium
from database import get_fincas_full_data, get_estado_lote
# Importamos mostrar_encabezado para la navegación
from utils import check_login, mostrar_encabezado

# 1. VERIFICACIÓN Y ENCABEZADO
OWNER = check_login()
mostrar_encabezado("🗺️ Visión Satelital")

# 2. CARGAR DATOS
lotes_data = get_fincas_full_data(OWNER)

# Filtrar solo los que tienen dibujo (polígono) guardado
lotes_dibujados = [l for l in lotes_data if l[3] is not None]

if not lotes_dibujados:
    st.warning("⚠️ No ha dibujado ningún lote aún.")
    with st.container(border=True):
        st.info("Para ver el mapa aquí:")
        st.markdown("1. Vaya a **⚙️ Ajustes**")
        st.markdown("2. Entre a la pestaña **Fincas**")
        st.markdown("3. Seleccione un lote y **dibújelo** en el mapa.")
    st.stop()

# 3. SELECTOR DE LOTE
# En móvil ponemos el selector arriba del todo
nombres_lotes = [l[0] for l in lotes_dibujados]
nombre_seleccionado = st.selectbox("📍 Seleccione Lote a Visualizar:", nombres_lotes)

# Buscar los datos del lote seleccionado
lote_actual = next((l for l in lotes_dibujados if l[0] == nombre_seleccionado), None)

if lote_actual:
    nombre = lote_actual[0]
    geojson_str = lote_actual[3]
    
    # Coordenadas: Si son 0.0 (default), usamos una coordenada central de Costa Rica aprox
    lat_center = float(lote_actual[1]) if float(lote_actual[1]) != 0.0 else 9.65
    lon_center = float(lote_actual[2]) if float(lote_actual[2]) != 0.0 else -84.02

    # Obtener estado (Color Inteligente)
    color, estado = get_estado_lote(nombre, OWNER)

    # 4. CONFIGURAR MAPA
    # zoom_start=17 es muy cerca, ideal para ver matas de café
    m = folium.Map(location=[lat_center, lon_center], zoom_start=17, control_scale=True)

    # Capa Satelital (Esri World Imagery)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Satélite'
    ).add_to(m)

    # 5. DIBUJAR POLÍGONO
    try:
        geojson_data = json.loads(geojson_str)
        
        # Estilo del polígono según estado (Verde/Rojo/Azul)
        def style_function(feature):
            return {
                'fillColor': color,
                'color': 'white',      # Borde blanco para contraste
                'weight': 2,
                'fillOpacity': 0.4,    # Transparencia para ver el cultivo debajo
                'dashArray': '5, 5'    # Borde punteado
            }

        folium.GeoJson(
            geojson_data,
            name=nombre,
            style_function=style_function,
            tooltip=f"<b>{nombre}</b><br>{estado}"
        ).add_to(m)
        
        # Marcador con información
        folium.Marker(
            [lat_center, lon_center],
            tooltip=f"{nombre}",
            icon=folium.Icon(color=color, icon="info-sign"),
            popup=folium.Popup(f"<b>{nombre}</b><br>Estado: {estado}", max_width=200)
        ).add_to(m)

        # Centrar mapa en el polígono automáticamente
        # (Truco para que no tengas que adivinar coordenadas)
        folium.FitBounds(m.get_bounds(), padding=(30, 30)).add_to(m)

    except Exception as e:
        st.error(f"Error mostrando el mapa: {e}")

    # 6. RENDERIZAR MAPA
    st_folium(m, width="100%", height=500) 

    # 7. LEYENDA
    st.caption("Estado del Lote:")
    c1, c2, c3 = st.columns(3)
    c1.success("✅ Recién Abonado")
    c2.error("⚠️ Baja Producción")
    c3.info("🔵 Estable")