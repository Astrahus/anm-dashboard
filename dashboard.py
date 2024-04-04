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
def estabelecer_conexao():
    conn = st.connection("postgresql", type="sql")
    return conn


@st.cache_data(show_spinner=False)
def carregar_grupos():
    with open("grupos.json") as f:
        grupos = json.load(f)
    return grupos


@st.cache_data(show_spinner="Baixando e processando dados...")
def baixar_processos() -> pd.DataFrame:
    conn = estabelecer_conexao()
    query: pd.DataFrame = conn.query("SELECT * FROM processos", show_spinner=False)

    query.fase = pd.Categorical(query.fase, ordered=True)
    query.uf = pd.Categorical(query.uf, ordered=True)
    query.subs = pd.Categorical(query.subs)

    grupos = carregar_grupos()
    query.nome = query.nome.replace(grupos)
    return query


@st.cache_data(show_spinner=False)
def baixar_titulares():
    conn = estabelecer_conexao()
    query = conn.query("SELECT * FROM processos_titulares", show_spinner=False)
    return query


def filtrar_titulares(processos):
    titulares = baixar_titulares()
    return titulares.merge(processos, on=["numero", "ano"])


processos = baixar_processos()
filtro = Filtro(processos)


Stats = namedtuple("Stats", ["quantidade", "dms", "area"])


def get_agrupados(processos, filtro):
    mask = processos.uf.isin(filtro.ufs)
    filtrados = processos[mask]

    agrupado_todos = (
        filtrados.groupby("nome")
        .agg(
            quantidade_dms_todos=("nome", "count"),
            area_total_todos=("area_ha", "sum"),
        )
        .rename(
            index={"nome": "Nome da empresa"},
            columns={
                "quantidade_dms_todos": "Quantidade de DMs",
                "area_total_todos": "Área total",
            },
        )
    )
    quantidade_todos = agrupado_todos.shape[0]
    quantidade_dms_todos = agrupado_todos["Quantidade de DMs"].sum()
    area_total_todos = agrupado_todos["Área total"].sum()

    if filtro.usando_titulares:
        filtrados = filtrar_titulares(filtrados)
    else:
        fase_mask = processos.fase.isin(filtro.fases)
        filtrados = processos[fase_mask]

    agrupado_filtrados = (
        filtrados.groupby("nome")
        .agg(
            quantidade_dms_filtrados=("nome", "count"),
            area_total_filtrados=("area_ha", "sum"),
        )
        .rename(
            index={"nome": "Nome da empresa"},
            columns={
                "quantidade_dms_filtrados": "Quantidade de DMs",
                "area_total_filtrados": "Área total",
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
        .sort_values(by="Área total (Filtrados)", ascending=False)
    )

    return (
        Stats(quantidade_todos, quantidade_dms_todos, area_total_todos),
        Stats(quantidade_filtro, quantidade_dms_filtro, area_total_filtro),
        agrupados,
    )


stats_todos, stats_filtro, agrupados = get_agrupados(processos, filtro)


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


def get_top(agrupados):
    top_dms = agrupados["Quantidade de DMs (Filtrados)"].nlargest(filtro.quantidade)
    top_area = agrupados["Área total (Filtrados)"].nlargest(filtro.quantidade)
    top_dms_todos = agrupados["Quantidade de DMs (Todos)"].loc[top_dms.index]
    top_area_todos = agrupados["Área total (Todos)"].loc[top_area.index]

    top_dms.rename("Quantidade de DMs", inplace=True)
    top_area.rename("Área total", inplace=True)
    top_dms_todos.rename("Quantidade de DMs", inplace=True)
    top_area_todos.rename("Área total", inplace=True)

    top_dms = top_dms.reset_index()
    top_area = top_area.reset_index()
    top_dms_todos = top_dms_todos.reset_index()
    top_area_todos = top_area_todos.reset_index()

    top_dms["Tipo"] = "Filtrados"
    top_area["Tipo"] = "Filtrados"
    top_dms_todos["Tipo"] = "Todos"
    top_area_todos["Tipo"] = "Todos"

    top_dms = pd.concat([top_dms_todos, top_dms], join="inner")
    top_area = pd.concat([top_area_todos, top_area], join="inner")

    # reduce nome da empresa size
    top_dms["Nome da empresa"] = top_dms["Nome da empresa"].str[:30]
    top_area["Nome da empresa"] = top_area["Nome da empresa"].str[:30]

    return top_dms, top_area


top_dms, top_area = get_top(agrupados)

with st.container(border=True):
    st.markdown("## Gráficos de barras")

    col1, col2 = st.columns(2)

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
    fig.update_layout(
        height=filtro.altura, yaxis={"autorange": "reversed", "title": ""}
    )
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
    fig.update_layout(
        height=filtro.altura, yaxis={"autorange": "reversed", "title": ""}
    )
    col2.plotly_chart(
        fig,
        use_container_width=True,
    )

with st.container(border=True):
    st.markdown("## Gráficos de pizza")

    col1, col2 = st.columns(2)

    fig = px.pie(
        data_frame=top_dms[top_dms["Tipo"] == "Todos"],
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
        data_frame=top_area[top_area["Tipo"] == "Todos"],
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
        data_frame=top_dms[top_dms["Tipo"] == "Filtrados"],
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
        data_frame=top_area[top_area["Tipo"] == "Filtrados"],
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
    st.markdown("## Tabelas de dados")

    st.markdown("### Dados agrupados")
    st.dataframe(agrupados, use_container_width=True)
    csv = convert_df(agrupados)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="agrupados.csv",
        mime="text/csv",
    )

    st.markdown("### Processos")
    processos = baixar_processos()
    processos.columns = processos.columns.str.capitalize()
    processos["Processo"] = processos["Numero"] + "/" + processos["Ano"]
    processos = processos.drop(columns=["Numero", "Ano"])
    processos.set_index("Processo", inplace=True)
    st.dataframe(processos, use_container_width=True)
    csv = convert_df(processos)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="processos.csv",
        mime="text/csv",
    )
