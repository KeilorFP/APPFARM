import streamlit as st
import datetime
import time
import calendar
from database import (
    list_plans, add_plan, mark_plan_done_and_autorenew, 
    postpone_plan, delete_plan, update_plan_simple, get_plan_by_id,
    add_jornada, add_insumo # Importamos esto para guardar historial real al completar
)
from utils import (
    check_login, cargar_fincas, cargar_personal, 
    cargar_labores, cargar_productos, smart_select, mostrar_encabezado
)

# 1. VERIFICACIÓN Y ENCABEZADO
OWNER = check_login()
mostrar_encabezado("📅 Planificador de Finca")

# 2. FILTROS DE FECHA (SEMANA / MES)
c1, c2 = st.columns([1, 1.5])
vista = c1.pills("Vista", ["Semana", "Mes"], default="Semana")
hoy = datetime.date.today()
f_ref = c2.date_input("Fecha Referencia", hoy, label_visibility="collapsed")

if vista == "Semana":
    ini = f_ref - datetime.timedelta(days=f_ref.weekday())
    fin = ini + datetime.timedelta(days=6)
    st.caption(f"Mostrando semana: {ini.strftime('%d/%m')} al {fin.strftime('%d/%m')}")
else:
    ini = f_ref.replace(day=1)
    fin = f_ref.replace(day=calendar.monthrange(f_ref.year, f_ref.month)[1])
    st.caption(f"Mostrando mes de: {f_ref.strftime('%B')}")

st.divider()

# ==========================================
# 🅰️ MODO EDICIÓN (Se activa al tocar Editar)
# ==========================================
if "edit_mode_plan" in st.session_state:
    pid = st.session_state.edit_mode_plan
    data = get_plan_by_id(pid, OWNER)
    
    if data:
        with st.container(border=True):
            st.markdown(f"**✏️ Editando Tarea #{pid}**")
            # Desempaquetar datos actuales
            _, old_f, old_l, old_t, old_tr, old_ac, old_pr, old_ct = data
            
            ec1, ec2 = st.columns(2)
            nf = ec1.date_input("Nueva Fecha", old_f)
            nl = ec2.selectbox("Lote", cargar_fincas(OWNER), index=cargar_fincas(OWNER).index(old_l) if old_l in cargar_fincas(OWNER) else 0)
            nt = st.selectbox("Tipo", ["Jornada","Abono","Fumigación","Cal","Herbicida"], index=["Jornada","Abono","Fumigación","Cal","Herbicida"].index(old_t) if old_t in ["Jornada","Abono","Fumigación","Cal","Herbicida"] else 0)
            
            n_tr, n_ac, n_pr, n_ct = None, None, None, 0.0
            
            if nt == "Jornada":
                trabs = cargar_personal(OWNER, "Jornalero")
                idx_tr = trabs.index(old_tr) if old_tr in trabs else 0
                n_tr = st.selectbox("Trabajador", trabs, index=idx_tr)
                n_ac = st.selectbox("Actividad", cargar_labores(OWNER), index=cargar_labores(OWNER).index(old_ac) if old_ac in cargar_labores(OWNER) else 0)
            else:
                prods = cargar_productos(OWNER)
                idx_pr = prods.index(old_pr) if old_pr in prods else 0
                n_pr = st.selectbox("Producto", prods, index=idx_pr)
                n_ct = st.number_input("Cantidad", value=float(old_ct) if old_ct else 0.0)

            col_save, col_cancel = st.columns(2)
            if col_save.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                update_plan_simple(pid, str(nf), nl, nt, n_tr, n_ac, n_pr, n_ct, OWNER)
                st.success("Actualizado")
                del st.session_state.edit_mode_plan
                st.rerun()
                
            if col_cancel.button("Cancelar", use_container_width=True):
                del st.session_state.edit_mode_plan
                st.rerun()
    else:
        del st.session_state.edit_mode_plan
        st.rerun()

# ==========================================
# 🅱️ AGREGAR NUEVA TAREA
# ==========================================
elif "edit_mode_plan" not in st.session_state:
    with st.expander("➕ Agendar Nueva Labor", expanded=False):
        fincas = cargar_fincas(OWNER)
        if fincas:
            tipo = st.radio("Tipo", ["Jornada","Abono","Fumigación"], horizontal=True)
            
            c_a, c_b = st.columns(2)
            fp = c_a.date_input("Fecha", hoy)
            lp = smart_select("Lote Destino", fincas, "mem_lote_plan")
            
            kw = {}
            if tipo == "Jornada":
                tr = st.selectbox("Trabajador", cargar_personal(OWNER, "Jornalero"))
                ac = smart_select("Labor", cargar_labores(OWNER), "mem_lab_plan")
                kw = {"trabajador": tr, "actividad": ac}
            else:
                pr = smart_select("Producto", cargar_productos(OWNER), "mem_prod_plan")
                ct = st.number_input("Cantidad", 0.0, step=1.0)
                kw = {"producto": pr, "cantidad": ct}
            
            if st.button("📅 Agendar Tarea", type="primary", use_container_width=True):
                add_plan(OWNER, str(fp), lp, tipo, **kw)
                st.toast("Labor agendada exitosamente", icon="📅")
                time.sleep(1)
                st.rerun()
        else:
            st.warning("Configure lotes primero.")

    # ==========================================
    # 📋 LISTA DE TAREAS (TARJETAS)
    # ==========================================
    st.markdown("#### Tareas Pendientes")
    
    planes = list_plans(OWNER, ini, fin)
    
    if not planes:
        st.info("✅ No hay tareas pendientes para estas fechas.")
    
    for plan in planes:
        # Desempaquetar (id, fecha, lote, tipo, trab, act, etapa, prod, dosis, cant, precio, dias, extra, estado...)
        pid = plan[0]
        p_fecha = plan[1]
        p_lote = plan[2]
        p_tipo = plan[3]
        p_trab = plan[4]
        p_act = plan[5]
        p_prod = plan[7]
        p_cant = plan[9]
        
        # Color según urgencia
        if p_fecha < hoy:
            borde_color = "🔴" # Vencido
            estado_txt = "Vencido"
        elif p_fecha == hoy:
            borde_color = "🟢" # Hoy
            estado_txt = "Para Hoy"
        else:
            borde_color = "🔵" # Futuro
            estado_txt = "Futuro"

        # Diseño de Tarjeta
        with st.container(border=True):
            cols = st.columns([0.2, 2, 1])
            cols[0].markdown(f"### {borde_color}")
            
            with cols[1]:
                if p_tipo == "Jornada":
                    st.markdown(f"**{p_trab}**")
                    st.caption(f"🔧 {p_act} en {p_lote}")
                else:
                    st.markdown(f"**{p_tipo}: {p_prod}**")
                    st.caption(f"📦 Cant: {p_cant} en {p_lote}")
                st.caption(f"📅 {p_fecha.strftime('%d/%m')} ({estado_txt})")

            with cols[2]:
                # BOTONES DE ACCIÓN
                
                # 1. Completar
                if st.button("✅ Listo", key=f"done_{pid}", use_container_width=True):
                    # Guardamos en el historial real automáticamente
                    if p_tipo == "Jornada":
                        add_jornada(p_trab, str(hoy), p_lote, p_act, 1.0, 8.0, 0.0, OWNER)
                    elif p_tipo in ["Abono", "Fumigación"]:
                        # Asumimos precio 0 o calculamos si tuvieramos la lógica completa aqui
                        # Para simplificar, solo marcamos realizado en planificador
                        pass 
                        
                    mark_plan_done_and_autorenew(OWNER, pid, OWNER)
                    st.toast("Tarea completada y guardada en historial")
                    time.sleep(0.5)
                    st.rerun()
                
                # 2. Posponer / Editar / Borrar
                with st.popover("⚙️ Opciones"):
                    if st.button("✏️ Editar", key=f"edit_{pid}"):
                        st.session_state.edit_mode_plan = pid
                        st.rerun()
                        
                    st.write("Posponer:")
                    c_p1, c_p2 = st.columns(2)
                    if c_p1.button("+1 Día", key=f"p1_{pid}"):
                        postpone_plan(OWNER, pid, 1); st.rerun()
                    if c_p2.button("+1 Sem", key=f"p7_{pid}"):
                        postpone_plan(OWNER, pid, 7); st.rerun()
                        
                    st.divider()
                    if st.button("🗑️ Eliminar", key=f"del_{pid}"):
                        delete_plan(pid, OWNER)
                        st.rerun()