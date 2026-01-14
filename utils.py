import streamlit as st
from decimal import Decimal
from database import (
    get_all_fincas, get_all_trabajadores, get_trabajadores_por_tipo,
    get_catalogo_productos, get_catalogo_labores
)

# ==========================================
# 1. SEGURIDAD Y NAVEGACIÓN
# ==========================================

def check_login():
    """Verifica si el usuario entró. Si no, lo manda al inicio."""
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.switch_page("app.py")
    return st.session_state.user

def mostrar_encabezado(titulo="Finca App"):
    """Muestra el botón de volver y el título de la página con estilo moderno."""
    aplicar_estilos_css() # Inyectamos el diseño aquí
    
    # Grid: Botón Volver (pequeño) | Título (Grande)
    c1, c2 = st.columns([1, 4], gap="small")
    
    with c1:
        # Botón para volver
        if st.button("⬅️", key="btn_volver_global", use_container_width=True):
            st.switch_page("app.py")
    
    with c2:
        # Título en verde neón o blanco
        st.markdown(f"<h2 style='margin: 0; padding-top: 5px; color:#00E676; font-weight: 300;'>{titulo}</h2>", unsafe_allow_html=True)
    
    st.divider()

# ==========================================
# 2. ESTILOS VISUALES (CSS MODERNO)
# ==========================================

def aplicar_estilos_css():
    st.markdown("""
        <style>
        /* A. FONDO OSCURO GENERAL */
        .stApp {
            background: linear-gradient(180deg, #0f1712 0%, #0a1f13 100%);
            color: #e0e0e0;
        }

        /* B. OCULTAR BARRA LATERAL Y ELEMENTOS EXTRA */
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none !important; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* C. AJUSTES DE ESPACIO MÓVIL */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 5rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        /* D. ESTILO DE BOTONES (GLASSMORPHISM) */
        div.stButton > button {
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 230, 118, 0.3) !important;
            border-radius: 12px !important;
            color: white !important;
            height: 3.2rem !important; /* Altura cómoda para el dedo */
            font-weight: 600 !important;
            transition: all 0.2s;
        }
        
        div.stButton > button:active {
            background-color: rgba(0, 230, 118, 0.2) !important;
            transform: scale(0.98);
        }
        
        /* Botones Primarios (Acciones fuertes) */
        button[kind="primary"] {
            background: linear-gradient(135deg, rgba(0, 230, 118, 0.2) 0%, rgba(0, 200, 83, 0.1) 100%) !important;
            border: 1px solid #00E676 !important;
            box-shadow: 0 0 10px rgba(0, 230, 118, 0.1);
        }

        /* E. INPUTS Y SELECTS (Adaptados al modo oscuro) */
        /* Texto de etiquetas */
        .stMarkdown label, .stTextInput label, .stNumberInput label, .stSelectbox label {
            color: #00E676 !important; /* Verde neón para etiquetas */
            font-weight: 500;
        }
        
        /* Cajas de texto */
        div[data-baseweb="input"], div[data-baseweb="select"] > div {
            background-color: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            color: white !important;
        }
        
        /* Texto dentro de los inputs */
        input { color: white !important; }
        
        /* Divisores */
        hr { border-color: rgba(0, 230, 118, 0.2) !important; }

        /* Expander (Acordeones) */
        .streamlit-expanderHeader {
            background-color: rgba(255, 255, 255, 0.02) !important;
            color: white !important;
            border-radius: 8px !important;
        }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS (Cache y Utilidades)
# ==========================================

def normalize_decimal(value):
    """Convierte Decimals de la BD a float para que Python no falle."""
    if isinstance(value, Decimal): return float(value)
    if isinstance(value, (list, tuple)): return type(value)(normalize_decimal(v) for v in value)
    return value

@st.cache_data(ttl=60, show_spinner=False)
def cargar_fincas(owner):
    return normalize_decimal(get_all_fincas(owner))

@st.cache_data(ttl=60, show_spinner=False)
def cargar_personal(owner, tipo=None):
    if tipo:
        try: return normalize_decimal(get_trabajadores_por_tipo(owner, tipo))
        except: return []
    return normalize_decimal(get_all_trabajadores(owner))

@st.cache_data(ttl=60, show_spinner=False)
def cargar_productos(owner):
    return get_catalogo_productos(owner)

@st.cache_data(ttl=60, show_spinner=False)
def cargar_labores(owner):
    return get_catalogo_labores(owner)

def limpiar_cache():
    st.cache_data.clear()

def smart_select(label, options, key_name):
    """Crea un selectbox que recuerda qué elegiste la última vez."""
    if not options:
        return st.selectbox(label, ["Sin datos..."], disabled=True)
        
    if key_name not in st.session_state:
        st.session_state[key_name] = options[0]

    try:
        default_index = options.index(st.session_state[key_name])
    except ValueError:
        default_index = 0
    
    selected = st.selectbox(label, options, index=default_index, key=f"widget_{key_name}")
    st.session_state[key_name] = selected
    return selected
