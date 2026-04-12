import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Solar", layout="wide")

st.markdown("""
<style>
/* objetivo: reducir margen del bloque que envuelve pills */
div[data-testid^="stPills"] { margin-top: 0px !important; padding-top: 0px !important; }
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
def _toggle_all_callback(key_prefix, items):
    sel_key = f"{key_prefix}_selected"
    show_all_key = f"{key_prefix}_show_all"
    ver_key = f"{key_prefix}_version"

    # Alternar selección completa
    if st.session_state.get(show_all_key, False):
        st.session_state[sel_key] = []
        st.session_state[show_all_key] = False
    else:
        st.session_state[sel_key] = items.copy()
        st.session_state[show_all_key] = True

    # Forzar nueva instancia de pills cambiando la versión
    st.session_state[ver_key] = st.session_state.get(ver_key, 0) + 1

def pills_selector(label, items, key_prefix, default_selected=None):
    # Título compacto
    st.markdown(f"<div style='font-size:14px; font-weight:600; margin:0 0 4px 0'>{label}</div>", unsafe_allow_html=True)

    items = [str(i) for i in items]
    sel_key = f"{key_prefix}_selected"
    ver_key = f"{key_prefix}_version"
    show_all_key = f"{key_prefix}_show_all"

    # Inicializar estado
    if sel_key not in st.session_state:
        st.session_state[sel_key] = items.copy() if default_selected is None else [str(x) for x in default_selected]
    if ver_key not in st.session_state:
        st.session_state[ver_key] = 0
    # show_all_key se sincroniza más abajo según la selección real

    # Creamos dos placeholders: uno para el botón (arriba) y otro para las pills (debajo)
    ph_btn = st.empty()
    ph_pills = st.empty()

    # Renderizamos las pills primero dentro de su placeholder para obtener la selección actual
    pills_key = f"{key_prefix}_pills_v{st.session_state[ver_key]}"
    with ph_pills.container():
        new_selected = st.pills(
            "",
            options=items,
            selection_mode="multi",
            default=st.session_state[sel_key],
            key=pills_key
        )

    # Actualizamos el estado según la selección manual del usuario
    st.session_state[sel_key] = new_selected
    st.session_state[show_all_key] = (len(new_selected) == len(items))

    # Ahora renderizamos el botón en su placeholder (aparecerá arriba) usando el estado actualizado
    btn_label = "Deseleccionar todo" if st.session_state.get(show_all_key, False) else "Seleccionar todo"
    # Usamos on_click para alternar y forzar re-render de las pills
    ph_btn.button(
        btn_label,
        key=f"{key_prefix}_btn",
        on_click=_toggle_all_callback,
        args=(key_prefix, items)
    )

    # Devolver en tipo original si procede
    try:
        return [int(x) for x in st.session_state[sel_key]]
    except:
        return st.session_state[sel_key]

# Ejemplo de uso
# años_sel = pills_selector("Años", [2023,2024,2025,2026], key_prefix="anos", default_selected=[2025])

# ---------------------------------------------------------
# LAYOUT PRINCIPAL: COLUMNA IZQUIERDA (FILTROS + KPIs)
# ---------------------------------------------------------
col_left, col_right = st.columns([1, 3])

with col_left:
    st.subheader("⚙️ Filtros")

    años_disponibles = sorted(df_long["Año"].unique())
    meses_disponibles = orden_meses
    tipos_disponibles = ["Produced", "Consumed", "PV Used", "To Netz", "From Netz"]

    años_sel = pills_selector("Años", años_disponibles, key_prefix="anos", default_selected=[2025])
    meses_sel = pills_selector("Meses", meses_disponibles, key_prefix="meses", default_selected=["Jun", "Jul"])
    tipos_sel = pills_selector("Tipos de dato", tipos_disponibles, key_prefix="tipos", default_selected=["Produced"])
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
            color_discrete_sequence=px.colors.qualitative.Set1
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
        st.subheader("🔆 Producción mensual — desglose PV Used / To Netz")

        df_prod = df_kpi[df_kpi["Tipo"].isin(["Produced", "PV Used", "To Netz"])]
        df_prod_m = df_prod.groupby(["Año", "Mes", "Tipo"])["Valor"].sum().reset_index()

        dfp = df_prod_m.pivot_table(
            index=["Año", "Mes"],
            columns="Tipo",
            values="Valor",
            fill_value=0
        ).reset_index()

        dfp["Mes"] = pd.Categorical(dfp["Mes"], categories=orden_meses, ordered=True)
        dfp = dfp.sort_values(["Año", "Mes"])

        fig_prod = go.Figure()

        fig_prod.add_bar(
            x=dfp["Mes"],
            y=dfp["Produced"],
            name="Produced",
            marker_color="#F7DC6F",
            offsetgroup=0
        )

        fig_prod.add_bar(
            x=dfp["Mes"],
            y=dfp["PV Used"],
            name="PV Used",
            marker_color="#A6ACAF",
            offsetgroup=1
        )

        fig_prod.add_bar(
            x=dfp["Mes"],
            y=dfp["To Netz"],
            name="To Netz",
            marker_color="#2980B9",
            offsetgroup=1
        )

        fig_prod.add_scatter(
            x=dfp["Mes"],
            y=dfp["Produced"],
            mode="lines",
            showlegend=False,
            line=dict(color="#2980B9", width=1, dash="dash")
        )

        fig_prod.update_layout(
            barmode="relative",
            plot_bgcolor="#f4f4f4",
            paper_bgcolor="#f4f4f4",
            font_color="#222",
            height=500,
            title="Producción mensual — Total vs PV Used / To Netz"
        )

        st.plotly_chart(fig_prod, use_container_width=True)

        # ---------------------------------------------------------
        # CONSUMO
        # ---------------------------------------------------------
        st.subheader("⚡ Consumo mensual — desglose PV Used / From Netz")

        df_con = df_kpi[df_kpi["Tipo"].isin(["Consumed", "PV Used", "From Netz"])]
        df_con_m = df_con.groupby(["Año", "Mes", "Tipo"])["Valor"].sum().reset_index()

        dfc = df_con_m.pivot_table(
            index=["Año", "Mes"],
            columns="Tipo",
            values="Valor",
            fill_value=0
        ).reset_index()

        dfc["Mes"] = pd.Categorical(dfc["Mes"], categories=orden_meses, ordered=True)
        dfc = dfc.sort_values(["Año", "Mes"])

        fig_con = go.Figure()

        fig_con.add_bar(
            x=dfc["Mes"],
            y=dfc["Consumed"],
            name="Consumed",
            marker_color="#A6ACAF",
            offsetgroup=0
        )

        fig_con.add_bar(
            x=dfc["Mes"],
            y=dfc["PV Used"],
            name="PV Used",
            marker_color="#F7DC6F",
            offsetgroup=1
        )

        fig_con.add_bar(
            x=dfc["Mes"],
            y=dfc["From Netz"],
            name="From Netz",
            marker_color="#2980B9",
            offsetgroup=1
        )

        fig_con.add_scatter(
            x=dfc["Mes"],
            y=dfc["Consumed"],
            mode="lines",
            showlegend=False,
            line=dict(color="#2980B9", width=1, dash="dash")
        )

        fig_con.update_layout(
            barmode="relative",
            plot_bgcolor="#f4f4f4",
            paper_bgcolor="#f4f4f4",
            font_color="#222",
            height=500,
            title="Consumo mensual — Total vs PV Used / From Netz"
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
