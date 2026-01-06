import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
from database import calcular_resumen_periodo, crear_cierre_mensual, listar_cierres, get_gastos_por_lote
# Importamos mostrar_encabezado para la navegación
from utils import check_login, mostrar_encabezado
from fpdf import FPDF
import base64

# --- FUNCIÓN GENERADORA DE PDF ---
class PDFReport(FPDF):
    def header(self):
        # Título
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Reporte Financiero Finca', ln=True, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_cierre(res, ini, fin, owner):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 1. Encabezado
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Periodo: {ini} al {fin}", ln=True)
    pdf.cell(0, 10, f"Generado por: {owner}", ln=True)
    pdf.ln(10)
    
    # 2. Tabla de Resumen
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Desglose de Gastos", ln=True)
    
    pdf.set_font("Arial", size=12)
    # Encabezados
    pdf.set_fill_color(230, 240, 230) # Verde muy suave
    pdf.cell(100, 10, "Concepto", 1, 0, 'C', 1)
    pdf.cell(60, 10, "Monto (CRC)", 1, 1, 'C', 1)
    
    # Filas
    pdf.cell(100, 10, "Mano de Obra (Jornales)", 1)
    pdf.cell(60, 10, f"{res['ManoObra']:,.0f}", 1, 1, 'R')
    
    pdf.cell(100, 10, "Insumos (Abonos/Químicos)", 1)
    pdf.cell(60, 10, f"{res['Insumos']:,.0f}", 1, 1, 'R')
    
    pdf.cell(100, 10, "Cosecha (Recolección)", 1)
    pdf.cell(60, 10, f"{res['Cosecha']:,.0f}", 1, 1, 'R')
    
    # Total
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(200, 255, 200) # Verde claro
    pdf.cell(100, 10, "TOTAL GENERAL", 1, 0, 'L', 1)
    pdf.cell(60, 10, f"{res['TotalGeneral']:,.0f}", 1, 1, 'R', 1)
    
    # 3. Firmas
    pdf.ln(30)
    pdf.line(20, pdf.get_y(), 90, pdf.get_y())
    pdf.text(20, pdf.get_y() + 5, "Firma Responsable")
    
    return pdf.output(dest='S').encode('latin-1')

# --- INICIO DE LA APP ---
OWNER = check_login()
# Esto agrega el botón de volver al menú automáticamente
mostrar_encabezado("📊 Reportes Gerenciales")

if 'resumen_actual' not in st.session_state:
    st.session_state.resumen_actual = None

# Navegación interna
t1, t2 = st.tabs(["📅 Cierre de Mes", "📈 Rentabilidad por Lote"])

# ---------------------------------------------------------
# PESTAÑA 1: CIERRE CONTABLE
# ---------------------------------------------------------
with t1:
    with st.container(border=True):
        st.markdown("##### 🧮 Calculadora de Gastos")
        c1, c2 = st.columns(2)
        # Por defecto el mes actual
        hoy = datetime.date.today()
        ini = c1.date_input("Inicio", hoy.replace(day=1))
        fin = c2.date_input("Fin", hoy)
        
        if st.button("Calcular Total", type="primary", use_container_width=True):
            st.session_state.resumen_actual = calcular_resumen_periodo(ini, fin, OWNER)

    # Mostrar Resultados
    if st.session_state.resumen_actual:
        res = st.session_state.resumen_actual
        
        st.divider()
        k1, k2, k3 = st.columns(3)
        k1.metric("Mano Obra", f"₡{res['ManoObra']:,.0f}")
        k2.metric("Insumos", f"₡{res['Insumos']:,.0f}")
        k3.metric("Cosecha", f"₡{res['Cosecha']:,.0f}")
        
        total = res['TotalGeneral']
        st.metric("TOTAL GASTO PERIODO", f"₡{total:,.0f}", delta_color="inverse")
        
        if total > 0:
            st.progress(res['ManoObra']/total, text="Mano de Obra")
            st.progress(res['Insumos']/total, text="Insumos")
            st.progress(res['Cosecha']/total, text="Cosecha")
        
        st.divider()
        col_pdf, col_save = st.columns(2)
        
        with col_pdf:
            pdf_bytes = generar_pdf_cierre(res, ini, fin, OWNER)
            st.download_button(
                label="📄 Descargar PDF",
                data=pdf_bytes,
                file_name=f"Reporte_Finca_{ini}_{fin}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        with col_save:
            if st.button("💾 Guardar en Historial", use_container_width=True):
                crear_cierre_mensual(ini, fin, OWNER, OWNER, 0, 0)
                st.success("Cierre guardado exitosamente")

    # Historial
    st.markdown("#### 📜 Historial de Cierres")
    cierres = listar_cierres(OWNER)
    if cierres:
        df_cierres = pd.DataFrame(cierres, columns=["ID","Ini","Fin","User","Fecha","Nom","Ins","Total"])
        st.dataframe(
            df_cierres[["Ini","Fin","Total"]], 
            hide_index=True,
            use_container_width=True,
            column_config={
                "Total": st.column_config.NumberColumn(format="₡%d")
            }
        )

# ---------------------------------------------------------
# PESTAÑA 2: ANÁLISIS POR LOTE
# ---------------------------------------------------------
with t2:
    st.info("¿Qué lote me está gastando más dinero?")
    gastos = get_gastos_por_lote(OWNER)
    
    if gastos:
        df = pd.DataFrame(gastos)
        
        # Gráficos
        c_chart1, c_chart2 = st.columns(2)
        
        with c_chart1:
            st.markdown("##### 🍰 Distribución")
            fig = px.pie(df, values='TotalGasto', names='Lote', hole=0.4)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            
        with c_chart2:
            st.markdown("##### 🏆 Ranking de Gasto")
            df_sorted = df.sort_values(by="TotalGasto", ascending=True)
            fig_bar = px.bar(df_sorted, x="TotalGasto", y="Lote", orientation='h', text_auto='.2s')
            fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("##### Detalle Exacto")
        st.dataframe(
            df, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "TotalGasto": st.column_config.NumberColumn("Gasto Total", format="₡%d"),
                "Lote": st.column_config.TextColumn("Nombre del Lote")
            }
        )
    else:
        st.warning("No hay suficientes datos de gastos para generar gráficas.")