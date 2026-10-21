import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Paneles Solares",
    page_icon="🏠",
    layout="wide"
)


# ---------------------------------------------------------
# ESTILOS CSS PARA KPIS (TEXTO EN NEGRITA, VALOR NORMAL)
# ---------------------------------------------------------
st.markdown("""
<style>
/* Reduce el margen superior por defecto que Streamlit deja en la página */
.block-container {
    padding-top: 3.0rem !important;
    padding-bottom: 0rem;
}

/* Estilos para el título principal y subtítulo destacado */
.big-title {
    font-size: 40px;
    font-weight: 700;
    color: #B8860B; 
    letter-spacing: -1px;
    text-shadow: 0 4px 12px rgba(40, 54, 24, 0.45); 
}

.sub-title {
    font-size: 1.15rem !important;
    color: #555555;
    margin-top: 5px;
    margin-bottom: 15px;
}

/* Fuerza el tamaño y la NEGRITA en la ETIQUETA (incluyendo párrafos internos) */
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] div, [data-testid="stMetricLabel"] span, [data-testid="stMetricLabel"] p {
    font-size: 0.85rem !important;
    font-weight: 700 !important;
}

/* Ajusta el tamaño del valor numérico pero SIN negrita (peso normal) */
[data-testid="stMetricValue"] {
    font-size: 0.9rem !important;
    font-weight: 400 !important;
}

/* Ajusta el margen interno de la tarjeta KPI */
[data-testid="stMetric"] {
    background-color: rgba(128, 128, 128, 0.05);
    padding: 8px 12px;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <div class="big-title">☀️ Dashboard: Energía Solar & Paneles Fotovoltaicos</div>
    <div class="sub-title" style="margin-left: 10%;"><i>Análisis detallado de producción, consumo y flujos de red [05.10.2026]</i></div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ---------------------------------------------------------
# ORDEN PERSONALIZADO DE MESES
# ---------------------------------------------------------
orden_meses = ["Jan", "Feb", "Mar", "Avr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

# ---------------------------------------------------------
# CARGA Y TRANSFORMACIÓN DEL EXCEL (wide → long)
# ---------------------------------------------------------
@st.cache_data
def cargar_y_transformar(file):
    df = pd.read_excel(file, header=0)

    df.rename(columns={
        df.columns[0]: "Año",
        df.columns[1]: "Mes",
        df.columns[2]: "Tipo"
    }, inplace=True)

    df["Mes"] = pd.Categorical(df["Mes"], categories=orden_meses, ordered=True)

    df["Tipo"] = df["Tipo"].replace({
        "Pro": "Produced",
        "Con": "Consumed",
        "PV_used": "PV Used",
        "to_netz": "To Netz",
        "from_netz": "From Netz"
    })
    
    columnas_dias = [c for c in df.columns if c not in ["Año", "Mes", "Tipo"]]

    columnas_dias_limpias = []
    for c in columnas_dias:
        try:
            columnas_dias_limpias.append(int(c))
        except:
            columnas_dias_limpias.append(c)

    df.columns = ["Año", "Mes", "Tipo"] + columnas_dias_limpias

    df_long = df.melt(
        id_vars=["Año", "Mes", "Tipo"],
        value_vars=columnas_dias_limpias,
        var_name="Día",
        value_name="Valor"
    )

    df_long = df_long.dropna(subset=["Valor"])
    df_long["Día"] = df_long["Día"].astype(int)
    df_long["Año"] = df_long["Año"].astype(int)

    df_long["Serie"] = (
        df_long["Año"].astype(str)
        + " - "
        + df_long["Mes"].astype(str)
        + " - "
        + df_long["Tipo"]
    )

    return df_long

# ---------------------------------------------------------
# CARGA AUTOMÁTICA DEL ARCHIVO POR DEFECTO
# ---------------------------------------------------------
ruta_defecto = "SolarAnlage-Data.xlsx"

# Si 'archivo_subido' se define abajo en la barra lateral, 
# Streamlit lo recordará y estará disponible aquí en la ejecución.
if 'archivo_subido' not in locals():
    archivo_subido = None

if archivo_subido is not None:
    df_long = cargar_y_transformar(archivo_subido)
else:
    try:
        df_long = cargar_y_transformar(ruta_defecto)
    except Exception as e:
        st.error("No se pudo cargar el archivo por defecto. Sube un archivo manualmente.")
        st.stop()

# ---------------------------------------------------------
# COMPONENTE REUTILIZABLE DE PILLS
# ---------------------------------------------------------
def pills_selector(label, items, default_selected=None, key_prefix="pills"):
    st.markdown(f"#### {label}")

    items = [str(i) for i in items]

    if default_selected is None:
        default_selected = []
    default_selected = [str(i) for i in default_selected]

    state_key = f"{key_prefix}_state"
    version_key = f"{key_prefix}_version"

    # Estado inicial
    if state_key not in st.session_state:
        st.session_state[state_key] = default_selected.copy()

    if version_key not in st.session_state:
        st.session_state[version_key] = 0

    selected = st.session_state[state_key]

    # Detectar si todo está seleccionado
    all_selected = len(selected) == len(items)
    label_btn = "Deselect All" if all_selected else "Select All"

    # BOTÓN SELECT/DESELECT ALL
    if st.button(label_btn, key=f"{key_prefix}_toggle"):
        st.session_state[state_key] = [] if all_selected else items.copy()
        st.session_state[version_key] += 1
        st.rerun()

    # PILLS REALES (clave dinámica)
    pills_key = f"{key_prefix}_pills_v{st.session_state[version_key]}"

    new_selected = st.pills(
        label="",
        options=items,
        default=st.session_state[state_key],
        selection_mode="multi",
        key=pills_key
    )

    # Si el usuario tocó una pill → actualizar estado y rerun
    if new_selected != st.session_state[state_key]:
        st.session_state[state_key] = new_selected
        st.session_state[version_key] += 1
        st.rerun()

    # Devolver enteros si aplica
    try:
        return [int(x) for x in st.session_state[state_key]]
    except:
        return st.session_state[state_key]   


# ---------------------------------------------------------
# BARRA LATERAL (ST.SIDEBAR): FILTROS CON SCROLL VERTICAL
# ---------------------------------------------------------
with st.sidebar:
    st.subheader("⚙️ Filtros")

    años_disponibles = sorted(df_long["Año"].unique())
    meses_disponibles = orden_meses
    tipos_disponibles = ["Produced", "Consumed", "PV Used", "To Netz", "From Netz"]

    # 1. Detectar automáticamente el año más reciente con datos
    max_año = int(df_long["Año"].max())
    
    # 2. Detectar el último mes con datos dentro de ese año más reciente
    df_max_ano = df_long[df_long["Año"] == max_año]
    meses_presentes_ano = [m for m in orden_meses if m in df_max_ano["Mes"].astype(str).unique()]
    ultimo_mes_por_defecto = [meses_presentes_ano[-1]] if meses_presentes_ano else [orden_meses[-1]]

    # 3. Aplicar los valores por defecto automáticos
    años_sel = pills_selector("Años", años_disponibles, default_selected=[max_año], key_prefix="anos")
    meses_sel = pills_selector("Meses", meses_disponibles, default_selected=ultimo_mes_por_defecto, key_prefix="meses")
    tipos_sel = pills_selector("Tipos de dato", tipos_disponibles, default_selected=["Produced","Consumed"], key_prefix="tipos")

    dias = sorted(df_long[
        (df_long["Año"].isin(años_sel)) &
        (df_long["Mes"].isin(meses_sel))
    ]["Día"].unique())

    if len(dias) == 0:
        st.warning("Hefe, no hay datos para mostrar!")
        st.stop()
        
    rango_dias = st.slider(
        "Rango de días",
        min_value=int(min(dias)),
        max_value=int(max(dias)),
        value=(int(min(dias)), int(max(dias)))
    )

    # ---------------------------------------------------------
    # UPLOADER ABAJO DEL TODO EN LA BARRA LATERAL
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown(f"Sube tu archivo (*`{ruta_defecto}`)*")
    archivo_subido = st.file_uploader(
        "Selecciona el archivo Excel",
        type=["xlsx"],
        label_visibility="collapsed" # Opcional: oculta la etiqueta repetitiva si ya usas el markdown arriba
    )

# ---------------------------------------------------------
# CUERPO PRINCIPAL: KPIS EN UNA SOLA FILA + TABS
# ---------------------------------------------------------

# ----------
# KPIs
# ----------
st.subheader("🔍 KPIs del Período Seleccionado")

df_kpi = df_long[
    (df_long["Año"].isin(años_sel)) & 
    (df_long["Mes"].isin(meses_sel)) & 
    (df_long["Día"] >= rango_dias[0]) & 
    (df_long["Día"] <= rango_dias[1])
]

def get_val(tipo):
    return df_kpi[df_kpi["Tipo"] == tipo]["Valor"].sum()

pro = get_val("Produced")
con = get_val("Consumed")
pv_used = get_val("PV Used")
to_netz = get_val("To Netz")
from_netz = get_val("From Netz")

autoc_pct = (pv_used/pro*100) if pro > 0 else 0
dep_pct = (from_netz/con*100) if con > 0 else 0
exc_pct = (to_netz/pro*100) if pro > 0 else 0

# KPIs adicionales recomendados: Grado de Autosuficiencia (Self-Sufficiency)
self_suff_pct = (pv_used / con * 100) if con > 0 else 0

# Todos los KPIs en una sola fila usando 5 columnas
kpi_cols = st.columns(6)
with kpi_cols[0]:
    st.metric("Producción Total", f"{pro:.2f} kWh")
with kpi_cols[1]:
    st.metric("Consumo Total", f"{con:.2f} kWh")
with kpi_cols[2]:
    st.metric("Autoconsumo", f"{pv_used:.1f} kWh / {autoc_pct:.1f}%")
with kpi_cols[3]:
    st.metric("Dependencia Red", f"{from_netz:.1f} kWh / {dep_pct:.1f}%")
with kpi_cols[4]:
    st.metric("Excedente", f"{to_netz:.1f} kWh / {exc_pct:.1f}%")
with kpi_cols[5]:
    st.metric("Autosuficiencia", f"{self_suff_pct:.1f}%")
    
st.markdown("---")

# ---------------------------------------------------------
# PESTAÑAS CON LAS GRÁFICAS (JUSTO DEBAJO DE LOS KPIS)
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📈 Evolución Diaria",
    "📊 Distribución Mensual",
    "📅 Evolución Anual",
    "🌤 Paneles y Clima",
    "🌍 Impacto",
    "📄 Tabla de Datos",
    "ℹ️ Info",
    "📖 Manual de Usuario"
])

# =========================================================
# 1) 📈 EVOLUCIÓN DIARIA
# =========================================================
with tab1:
    st.subheader("📈 Evolución Diaria")

    df_filtrado = df_long[
        (df_long["Año"].isin(años_sel)) &
        (df_long["Mes"].isin(meses_sel)) &
        (df_long["Tipo"].isin(tipos_sel)) &
        (df_long["Día"] >= rango_dias[0]) &
        (df_long["Día"] <= rango_dias[1])
    ].copy()

    if df_filtrado.empty:
        st.warning("Hefe, no hay datos para mostrar!")
        st.stop()
    
    # Creamos la fecha formateada para el hover
    df_filtrado["Mes_Num_Temp"] = df_filtrado["Mes"].map(lambda m: orden_meses.index(m) + 1 if m in orden_meses else 1)
    df_filtrado["Fecha_Filtro"] = (
        df_filtrado["Año"].astype(str) + "." + 
        df_filtrado["Mes_Num_Temp"].astype(str).str.zfill(2) + "." + 
        df_filtrado["Día"].astype(str).str.zfill(2)
    )

    fig = px.line(
        df_filtrado,
        x="Día",
        y="Valor",
        color="Serie",
        line_group="Serie",
        markers=True,
        color_discrete_sequence=px.colors.qualitative.Set1,
        render_mode="svg",
        custom_data=["Fecha_Filtro", "Tipo"]  # Pasamos la fecha unificada y el tipo
    )

    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br><b>%{customdata[1]}:</b> %{y:.2f} kWh<extra></extra>"
    )

    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor="#f4f4f4",
        paper_bgcolor="#f4f4f4",
        font_color="#222",
        legend_title_text="Año - Mes - Tipo",
        margin=dict(l=40, r=150, t=60, b=40),
        height=550,
        yaxis_title="kWh",
        xaxis=dict(
            showline=True,
            linewidth=1.5,
            linecolor="black",
            mirror=False
        ),
        yaxis=dict(
            showline=True,
            linewidth=1.5,
            linecolor="black",
            mirror=False
        )
    )

    dias_presentes = sorted(df_filtrado["Día"].unique())
    for d in dias_presentes:
        fig.add_vline(
            x=d,
            line_width=1,
            line_dash="dot",  # Línea punteada ('dash', 'dot', 'dashdot')
            line_color="rgba(0, 0, 0, 0.12)"  # Sutil y elegante
        )

    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # NUEVA GRÁFICA: EVOLUCIÓN ANUAL COMPLETA (Línea Continua Ene - Dic)
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("📅 Evolución Anual Completa (01 Ene — 31 Dic)")

    df_anual_completo = df_long[
        (df_long["Año"].isin(años_sel)) &
        (df_long["Tipo"].isin(tipos_sel))
    ].copy()

    if df_anual_completo.empty:
        st.warning("No hay datos anuales para mostrar.")
    else:
        # 1. Creamos una Serie limpia que no incluya el mes
        df_anual_completo["Serie_Anual"] = df_anual_completo["Año"].astype(str) + " - " + df_anual_completo["Tipo"]

        # 2. Orden cronológico estricto
        df_anual_completo["Mes_Num"] = df_anual_completo["Mes"].map(lambda m: orden_meses.index(m) + 1)
        df_anual_completo = df_anual_completo.sort_values(["Año", "Mes_Num", "Día"])

        # 3. SECUENCIA COMPARTIDA: Asignamos un índice único por cada combinación de Mes y Día para que todos los tipos compartan la misma X
        dias_unicos = df_anual_completo[["Mes_Num", "Mes", "Día"]].drop_duplicates().sort_values(["Mes_Num", "Día"]).reset_index(drop=True)
        dias_unicos["Secuencia_X"] = dias_unicos.index

        # Mapeamos esa secuencia al DataFrame principal
        df_anual_completo = df_anual_completo.merge(dias_unicos, on=["Mes_Num", "Mes", "Día"], how="left")

        # Creamos la fecha formateada para la gráfica anual
        df_anual_completo["Fecha_Anual"] = (
            df_anual_completo["Año"].astype(str) + "." + 
            df_anual_completo["Mes_Num"].astype(str).str.zfill(2) + "." + 
            df_anual_completo["Día"].astype(str).str.zfill(2)
        )

        fig_anual = px.line(
            df_anual_completo,
            x="Secuencia_X",
            y="Valor",
            color="Serie_Anual",
            line_group="Serie_Anual",
            markers=False,
            color_discrete_sequence=px.colors.qualitative.Set1,
            render_mode="svg",
            custom_data=["Fecha_Anual", "Tipo"]  # Usamos la fecha formateada en custom_data
        )

        fig_anual.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br><b>%{customdata[1]}:</b> %{y:.2f} kWh<extra></extra>"
        )

        # 4. Calcular posiciones para las líneas divisorias de meses y las marcas del eje X (solo días 1 y 15) usando la secuencia unificada
        tickvals = []
        ticktext = []
        meses_cambio_indices = []
        meses_procesados_lineas = set()

        for (mes_num, mes), grupo in dias_unicos.groupby(["Mes_Num", "Mes"], sort=False):
            primer_indice = grupo["Secuencia_X"].min()  # <--- Corregido (primer_indice sin s)
            
            if mes not in meses_procesados_lineas:
                meses_cambio_indices.append(primer_indice)
                meses_procesados_lineas.add(mes)

            for _, row in grupo.iterrows():
                dia = row["Día"]
                if dia in [1, 15]:
                    etiqueta = f"{row['Mes']} {dia}"
                    if row["Secuencia_X"] not in tickvals:
                        tickvals.append(row["Secuencia_X"])
                        ticktext.append(etiqueta)

        # 5. Configuración del diseño
        fig_anual.update_layout(
            plot_bgcolor="#f4f4f4",
            paper_bgcolor="#f4f4f4",
            font_color="#222",
            height=500,
            margin=dict(l=40, r=40, t=60, b=40),
            showlegend=False,
            xaxis=dict(
                title="Fecha",
                tickmode="array",
                tickvals=tickvals,
                ticktext=ticktext,
                tickangle=-45,
                showgrid=True,
                gridcolor="rgba(0,0,0,0.08)",
                zeroline=False,
                showline=True,
                linewidth=1.5,
                linecolor="black",
                mirror=False
            ),
            yaxis=dict(
                title="kWh",
                showgrid=True,
                gridcolor="rgba(0,0,0,0.1)",
                zeroline=False,
                showline=True,
                linewidth=1.5,
                linecolor="black",
                mirror=False
            ),
            hovermode="x unified"
        )

        # Añadir líneas verticales divisorias para cada inicio de mes en el grid
        for idx_mes in meses_cambio_indices:
            fig_anual.add_vline(
                x=idx_mes,
                line_width=1,
                line_dash="dash",
                line_color="rgba(0, 0, 0, 0.2)"
            )

        st.plotly_chart(fig_anual, use_container_width=True)

        # ---------------------------------------------------------
        # TABLA ADICIONAL DE MÁXIMOS Y MÍNIMOS POR TIPO (AÑO MOSTRADO)
        # ---------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 📋 Resumen Anual: Máximos y Mínimos por Tipo")
        
        # Filtramos datos para el año/s seleccionado/s en la gráfica anterior
        df_tabla_resumen = df_anual_completo[df_anual_completo["Año"].isin(años_sel)]

        if not df_tabla_resumen.empty:
            registros_resumen = []
            
            # Agrupamos por Tipo (Produced, Consumed, etc.)
            for tipo_val, grupo_tipo in df_tabla_resumen.groupby("Tipo"):
                if grupo_tipo.empty:
                    continue
                
                # Fila de Valor Máximo
                idx_max = grupo_tipo["Valor"].idxmax()
                row_max = grupo_tipo.loc[idx_max]
                date_max_str = f"{row_max['Mes']} {int(row_max['Día'])}, {int(row_max['Año'])}"
                
                # Fila de Valor Mínimo
                idx_min = grupo_tipo["Valor"].idxmin()
                row_min = grupo_tipo.loc[idx_min]
                date_min_str = f"{row_min['Mes']} {int(row_min['Día'])}, {int(row_min['Año'])}"
                
                # Unificamos ambos en una sola fila por cada tipo
                registros_resumen.append({
                    "Type": tipo_val,
                    "Max": f"{row_max['Valor']:.2f} kWh",
                    "Date Max": date_max_str,
                    "Min": f"{row_min['Valor']:.2f} kWh",
                    "Date Min": date_min_str
                })

            df_resumen_final = pd.DataFrame(registros_resumen)
            # Configuramos un ancho razonable/pequeño para evitar que se expandan demasiado
            st.dataframe(
                df_resumen_final, 
                use_container_width=False, 
                hide_index=True,
                column_config={
                    "Type": st.column_config.TextColumn("Type", width="medium"),
                    "Max": st.column_config.TextColumn("Max", width="medium"),
                    "Date Max": st.column_config.TextColumn("Date Max", width="medium"),
                    "Min": st.column_config.TextColumn("Min", width="medium"),
                    "Date Min": st.column_config.TextColumn("Date Min", width="medium"),
                }
            )
        else:
            st.info("No hay suficientes datos para generar la tabla resumen.")

# =========================================================
# 2) 📊 EVOLUCIÓN / DISTRIBUCIÓN MENSUAL 
# =========================================================
with tab2:
    st.subheader("🎞 Evolución Mensual (animación)")
    st.markdown("*Selecciona los meses para activar la animación*")

    if df_filtrado.empty:
        st.warning("Hefe, no hay datos para mostrar!")
        st.stop()

    # Preparamos los datos para la animación con una serie estable
    df_anim = df_filtrado.copy()
    df_anim["Serie_Anim"] = df_anim["Año"].astype(str) + " - " + df_anim["Tipo"]

    # 1. Definimos primero el número de mes que faltaba
    df_anim["Mes_Num"] = df_anim["Mes"].map(lambda m: orden_meses.index(m) + 1 if m in orden_meses else 1)

    # 2. Nos aseguramos de que el mes respete la categoría ordenada y ordenamos filas
    df_anim["Mes"] = pd.Categorical(df_anim["Mes"], categories=orden_meses, ordered=True)
    df_anim = df_anim.sort_values(["Mes", "Día"])

    # 3. Construimos la fecha completa con formato YYYY.MM.DD
    df_anim["Fecha_Hover"] = (
        df_anim["Año"].astype(str) + "." + 
        df_anim["Mes_Num"].astype(str).str.zfill(2) + "." + 
        df_anim["Día"].astype(str).str.zfill(2)
    )

    fig_anim_mes = px.line(
        df_anim,
        x="Día",
        y="Valor",
        color="Serie_Anim",
        line_group="Serie_Anim",
        animation_frame="Mes",
        range_y=[0, df_anim["Valor"].max() * 1.1],
        color_discrete_sequence=px.colors.qualitative.Set1,
        render_mode="svg",
        custom_data=["Fecha_Hover", "Tipo"]  # [0] -> Fecha YYYY.MM.DD limpia arriba, [1] -> Tipo
    )
    
    # 4. FORZAMOS la fecha en la cabecera del hover unificado usando customdata[0]
    mi_hovertemplate = "<b>%{customdata[0]}</b><br><b>%{customdata[1]}:</b> %{y:.2f} kWh<extra></extra>"
    
    # 5. Aplicamos el hovertemplate al gráfico principal
    fig_anim_mes.update_traces(hovertemplate=mi_hovertemplate)

    # 6. Forzamos el orden cronológico de los frames y aplicamos el hovertemplate
    if fig_anim_mes.frames:
        fig_anim_mes.frames = sorted(
            fig_anim_mes.frames, 
            key=lambda f: orden_meses.index(f.name) if f.name in orden_meses else 99
        )
        
        for frame in fig_anim_mes.frames:
            for trace_data in frame.data:
                trace_data.hovertemplate = mi_hovertemplate

    # Creamos las formas (shapes) para las líneas verticales de cada día
    dias_presentes_anim = sorted(df_anim["Día"].unique())
    formas_verticales = [
        dict(
            type="line",
            x0=d, x1=d,
            y0=0, y1=1,
            yref="paper",  # Hace que la línea abarque toda la altura vertical del gráfico
            line=dict(
                color="rgba(0, 0, 0, 0.12)",
                width=1,
                dash="dot"
            )
        )
        for d in dias_presentes_anim
    ]

    fig_anim_mes.update_layout(
        hovermode="x unified",
        plot_bgcolor="#f4f4f4",
        paper_bgcolor="#f4f4f4",
        font_color="#222",
        legend_title_text="Año - Tipo",
        margin=dict(l=40, r=150, t=60, b=40),
        height=550,
        yaxis_title="kWh",
        shapes=formas_verticales,  # 👈 Añadimos las líneas verticales aquí para que funcionen con la animación
        xaxis=dict(
            showline=True,
            linewidth=1.5,
            linecolor="black",
            mirror=False,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            zeroline=False
        ),
        yaxis=dict(
            showline=True,
            linewidth=1.5,
            linecolor="black",
            mirror=False,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            zeroline=False
        )
    )

    st.plotly_chart(fig_anim_mes, use_container_width=True)

    # =========================================================
    # Producción Mensual
    # =========================================================
    st.subheader("🔆 Producción Mensual — PV Used / To Netz")

    df_prod = df_kpi[df_kpi["Tipo"].isin(["Produced", "PV Used", "To Netz"])]
    df_prod_m = df_prod.groupby(["Año", "Mes", "Tipo"])["Valor"].sum().reset_index()

    dfp = df_prod_m.pivot_table(
        index=["Año", "Mes"],
        columns="Tipo",
        values="Valor",
        fill_value=0
    ).reset_index()

    # 1. FORZAMOS QUE EXISTAN TODOS LOS MESES DE LA LISTA EN EL EJE X POR CADA AÑO
    años_unicos = sorted(df_kpi["Año"].unique()) if not df_kpi.empty else sorted(df_long["Año"].unique())
    idx_completo = pd.MultiIndex.from_product([años_unicos, orden_meses], names=["Año", "Mes"])
    
    if not dfp.empty:
        dfp = dfp.set_index(["Año", "Mes"]).reindex(idx_completo, fill_value=0).reset_index()
    else:
        dfp = pd.DataFrame(columns=["Año", "Mes", "Produced", "PV Used", "To Netz"])
        dfp["Año"] = [a for a in años_unicos for _ in orden_meses]
        dfp["Mes"] = orden_meses * len(años_unicos)
        dfp.fillna(0, inplace=True)

    # Calculamos el número de mes para armar el YYYY.MM
    dfp["Mes_Num"] = dfp["Mes"].map(lambda m: orden_meses.index(m) + 1 if m in orden_meses else 1)
    dfp["Mes"] = pd.Categorical(dfp["Mes"], categories=orden_meses, ordered=True)
    dfp = dfp.sort_values(["Mes", "Año"])

    fig_prod = go.Figure()

    # Paletas por año con amarillos/dorados de alta visibilidad
    colores_produced = ["#F4D03F", "#F1C40F", "#D4AC0D", "#B7950B"]
    colores_pvused   = ["#D5D8DC", "#A6ACAF", "#7F8C8D", "#566573"]
    colores_tonetz   = ["#85C1E9", "#5DADE2", "#3498DB", "#2E86C1"]

    for idx, año in enumerate(años_unicos):
        df_a = dfp[dfp["Año"] == año]

        c_prod = colores_produced[idx % len(colores_produced)]
        c_pv = colores_pvused[idx % len(colores_pvused)]
        c_net = colores_tonetz[idx % len(colores_tonetz)]

        # Generamos la fecha limpia YYYY.MM para cada barra de este año
        custom_data_a = [[str(año) + "." + str(row["Mes_Num"]).zfill(2)] for _, row in df_a.iterrows()]

        # --- PRODUCED ---
        fig_prod.add_bar(
            x=df_a["Mes"],
            y=df_a["Produced"],
            name=f"Produced {año}",
            marker_color=c_prod,
            offsetgroup=f"{año}_prod",
            customdata=custom_data_a,
            hovertemplate="<b>%{customdata[0]}</b><br>" + f"<span style='color:{c_prod}'><b>Produced:</b> %{{y:,.2f}} kWh</span><extra></extra>"
        )

        # --- PV USED ---
        fig_prod.add_bar(
            x=df_a["Mes"],
            y=df_a["PV Used"],
            name=f"PV Used {año}",
            marker_color=c_pv,
            offsetgroup=f"{año}_stack",
            customdata=custom_data_a,
            hovertemplate="<b>%{customdata[0]}</b><br>" + f"<span style='color:{c_pv}'><b>PV Used:</b> %{{y:,.2f}} kWh</span><extra></extra>"
        )

        # --- TO NETZ ---
        fig_prod.add_bar(
            x=df_a["Mes"],
            y=df_a["To Netz"],
            name=f"To Netz {año}",
            marker_color=c_net,
            offsetgroup=f"{año}_stack",
            customdata=custom_data_a,
            hovertemplate="<b>%{customdata[0]}</b><br>" + f"<span style='color:{c_net}'><b>To Netz:</b> %{{y:,.2f}} kWh</span><extra></extra>"
        )

        # Línea discontinua por año
        fig_prod.add_scatter(
            x=df_a["Mes"],
            y=df_a["Produced"],
            mode="lines",
            name=f"Trend {año}",
            line=dict(
                color=c_prod,
                width=1.5,
                dash="dash"
            ),
            showlegend=False,
            hoverinfo="skip"
        )

    # Creamos las líneas divisorias verticales para separar los meses (de -0.5 a len(orden_meses) - 0.5)
    shapes_meses = [
        dict(
            type="line",
            x0=i - 0.5,
            x1=i - 0.5,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(
                color="rgba(0, 0, 0, 0.15)",
                width=1,
                dash="dot"
            )
        )
        for i in range(len(orden_meses) + 1)
    ]

    fig_prod.update_layout(
        barmode="relative",
        plot_bgcolor="#f4f4f4",
        paper_bgcolor="#f4f4f4",
        font_color="#222",
        height=550,
        hovermode="closest",
        yaxis_title="kWh",
        shapes=shapes_meses,  # 👈 Añadimos las líneas delimitadoras verticales punteadas
        xaxis=dict(
            showline=True,
            linewidth=1.5,
            linecolor="black",
            mirror=False,
            showgrid=False,  # Ocultamos la rejilla vertical por defecto para que manden las formas delimitadoras
            zeroline=False
        ),
        yaxis=dict(
            showline=True,
            linewidth=1.5,
            linecolor="black",
            mirror=False,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            zeroline=False
        )
    )

    st.plotly_chart(fig_prod, use_container_width=True)
    
    # ---------------------------------------------------------
    # ⚡ CONSUMO MENSUAL
    # ---------------------------------------------------------
    st.subheader("⚡ Consumo Mensual — PV Used / From Netz")

    df_con = df_kpi[df_kpi["Tipo"].isin(["Consumed", "PV Used", "From Netz"])]
    df_con_m = df_con.groupby(["Año", "Mes", "Tipo"])["Valor"].sum().reset_index()

    dfc = df_con_m.pivot_table(
        index=["Año", "Mes"],
        columns="Tipo",
        values="Valor",
        fill_value=0
    ).reset_index()

    # FORZAMOS IGUALMENTE EL EJE X COMPLETO PARA CONSUMO
    if not dfc.empty:
        dfc = dfc.set_index(["Año", "Mes"]).reindex(idx_completo, fill_value=0).reset_index()
    else:
        dfc = pd.DataFrame(columns=["Año", "Mes", "Consumed", "PV Used", "From Netz"])
        dfc["Año"] = [a for a in años_unicos for _ in orden_meses]
        dfc["Mes"] = orden_meses * len(años_unicos)
        dfc.fillna(0, inplace=True)

    dfc["Mes_Num"] = dfc["Mes"].map(lambda m: orden_meses.index(m) + 1 if m in orden_meses else 1)
    dfc["Mes"] = pd.Categorical(dfc["Mes"], categories=orden_meses, ordered=True)
    dfc = dfc.sort_values(["Mes", "Año"])

    fig_con = go.Figure()

    # Paletas por año con los mismos tonos intensos para PV Used
    colores_consumed = ["#A6ACAF", "#909497", "#7B7D7D", "#626567"]
    colores_pvused   = ["#F4D03F", "#F1C40F", "#D4AC0D", "#B7950B"]
    colores_fromnetz = ["#85C1E9", "#5DADE2", "#3498DB", "#2E86C1"]

    for idx, año in enumerate(años_unicos):
        df_a = dfc[dfc["Año"] == año]

        c_con = colores_consumed[idx % len(colores_consumed)]
        c_pv = colores_pvused[idx % len(colores_pvused)]
        c_net_from = colores_fromnetz[idx % len(colores_fromnetz)]

        # Generamos la fecha limpia YYYY.MM para cada barra de consumo de este año
        custom_data_a = [[str(año) + "." + str(row["Mes_Num"]).zfill(2)] for _, row in df_a.iterrows()]

        # --- CONSUMED ---
        fig_con.add_bar(
            x=df_a["Mes"],
            y=df_a["Consumed"],
            name=f"Consumed {año}",
            marker_color=c_con,
            offsetgroup=f"{año}_cons",
            customdata=custom_data_a,
            hovertemplate="<b>%{customdata[0]}</b><br>" + f"<span style='color:{c_con}'><b>Consumed:</b> %{{y:,.2f}} kWh</span><extra></extra>"
        )

        # --- PV USED ---
        fig_con.add_bar(
            x=df_a["Mes"],
            y=df_a["PV Used"],
            name=f"PV Used {año}",
            marker_color=c_pv,
            offsetgroup=f"{año}_stack",
            customdata=custom_data_a,
            hovertemplate="<b>%{customdata[0]}</b><br>" + f"<span style='color:{c_pv}'><b>PV Used:</b> %{{y:,.2f}} kWh</span><extra></extra>"
        )

        # --- FROM NETZ ---
        fig_con.add_bar(
            x=df_a["Mes"],
            y=df_a["From Netz"],
            name=f"From Netz {año}",
            marker_color=c_net_from,
            offsetgroup=f"{año}_stack",
            customdata=custom_data_a,
            hovertemplate="<b>%{customdata[0]}</b><br>" + f"<span style='color:{c_net_from}'><b>From Netz:</b> %{{y:,.2f}} kWh</span><extra></extra>"
        )

        # Línea discontinua por año
        fig_con.add_scatter(
            x=df_a["Mes"],
            y=df_a["Consumed"],
            mode="lines",
            name=f"Trend {año}",
            line=dict(
                color=c_con,
                width=1.5,
                dash="dash"
            ),
            showlegend=False,
            hoverinfo="skip"
        )

    # Creamos las líneas divisorias verticales para separar los meses
    shapes_meses_con = [
        dict(
            type="line",
            x0=i - 0.5,
            x1=i - 0.5,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(
                color="rgba(0, 0, 0, 0.15)",
                width=1,
                dash="dot"
            )
        )
        for i in range(len(orden_meses) + 1)
    ]

    fig_con.update_layout(
        barmode="relative",
        plot_bgcolor="#f4f4f4",
        paper_bgcolor="#f4f4f4",
        font_color="#222",
        height=550,
        hovermode="closest",
        yaxis_title="kWh",
        shapes=shapes_meses_con,  # 👈 Líneas delimitadoras verticales punteadas para separar meses
        xaxis=dict(
            showline=True,
            linewidth=1.5,
            linecolor="black",
            mirror=False,
            showgrid=False,  # Ocultamos grid vertical para que manden las líneas delimitadoras
            zeroline=False
        ),
        yaxis=dict(
            showline=True,
            linewidth=1.5,
            linecolor="black",
            mirror=False,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            zeroline=False
        )
    )

    st.plotly_chart(fig_con, use_container_width=True)

    
# =========================================================
# 3) 📅 VISTA ANUAL (Cuadrícula 2x3)
# =========================================================
with tab3:
    st.subheader("📅 Vista Anual")

    df_anual_full = df_long.groupby(["Año", "Tipo"])["Valor"].sum().reset_index()
    df_anual_full["Valor_MWh"] = df_anual_full["Valor"] / 1000.0
    # Formateamos con 2 decimales y reemplazamos el punto por coma
    df_anual_full["Valor_Str"] = df_anual_full["Valor_MWh"].apply(lambda x: f"{x:.2f}".replace('.', ','))

    # Definimos los colores base que usábamos en el tab3 para mantener coherencia
    colores_map = {
        "Produced": "#F1C40F",   # Amarillo principal
        "Consumed": "#7B7D7D",   # Gris oscuro principal
        "PV Used": "#00C268",    # Verde / Gris de apilado
        "To Netz": "#3498DB",    # Azul de red (producción)
        "From Netz": "#5DADE2"   # Azul claro de red (consumo)
    }

    # Diccionario de iconos para cada tipo
    iconos_map = {
        "Produced": "☀️",
        "Consumed": "🏠",
        "PV Used": "🔋",
        "To Netz": "➡⚡",
        "From Netz": "⬅️🔌"
    }

    # Fila 1: Producción y derivados
    tipos_fila1 = ["Produced", "PV Used", "To Netz"]
    cols1 = st.columns(3)

    for i, t in enumerate(tipos_fila1):
        with cols1[i]:
            icono = iconos_map.get(t, "📊")
            st.markdown(f"#### {icono} {t}")
            df_t = df_anual_full[df_anual_full["Tipo"] == t].sort_values("Año")

            x_numeric = list(range(len(df_t)))
            x_labels = df_t["Año"].astype(str).tolist()
            
            # Combinamos Año y el valor con coma en customdata
            customdata_arr = df_t[["Año", "Valor_Str"]].values.tolist()
            color_actual = colores_map.get(t, "#F7DC6F")

            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=x_numeric,
                y=df_t["Valor_MWh"],
                marker_color=color_actual,
                width=0.25,
                customdata=customdata_arr,
                hovertemplate=f"<b>%{{customdata[0]}}</b><br><span style='color:{color_actual}'><b>{t}:</b> %{{customdata[1]}} MWh</span><extra></extra>"
            ))

            fig.add_trace(go.Scatter(
                x=x_numeric,
                y=df_t["Valor_MWh"],
                mode="lines+markers",
                line=dict(color=color_actual, width=2),
                marker=dict(size=5),
                customdata=customdata_arr,
                hovertemplate=f"<b>%{{customdata[0]}}</b><br><span style='color:{color_actual}'><b>{t}:</b> %{{customdata[1]}} MWh</span><extra></extra>"
            ))

            fig.update_layout(
                height=220,
                margin=dict(l=0, r=10, t=20, b=30),
                plot_bgcolor="#f7f7f7",
                paper_bgcolor="#f7f7f7",
                font_color="#333",
                showlegend=False,
                hovermode="closest",
                xaxis=dict(tickmode="array", tickvals=x_numeric, ticktext=x_labels, showgrid=False, zeroline=False),
                yaxis=dict(title="MWh", showgrid=True, gridcolor="rgba(0,0,0,0.15)", zeroline=False)
            )

            st.plotly_chart(fig, use_container_width=True, key=f"anual_f1_{t}")

    # Fila 2: Consumo y derivados
    tipos_fila2 = ["Consumed", "PV Used", "From Netz"]
    cols2 = st.columns(3)

    for i, t in enumerate(tipos_fila2):
        with cols2[i]:
            icono = iconos_map.get(t, "📊")
            st.markdown(f"#### {icono} {t}")
            df_t = df_anual_full[df_anual_full["Tipo"] == t].sort_values("Año")

            x_numeric = list(range(len(df_t)))
            x_labels = df_t["Año"].astype(str).tolist()
            customdata_arr = df_t[["Año", "Valor_Str"]].values.tolist()
            color_actual = colores_map.get(t, "#2980B9")

            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=x_numeric,
                y=df_t["Valor_MWh"],
                marker_color=color_actual,
                width=0.25,
                customdata=customdata_arr,
                hovertemplate=f"<b>%{{customdata[0]}}</b><br><span style='color:{color_actual}'><b>{t}:</b> %{{customdata[1]}} MWh</span><extra></extra>"
            ))

            fig.add_trace(go.Scatter(
                x=x_numeric,
                y=df_t["Valor_MWh"],
                mode="lines+markers",
                line=dict(color=color_actual, width=2),
                marker=dict(size=5),
                customdata=customdata_arr,
                hovertemplate=f"<b>%{{customdata[0]}}</b><br><span style='color:{color_actual}'><b>{t}:</b> %{{customdata[1]}} MWh</span><extra></extra>"
            ))

            fig.update_layout(
                height=220,
                margin=dict(l=0, r=10, t=20, b=30),
                plot_bgcolor="#f7f7f7",
                paper_bgcolor="#f7f7f7",
                font_color="#333",
                showlegend=False,
                hovermode="closest",
                xaxis=dict(tickmode="array", tickvals=x_numeric, ticktext=x_labels, showgrid=False, zeroline=False),
                yaxis=dict(title="MWh", showgrid=True, gridcolor="rgba(0,0,0,0.15)", zeroline=False)
            )

            st.plotly_chart(fig, use_container_width=True, key=f"anual_f2_{t}")


# =========================================================
# 4) 🌤️ PANEL DE CLIMA E HISTÓRICO EN INGOLSTADT
# =========================================================
with tab4:
    import requests
    from datetime import date

    st.subheader("🌤️ Panel Meteorológico")
    st.markdown("*Datos públicos de tiempo vs producción y consumo total para los meses seleccionados.*")

    # ÚNICA CAJA DE TEXTO LIBRE: Precargada por defecto con "Ingolstadt"
    busqueda_usuario = st.text_input(
        "🔍 Escribe cualquier ciudad o código postal del mundo (ej. Ingolstadt, 47004):",
        value="Ingolstadt"
    )

    # Función para buscar coordenadas globales en tiempo real mediante la API de Open-Meteo
    @st.cache_data
    def buscar_coordenadas(nombre_lugar):
        if not nombre_lugar.strip():
            return 48.7657, 11.4231, "Ingolstadt" # Fallback por defecto
        
        url_geo = f"https://geocoding-api.open-meteo.com/v1/search?name={nombre_lugar}&count=1&language=es&format=json"
        try:
            res = requests.get(url_geo)
            data = res.json()
            if "results" in data and len(data["results"]) > 0:
                loc = data["results"][0]
                lat = loc["latitude"]
                lon = loc["longitude"]
                nombre = loc.get("name", nombre_lugar)
                pais = loc.get("country", "")
                nombre_completo = f"{nombre} ({pais})" if pais else nombre
                return lat, lon, nombre_completo
        except Exception:
            pass
        
        return 48.7657, 11.4231, "Ingolstadt"

    LAT_LOC, LON_LOC, nombre_loc = buscar_coordenadas(busqueda_usuario)

    def obtener_info_clima(code, horas_sol=0):
        if isinstance(code, list):
            code = code[0] if len(code) > 0 else 0
            
        if pd.isna(code):
            return "⛅ Parcialmente nublado"

        try:
            code = int(code)
        except Exception:
            return "⛅ Parcialmente nublado"
        
        if code == 3:
            return "☁️ Nublado"
        elif code in [45, 48]:
            return "🌁️ Niebla"
        elif code in [53, 55, 56, 57, 63, 65, 66, 67, 80, 81, 82]:
            return "🌧️ Lluvioso"
        elif code in [71, 73, 75, 77, 85, 86] and horas_sol < 10:
            return "❄️ Nieve"
        elif code in [95, 96, 99]:
            return "🌩️Tormenta"
        elif code in [2, 51, 61] and (horas_sol >= 5.5 and horas_sol < 10.8):
            return "⛅ Parcialmente nublado"
        elif code in [0, 1] or horas_sol >= 10.8:
            return "☀️ Soleado"
        else:
            return "⛅ Parcialmente nublado"

    if años_sel and meses_sel:
        try:
            min_anio = min(años_sel)
            max_anio = max(años_sel)
            f_inicio = f"{min_anio}-01-01"
            hoy_str = date.today().strftime("%Y-%m-%d")
            if max_anio >= date.today().year:
                f_fin = min(f"{max_anio}-12-31", hoy_str)
            else:
                f_fin = f"{max_anio}-12-31"
            
            @st.cache_data
            def cargar_clima_localidad(lat, lon, start_d, end_d):
                url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_d}&end_date={end_d}&daily=weathercode,precipitation_sum,snowfall_sum,temperature_2m_max,temperature_2m_min,sunshine_duration,windspeed_10m_max&timezone=Europe/Berlin"
                try:
                    response = requests.get(url)
                    data = response.json()
                    if "daily" in data:
                        df_w = pd.DataFrame(data["daily"])
                        df_w["time"] = pd.to_datetime(df_w["time"])
                        df_w["Fecha"] = df_w["time"].dt.strftime("%Y.%m.%d")
                        df_w["Año"] = df_w["time"].dt.year
                        df_w["Mes_Num"] = df_w["time"].dt.month
                        df_w["Día"] = df_w["time"].dt.day
                        
                        meses_es = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Avr", 5: "Mai", 6: "Jun",
                                    7: "Jul", 8: "Aug", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Dez"}
                        df_w["Mes"] = df_w["Mes_Num"].map(meses_es)
                        
                        df_w["Horas_Sol"] = (df_w["sunshine_duration"].fillna(0) / 3600).round(1) if "sunshine_duration" in df_w else 0
                        df_w["Horas_Nubes"] = (12 - df_w["Horas_Sol"]).clip(lower=0).round(1)
                        
                        df_w["Clima_Texto"] = [obtener_info_clima(code, sol) for code, sol in zip(df_w["weathercode"], df_w["Horas_Sol"])]
                        df_w["Icono"] = [
                            "☀️" if "Soleado" in t else 
                            ("⛅" if "Parcial" in t else 
                            ("☁️" if ("Nublado" in t or "Nubes" in t) else 
                            ("🌧️" if ("Lluvia" in t or "Lluvioso" in t) else 
                            ("❄️" if "Nieve" in t else 
                            ("🌩️" if "Tormenta" in t else 
                            ("🌁️" if "Niebla" in t else "☁️"))))))
                            for t in df_w["Clima_Texto"]
                        ]
                        
                        df_w = df_w.rename(columns={
                            "precipitation_sum": "Lluvia", 
                            "snowfall_sum": "Nieve",
                            "temperature_2m_max": "Temp_Max",
                            "temperature_2m_min": "Temp_Min",
                            "windspeed_10m_max": "Viento"
                        })
                        
                        df_w["Temp_Media"] = ((df_w["Temp_Max"] + df_w["Temp_Min"]) / 2).round(2)
                        
                        return df_w[["Fecha", "Año", "Mes_Num", "Mes", "Día", "Clima_Texto", "Icono", "Temp_Max", "Temp_Min", "Temp_Media", "Horas_Sol", "Horas_Nubes", "Viento", "Lluvia", "Nieve"]]
                except Exception:
                    pass
                return pd.DataFrame()

            df_weather = cargar_clima_localidad(LAT_LOC, LON_LOC, f_inicio, f_fin)

            if not df_weather.empty:
                for col, val in [("Fecha", ""), ("Clima_Texto", "☁️ Nublado"), ("Temp_Max", 0), ("Temp_Min", 0), ("Temp_Media", 0),
                                 ("Horas_Sol", 0), ("Horas_Nubes", 0), ("Viento", 0), ("Lluvia", 0), ("Nieve", 0), ("Icono", "☁"), ("Mes_Num", 1)]:
                    if col not in df_weather.columns:
                        df_weather[col] = val

                df_energia_total = df_long[
                    (df_long["Año"].isin(años_sel)) & 
                    (df_long["Mes"].isin(meses_sel)) & 
                    (df_long["Tipo"].isin(["Produced", "Consumed"]))
                ].copy()

                df_panel_final = pd.merge(df_energia_total, df_weather, on=["Año", "Mes", "Día"], how="left", suffixes=('', '_weather'))
                
                if "Mes_Num_weather" in df_panel_final.columns:
                    df_panel_final["Mes_Num"] = df_panel_final["Mes_Num_weather"].fillna(df_panel_final.get("Mes_Num", 1))
                    df_panel_final.drop(columns=[c for c in ["Mes_Num_weather", "Mes_Num_energia"] if c in df_panel_final.columns], inplace=True, errors='ignore')

                df_panel_final["Lluvia"] = df_panel_final["Lluvia"].fillna(0)
                df_panel_final["Nieve"] = df_panel_final["Nieve"].fillna(0)
                df_panel_final["Temp_Max"] = df_panel_final["Temp_Max"].fillna(0)
                df_panel_final["Temp_Min"] = df_panel_final["Temp_Min"].fillna(0)
                df_panel_final["Temp_Media"] = df_panel_final["Temp_Media"].fillna(0)
                df_panel_final["Horas_Sol"] = df_panel_final["Horas_Sol"].fillna(0)
                df_panel_final["Horas_Nubes"] = df_panel_final["Horas_Nubes"].fillna(0)
                df_panel_final["Viento"] = df_panel_final["Viento"].fillna(0)
                df_panel_final["Clima_Texto"] = df_panel_final["Clima_Texto"].fillna("☁ Nublado")
                df_panel_final["Icono"] = df_panel_final["Icono"].fillna("☁️")
                
                if "Fecha" in df_panel_final.columns:
                    df_panel_final["Fecha"] = df_panel_final["Fecha"].fillna(
                        df_panel_final["Año"].astype(str) + "." + 
                        df_panel_final["Mes_Num"].astype(str).str.zfill(2) + "." + 
                        df_panel_final["Día"].astype(str).str.zfill(2)
                    )
                
                df_panel_final = df_panel_final.sort_values(["Año", "Mes_Num", "Día"])

                dias_unicos_clima = df_panel_final[["Fecha", "Año", "Mes_Num", "Mes", "Día", "Clima_Texto", "Icono", "Temp_Max", "Temp_Min", "Temp_Media", "Horas_Sol", "Horas_Nubes", "Viento", "Lluvia", "Nieve"]].drop_duplicates().sort_values(["Año", "Mes_Num", "Día"]).reset_index(drop=True)
                dias_unicos_clima["Secuencia_X"] = dias_unicos_clima.index

                df_panel_final = df_panel_final.merge(dias_unicos_clima[["Año", "Mes_Num", "Mes", "Día", "Secuencia_X"]], on=["Año", "Mes_Num", "Mes", "Día"], how="left", suffixes=('', '_dup'))
                df_panel_final = df_panel_final.loc[:, ~df_panel_final.columns.str.endswith('_dup')]

                fig_clima = go.Figure()

                df_pivot = df_panel_final.pivot_table(
                    index=["Secuencia_X", "Fecha", "Año", "Mes", "Día", "Clima_Texto", "Lluvia", "Nieve", "Temp_Max", "Temp_Min", "Icono"],
                    columns="Tipo",
                    values="Valor"
                ).reset_index()

                if "Produced" not in df_pivot.columns:
                    df_pivot["Produced"] = 0
                if "Consumed" not in df_pivot.columns:
                    df_pivot["Consumed"] = 0
                df_pivot["Produced"] = df_pivot["Produced"].fillna(0)
                df_pivot["Consumed"] = df_pivot["Consumed"].fillna(0)

                customdata_arr = df_pivot[["Fecha", "Produced", "Consumed", "Lluvia", "Nieve", "Temp_Max", "Temp_Min"]].values.tolist()

                fig_clima.add_trace(go.Scatter(
                    x=df_pivot["Secuencia_X"],
                    y=df_pivot["Produced"],
                    mode="lines+markers",
                    name="Produced",
                    line=dict(width=2, color="#F1C40F"),
                    marker=dict(color="#F1C40F", size=6),
                    customdata=customdata_arr,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "🟡 Produced: %{customdata[1]:.2f} kWh<br>"
                        "🔵 Consumed: %{customdata[2]:.2f} kWh<br>"
                        "🌧️ Lluvia: %{customdata[3]:.1f} mm | ❄️ Nieve: %{customdata[4]:.1f} cm<br>"
                        "🌡 Máx: %{customdata[5]:.1f} °C | Mín: %{customdata[6]:.1f} °C<extra></extra>"
                    )
                ))

                fig_clima.add_trace(go.Scatter(
                    x=df_pivot["Secuencia_X"],
                    y=df_pivot["Consumed"],
                    mode="lines+markers",
                    name="Consumed",
                    line=dict(width=2, color="#3B82F6"),
                    marker=dict(color="#3B82F6", size=6),
                    customdata=customdata_arr,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "🟡 Produced: %{customdata[1]:.2f} kWh<br>"
                        "🔵 Consumed: %{customdata[2]:.2f} kWh<br>"
                        "🌧️ Lluvia: %{customdata[3]:.1f} mm | ❄️ Nieve: %{customdata[4]:.1f} cm<br>"
                        "🌡️ Máx: %{customdata[5]:.1f} °C | Mín: %{customdata[6]:.1f} °C<extra></extra>"
                    )
                ))

                if len(meses_sel) <= 2:
                    paso_iconos = 1
                elif len(meses_sel) > 5:
                    paso_iconos = 5
                else:
                    paso_iconos = 3
                    
                df_iconos_filtrados = dias_unicos_clima.iloc[::paso_iconos].copy()
                max_y_val = df_panel_final["Valor"].max() if not df_panel_final["Valor"].empty else 100

                fig_clima.add_trace(go.Scatter(
                    x=df_iconos_filtrados["Secuencia_X"],
                    y=[max_y_val * 1.08] * len(df_iconos_filtrados),
                    mode="text",
                    text=df_iconos_filtrados["Icono"],
                    textfont=dict(size=14),
                    showlegend=False,
                    hoverinfo="skip"
                ))

                tickvals = []
                ticktext = []
                meses_cambio_indices = []
                meses_procesados = set()

                for _, row in dias_unicos_clima.iterrows():
                    sec_x = row["Secuencia_X"]
                    mes = row["Mes"]
                    dia = row["Día"]
                    
                    if (row["Año"], mes) not in meses_procesados:
                        meses_cambio_indices.append(sec_x)
                        meses_procesados.add((row["Año"], mes))

                    if dia in [1, 15]:
                        tickvals.append(sec_x)
                        ticktext.append(f"{mes} {dia}")

                fig_clima.update_layout(
                    plot_bgcolor="#f4f4f4",
                    paper_bgcolor="#f4f4f4",
                    font_color="#222",
                    height=580,
                    title=f"    Producción y Consumo Total vs Meteo en:   <i>{nombre_loc}</i>",
                    xaxis=dict(
                        title="Fecha",
                        tickmode="array",
                        tickvals=tickvals,
                        ticktext=ticktext,
                        tickangle=-45,
                        showgrid=True,
                        gridcolor="rgba(0,0,0,0.08)",
                        zeroline=False
                    ),
                    yaxis=dict(
                        title="kWh",
                        range=[0, max_y_val * 1.18]
                    )
                )

                for idx_mes in meses_cambio_indices:
                    fig_clima.add_vline(
                        x=idx_mes,
                        line_width=1,
                        line_dash="dash",
                        line_color="rgba(0, 0, 0, 0.15)"
                    )
                for idx_icono in df_iconos_filtrados["Secuencia_X"]:
                    fig_clima.add_vline(
                        x=idx_icono,
                        line_width=1,
                        line_dash="dot",
                        line_color="rgba(0, 0, 0, 0.10)"
                    )

                st.plotly_chart(fig_clima, use_container_width=True)
                
                # =========================================================
                # TABLA DETALLADA DE CLIMA Y ENERGÍA
                # =========================================================
                st.markdown("---")
                st.subheader("📋 Detalle Meteorológico y Energético Diario")

                df_tabla_final = pd.merge(
                    dias_unicos_clima[["Fecha", "Secuencia_X", "Clima_Texto", "Temp_Max", "Temp_Min", "Horas_Sol", "Horas_Nubes", "Viento", "Lluvia", "Nieve"]],
                    df_pivot[["Secuencia_X", "Produced", "Consumed"]],
                    on="Secuencia_X",
                    how="left"
                )

                df_tabla_final = df_tabla_final[[
                    "Fecha", "Produced", "Consumed", "Clima_Texto", "Temp_Max", "Temp_Min", 
                    "Horas_Sol", "Horas_Nubes", "Viento", "Lluvia", "Nieve"
                ]].copy()

                df_tabla_final.columns = [
                    "Fecha", "Producción", "Consumo", "Nubosidad", "Temp Max", "Temp Min", 
                    "Horas de sol", "Horas Nublado", "Viento", "Lluvia", "Nieve"
                ]

                df_tabla_final["Producción"] = df_tabla_final["Producción"].fillna(0).round(2)
                df_tabla_final["Consumo"] = df_tabla_final["Consumo"].fillna(0).round(2)

                st.dataframe(
                    df_tabla_final,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Fecha": st.column_config.TextColumn("Fecha", width="medium"),
                        "Producción": st.column_config.NumberColumn("Producción", format="%.2f kWh"),
                        "Consumo": st.column_config.NumberColumn("Consumo", format="%.2f kWh"),
                        "Nubosidad": st.column_config.TextColumn("Nubosidad", width="medium"),
                        "Temp Max": st.column_config.NumberColumn("Temp Max", format="%.1f °C"),
                        "Temp Min": st.column_config.NumberColumn("Temp Min", format="%.1f °C"),
                        "Horas de sol": st.column_config.NumberColumn("Horas de sol", format="%.1f h"),
                        "Horas Nublado": st.column_config.NumberColumn("Horas Nublado", format="%.1f h"),
                        "Viento": st.column_config.NumberColumn("Viento", format="%.1f km/h"),
                        "Lluvia": st.column_config.NumberColumn("Lluvia", format="%.1f mm"),
                        "Nieve": st.column_config.NumberColumn("Nieve", format="%.1f cm")
                    }
                )

            # =========================================================
            # 🗓️ 1er HEATMAP: CALENDAR HEATMAP DE PRODUCCIÓN SOLAR
            # =========================================================
            st.markdown("---")
            st.subheader("🔥 Heatmap Estacional de Producción Solar")
            st.markdown("*Matriz de calor que representa la generación diaria de energía (kWh) a lo largo del año por cada año seleccionado.*")

            df_heat_data = df_long[
                (df_long["Año"].isin(años_sel)) & 
                (df_long["Tipo"] == "Produced")
            ].copy()

            if not df_heat_data.empty:
                df_heat_data["Mes_Num_H"] = df_heat_data["Mes"].map(lambda m: orden_meses.index(m) + 1 if m in orden_meses else 1)
                df_heat_data["Fecha_Format"] = (
                    df_heat_data["Día"].astype(str).str.zfill(2) + "." + 
                    df_heat_data["Mes_Num_H"].astype(str).str.zfill(2) + "." + 
                    df_heat_data["Año"].astype(str)
                )

                # Creamos una clave combinada Año - Mes y ordenamos los años de más reciente a más antiguo
                df_heat_data["Año_Mes"] = df_heat_data["Año"].astype(str) + " - " + df_heat_data["Mes"].astype(str)
                anios_ordenados = sorted(años_sel, reverse=True)
                index_esperado = [f"{a} - {m}" for a in anios_ordenados for m in orden_meses]

                pivot_heat = df_heat_data.pivot_table(
                    index="Año_Mes",
                    columns="Día",
                    values="Valor",
                    aggfunc="sum"
                ).reindex(index_esperado)

                pivot_fechas = df_heat_data.pivot_table(
                    index="Año_Mes",
                    columns="Día",
                    values="Fecha_Format",
                    aggfunc="first"
                ).reindex(index_esperado).fillna("")

                fig_cal_heat = go.Figure(go.Heatmap(
                    z=pivot_heat.values,
                    x=pivot_heat.columns,
                    y=pivot_heat.index,
                    colorscale="YlOrRd",
                    customdata=pivot_fechas.values,
                    hovertemplate="<b>Fecha:</b> %{customdata}<br><b>Producción:</b> %{z:.2f} kWh<extra></extra>"
                ))

                fig_cal_heat.update_layout(
                    plot_bgcolor="#f4f4f4",
                    paper_bgcolor="#f4f4f4",
                    font_color="#222",
                    height=max(380, len(index_esperado) * 22),
                    xaxis=dict(title="Día del Mes", dtick=2),
                    yaxis=dict(title="", autorange="reversed")
                )
                st.plotly_chart(fig_cal_heat, use_container_width=True)

            # =========================================================
            # 🗓️ 2do HEATMAP: NUEVO HEATMAP METEOROLÓGICO (Escalas invertidas)
            # =========================================================
            if not df_weather.empty:
                st.markdown("---")
                st.subheader("🌡️ Heatmap Meteorológico Estacional")
                st.markdown("*Matriz de calor interactiva para visualizar las horas de sol o la temperatura media diaria desglosada por años.*")

                metrica_heat = st.radio(
                    "Selecciona la métrica a visualizar en el heatmap:",
                    options=["Horas de luz", "Temperatura media"],
                    horizontal=True,
                    key="selector_metrica_heatmap"
                )

                df_weather["Mes"] = pd.Categorical(df_weather["Mes"], categories=orden_meses, ordered=True)
                df_weather["Fecha_Format"] = (
                    df_weather["Día"].astype(str).str.zfill(2) + "." + 
                    df_weather["Mes_Num"].astype(str).str.zfill(2) + "." + 
                    df_weather["Año"].astype(str)
                )

                df_weather["Año_Mes"] = df_weather["Año"].astype(str) + " - " + df_weather["Mes"].astype(str)
                anios_ordenados = sorted(años_sel, reverse=True)
                index_esperado = [f"{a} - {m}" for a in anios_ordenados for m in orden_meses]

                columna_valor = "Horas_Sol" if metrica_heat == "Horas de luz" else "Temp_Media"
                unidad_medida = "h" if metrica_heat == "Horas de luz" else "°C"
                
                if metrica_heat == "Horas de luz":
                    escala_colores = "YlGnBu_r"
                else:
                    escala_colores = "RdBu_r"
                    
                pivot_meteo_val = df_weather.pivot_table(
                    index="Año_Mes",
                    columns="Día",
                    values=columna_valor,
                    aggfunc="mean"
                ).reindex(index_esperado)

                pivot_meteo_fec = df_weather.pivot_table(
                    index="Año_Mes",
                    columns="Día",
                    values="Fecha_Format",
                    aggfunc="first"
                ).reindex(index_esperado).fillna("")

                fig_meteo_heat = go.Figure(go.Heatmap(
                    z=pivot_meteo_val.values,
                    x=pivot_meteo_val.columns,
                    y=pivot_meteo_val.index,
                    colorscale=escala_colores,
                    customdata=pivot_meteo_fec.values,
                    hovertemplate=f"<b>Fecha:</b> %{{customdata}}<br><b>{metrica_heat}:</b> %{{z:.2f}} {unidad_medida}<extra></extra>"
                ))

                fig_meteo_heat.update_layout(
                    plot_bgcolor="#f4f4f4",
                    paper_bgcolor="#f4f4f4",
                    font_color="#222",
                    height=max(380, len(index_esperado) * 22),
                    xaxis=dict(title="Día del Mes", dtick=2),
                    yaxis=dict(title="", autorange="reversed")
                )
                st.plotly_chart(fig_meteo_heat, use_container_width=True)

        except Exception as e:
            st.warning(f"Error al procesar el panel meteorológico: {e}")
    else:
        st.warning("Selecciona al menos un año y un mes para consultar el panel del clima.")

        
# =========================================================
# 5) 💶 NUEVO TAB: IMPACTO AMBIENTAL & ECONÓMICO
# =========================================================
with tab5:
    st.subheader("🌍 Impacto Ambiental y Económico Estimado")
    st.markdown("*Configura los parámetros económicos y ecológicos mediante los controles deslizantes para calcular el ahorro y la huella de carbono evitada.*")

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        precio_luz = st.slider("Precio Electricidad (€/kWh)", min_value=0.10, max_value=0.60, value=0.3651, step=0.01, format="%.4f €")
    with col_s2:
        cuota_fija = st.slider("Contador Adicional (€/año)", min_value=0.0, max_value=400.0, value=213.60, step=1.0, format="%.2f €")
    with col_s3:
        precio_excedente = st.slider("Precio Excedente (€/kWh)", min_value=0.01, max_value=0.20, value=0.08216, step=0.0005, format="%.5f €")
    with col_s4:
        factor_co2 = st.slider("Factor CO₂ Evitado (kg/kWh)", min_value=0.10, max_value=0.60, value=0.30, step=0.01, format="%.2f kg")

    st.markdown("---")

    total_pro = df_kpi[df_kpi["Tipo"] == "Produced"]["Valor"].sum()
    total_pv_used = df_kpi[df_kpi["Tipo"] == "PV Used"]["Valor"].sum()
    total_to_netz = df_kpi[df_kpi["Tipo"] == "To Netz"]["Valor"].sum()

    co2_evitado_kg = total_pro * factor_co2
    co2_evitado_ton = co2_evitado_kg / 1000.0
    arboles_equivalentes = int(co2_evitado_kg / 22) if co2_evitado_kg > 0 else 0

    # Equivalencias de km en transporte (factores aproximados de kg CO2 por pasajero-km)
    # Coche medio: ~0.17 kg CO2/km | Avión medio: ~0.25 kg CO2/km | Barco Transatlántico: ~0.20 kg CO2/km
    km_coche = int(co2_evitado_kg / 0.17) if co2_evitado_kg > 0 else 0
    km_avion = int(co2_evitado_kg / 0.25) if co2_evitado_kg > 0 else 0
    km_barco = int(co2_evitado_kg / 0.20) if co2_evitado_kg > 0 else 0
    
    ahorro_autoconsumo = total_pv_used * precio_luz
    ingresos_excedentes = total_to_netz * precio_excedente
    meses_activos_ratio = len(meses_sel) / 12.0
    cuota_fija_periodo = cuota_fija * meses_activos_ratio
    ahorro_total_neto = ahorro_autoconsumo + ingresos_excedentes + cuota_fija_periodo

    st.markdown("### 🌳 Resumen de Impacto Ecológico")
    col_env1, col_env2, col_env3 = st.columns(3)
    
    with col_env1:
        texto_km_equivalentes = (
            f"🚗 Coche: {km_coche:,} km<br>"
            f"✈️ Avión: {km_avion:,} km<br>"
            f"🚢 Barco: {km_barco:,} km"
        ).replace(",", ".")
        st.markdown(
            f"""
            <div style="background-color: rgba(128, 128, 128, 0.05); padding: 8px 12px; border-radius: 8px;">
                <div style="font-size: 0.85rem !important; font-weight: 700 !important; margin-bottom: 4px;"><b>km equivalentes</b></div>
                <div style="font-size: 0.9rem !important; font-weight: 400 !important; line-height: 1.5;">{texto_km_equivalentes}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col_env2:
        st.markdown(
            f"""
            <div style="background-color: rgba(128, 128, 128, 0.05); padding: 8px 12px; border-radius: 8px;">
                <div style="font-size: 0.85rem !important; font-weight: 700 !important; margin-bottom: 4px;"><b>CO₂ Evitado (Total)</b></div>
                <div style="font-size: 0.9rem !important; font-weight: 400 !important; line-height: 1.5;">{f"{co2_evitado_ton:,.3f} t".replace(",", ".")}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_env3:
        st.markdown(
            f"""
            <div style="background-color: rgba(128, 128, 128, 0.05); padding: 8px 12px; border-radius: 8px;">
                <div style="font-size: 0.85rem !important; font-weight: 700 !important; margin-bottom: 4px;"><b>Equivalente en Árboles</b></div>
                <div style="font-size: 0.9rem !important; font-weight: 400 !important; line-height: 1.5;">{f"{arboles_equivalentes:,} árboles/año".replace(",", ".")}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("### 💰 Resumen Financiero y Ahorro Estimado")
    col_fin1, col_fin2, col_fin3, col_fin4 = st.columns(4)
    with col_fin1:
        st.metric("Ahorro por Autoconsumo", f"{ahorro_autoconsumo:,.2f} €".replace(",", "."))
    with col_fin2:
        st.metric("Ingresos por Excedentes", f"{ingresos_excedentes:,.2f} €".replace(",", "."))
    with col_fin3:
        st.metric("Ahorro Bruto Estimado", f"{ahorro_total_neto:,.2f} €".replace(",", "."))
    with col_fin4:
        st.metric("Cuota Fija (Prorrateada)", f"{cuota_fija_periodo:,.2f} €".replace(",", "."))

    st.markdown("---")

    # Construcción de datos para la gráfica de barras apiladas por año
    datos_financieros_anuales = []
    for anio in años_disponibles:
        if anio in años_sel:
            df_anio_kpi = df_long[
                (df_long["Año"] == anio) & 
                (df_long["Mes"].isin(meses_sel)) & 
                (df_long["Día"] >= rango_dias[0]) & 
                (df_long["Día"] <= rango_dias[1])
            ]
            pv_used_anio = df_anio_kpi[df_anio_kpi["Tipo"] == "PV Used"]["Valor"].sum()
            to_netz_anio = df_anio_kpi[df_anio_kpi["Tipo"] == "To Netz"]["Valor"].sum()
            
            ahorro_ac_anio = pv_used_anio * precio_luz
            ingresos_ex_anio = to_netz_anio * precio_excedente
            cuota_fija_anio = cuota_fija * (len(meses_sel) / 12.0)
        else:
            ahorro_ac_anio = 0.0
            ingresos_ex_anio = 0.0
            cuota_fija_anio = 0.0

        datos_financieros_anuales.append({
            "Año": str(anio),
            "Concepto": "Autoconsumo",
            "Euros": ahorro_ac_anio
        })
        datos_financieros_anuales.append({
            "Año": str(anio),
            "Concepto": "Cuota Fija",
            "Euros": cuota_fija_anio
        })
        datos_financieros_anuales.append({
            "Año": str(anio),
            "Concepto": "Excedente",
            "Euros": ingresos_ex_anio
        })

    df_financiero_anual = pd.DataFrame(datos_financieros_anuales)

    fig_fin = px.bar(
        df_financiero_anual,
        x="Año",
        y="Euros",
        color="Concepto",
        barmode="stack",
        color_discrete_sequence=["#00C268", "#F39C12", "#3498DB"],
        title="Desglose del Beneficio Económico por Año (Periodo Seleccionado)",
        custom_data=["Concepto"]
    )
    
    # Formato del hover personalizado: Concepto en negrita, valor con dos decimales y sin año
    fig_fin.update_traces(
        texttemplate='%{y:,.2f} €', 
        textposition='inside',
        hovertemplate="<b>%{customdata[0]}</b><br>%{y:,.2f} €<extra></extra>"
    )
    
    fig_fin.update_layout(
        plot_bgcolor="#f4f4f4", paper_bgcolor="#f4f4f4", font_color="#222",
        height=450, xaxis=dict(title="Año", type='category'), yaxis=dict(title="Euros (€)")
    )
    st.plotly_chart(fig_fin, use_container_width=True)


    # =========================================================
    # CASHFLOW ACUMULADO Y PREVISIÓN A 10 AÑOS
    # =========================================================
    st.markdown("---")
    st.subheader("📈 Cashflow Acumulado y Previsión a 10 Años")
    st.markdown("*Análisis financiero evolutivo desde 2022 incluyendo inversión inicial y proyección a futuro.*")

    col_grafica, col_controles = st.columns([0.7, 0.3])

    with col_controles:
        st.markdown("#### ⚙️ Parámetros Cashflow")
        inversion_inicial = st.number_input("Inversión Inicial (€)", min_value=0.0, max_value=30000.0, value=8600.0, step=200.0, format="%.2f")
        precio_luz_futuro = st.slider("Precio Luz Futuro (≥ 2028) (€/kWh)", min_value=0.10, max_value=0.60, value=0.3651, step=0.01, format="%.4f €")
        cuota_fija_futuro = st.slider("Cuota Fija Futura (≥ 2028) (€/año)", min_value=0.0, max_value=400.0, value=213.60, step=1.0, format="%.2f €")

    # 1. Obtener rendimiento anual base del último año disponible para las proyecciones futuras
    ultimo_anio_disponible = int(df_long["Año"].max())
    
    df_ultimo_anio = df_long[df_long["Año"] == ultimo_anio_disponible]
    pv_used_base = df_ultimo_anio[df_ultimo_anio["Tipo"] == "PV Used"]["Valor"].sum()
    to_netz_base = df_ultimo_anio[df_ultimo_anio["Tipo"] == "To Netz"]["Valor"].sum()

    # 2. Rango de años de simulación: desde 2022 (inversión) hasta 10 años después del último disponible
    anio_fin_prevision = max(2033, ultimo_anio_disponible + 10)
    anos_cashflow = list(range(2022, anio_fin_prevision + 1))

    cashflow_acumulado = -inversion_inicial
    datos_cashflow = []

    for anio in anos_cashflow:
        if anio == 2022:
            ahorro_ac = 0.0
            c_fija = 0.0
            ingresos_ex = 0.0
        else:
            if anio <= ultimo_anio_disponible:
                df_a = df_long[df_long["Año"] == anio]
                
                # --- EXTRAPOLACIÓN AUTOMÁTICA DE MESES FALTANTES ---
                meses_presentes = set(df_a["Mes"].unique()) if not df_a.empty else set()
                meses_faltantes = [m for m in orden_meses if m not in meses_presentes]
                
                if meses_faltantes and anio > min(anos_cashflow):
                    # Si faltan meses, buscamos los datos del año anterior para esos mismos meses
                    df_anterior = df_long[df_long["Año"] == (anio - 1)]
                    df_faltantes = df_anterior[df_anterior["Mes"].isin(meses_faltantes)]
                    
                    # Sumamos lo real del año actual + lo extrapolado del año anterior
                    pv_u = df_a[df_a["Tipo"] == "PV Used"]["Valor"].sum() + df_faltantes[df_faltantes["Tipo"] == "PV Used"]["Valor"].sum()
                    to_n = df_a[df_a["Tipo"] == "To Netz"]["Valor"].sum() + df_faltantes[df_faltantes["Tipo"] == "To Netz"]["Valor"].sum()
                else:
                    # Si el año está completo, usamos sus datos reales directamente
                    pv_u = df_a[df_a["Tipo"] == "PV Used"]["Valor"].sum()
                    to_n = df_a[df_a["Tipo"] == "To Netz"]["Valor"].sum()
                
                p_luz = precio_luz
                c_fija = cuota_fija
            else:
                # Años futuros (proyecciones a 10 años)
                pv_u = pv_used_base
                to_n = to_netz_base
                p_luz = precio_luz_futuro if anio >= 2028 else precio_luz
                c_fija = cuota_fija_futuro if anio >= 2028 else cuota_fija

            ahorro_ac = pv_u * p_luz
            ingresos_ex = to_n * precio_excedente
            ahorro_total_anual = ahorro_ac + c_fija + ingresos_ex

            # Acumulamos sumando el ahorro anual al saldo anterior
            cashflow_acumulado += ahorro_total_anual

        datos_cashflow.append({
            "Año": str(anio),
            "Cashflow Acumulado": cashflow_acumulado,
            "Autoconsumo": ahorro_ac if anio != 2022 else 0.0,
            "Cuota Fija": c_fija if anio != 2022 else 0.0,
            "Excedente": ingresos_ex if anio != 2022 else 0.0,
            "Estado": "Negativo" if cashflow_acumulado < 0 else "Positivo"
        })

    df_cf = pd.DataFrame(datos_cashflow)

    with col_grafica:
        fig_cf = px.bar(
            df_cf,
            x="Año",
            y="Cashflow Acumulado",
            text="Cashflow Acumulado",
            color="Estado",
            color_discrete_map={"Negativo": "#E74C3C", "Positivo": "#3498DB"},
            title="Evolución del Cashflow Acumulado y Previsión a 10 Años (Inv. 2022)",
            custom_data=["Autoconsumo", "Cuota Fija", "Excedente"]
        )

        fig_cf.update_traces(
            texttemplate='%{y:,.2f} €', 
            textposition='outside',
            hovertemplate=(
                "<b>Año: %{x}</b><br>"
                "Cashflow Acumulado: %{y:,.2f} €<br><br>"
                "<b>Ahorro del año:</b><br>"
                "• Autoconsumo: %{customdata[0]:,.2f} €<br>"
                "• Cuota Fija: %{customdata[1]:,.2f} €<br>"
                "• Excedente: %{customdata[2]:,.2f} €<extra></extra>"
            )
        )

        fig_cf.update_layout(
            plot_bgcolor="#f4f4f4", 
            paper_bgcolor="#f4f4f4", 
            font_color="#222",
            height=480, 
            xaxis=dict(title="Año", type='category'), 
            yaxis=dict(title="Euros Acumulados (€)"),
            showlegend=False,
            hoverlabel=dict(
                align="left"  # 👈 Esto fuerza globalmente que el texto del hover esté alineado a la izquierda en todas las barras
            )
        )

        st.plotly_chart(fig_cf, use_container_width=True)

    
# =========================================================
# 6) 📄 TABLA DE DATOS
# =========================================================
with tab6:
    st.subheader("📄 Tabla de Datos")

    tabla_wide = df_filtrado.pivot_table(
        index=["Año", "Mes", "Tipo"],
        columns="Día",
        values="Valor"
    ).reset_index()

    # Ordenar por Año de mayor a menor y por Mes de mayor a menor (inverso al orden_meses)
    tabla_wide["Mes_Num"] = tabla_wide["Mes"].map(lambda m: orden_meses.index(m) if m in orden_meses else 0)
    tabla_wide = tabla_wide.sort_values(by=["Año", "Mes_Num"], ascending=[False, False]).drop(columns=["Mes_Num"])

    # Identificamos las columnas de los días originales (números)
    dias_cols_originales = [c for c in tabla_wide.columns if c not in ["Año", "Mes", "Tipo"]]

    # Renombramos las columnas de los días al formato "Day 01", "Day 02", etc.
    rename_mapping = {c: f"Day {str(c).zfill(2)}" for c in dias_cols_originales}
    tabla_wide = tabla_wide.rename(columns=rename_mapping)
    dias_cols = list(rename_mapping.values())

    # ⚠️ IMPORTANTE: Mantenemos los valores como números (floats) para que el ordenamiento 
    # de Streamlit funcione de forma numérica. Los valores nulos se quedan como NaN automáticamente.

    # Construimos el column_config dinámicamente para formatear los días con " kWh" manteniendo la propiedad numérica
    column_config_tabla = {
        "Año": st.column_config.NumberColumn("Año", format="%d"),
        "Mes": "Mes",
        "Tipo": "Tipo"
    }
    for col in dias_cols:
        column_config_tabla[col] = st.column_config.NumberColumn(
            col,
            format="%.2f kWh"
        )

    # 12 colores pasteles suaves y diferentes para cada uno de los 12 meses
    rgb_meses = {
        "Jan": (235, 243, 250), # Azul hielo suave
        "Feb": (232, 246, 243), # Menta suave
        "Mar": (235, 247, 238), # Verde claro suave
        "Avr": (245, 249, 233), # Lima suave
        "Mai": (254, 250, 231), # Amarillo crema suave
        "Jun": (253, 242, 233), # Durazno suave
        "Jul": (253, 238, 238), # Coral suave
        "Aug": (250, 238, 245), # Rosa suave
        "Sep": (242, 239, 250), # Lavanda suave
        "Okt": (238, 242, 252), # Violeta claro suave
        "Nov": (243, 240, 238), # Topo / Gris cálido suave
        "Dez": (230, 240, 248)  # Azul acero suave
    }
    
    # Ajuste muy sutil de tono por tipo para generar un degradado ordenado
    ajuste_tipo = {
        "Produced": 0,
        "Consumed": -4,
        "PV Used": -8,
        "To Netz": -12,
        "From Netz": -16
    }

    def estilizar_tabla(df):
        def estilizar_fila(row):
            mes = row["Mes"]
            tipo = row["Tipo"]
            rgb = rgb_meses.get(mes, (245, 245, 245))
            ajuste = ajuste_tipo.get(tipo, 0)
            
            r = max(0, min(255, rgb[0] + ajuste))
            g = max(0, min(255, rgb[1] + ajuste))
            b = max(0, min(255, rgb[2] + ajuste))
            
            return [f"background-color: rgb({r}, {g}, {b})" for _ in row]

        return df.style.apply(estilizar_fila, axis=1)

    # Estilo CSS para forzar las cabeceras de la tabla en negrita y color negro
    st.markdown("""
    <style>
    [data-testid="stDataFrame"] th {
        color: #000000 !important;
        font-weight: 700 !important;
        background-color: #eaecef !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Mostramos la tabla aplicando los estilos y la configuración de columnas numéricas
    st.dataframe(
        estilizar_tabla(tabla_wide), 
        hide_index=True,
        column_config=column_config_tabla
    )
    
# =========================================================
# 7) ℹ️ RESOURCES / INFO
# =========================================================
with tab7:
    st.markdown("""
    ### ℹ️ About Dashboard Solar App
    * **Script by:** dJoZeR - Ingolstadt, 2026
    * **Created with the help of:** Copilot and Gemini

    ---

    ### 📋 Estructura requerida del fichero Excel (`.xlsx`)
    Para que el script pueda procesar e interpretar los datos correctamente, el archivo Excel debe cumplir con el siguiente formato de tabla (formato *wide*):

    1. **Estructura de las tres primeras columnas (Cabeceras):**
       * **Columna 1:** Debe contener el **Año** (ej. `2025`, `2026`).
       * **Columna 2:** Debe contener el **Mes** utilizando abreviaturas en inglés/alemán correspondientes exactamente a esta lista: `Jan`, `Feb`, `Mar`, `Avr`, `Mai`, `Jun`, `Jul`, `Aug`, `Sep`, `Okt`, `Nov`, `Dez`.
       * **Columna 3:** Debe contener el **Tipo de métrica energética**. El script traducirá automáticamente las siguientes abreviaturas internas:
         * `Pro` → Convertido a **Produced** (Producción)
         * `Con` → Convertido a **Consumed** (Consumo)
         * `PV_used` → Convertido a **PV Used** (Autoconsumo directo)
         * `to_netz` → Convertido a **To Netz** (Excedentes vertidos a la red)
         * `from_netz` → Convertido a **From Netz** (Electricidad comprada de la red)

    2. **Estructura de los días del mes (Columnas 4 en adelante):**
       * A partir de la cuarta columna, cada cabecera debe representar un **día del mes** (números enteros del `1` al `31`).
       * Las celdas correspondientes deben contener el valor numérico en **kWh** medido para ese día, mes, año y tipo de registro.

    > **Nota:** Los días que no existan en meses más cortos (ej. el 30 o 31 de febrero) simplemente se pueden dejar vacíos o sin definir, ya que el script elimina automáticamente los valores nulos (`dropna`).
    
    ---

    ### 🌤️ Información sobre la API de Open-Meteo y Variables Utilizadas
    La pestaña **"🌤 Paneles y Clima"** se conecta en tiempo de ejecución a la **API Archive de Open-Meteo** para correlacionar la producción y consumo energético con las condiciones meteorológicas reales registradas en **Ingolstadt** (Alemania).

    #### 1. Endpoint y URL de la Petición
    Se utiliza el servicio histórico de Open-Meteo mediante peticiones HTTP `GET`:
    ```text
    [https://archive-api.open-meteo.com/v1/archive?latitude=48.7657&longitude=11.4231&start_date=...&end_date=...&daily=weathercode,precipitation_sum,snowfall_sum,temperature_2m_max,temperature_2m_min,sunshine_duration,windspeed_10m_max&timezone=Europe/Berlin](https://archive-api.open-meteo.com/v1/archive?latitude=48.7657&longitude=11.4231&start_date=...&end_date=...&daily=weathercode,precipitation_sum,snowfall_sum,temperature_2m_max,temperature_2m_min,sunshine_duration,windspeed_10m_max&timezone=Europe/Berlin)
    ```

    #### 2. Parámetros de Coordenadas y Configuración
    * **`latitude` y `longitude`**: Coordenadas geográficas fijas de Ingolstadt (`48.7657`, `11.4231`).
    * **`start_date` y `end_date`**: Rango de fechas dinámico calculado automáticamente en función de los años seleccionados en los filtros de la barra lateral (desde el 1 de enero del año inicial hasta el 31 de diciembre o la fecha actual del año en curso).
    * **`timezone`**: Configurado en `Europe/Berlin` para alinear correctamente los registros diarios con la zona horaria local.

    #### 3. Variables Meteorológicas Solicitadas (`daily`)
    La API devuelve un conjunto de métricas diarias que el script procesa y transforma:
    * **`weathercode`**: Código de condición meteorológica (WMO Weather interpretation codes). Se utiliza para clasificar y renderizar los iconos y textos descriptivos (*☀️ Soleado, ⛅ Parcialmente nublado, ☁️ Cubierto, 🌧️ Lluvioso, ❄️ Nevado*).
    * **`sunshine_duration`**: Duración de la insolación expresada en segundos. El script la divide entre `3600` para transformarla en **Horas de Sol** netas (`Horas_Sol`) y calcula de forma complementaria las **Horas de Nubes** estimadas.
    * **`temperature_2m_max` / `temperature_2m_min`**: Temperaturas máximas y mínimas diarias registradas a 2 metros de altura (en **°C**).
    * **`precipitation_sum`**: Precipitación total acumulada en forma de lluvia (en **mm**).
    * **`snowfall_sum`**: Nevadas acumuladas convertidas o medidas (en **cm**).
    * **`windspeed_10m_max`**: Velocidad máxima del viento a 10 metros de altura (en **km/h**).

    ---
    """)

# =========================================================
# 8) 📖 MANUAL DE USUARIO
# =========================================================
with tab8:
    st.markdown("## 📖 Manual de Usuario")
    st.markdown(
        "Bienvenido al manual de usuario oficial del Dashboard de Energía Solar y Análisis Financiero. "
        "Esta guía detalla el modelo de datos, la integración meteorológica en tiempo real y explica de forma exhaustiva "
        "el funcionamiento, controles y gráficas de cada una de las pestañas del sistema."
    )
    
    st.divider()

    # --- SECCIÓN 1: FUNDAMENTOS FOTOVOLTAICOS Y ENERGÉTICOS ---
    st.markdown("### ☀️ ¿Cómo funciona el Análisis Solar y el Cashflow en la App?")
    
    col_t1, col_t2 = st.columns([1.2, 1])
    
    with col_t1:
        st.markdown("""
        * **La Producción y el Autoconsumo:** El sistema procesa registros en formato ancho y largo para correlacionar la energía generada por los paneles fotovoltaicos (`Produced`) frente a la energía consumida (`Consumed`) y exportada a la red (`To Netz`). 
          * *PV Used:* Representa el autoconsumo directo de la energía limpia generada.
          * *To Netz:* Excedentes vertidos a la red eléctrica remunerados mediante el precio de compensación.
        * **¿Qué es el Cashflow Acumulado y la Previsión?:** El modelo financiero evalúa la rentabilidad a largo plazo partiendo de una **Inversión Inicial en 2022** (con valor base ajustable de `-8.600,00 €`). 
          * A partir de 2023, la aplicación resta año a año el ahorro neto total (autoconsumo + cuota fija del contador + excedentes) a la inversión inicial.
          * Permite proyectar el flujo de caja hasta 10 años más allá del último registro disponible, aplicando nuevos precios de la luz y cuotas fijas configurables a partir de 2028.
        """)
        
    with col_t2:
        st.markdown(
            """
            <div style="background: #f0f2f6; padding: 15px; border-radius: 8px; border-left: 4px solid #00C268; font-size: 13px; line-height: 1.5;">
                <b>💡 Clave Financiera y Ecológica:</b><br>
                El sistema combina la evolución económica con el impacto ambiental cuantificado:
                <br><br>
                1. <b>Equivalencia de Transporte:</b> Transforma los kg de CO₂ evitados en kilómetros equivalentes en coche, avión y barco.<br>
                2. <b>Amortización Progresiva:</b> Muestra visualmente el punto exacto de retorno de inversión mediante barras de saldo negativo (rojo) y positivo (azul).
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # --- SECCIÓN 2: GUÍA POR PESTAÑAS Y GRÁFICAS ---
    st.markdown("### 🗂️ Descripción Funcional por Pestañas")

    tab_m1, tab_m2, tab_m3, tab_m4, tab_m5 = st.tabs([
        "Tab 1: Evolución Diaria", 
        "Tab 2: Evolución Mensual", 
        "Tab 3: Evolución Anual", 
        "Tab 4: Paneles y Clima",
        "Tab 5: Impacto y Cashflow"
    ])
    
    with tab_m1:
        st.markdown("#### 📈 Tab 1 – Evolución Diaria")
        st.markdown("""
        * **Propósito:** Exploración detallada de la producción solar, autoconsumo y exportación a escala diaria.
        * **Componentes principales:**
          * **Filtros Temporales:** Selectores multianuales, de meses (`Jan` a `Dez`) y rango deslizante de días del mes.
          * **Tarjetas KPI (Métricas):** Resumen de energía producida, autoconsumida, consumida de la red y vertida.
          * **Gráfica Diaria:** Línea temporal interactiva que contrasta la generación fotovoltaica con los hábitos de consumo día a día.
        """)

    with tab_m2:
        st.markdown("#### 📊 Tab 2 – Evolución Mensual")
        st.markdown("""
        * **Propósito:** Análisis estacional de la energía generada y consumida agrupada por meses.
        * **Componentes principales:**
          * **Gráfica de Barras Mensuales:** Permite evaluar el comportamiento de los paneles a lo largo de las distintas estaciones del año.
          * **Comparativa de Rendimiento:** Contraste directo entre los volúmenes de autoconsumo y excedentes mes a mes.
        """)
        
    with tab_m3:
        st.markdown("#### 📈 Tab 3 – Evolución Anual")
        st.markdown("""
        * **Propósito:** Evaluar el rendimiento macroscópico de la instalación fotovoltaica a escala plurianual.
        * **Gráficas y Controles:**
          * **Comparativa Anual de Métricas:** Barras agrupadas por año para contrastar volúmenes totales de producción y consumo.
          * **Grado de Autoconsumo y Autarquía:** Indicadores porcentuales clave que miden la eficiencia de aprovechamiento energético de la planta solar frente a la dependencia de la red eléctrica convencional.
        """)

    with tab_m4:
        st.markdown("#### 🌤️ Tab 4 – Paneles y Clima")
        st.markdown("""
        * **Propósito:** Fusionar el rendimiento energético de los paneles con las condiciones meteorológicas reales e históricas mediante la API de Open-Meteo.
        * **Características:**
          * **Buscador de Ubicación Global:** Caja de texto libre para consultar ciudades o códigos postales del mundo (por defecto *Ingolstadt*).
          * **Gráfica Clima vs Energía:** Curvas de producción/consumo combinadas con iconos meteorológicos (☀️, ⛅, ☁️, 🌧️, ❄️, 🌩️, 🌁) y temperaturas extremas.
          * **Tabla Detallada Diaria:** Registro tabulado con horas de sol, viento, lluvia y nieve.
          * **Heatmaps Estacionales:** Dos matrices de calor con Enero arriba y Diciembre abajo:
            1. *Producción Solar:* Formato de fecha `DD.MM.YYYY` en el hover.
            2. *Meteorología:* Selector interactivo entre **Horas de luz** (escala `YlGnBu_r`, donde más luz es más claro) y **Temperatura media** (`RdBu_r`, con azules/morados para frío y cálidos para calor).

        * **Heatmaps Meteorológicos Estacionales (NUEVO):** 
          * **Matriz de Calor de Producción Solar:** Representa en formato de calendario estacional (con los meses ordenados de Enero a Diciembre y los años en orden descendente) la generación diaria de energía en kWh. Al pasar el cursor (*hover*), muestra la fecha exacta en formato `DD.MM.YYYY` y el valor de producción.
          * **Matriz de Calor Meteorológica:** Permite alternar mediante un selector entre dos métricas clave:
            1. *Horas de luz:* Visualiza la duración de la insolación diaria utilizando una escala de colores optimizada (`YlGnBu_r`).
            2. *Temperatura media:* Muestra la temperatura media diaria registrada (`Temp_Media`) utilizando una escala térmica divergente (`RdBu_r`, donde los tonos fríos representan bajas temperaturas y los cálidos el calor estival).
        """)

    with tab_m5:
        st.markdown("#### 🌍 Tab 5 – Impacto Ambiental y Económico")
        st.markdown("""
        * **Propósito:** Cuantificar el ahorro económico, la reducción de emisiones de CO₂ y proyectar el flujo de caja a largo plazo.
        * **Componentes:**
          * **Sliders de Parámetros:** Ajuste de precio de la electricidad, cuota fija del contador, precio de excedentes y factor de CO₂ evitado.
          * **Resumen Ecológico:** Equivalencias de emisiones en km de transporte (coche, avión, barco) y absorción anual en árboles.
          * **Resumen Financiero:** Autoconsumo, excedentes y cuota fija prorrateada.
          * **Cashflow Acumulado y Previsión a 10 Años (Layout 70% / 30%):** Gráfica de barras verticales que arranca en **2022 con la inversión inicial en negativo (rojo)** y acumula los ahorros netos anuales a partir de 2023. Incluye sliders específicos para tarifas futuras (≥ 2028) y hover detallado con el desglose anual por concepto.
        """)

    st.divider()
    st.success("✨ **Consejo de Navegación:** Los ajustes realizados en los controles deslizantes y selectores globales de las pestañas se actualizan en tiempo real gracias al estado de sesión de Streamlit, manteniendo la coherencia financiera y climática en todo el dashboard.")
