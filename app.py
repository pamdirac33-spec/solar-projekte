import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Solar", layout="wide")
st.title("⚡ Dashboard Solar — Producción, Consumo y Flujo con la Red")

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
# INTERFAZ STREAMLIT
# ---------------------------------------------------------
archivo = st.file_uploader("Sube tu archivo Excel (Año, Mes, Tipo, días 1..31)", type=["xlsx"])

if archivo:
    df_long = cargar_y_transformar(archivo)

    col1, col2, col3 = st.columns(3)

    años_sel = col1.multiselect(
        "Años",
        sorted(df_long["Año"].unique()),
        default=sorted(df_long["Año"].unique())
    )

    meses_sel = col2.multiselect(
        "Meses",
        orden_meses,
        default=orden_meses
    )

    tipos_sel = col3.multiselect(
        "Tipos de dato",
        ["Pro", "Con", "PV_used", "to_netz", "from_netz"],
        default=["Pro", "Con"]
    )

    df_filtrado = df_long[
        (df_long["Año"].isin(años_sel)) &
        (df_long["Mes"].isin(meses_sel)) &
        (df_long["Tipo"].isin(tipos_sel))
    ]

    dias = sorted(df_filtrado["Día"].unique())
    rango_dias = st.slider(
        "Rango de días",
        min_value=int(min(dias)),
        max_value=int(max(dias)),
        value=(int(min(dias)), int(max(dias)))
    )

    df_filtrado = df_filtrado[
        (df_filtrado["Día"] >= rango_dias[0]) &
        (df_filtrado["Día"] <= rango_dias[1])
    ]

    # ---------------------------------------------------------
    # KPIs
    # ---------------------------------------------------------
    st.subheader("🔍 KPIs del periodo seleccionado")

    def get_val(tipo):
        return df_filtrado[df_filtrado["Tipo"] == tipo]["Valor"].sum()

    pro = get_val("Pro")
    con = get_val("Con")
    pv_used = get_val("PV_used")
    to_netz = get_val("to_netz")
    from_netz = get_val("from_netz")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Producción total (kWh)", f"{pro:.2f}")
    k2.metric("Consumo total (kWh)", f"{con:.2f}")
    k3.metric("Autoconsumo (%)", f"{(pv_used/pro*100 if pro>0 else 0):.1f}%")
    k4.metric("Dependencia red (%)", f"{(from_netz/con*100 if con>0 else 0):.1f}%")
    k5.metric("Excedente (%)", f"{(to_netz/pro*100 if pro>0 else 0):.1f}%")

    # ---------------------------------------------------------
    # GRÁFICA SUPERPUESTA REAL
    # ---------------------------------------------------------
    st.subheader("📈 Evolución diaria (superposición real)")

    fig = px.line(
        df_filtrado,
        x="Día",
        y="Valor",
        color="Serie",
        line_group="Serie",
        markers=True,
        title="Evolución diaria superpuesta",
        color_discrete_sequence=px.colors.qualitative.Set1  # COLORES BRILLANTES
    )

    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor="#222",
        paper_bgcolor="#222",
        font_color="#EEE",
        legend_title_text="Serie (Año - Mes - Tipo)",
        legend=dict(
        bgcolor="rgba(0,0,0,0.5)",   # fondo semitransparente
        bordercolor="#444",
        borderwidth=1,
	font=dict(
        	color="#f2f2f2",         # gris muy claro (casi blanco)
    		)
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # ANIMACIÓN MENSUAL
    # ---------------------------------------------------------
    st.subheader("🎞 Evolución mes a mes (animación)")

    fig_anim_mes = px.line(
        df_filtrado,
        x="Día",
        y="Valor",
        color="Serie",
        line_group="Serie",
        animation_frame="Mes",
        range_y=[0, df_filtrado["Valor"].max() * 1.1],
        title="Animación mensual"
    )

    fig_anim_mes.update_layout(
	hovermode="x unified",
        plot_bgcolor="#222",
        paper_bgcolor="#222",
        font_color="#EEE",
        legend_title_text="Serie (Año - Mes - Tipo)",
        legend=dict(
		bgcolor="rgba(0,0,0,0.5)",   # fondo semitransparente
        	bordercolor="#444",
        	borderwidth=1,
		font=dict(
        		color="#f2f2f2",         # gris muy claro (casi blanco)
    			)
        	)
    	)

    st.plotly_chart(fig_anim_mes, use_container_width=True)

    # ---------------------------------------------------------
    # VISTA MENSUAL AGREGADA
    # ---------------------------------------------------------
    st.subheader("📆 Vista mensual agregada")

    df_mensual = df_filtrado.groupby(["Año", "Mes", "Tipo"])["Valor"].sum().reset_index()

    # Crear una etiqueta única por serie
    df_mensual["Serie"] = (
        df_mensual["Año"].astype(str)
        + " - "
        + df_mensual["Tipo"]
    )

    # Pivotar para tener columnas independientes
    df_mensual_wide = df_mensual.pivot_table(
        index="Mes",
        columns="Serie",
        values="Valor"
    ).reset_index()

    fig_mensual = px.bar(
        df_mensual_wide,
        x="Mes",
        y=df_mensual_wide.columns[1:],   # todas las series
        barmode="group",
        title="Energía total por mes (columnas independientes)",
        color_discrete_sequence=px.colors.qualitative.Set1
    )

    st.plotly_chart(fig_mensual, use_container_width=True)

    # ---------------------------------------------------------
    # VISTA ANUAL AGREGADA
    # ---------------------------------------------------------
    st.subheader("📅 Vista anual agregada")

    df_anual = df_filtrado.groupby(["Año", "Tipo"])["Valor"].sum().reset_index()

    df_anual["Serie"] = df_anual["Tipo"]

    df_anual_wide = df_anual.pivot_table(
        index="Año",
        columns="Serie",
        values="Valor"
    ).reset_index()

    fig_anual = px.bar(
        df_anual_wide,
        x="Año",
        y=df_anual_wide.columns[1:],   # todas las series
        barmode="group",
        title="Energía total por año (columnas independientes)",
        color_discrete_sequence=px.colors.qualitative.Set1
    )

    st.plotly_chart(fig_anual, use_container_width=True)

    # ---------------------------------------------------------
    # TABLA FINAL EN FORMATO WIDE
    # ---------------------------------------------------------
    st.subheader("📄 Tabla en formato original (wide)")

    tabla_wide = df_filtrado.pivot_table(
        index=["Año", "Mes", "Tipo"],
        columns="Día",
        values="Valor"
    ).reset_index()

    st.dataframe(tabla_wide)

else:
    st.info("Sube tu Excel con filas = tipos y columnas = días.")