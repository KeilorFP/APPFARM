import streamlit as st
import datetime
import requests
from utils import aplicar_estilos_css
from database import verify_user, create_user

# 1. CONFIGURACIÓN: 'layout="wide"' ES LA CLAVE PARA USAR TODA LA PANTALLA
st.set_page_config(
    page_title="Finca App", 
    page_icon="🚜", 
    layout="wide",  # <--- ESTO OCUPA TODO EL ANCHO
    initial_sidebar_state="collapsed"
)

# 2. CSS "MODO PANTALLA COMPLETA"
st.markdown("""
    <style>
        /* A. FONDO Y COLORES */
        .stApp {
            background: linear-gradient(180deg, #050a06 0%, #102015 100%);
            color: white;
        }

        /* B. QUITAR MÁRGENES EXCESIVOS (Para aprovechar los bordes) */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0.5rem !important; /* Márgenes laterales mínimos */
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }

        /* C. OCULTAR ELEMENTOS INNECESARIOS */
        [data-testid="stSidebar"] { display: none !important; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* D. BOTONES GIGANTES (150px de alto) */
        div.stButton > button {
            width: 100% !important;
            height: 150px !important; /* <--- AUMENTADO PARA SER MUY GRANDE */
            margin-bottom: 5px !important;
            
            display: flex !important;
            flex-direction: column !important; 
            align-items: center !important;
            justify-content: center !important;
            gap: 10px !important;

            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 230, 118, 0.3) !important;
            border-radius: 25px !important; /* Bordes más redondeados */
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
            
            transition: transform 0.1s !important;
        }

        div.stButton > button:active {
            transform: scale(0.97);
            background-color: rgba(0, 230, 118, 0.2) !important;
            border-color: #00E676 !important;
        }

        /* E. TEXTO E ICONOS MÁS GRANDES */
        div.stButton > button p { line-height: 1.2 !important; }
        
        /* Emoji Gigante */
        div.stButton > button p:first-child {
             font-size: 45px !important; /* <--- EMOJI MÁS GRANDE */
             margin-bottom: 0px !important;
             filter: drop-shadow(0 0 8px rgba(0,230,118,0.6));
        }
        
        /* Texto Grande */
        div.stButton > button p:last-child {
             color: #ffffff !important;
             font-size: 19px !important; /* <--- TEXTO MÁS LEGIBLE */
             font-weight: 700 !important;
             letter-spacing: 0.5px !important;
             text-transform: uppercase; /* MAYÚSCULAS PARA QUE SE VEA MEJOR */
        }

        /* F. AJUSTES VARIOS */
        h3 { margin: 0 !important; color: #00E676 !important; font-size: 1.5rem !important; }
        p { color: #ccc; }
        
        /* Login container */
        div[data-testid="stExpander"] { background: rgba(255,255,255,0.05); }
    </style>
""", unsafe_allow_html=True)

# 3. LÓGICA LOGIN (Igual que antes)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

if not st.session_state.logged_in:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #00E676;'>🚜 Acceso</h2>", unsafe_allow_html=True)
        tab_login, tab_registro = st.tabs(["Ingresar", "Registro"])
        
        with tab_login:
            u = st.text_input("Usuario", key="login_u")
            p = st.text_input("Clave", type="password", key="login_p")
            st.markdown("<br>", unsafe_allow_html=True)
            # Botón de login ajustado manualmente para que no sea tan alto como los del menú
            st.markdown("""<style>div.stButton > button { height: auto !important; }</style>""", unsafe_allow_html=True)
            if st.button("ENTRAR", type="primary", use_container_width=True):
                if verify_user(u, p):
                    st.session_state.logged_in = True
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("Datos incorrectos")
        
        with tab_registro:
            new_u = st.text_input("Usuario", key="reg_u")
            new_p = st.text_input("Clave", type="password", key="reg_p")
            if st.button("CREAR", type="secondary", use_container_width=True):
                success, msg = create_user(new_u, new_p)
                if success: st.success(msg)
                else: st.error(msg)
    st.stop()

# 4. ENCABEZADO COMPACTO
OWNER = st.session_state.user
hoy = datetime.date.today()

c1, c2 = st.columns([2, 1])
with c1:
    st.markdown(f"### {OWNER}") # Solo nombre para ahorrar espacio
    st.caption(f"{hoy.strftime('%d %b')}") # Fecha corta
with c2:
    st.markdown(f"""
    <div style="text-align: right; background: rgba(0,230,118,0.1); padding: 5px 10px; border-radius: 12px; border: 1px solid #00E676;">
        <span style="font-size: 16px; font-weight: bold; color: white;">24°C</span>
    </div>
    """, unsafe_allow_html=True)

# 5. MENÚ GRID (PANTALLA COMPLETA)
# Al usar layout="wide" y quitar márgenes, esto llenará la pantalla horizontalmente

c_a, c_b = st.columns(2, gap="small")

with c_a:
    if st.button("📅\n\nPlanificar"): st.switch_page("pages/Planificador.py")
    # Agregamos espacio vertical pequeño entre filas si es necesario, 
    # pero el margin-bottom del CSS ya lo maneja
    if st.button("☕\n\nCosecha"): st.switch_page("pages/Cosecha.py")
    if st.button("🗺️\n\nMapa"): st.switch_page("pages/Mapa_Finca.py")

with c_b:
    if st.button("🚜\n\nJornadas"): st.switch_page("pages/Jornadas.py")
    if st.button("📦\n\nInsumos"): st.switch_page("pages/Insumos.py")
    if st.button("📊\n\nReportes"): st.switch_page("pages/Reportes.py")

# Botón Ajustes al final (Ancho completo)
st.markdown("<br>", unsafe_allow_html=True)
if st.button("⚙️ Configuración"):
    st.switch_page("pages/Ajustes.py")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("Salir 🔒", type="secondary"):
    st.session_state.logged_in = False
    st.rerun()
