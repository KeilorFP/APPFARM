import streamlit as st
from decimal import Decimal
from database import (
    get_all_fincas, get_all_trabajadores, get_trabajadores_por_tipo,
    get_catalogo_productos, get_catalogo_labores
)

# --- NORMALIZADOR ---
def normalize_decimal(value):
    if isinstance(value, Decimal): return float(value)
    if isinstance(value, (list, tuple)): return type(value)(normalize_decimal(v) for v in value)
    return value

# --- CACHÉ INTELIGENTE (Para velocidad) ---
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

# --- SELECTOR CON MEMORIA (Smart Select) ---
def smart_select(label, options, key_name):
    """
    Crea un selectbox que recuerda la última opción seleccionada por el usuario.
    """
    if not options:
        return st.selectbox(label, ["Sin datos..."], disabled=True)
        
    # Inicializar memoria si no existe
    if key_name not in st.session_state:
        st.session_state[key_name] = options[0]

    # Verificar si el valor guardado sigue existiendo en las opciones actuales
    default_index = 0
    if st.session_state[key_name] in options:
        default_index = options.index(st.session_state[key_name])
    
    selected = st.selectbox(label, options, index=default_index, key=f"widget_{key_name}")
    
    # Actualizar memoria
    st.session_state[key_name] = selected
    return selected

# --- SEGURIDAD ---
def check_login():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Acceso denegado. Inicie sesión.")
        st.stop()
    return st.session_state.user

def aplicar_estilos_css():
    st.markdown("""
        <style>
        /* Ocultar menú de Streamlit y Footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Estilo de Tarjetas Métricas */
        div[data-testid="metric-container"] {
            background-color: rgba(28, 31, 46, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s;
        }
        div[data-testid="metric-container"]:hover {
            transform: scale(1.02);
            border-color: #22c55e;
        }

        /* Botones Verdes y Redondos */
        .stButton>button {
            border-radius: 20px;
            font-weight: bold;
            border: none;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #22c55e !important;
            color: black !important;
            box-shadow: 0 0 10px #22c55e;
        }
        
        /* Títulos */
        h1, h2, h3 {
            font-family: 'Segoe UI', sans-serif;
            color: #e2e8f0;
        }
        </style>
    """, unsafe_allow_html=True)