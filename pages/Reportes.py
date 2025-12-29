import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
from database import calcular_resumen_periodo, crear_cierre_mensual, listar_cierres, get_gastos_por_lote
from utils import check_login
from fpdf import FPDF
import base64

# --- FUNCIÓN GENERADORA DE PDF ---
class PDFReport(FPDF):
    def header(self):
        # Título
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Reporte de Cierre Financiero', ln=True, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_cierre(res, ini, fin, owner):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 1. Encabezado de información
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Periodo: {ini} al {fin}", ln=True)
    pdf.cell(0, 10, f"Generado por: {owner}", ln=True)
    pdf.ln(10)
    
    # 2. Tabla de Totales
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Resumen de Gastos", ln=True)
    
    pdf.set_font("Arial", size=12)
    # Encabezados de tabla
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(100, 10, "Concepto", 1, 0, 'C', 1)
    pdf.cell(60, 10, "Monto (CRC)", 1, 1, 'C', 1)
    
    # Filas
    pdf.cell(100, 10, "Mano de Obra", 1)
    pdf.cell(60, 10, f"{res['ManoObra']:,.0f}", 1, 1, 'R')
    
    pdf.cell(100, 10, "Insumos (Abono/Fumiga)", 1)
    pdf.cell(60, 10, f"{res['Insumos']:,.0f}", 1, 1, 'R')
    
    pdf.cell(100, 10, "Cosecha (Recolección)", 1)
    pdf.cell(60, 10, f"{res['Cosecha']:,.0f}", 1, 1, 'R')
    
    # Total
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "TOTAL GENERAL", 1)
    pdf.cell(60, 10, f"{res['TotalGeneral']:,.0f}", 1, 1, 'R')
    
    # 3. Espacio para firmas
    pdf.ln(30)
    pdf.line(20, pdf.get_y(), 90, pdf.get_y())
    pdf.text(20, pdf.get_y() + 5, "Firma Responsable")
    
    # Retornar el PDF como string binario
    return pdf.output(dest='S').encode('latin-1')

# --- INICIO DE LA APP ---
OWNER = check_login()
st.title("📊 Reportes Gerenciales")

if 'resumen_actual' not in st.session_state:
    st.session_state.resumen_actual = None

t1, t2 = st.tabs(["📅 Cierre Periodo", "📈 Rentabilidad"])

with t1:
    st.caption("Calculadora de Cierre (Caja)")
    c1, c2 = st.columns(2)
    ini = c1.date_input("Inicio", datetime.date.today().replace(day=1))
    fin = c2.date_input("Fin", datetime.date.today())
    
    # Botón Calcular
    if st.button("Calcular Total", type="primary"):
        # Guardamos en session_state para que no se pierda al darle click a descargar
        st.session_state.resumen_actual = calcular_resumen_periodo(ini, fin, OWNER)
    
    # Mostrar resultados si existen en memoria
    if st.session_state.resumen_actual:
        res = st.session_state.resumen_actual
        
        st.divider()
        k1, k2, k3 = st.columns(3)
        k1.metric("Mano Obra", f"₡{res['ManoObra']:,.0f}")
        k2.metric("Insumos", f"₡{res['Insumos']:,.0f}")
        k3.metric("Cosecha", f"₡{res['Cosecha']:,.0f}")
        
        # MEJORA BI: Mostrar % de impacto
        total = res['TotalGeneral']
        if total > 0:
            st.caption(f"Distribución: MO {(res['ManoObra']/total):.1%} | Ins {(res['Insumos']/total):.1%} | Cos {(res['Cosecha']/total):.1%}")
        
        st.metric("TOTAL GASTO", f"₡{total:,.0f}", delta_color="inverse")
        
        st.divider()
        col_pdf, col_save = st.columns(2)
        
        # --- BOTÓN DE DESCARGA PDF ---
        with col_pdf:
            pdf_bytes = generar_pdf_cierre(res, ini, fin, OWNER)
            st.download_button(
                label="📄 Descargar Reporte PDF",
                data=pdf_bytes,
                file_name=f"Cierre_{ini}_{fin}.pdf",
                mime="application/pdf"
            )

        with col_save:
            if st.button("💾 Guardar Historial"):
                crear_cierre_mensual(ini, fin, OWNER, OWNER, 0, 0) # Ajusta si necesitas pasar otros params
                st.success("Cierre Guardado en Base de Datos")

    st.subheader("Historial de Cierres")
    cierres = listar_cierres(OWNER)
    if cierres:
        # MEJORA VISUAL: Tabla con formato
        df_cierres = pd.DataFrame(cierres, columns=["ID","Ini","Fin","User","Fecha","Nom","Ins","Total"])
        st.dataframe(
            df_cierres[["Ini","Fin","Total"]], 
            hide_index=True,
            use_container_width=True
        )

with t2:
    gastos = get_gastos_por_lote(OWNER)
    if gastos:
        df = pd.DataFrame(gastos)
        
        # MEJORA BI: Gráfico de Barras es mejor para comparar montos que el Pie Chart
        c_chart1, c_chart2 = st.columns(2)
        
        with c_chart1:
            st.markdown("##### Distribución Visual")
            fig = px.pie(df, values='TotalGasto', names='Lote', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
        with c_chart2:
            st.markdown("##### Ranking de Gastos")
            # Ordenar de mayor a menor gasto para ver los "puntos calientes"
            df_sorted = df.sort_values(by="TotalGasto", ascending=True)
            fig_bar = px.bar(df_sorted, x="TotalGasto", y="Lote", orientation='h', text_auto='.2s')
            st.plotly_chart(fig_bar, use_container_width=True)

        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Sin datos de gastos registrados aún.")