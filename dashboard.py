import json

import pandas as pd
import streamlit as st

from plots import Barplot, Pieplot, Scatter

st.set_page_config(
    page_title="Dashboard SIGMINE",
    page_icon=":pick:",
    layout="wide",
)


def estabelecer_conexao():
    conn = st.connection("postgresql", type="sql")
    return conn


def baixar_dados(conn):
    query: pd.DataFrame = conn.query("SELECT * FROM sigmine_view", show_spinner=False)
    return query


@st.cache_data(show_spinner=False)
def carregar_grupos():
    with open("grupos.json") as f:
        grupos = json.load(f)
    return grupos


@st.cache_data(show_spinner="Baixando e processando dados...")
def processar_dados(grupos) -> pd.DataFrame:
    conn = estabelecer_conexao()
    query = baixar_dados(conn)

    query.fase = pd.Categorical(query.fase, ordered=True)
    query.uf = pd.Categorical(query.uf, ordered=True)
    query.subs = pd.Categorical(query.subs)

    query.nome = query.nome.replace(grupos)

    quantidade_dms = query.shape[0]
    area_total = query["area_ha"].sum()
    quantidade_empresas = query["nome"].nunique()

    return query, quantidade_dms, area_total, quantidade_empresas


grupos = carregar_grupos()
dados_processados, quantidade_dms, area_total, quantidade_empresas = processar_dados(
    grupos
)


st.markdown("# Dashboard SIGMINE<br>", unsafe_allow_html=True)


def set_fases():
    for i, _ in enumerate(dados_processados.fase.cat.categories):
        st.session_state[f"fase_{i}"] = True


def reset_fases():
    for i, _ in enumerate(dados_processados.fase.cat.categories):
        st.session_state[f"fase_{i}"] = False


def set_uf():
    for i, _ in enumerate(dados_processados.uf.cat.categories):
        st.session_state[f"uf_{i}"] = True


def reset_uf():
    for i, _ in enumerate(dados_processados.uf.cat.categories):
        st.session_state[f"uf_{i}"] = False


# SIDEDBAR
with st.sidebar:
    st.markdown("# Configurações")
    with st.popover("Fases", use_container_width=True):
        st.markdown("### Fases")
        ncols = 3
        uf_cols = st.columns(ncols)
        filtro_fases = {}
        TITULADOS = {
            "AUTORIZAÇÃO DE PESQUISA",
            "CONCESSÃO DE LAVRA",
            "DIREITO DE REQUERER A LAVRA",
            "LAVRA GARIMPEIRA",
            "LICENCIAMENTO",
            "REGISTRO DE EXTRAÇÃO",
            "REQUERIMENTO DE LAVRA",
        }
        for i, fase in enumerate(dados_processados.fase.cat.categories):
            filtro_fases[fase] = uf_cols[i % ncols].checkbox(
                fase, value=(fase in TITULADOS), key=f"fase_{i}"
            )
        st.button("Selecionar todas", on_click=set_fases)
        st.button("Desmarcar todas", on_click=reset_fases)

    with st.popover("Estados", use_container_width=True):
        st.markdown("### Estados")
        ncols = 4
        uf_cols = st.columns(ncols)
        filtro_uf = {}
        for i, uf in enumerate(dados_processados.uf.cat.categories):
            filtro_uf[uf] = uf_cols[i % ncols].checkbox(uf, value=True, key=f"uf_{i}")
        st.button("Selecionar todos", on_click=set_uf)
        st.button("Desmarcar todos", on_click=reset_uf)

    filtro_quantidade = st.number_input(
        "Quantidade de empresas",
        min_value=1,
        max_value=100,
        value=20,
    )

    filtro_tipo_total = st.radio(
        "'Outras empresas' se refere a:",
        ["Dados filtrados", "Todos os dados"],
    )

    filtro_altura = 30 * filtro_quantidade

    filtro_incluir_outras = st.checkbox("Incluir 'Outras empresas' nos gráficos")

mask_fases = dados_processados.fase.isin(
    {fase for fase, filtro in filtro_fases.items() if filtro}
)
mask_uf = dados_processados.uf.isin({uf for uf, filtro in filtro_uf.items() if filtro})
dados_processados = dados_processados[mask_fases & mask_uf].drop_duplicates(
    subset=("numero", "ano")
)

dados_agrupados = (
    dados_processados.groupby("nome")
    .agg(
        quantidade=("nome", "count"),
        area_total=("area_ha", "sum"),
    )
    .sort_values(by="area_total", ascending=False)
)
quantidade_dms_filtro = dados_agrupados["quantidade"].sum()
area_total_filtro = dados_agrupados["area_total"].sum()
quantidade_empresas_filtro = dados_agrupados.shape[0]


df_quantidade = (
    dados_agrupados[["quantidade"]]
    .sort_values(by="quantidade", ascending=False)
    .head(filtro_quantidade)
    .reset_index()
)
df_quantidade["nome"] = df_quantidade["nome"].str[:30]

df_area = dados_agrupados[["area_total"]].head(filtro_quantidade).reset_index()
df_area["nome"] = df_area["nome"].str[:30]


if filtro_incluir_outras:
    if filtro_tipo_total == "Dados filtrados":
        df_quantidade.loc[filtro_quantidade] = [
            "Outras",
            quantidade_dms_filtro - df_quantidade["quantidade"].sum(),
        ]
        df_area.loc[filtro_quantidade] = [
            "Outras",
            area_total_filtro - df_area["area_total"].sum(),
        ]
    elif filtro_tipo_total == "Todos os dados":
        df_quantidade.loc[filtro_quantidade] = [
            "Outras",
            quantidade_dms - df_quantidade["quantidade"].sum(),
        ]
        df_area.loc[filtro_quantidade] = [
            "Outras",
            area_total - df_area["area_total"].sum(),
        ]

# METRICAS
with st.container(border=True):
    top_n_quantidade = df_quantidade.iloc[:filtro_quantidade]["quantidade"].sum()
    top_n_area = df_area.iloc[:filtro_quantidade]["area_total"].sum()

    if filtro_tipo_total == "Dados filtrados":
        quantidade_outras = quantidade_empresas_filtro - top_n_quantidade
        quantidade_dms_outras = quantidade_dms_filtro - top_n_quantidade
        area_outras = area_total_filtro - top_n_area
    elif filtro_tipo_total == "Todos os dados":
        quantidade_outras = quantidade_empresas - filtro_quantidade
        quantidade_dms_outras = quantidade_dms - top_n_quantidade
        area_outras = area_total - top_n_area

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label="Total de DMs",
        value=f"{round(quantidade_dms / 1000, 2)}k",
    )
    col2.metric(
        label="Total de empresas",
        value=f"{quantidade_empresas}",
    )
    col3.metric(
        label="Área total",
        value=f"{round(area_total / 1e6, 2)}M ha",
    )

    col1, col2 = st.columns(2)
    with col1:
        col11, col12 = st.columns(2)
        col11.metric(
            label=f"Top {filtro_quantidade} empresas possuem",
            value=f"{round(top_n_quantidade / 1000, 2)}k DMs ({top_n_quantidade / quantidade_dms * 100:.2f}%)",
        )
        col12.metric(
            label=f"Outras {quantidade_outras} empresas possuem",
            value=f"{round(quantidade_dms_outras / 1000, 2)}k DMs ({quantidade_dms_outras / quantidade_dms * 100:.2f}%)",
        )
    with col2:
        col21, col22 = st.columns(2)
        col21.metric(
            label=f"Top {filtro_quantidade} empresas possuem",
            value=f"{round(top_n_area / 1e6, 2)}M ha ({top_n_area / area_total * 100:.2f}%)",
        )
        col22.metric(
            label=f"Outras {quantidade_outras} empresas possuem",
            value=f"{round(area_outras / 1e6, 2)}M ha ({area_outras / area_total * 100:.2f}%)",
        )

if not filtro_incluir_outras:
    st.plotly_chart(
        Scatter.plot(
            dados_agrupados.head(filtro_quantidade),
            "quantidade",
            "area_total",
            "Área x Quantidade",
            "Área (ha)",
            "Quantidade",
        ),
        use_container_width=True,
    )
else:
    st.plotly_chart(
        Scatter.plot(
            dados_agrupados.head(1000),
            "quantidade",
            "area_total",
            "Área x Quantidade",
            "Área (ha)",
            "Quantidade",
        ),
        use_container_width=True,
    )

# GRÁFICOS DE BARRAS
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            Barplot.plot(
                df_quantidade,
                "quantidade",
                "nome",
                "Quantidade de DMs",
                "Quantidade",
                filtro_altura,
            ),
            use_container_width=True,
        )

    with col2:
        st.plotly_chart(
            Barplot.plot(
                df_area,
                "area_total",
                "nome",
                "Área total",
                "Área (ha)",
                filtro_altura,
            ),
            use_container_width=True,
        )

# GRÁFICOS DE PIZZA
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            Pieplot.plot(df_quantidade, "nome", "quantidade", "Proporção de DMs"),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            Pieplot.plot(df_area, "nome", "area_total", "Proporção de área"),
            use_container_width=True,
        )


# TABELA DE DADOS FILTRADOS
st.markdown("## Dados filtrados")
col1, col2 = st.columns([4, 1])
col1.write(dados_processados)
col2.write(dados_agrupados)
