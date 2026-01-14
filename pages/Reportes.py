import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
from fpdf import FPDF

# Importamos funciones de base de datos
# IMPORTANTE: Asegúrate de tener 'get_resumen_semanal' en database.py (te lo di en la respuesta anterior)
from database import (
    calcular_resumen_periodo, 
    crear_cierre_mensual, 
    listar_cierres, 
    get_gastos_por_lote,
    get_resumen_semanal 
)
from utils import check_login, mostrar_encabezado

# ==========================================
# 1. CLASE GENERADORA DE PDF (PLANILLA Y REPORTE)
# ==========================================
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.set_text_color(46, 125, 50) # Verde Finca
        self.cell(0, 10, 'Finca App - Reporte Oficial', ln=True, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generar_pdf_planilla(datos, inicio, fin):
    """Genera el PDF específico para pagar a los trabajadores"""
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Título
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0)
    pdf.cell(0, 10, "PLANILLA DE PAGO SEMANAL", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Periodo: {inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(10)
    
    # Tabla
    pdf.set_fill_color(0, 230, 118) # Verde neón suave
    pdf.set_text_color(255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(110, 10, "Trabajador", 1, 0, 'C', 1)
    pdf.cell(50, 10, "A Pagar (CRC)", 1, 1, 'C', 1)
    
    pdf.set_text_color(0)
    pdf.set_font("Arial", size=12)
    
    total = 0
    for trabajador, monto in datos:
        monto_float = float(monto) if monto else 0.0
        total += monto_float
        pdf.cell(110, 10, f"  {trabajador}", 1)
        pdf.cell(50, 10, f"{monto_float:,.2f}", 1, 1, 'R')
        
    # Total
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(110, 10, "TOTAL A DISPERSAR:", 0, 0, 'R')
    pdf.set_text_color(0, 150, 0)
    pdf.cell(50, 10, f"{total:,.2f}", 0, 1, 'R')
    
    # Firma
    pdf.ln(25)
    pdf.set_text_color(0)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, "_______________________________", ln=True, align='C')
    pdf.cell(0, 5, "Firma de Autorización", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

def generar_pdf_financiero(res, ini, fin, owner):
    """Genera el PDF general de gastos (tu código anterior mejorado)"""
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_text_color(0)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Cierre Financiero: {ini} al {fin}", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Generado por: {owner}", ln=True)
    pdf.ln(5)
    
    # Tabla
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "Concepto", 1)
    pdf.cell(60, 10, "Monto", 1, 1)
    
    pdf.set_font("Arial", size=12)
    items = [
        ("Mano de Obra", res['ManoObra']),
        ("Insumos", res['Insumos']),
        ("Cosecha", res['Cosecha'])
    ]
    
    for concepto, valor in items:
        pdf.cell(100, 10, concepto, 1)
        pdf.cell(60, 10, f"{valor:,.2f}", 1, 1, 'R')
        
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "TOTAL GENERAL", 1, 0, 'L', 1)
    pdf.cell(60, 10, f"{res['TotalGeneral']:,.2f}", 1, 1, 'R', 1)
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 2. INICIO DE LA APP
# ==========================================
OWNER = check_login()
mostrar_encabezado("📊 Centro de Reportes")

# Tabs para organizar la información
tab_planilla, tab_cierre, tab_lotes = st.tabs(["💰 Planilla Pago", "📅 Cierre Mes", "📈 Análisis Lotes"])

# ---------------------------------------------------------
# PESTAÑA 1: PLANILLA DE PAGO (¡LO QUE NECESITAS YA!)
# ---------------------------------------------------------
with tab_planilla:
    st.markdown("##### 💵 Cálculo de Pago Semanal")
    st.caption("Selecciona la semana para ver cuánto debes pagar a cada peón.")
    
    c1, c2 = st.columns(2)
    hoy = datetime.date.today()
    # Calcular lunes pasado automáticamente
    lunes_pasado = hoy - datetime.timedelta(days=hoy.weekday())
    
    ini_p = c1.date_input("Desde (Lunes)", lunes_pasado, key="d_ini")
    fin_p = c2.date_input("Hasta (Domingo)", hoy, key="d_fin")
    
    if st.button("🔍 Calcular Planilla", use_container_width=True, type="primary"):
        datos_planilla = get_resumen_semanal(OWNER, ini_p, fin_p)
        
        if datos_planilla:
            st.markdown("---")
            # Convertir a DataFrame para métricas
            df_p = pd.DataFrame(datos_planilla, columns=["Trabajador", "Total"])
            total_neto = df_p["Total"].sum()
            
            # Gran Métrica
            st.metric("Total a Sacar del Banco", f"₡ {total_neto:,.0f}")
            
            # Tabla Visual
            st.dataframe(
                df_p, 
                use_container_width=True, 
                hide_index=True,
                column_config={"Total": st.column_config.NumberColumn(format="₡ %.2f")}
            )
            
            # Botón PDF
            pdf_bytes = generar_pdf_planilla(datos_planilla, ini_p, fin_p)
            st.download_button(
                label="🖨️ IMPRIMIR PLANILLA PDF",
                data=pdf_bytes,
                file_name=f"Planilla_{ini_p}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="secondary"
            )
        else:
            st.warning("No hay jornadas registradas en esas fechas.")

# ---------------------------------------------------------
# PESTAÑA 2: CIERRE FINANCIERO (TU CÓDIGO VIEJO)
# ---------------------------------------------------------
with tab_cierre:
    st.markdown("##### 📉 Balance General")
    c1, c2 = st.columns(2)
    ini_c = c1.date_input("Inicio Mes", hoy.replace(day=1), key="c_ini")
    fin_c = c2.date_input("Fin Mes", hoy, key="c_fin")
    
    if st.button("Calcular Gastos Generales", use_container_width=True):
        res = calcular_resumen_periodo(ini_c, fin_c, OWNER)
        st.session_state.resumen_cache = res # Guardar en memoria
    
    if 'resumen_cache' in st.session_state:
        res = st.session_state.resumen_cache
        st.divider()
        k1, k2, k3 = st.columns(3)
        k1.metric("Mano Obra", f"₡{res['ManoObra']:,.0f}")
        k2.metric("Insumos", f"₡{res['Insumos']:,.0f}")
        k3.metric("Cosecha", f"₡{res['Cosecha']:,.0f}")
        
        st.metric("GASTO TOTAL", f"₡{res['TotalGeneral']:,.0f}", delta_color="inverse")
        
        # Botón PDF Financiero
        pdf_fin = generar_pdf_financiero(res, ini_c, fin_c, OWNER)
        st.download_button("📄 Descargar Reporte Gerencial", pdf_fin, f"Financiero_{ini_c}.pdf", "application/pdf", use_container_width=True)

# ---------------------------------------------------------
# PESTAÑA 3: ANÁLISIS POR LOTE (GRÁFICOS)
# ---------------------------------------------------------
with tab_lotes:
    st.markdown("##### 🚜 Rentabilidad por Lote")
    gastos = get_gastos_por_lote(OWNER)
    
    if gastos:
        df_g = pd.DataFrame(gastos)
        c_chart1, c_chart2 = st.columns(2)
        
        with c_chart1:
            fig = px.pie(df_g, values='TotalGasto', names='Lote', hole=0.4, title="Gasto por Lote")
            fig.update_layout(margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            
        with c_chart2:
            st.dataframe(df_g, hide_index=True, use_container_width=True, column_config={"TotalGasto": st.column_config.NumberColumn(format="₡%d")})
    else:
        st.info("Aún no hay suficientes datos para gráficas.")
