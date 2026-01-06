import streamlit as st
import datetime
import requests
from utils import aplicar_estilos_css
from database import verify_user

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Finca App ERP", page_icon="🚜", layout="wide")

# 2. APLICAR ESTILOS GLOBALES (Base)
aplicar_estilos_css()

# 3. CSS "AGRI-TECH FUTURISTA" (NUEVO FONDO DIGITAL)
st.markdown("""
    <style>
        /* A. ELIMINAR BARRA LATERAL */
        [data-testid="stSidebar"] { display: none !important; }
        
        /* B. BOTONES ESTILO "PANEL DIGITAL AGRITECH" */
        div.stButton > button {
            /* 1. FONDO TECNOLÓGICO DE CUADRÍCULA (GRID) */
            /* Fondo base oscuro verdoso */
            background-color: rgba(10, 30, 15, 0.85) !important;
            /* Dibujamos lineas horizontales y verticales con gradientes */
            background-image: 
                linear-gradient(rgba(76, 175, 80, 0.3) 1px, transparent 1px),
                linear-gradient(90deg, rgba(76, 175, 80, 0.3) 1px, transparent 1px) !important;
            /* Tamaño de los cuadros de la rejilla */
            background-size: 20px 20px !important;
            
            /* 2. BORDE NEÓN */
            border: 2px solid #00E676 !important; /* Verde eléctrico */
            border-radius: 16px !important;
            
            /* 3. RESPLANDOR INTERNO Y EXTERNO (GLOW) */
            /* Sombra externa + Sombra interna para efecto de pantalla encendida */
            box-shadow: 0 0 15px rgba(0, 230, 118, 0.2), inset 0 0 25px rgba(0, 230, 118, 0.1) !important;
            backdrop-filter: blur(5px);
            
            /* 4. FORMA Y TAMAÑO (Igual que antes) */
            aspect-ratio: 1 / 1 !important; 
            height: auto !important; 
            width: 100% !important;
            max-width: 200px !important; 
            margin: 0 auto !important;
            
            /* 5. TIPOGRAFÍA DIGITAL */
            color: #ffffff !important; /* Texto blanco siempre */
            text-shadow: 0 1px 4px rgba(0,0,0,0.8); /* Sombra para leer mejor */
            font-size: 20px !important;
            font-weight: 700 !important;
            white-space: pre-wrap !important;
            
            /* Alineación y Transición */
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        }
        
        /* C. EFECTO HOVER (MÁS BRILLO) */
        div.stButton > button:hover {
            transform: translateY(-5px) scale(1.03);
            background-color: rgba(20, 50, 25, 0.95) !important;
            /* El borde y el brillo se intensifican al pasar el mouse */
            border-color: #69F0AE !important; 
            box-shadow: 0 0 25px rgba(105, 240, 174, 0.5), inset 0 0 35px rgba(105, 240, 174, 0.3) !important;
        }
        
        div.stButton > button:active {
            transform: scale(0.98);
            box-shadow: 0 0 10px rgba(0, 230, 118, 0.8) !important;
        }

        /* D. ICONOS GRANDES Y BRILLANTES */
        div.stButton > button p {
            font-size: 3rem !important; 
            margin-bottom: 10px !important;
            /* Un brillo extra al emoji */
            filter: drop-shadow(0 0 5px rgba(0, 230, 118, 0.5));
        }
        
        /* E. LIMPIEZA INTERFAZ */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
    </style>
""", unsafe_allow_html=True)

# 4. LÓGICA DE LOGIN
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_log1, col_log2, col_log3 = st.columns([1, 8, 1])
    with col_log2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🚜 Acceso Finca</h2>", unsafe_allow_html=True)
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("INGRESAR 🔐", type="primary", use_container_width=True):
                if verify_user(u, p):
                    st.session_state.logged_in = True
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("⚠️ Credenciales incorrectas")
    st.stop()

# 5. HEADER (DATOS DE USUARIO Y CLIMA)
OWNER = st.session_state.user
hoy = datetime.date.today()

@st.cache_data(ttl=3600)
def obtener_clima_cached():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=9.66&longitude=-84.02&current=temperature_2m,precipitation&daily=precipitation_probability_max&timezone=auto"
        r = requests.get(url, timeout=2)
        data = r.json()
        return data["current"]["temperature_2m"], data["daily"]["precipitation_probability_max"][0]
    except:
        return None, None

c_head1, c_head2 = st.columns([2, 1])
with c_head1:
    st.markdown(f"### 👋 Hola, {OWNER}")
    st.caption(f"📅 {hoy.strftime('%d de %B, %Y')}")

with c_head2:
    temp, prob = obtener_clima_cached()
    if temp:
        st.metric("Clima", f"{temp}°C", f"{prob}% Lluvia")

st.divider()

# 6. MENÚ GRID (7 BOTONES)
c_pad_izq, c_grid, c_pad_der = st.columns([1, 6, 1]) 

with c_grid:
    # --- FILA 1: OPERACIÓN DIARIA ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if st.button("📅\n\nPlanificar", use_container_width=True):
            st.switch_page("pages/Planificador.py")

    with c2:
        if st.button("🧑‍🌾\n\nJornadas", use_container_width=True):
            st.switch_page("pages/Jornadas.py")

    with c3:
        if st.button("☕\n\nCosecha", use_container_width=True):
            st.switch_page("pages/Cosecha.py")

    st.write("") # Separador vertical

    # --- FILA 2: CONTROL TÉCNICO ---
    c4, c5, c6 = st.columns(3)

    with c4:
        if st.button("📦\n\nInsumos", use_container_width=True):
            st.switch_page("pages/Insumos.py")
            
    with c5:
        if st.button("🗺️\n\nMapa", use_container_width=True):
            st.switch_page("pages/Mapa_Finca.py")

    with c6:
        if st.button("📊\n\nReportes", use_container_width=True):
            st.switch_page("pages/Reportes.py")

    st.write("") # Separador vertical

    # --- FILA 3: AJUSTES (CENTRADO) ---
    c7, c8, c9 = st.columns(3)
    
    with c8:
        if st.button("⚙️\n\nAjustes", use_container_width=True):
            st.switch_page("pages/Ajustes.py")

# 7. FOOTER
st.markdown("<br><br>", unsafe_allow_html=True)
if st.button("Cerrar Sesión 🔒", type="secondary"):
    st.session_state.logged_in = False
    st.rerun()