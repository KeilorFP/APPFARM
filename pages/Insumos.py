import streamlit as st
import datetime
from database import add_insumo, add_analisis_suelo, get_analisis_suelo
from utils import check_login, cargar_fincas, cargar_productos, smart_select
import pandas as pd

# ---------------------------------------------------------
# INICIO DE LA APP
# ---------------------------------------------------------

OWNER = check_login()
st.title("📦 Insumos & Suelos")

t_ins, t_suelo = st.tabs(["🛢️ Registro", "🧪 Análisis Suelo"])

# ---------------------------------------------------------
# PESTAÑA 1: REGISTRO DE INSUMOS (Lógica BI Mejorada)
# ---------------------------------------------------------
with t_ins:
    fincas = cargar_fincas(OWNER)
    prods = cargar_productos(OWNER)
    
    if fincas:
        # Selección principal
        tipo = st.radio("Labor", ["Abono", "Fumigación", "Cal", "Herbicida"], horizontal=True)
        
        with st.container(border=True):
            # Fila 1: Lote y Fecha
            c1, c2 = st.columns(2)
            # MEMORIA INTELIGENTE: Recuerda el último lote seleccionado
            lote = smart_select("Lote", fincas, "mem_lote_ins")
            fecha = c2.date_input("Fecha", datetime.date.today())
            
            # Validación de productos
            if not prods:
                st.error("⚠️ No hay productos creados en Ajustes > Listas")
            else:
                # Fila 2: Producto
                prod = st.selectbox("Producto", prods)
                
                # --- LÓGICA BI: DEFINICIÓN DE UNIDADES ---
                # Si es sólido (Abono/Cal) usamos Sacos/Gramos. Si es líquido, Litros.
                es_solido = tipo in ["Abono", "Cal"]
                unidad_medida = "Sacos" if es_solido else "Litros"
                unidad_precio = "Saco" if es_solido else "Litro"
                
                # Fila 3: Dosis y Cantidad
                c_d, c_c = st.columns(2)
                
                # Lógica de Dosis
                if es_solido:
                    val_dosis = c_d.number_input('Gramos por Mata', 0.0, step=10.0)
                    dosis = f"{val_dosis} gr"
                else:
                    # En líquidos la dosis suele ser por tonel o bomba, 
                    # lo dejamos general o puedes pedir "cc por litro"
                    c_d.info("💧 Aplicación Líquida")
                    dosis = "Dosis General"

                # Lógica de Cantidad (Input Usuario)
                cant = c_c.number_input(f"Cantidad Total ({unidad_medida})", min_value=0.0, step=1.0)
                
                # Fila 4: Precio Unitario y Cálculo Total
                st.write("---")
                cp_uni, cp_tot = st.columns(2)
                
                # Input: Precio Unitario
                precio_unit = cp_uni.number_input(f"Precio por {unidad_precio} (₡)", min_value=0.0, step=100.0)
                
                # Cálculo Automático: Cantidad * Precio Unitario
                total_calculado = cant * precio_unit
                
                # Output Visual: Mostrar el total calculado (Metric se ve más profesional)
                cp_tot.metric("Costo Total Calculado", f"₡ {total_calculado:,.2f}")

                # Botón de Guardado
                if st.button(f"Guardar {tipo}", type="primary"):
                    # Validación de integridad de datos (Data Quality)
                    if cant > 0 and precio_unit > 0:
                        try:
                            # NOTA: Tu función add_insumo espera el 'precio total', 
                            # así que le pasamos la variable 'total_calculado'.
                            add_insumo(
                                str(fecha), 
                                lote, 
                                tipo, 
                                "",         # Receta (vacío por ahora)
                                prod, 
                                dosis, 
                                cant, 
                                total_calculado, # Pasamos el cálculo, no el input
                                OWNER
                            )
                            st.success(f"✅ Registro Guardado: {cant} {unidad_medida} de {prod}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo guardar el insumo. Error: {e}")
                    else:
                        st.warning(f"⚠️ La cantidad de {unidad_medida} y el precio deben ser mayores a 0.")
    else:
        st.warning("Configure Fincas primero.")

# ---------------------------------------------------------
# PESTAÑA 2: ANÁLISIS DE SUELO (Sin cambios mayores)
# ---------------------------------------------------------
with t_suelo:
    st.caption("Historial de Análisis de Laboratorio")
    with st.expander("➕ Nuevo Resultado"):
        if fincas:
            sl_lote = st.selectbox("Lote Muestra", fincas)
            sl_fecha = st.date_input("Fecha Muestra", datetime.date.today())
            
            c_ph, c_n, c_p, c_k = st.columns(4)
            ph = c_ph.number_input("pH", 0.0, 14.0, 5.5)
            n = c_n.number_input("N", 0.0)
            p = c_p.number_input("P", 0.0)
            k = c_k.number_input("K", 0.0)
            
            notas = st.text_area("Observaciones")
            
            if st.button("Guardar Análisis"):
                try:
                    add_analisis_suelo(sl_fecha, sl_lote, ph, n, p, k, notas, OWNER)
                    st.success("Guardado correctamente")
                    st.rerun()
                except Exception:
                    st.error("No se pudo guardar el análisis. Intente de nuevo.")
    
    # Tabla de Historial
    hist = get_analisis_suelo(OWNER)
    if hist:
        df_suelo = pd.DataFrame(hist, columns=["ID","Fecha","Lote","pH","N","P","K","Notas"])
        st.dataframe(df_suelo, hide_index=True, use_container_width=True)