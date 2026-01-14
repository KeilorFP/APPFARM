import streamlit as st
import datetime
import time
import pandas as pd
from database import add_jornada, get_jornadas_between, get_tarifas, add_vale, get_saldo_global
# Importamos la nueva función de encabezado
from utils import check_login, cargar_fincas, cargar_personal, cargar_labores, smart_select, mostrar_encabezado

# 1. VERIFICACIÓN Y ENCABEZADO
OWNER = check_login()
# Esto agrega el botón de volver al menú automáticamente
mostrar_encabezado("🧑‍🌾 Gestión de Jornadas")

# 2. NAVEGACIÓN INTERNA
opcion = st.pills("Seleccione opción:", ["🚀 Registro Masivo", "💰 Planilla y Pagos"], default="🚀 Registro Masivo")

st.divider()

# ---------------------------------------------------------
# MÓDULO 1: REGISTRO MASIVO (CUADRILLAS)
# ---------------------------------------------------------
if opcion == "🚀 Registro Masivo":
    st.caption("Seleccione varios peones para registrar la misma labor simultáneamente.")
    
    fincas = cargar_fincas(OWNER)
    jornaleros = cargar_personal(OWNER, "Jornalero")
    labores = cargar_labores(OWNER)
    
    if not fincas: st.warning("Cree lotes en Ajustes."); st.stop()
    if not jornaleros: st.warning("Cree personal en Ajustes."); st.stop()
    if not labores: st.warning("Cree labores en Ajustes."); st.stop()

    with st.container(border=True):
        # Fila 1: Configuración de la Labor
        c1, c2 = st.columns(2)
        # Memorias inteligentes para recordar última selección
        lote = smart_select("Lote / Sector", fincas, "mem_lote_jor")
        act = smart_select("Labor Realizada", labores, "mem_act_jor")
        
        # Fila 2: Tiempos
        st.markdown("**Tiempo Trabajado**")
        t1, t2, t3 = st.columns(3)
        fecha = t1.date_input("Fecha", datetime.date.today())
        dias = t2.number_input("Días", 1.0, step=0.5)
        extras = t3.number_input("Horas Extras", 0.0, step=1.0)

        st.divider()
        
        # Fila 3: Selección de Personal (Multiselect)
        st.markdown("##### 👥 Seleccione la Cuadrilla")
        lista_peones = st.multiselect("Personal", jornaleros, placeholder="Toque para seleccionar...")

        # Botón Guardar Gigante
        if st.button(f"💾 Guardar Jornada para {len(lista_peones)} personas", type="primary", use_container_width=True):
            if lista_peones:
                exitos = 0
                errores = 0
                barra = st.progress(0)
                
                for i, trab in enumerate(lista_peones):
                    try:
                        dias_val = float(dias)
                        # Asumimos jornada de 8 horas para cálculo base interno
                        horas_normales = dias_val * 8.0 
                        add_jornada(trab, str(fecha), lote, act, dias_val, horas_normales, float(extras), OWNER)
                        exitos += 1
                    except Exception:
                        errores += 1
                    # Actualizar barra
                    barra.progress((i + 1) / len(lista_peones))
                
                if errores == 0:
                    st.success(f"✅ ¡Éxito! {exitos} jornadas registradas.")
                    st.balloons()
                    time.sleep(1)
                    # No hacemos rerun para permitir seguir registrando otra cuadrilla rápido
                else:
                    st.warning(f"⚠️ Guardados: {exitos}. Fallidos: {errores}.")
            else:
                st.error("⚠️ Debe seleccionar al menos una persona.")

# ---------------------------------------------------------
# MÓDULO 2: PLANILLA INTELIGENTE
# ---------------------------------------------------------
elif opcion == "💰 Planilla y Pagos":
    
    with st.expander("📅 Rango de Fechas", expanded=True):
        c_f1, c_f2 = st.columns(2)
        hoy = datetime.date.today()
        # Truco: Lunes pasado a Hoy
        inicio_sem = hoy - datetime.timedelta(days=hoy.weekday())
        ini = c_f1.date_input("Desde", inicio_sem)
        fin = c_f2.date_input("Hasta", hoy)
    
    # Obtener datos
    raw = get_jornadas_between(ini, fin, OWNER)
    td, th = get_tarifas(OWNER) # Tarifa Día, Tarifa Hora Extra
    saldo_global = get_saldo_global(OWNER)
    
    if raw:
        # Procesar Datos
        df = pd.DataFrame(raw, columns=["ID","Trab","Fecha","Lote","Act","Días","HN","Ext"])
        df["Días"] = pd.to_numeric(df["Días"])
        df["Ext"] = pd.to_numeric(df["Ext"])
        
        # Agrupar por Trabajador
        res = df.groupby("Trab")[["Días","Ext"]].sum().reset_index()
        
        # Cálculos Financieros
        res["Bruto"] = (res["Días"] * td) + (res["Ext"] * th)
        res["Deuda Total"] = res["Trab"].map(saldo_global).fillna(0.0)
        res["Abono Deuda"] = 0.0 # Editable por el usuario
        
        # Tabla Editable
        st.info(f"Tarifas -> Día: ₡{td:,.0f} | Extra: ₡{th:,.0f}")
        
        edited_df = st.data_editor(
            res[["Trab", "Días", "Ext", "Bruto", "Deuda Total", "Abono Deuda"]], 
            hide_index=True,
            column_config={
                "Trab": st.column_config.TextColumn("Nombre", disabled=True),
                "Bruto": st.column_config.NumberColumn(format="₡%d", disabled=True),
                "Deuda Total": st.column_config.NumberColumn(format="₡%d", disabled=True),
                "Abono Deuda": st.column_config.NumberColumn("Rebajar", format="₡%d", min_value=0),
            },
            use_container_width=True
        )

        # Totales en Tiempo Real
        neto_pagar = edited_df["Bruto"] - edited_df["Abono Deuda"]
        total_planilla = neto_pagar.sum()
        
        st.metric("💰 TOTAL EFECTIVO A PAGAR", f"₡{total_planilla:,.0f}")
        
        # Validación de Negativos
        if (neto_pagar < 0).any():
            st.error("⚠️ ALERTA: Hay trabajadores con SALARIO NEGATIVO. Ajuste el 'Rebajar'.")
        else:
            if st.button("✅ Pagar Planilla y Aplicar Rebajos", type="primary", use_container_width=True):
                count = 0
                for index, r in edited_df.iterrows():
                    monto_rebajo = float(r["Abono Deuda"])
                    if monto_rebajo > 0:
                        add_vale(hoy, r["Trab"], -monto_rebajo, f"Rebajo {ini}", OWNER)
                        count += 1
                st.success(f"Planilla procesada. {count} rebajos aplicados.")
                time.sleep(1.5)
                st.rerun()
    else:
        st.info("No hay jornadas registradas en estas fechas.")
