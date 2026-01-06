import streamlit as st
import pandas as pd
import datetime
import time
from io import BytesIO

# Librerías para PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Base de datos
from database import (
    add_recoleccion_batch, get_reporte_cosecha_detallado, add_vale, get_saldo_global
)
# Utils (Con la nueva navegación)
from utils import check_login, cargar_fincas, cargar_personal, mostrar_encabezado

# --- 1. FUNCIÓN PDF (Lógica de Reportes) ---
def generar_pdf_planilla(df_resumen, f1, f2):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Planilla de Recolección", styles['Title']))
    elements.append(Paragraph(f"Periodo: {f1} al {f2}", styles['Normal']))
    elements.append(Spacer(1, 12))

    data = [['Recolector', 'Caj', 'Bruto ₡', 'Rebajo ₡', 'NETO ₡']]
    total_caj = 0
    total_pagar = 0

    for _, row in df_resumen.iterrows():
        neto = row["Total ₡"] - row["Abono Deuda"]
        data.append([
            row['Recolector'][:20], 
            f"{row['Cajuelas']:.2f}", 
            f"{row['Total ₡']:,.0f}", 
            f"{row['Abono Deuda']:,.0f}", 
            f"{neto:,.0f}"
        ])
        total_caj += row['Cajuelas']
        total_pagar += neto

    data.append(['TOTALES', f"{total_caj:.2f}", '', '', f"₡{total_pagar:,.0f}"])

    t = Table(data, colWidths=[150, 60, 80, 80, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(t)
    doc.build(elements)
    return buffer.getvalue()

# --- 2. INICIO DE PÁGINA ---
OWNER = check_login()

# AQUÍ ESTÁ EL CAMBIO IMPORTANTE: Botón de volver al menú
mostrar_encabezado("☕ Control Cosecha") 

# Inicializar "Carrito" de recolección
if "temp_harvest" not in st.session_state:
    st.session_state.temp_harvest = []

# Tabs Superiores
# Usamos radio horizontal o pills para navegar entre pestañas
modo = st.pills("Seleccione Modo:", ["⚡ Registro Rápido", "💵 Planilla Semanal"], default="⚡ Registro Rápido")

st.divider()

# =======================================================
# MODO 1: REGISTRO RÁPIDO (BOTONES SIN TECLADO)
# =======================================================
if modo == "⚡ Registro Rápido":
    
    # A. Configuración Global (Día, Precio, Lote)
    with st.container(border=True):
        c1, c2 = st.columns([1.5, 1])
        f_hoy = c1.date_input("Fecha", datetime.date.today())
        p_hoy = c2.number_input("Precio ₡", value=1300, step=50)
        
        lista_fincas = cargar_fincas(OWNER)
        l_hoy = st.selectbox("Finca / Lote", lista_fincas if lista_fincas else ["General"])

    # B. Selección de Trabajador
    lista_recolectores = cargar_personal(OWNER, "Recolector")
    if not lista_recolectores:
        st.warning("⚠️ No hay recolectores registrados en Ajustes.")
        st.stop()
        
    st.markdown("##### 👤 Seleccione Recolector:")
    trabajador_actual = st.selectbox("Trabajador", lista_recolectores, label_visibility="collapsed")

    # C. BOTONERA DE VELOCIDAD (Aquí ocurre la magia)
    st.markdown("##### 📦 ¿Cuántas cajuelas trajo?")
    
    # CSS para hacer estos botones específicos muy grandes
    st.markdown("""
        <style>
        div.stButton.cant-btn > button {
            height: 3.5rem !important;
            font-size: 1.3rem !important;
            border: 1px solid #2E7D32 !important;
            color: #2E7D32 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    def agregar_rapido(cantidad):
        """Agrega a la lista temporal sin recargar toda la UI"""
        st.session_state.temp_harvest.insert(0, {
            "Nombre": trabajador_actual,
            "Cajuelas": cantidad,
            "Total": cantidad * p_hoy,
            "Hora": datetime.datetime.now().strftime("%H:%M")
        })
        st.toast(f"✅ {trabajador_actual}: +{cantidad} cajuelas", icon="☕")

    # Fila 1 de Botones
    cb1, cb2, cb3, cb4 = st.columns(4)
    with cb1: 
        if st.button("0.25", use_container_width=True): agregar_rapido(0.25)
    with cb2: 
        if st.button("0.50", use_container_width=True): agregar_rapido(0.50)
    with cb3: 
        if st.button("1.0", use_container_width=True, type="primary"): agregar_rapido(1.0) # El 1.0 es el primario
    with cb4: 
        if st.button("1.5", use_container_width=True): agregar_rapido(1.5)
        
    # Fila 2 de Botones
    cb5, cb6, cb7 = st.columns([1,1,2])
    with cb5: 
        if st.button("2.0", use_container_width=True): agregar_rapido(2.0)
    with cb6: 
        if st.button("3.0", use_container_width=True): agregar_rapido(3.0)
    with cb7:
        # Entrada Manual
        with st.popover("🔢 Otra Cantidad", use_container_width=True):
            cant_manual = st.number_input("Ingrese cantidad exacta", step=0.1)
            if st.button("Agregar Manual"):
                if cant_manual > 0: agregar_rapido(cant_manual); st.rerun()

    st.divider()

    # D. Lista de Registros (Carrito)
    if st.session_state.temp_harvest:
        df_temp = pd.DataFrame(st.session_state.temp_harvest)
        
        # Métricas Totales
        tot_caj = df_temp["Cajuelas"].sum()
        tot_din = df_temp["Total"].sum()
        
        m1, m2 = st.columns(2)
        m1.metric("Total Cajuelas", f"{tot_caj:.2f}")
        m2.metric("Total a Pagar", f"₡{tot_din:,.0f}")
        
        # BOTÓN GUARDAR
        if st.button(f"💾 GUARDAR {len(df_temp)} REGISTROS EN NUBE", type="primary", use_container_width=True):
            datos_db = []
            for item in st.session_state.temp_harvest:
                datos_db.append((str(f_hoy), item["Nombre"], l_hoy, float(item["Cajuelas"]), float(p_hoy), OWNER))
            
            if add_recoleccion_batch(datos_db):
                st.success("✅ Datos guardados correctamente")
                st.session_state.temp_harvest = []
                time.sleep(1)
                st.rerun()
            else:
                st.error("Error de conexión")

        # Visualización simple
        st.markdown("###### 📋 Registros en cola:")
        st.dataframe(df_temp[["Hora", "Nombre", "Cajuelas"]], use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Borrar Lista (Empezar de cero)"):
            st.session_state.temp_harvest = []
            st.rerun()
    else:
        st.info("👆 Seleccione trabajador y toque un botón de cantidad.")


# =======================================================
# MODO 2: PLANILLA SEMANAL
# =======================================================
elif modo == "💵 Planilla Semanal":
    
    # Filtros
    with st.expander("📅 Rango de Fechas", expanded=True):
        c_f1, c_f2 = st.columns(2)
        hoy = datetime.date.today()
        ini = hoy - datetime.timedelta(days=hoy.weekday())
        f1 = c_f1.date_input("Desde", ini)
        f2 = c_f2.date_input("Hasta", hoy)

    # Obtener Datos
    raw = get_reporte_cosecha_detallado(f1, f2, OWNER)
    
    if raw:
        df = pd.DataFrame(raw, columns=["Recolector", "Lote", "Cajuelas", "Total ₡"])
        df["Cajuelas"] = pd.to_numeric(df["Cajuelas"])
        df["Total ₡"] = pd.to_numeric(df["Total ₡"])
        
        # Agrupar
        resumen = df.groupby("Recolector")[["Cajuelas", "Total ₡"]].sum().reset_index()
        
        # Deudas
        saldo = get_saldo_global(OWNER)
        resumen["Deuda"] = resumen["Recolector"].map(saldo).fillna(0.0)
        resumen["Abono Deuda"] = 0.0 # Columna editable

        st.caption("Edite la columna 'Abono Deuda' para cobrar préstamos.")
        
        edited = st.data_editor(
            resumen,
            column_config={
                "Recolector": st.column_config.TextColumn("Nombre", disabled=True),
                "Cajuelas": st.column_config.NumberColumn("Caj", format="%.1f", disabled=True),
                "Total ₡": st.column_config.NumberColumn("Ganado", format="₡%d", disabled=True),
                "Deuda": st.column_config.NumberColumn("Deuda", format="₡%d", disabled=True),
                "Abono Deuda": st.column_config.NumberColumn("Rebajar", format="₡%d", min_value=0)
            },
            hide_index=True,
            use_container_width=True
        )
        
        neto = edited["Total ₡"] - edited["Abono Deuda"]
        st.metric("Efectivo Total a Pagar", f"₡{neto.sum():,.0f}")
        
        # Acciones
        c_p1, c_p2 = st.columns(2)
        
        # PDF
        pdf = generar_pdf_planilla(edited, f1, f2)
        c_p1.download_button("📄 PDF", pdf, "planilla.pdf", "application/pdf", use_container_width=True)
        
        # Cerrar
        if c_p2.button("✅ Pagar y Cerrar", type="primary", use_container_width=True):
            cobros = 0
            for _, row in edited.iterrows():
                if row["Abono Deuda"] > 0:
                    add_vale(hoy, row["Recolector"], -float(row["Abono Deuda"]), f"Rebajo {f1}", OWNER)
                    cobros += 1
            st.success(f"Planilla cerrada. {cobros} rebajos aplicados.")
            time.sleep(1.5)
            st.rerun()
            
    else:
        st.info("No hay datos de recolección en estas fechas.")
        
    # Registro Vales
    st.divider()
    with st.expander("💸 Nuevo Préstamo / Vale"):
        vt = st.selectbox("Trabajador", cargar_personal(OWNER, "Recolector"))
        vm = st.number_input("Monto", step=1000)
        if st.button("Guardar Vale"):
            add_vale(hoy, vt, vm, "Adelanto", OWNER)
            st.success("Guardado")