import streamlit as st
import pandas as pd
import datetime
import time
from decimal import Decimal
from streamlit_option_menu import option_menu
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# ==========================================
# 📥 IMPORTACIÓN DE BACKEND
# ==========================================
try:
    from database import (
        connect_db, create_all_tables, verify_user, add_user,
        get_all_fincas, add_finca, delete_finca,
        get_all_trabajadores, add_trabajador, delete_trabajador_by_fullname,
        add_jornada, get_all_jornadas, get_last_jornada_by_date, update_jornada,
        add_insumo, get_tarifas, set_tarifas,
        get_jornadas_between, get_insumos_between,
        crear_cierre_mensual, listar_cierres,
        add_plan, list_plans, mark_plan_done_and_autorenew, postpone_plan,
        add_recoleccion_batch, get_reporte_cosecha_detallado, get_totales_por_lote,
        get_trabajadores_por_tipo # <--- Asegúrate que esta función exista en database.py
    )
except ImportError as e:
    st.error(f"❌ Error crítico: No se pudieron importar funciones de database.py: {e}")
    st.info("💡 Sugerencia: Revisa que database.py tenga la función 'get_trabajadores_por_tipo'.")
    st.stop()

# ==========================================
# ⚙️ CONFIGURACIÓN "DARK TECH"
# ==========================================
st.set_page_config(page_title="Finca App Pro", page_icon="☕", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: radial-gradient(circle at top, #141824 0, #05060a 40%, #020308 100%); }
    .block-container { padding-top: 1rem !important; max-width: 850px !important; }
    #MainMenu, footer, header {visibility: hidden;}
    .metric-card {
        background: linear-gradient(145deg, #181d2b, #11141f);
        border-radius: 16px; padding: 14px 16px;
        box-shadow: 0 14px 35px rgba(0,0,0,0.55);
        border: 1px solid rgba(255,255,255,0.04);
        text-align: center;
    }
    .stButton>button {
        width: 100%; border-radius: 999px;
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 40%, #15803d 100%);
        color: #0b1120; border: none; font-weight: 600;
    }
    input, select, textarea { border-radius: 12px !important; background-color: rgba(15, 23, 42, 0.8) !important; color: #e5e7eb !important; }
    .stTabs [aria-selected="true"] { background-color: #22c55e !important; color: #000 !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔧 UTILS & CACHÉ
# ==========================================
def _normalize_decimal(value):
    if isinstance(value, Decimal): return float(value)
    if isinstance(value, (list, tuple)): return type(value)(_normalize_decimal(v) for v in value)
    return value

@st.cache_data(ttl=10, show_spinner=False)
def cargar_personal_por_tipo(owner, tipo):
    try:
        # Intenta usar la función específica, si falla usa la genérica
        try:
            raw = get_trabajadores_por_tipo(owner, tipo)
        except NameError:
            raw = get_all_trabajadores(owner) # Fallback por si database.py es viejo
        return _normalize_decimal(raw)
    except Exception as e:
        return []

@st.cache_data(ttl=60, show_spinner=False)
def cargar_fincas_rapido(owner):
    try: return _normalize_decimal(get_all_fincas(owner))
    except: return []

def limpiar_cache():
    st.cache_data.clear()

# ==========================================
# 🔐 LOGIN
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #22c55e;'>☕ Finca App Pro</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["Ingresar", "Registrar"])
    with t1:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("🚀 Entrar", type="primary"):
            if verify_user(u, p):
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Credenciales incorrectas")
    with t2:
        nu = st.text_input("Nuevo Usuario")
        np = st.text_input("Nueva Contraseña", type="password")
        if st.button("Crear Cuenta"):
            if add_user(nu, np): st.success("Creado correctamente")
            else: st.error("Error al crear usuario")
    st.stop()

OWNER = st.session_state.user

# ==========================================
# 📱 NAVEGACIÓN
# ==========================================
selected = option_menu(
    menu_title=None,
    options=["Inicio", "Planificador", "Cosecha", "Jornadas", "Insumos", "Reportes", "Ajustes"],
    icons=["house", "calendar-week", "basket", "person-check", "box-seam", "file-earmark-bar-graph", "gear"],
    default_index=0, orientation="horizontal",
    styles={"nav-link": {"font-size": "10px", "margin": "1px", "border-radius": "10px"}, "nav-link-selected": {"background-color": "#22c55e", "color": "#000"}}
)

# ==========================================
# 🏠 INICIO
# ==========================================
if selected == "Inicio":
    st.markdown(f"#### 👋 Hola, {OWNER}")
    fincas = cargar_fincas_rapido(OWNER)
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='metric-card'><h4>Fincas</h4><h2>{len(fincas)}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><h4>Estado</h4><h2>Activo</h2></div>", unsafe_allow_html=True)

# ==========================================
# 🗓️ PLANIFICADOR (RESTAURADO)
# ==========================================
elif selected == "Planificador":
    st.markdown("### 🗓️ Calendario de Labores")
    
    # Filtros de Fecha
    hoy = datetime.date.today()
    c1, c2 = st.columns([1,2])
    vista = c1.radio("Vista", ["Semana", "Mes"], horizontal=True, label_visibility="collapsed")
    f_ref = c2.date_input("Fecha", hoy, label_visibility="collapsed")

    if vista == "Semana":
        ini = f_ref - datetime.timedelta(days=f_ref.weekday())
        fin = ini + datetime.timedelta(days=6)
    else:
        import calendar
        ini = f_ref.replace(day=1)
        fin = f_ref.replace(day=calendar.monthrange(f_ref.year, f_ref.month)[1])
    
    st.info(f"Mostrando planes del **{ini}** al **{fin}**")

    # Formulario para Agendar
    with st.expander("➕ Agendar Nueva Labor"):
        fincas = cargar_fincas_rapido(OWNER)
        if fincas:
            tipo = st.selectbox("Tipo", ["Jornada","Abono","Fumigación","Cal","Herbicida"])
            ca, cb = st.columns(2)
            f_p = ca.date_input("Para cuándo", hoy)
            l_p = cb.selectbox("Lote destino", fincas)
            
            # Inputs dinámicos
            if tipo == "Jornada":
                trabajadores = cargar_personal_por_tipo(OWNER, "Jornalero")
                t_sel = st.selectbox("Trabajador", trabajadores) if trabajadores else None
                act_sel = st.text_input("Actividad (Poda, Deshije...)")
                kwargs = {"trabajador": t_sel, "actividad": act_sel}
            else:
                prod = st.text_input("Producto")
                cant = st.number_input("Cantidad", 0.0)
                kwargs = {"producto": prod, "cantidad": cant}
                
            if st.button("📅 Agendar Tarea"):
                add_plan(OWNER, str(f_p), l_p, tipo, **kwargs)
                st.success("Tarea agendada")
                time.sleep(1)
                st.rerun()
        else:
            st.warning("Registra fincas primero en Ajustes.")

    # Lista de Tareas
    try:
        planes = list_plans(OWNER, ini, fin)
        if not planes:
            st.write("✅ No hay tareas pendientes para este periodo.")
        else:
            for p in planes:
                # Desempaquetado seguro (evita errores si cambian las columnas)
                pid = p[0]
                fecha = p[1]
                lote = p[2]
                tipo = p[3]
                estado = p[13] # Índice basado en la consulta SQL estándar
                detalle = p[4] if tipo == "Jornada" else p[7] # Trabajador o Producto
                
                # Card Visual
                color = "#22c55e" if estado == "realizado" else "#eab308"
                with st.container(border=True):
                    col_info, col_btn = st.columns([4, 1])
                    with col_info:
                        st.markdown(f"**{tipo}** en *{lote}* - {fecha}")
                        st.caption(f"Detalle: {detalle} | Estado: {estado}")
                    with col_btn:
                        if estado == "pendiente":
                            if st.button("✅", key=f"ok_{pid}"):
                                mark_plan_done_and_autorenew(OWNER, pid, OWNER)
                                st.rerun()
    except Exception as e:
        st.error(f"Error al cargar planes: {e}")

# ==========================================
# ☕ COSECHA (RECOLECTORES)
# ==========================================
elif selected == "Cosecha":
    st.markdown("### ☕ Control de Recolección")
    t_reg, t_plan = st.tabs(["📝 Medida Diaria", "💰 Planilla Semanal"])

    with t_reg:
        fincas = cargar_fincas_rapido(OWNER)
        # FILTRO: Solo recolectores
        recolectores = cargar_personal_por_tipo(OWNER, "Recolector")
        
        if not fincas or not recolectores:
            st.warning("⚠️ Necesitas registrar Fincas y Personal tipo 'Recolector' en Ajustes.")
        else:
            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                f_hoy = c1.date_input("Fecha", datetime.date.today())
                l_hoy = c2.selectbox("Lote", fincas)
                p_hoy = c3.number_input("Precio Cajuela ₡", value=1300.0, step=50.0)

            # Grid de entrada rápida (Sin notas, width stretch)
            if "df_recoleccion" not in st.session_state:
                st.session_state.df_recoleccion = pd.DataFrame({
                    "Recolector": recolectores,
                    "Cajuelas": [0.0] * len(recolectores)
                })

            edited_df = st.data_editor(
                st.session_state.df_recoleccion,
                column_config={
                    "Recolector": st.column_config.TextColumn("Nombre", disabled=True),
                    "Cajuelas": st.column_config.NumberColumn("Cajuelas", min_value=0.0, step=0.25)
                },
                hide_index=True, width='stretch'
            )

            if st.button("💾 Guardar Cosecha de Hoy", type="primary"):
                try:
                    datos = []
                    for _, row in edited_df.iterrows():
                        if row["Cajuelas"] > 0:
                            datos.append((str(f_hoy), row["Recolector"], l_hoy, float(row["Cajuelas"]), float(p_hoy), OWNER))
                    
                    if datos:
                        if add_recoleccion_batch(datos):
                            st.success(f"✅ ¡{len(datos)} registros guardados!")
                            # Resetear grid
                            del st.session_state.df_recoleccion
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Error al guardar en base de datos.")
                    else:
                        st.warning("No hay datos para guardar (todo en 0).")
                except Exception as e:
                    st.error(f"Error procesando datos: {e}")

    with t_plan:
        st.markdown("#### 💰 Acumulado Semanal (Lunes-Domingo)")
        hoy = datetime.date.today()
        ini_sem = hoy - datetime.timedelta(days=hoy.weekday())
        fin_sem = ini_sem + datetime.timedelta(days=6)
        
        c1, c2 = st.columns(2)
        f1 = c1.date_input("Desde", ini_sem)
        f2 = c2.date_input("Hasta", fin_sem)

        try:
            raw = get_reporte_cosecha_detallado(f1, f2, OWNER)
            if raw:
                df = pd.DataFrame(raw, columns=["Recolector", "Lote", "Cajuelas", "Total ₡"])
                
                # Tabla dinámica (Pivot)
                pivot = df.pivot_table(index="Recolector", columns="Lote", values="Cajuelas", aggfunc="sum", fill_value=0)
                pivot["TOTAL CAJUELAS"] = pivot.sum(axis=1)
                pivot["A PAGAR"] = df.groupby("Recolector")["Total ₡"].sum()
                
                # Formato visual
                st.dataframe(
                    pivot, 
                    width='stretch',
                    column_config={"A PAGAR": st.column_config.NumberColumn(format="₡%.0f")}
                )
                
                total_dinero = df['Total ₡'].sum()
                st.metric("Total Planilla a Pagar", f"₡{total_dinero:,.0f}")
                
                # Generar PDF Simple
                if st.button("Descargar PDF de Pago"):
                    buffer = BytesIO()
                    p = canvas.Canvas(buffer, pagesize=letter)
                    p.drawString(100, 750, f"Planilla Recolección: {f1} al {f2}")
                    y = 730
                    for idx, row in pivot.iterrows():
                        p.drawString(50, y, f"{idx}: {row['TOTAL CAJUELAS']:.2f} cajuelas - ₡{row['A PAGAR']:,.0f}")
                        y -= 20
                    p.save()
                    st.download_button("📄 Bajar PDF", buffer.getvalue(), "planilla_cafe.pdf", "application/pdf")
                    
            else:
                st.info("No hay recolección registrada en estas fechas.")
        except Exception as e:
            st.error(f"Error cargando reporte: {e}")

# ==========================================
# 🧑‍🌾 JORNADAS (JORNALEROS)
# ==========================================
elif selected == "Jornadas":
    st.markdown("### 🧑‍🌾 Registro de Jornales")
    fincas = cargar_fincas_rapido(OWNER)
    # FILTRO: Solo jornaleros
    jornaleros = cargar_personal_por_tipo(OWNER, "Jornalero")

    if not fincas or not jornaleros:
        st.warning("⚠️ Registra Fincas y Personal tipo 'Jornalero' en Ajustes.")
    else:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            trab = c1.selectbox("Jornalero", jornaleros)
            lote = c2.selectbox("Lote", fincas)
            fecha = st.date_input("Fecha", datetime.date.today())
            act = st.selectbox("Actividad", ["Chapea", "Poda", "Fumigación", "Deshije", "Otros"])
            d, e = st.columns(2)
            num_d = d.number_input("Días", 1.0)
            num_e = e.number_input("Horas Extra", 0.0)

            if st.button("💾 Guardar Jornal"):
                try:
                    add_jornada(trab, str(fecha), lote, act, int(num_d), int(num_d)*6, float(num_e), OWNER)
                    st.success("Guardado correctamente")
                except Exception as e:
                    st.error(f"Error guardando jornal: {e}")

# ==========================================
# 📦 INSUMOS
# ==========================================
elif selected == "Insumos":
    st.markdown("### 📦 Control de Gastos")
    fincas = cargar_fincas_rapido(OWNER)
    if not fincas:
        st.warning("Registra fincas primero.")
    else:
        tipo = st.radio("Tipo", ["Abono", "Fumigación", "Cal", "Herbicida"], horizontal=True)
        with st.container(border=True):
            c1, c2 = st.columns(2)
            lote = c1.selectbox("Lote Aplicación", fincas)
            fecha = c2.date_input("Fecha Aplicación", datetime.date.today())
            
            prod = st.text_input("Producto")
            dosis = st.text_input("Dosis")
            c3, c4 = st.columns(2)
            cant = c3.number_input("Cantidad Total", 0.0)
            precio = c4.number_input("Costo Total ₡", 0.0)
            
            if st.button(f"Guardar {tipo}"):
                add_insumo(str(fecha), lote, tipo, "", prod, dosis, cant, precio, OWNER)
                st.success("Gasto registrado")

# ==========================================
# 📑 REPORTES
# ==========================================
elif selected == "Reportes":
    st.markdown("### 📊 Reporte Financiero Mensual")
    c1, c2 = st.columns(2)
    mes = c1.selectbox("Mes", range(1, 13), index=datetime.date.today().month - 1)
    anio = c2.number_input("Año", value=2025)
    
    if st.button("Generar Cierre de Mes", width="stretch"):
        # Fechas
        import calendar
        ini = datetime.date(anio, mes, 1)
        fin = datetime.date(anio, mes, calendar.monthrange(anio, mes)[1])
        
        try:
            td, th = get_tarifas(OWNER)
            pid = crear_cierre_mensual(ini, fin, OWNER, OWNER, float(td), float(th), overwrite=True)
            st.success(f"Cierre generado con ID: {pid}")
        except Exception as e:
            st.error(f"Error generando cierre: {e}")
            
    # Listar cierres pasados
    cierres = listar_cierres(OWNER)
    if cierres:
        st.write("---")
        df_c = pd.DataFrame(cierres, columns=["ID", "Inicio", "Fin", "Creador", "Fecha", "Nómina", "Insumos", "Total"])
        st.dataframe(df_c, width="stretch")

# ==========================================
# ⚙️ AJUSTES (CONFIGURACIÓN)
# ==========================================
elif selected == "Ajustes":
    st.markdown("### ⚙️ Configuración")
    tab = st.segmented_control("Sección", ["Fincas", "Personal", "Tarifas"])

    if tab == "Fincas":
        nf = st.text_input("Nombre de Finca/Lote")
        if st.button("Añadir Finca"):
            add_finca(nf, OWNER)
            limpiar_cache()
            st.rerun()
        
        # Eliminar
        fincas = cargar_fincas_rapido(OWNER)
        del_f = st.selectbox("Eliminar Finca", ["Seleccionar..."] + fincas)
        if del_f != "Seleccionar..." and st.button("Borrar Finca"):
            delete_finca(del_f, OWNER)
            limpiar_cache()
            st.rerun()

    elif tab == "Personal":
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nombre")
        ape = c2.text_input("Apellido")
        # SELECCIÓN CRÍTICA: Jornalero o Recolector
        tipo_p = st.radio("Tipo de Personal", ["Jornalero", "Recolector"], horizontal=True)
        
        if st.button("Añadir Persona"):
            # Usamos la función segura del backend
            try:
                if add_trabajador(nom, ape, tipo_p, OWNER):
                    st.success(f"{nom} añadido como {tipo_p}")
                    limpiar_cache()
                else:
                    st.error("Error: Puede que ya exista.")
            except Exception as e:
                st.error(f"Error técnico: {e}")
        
        # Eliminar Personal
        all_p = get_all_trabajadores(OWNER) # Función genérica para listar todos
        del_p = st.selectbox("Eliminar Personal", ["Seleccionar..."] + all_p)
        if del_p != "Seleccionar..." and st.button("Borrar Persona"):
            delete_trabajador_by_fullname(OWNER, del_p)
            limpiar_cache()
            st.rerun()

    elif tab == "Tarifas":
        td, th = get_tarifas(OWNER)
        ntd = st.number_input("Pago Día ₡", value=float(td))
        nth = st.number_input("Pago Hora Extra ₡", value=float(th))
        if st.button("Guardar Tarifas"):
            set_tarifas(OWNER, ntd, nth)
            st.success("Tarifas actualizadas")

    st.divider()
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()