import streamlit as st
import plotly.express as px
import pandas as pd
import datetime
import requests
from database import verify_user, add_user, get_gastos_por_lote, get_produccion_total_lote, calcular_resumen_periodo, create_all_tables
from utils import cargar_fincas, aplicar_estilos_css

# 1. Configuración
st.set_page_config(page_title="Finca App ERP", page_icon="🚜", layout="wide")
aplicar_estilos_css() # <--- AQUI EL ESTILO NUEVO
# Inicialización de tablas (segura)
try:
    create_all_tables()
except Exception as e:
    st.error("Error inicializando la base de datos. Revise configuración de conexión.")

# 2. Login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>🚜 Acceso Seguro</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Ingresar", type="primary"):
                if verify_user(u, p):
                    st.session_state.logged_in = True
                    st.session_state.user = u
                    st.rerun()
                else: st.error("Acceso Denegado")
    st.stop()

# 3. DASHBOARD PRINCIPAL
OWNER = st.session_state.user
hoy = datetime.date.today()
inicio_mes = hoy.replace(day=1)

# --- HEADER ---
c_head_1, c_head_2 = st.columns([3, 1])
c_head_1.title(f"Bienvenido, {OWNER}")
c_head_1.caption(f"Resumen de operaciones al {hoy.strftime('%d/%m/%Y')}")

# --- WIDGET CLIMA (Pequeño y funcional) ---
def obtener_clima():
    import logging
    logger = logging.getLogger(__name__)
    try:
        # Los Santos (Aprox)
        url = "https://api.open-meteo.com/v1/forecast?latitude=9.66&longitude=-84.02&current=temperature_2m,precipitation&daily=precipitation_probability_max&timezone=auto"
        r = requests.get(url, timeout=2)
        r.raise_for_status()
        data = r.json()
        temp = data["current"]["temperature_2m"]
        prob = data["daily"]["precipitation_probability_max"][0]
        return temp, prob
    except (requests.RequestException, ValueError, KeyError) as e:
        logger.warning("Fallo obteniendo clima: %s", e)
        return None, None

temp, prob_lluvia = obtener_clima()
if temp:
    color_clima = "red" if prob_lluvia > 60 else "green"
    c_head_2.markdown(f"""
    <div style="text-align: right; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 10px; border-left: 5px solid {color_clima}">
        <b>🌡️ {temp}°C</b> <br>
        ☔ Prob. Lluvia: {prob_lluvia}%
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- KPIs FINANCIEROS (CALCULADOS EN VIVO) ---
# Calculamos gastos e ingresos desde el dia 1 del mes hasta hoy
datos_mes = calcular_resumen_periodo(inicio_mes, hoy, OWNER)
gasto_total = datos_mes['TotalGeneral']
ingreso_bruto = datos_mes['Cosecha'] * 1.5 # Estimado: Asumimos que la cosecha vale un 50% más de lo que pagamos al recolector (Margen)

# Definimos métricas
col1, col2, col3, col4 = st.columns(4)
col1.metric("Gasto Mano de Obra", f"₡{datos_mes['ManoObra']:,.0f}", delta="Mes Actual")
col2.metric("Gasto Insumos", f"₡{datos_mes['Insumos']:,.0f}", delta="Mes Actual")
col3.metric("Pago Recolectores", f"₡{datos_mes['Cosecha']:,.0f}", delta="Mes Actual")

# El balance es critico
balance = ingreso_bruto - gasto_total # Esto es muy simplificado, solo para el ejemplo
col4.metric("Salida Total Caja", f"₡{gasto_total:,.0f}", delta_color="inverse", help="Dinero total que ha salido este mes")

# --- GRÁFICOS Y MAPAS ---
st.subheader("📍 Situación de Lotes")
c_graf, c_accesos = st.columns([2, 1])

with c_graf:
    # Gráfico de gastos por lote
    gastos = get_gastos_por_lote(OWNER)
    if gastos:
        df_g = pd.DataFrame(gastos)
        # Usamos un gráfico de barras horizontal que es más fácil de leer
        fig = px.bar(df_g, x="TotalGasto", y="Lote", orientation='h', 
                     title="Lotes más costosos (Acumulado)",
                     color="TotalGasto", color_continuous_scale="Reds")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig, use_container_width=True) # <-- use_container_width está bien aquí si no da warning
    else:
        st.info("No hay datos de gastos aún.")

with c_accesos:
    st.markdown("#### ⚡ Acciones Rápidas")
    with st.container(border=True):
        st.write("¿Qué desea hacer?")
        if st.button("📅 Planificar Semana"): st.switch_page("pages/1_📅_Planificador.py")
        if st.button("☕ Registrar Cosecha"): st.switch_page("pages/2_☕_Cosecha.py")
        if st.button("🗺️ Ver Mapa Satelital"): st.switch_page("pages/8_🗺️_Mapa_Finca.py")

# Botón salir en sidebar
with st.sidebar:
    st.write("---")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()