import streamlit as st
import pandas as pd
import datetime
import time
from io import BytesIO

# Librerías para PDF Profesional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from database import (
    add_recoleccion_batch, get_reporte_cosecha_detallado, add_vale, get_saldo_global
)
from utils import check_login, cargar_fincas, cargar_personal, smart_select

# --- FUNCIÓN PDF PROFESIONAL ---
def generar_pdf_planilla(df_resumen, f1, f2):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # 1. Título
    elements.append(Paragraph(f"Planilla de Recolección de Café", styles['Title']))
    elements.append(Paragraph(f"Periodo: {f1} al {f2}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # 2. Preparar Datos para la Tabla
    # Encabezados
    data = [['Recolector', 'Cajuelas', 'Ganado (₡)', 'Rebajos (₡)', 'NETO A PAGAR (₡)']]
    
    total_caj = 0
    total_pagar = 0

    # Filas
    for _, row in df_resumen.iterrows():
        neto = row["Total ₡"] - row["Abono Deuda"]
        data.append([
            row['Recolector'],
            f"{row['Cajuelas']:.2f}",
            f"{row['Total ₡']:,.0f}",
            f"{row['Abono Deuda']:,.0f}",
            f"{neto:,.0f}"  # El Neto calculado
        ])
        total_caj += row['Cajuelas']
        total_pagar += neto

    # Fila de Totales
    data.append(['TOTALES', f"{total_caj:.2f}", '', '', f"₡{total_pagar:,.0f}"])

    # 3. Estilo de Tabla
    t = Table(data, colWidths=[180, 70, 80, 80, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.brown),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'), # Números a la derecha
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey), # Fila de totales gris
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(t)
    doc.build(elements)
    return buffer.getvalue()

# --- INICIO APP ---
OWNER = check_login()
st.title("☕ Gestión de Cosecha")

t_reg, t_plan = st.tabs(["📝 Medida Diaria", "💰 Planilla & Vales"])

# -----------------------------------------------------------
# PESTAÑA 1: REGISTRO DE CAJUELAS
# -----------------------------------------------------------
with t_reg:
    fincas = cargar_fincas(OWNER)
    recolectores = cargar_personal(OWNER, "Recolector")
    
    if fincas and recolectores:
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            f_hoy = c1.date_input("Fecha", datetime.date.today())
            l_hoy = smart_select("Lote", fincas, "mem_lote_cafe") 
            p_hoy = c3.number_input("Precio Cajuela ₡", value=1300.0, step=50.0)

        # Inicializar DataFrame en Session State
        if "df_recoleccion" not in st.session_state:
            st.session_state.df_recoleccion = pd.DataFrame({
                "Recolector": recolectores,
                "Cajuelas": [0.0] * len(recolectores)
            })

        st.caption("Ingrese las cajuelas recolectadas por persona:")
        
        # Editor de Datos
        edited_df = st.data_editor(
            st.session_state.df_recoleccion,
            column_config={
                "Recolector": st.column_config.TextColumn("Nombre", disabled=True),
                "Cajuelas": st.column_config.NumberColumn("Cajuelas", min_value=0.0, step=0.25)
            },
            hide_index=True, 
            use_container_width=True,
            height=400 # Altura fija para scroll cómodo
        )

        # MÉTRICAS EN TIEMPO REAL (Post-Edición)
        # Calculamos totales visuales para que el capataz verifique
        total_cajuelas_dia = edited_df["Cajuelas"].sum()
        total_dinero_dia = total_cajuelas_dia * p_hoy
        
        m1, m2 = st.columns(2)
        m1.metric("Total Cajuelas (Hoy)", f"{total_cajuelas_dia:.2f}")
        m2.metric("Costo Planilla (Hoy)", f"₡{total_dinero_dia:,.0f}")

        if st.button("💾 Procesar Cierre del Día", type="primary", use_container_width=True):
            datos = []
            for _, row in edited_df.iterrows():
                if row["Cajuelas"] > 0:
                    datos.append((str(f_hoy), row["Recolector"], l_hoy, float(row["Cajuelas"]), float(p_hoy), OWNER))
            
            if datos:
                ok = add_recoleccion_batch(datos)
                if ok:
                    st.success(f"✅ Se guardaron {len(datos)} registros correctamente.")
                    st.balloons()
                    # Limpiar datos para el día siguiente
                    st.session_state.df_recoleccion["Cajuelas"] = 0.0
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Error de conexión. Intente de nuevo.")
            else:
                st.warning("⚠️ No hay cajuelas registradas (todo está en 0).")
    else:
        st.warning("⚠️ Configure Fincas y Recolectores en Ajustes.")

# -----------------------------------------------------------
# PESTAÑA 2: PLANILLA Y PAGOS (MEJORADA)
# -----------------------------------------------------------
with t_plan:
    st.markdown("#### 💵 Nómina Semanal")

    # 1. Registro Rápido de Vales
    with st.expander("💸 Registrar Vale / Adelanto Rápido"):
        c_v1, c_v2, c_v3 = st.columns([2,2,1])
        v_trab = c_v1.selectbox("Trabajador", recolectores if recolectores else [])
        v_monto = c_v2.number_input("Monto Vale ₡", min_value=1000.0, step=1000.0)
        if c_v3.button("Guardar Vale"):
            add_vale(datetime.date.today(), v_trab, v_monto, "Adelanto Cosecha", OWNER)
            st.success(f"Vale de ₡{v_monto} guardado.")

    st.divider()

    # 2. Generador de Planilla
    c1, c2 = st.columns(2)
    hoy = datetime.date.today()
    f1 = c1.date_input("Inicio Periodo", hoy - datetime.timedelta(days=hoy.weekday()))
    f2 = c2.date_input("Fin Periodo", hoy)

    raw = get_reporte_cosecha_detallado(f1, f2, OWNER)
    saldo_global = get_saldo_global(OWNER)

    if raw:
        df = pd.DataFrame(raw, columns=["Recolector", "Lote", "Cajuelas", "Total ₡"])
        df["Cajuelas"] = pd.to_numeric(df["Cajuelas"])
        df["Total ₡"] = pd.to_numeric(df["Total ₡"])

        # Agrupación por Recolector
        resumen = df.groupby("Recolector")[["Cajuelas", "Total ₡"]].sum().reset_index()
        
        # Datos Financieros
        resumen["Fanegas"] = resumen["Cajuelas"] / 20.0
        resumen["Deuda Total"] = resumen["Recolector"].map(saldo_global).fillna(0.0)
        
        # LÓGICA SEGURA: Empezamos abono en 0 para que el usuario decida cuánto rebajar
        resumen["Abono Deuda"] = 0.0 

        st.info("👇 Ingrese en la columna 'Abono Deuda' cuánto desea rebajar esta semana.")
        
        edited_planilla = st.data_editor(
            resumen[["Recolector", "Cajuelas", "Total ₡", "Deuda Total", "Abono Deuda"]],
            column_config={
                "Total ₡": st.column_config.NumberColumn("Bruto Ganado", format="₡%d", disabled=True),
                "Deuda Total": st.column_config.NumberColumn("Deuda Actual", format="₡%d", disabled=True),
                "Abono Deuda": st.column_config.NumberColumn("Rebajar Hoy", format="₡%d", min_value=0)
            },
            hide_index=True, 
            use_container_width=True
        )

        # CÁLCULOS FINALES EN TIEMPO REAL
        neto_col = edited_planilla["Total ₡"] - edited_planilla["Abono Deuda"]
        total_pagar_efectivo = neto_col.sum()

        # Métricas de pago
        col_res1, col_res2 = st.columns(2)
        col_res1.metric("Total Cajuelas Periodo", f"{edited_planilla['Cajuelas'].sum():.2f}")
        col_res2.metric("💰 TOTAL EFECTIVO A PAGAR", f"₡{total_pagar_efectivo:,.0f}", delta_color="inverse")

        # Advertencia de Salarios Negativos
        if (neto_col < 0).any():
            st.error("⚠️ ERROR: Estás intentando rebajar más dinero del que el recolector ganó. Corrige la columna 'Rebajar Hoy'.")
        else:
            c_btn1, c_btn2 = st.columns(2)
            
            # Botón PDF
            with c_btn1:
                pdf_data = generar_pdf_planilla(edited_planilla, f1, f2)
                st.download_button(
                    "📄 Descargar Planilla PDF", 
                    data=pdf_data, 
                    file_name=f"Planilla_Cafe_{f1}_{f2}.pdf", 
                    mime="application/pdf",
                    use_container_width=True
                )

            # Botón Guardar (Rebajos)
            with c_btn2:
                if st.button("✅ Confirmar Pagos y Rebajos", type="primary", use_container_width=True):
                    count = 0
                    for _, row in edited_planilla.iterrows():
                        if row["Abono Deuda"] > 0:
                            # Registramos el abono como un vale negativo
                            add_vale(hoy, row["Recolector"], -float(row["Abono Deuda"]), f"Abono Planilla {f1}", OWNER)
                            count += 1
                    st.success(f"Planilla cerrada. {count} abonos aplicados a deudas.")
                    time.sleep(2)
                    st.rerun()

    else:
        st.info("No hay registros de cosecha para las fechas seleccionadas.")