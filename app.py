import streamlit as st
import datetime
import requests
from utils import aplicar_estilos_css
# 1. IMPORTANTE: Funciones de base de datos
from database import verify_user, create_user

# 2. CONFIGURACIÓN DE PÁGINA (Modo Móvil Centrado)
st.set_page_config(
    page_title="Finca App", 
    page_icon="🚜", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# 3. CSS "GLASSMORPHISM DARK" (DISEÑO MÓVIL 2x2)
st.markdown("""
    <style>
        /* A. FONDO OSCURO */
        .stApp {
            background: linear-gradient(180deg, #050a06 0%, #102015 100%);
            color: white;
        }

        /* B. OCULTAR COSAS QUE MOLESTAN EN EL CELULAR */
        [data-testid="stSidebar"] { display: none !important; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* C. BOTONES DEL MENÚ (TARJETAS DE VIDRIO) */
        div.stButton > button {
            width: 100% !important;
            height: 100px !important; /* Altura perfecta para el dedo */
            margin-bottom: 0px !important;
            
            /* Diseño interno: Icono arriba, texto abajo */
            display: flex !important;
            flex-direction: column !important; 
            align-items: center !important;
            justify-content: center !important;
            gap: 8px !important;

            /* Efecto Vidrio (Glassmorphism) */
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 230, 118, 0.3) !important;
            border-radius: 20px !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            
            transition: transform 0.1s !important;
        }

        /* Efecto al presionar */
        div.stButton > button:active {
            transform: scale(0.95);
            background-color: rgba(0, 230, 118, 0.2) !important;
            border-color: #00E676 !important;
        }

        /* D. TEXTO DE LOS BOTONES */
        div.stButton > button p {
            line-height: 1.2 !important;
        }
        
        /* El Emoji (Primer párrafo dentro del botón) */
        div.stButton > button p:first-child {
             font-size: 32px !important; 
             margin-bottom: 0px !important;
             filter: drop-shadow(0 0 5px rgba(0,230,118,0.5));
        }
        
        /* El Texto (Segundo párrafo) */
        div.stButton > button p:last-child {
             color: #ffffff !important;
             font-size: 16px !important;
             font-weight: 600 !important;
             letter-spacing: 0.5px !important;
        }

        /* E. ENCABEZADO Y TEXTOS */
        h3 { margin-bottom: 0 !important; color: #00E676 !important; }
        p { color: #ccc; }
        
        /* F. ESTILO ESPECÍFICO PARA EL LOGIN (Evitar conflictos) */
        div[data-testid="stExpander"] {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }
        
    </style>
""", unsafe_allow_html=True)

# 4. LÓGICA DE LOGIN CON REGISTRO
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Contenedor centrado para el login
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #00E676;'>🚜 Acceso Finca</h2>", unsafe_allow_html=True)
        
        tab_login, tab_registro = st.tabs(["🔑 Ingresar", "📝 Crear Usuario"])
        
        # Pestaña 1: Login
        with tab_login:
            u = st.text_input("Usuario", key="login_u")
            p = st.text_input("Contraseña", type="password", key="login_p")
            
            st.markdown("<br>", unsafe_allow_html=True)
            # Nota: El estilo de botón definido en CSS se aplicará aquí también, se verá moderno
            if st.button("INGRESAR 🔐", type="primary", use_container_width=True):
                if verify_user(u, p):
                    st.session_state.logged_in = True
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("⚠️ Datos incorrectos")

        # Pestaña 2: Registro
        with tab_registro:
            st.caption("Crea una cuenta nueva para el equipo.")
            new_u = st.text_input("Nuevo Usuario", key="reg_u")
            new_p = st.text_input("Nueva Contraseña", type="password", key="reg_p")
            confirm_p = st.text_input("Confirmar", type="password", key="reg_c")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("CREAR CUENTA ✨", type="secondary", use_container_width=True):
                if not new_u or not new_p:
                    st.warning("⚠️ Llena todo.")
                elif new_p != confirm_p:
                    st.error("❌ Las claves no coinciden.")
                else:
                    success, msg = create_user(new_u, new_p)
                    if success:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
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

col_saludo, col_clima = st.columns([2, 1])

with col_saludo:
    st.markdown(f"### Hola, {OWNER} 👋")
    st.caption(f"{hoy.strftime('%d de %B, %Y')}")

with col_clima:
    temp, prob = obtener_clima_cached()
    if temp:
        # Micro-widget de clima
        st.markdown(f"""
        <div style="text-align: right; background: rgba(255,255,255,0.05); padding: 5px; border-radius: 10px;">
            <span style="font-size: 18px; font-weight: bold; color: white;">{temp}°C</span><br>
            <span style="font-size: 11px; color: #00E676;">☔ {prob}%</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 6. MENÚ GRID 2x2 (OPTIMIZADO PARA CELULAR)
# Usamos 'gap="small"' para que se vean juntos pero ordenados

# --- FILA 1 ---
c1, c2 = st.columns(2, gap="small")
with c1:
    if st.button("📅\n\nPlanificar"): st.switch_page("pages/Planificador.py")
with c2:
    if st.button("🚜\n\nJornadas"): st.switch_page("pages/Jornadas.py")

st.markdown("<br>", unsafe_allow_html=True) # Espacio separador

# --- FILA 2 ---
c3, c4 = st.columns(2, gap="small")
with c3:
    if st.button("☕\n\nCosecha"): st.switch_page("pages/Cosecha.py")
with c4:
    if st.button("📦\n\nInsumos"): st.switch_page("pages/Insumos.py")

st.markdown("<br>", unsafe_allow_html=True) # Espacio separador

# --- FILA 3 ---
c5, c6 = st.columns(2, gap="small")
with c5:
    if st.button("🗺️\n\nMapa"): st.switch_page("pages/Mapa_Finca.py")
with c6:
    if st.button("📊\n\nReportes"): st.switch_page("pages/Reportes.py")

# --- AJUSTES Y SALIDA ---
st.markdown("<br>", unsafe_allow_html=True)
if st.button("⚙️   Configuración & Ajustes"):
    st.switch_page("pages/Ajustes.py")

st.markdown("<br><br>", unsafe_allow_html=True)
if st.button("Cerrar Sesión 🔒", type="secondary"):
    st.session_state.logged_in = False
    st.rerun()
