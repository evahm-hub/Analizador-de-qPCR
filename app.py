import streamlit as st
import pandas as pd
import numpy as np

# Configuración de la página de la App
st.set_page_config(page_title="Analizador qPCR Multitarget", page_icon="🧬", layout="wide")

st.title("🧬 Analizador Genérico y Configurable de qPCR")
st.markdown("### Adapta la interpretación analítica a cualquier protocolo comercial o de diseño propio")

# --- BARRA LATERAL: CONFIGURACIÓN DINÁMICA DEL PROTOCOLO ---
st.sidebar.header("📋 Parámetros del Protocolo")

# 1. Configuración de la Diana / Patógeno
nombre_patogeno = st.sidebar.text_input("Nombre de la Diana (Patógeno)", value="Mycoplasma hyopneumoniae")
canal_patogeno = st.sidebar.selectbox("Canal del Patógeno", ["FAM", "HEX/VIC", "Cy5", "ROX", "TEXAS RED"], index=0)
corte_cq_patogeno = st.sidebar.number_input("Corte de Positividad / Límite Cq", min_value=10.0, max_value=45.0, value=38.0, step=0.5)

st.sidebar.markdown("---")

# 2. Configuración del Control Endógeno (IC)
usar_ic = st.sidebar.checkbox("¿Incluye Control Endógeno / Interno (IC)?", value=True)
if usar_ic:
    canal_ic = st.sidebar.selectbox("Canal del Control Endógeno", ["HEX/VIC", "FAM", "Cy5", "ROX"], index=0)
    ic_min = st.sidebar.number_input("Cq Mínimo aceptable para IC", min_value=10.0, max_value=30.0, value=22.0, step=0.5)
    ic_max = st.sidebar.number_input("Cq Máximo aceptable para IC (Límite de inhibición)", min_value=30.0, max_value=45.0, value=37.0, step=0.5)

st.sidebar.markdown("---")

# 3. Parámetros Técnicos de Validación del Termociclador (Control de Calidad)
st.sidebar.subheader("🎛️ Parámetros del Termociclador")
monitorear_threshold = st.sidebar.checkbox("Validar altura del Threshold", value=False)
if monitorear_threshold:
    threshold_min = st.sidebar.number_input("Valor mínimo del Threshold (RFU)", value=200)
    
monitorear_baseline = st.sidebar.checkbox("Validar rango de Baseline", value=False)
if monitorear_baseline:
    col_b1, col_b2 = st.sidebar.columns(2)
    with col_b1:
        base_start = col_b1.number_input("Ciclo Inicio", value=3)
    with col_b2:
        base_end = col_b2.number_input("Ciclo Fin", value=15)

# --- FUNCIÓN GENÉRICA DE INTERPRETACIÓN ---
def interpretar_qPCR_generico(cq_pato, cq_ic, th_valor=None, base_start_val=None, base_end_val=None):
    # Control de Calidad previo del hardware si está activo
    if monitorear_threshold and th_valor is not None and th_valor < threshold_min:
        return "❌ ERROR HARDWARE", f"Threshold demasiado bajo ({th_valor} RFU). Riesgo de falsos positivos por ruido de fondo."
        
    # Conversión segura de valores analíticos
    pato_val = pd.to_numeric(cq_pato, errors='coerce')
    ic_val = pd.to_numeric(cq_ic, errors='coerce') if usar_ic else np.nan
    
    es_pato_positivo = not np.isnan(pato_val) and pato_val <= corte_cq_patogeno
    
    if es_pato_positivo:
        if pato_val <= (corte_cq_patogeno - 8): # Alta carga relativa (ej: <= 30 si el corte es 38)
            return "🟢 POSITIVO (Alta Carga)", f"Detección fuerte de {nombre_patogeno} (Cq: {pato_val})."
        else:
            return "🟡 POSITIVO (Baja Carga)", f"Detección débil/fase límite de {nombre_patogeno} (Cq: {pato_val})."
    else:
        if usar_ic:
            es_ic_valido = not np.isnan(ic_val) and (ic_min <= ic_val <= ic_max)
            if es_ic_valido:
                return "⚪ NEGATIVO VÁLIDO", f"Ausencia de {nombre_patogeno}. Control endógeno correcto (Cq: {ic_val})."
            else:
                return "🔴 NO VÁLIDO / INHIBIDO", f"Muestra no concluyente. Control endógeno fuera de rango ({ic_val}). Diluir 1:10."
        else:
            return "⚪ NEGATIVO", f"Ausencia de amplificación de {nombre_patogeno} (Sin Control de Inhibición)."

# --- INTERFAZ PRINCIPAL ---
tab1, tab2 = st.tabs(["📝 Formulario Manual Rápido", "📂 Carga Masiva y Mapeo Dinámico"])

with tab1:
    st.subheader("Análisis rápido por muestra")
    c1, c2, c3 = st.columns(3)
    with c1:
        id_m = st.text_input("ID Muestra", value="Muestra_Ensayo")
    with c2:
        v_pato = st.text_input(f"Cq Canal {canal_patogeno} ({nombre_patogeno})", value="28.4")
    with c3:
        v_ic = st.text_input(f"Cq Canal {canal_ic if usar_ic else 'N/A'} (Control)", value="24.1") if usar_ic else "0"
        
    if st.button("Evaluar Criterios"):
        res, detalle = interpretar_qPCR_generico(v_pato, v_ic)
        st.metric(label=f"Resultado: {id_m}", value=res)
        st.info(detalle)

with tab2:
    st.subheader("Carga de datos tabulares (Cualquier formato de Termociclador)")
    archivo = st.file_uploader("Sube el archivo Excel o CSV exportado", type=["csv", "xlsx"])
    
    if archivo is not None:
        try:
            if archivo.name.endswith('.csv'):
                df = pd.read_csv(archivo)
            else:
                df = pd.read_excel(archivo)
                
            st.success("Archivo leído con éxito.")
            st.write("Muestra de las primeras filas detectadas:")
            st.dataframe(df.head(3))
            
            st.markdown("#### Mapeo dinámico de tus columnas con el protocolo:")
            columnas_disponibles = df.columns.tolist()
            
            c_id = st.selectbox("Columna del identificador de muestra", columnas_disponibles)
            c_pato = st.selectbox(f"Columna de Cq para {nombre_patogeno} ({canal_patogeno})", columnas_disponibles)
            
            c_ic = None
            if usar_ic:
                c_ic = st.selectbox(f"Columna de Cq para el Control Endógeno ({canal_ic})", columnas_disponibles)
                
            # Mapeo de Threshold opcional si viene en el Excel por fila
            col_th_excel = None
            if monitorear_threshold:
                confirmar_th_col = st.checkbox("¿El valor del Threshold viene en una columna del archivo?")
                if confirmar_th_col:
                    col_th_excel = st.selectbox("Selecciona la columna de Threshold", columnas_disponibles)

            if st.button("Ejecutar Análisis Automatizado"):
                res_lista = []
                det_lista = []
                
                for _, fila in df.iterrows():
                    th_f = fila[col_th_excel] if col_th_excel else None
                    val_p = fila[c_pato]
                    val_i = fila[c_ic] if usar_ic else None
                    
                    r, d = interpretar_qPCR_generico(val_p, val_i, th_valor=th_f)
                    res_lista.append(r)
                    det_lista.append(d)
                    
                df['DIAGNÓSTICO PROTOCOLO'] = res_lista
                df['OBSERVACIONES TÉCNICAS'] = det_lista
                
                st.markdown("### 📊 Reporte Analítico Generado")
                st.dataframe(df)
                
                # Descarga unificada
                csv_file = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Guardar informe automatizado (CSV)", csv_file, "Reporte_qPCR_Configurable.csv", "text/csv")
                
        except Exception as e:
            st.error(f"Error procesando la tabla: {e}")
