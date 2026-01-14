import streamlit as st
import datetime
import requests
from database import verify_user, create_user

# 1. CONFIGURACIÓN: LAYOUT WIDE (OBLIGATORIO)
st.set_page_config(
    page_title="Finca App", 
    page_icon="🚜", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# 2. CSS AGRESIVO (FORZAR GRID 2x2 EN MÓVIL)
st.markdown("""
    <style>
        /* A. FONDO OSCURO */
        .stApp {
            background: linear-gradient(180deg, #050a06 0%, #102015 100%);
            color: white;
        }

        /* B. ELIMINAR TODOS LOS MÁRGENES DE LA PANTALLA */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }

        /* C. OCULTAR BARRA DE HERRAMIENTAS (ADMINISTRAR APP) */
        [data-testid="stToolbar"] { display: none !important; } 
        [data-testid="stHeader"] { display: none !important; } 
        footer { display: none !important; }
        .stDeployButton { display: none !important; } /* Oculta el botón flotante inferior */
        div[class*="stDecoration"] { display: none !important; }

        /* D. TRUCO MAESTRO: OBLIGAR COLUMNAS LADO A LADO EN MÓVIL */
        /* Esto evita que se pongan una debajo de otra */
        [data-testid="column"] {
            width: 50% !important;
            flex: 1 1 50% !important;
            min-width: 50% !important;
        }
        
        /* E. ESTILO DE LOS BOTONES GIGANTES */
        div.stButton > button {
            width: 100% !important;
            height: 140px !important; /* Altura fija */
            margin: 0px !important;
            padding: 0px !important;
            
            /* Alineación interna */
            display: flex !important;
            flex-direction: column !important; 
            align-items: center !important;
            justify-content: center !important;
            gap: 5px !important;

            /* Visual */
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 230, 118, 0.4) !important;
            border-radius: 15px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        
        /* F. TEXTO DENTRO DE LOS BOTONES */
        div.stButton > button p { line-height: 1.1 !important; }
        
        div.stButton > button p:first-child {
             font-size: 38px !important; /* Emoji grande */
             margin: 0 !important;
        }
        
        div.stButton > button p:last-child {
             font-size: 16px !important; /* Texto legible */
             font-weight: 700 !important;
             color: #ffffff !important;
             text-transform: uppercase;
        }
        
        /* G. LOGIN */
        div[data-testid="stExpander"] { background: rgba(255,255,255,0.05); }

    </style>
""", unsafe_allow_html=True)

# 3. LÓGICA DE LOGIN
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #00E676;'>🚜 Acceso</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuario", key="u")
        p = st.text_input("Clave", type="password", key="p")
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Botón de login normal
        st.markdown("""<style>div.stButton > button { height: auto !important; }</style>""", unsafe_allow_html=True)
        if st.button("ENTRAR", type="primary", use_container_width=True):
            if verify_user(u, p):
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Error")
    st.stop()

# 4. HEADER
OWNER = st.session_state.user
hoy = datetime.date.today()

c1, c2 = st.columns([2, 1])
with c1:
    st.markdown(f"<h3 style='color:#00E676; margin:0;'>{OWNER}</h3>", unsafe_allow_html=True)
    st.caption(f"{hoy.strftime('%d %b')}")
with c2:
    st.markdown("""
    <div style="text-align: right;">
        <span style="color: white; font-weight: bold; font-size: 20px;">24°C</span>
    </div>""", unsafe_allow_html=True)

# 5. GRID 2x2 FORZADO
st.markdown("<br>", unsafe_allow_html=True)

# FILA 1
c_a, c_b = st.columns(2, gap="small")
with c_a:
    if st.button("📅\n\nPlanificar", key="btn_plan"): st.switch_page("pages/Planificador.py")
with c_b:
    if st.button("🚜\n\nJornadas", key="btn_jor"): st.switch_page("pages/Jornadas.py")

st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True) # Pequeño espacio vertical

# FILA 2
c_c, c_d = st.columns(2, gap="small")
with c_c:
    if st.button("☕\n\nCosecha", key="btn_cos"): st.switch_page("pages/Cosecha.py")
with c_d:
    if st.button("📦\n\nInsumos", key="btn_ins"): st.switch_page("pages/Insumos.py")

st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)

# FILA 3
c_e, c_f = st.columns(2, gap="small")
with c_e:
    if st.button("🗺️\n\nMapa", key="btn_map"): st.switch_page("pages/Mapa_Finca.py")
with c_f:
    if st.button("📊\n\nReportes", key="btn_rep"): st.switch_page("pages/Reportes.py")

# BOTONES DE ABAJO
st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)
if st.button("⚙️ Configuración", key="btn_conf"):
    st.switch_page("pages/Ajustes.py")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("Salir", type="secondary"):
    st.session_state.logged_in = False
    st.rerun()
