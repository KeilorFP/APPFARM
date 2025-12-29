import streamlit as st
import datetime
import time
from database import list_plans, add_plan, mark_plan_done_and_autorenew, postpone_plan, delete_plan, update_plan_simple, get_plan_by_id
from utils import check_login, cargar_fincas, cargar_personal, cargar_labores, cargar_productos, smart_select

OWNER = check_login()
st.title("📅 Planificador")

hoy = datetime.date.today()
c1, c2 = st.columns([1,2])
vista = c1.radio("Vista", ["Semana", "Mes"], horizontal=True, label_visibility="collapsed")
# AGREGAMOS KEY ÚNICO AQUÍ 👇
f_ref = c2.date_input("Fecha de consulta", hoy, label_visibility="collapsed", key="fecha_filtro_plan")

if vista == "Semana":
    ini = f_ref - datetime.timedelta(days=f_ref.weekday())
    fin = ini + datetime.timedelta(days=6)
else:
    import calendar
    ini = f_ref.replace(day=1)
    fin = f_ref.replace(day=calendar.monthrange(f_ref.year, f_ref.month)[1])

# --- MODO EDICIÓN ---
if "edit_mode_plan" in st.session_state:
    pid = st.session_state.edit_mode_plan
    data = get_plan_by_id(pid, OWNER)
    if data:
        with st.container(border=True):
            st.markdown(f"**✏️ Editando Tarea #{pid}**")
            _, old_f, old_l, old_t, old_tr, old_ac, old_pr, old_ct = data
            ec1, ec2 = st.columns(2)
            # KEY ÚNICO PARA EDICIÓN 👇
            nf = ec1.date_input("Nueva Fecha", old_f, key=f"edit_f_{pid}")
            nl = ec2.selectbox("Lote", cargar_fincas(OWNER), index=cargar_fincas(OWNER).index(old_l) if old_l in cargar_fincas(OWNER) else 0)
            nt = st.selectbox("Tipo", ["Jornada","Abono","Fumigación","Cal","Herbicida"], index=["Jornada","Abono","Fumigación","Cal","Herbicida"].index(old_t))
            
            n_tr, n_ac, n_pr, n_ct = None, None, None, 0.0
            if nt == "Jornada":
                trabs = cargar_personal(OWNER, "Jornalero")
                n_tr = st.selectbox("Trabajador", trabs, index=trabs.index(old_tr) if old_tr in trabs else 0)
                n_ac = st.text_input("Actividad", old_ac)
            else:
                n_pr = st.text_input("Producto", old_pr)
                n_ct = st.number_input("Cantidad", float(old_ct) if old_ct else 0.0)

            if st.button("💾 Guardar Cambios", type="primary"):
                update_plan_simple(pid, str(nf), nl, nt, n_tr, n_ac, n_pr, n_ct, OWNER)
                del st.session_state.edit_mode_plan; st.rerun()
            if st.button("Cancelar"): del st.session_state.edit_mode_plan; st.rerun()

# --- AGREGAR ---
if "edit_mode_plan" not in st.session_state:
    with st.expander("➕ Nueva Tarea"):
        fincas = cargar_fincas(OWNER)
        if fincas:
            tipo = st.selectbox("Tipo de labor", ["Jornada","Abono","Fumigación","Cal","Herbicida"], key="tipo_nueva_tarea")
            c_a, c_b = st.columns(2)
            # KEY ÚNICO PARA CREACIÓN 👇
            fp = c_a.date_input("Fecha para realizar", hoy, key="fecha_crear_tarea")
            lp = smart_select("Lote de destino", fincas, "mem_lote_plan")
            
            kw = {}
            if tipo == "Jornada":
                tr = st.selectbox("Trabajador asignado", cargar_personal(OWNER, "Jornalero"))
                ac = st.selectbox("Labor a realizar", cargar_labores(OWNER))
                kw = {"trabajador": tr, "actividad": ac}
            else:
                pr = st.selectbox("Producto a usar", cargar_productos(OWNER))
                ct = st.number_input("Cantidad necesaria", 0.0)
                kw = {"producto": pr, "cantidad": ct}
            
            if st.button("📅 Agendar Labor"):
                add_plan(OWNER, str(fp), lp, tipo, **kw)
                st.success("Labor agendada"); time.sleep(0.5); st.rerun()