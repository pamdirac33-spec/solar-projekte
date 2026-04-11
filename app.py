import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Solar", layout="wide")

# ---------------------------------------------------------
# CSS PARA COLUMNA IZQUIERDA (sidebar visual)
# ---------------------------------------------------------
st.markdown("""
<style>
.left-column {
    background-color: #f0f0f0;
    padding: 20px;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

st.title("⚡ Dashboard Solar — Producción, Consumo y Flujo de Red")

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
    "Sube tu archivo Excel (opcional).",
    type=["xlsx"]
)

if archivo_subido is not None:
    df_long = cargar_y_transformar(archivo_subido)
    st.success("Archivo cargado desde el uploader.")
else:
    try:
        df_long = cargar_y_transformar(ruta_defecto)
        st.info(f"Usando archivo por defecto: {ruta_defecto}")
    except Exception as e:
        st.error("No se pudo cargar el archivo por defecto. Sube un archivo manualmente.")
        st.stop()

# ---------------------------------------------------------
# LAYOUT PRINCIPAL: COLUMNA IZQUIERDA (FILTROS + KPIs)
# ---------------------------------------------------------
col_left, col_right = st.columns([1, 3])

with col_left:
    st.markdown('<div class="left-column">', unsafe_allow_html=True)

    st.subheader("⚙️ Filtros")

    años_sel = st.multiselect(
        "Años",
        sorted(df_long["Año"].unique()),
        default=[2025]
    )

    meses_sel = st.multiselect(
        "Meses",
        orden_meses,
        default=["Jun", "Jul"]
    )

    tipos_sel = st.multiselect(
        "Tipos de Dato",
        ["Produced", "Consumed", "PV Used", "To Netz", "From Netz"],
        default=["Produced"]
    )

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
    # KPIs
    # ---------------------------------------------------------
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

    st.markdown("""
    <style>
    .kpi-block {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="kpi-block">', unsafe_allow_html=True)

    st.metric("Producción Total", f"{pro:.2f} kWh")
    st.metric("Consumo Total", f"{con:.2f} kWh")
    st.metric("Autoconsumo", f"{pv_used:.1f} kWh / {autoc_pct:.1f}%")
    st.metric("Dependencia Red", f"{from_netz:.1f} kWh / {dep_pct:.1f}%")
    st.metric("Excedente", f"{to_netz:.1f} kWh / {exc_pct:.1f}%")

    st.markdown('</div>', unsafe_allow_html=True)



# ---------------------------------------------------------
# COLUMNA DERECHA: PESTAÑAS CON TODAS LAS GRÁFICAS
# ---------------------------------------------------------
with col_right:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Evolución Diaria",
        "🎞 Evolución Mensual",
        "📊 Distribución Mensual",
        "📅 Evolución Anual",
        "📄 Tabla de Datos"
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
            color_discrete_sequence=px.colors.qualitative.Set1
        )

        fig.update_layout(
            hovermode="x unified",
            plot_bgcolor="#f4f4f4",      # fondo más claro
            paper_bgcolor="#f4f4f4",
            font_color="#222",
            legend_title_text="Año - Mes - Tipo",
            legend=dict(
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#cccccc",
                borderwidth=1,
                font=dict(
                    color="#222",
                    size=9          # tamaño pequeño para que quepan al menos ~12 entradas
                ),
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                itemwidth=40
            ),
            margin=dict(l=40, r=150, t=60, b=40),  # espacio extra para la leyenda
            height=550
        )
        fig.update_yaxes(title_text="kWh")

        # Máximo 31 días + líneas verticales por día
        fig.update_xaxes(
            range=[1, 31],
            dtick=1,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1
        )

        # Líneas horizontales cada 5 kWh
        fig.update_yaxes(
            dtick=5,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1
        )

        st.plotly_chart(fig, use_container_width=True)

        # ---------------------------------------------------------
        # 📊 Evolución diaria (versión en barras)
        # ---------------------------------------------------------
        st.subheader("📊 Evolución Diaria — Barras")

        if df_filtrado.empty:
            st.warning("Hefe, no hay datos para mostrar!")
            st.stop()
            
        fig_bar = px.bar(
            df_filtrado,
            x="Día",
            y="Valor",
            color="Serie",
            barmode="group",   # ← barras independientes
            color_discrete_sequence=px.colors.qualitative.Set1
        )

        fig_bar.update_layout(
            hovermode="x unified",
            plot_bgcolor="#f4f4f4",
            paper_bgcolor="#f4f4f4",
            font_color="#222",
            legend_title_text="Año - Mes - Tipo",
            legend=dict(
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#cccccc",
                borderwidth=1,
                font=dict(color="#222", size=9),
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                itemwidth=40,
                tracegroupgap=4
            ),
            margin=dict(l=40, r=150, t=60, b=40),
            height=550
        )

        # Líneas verticales por día
        fig_bar.update_xaxes(
            range=[0.5, 31.5],   # ← margen lateral

            dtick=1,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1,
            title_text="Día"
        )

        # Líneas horizontales cada 5 kWh
        fig_bar.update_yaxes(
            dtick=5,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1,
            title_text="kWh"
        )

        st.plotly_chart(fig_bar, use_container_width=True)

    # ---------------------------------------------------------
    # ANIMACIÓN MENSUAL
    # ---------------------------------------------------------
    with tab2:
        st.subheader("🎞 Evolución Mensual (animación)")

        if df_filtrado.empty:
            st.warning("Hefe, no hay datos para mostrar!")
            st.stop()
            
        fig_anim_mes = px.line(
            df_filtrado,
            x="Día",
            y="Valor",
            color="Serie",
            line_group="Serie",
            animation_frame="Mes",
            range_y=[0, df_filtrado["Valor"].max() * 1.1],
            color_discrete_sequence=px.colors.qualitative.Set1,
        )

        fig_anim_mes.update_layout(
            hovermode="x unified",
            plot_bgcolor="#f4f4f4",
            paper_bgcolor="#f4f4f4",
            font_color="#222",
            legend_title_text="Año - Mes - Tipo",
            legend=dict(
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#cccccc",
                borderwidth=1,
                font=dict(size=9),
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                itemwidth=40
            ),
            margin=dict(l=40, r=150, t=60, b=40),
            height=550
        )

        # Ejes homogéneos
        fig_anim_mes.update_xaxes(
            range=[1, 31],
            dtick=1,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1,
            title_text="Día"
        )

        fig_anim_mes.update_yaxes(
            dtick=5,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1,
            title_text="kWh"
        )

        st.plotly_chart(fig_anim_mes, use_container_width=True)

        # ---------------------------------------------------------
        # VISTA MENSUAL AGREGADA
        # ---------------------------------------------------------
        st.subheader("📆 Vista Mensual")

        if df_filtrado.empty:
            st.warning("Hefe, no hay datos para mostrar!")
            st.stop()
            
        df_mensual = df_filtrado.groupby(["Año", "Mes", "Tipo"])["Valor"].sum().reset_index()
        df_mensual["Etiqueta"] = df_mensual["Año"].astype(str) + " - " + df_mensual["Tipo"]

        fig_mensual = px.bar(
            df_mensual,
            x="Mes",
            y="Valor",
            color="Etiqueta",
            animation_frame="Año",
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Set1
        )

        fig_mensual.update_layout(
            hovermode="x unified",
            plot_bgcolor="#f4f4f4",
            paper_bgcolor="#f4f4f4",
            font_color="#222",
            legend=dict(
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#cccccc",
                borderwidth=1,
                font=dict(size=9)
            ),
            margin=dict(l=40, r=40, t=60, b=40),
            height=550
        )

        # Calcular el máximo del periodo seleccionado
        ymax = df_mensual["Valor"].max()

        # Determinar dtick dinámico según el orden de magnitud
        if ymax <= 20:
            dtick = 1
        elif ymax <= 50:
            dtick = 5
        elif ymax <= 200:
            dtick = 10
        elif ymax <= 500:
            dtick = 50
        elif ymax <= 2000:
            dtick = 100
        else:
            dtick = 200

        # Redondear ymax hacia arriba al siguiente múltiplo del dtick
        ymax_redondeado = ((ymax // dtick) + 1) * dtick

        fig_mensual.update_yaxes(
            range=[0, ymax_redondeado],
            tickmode="linear",
            dtick=dtick,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1,
            zeroline=False,
            title_text="kWh"
        )
        
        fig_mensual.update_xaxes(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1,
            title_text="Mes"
        )

        st.plotly_chart(fig_mensual, use_container_width=True)

        # ---------------------------------------------------------
        # NUEVA GRÁFICA MENSUAL — PRODUCCIÓN (CORREGIDA)
        # ---------------------------------------------------------
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

            # PRODUCED (independiente)
            fig_prod.add_bar(
                x=df_a["Mes"],
                y=df_a["Produced"],
                name=f"Produced {año}",
                marker_color=colores_produced[idx % len(colores_produced)],
                offsetgroup=f"{año}_prod",     # ← independiente
                legendgroup=f"{año}_prod"
            )

            # PV USED (apilado)
            fig_prod.add_bar(
                x=df_a["Mes"],
                y=df_a["PV Used"],
                name=f"PV Used {año}",
                marker_color=colores_pvused[idx % len(colores_pvused)],
                offsetgroup=f"{año}_stack",    # ← mismo grupo apilado
                legendgroup=f"{año}_stack"
            )

            # TO NETZ (apilado)
            fig_prod.add_bar(
                x=df_a["Mes"],
                y=df_a["To Netz"],
                name=f"To Netz {año}",
                marker_color=colores_tonetz[idx % len(colores_tonetz)],
                offsetgroup=f"{año}_stack",    # ← mismo grupo apilado
                legendgroup=f"{año}_stack"
            )

            # Línea discontinua por año
            fig_prod.add_scatter(
                x=df_a["Mes"],
                y=df_a["Produced"],
                mode="lines",
                name=f"Trend {año}",
                line=dict(
                    color=colores_produced[idx % len(colores_produced)],
                    width=1.5,
                    dash="dash"
                ),
                showlegend=False
            )

        fig_prod.update_layout(
            barmode="relative",
            plot_bgcolor="#f4f4f4",
            paper_bgcolor="#f4f4f4",
            font_color="#222",
            height=550,
            title="Producción mensual — comparación multiaño"
        )

        st.plotly_chart(fig_prod, use_container_width=True)


        # ---------------------------------------------------------
        # NUEVA GRÁFICA MENSUAL — CONSUMO (CORREGIDA)
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

        # Paletas por año (coherentes con Producción)
        años_unicos = sorted(dfc["Año"].unique())
        colores_consumed = ["#A6ACAF", "#909497", "#7B7D7D", "#626567"]
        colores_pvused   = ["#F9E79F", "#F7DC6F", "#F4D03F", "#F1C40F"]
        colores_fromnetz = ["#85C1E9", "#5DADE2", "#3498DB", "#2E86C1"]

        for idx, año in enumerate(años_unicos):
            df_a = dfc[dfc["Año"] == año]

            # CONSUMED (independiente)
            fig_con.add_bar(
                x=df_a["Mes"],
                y=df_a["Consumed"],
                name=f"Consumed {año}",
                marker_color=colores_consumed[idx % len(colores_consumed)],
                offsetgroup=f"{año}_cons",     # ← independiente
                legendgroup=f"{año}_cons"
            )

            # PV USED (apilado)
            fig_con.add_bar(
                x=df_a["Mes"],
                y=df_a["PV Used"],
                name=f"PV Used {año}",
                marker_color=colores_pvused[idx % len(colores_pvused)],
                offsetgroup=f"{año}_stack",    # ← grupo apilado
                legendgroup=f"{año}_stack"
            )

            # FROM NETZ (apilado)
            fig_con.add_bar(
                x=df_a["Mes"],
                y=df_a["From Netz"],
                name=f"From Netz {año}",
                marker_color=colores_fromnetz[idx % len(colores_fromnetz)],
                offsetgroup=f"{año}_stack",    # ← mismo grupo apilado
                legendgroup=f"{año}_stack"
            )

            # Línea discontinua por año
            fig_con.add_scatter(
                x=df_a["Mes"],
                y=df_a["Consumed"],
                mode="lines",
                name=f"Trend {año}",
                line=dict(
                    color=colores_consumed[idx % len(colores_consumed)],
                    width=1.5,
                    dash="dash"
                ),
                showlegend=False
            )

        fig_con.update_layout(
            barmode="relative",
            plot_bgcolor="#f4f4f4",
            paper_bgcolor="#f4f4f4",
            font_color="#222",
            height=550,
            title="Consumo mensual — comparación multiaño"
        )

        st.plotly_chart(fig_con, use_container_width=True)
    # ---------------------------------------------------------
    # VISTA ANUAL AGREGADA
    # ---------------------------------------------------------
    with tab4:
        st.subheader("📅 Vista Anual")

        if df_filtrado.empty:
            st.warning("Hefe, no hay datos para mostrar!")
            st.stop()
            
        # Usar SIEMPRE todos los datos del Excel
        df_anual_full = df_long.groupby(["Año", "Tipo"])["Valor"].sum().reset_index()

        tipos = ["Produced", "Consumed", "PV Used", "To Netz", "From Netz"]

        cols = st.columns(5)

        for i, t in enumerate(tipos):
            with cols[i]:
                st.markdown(f"#### {t}")

                df_t = df_anual_full[df_anual_full["Tipo"] == t].sort_values("Año")

                # Convertir años a numérico para permitir width en barras
                x_numeric = list(range(len(df_t)))
                x_labels = df_t["Año"].astype(str).tolist()

                fig = go.Figure()

                # --- Barras finas ---
                fig.add_trace(go.Bar(
                    x=x_numeric,
                    y=df_t["Valor"],
                    marker_color="#F7DC6F",
                    width=0.25
                ))

                # --- Línea de tendencia ---
                fig.add_trace(go.Scatter(
                    x=x_numeric,
                    y=df_t["Valor"],
                    mode="lines+markers",
                    line=dict(color="#2980B9", width=2),
                    marker=dict(size=5)
                ))

                # --- Estética profesional ---
                fig.update_layout(
                height=240,
                margin=dict(l=0, r=10, t=25, b=40),
                plot_bgcolor="#f7f7f7",
                paper_bgcolor="#f7f7f7",
                font_color="#333",
                showlegend=False,
                xaxis=dict(
                    title="",
                    tickfont=dict(size=9),
                    tickmode="array",
                    tickvals=x_numeric,
                    ticktext=x_labels,
                    showgrid=False,
                    zeroline=False
                ),
                yaxis=dict(
                    title="",  # quitamos el título del eje
                    tickfont=dict(size=9),
                    showgrid=True,
                    gridcolor="rgba(0,0,0,0.15)",
                    zeroline=False
                ),
                annotations=[
                    dict(
                        xref="paper",
                        yref="paper",
                        x=0,          # extremo izquierdo
                        y=-0.22,      # debajo del eje
                        text="kWh",
                        showarrow=False,
                        font=dict(size=10, color="#555")
                    )
                ]
            )

                st.plotly_chart(fig, use_container_width=True, key=f"anual_{t}")

    # ---------------------------------------------------------
    # TABLA FINAL EN FORMATO WIDE
    # ---------------------------------------------------------
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
