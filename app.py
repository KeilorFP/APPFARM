import streamlit as st
import datetime
import requests
from database import verify_user, create_user

# 1. CONFIGURACIÓN DE PÁGINA (WIDE + COLLAPSED)
st.set_page_config(
    page_title="Finca App", 
    page_icon="🚜", 
    layout="wide",  # Ocupar todo el ancho disponible
    initial_sidebar_state="collapsed"
)

# 2. CSS AGRESIVO (PANTALLA COMPLETA + SIN BORDES)
st.markdown("""
    <style>
        /* A. FONDO OSCURO */
        .stApp {
            background: linear-gradient(180deg, #050a06 0%, #102015 100%);
            color: white;
        }

        /* B. ELIMINAR MÁRGENES (FULL WIDTH) */
        /* Esto es lo que hará que los botones ocupen todo el ancho del celular */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0.5rem !important; /* Margen mínimo */
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }

        /* C. OCULTAR MENÚ "ADMINISTRAR APP" Y BARRA SUPERIOR */
        [data-testid="stToolbar"] { display: none !important; } 
        [data-testid="stDecoration"] { display: none !important; } 
        [data-testid="stHeader"] { display: none !important; } 
        header { display: none !important; } 
        #MainMenu { display: none !important; }
        footer { display: none !important; }
        
        /* Ocultar botón "Manage app" flotante inferior si aparece */
        .stDeployButton { display: none !important; }

        /* D. BOTONES GIGANTES (ESTILO PANEL) */
        div.stButton > button {
            width: 100% !important;
            height: 160px !important; /* Altura forzada */
            
            /* Alineación del contenido */
            display: flex !important;
            flex-direction: column !important; 
            align-items: center !important;
            justify-content: center !important;
            gap: 10px !important;

            /* Diseño Visual */
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 230, 118, 0.4) !important; /* Borde verde más visible */
            border-radius: 20px !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
            margin: 0px !important;
        }
        
        /* Efecto al tocar */
        div.stButton > button:active {
            background-color: rgba(0, 230, 118, 0.2) !important;
            transform: scale(0.98);
        }

        /* E. TEXTOS GIGANTES */
        /* Emoji */
        div.stButton > button p:first-child {
             font-size: 45px !important; 
             line-height: 1 !important;
             margin: 0 !important;
             filter: drop-shadow(0 0 5px rgba(0, 230, 118, 0.5));
        }
        /* Texto */
        div.stButton > button p:last-child {
             font-size: 18px !important;
             font-weight: 800 !important;
             text-transform: uppercase;
             color: white !important;
             letter-spacing: 1px;
        }

        /* F. HEADER PERSONALIZADO (Pequeño para dar espacio a botones) */
        h3 { margin: 0 !important; font-size: 1.4rem !important; color: #00E676 !important;}
        p { margin: 0 !important; }

    </style>
""", unsafe_allow_html=True)

# 3. LÓGICA DE LOGIN (Mantenemos tu lógica)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #00E676;'>🚜 Login</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuario", key="u")
        p = st.text_input("Clave", type="password", key="p")
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Estilo específico para botón de login (para que no sea gigante)
        st.markdown("""<style>div.stButton > button { height: auto !important; }</style>""", unsafe_allow_html=True)
        
        if st.button("ENTRAR", type="primary", use_container_width=True):
            if verify_user(u, p):
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Error de acceso")
    st.stop()

# 4. HEADER MINIMALISTA
OWNER = st.session_state.user
hoy = datetime.date.today()

c1, c2 = st.columns([2, 1])
with c1:
    st.markdown(f"### {OWNER}")
    st.caption(f"{hoy.strftime('%d %b')}")
with c2:
    st.markdown(f"""
    <div style="text-align: right; padding: 5px;">
        <span style="color: #00E676; font-size: 20px; font-weight: bold;">24°C</span>
    </div>
    """, unsafe_allow_html=True)

# 5. GRID 2x2 (SIN GAP)
# Usamos un contenedor para quitar espacios extra
st.markdown("<br>", unsafe_allow_html=True)

# FILA 1
c_a, c_b = st.columns(2) # Streamlit dividirá la pantalla al 50% exacto
with c_a:
    if st.button("📅\n\nPlanificar"): st.switch_page("pages/Planificador.py")
with c_b:
    if st.button("🚜\n\nJornadas"): st.switch_page("pages/Jornadas.py")

# Espacio pequeño
st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

# FILA 2
c_c, c_d = st.columns(2)
with c_c:
    if st.button("☕\n\nCosecha"): st.switch_page("pages/Cosecha.py")
with c_d:
    if st.button("📦\n\nInsumos"): st.switch_page("pages/Insumos.py")

# Espacio pequeño
st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

# FILA 3
c_e, c_f = st.columns(2)
with c_e:
    if st.button("🗺️\n\nMapa"): st.switch_page("pages/Mapa_Finca.py")
with c_f:
    if st.button("📊\n\nReportes"): st.switch_page("pages/Reportes.py")

# Espacio y Botón Ajustes (Ancho completo)
st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)
if st.button("⚙️ Configuración"):
    st.switch_page("pages/Ajustes.py")

# Botón Salir Discreto
st.markdown("<br>", unsafe_allow_html=True)
if st.button("Salir", type="secondary"):
    st.session_state.logged_in = False
    st.rerun()
