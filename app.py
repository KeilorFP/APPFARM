import streamlit as st
import datetime
from database import verify_user, create_user

# 1. CONFIGURACIÓN
st.set_page_config(
    page_title="Finca App", 
    page_icon="🚜", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. CSS "NUCLEAR" ANTI-ADMIN
st.markdown("""
    <style>
        /* A. FONDO */
        .stApp {
            background: linear-gradient(180deg, #050a06 0%, #102015 100%);
            color: white;
        }

        /* B. OCULTAR TODO LO DE STREAMLIT (NIVEL EXTREMO) */
        
        /* 1. Header y Barra Superior */
        header { visibility: hidden !important; height: 0 !important; }
        [data-testid="stHeader"] { display: none !important; }
        div[class^="st-emotion-cache-"] { padding-top: 0 !important; } /* Quita espacio blanco superior */
        
        /* 2. Barra de Herramientas (La que te molesta) */
        [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; }
        
        /* 3. Botones Flotantes Inferiores (Manage App / Deploy) */
        .stDeployButton { display: none !important; visibility: hidden !important; }
        div[data-testid="stStatusWidget"] { display: none !important; }
        button[kind="header"] { display: none !important; }
        
        /* 4. Pie de página */
        footer { display: none !important; }
        #MainMenu { display: none !important; }
        
        /* C. CONTENEDOR LIMPIO */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        /* D. BOTONES (Tu diseño actual) */
        div.stButton > button {
            width: 100% !important;
            height: 72px !important;
            margin-bottom: 10px !important;
            display: flex !important;
            flex-direction: row !important; 
            align-items: center !important;
            justify-content: flex-start !important;
            padding-left: 20px !important; 
            gap: 15px !important;
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 230, 118, 0.25) !important;
            border-radius: 12px !important;
        }
        
        /* Textos */
        div.stButton > button p:first-child { font-size: 26px !important; margin: 0 !important; }
        div.stButton > button p:last-child { font-size: 18px !important; color: #e0e0e0 !important; }
        
        /* Login */
        h3 { margin: 0 !important; color: #00E676 !important;}
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
        st.markdown("""<style>div.stButton > button { height: 45px !important; justify-content: center !important; padding-left: 0 !important;}</style>""", unsafe_allow_html=True)
        if st.button("ENTRAR", type="primary", use_container_width=True):
            if verify_user(u, p):
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Error")
    st.stop()

# 4. ENCABEZADO
OWNER = st.session_state.user
hoy = datetime.date.today()

c1, c2 = st.columns([2, 1])
with c1:
    st.markdown(f"### {OWNER}")
    st.caption(f"{hoy.strftime('%d %B')}")
with c2:
    st.markdown("""
    <div style="text-align: right; margin-top: 5px;">
        <span style="color: #00E676; font-weight: bold; font-size: 20px;">24°C</span>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 5. MENÚ
if st.button("📅  Planificador"): st.switch_page("pages/Planificador.py")
if st.button("🚜  Jornadas"): st.switch_page("pages/Jornadas.py")
if st.button("☕  Cosecha"): st.switch_page("pages/Cosecha.py")
if st.button("📦  Insumos"): st.switch_page("pages/Insumos.py")
if st.button("🗺️  Mapa"): st.switch_page("pages/Mapa_Finca.py")
if st.button("📊  Reportes"): st.switch_page("pages/Reportes.py")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("⚙️  Configuración"): st.switch_page("pages/Ajustes.py")

st.markdown("<br>", unsafe_allow_html=True)
col_salir, _ = st.columns([1, 2])
with col_salir:
    st.markdown("""<style>div.row-widget.stButton > button[kind="secondary"] { height: 40px !important; border-color: #555 !important; justify-content: center !important; padding-left: 0 !important; }</style>""", unsafe_allow_html=True)
    if st.button("🔒 Salir", type="secondary"):
        st.session_state.logged_in = False
        st.rerun()
