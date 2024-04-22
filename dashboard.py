from datetime import datetime
import json

from collections import namedtuple
import pandas as pd
import streamlit as st

from filtro import Filtro

import plotly.express as px

st.set_page_config(
    page_title="Dashboard SIGMINE",
    page_icon=":pick:",
    layout="wide",
)

st.markdown("# Dashboard SIGMINE<br>", unsafe_allow_html=True)


@st.cache_resource
def conectar_db():
    conn = st.connection("postgresql", type="sql")
    return conn


@st.cache_data(show_spinner=False)
def carregar_grupos():
    with open("grupos.json") as f:
        grupos = json.load(f)
    return grupos


@st.cache_data(show_spinner="Processando dados...")
def baixar_processos() -> pd.DataFrame:
    conn = conectar_db()
    df: pd.DataFrame = conn.query(
        "SELECT * FROM dashboard_vale.mv_dashboard_vale",
        show_spinner="Baixando dados do banco de dados...",
    )

    df.fase = pd.Categorical(df.fase, ordered=True)
    df.uf = pd.Categorical(df.uf, ordered=True)

    grupos = carregar_grupos()
    df.nome = df.nome.replace(grupos)
    return df


df = baixar_processos()
filtro = Filtro(df)

Stats = namedtuple("Stats", ["quantidade", "dms", "area"])


def get_agrupados(df: pd.DataFrame, filtro: Filtro):
    mask = df.uf.isin(filtro.uf)
    df_todos = df[mask].drop_duplicates("processo")

    agrupado_todos = (
        df_todos.groupby("nome")
        .agg(
            quantidade_dms_todos=("nome", "count"),
            area_total_todos=("area_ha", "sum"),
            total_recolhido_todos=("total_recolhido", "sum"),
        )
        .rename(
            index={"nome": "Nome da empresa"},
            columns={
                "quantidade_dms_todos": "Quantidade de DMs",
                "area_total_todos": "Área total",
                "total_recolhido_todos": "Total recolhido",
            },
        )
    )
    quantidade_todos = agrupado_todos.shape[0]
    quantidade_dms_todos = agrupado_todos["Quantidade de DMs"].sum()
    area_total_todos = agrupado_todos["Área total"].sum()

    if filtro.somente_titulares:
        df_filtrado = df_todos.query("titular == True")
    else:
        mask = df_todos.fase.isin(filtro.fase)
        df_filtrado = df_todos[mask]

    agrupado_filtrados = (
        df_filtrado.groupby("nome")
        .agg(
            quantidade_dms_filtrados=("nome", "count"),
            area_total_filtrados=("area_ha", "sum"),
            total_recolhido_filtrados=("total_recolhido", "sum"),
        )
        .rename(
            index={"nome": "Nome da empresa"},
            columns={
                "quantidade_dms_filtrados": "Quantidade de DMs",
                "area_total_filtrados": "Área total",
                "total_recolhido_filtrados": "Total recolhido",
            },
        )
    )

    quantidade_filtro = agrupado_filtrados.shape[0]
    quantidade_dms_filtro = agrupado_filtrados["Quantidade de DMs"].sum()
    area_total_filtro = agrupado_filtrados["Área total"].sum()

    agrupados = (
        agrupado_filtrados.join(
            agrupado_todos, how="outer", lsuffix=" (Filtrados)", rsuffix=" (Todos)"
        )
        .fillna(0)
        .rename_axis("Nome da empresa")
        .sort_values(by="Área total (Todos)", ascending=False)
    )

    return (
        Stats(quantidade_todos, quantidade_dms_todos, area_total_todos),
        Stats(quantidade_filtro, quantidade_dms_filtro, area_total_filtro),
        agrupados,
    )


stats_todos, stats_filtro, df_agrupado = get_agrupados(df, filtro)


with st.container(border=True):

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label="Quantidade total de empresas",
        value=f"{stats_todos.quantidade}",
    )
    col2.metric(
        label="Quantidade total de DMs",
        value=f"{round(stats_todos.dms / 1000, 2)}k",
    )

    col3.metric(
        label="Área total",
        value=f"{round(stats_todos.area / 1e6, 2)}M ha",
    )

    col1.metric(
        label="Quantidade de empresas nas fases filtradas",
        value=f"{stats_filtro.quantidade}",
    )
    col2.metric(
        label="Quantidade de DMs nas fases filtradas",
        value=f"{round(stats_filtro.dms / 1000, 2)}k",
    )

    col3.metric(
        label="Área total nas fases filtradas",
        value=f"{round(stats_filtro.area / 1e6, 2)}M ha",
    )

barplot_container = st.container(border=True)
barplot_cols = barplot_container.columns(2)

ordenar_dms = barplot_cols[0].selectbox(
    "Ordenar por", ["Todos", "Filtrados"], index=0, key="ordenar_quantidade"
)
ordenar_area = barplot_cols[1].selectbox(
    "Ordenar por", ["Todos", "Filtrados"], index=0, key="ordenar_area"
)


def get_top(agrupados, quantidade: int, ordenar_dms="Todos", ordenar_area="Todos"):

    def _get_top(ordenacao, coluna):
        match ordenacao:
            case "Todos":
                top_todos = agrupados[f"{coluna} (Todos)"].nlargest(quantidade)
                top_filtrados = agrupados[f"{coluna} (Filtrados)"].loc[top_todos.index]
            case "Filtrados":
                top_filtrados = agrupados[f"{coluna} (Filtrados)"].nlargest(quantidade)
                top_todos = agrupados[f"{coluna} (Todos)"].loc[top_filtrados.index]

        top_filtrados = top_filtrados.rename(coluna).reset_index()
        top_todos = top_todos.rename(coluna).reset_index()
        top_filtrados["Tipo"] = "Filtrados"
        top_todos["Tipo"] = "Todos"
        top = pd.concat([top_todos, top_filtrados], join="inner")
        top["Nome da empresa"] = top["Nome da empresa"].str[:30]
        top = top.sort_values(
            by=["Tipo", coluna], ascending=(ordenacao == "Filtrados", False)
        )
        return top

    top_dms = _get_top(ordenar_dms, "Quantidade de DMs")
    top_area = _get_top(ordenar_area, "Área total")
    return top_dms, top_area


top_dms, top_area = get_top(df_agrupado, filtro.quantidade, ordenar_dms, ordenar_area)

barplot_container.markdown("## Gráficos de barras")

col1, col2 = barplot_cols

fig = px.bar(
    data_frame=top_dms,
    x="Quantidade de DMs",
    y="Nome da empresa",
    color="Tipo",
    barmode="group",
    title=f"Top {filtro.quantidade} empresas por quantidade de DMs",
    text_auto=True,
    template="plotly_white",
)
fig.update_layout(height=filtro.altura, yaxis={"autorange": "reversed", "title": ""})
col1.plotly_chart(
    fig,
    use_container_width=True,
)

fig = px.bar(
    data_frame=top_area,
    x="Área total",
    y="Nome da empresa",
    color="Tipo",
    barmode="group",
    title=f"Top {filtro.quantidade} empresas por área total",
    text_auto=True,
    template="plotly_white",
)
fig.update_layout(height=filtro.altura, yaxis={"autorange": "reversed", "title": ""})
col2.plotly_chart(
    fig,
    use_container_width=True,
)

with st.container(border=True):
    st.markdown("## Gráficos de pizza")

    col1, col2 = st.columns(2)

    fig = px.pie(
        data_frame=top_dms[top_dms.Tipo == "Todos"],
        names="Nome da empresa",
        values="Quantidade de DMs",
        hole=0.5,
        title=f"Top {filtro.quantidade} empresas por quantidade de DMs (Todos)",
        template="plotly_white",
    )
    fig.update_layout(height=filtro.altura / 2)
    col1.plotly_chart(
        fig,
        use_container_width=True,
    )

    fig = px.pie(
        data_frame=top_area[top_area.Tipo == "Todos"],
        names="Nome da empresa",
        values="Área total",
        hole=0.5,
        title=f"Top {filtro.quantidade} empresas por área (Todos)",
        template="plotly_white",
    )

    fig.update_layout(height=filtro.altura / 2)
    col2.plotly_chart(
        fig,
        use_container_width=True,
    )

    fig = px.pie(
        data_frame=top_dms[top_dms.Tipo == "Filtrados"],
        names="Nome da empresa",
        values="Quantidade de DMs",
        hole=0.5,
        title=f"Top {filtro.quantidade} empresas por quantidade de DMs (Filtrados)",
        template="plotly_white",
    )

    fig.update_layout(height=filtro.altura / 2)
    col1.plotly_chart(
        fig,
        use_container_width=True,
    )

    fig = px.pie(
        data_frame=top_area[top_area.Tipo == "Filtrados"],
        names="Nome da empresa",
        values="Área total",
        hole=0.5,
        title=f"Top {filtro.quantidade} empresas por área (Filtrados)",
        template="plotly_white",
    )
    fig.update_layout(height=filtro.altura / 2)
    col2.plotly_chart(
        fig,
        use_container_width=True,
    )


@st.cache_data
def convert_df(df: pd.DataFrame) -> str:
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv()


with st.container(border=True):
    st.markdown("## Tabelas")

    st.markdown("### Dados agrupados")
    st.dataframe(df_agrupado, use_container_width=True)
    csv = convert_df(df_agrupado)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="agrupados.csv",
        mime="text/csv",
    )

    st.markdown("### Dados brutos")
    df = baixar_processos()
    df.columns = df.columns.str.capitalize().str.replace("_", " ")
    df = df.drop(columns="Titular")
    df.set_index("Processo", inplace=True)
    st.dataframe(df, use_container_width=True)
    csv = convert_df(df)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="processos.csv",
        mime="text/csv",
    )
