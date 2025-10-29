import streamlit as st
import pandas as pd
import time
import importlib
import sys

# ====================================
# PROTECCIÓN CON CONTRASEÑA
# ====================================
def check_password():
    """Verifica la contraseña antes de mostrar la app"""
    
    def password_entered():
        if st.session_state["password"] == st.secrets.get("password", "Optimizador05"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Primera vez - pedir contraseña
        st.title("🔐 Acceso Restringido")
        st.markdown("### Optimizador de Bobinas - Versión Beta")
        st.text_input(
            "Introduce la contraseña:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.caption("Contacta al administrador si necesitas acceso")
        return False
    elif not st.session_state["password_correct"]:
        # Contraseña incorrecta
        st.title("🔐 Acceso Restringido")
        st.markdown("### Optimizador de Bobinas - Versión Beta")
        st.text_input(
            "Introduce la contraseña:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ Contraseña incorrecta")
        return False
    else:
        # Contraseña correcta
        return True

# Verificar contraseña antes de mostrar la app
if not check_password():
    st.stop()

# ====================================
# RESTO DE TU CÓDIGO AQUÍ
# ====================================

# Configuración de página PRIMERO
st.set_page_config(page_title="Optimizador de Bobinas", layout="wide")

# Forzar recarga del módulo optimizador para evitar caché
if 'optimizador_ilp_v2' in sys.modules:
    importlib.reload(sys.modules['optimizador_ilp_v2'])

from optimizador_ilp_v2 import optimizar_ilp
from visualizador_bobinas import visualizar_bobinas, visualizar_bobinas_detallado, mostrar_estadisticas_visuales

# HEADER MÁS PEQUEÑO
st.header("Optimizador de Asignación de Bobinas - ILP")
st.caption("🔬 Optimización Matemática - Garantiza el MÍNIMO número de bobinas")

# Estructura vacía para desarrollos (orden correcto de columnas)
estructura_desarrollos = pd.DataFrame(columns=['ALEACION', 'ESTADO', 'ANCHO', 'ESPESOR', 'KG'])

# Estructura vacía para pedidos (orden correcto de columnas)
estructura_pedidos = pd.DataFrame(columns=['PEDIDO', 'COLOR', 'ALEACION', 'ESTADO', 'ANCHO', 'ESPESOR', 'KG', 'ML'])

# Inicializar datos VACÍOS en session_state
if 'df_desarrollos' not in st.session_state:
    st.session_state.df_desarrollos = estructura_desarrollos.copy()

if 'df_pedidos' not in st.session_state:
    st.session_state.df_pedidos = estructura_pedidos.copy()

# Sidebar con parámetros
with st.sidebar:
    st.header("⚙️ Parámetros de Optimización")
    
    st.markdown("---")
    
    # ========================================
    # RESTRICCIONES
    # ========================================
    with st.expander("🔧 Restricciones", expanded=True):
        desperdicio_bordes_minimo = st.number_input(
            "Desperdicio en bordes mínimo (mm)", 
            0, 50, 0, 1,
            help="Desperdicio mínimo de seguridad requerido en los bordes para las máquinas de corte (0 = sin restricción)"
        )
        
        desperdicio_bordes_maximo = st.number_input(
            "Desperdicio en bordes máximo (mm)", 
            0, 100, 40, 5,
            help="Desperdicio máximo de borde permitido en el ancho de la bobina (espacio que queda sin usar)"
        )
        
        # Validación de compatibilidad
        if desperdicio_bordes_minimo > desperdicio_bordes_maximo:
            st.error(f"⚠️ ERROR: Desperdicio mínimo ({desperdicio_bordes_minimo}mm) no puede ser mayor que el máximo ({desperdicio_bordes_maximo}mm)")
        
        margen_exceso_pedidos = st.number_input(
            "Margen Exceso Pedidos (%)", 
            0, 100, 100, 5,
            help="Tolerancia máxima de exceso sobre el TOTAL del pedido"
        )
        
        kg_max_bobina = st.number_input(
            "KG máx bobina", 
            1000, 10000, 7500, 500,
            help="Peso máximo permitido por bobina"
        )
        
        kg_min_bobina = st.number_input(
            "KG mín bobina", 
            50, 2000, 200, 50,
            help="Peso mínimo para considerar una bobina válida"
        )
        
        max_cortes_por_pedido = st.number_input(
            "Máx cortes por pedido", 
            5, 30, 15, 1,
            help="Número máximo de cortes del mismo pedido en una bobina"
        )
    
    # ========================================
    # PARÁMETROS ILP
    # ========================================
    with st.expander("🔬 Parámetros ILP", expanded=True):
        margen_cobertura = st.slider(
            "% de exigencia para llegar exactamente a los kg del pedido",
            80, 100, 95, 1,
            help="Porcentaje mínimo de kg que debe asignarse. 100% = debe llegar exacto, 95% = acepta 95% del pedido, 80% = acepta 80%"
        ) / 100.0
        
        factor_penalizacion_desperdicio = st.slider(
            "⚖️ Penalización de desperdicio de bordes",
            0.0, 0.1, 0.01, 0.005,
            help="Controla el balance entre minimizar bobinas y reducir desperdicio. 0 = solo minimiza bobinas, 0.01 = balance recomendado, 0.05+ = prioriza compactación"
        )
        
        relajacion_ml_minimos_porcentaje = st.number_input(
            "% relajación para cumplir los ml minimos por bobina", 
            0, 100, 50, 5,
            help="Porcentaje de relajación del requisito ML. Con 10%, si pedido requiere 3000ml acepta desde 2700ml (solo hacia abajo)"
        )
        
        ml_minimo_resto = st.number_input(
            "No dejar bobinas con menos de estos metros lineales (usar todo si se puede)",
            0, 1000, 600, 50,
            help="Si una bobina dejaría menos ML de resto que este valor, el optimizador la usará completa. Ejemplo: con 600ml, si sobrarían 400ml, usa toda la bobina. 0 = desactivado"
        )
        
        tiempo_max_segundos = st.number_input(
            "Tiempo máximo (segundos)",
            30, 600, 300, 30,
            help="Tiempo máximo de resolución. Si no encuentra solución, se detiene."
        )
        
        st.info(f"""
        ⏱️ **Tiempo configurado:** {tiempo_max_segundos}s
        
        Para casos pequeños (<10 pedidos): ~1-30s
        Para casos medianos (10-20 pedidos): ~30-300s
        """)

# ========================================
# MAIN CONTENT
# ========================================

# Tabs principales
tab_entrada, tab_optimizar, tab_visualizacion, tab_bobinas, tab_detalle = st.tabs([
    "📥 Datos de Entrada",
    "⚡ Optimizar",
    "📈 Visualización",
    "🎲 Bobinas",
    "📋 Detalle"
])

# ========================================
# TAB: DATOS DE ENTRADA (SIN LABEL)
# ========================================
with tab_entrada:
    col_dev, col_ped = st.columns(2)
    
    with col_dev:
        st.caption("🧵 **Desarrollos**")
        
        with st.expander("📤 Drag and drop file here", expanded=False):
            st.caption("Límit 200MB per file • CSV, XLSX, XLS")
            uploaded_dev = st.file_uploader(
                "Browse files",
                type=['csv', 'xlsx', 'xls'],
                key='upload_desarrollos',
                label_visibility='collapsed'
            )
            
            if uploaded_dev:
                try:
                    if uploaded_dev.name.endswith('.csv'):
                        df_desarrollos_cargado = pd.read_csv(uploaded_dev)
                    else:
                        df_desarrollos_cargado = pd.read_excel(uploaded_dev)
                    
                    # Convertir columnas de texto a string
                    df_desarrollos_cargado['ALEACION'] = df_desarrollos_cargado['ALEACION'].astype(str)
                    df_desarrollos_cargado['ESTADO'] = df_desarrollos_cargado['ESTADO'].astype(str)
                    
                    # Limpiar y convertir columnas numéricas (comas a puntos)
                    for col in ['ANCHO', 'ESPESOR', 'KG']:
                        if col in df_desarrollos_cargado.columns:
                            # Reemplazar comas por puntos y convertir a float
                            df_desarrollos_cargado[col] = df_desarrollos_cargado[col].astype(str).str.replace(',', '.')
                            df_desarrollos_cargado[col] = pd.to_numeric(df_desarrollos_cargado[col], errors='coerce').fillna(0).astype('float64')
                    
                    st.session_state.df_desarrollos = df_desarrollos_cargado
                    st.success(f"✅ {len(df_desarrollos_cargado)} desarrollos cargados")
                except Exception as e:
                    st.error(f"Error al cargar archivo: {str(e)}")
        
        # EDITOR EDITABLE con altura mayor (600px)
        edited_desarrollos = st.data_editor(
            st.session_state.df_desarrollos.reset_index(drop=True),  # Resetear índice
            use_container_width=True, 
            height=600,
            num_rows="dynamic",
            key="data_editor_dev",
            hide_index=True,  # Ocultar columna de índice
            column_config={
                "ANCHO": st.column_config.NumberColumn(
                    "ANCHO",
                    help="Ancho del desarrollo en mm (puede ser decimal, ej: 1250.5)",
                    format="%.2f",
                    step=0.01,
                    min_value=0
                ),
                "ESPESOR": st.column_config.NumberColumn(
                    "ESPESOR",
                    help="Espesor en mm",
                    format="%.2f",
                    step=0.01,
                    min_value=0
                ),
                "KG": st.column_config.NumberColumn(
                    "KG",
                    help="Kilogramos disponibles",
                    format="%.2f",
                    step=0.01,
                    min_value=0
                )
            }
        )
        
        # Botón discreto al lado del caption
        col_caption, col_btn = st.columns([3, 1])
        with col_caption:
            st.caption(f"📊 {len(edited_desarrollos)} desarrollos")
        with col_btn:
            if st.button("💾 Guardar", key='btn_save_dev', type="secondary", use_container_width=True):
                # Procesar datos
                df_temp = edited_desarrollos.copy()
                df_temp['ALEACION'] = df_temp['ALEACION'].astype(str)
                df_temp['ESTADO'] = df_temp['ESTADO'].astype(str)
                
                for col in ['ANCHO', 'ESPESOR', 'KG']:
                    if col in df_temp.columns:
                        df_temp[col] = df_temp[col].astype(str).str.replace(',', '.')
                        df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce').fillna(0).astype('float64')
                
                # Resetear índice para que sea consecutivo
                df_temp = df_temp.reset_index(drop=True)
                st.session_state.df_desarrollos = df_temp
                st.rerun()  # FORZAR recarga para que el editor se recree
    
    with col_ped:
        st.caption("📦 **Pedidos**")
        
        with st.expander("📤 Drag and drop file here", expanded=False):
            st.caption("Límit 200MB per file • CSV, XLSX, XLS")
            uploaded_ped = st.file_uploader(
                "Browse files",
                type=['csv', 'xlsx', 'xls'],
                key='upload_pedidos',
                label_visibility='collapsed'
            )
            
            if uploaded_ped:
                try:
                    if uploaded_ped.name.endswith('.csv'):
                        df_pedidos_cargado = pd.read_csv(uploaded_ped)
                    else:
                        df_pedidos_cargado = pd.read_excel(uploaded_ped)
                    
                    # Convertir columnas de texto a string
                    df_pedidos_cargado['PEDIDO'] = df_pedidos_cargado['PEDIDO'].astype(str)
                    df_pedidos_cargado['ALEACION'] = df_pedidos_cargado['ALEACION'].astype(str)
                    df_pedidos_cargado['ESTADO'] = df_pedidos_cargado['ESTADO'].astype(str)
                    if 'COLOR' in df_pedidos_cargado.columns:
                        df_pedidos_cargado['COLOR'] = df_pedidos_cargado['COLOR'].astype(str)
                    
                    # Limpiar y convertir columnas numéricas (comas a puntos)
                    for col in ['ANCHO', 'ESPESOR', 'KG', 'ML']:
                        if col in df_pedidos_cargado.columns:
                            # Reemplazar comas por puntos y convertir a float
                            df_pedidos_cargado[col] = df_pedidos_cargado[col].astype(str).str.replace(',', '.')
                            df_pedidos_cargado[col] = pd.to_numeric(df_pedidos_cargado[col], errors='coerce').fillna(0).astype('float64')
                    
                    st.session_state.df_pedidos = df_pedidos_cargado
                    st.success(f"✅ {len(df_pedidos_cargado)} pedidos cargados")
                except Exception as e:
                    st.error(f"Error al cargar archivo: {str(e)}")
        
        # EDITOR EDITABLE con altura mayor (600px)
        edited_pedidos = st.data_editor(
            st.session_state.df_pedidos.reset_index(drop=True),  # Resetear índice
            use_container_width=True, 
            height=600,
            num_rows="dynamic",
            key="data_editor_ped",
            hide_index=True,  # Ocultar columna de índice
            column_config={
                "ANCHO": st.column_config.NumberColumn(
                    "ANCHO",
                    help="Ancho del pedido en mm (puede ser decimal, ej: 390.5)",
                    format="%.2f",
                    step=0.01,
                    min_value=0
                ),
                "ESPESOR": st.column_config.NumberColumn(
                    "ESPESOR",
                    help="Espesor en mm",
                    format="%.2f",
                    step=0.01,
                    min_value=0
                ),
                "KG": st.column_config.NumberColumn(
                    "KG",
                    help="Kilogramos",
                    format="%.2f",
                    step=0.01,
                    min_value=0
                ),
                "ML": st.column_config.NumberColumn(
                    "ML",
                    help="Metros lineales mínimos",
                    format="%.0f",
                    step=1,
                    min_value=0
                )
            }
        )
        
        # Botón discreto al lado del caption
        col_caption, col_btn = st.columns([3, 1])
        with col_caption:
            st.caption(f"📊 {len(edited_pedidos)} pedidos")
        with col_btn:
            if st.button("💾 Guardar", key='btn_save_ped', type="secondary", use_container_width=True):
                # Procesar datos
                df_temp = edited_pedidos.copy()
                df_temp['PEDIDO'] = df_temp['PEDIDO'].astype(str)
                df_temp['ALEACION'] = df_temp['ALEACION'].astype(str)
                df_temp['ESTADO'] = df_temp['ESTADO'].astype(str)
                if 'COLOR' in df_temp.columns:
                    df_temp['COLOR'] = df_temp['COLOR'].astype(str)
                
                for col in ['ANCHO', 'ESPESOR', 'KG', 'ML']:
                    if col in df_temp.columns:
                        df_temp[col] = df_temp[col].astype(str).str.replace(',', '.')
                        df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce').fillna(0).astype('float64')
                
                # Resetear índice para que sea consecutivo
                df_temp = df_temp.reset_index(drop=True)
                st.session_state.df_pedidos = df_temp
                st.rerun()  # FORZAR recarga para que el editor se recree

# ========================================
# TAB: OPTIMIZAR
# ========================================
with tab_optimizar:
    st.header("⚡ Ejecutar Optimización")
    
    if st.button("🚀 OPTIMIZAR", type="primary", use_container_width=True):
        if len(st.session_state.df_desarrollos) == 0:
            st.error("❌ No hay desarrollos cargados")
        elif len(st.session_state.df_pedidos) == 0:
            st.error("❌ No hay pedidos cargados")
        else:
            with st.spinner("🔄 Optimizando... Esto puede tardar unos segundos"):
                tiempo_inicio = time.time()
                
                try:
                    # ========================================
                    # LIMPIAR DATOS: Convertir comas a puntos y manejar valores vacíos
                    # ========================================
                    def limpiar_datos_numericos(df, columnas_numericas):
                        """
                        Convierte comas decimales a puntos y maneja valores vacíos/nulos
                        - Reemplaza None, 'None', '', NaN por 0
                        - Convierte comas a puntos
                        - Convierte a float
                        """
                        df_limpio = df.copy()
                        
                        for col in columnas_numericas:
                            if col in df_limpio.columns:
                                # Paso 1: Reemplazar valores nulos/vacíos
                                df_limpio[col] = df_limpio[col].replace(['None', 'none', '', ' ', 'nan', 'NaN'], pd.NA)
                                df_limpio[col] = df_limpio[col].fillna(0)
                                
                                # Paso 2: Convertir a string y reemplazar comas por puntos
                                df_limpio[col] = df_limpio[col].astype(str).str.strip()
                                df_limpio[col] = df_limpio[col].str.replace(',', '.')
                                
                                # Paso 3: Convertir a float (ahora seguro que no hay None)
                                df_limpio[col] = pd.to_numeric(df_limpio[col], errors='coerce').fillna(0)
                        
                        return df_limpio
                    
                    # Limpiar desarrollos
                    df_desarrollos_limpio = limpiar_datos_numericos(
                        st.session_state.df_desarrollos,
                        columnas_numericas=['ANCHO', 'ESPESOR', 'KG']
                    )
                    
                    # Contar filas antes de eliminar
                    filas_originales_dev = len(df_desarrollos_limpio)
                    
                    # Eliminar filas con valores críticos en 0 (opcional pero recomendado)
                    df_desarrollos_limpio = df_desarrollos_limpio[
                        (df_desarrollos_limpio['ANCHO'] > 0) & 
                        (df_desarrollos_limpio['ESPESOR'] > 0) & 
                        (df_desarrollos_limpio['KG'] > 0)
                    ]
                    
                    # Informar si se eliminaron filas
                    filas_eliminadas_dev = filas_originales_dev - len(df_desarrollos_limpio)
                    if filas_eliminadas_dev > 0:
                        st.warning(f"⚠️ Se eliminaron {filas_eliminadas_dev} desarrollos con valores vacíos o cero")
                    
                    # Limpiar pedidos
                    df_pedidos_limpio = limpiar_datos_numericos(
                        st.session_state.df_pedidos,
                        columnas_numericas=['ANCHO', 'KG', 'ESPESOR', 'ML']
                    )
                    
                    # Contar filas antes de eliminar
                    filas_originales_ped = len(df_pedidos_limpio)
                    
                    # Eliminar filas con valores críticos en 0 (opcional pero recomendado)
                    df_pedidos_limpio = df_pedidos_limpio[
                        (df_pedidos_limpio['ANCHO'] > 0) & 
                        (df_pedidos_limpio['KG'] > 0) & 
                        (df_pedidos_limpio['ESPESOR'] > 0)
                    ]
                    
                    # Informar si se eliminaron filas
                    filas_eliminadas_ped = filas_originales_ped - len(df_pedidos_limpio)
                    if filas_eliminadas_ped > 0:
                        st.warning(f"⚠️ Se eliminaron {filas_eliminadas_ped} pedidos con valores vacíos o cero")
                    
                    # Verificar que hay datos después de limpiar
                    if len(df_desarrollos_limpio) == 0:
                        st.error("❌ No hay desarrollos válidos después de limpiar los datos. Verifica que no haya celdas vacías.")
                        st.stop()
                    
                    if len(df_pedidos_limpio) == 0:
                        st.error("❌ No hay pedidos válidos después de limpiar los datos. Verifica que no haya celdas vacías.")
                        st.stop()
                    
                    # ========================================
                    # OPTIMIZAR con datos limpios
                    # ========================================
                    resultado = optimizar_ilp(
                        df_desarrollos=df_desarrollos_limpio,
                        df_pedidos=df_pedidos_limpio,
                        desperdicio_bordes_minimo=desperdicio_bordes_minimo,
                        desperdicio_bordes_maximo=desperdicio_bordes_maximo,
                        margen_exceso=1 + (margen_exceso_pedidos / 100),  # Convertir % a factor
                        kg_max_bobina=kg_max_bobina,
                        kg_min_bobina=kg_min_bobina,
                        max_cortes_por_pedido=max_cortes_por_pedido,
                        margen_cobertura=margen_cobertura,
                        margen_tolerancia_ml_pct=relajacion_ml_minimos_porcentaje,  # Ya viene en %
                        ml_minimo_resto=ml_minimo_resto,
                        tiempo_max_segundos=tiempo_max_segundos,
                        factor_penalizacion_desperdicio=factor_penalizacion_desperdicio,
                        debug=True
                    )
                    
                    tiempo_total = time.time() - tiempo_inicio
                    
                    if resultado and len(resultado) > 0:
                        st.session_state.solucion = resultado[0]['dataframe']
                        st.success(f"✅ Optimización completada en {tiempo_total:.2f}s")
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Bobinas Generadas", resultado[0]['num_bobinas'])
                        col2.metric("Desperdicio Total", f"{resultado[0]['desperdicio_total']:.0f}mm")
                        col3.metric("KG Totales", f"{resultado[0]['kg_totales']:.0f}kg")
                        
                        st.info("👉 Ve a las pestañas 'Visualización', 'Bobinas' o 'Detalle' para ver los resultados")
                    else:
                        st.error("❌ No se encontró solución óptima")
                        
                except Exception as e:
                    st.error(f"❌ Error durante la optimización: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    st.markdown("---")
    
    if 'solucion' in st.session_state:
        st.subheader("📊 Resumen de Cumplimiento")
        
        num_bobinas = len(st.session_state.solucion['BOBINA'].unique())
        
        pedidos_asignados = st.session_state.solucion.groupby('PEDIDO')['KG_ASIGNADOS'].sum()
        pedidos_solicitados = st.session_state.df_pedidos.set_index('PEDIDO')['KG']
        
        cumplimiento_data = []
        for pedido_id in st.session_state.df_pedidos['PEDIDO']:
            kg_asignado = float(pedidos_asignados.get(pedido_id, 0))
            kg_solicitado = float(pedidos_solicitados.get(pedido_id, 0))
            porcentaje = (kg_asignado / kg_solicitado * 100) if kg_solicitado > 0 else 0
            cumplimiento_data.append({
                'PEDIDO': pedido_id,
                'KG_SOLICITADO': kg_solicitado,
                'KG_ASIGNADO': kg_asignado,
                'PORCENTAJE': porcentaje
            })
        
        df_cumplimiento = pd.DataFrame(cumplimiento_data)
        promedio_cumplimiento = df_cumplimiento['PORCENTAJE'].mean()
        completos = len(df_cumplimiento[df_cumplimiento['PORCENTAJE'] >= 95])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Promedio Cumplimiento", f"{promedio_cumplimiento:.1f}%")
        col2.metric("Pedidos Completos", f"{completos}/{len(df_cumplimiento)}")
        col3.metric("Bobinas Generadas", num_bobinas)
        
        for _, row in df_cumplimiento.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{row['PEDIDO']}** - {row['KG_ASIGNADO']:.0f} de {row['KG_SOLICITADO']:.0f} kg")
            with col2:
                color = 'normal' if row['PORCENTAJE'] >= 95 else 'off'
                st.progress(min(row['PORCENTAJE']/100, 1.0), text=f"{row['PORCENTAJE']:.1f}%")


# ========================================
# TAB: VISUALIZACIÓN
# ========================================
with tab_visualizacion:
    if 'solucion' not in st.session_state:
        st.info("⚠️ Ejecuta la optimización primero para ver resultados")
    else:
        st.header("📊 Visualización Gráfica de Bobinas")
        
        tipo_viz = st.radio(
            "Tipo de visualización:",
            options=["Compacta (varias bobinas)", "Detallada (una por fila)", "Estadísticas"],
            horizontal=True
        )
        
        if tipo_viz == "Compacta (varias bobinas)":
            st.info("📊 Cada bobina se muestra como un rectángulo dividido proporcionalmente por sus cortes")
            fig = visualizar_bobinas(st.session_state.solucion)
            if fig:
                st.pyplot(fig)
                
                # Botón para descargar/imprimir
                import io
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                buf.seek(0)
                st.download_button(
                    label="🖨️ Descargar gráfico para imprimir",
                    data=buf,
                    file_name="bobinas_compacta.png",
                    mime="image/png",
                    use_container_width=True
                )
        
        elif tipo_viz == "Detallada (una por fila)":
            st.info("📊 Vista ampliada mostrando cada bobina con todos sus detalles")
            fig = visualizar_bobinas_detallado(st.session_state.solucion)
            if fig:
                st.pyplot(fig)
                
                # Botón para descargar/imprimir
                import io
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                buf.seek(0)
                st.download_button(
                    label="🖨️ Descargar gráfico para imprimir",
                    data=buf,
                    file_name="bobinas_detallada.png",
                    mime="image/png",
                    use_container_width=True
                )
        
        else:  # Estadísticas
            st.info("📊 Gráficos de cumplimiento y distribución de bobinas")
            fig = mostrar_estadisticas_visuales(st.session_state.solucion, st.session_state.df_pedidos)
            if fig:
                st.pyplot(fig)
                
                # Botón para descargar/imprimir
                import io
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                buf.seek(0)
                st.download_button(
                    label="🖨️ Descargar gráfico para imprimir",
                    data=buf,
                    file_name="estadisticas.png",
                    mime="image/png",
                    use_container_width=True
                )

# ========================================
# TAB: BOBINAS
# ========================================
with tab_bobinas:
    if 'solucion' not in st.session_state:
        st.info("⚠️ Ejecuta la optimización primero para ver resultados")
    else:
        st.header("🎲 Detalle por Bobina")
        
        bobinas = sorted(st.session_state.solucion['BOBINA'].unique())
        
        for bobina in bobinas:
            bobina_data = st.session_state.solucion[st.session_state.solucion['BOBINA'] == bobina]
            
            # Calcular totales
            ml_total = bobina_data['METROS_LINEALES'].iloc[0]
            desarrollo = bobina_data['DESARROLLO'].iloc[0]
            # ✅ CORRECCIÓN: Usar KG_TOTALES_BOBINA (incluye desperdicio)
            kg_total = bobina_data['KG_TOTALES_BOBINA'].iloc[0] if 'KG_TOTALES_BOBINA' in bobina_data.columns else bobina_data['KG_ASIGNADOS'].sum()
            desperdicio = bobina_data['DESPERDICIO'].iloc[0]
            
            # Obtener aleación, estado desde df_desarrollos
            desarrollo_parts = desarrollo.split('×')
            if len(desarrollo_parts) == 2:
                ancho_dev = float(desarrollo_parts[0])
                espesor_dev = float(desarrollo_parts[1])
                
                # Buscar en desarrollos
                dev_match = st.session_state.df_desarrollos[
                    (st.session_state.df_desarrollos['ANCHO'] == ancho_dev) &
                    (st.session_state.df_desarrollos['ESPESOR'] == espesor_dev)
                ]
                
                if not dev_match.empty:
                    aleacion = dev_match.iloc[0]['ALEACION']
                    estado = dev_match.iloc[0]['ESTADO']
                    desarrollo_completo = f"{aleacion} {estado} {desarrollo}"
                else:
                    desarrollo_completo = desarrollo
            else:
                desarrollo_completo = desarrollo
            
            # Construir resumen de cortes: 2×120 + 5×132.5 + 2×153
            cortes_resumen = []
            for _, row in bobina_data.iterrows():
                cortes_resumen.append(f"{row['NUM_CORTES']}×{row['ANCHO_CORTE']:.1f}")
            cortes_str = " + ".join(cortes_resumen)
            
            # Título descriptivo del expander
            titulo_bobina = f"📦 {desarrollo_completo} | {kg_total:.0f}kg | {ml_total:.0f}ml | Cortes: {cortes_str}"
            
            with st.expander(titulo_bobina, expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Desarrollo", desarrollo)
                col2.metric("ML", f"{ml_total:.0f}")
                col3.metric("KG Total", f"{kg_total:.0f}")
                col4.metric("Desperdicio", f"{desperdicio:.0f}mm")
                
                st.dataframe(
                    bobina_data[['PEDIDO', 'NUM_CORTES', 'ANCHO_CORTE', 'KG_ASIGNADOS']],
                    use_container_width=True
                )

# ========================================
# TAB: DETALLE
# ========================================
with tab_detalle:
    if 'solucion' not in st.session_state:
        st.info("⚠️ Ejecuta la optimización primero para ver resultados")
    else:
        st.header("📋 Tabla Detallada")
        
        st.dataframe(
            st.session_state.solucion,
            use_container_width=True,
            height=600
        )
        
        # Botón de descarga
        csv = st.session_state.solucion.to_csv(index=False)
        st.download_button(
            "📥 Descargar CSV",
            csv,
            "solucion_optimizada.csv",
            "text/csv",
            use_container_width=True
        )