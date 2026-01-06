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
        # Si intenta entrar directo a una página sin loguearse, va pa' fuera
        st.switch_page("app.py")
    return st.session_state.user

def mostrar_encabezado(titulo="Finca App"):
    """Muestra el botón de volver y el título de la página."""
    aplicar_estilos_css() # Aseguramos que el estilo cargue siempre
    
    # Columnas: Botón Volver (pequeño) | Título (Resto)
    c1, c2 = st.columns([1, 4])
    
    with c1:
        # Botón discreto para volver al menú principal
        if st.button("⬅️ Menú", key="btn_volver_global", use_container_width=True):
            st.switch_page("app.py")
    
    with c2:
        st.markdown(f"<h3 style='margin-top: 5px; color:#3E2723;'>{titulo}</h3>", unsafe_allow_html=True)
    
    st.divider()

# ==========================================
# 2. ESTILOS VISUALES (CSS)
# ==========================================

def aplicar_estilos_css():
    st.markdown("""
        <style>
        /* A. OCULTAR BARRA LATERAL (SIDEBAR) SIEMPRE */
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none !important; }
        
        /* B. LIMPIEZA DE INTERFAZ */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* C. AJUSTES MÓVILES */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 5rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }

        /* D. PALETA DE COLORES */
        :root { --verde-finca: #2E7D32; --cafe-oscuro: #3E2723; }

        /* E. BOTONES Y TARJETAS */
        div.stButton > button {
            border-radius: 10px !important;
            height: 3rem !important; /* Botones altos para dedos */
        }
        button[kind="primary"] {
            background-color: var(--verde-finca) !important;
            border: none !important;
            color: white !important;
            font-weight: bold !important;
        }
        
        /* Inputs grandes */
        input { font-size: 1.1rem !important; padding: 10px !important; }
        div[data-baseweb="select"] > div { height: 3rem !important; }
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
    """Borra la memoria para recargar datos nuevos."""
    st.cache_data.clear()

def smart_select(label, options, key_name):
    """Crea un selectbox que recuerda qué elegiste la última vez."""
    if not options:
        return st.selectbox(label, ["Sin datos..."], disabled=True)
        
    # Inicializar memoria si no existe
    if key_name not in st.session_state:
        st.session_state[key_name] = options[0]

    # Intentar recuperar el índice
    try:
        default_index = options.index(st.session_state[key_name])
    except ValueError:
        default_index = 0
    
    # Crear el widget
    selected = st.selectbox(label, options, index=default_index, key=f"widget_{key_name}")
    
    # Guardar nueva selección
    st.session_state[key_name] = selected
    return selected