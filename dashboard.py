from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Dashboard SIGMINE",
    page_icon=":pick:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Query ----
conn = st.connection("postgresql", type="sql")
processos_df = conn.query("SELECT * FROM processos;", ttl="5m")
fases_df = conn.query("SELECT * FROM fases;", ttl="5m")


# ---- SIDEBAR ----
with st.sidebar:
    st.header("Selecionar filtros")

    if "fases" not in st.session_state:
        st.session_state.fases = []
    if "uf" not in st.session_state:
        st.session_state.uf = []
    if "quantidade" not in st.session_state:
        st.session_state.quantidade = 10

    filtro_fase = st.multiselect(
        "Fases",
        fases_df["fase"].unique(),
        key="fases",
        placeholder="Selecione uma ou mais fases",
    )
    filtro_uf = st.multiselect(
        "UF", fases_df["uf"].unique(), key="uf", placeholder="Selecione uma ou mais UFs"
    )
    filtro_quantidade = st.slider(
        "Top N empresas",
        min_value=2,
        max_value=30,
        key="quantidade",
        help="Selecione a quantidade de empresas que deseja visualizar",
    )

# ---- FILTER ----
fases_df = fases_df if not filtro_fase else fases_df[fases_df["fase"].isin(filtro_fase)]
fases_df = fases_df if not filtro_uf else fases_df[fases_df["uf"].isin(filtro_uf)]
processos_df["indicator"] = processos_df["numero"].str.cat(processos_df["ano"])
fases_df["indicator"] = fases_df["numero"].str.cat(fases_df["ano"])
processos_df = processos_df.loc[
    processos_df["indicator"].isin(fases_df["indicator"])
].drop(columns=["indicator"])
fases_df = fases_df.drop(columns=["indicator"])

# ---- MAIN PAGE ----
st.title("Dashboard SIGMINE")
st.markdown("##")

col1, col2 = st.columns(2)


@dataclass
class Barplot:
    df: pd.DataFrame
    title: str
    xlabel: str
    ylabel: str

    def __call__(self):
        fig = px.bar(
            self.df,
            x=self.df.values,
            y=self.df.index,
            title=self.title,
            labels={"x": self.xlabel, "y": self.ylabel},
            text_auto=True,
            template="plotly_white",
        )
        fig.update_layout(yaxis={"autorange": "reversed"})
        st.plotly_chart(fig)


@dataclass
class Pieplot:
    df: pd.DataFrame
    title: str

    def __call__(self):
        fig = px.pie(
            self.df,
            values=self.df.values,
            names=self.df.index,
            hole=0.5,
            title=self.title,
            template="plotly_white",
        )
        st.plotly_chart(fig)


@dataclass
class Metric:
    label: str
    value: str
    help: str = None

    def __call__(self):
        st.metric(label=self.label, value=self.value, help=self.help)


def plot_section(barplot: Barplot, pieplot: Pieplot, metric1: Metric, metric2: Metric):
    metric1()
    barplot()
    metric2()
    pieplot()


with col1:
    df = (
        processos_df.value_counts("nome")
        .sort_values(ascending=False)
        .head(filtro_quantidade)
    )
    plot_section(
        Barplot(
            df,
            "Quantidade de DMs por empresa",
            "Quantidade",
            "Empresa",
        ),
        Pieplot(
            df,
            "Proporção de DMs por empresa",
        ),
        Metric(
            label="Total de DMs",
            value=f"{processos_df.shape[0]}",
        ),
        Metric(
            label="Top N empresas representam",
            value=f"{df.sum() / processos_df.shape[0] * 100:.2f}%",
            help="Em relação ao total de DMs",
        ),
    )


with col2:
    area_total = processos_df["area_ha"].sum()
    df = (
        processos_df.groupby("nome")["area_ha"]
        .sum()
        .sort_values(ascending=False)
        .head(filtro_quantidade)
    )
    plot_section(
        Barplot(
            df,
            "Área total por empresa",
            "Área (ha)",
            "Empresa",
        ),
        Pieplot(
            df,
            "Proporção de área total por empresa",
        ),
        Metric(
            label="Área total",
            value=f"{area_total:.2f} ha",
        ),
        Metric(
            label="Top N empresas representam",
            value=f"{df.sum() / area_total * 100:.2f}%",
            help="Em relação à área total",
        ),
    )

# ---- Tabela de dados filtrados ----
st.markdown("## Dados filtrados")
download_df = fases_df.join(
    processos_df.set_index(["numero", "ano"]), on=["numero", "ano"]
)
download_df["data"] = pd.to_datetime(
    download_df[["ano", "mes", "dia"]].rename(
        columns={"ano": "year", "mes": "month", "dia": "day"}
    ),
    errors="coerce",
)
download_df["processo"] = download_df["numero"].str.cat(download_df["ano"], sep="/")
download_df.set_index(["processo", "uf"], inplace=True)
download_df = download_df.drop(columns=["ano", "mes", "dia", "numero"])
st.dataframe(download_df)
st.download_button(
    label="Baixar dados",
    data=download_df.to_csv(index=False).encode(),
    file_name="dados-filtrados.csv",
    mime="text/csv",
)
