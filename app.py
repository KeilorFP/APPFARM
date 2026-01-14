import streamlit as st
import datetime
import requests
from database import verify_user, create_user

# 1. CONFIGURACIÓN AGRESIVA DE PANTALLA COMPLETA
st.set_page_config(
    page_title="Finca App", 
    page_icon="🚜", 
    layout="wide",  # Ocupar todo el ancho
    initial_sidebar_state="collapsed" # Esconder barra lateral
)

# 2. CSS PARA ELIMINAR BORDES Y OCULTAR "ADMINISTRAR APP"
st.markdown("""
    <style>
        /* A. FONDO OSCURO */
        .stApp {
            background: linear-gradient(180deg, #050a06 0%, #102015 100%);
            color: white;
        }

        /* B. FUERZA BRUTA: ELIMINAR MÁRGENES BLANCOS */
        /* Esto obliga al contenido a tocar casi los bordes del celular */
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }

        /* C. OCULTAR MENÚS DE STREAMLIT (EL BOTÓN MOLESTO) */
        [data-testid="stToolbar"] { display: none !important; } /* Oculta menú top derecha */
        [data-testid="stDecoration"] { display: none !important; } /* Oculta barra de colores top */
        [data-testid="stHeader"] { display: none !important; } /* Oculta todo el header */
        header { display: none !important; } 
        footer { display: none !important; } /* Oculta 'Made with Streamlit' */
        #MainMenu { display: none !important; }

        /* D. BOTONES GIGANTES (PANEL DE CONTROL) */
        div.stButton > button {
            width: 100% !important;
            height: 140px !important; /* Altura fija grande */
            
            display: flex !important;
            flex-direction: column !important; 
            align-items: center !important;
            justify-content: center !important;
            gap: 5px !important;

            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 230, 118, 0.3) !important;
            border-radius: 20px !important;
            margin: 0px !important; /* Sin margen extra */
        }
        
        /* E. TEXTOS DEL BOTÓN */
        /* Emoji */
        div.stButton > button p:first-child {
             font-size: 40px !important; 
             line-height: 1 !important;
             margin: 0 !important;
        }
        /* Texto */
        div.stButton > button p:last-child {
             font-size: 18px !important;
             font-weight: 700 !important;
             text-transform: uppercase;
             color: white !important;
        }

        /* F. HEADER PERSONALIZADO */
        h3 { margin: 0 !important; font-size: 1.2rem !important; color: #00E676 !important;}
        p { margin: 0 !important; }

    </style>
""", unsafe_allow_html=True)

# 3. LÓGICA DE LOGIN (Simplificada visualmente)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #00E676;'>🚜 Login</h2>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Entrar", "Crear"])
        
        with tab1:
            u = st.text_input("Usuario", key="u")
            p = st.text_input("Clave", type="password", key="p")
            st.markdown("<br>", unsafe_allow_html=True)
            # Hack para que el botón de login no sea GIGANTE como los del menú
            if st.button("ENTRAR", type="primary", use_container_width=True):
                if verify_user(u, p):
                    st.session_state.logged_in = True
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("Error")
        with tab2:
            nu = st.text_input("Nuevo Usuario", key="nu")
            np = st.text_input("Nueva Clave", type="password", key="np")
            if st.button("REGISTRAR", type="secondary"):
                s, m = create_user(nu, np)
                if s: st.success(m)
                else: st.error(m)
    st.stop()

# 4. HEADER MINIMALISTA (Para ahorrar espacio)
OWNER = st.session_state.user
hoy = datetime.date.today()

# Usamos columnas ajustadas
c1, c2 = st.columns([2, 1])
with c1:
    st.markdown(f"### {OWNER}")
    st.caption(f"{hoy.strftime('%d %b')}")
with c2:
    st.markdown(f"""
    <div style="text-align: right; background: rgba(0,230,118,0.1); padding: 5px; border-radius: 8px;">
        <span style="color: white; font-weight: bold;">24°C</span>
    </div>
    """, unsafe_allow_html=True)

# 5. GRID 2x2 (Aprovechando todo el ancho)
st.markdown("<br>", unsafe_allow_html=True)

# Definimos las columnas
col_izq, col_der = st.columns(2, gap="small")

with col_izq:
    if st.button("📅\n\nPlanificar"): st.switch_page("pages/Planificador.py")
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True) # Espacio manual
    if st.button("☕\n\nCosecha"): st.switch_page("pages/Cosecha.py")
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
    if st.button("🗺️\n\nMapa"): st.switch_page("pages/Mapa_Finca.py")

with col_der:
    if st.button("🚜\n\nJornadas"): st.switch_page("pages/Jornadas.py")
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
    if st.button("📦\n\nInsumos"): st.switch_page("pages/Insumos.py")
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
    if st.button("📊\n\nReportes"): st.switch_page("pages/Reportes.py")

st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

# Botón Ajustes (Ancho completo al final)
if st.button("⚙️ Configuración"):
    st.switch_page("pages/Ajustes.py")

# Botón Salir (Pequeño y discreto)
st.markdown("<br>", unsafe_allow_html=True)
if st.button("Cerrar Sesión", type="secondary"):
    st.session_state.logged_in = False
    st.rerun()
