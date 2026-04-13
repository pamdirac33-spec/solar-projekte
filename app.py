import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Solar", layout="wide")

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
# LAYOUT PRINCIPAL: COLUMNA IZQUIERDA (FILTROS + KPIs)
# ---------------------------------------------------------
col_left, col_right = st.columns([1, 4])

with col_left:
    st.markdown('<div class="left-column">', unsafe_allow_html=True)

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

    st.metric("Producción Total", f"{pro:.2f} kWh")
    st.metric("Consumo Total", f"{con:.2f} kWh")
    st.metric("Autoconsumo", f"{pv_used:.1f} kWh / {autoc_pct:.1f}%")
    st.metric("Dependencia Red", f"{from_netz:.1f} kWh / {dep_pct:.1f}%")
    st.metric("Excedente", f"{to_netz:.1f} kWh / {exc_pct:.1f}%")

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
            color_discrete_sequence=px.colors.qualitative.Set1,
            render_mode="svg"
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
            
        fig_anim_mes = px.line(
            df_filtrado,
            x="Día",
            y="Valor",
            color="Serie",
            line_group="Serie",
            animation_frame="Mes",
            range_y=[0, df_filtrado["Valor"].max() * 1.1],
            color_discrete_sequence=px.colors.qualitative.Set1,
            render_mode="svg"
        )

        fig_anim_mes.update_layout(
            hovermode="x unified",
            plot_bgcolor="#f4f4f4",
            paper_bgcolor="#f4f4f4",
            font_color="#222",
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

            # PRODUCED (independiente)
            fig_prod.add_bar(
                x=df_a["Mes"],
                y=df_a["Produced"],
                name=f"Produced {año}",
                marker_color=colores_produced[idx % len(colores_produced)],
                offsetgroup=f"{año}_prod"
            )

            # PV USED (apilado)
            fig_prod.add_bar(
                x=df_a["Mes"],
                y=df_a["PV Used"],
                name=f"PV Used {año}",
                marker_color=colores_pvused[idx % len(colores_pvused)],
                offsetgroup=f"{año}_stack"
            )

            # TO NETZ (apilado)
            fig_prod.add_bar(
                x=df_a["Mes"],
                y=df_a["To Netz"],
                name=f"To Netz {año}",
                marker_color=colores_tonetz[idx % len(colores_tonetz)],
                offsetgroup=f"{año}_stack"
            )

            # Línea discontinua por año (mismo color que Produced pero más oscuro)
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
            title="Producción Mensual"
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

        # Paletas por año (mismo estilo que producción)
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
                offsetgroup=f"{año}_cons"
            )

            # PV USED (apilado)
            fig_con.add_bar(
                x=df_a["Mes"],
                y=df_a["PV Used"],
                name=f"PV Used {año}",
                marker_color=colores_pvused[idx % len(colores_pvused)],
                offsetgroup=f"{año}_stack"
            )

            # FROM NETZ (apilado)
            fig_con.add_bar(
                x=df_a["Mes"],
                y=df_a["From Netz"],
                name=f"From Netz {año}",
                marker_color=colores_fromnetz[idx % len(colores_fromnetz)],
                offsetgroup=f"{año}_stack"
            )

            # Línea discontinua por año (mismo color que Consumed)
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
            title="Consumo Mensual"
        )

        st.plotly_chart(fig_con, use_container_width=True)
        
    # =========================================================
    # 4) 📅 VISTA ANUAL
    # =========================================================
    with tab4:
        st.subheader("📅 Vista Anual")

        df_anual_full = df_long.groupby(["Año", "Tipo"])["Valor"].sum().reset_index()

        tipos = ["Produced", "Consumed", "PV Used", "To Netz", "From Netz"]

        cols = st.columns(5)

        for i, t in enumerate(tipos):
            with cols[i]:
                st.markdown(f"#### {t}")

                df_t = df_anual_full[df_anual_full["Tipo"] == t].sort_values("Año")

                x_numeric = list(range(len(df_t)))
                x_labels = df_t["Año"].astype(str).tolist()

                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=x_numeric,
                    y=df_t["Valor"],
                    marker_color="#F7DC6F",
                    width=0.25
                ))

                fig.add_trace(go.Scatter(
                    x=x_numeric,
                    y=df_t["Valor"],
                    mode="lines+markers",
                    line=dict(color="#2980B9", width=2),
                    marker=dict(size=5)
                ))

                fig.update_layout(
                    height=240,
                    margin=dict(l=0, r=10, t=25, b=40),
                    plot_bgcolor="#f7f7f7",
                    paper_bgcolor="#f7f7f7",
                    font_color="#333",
                    showlegend=False,
                    xaxis=dict(
                        tickmode="array",
                        tickvals=x_numeric,
                        ticktext=x_labels,
                        showgrid=False,
                        zeroline=False
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor="rgba(0,0,0,0.15)",
                        zeroline=False
                    )
                )

                st.plotly_chart(fig, use_container_width=True, key=f"anual_{t}")

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
