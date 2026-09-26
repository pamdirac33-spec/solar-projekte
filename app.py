import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Solar", layout="wide")

# ---------------------------------------------------------
# ESTILOS CSS PARA REDUCIR EL TAMAÑO DE LOS KPIS
# ---------------------------------------------------------
st.markdown("""
<style>
/* Disminuye el tamaño de la etiqueta/título del KPI */
[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
}

/* Disminuye el tamaño del valor numérico del KPI */
[data-testid="stMetricValue"] {
    font-size: 0.9rem !important;
}

/* Ajusta el margen interno de la tarjeta KPI */
[data-testid="stMetric"] {
    background-color: rgba(128, 128, 128, 0.05);
    padding: 8px 12px;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

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

archivo_subido = st.file_uploader(
    f"Sube tu archivo excel (por defecto, usando {ruta_defecto})",
    type=["xlsx"]
)

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

    años_sel = pills_selector("Años", años_disponibles, default_selected=[2025], key_prefix="anos")
    meses_sel = pills_selector("Meses", meses_disponibles, default_selected=["Jun", "Jul"], key_prefix="meses")
    tipos_sel = pills_selector("Tipos de dato", tipos_disponibles, default_selected=["Produced"], key_prefix="tipos")

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

# Todos los KPIs en una sola fila usando 5 columnas
kpi_cols = st.columns(5)
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

st.markdown("---")

# ---------------------------------------------------------
# PESTAÑAS CON LAS GRÁFICAS (JUSTO DEBAJO DE LOS KPIS)
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Evolución Diaria",
    "🎞 Evolución Mensual",
    "📊 Distribución Mensual",
    "📅 Evolución Anual",
    "📄 Tabla de Datos",
    "ℹ️ Resources/Info"
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
    ]

    if df_filtrado.empty:
        st.warning("Hefe, no hay datos para mostrar!")
        st.stop()
        
    fig = px.line(
        df_filtrado,
        x="Día",
        y="Valor",
        color="Serie",
        line_group="Serie",
        markers=True,
        color_discrete_sequence=px.colors.qualitative.Set1,
        render_mode="svg",
        custom_data=["Año", "Mes", "Tipo"]  # 1. Pasamos los tres campos que necesitamos
    )

    # 2. Diseñamos el hovertemplate combinando los customdata y el valor numérico
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]} - %{customdata[1]}</b><br><b>%{customdata[2]}:</b> %{y:.2f} kWh<extra></extra>"
    )

    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor="#f4f4f4",
        paper_bgcolor="#f4f4f4",
        font_color="#222",
        legend_title_text="Año - Mes - Tipo",
        margin=dict(l=40, r=150, t=60, b=40),
        height=550
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 2) 🎞 EVOLUCIÓN MENSUAL
# =========================================================
with tab2:
    st.subheader("🎞 Evolución Mensual (animación)")

    if df_filtrado.empty:
        st.warning("Hefe, no hay datos para mostrar!")
        st.stop()

    # Preparamos los datos para la animación con una serie estable
    df_anim = df_filtrado.copy()
    df_anim["Serie_Anim"] = df_anim["Año"].astype(str) + " - " + df_anim["Tipo"]

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
        custom_data=["Año", "Mes", "Tipo"]
    )
    
    # 1. Definimos la plantilla de hover exacta que deseas
    mi_hovertemplate = "<b>%{customdata[0]} - %{customdata[1]}</b><br><b>%{customdata[2]}:</b> %{y:.2f} kWh<extra></extra>"

    # 2. Aplicamos el hovertemplate al gráfico principal
    fig_anim_mes.update_traces(hovertemplate=mi_hovertemplate)

    # 3. Forzamos el hovertemplate en CADA fotograma (frame) de la animación para que no se pierda al dar al Play
    if fig_anim_mes.frames:
        for frame in fig_anim_mes.frames:
            for trace_data in frame.data:
                trace_data.hovertemplate = mi_hovertemplate

    fig_anim_mes.update_layout(
        hovermode="x unified",
        plot_bgcolor="#f4f4f4",
        paper_bgcolor="#f4f4f4",
        font_color="#222",
        legend_title_text="Año - Tipo",
        margin=dict(l=40, r=150, t=60, b=40),
        height=550
    )

    st.plotly_chart(fig_anim_mes, use_container_width=True)

# =========================================================
# 3) 📊 DISTRIBUCIÓN MENSUAL (Producción / Consumo)
# =========================================================
with tab3:
    st.subheader("🔆 Producción Mensual — PV Used / To Netz")

    df_prod = df_kpi[df_kpi["Tipo"].isin(["Produced", "PV Used", "To Netz"])]
    df_prod_m = df_prod.groupby(["Año", "Mes", "Tipo"])["Valor"].sum().reset_index()

    dfp = df_prod_m.pivot_table(
        index=["Año", "Mes"],
        columns="Tipo",
        values="Valor",
        fill_value=0
    ).reset_index()

    dfp["Mes"] = pd.Categorical(dfp["Mes"], categories=orden_meses, ordered=True)
    dfp = dfp.sort_values(["Mes", "Año"])

    fig_prod = go.Figure()

    # Paletas por año
    años_unicos = sorted(dfp["Año"].unique())
    colores_produced = ["#F9E79F", "#F7DC6F", "#F4D03F", "#F1C40F"]
    colores_pvused   = ["#D5D8DC", "#A6ACAF", "#7F8C8D", "#566573"]
    colores_tonetz   = ["#85C1E9", "#5DADE2", "#3498DB", "#2E86C1"]

    for idx, año in enumerate(años_unicos):
        df_a = dfp[dfp["Año"] == año]

        c_prod = colores_produced[idx % len(colores_produced)]
        c_pv = colores_pvused[idx % len(colores_pvused)]
        c_net = colores_tonetz[idx % len(colores_tonetz)]

        custom_data_a = [[año, m] for m in df_a["Mes"]]

        # --- PRODUCED ---
        fig_prod.add_bar(
            x=df_a["Mes"],
            y=df_a["Produced"],
            name=f"Produced {año}",
            marker_color=c_prod,
            offsetgroup=f"{año}_prod",
            customdata=custom_data_a,
            hovertemplate=f"<b>%{{customdata[0]}} - %{{customdata[1]}}</b><br><span style='color:{c_prod}'><b>Produced:</b> %{{y:,.2f}} kWh</span><extra></extra>"
        )

        # --- PV USED ---
        fig_prod.add_bar(
            x=df_a["Mes"],
            y=df_a["PV Used"],
            name=f"PV Used {año}",
            marker_color=c_pv,
            offsetgroup=f"{año}_stack",
            customdata=custom_data_a,
            hovertemplate=f"<b>%{{customdata[0]}} - %{{customdata[1]}}</b><br><span style='color:{c_pv}'><b>PV Used:</b> %{{y:,.2f}} kWh</span><extra></extra>"
        )

        # --- TO NETZ ---
        fig_prod.add_bar(
            x=df_a["Mes"],
            y=df_a["To Netz"],
            name=f"To Netz {año}",
            marker_color=c_net,
            offsetgroup=f"{año}_stack",
            customdata=custom_data_a,
            hovertemplate=f"<b>%{{customdata[0]}} - %{{customdata[1]}}</b><br><span style='color:{c_net}'><b>To Netz:</b> %{{y:,.2f}} kWh</span><extra></extra>"
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

    fig_prod.update_layout(
        barmode="relative",
        plot_bgcolor="#f4f4f4",
        paper_bgcolor="#f4f4f4",
        font_color="#222",
        height=550,
        title="Producción Mensual",
        hovermode="closest"
    )

    st.plotly_chart(fig_prod, use_container_width=True)

    # ---------------------------------------------------------
    # ⚡ CONSUMO MENSUAL (CORREGIDA)
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

    dfc["Mes"] = pd.Categorical(dfc["Mes"], categories=orden_meses, ordered=True)
    dfc = dfc.sort_values(["Mes", "Año"])

    fig_con = go.Figure()

    # Paletas por año
    años_unicos = sorted(dfc["Año"].unique())
    colores_consumed = ["#A6ACAF", "#909497", "#7B7D7D", "#626567"]
    colores_pvused   = ["#F9E79F", "#F7DC6F", "#F4D03F", "#F1C40F"]
    colores_fromnetz = ["#85C1E9", "#5DADE2", "#3498DB", "#2E86C1"]

    for idx, año in enumerate(años_unicos):
        df_a = dfc[dfc["Año"] == año]

        c_con = colores_consumed[idx % len(colores_consumed)]
        c_pv = colores_pvused[idx % len(colores_pvused)]
        c_net_from = colores_fromnetz[idx % len(colores_fromnetz)]

        custom_data_a = [[año, m] for m in df_a["Mes"]]

        # --- CONSUMED ---
        fig_con.add_bar(
            x=df_a["Mes"],
            y=df_a["Consumed"],
            name=f"Consumed {año}",
            marker_color=c_con,
            offsetgroup=f"{año}_cons",
            customdata=custom_data_a,
            hovertemplate=f"<b>%{{customdata[0]}} - %{{customdata[1]}}</b><br><span style='color:{c_con}'><b>Consumed:</b> %{{y:,.2f}} kWh</span><extra></extra>"
        )

        # --- PV USED ---
        fig_con.add_bar(
            x=df_a["Mes"],
            y=df_a["PV Used"],
            name=f"PV Used {año}",
            marker_color=c_pv,
            offsetgroup=f"{año}_stack",
            customdata=custom_data_a,
            hovertemplate=f"<b>%{{customdata[0]}} - %{{customdata[1]}}</b><br><span style='color:{c_pv}'><b>PV Used:</b> %{{y:,.2f}} kWh</span><extra></extra>"
        )

        # --- FROM NETZ ---
        fig_con.add_bar(
            x=df_a["Mes"],
            y=df_a["From Netz"],
            name=f"From Netz {año}",
            marker_color=c_net_from,
            offsetgroup=f"{año}_stack",
            customdata=custom_data_a,
            hovertemplate=f"<b>%{{customdata[0]}} - %{{customdata[1]}}</b><br><span style='color:{c_net_from}'><b>From Netz:</b> %{{y:,.2f}} kWh</span><extra></extra>"
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

    fig_con.update_layout(
        barmode="relative",
        plot_bgcolor="#f4f4f4",
        paper_bgcolor="#f4f4f4",
        font_color="#222",
        height=550,
        title="Consumo Mensual",
        hovermode="closest"
    )

    st.plotly_chart(fig_con, use_container_width=True)
    
# =========================================================
# 4) 📅 VISTA ANUAL (Cuadrícula 2x3)
# =========================================================
with tab4:
    st.subheader("📅 Vista Anual")

    df_anual_full = df_long.groupby(["Año", "Tipo"])["Valor"].sum().reset_index()

    # Definimos los colores base que usábamos en el tab3 para mantener coherencia
    colores_map = {
        "Produced": "#F1C40F",   # Amarillo principal
        "Consumed": "#7B7D7D",   # Gris oscuro principal
        "PV Used": "#566573",    # Gris/azulado de apilado
        "To Netz": "#3498DB",    # Azul de red (producción)
        "From Netz": "#5DADE2"   # Azul claro de red (consumo)
    }

    # Fila 1: Producción y derivados
    tipos_fila1 = ["Produced", "PV Used", "To Netz"]
    cols1 = st.columns(3)

    for i, t in enumerate(tipos_fila1):
        with cols1[i]:
            st.markdown(f"#### {t}")
            df_t = df_anual_full[df_anual_full["Tipo"] == t].sort_values("Año")

            x_numeric = list(range(len(df_t)))
            x_labels = df_t["Año"].astype(str).tolist()
            anios_custom = df_t["Año"].tolist()
            color_actual = colores_map.get(t, "#F7DC6F")

            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=x_numeric,
                y=df_t["Valor"],
                marker_color=color_actual,
                width=0.25,
                customdata=anios_custom,
                hovertemplate=f"<b>%{{customdata}}</b><br><span style='color:{color_actual}'><b>{t}:</b> %{{y:,.2f}} kWh</span><extra></extra>"
            ))

            fig.add_trace(go.Scatter(
                x=x_numeric,
                y=df_t["Valor"],
                mode="lines+markers",
                line=dict(color=color_actual, width=2),
                marker=dict(size=5),
                customdata=anios_custom,
                hovertemplate=f"<b>%{{customdata}}</b><br><span style='color:{color_actual}'><b>{t}:</b> %{{y:,.2f}} kWh</span><extra></extra>"
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
                yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.15)", zeroline=False)
            )

            st.plotly_chart(fig, use_container_width=True, key=f"anual_f1_{t}")

    # Fila 2: Consumo y derivados
    tipos_fila2 = ["Consumed", "PV Used", "From Netz"]
    cols2 = st.columns(3)

    for i, t in enumerate(tipos_fila2):
        with cols2[i]:
            st.markdown(f"#### {t}")
            df_t = df_anual_full[df_anual_full["Tipo"] == t].sort_values("Año")

            x_numeric = list(range(len(df_t)))
            x_labels = df_t["Año"].astype(str).tolist()
            anios_custom = df_t["Año"].tolist()
            color_actual = colores_map.get(t, "#2980B9")

            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=x_numeric,
                y=df_t["Valor"],
                marker_color=color_actual,
                width=0.25,
                customdata=anios_custom,
                hovertemplate=f"<b>%{{customdata}}</b><br><span style='color:{color_actual}'><b>{t}:</b> %{{y:,.2f}} kWh</span><extra></extra>"
            ))

            fig.add_trace(go.Scatter(
                x=x_numeric,
                y=df_t["Valor"],
                mode="lines+markers",
                line=dict(color=color_actual, width=2),
                marker=dict(size=5),
                customdata=anios_custom,
                hovertemplate=f"<b>%{{customdata}}</b><br><span style='color:{color_actual}'><b>{t}:</b> %{{y:,.2f}} kWh</span><extra></extra>"
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
                yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.15)", zeroline=False)
            )

            st.plotly_chart(fig, use_container_width=True, key=f"anual_f2_{t}")

# =========================================================
# 5) 📄 TABLA FINAL
# =========================================================
with tab5:
    st.subheader("📄 Tabla Datos")

    mostrar_tabla = st.toggle("Mostrar / Ocultar Tabla")

    if mostrar_tabla:
        tabla_wide = df_filtrado.pivot_table(
            index=["Año", "Mes", "Tipo"],
            columns="Día",
            values="Valor"
        ).reset_index()

        st.dataframe(tabla_wide)

# =========================================================
# 6) ℹ️ RESOURCES / INFO
# =========================================================
with tab6:
    st.markdown("""
    ### ℹ️ About Dashboard Solar App
    * **Script created by:** dJoZeR - Ingolstadt, 2026
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

    > **Nota importante:** Los días que no existan en meses más cortos (ej. el 30 o 31 de febrero) simplemente se pueden dejar vacíos o sin definir, ya que el script elimina automáticamente los valores nulos (`dropna`).
    """)
