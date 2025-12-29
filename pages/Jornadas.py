import streamlit as st
import datetime
import pandas as pd
from database import add_jornada, get_jornadas_between, get_tarifas, add_vale, get_saldo_global
from utils import check_login, cargar_fincas, cargar_personal, cargar_labores, smart_select

OWNER = check_login()
st.title("🧑‍🌾 Gestión de Jornadas")

t_reg, t_rep = st.tabs(["🚀 Registro Masivo", "💰 Planilla y Pagos"])

# ---------------------------------------------------------
# PESTAÑA 1: REGISTRO MASIVO (CUADRILLAS)
# ---------------------------------------------------------
with t_reg:
    st.caption("Seleccione varios peones para registrar la misma labor simultáneamente.")
    fincas = cargar_fincas(OWNER)
    jornaleros = cargar_personal(OWNER, "Jornalero")
    labores = cargar_labores(OWNER)
    
    if fincas and jornaleros and labores:
        # Memorias inteligentes
        lote = smart_select("Lote", fincas, "mem_lote_jor")
        act = smart_select("Actividad", labores, "mem_act_jor")
        
        # Fila de configuración de tiempo
        c1, c2, c3 = st.columns(3)
        fecha = c1.date_input("Fecha", datetime.date.today())
        dias = c2.number_input("Días", 1.0, step=0.5)
        extras = c3.number_input("Horas Extras", 0.0, step=1.0)

        st.divider()
        
        # MEJORA 1: Multiselect para Cuadrillas
        # Esto permite elegir 5 peones y guardar de un solo golpe
        lista_peones = st.multiselect("Seleccione Cuadrilla (Personal)", jornaleros)

        if st.button("💾 Guardar Cuadrilla", type="primary", use_container_width=True):
            if lista_peones:
                exitos = 0
                errores = 0
                barra = st.progress(0)
                
                for i, trab in enumerate(lista_peones):
                    try:
                        dias_val = float(dias)
                        # Asumimos jornada de 8 horas para cálculo base
                        horas_normales = dias_val * 8.0 
                        add_jornada(trab, str(fecha), lote, act, dias_val, horas_normales, float(extras), OWNER)
                        exitos += 1
                    except Exception:
                        errores += 1
                    # Actualizar barra de progreso
                    barra.progress((i + 1) / len(lista_peones))
                
                if errores == 0:
                    st.success(f"✅ Se registraron {exitos} jornadas correctamente.")
                    st.balloons()
                else:
                    st.warning(f"⚠️ Guardados: {exitos}. Errores: {errores}.")
            else:
                st.error("⚠️ Debe seleccionar al menos un jornalero.")
    else:
        st.warning("Configure Personal, Fincas y Labores en Ajustes.")

# ---------------------------------------------------------
# PESTAÑA 2: PLANILLA INTELIGENTE
# ---------------------------------------------------------
with t_rep:
    st.subheader("Cálculo de Pago Semanal")
    
    # Filtros de fecha
    c_f1, c_f2 = st.columns(2)
    hoy = datetime.date.today()
    # Truco BI: Por defecto poner el lunes pasado y el domingo
    inicio_sem = hoy - datetime.timedelta(days=hoy.weekday())
    ini = c_f1.date_input("Desde", inicio_sem)
    fin = c_f2.date_input("Hasta", hoy)
    
    # Obtener datos
    raw = get_jornadas_between(ini, fin, OWNER)
    td, th = get_tarifas(OWNER) # Tarifa Día, Tarifa Hora Extra
    saldo_global = get_saldo_global(OWNER)
    
    if raw:
        # Convertir a DataFrame
        df = pd.DataFrame(raw, columns=["ID","Trab","Fecha","Lote","Act","Días","HN","Ext"])
        df["Días"] = pd.to_numeric(df["Días"])
        df["Ext"] = pd.to_numeric(df["Ext"])
        
        # Agrupar por Trabajador
        res = df.groupby("Trab")[["Días","Ext"]].sum().reset_index()
        
        # Cálculos Financieros
        res["Bruto"] = (res["Días"] * td) + (res["Ext"] * th)
        res["Deuda Total"] = res["Trab"].map(saldo_global).fillna(0.0)
        
        # LÓGICA DE SEGURIDAD:
        # Por defecto NO sugerimos rebajar toda la deuda si es mayor al sueldo.
        # Creamos la columna 'Abono Deuda' iniciada en 0 para que el usuario decida.
        res["Abono Deuda"] = 0.0 
        
        # Reordenar columnas para el editor
        res_final = res[["Trab", "Días", "Ext", "Bruto", "Deuda Total", "Abono Deuda"]]

        st.info(f"Tarifas usadas -> Día: ₡{td:,.0f} | Extra: ₡{th:,.0f}")

        # EDITOR DE DATOS INTERACTIVO
        edited_df = st.data_editor(
            res_final, 
            hide_index=True,
            column_config={
                "Bruto": st.column_config.NumberColumn(format="₡%d", disabled=True),
                "Deuda Total": st.column_config.NumberColumn(format="₡%d", disabled=True),
                "Abono Deuda": st.column_config.NumberColumn(format="₡%d", min_value=0, help="Escriba cuánto rebajar esta semana"),
            },
            use_container_width=True
        )

        # CÁLCULO EN TIEMPO REAL (Post-Edición)
        # Calculamos el Neto aquí basado en lo que el usuario editó en la tabla
        neto_pagar = edited_df["Bruto"] - edited_df["Abono Deuda"]
        total_planilla = neto_pagar.sum()
        
        # Métricas de Resumen
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Bruto", f"₡{edited_df['Bruto'].sum():,.0f}")
        m2.metric("Total Rebajos", f"₡{edited_df['Abono Deuda'].sum():,.0f}")
        m3.metric("💰 TOTAL A PAGAR (EFECTIVO)", f"₡{total_planilla:,.0f}", delta_color="inverse")
        
        # Validación de Negativos
        if (neto_pagar < 0).any():
            st.error("⚠️ ALERTA: Hay trabajadores con SALARIO NEGATIVO. Ajuste el 'Abono Deuda' para que sea menor al Bruto.")
        else:
            st.divider()
            if st.button("✅ Confirmar y Aplicar Rebajos"):
                count = 0
                for index, r in edited_df.iterrows():
                    monto_rebajo = float(r["Abono Deuda"])
                    if monto_rebajo > 0:
                        # Registramos el vale negativo (pago de deuda)
                        add_vale(hoy, r["Trab"], -monto_rebajo, f"Rebajo Planilla {ini}-{fin}", OWNER)
                        count += 1
                
                st.success(f"Planilla procesada. Se aplicaron {count} rebajos a deudas.")
                st.balloons()
                # Opcional: st.rerun() para limpiar
    else:
        st.info("No hay jornadas registradas en este rango de fechas.")