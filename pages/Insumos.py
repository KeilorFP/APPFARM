import streamlit as st
import datetime
import pandas as pd
from database import add_insumo, add_analisis_suelo, get_analisis_suelo
from utils import check_login, cargar_fincas, cargar_productos, smart_select, mostrar_encabezado

# 1. VERIFICACIÓN Y ENCABEZADO
OWNER = check_login()
mostrar_encabezado("📦 Insumos & Suelos") # <--- Botón de volver al menú

# 2. NAVEGACIÓN INTERNA
opcion = st.pills("Seleccione módulo:", ["🛢️ Registro Insumos", "🧪 Análisis Suelo"], default="🛢️ Registro Insumos")

st.divider()

# ---------------------------------------------------------
# MÓDULO 1: REGISTRO DE INSUMOS (Abonos, Químicos)
# ---------------------------------------------------------
if opcion == "🛢️ Registro Insumos":
    
    # Cargar catálogos
    fincas = cargar_fincas(OWNER)
    prods = cargar_productos(OWNER)
    
    if not fincas:
        st.warning("⚠️ Primero cree Lotes en 'Ajustes'")
        st.stop()
    if not prods:
        st.warning("⚠️ Primero cree Productos en 'Ajustes'")
        st.stop()

    # Formulario Tarjeta
    with st.container(border=True):
        st.markdown("##### 📝 Nuevo Registro")
        
        # Selección de Tipo
        tipo = st.radio("Tipo de Labor:", ["Abono", "Fumigación", "Cal", "Herbicida"], horizontal=True)
        
        # Fila 1: Dónde y Cuándo
        c1, c2 = st.columns(2)
        lote = smart_select("Lote / Sector", fincas, "mem_lote_ins")
        fecha = c2.date_input("Fecha", datetime.date.today())
        
        # Fila 2: Qué Producto
        prod = st.selectbox("Producto Comercial", prods)
        
        # --- LÓGICA INTELIGENTE (BI) ---
        es_solido = tipo in ["Abono", "Cal"]
        unidad_medida = "Sacos" if es_solido else "Litros"
        unidad_precio = "Saco" if es_solido else "Litro"
        
        # Fila 3: Cantidades
        st.markdown(f"**Detalles de Aplicación ({unidad_medida})**")
        c3, c4 = st.columns(2)
        
        if es_solido:
            gramos = c3.number_input('Gramos/Mata', 0.0, step=10.0)
            dosis = f"{gramos} gr"
        else:
            # Para líquidos (Fumigación)
            cc_litro = c3.number_input('cc por Litro', 0.0, step=5.0)
            dosis = f"{cc_litro} cc/lt" if cc_litro > 0 else "Dosis General"
            
        cant = c4.number_input(f"Total {unidad_medida}", min_value=0.0, step=1.0)
        
        # Fila 4: Costos
        st.markdown("**Costos**")
        c5, c6 = st.columns(2)
        precio_unit = c5.number_input(f"Precio por {unidad_precio} ₡", min_value=0.0, step=500.0)
        
        # Cálculo en tiempo real
        total_calc = cant * precio_unit
        c6.metric("Costo Total", f"₡{total_calc:,.0f}")
        
        # Botón Guardar
        if st.button(f"💾 Guardar {tipo}", type="primary", use_container_width=True):
            if cant > 0 and precio_unit > 0:
                try:
                    # NOTA: Guardamos total_calc como el precio final
                    add_insumo(str(fecha), lote, tipo, "", prod, dosis, cant, precio_unit, OWNER) 
                    st.success(f"✅ Guardado: {cant} {unidad_medida} de {prod}")
                    st.toast("Registro exitoso", icon="📦")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error(f"⚠️ La cantidad y el precio deben ser mayores a 0")

# ---------------------------------------------------------
# MÓDULO 2: ANÁLISIS DE SUELO
# ---------------------------------------------------------
elif opcion == "🧪 Análisis Suelo":
    
    with st.expander("➕ Ingresar Nuevo Análisis", expanded=True):
        fincas = cargar_fincas(OWNER)
        if fincas:
            c_l, c_f = st.columns(2)
            sl_lote = c_l.selectbox("Lote", fincas)
            sl_fecha = c_f.date_input("Fecha Muestreo", datetime.date.today())
            
            st.markdown("**Resultados Químicos**")
            k1, k2, k3, k4 = st.columns(4)
            ph = k1.number_input("pH", 0.0, 14.0, 5.5, step=0.1)
            n = k2.number_input("N", 0.0, step=0.1)
            p = k3.number_input("P", 0.0, step=0.1)
            k = k4.number_input("K", 0.0, step=0.1)
            
            notas = st.text_area("Recomendación del Agrónomo", height=80)
            
            if st.button("Guardar Análisis", type="primary", use_container_width=True):
                add_analisis_suelo(sl_fecha, sl_lote, ph, n, p, k, notas, OWNER)
                st.success("Análisis guardado")
                st.rerun()
        else:
            st.warning("No hay lotes configurados.")

    # Tabla Histórica
    st.divider()
    st.markdown("#### 📉 Historial")
    hist = get_analisis_suelo(OWNER)
    if hist:
        df = pd.DataFrame(hist, columns=["ID","Fecha","Lote","pH","N","P","K","Notas"])
        # Formato condicional simple para pH (Rojo si es muy ácido)
        st.dataframe(
            df, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "pH": st.column_config.NumberColumn("pH", format="%.1f"),
                "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY")
            }
        )
    else:
        st.info("No hay análisis registrados aún.")