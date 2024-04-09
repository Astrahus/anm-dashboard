from datetime import datetime, timedelta

import streamlit as st

TITULADOS = {
    "AUTORIZAÇÃO DE PESQUISA",
    "CONCESSÃO DE LAVRA",
    "DIREITO DE REQUERER A LAVRA",
    "LAVRA GARIMPEIRA",
    "LICENCIAMENTO",
    "REGISTRO DE EXTRAÇÃO",
    "REQUERIMENTO DE LAVRA",
}


class Callbacks:
    fases: list = None
    ufs: list = None

    @staticmethod
    def configure(processos):
        Callbacks.fases = processos.fase.cat.categories
        Callbacks.ufs = processos.uf.cat.categories

    @staticmethod
    def set_fases_all():
        for i, _ in enumerate(Callbacks.fases):
            st.session_state[f"fase_{i}"] = True

    @staticmethod
    def set_fases_titulados():
        for i, fase in enumerate(Callbacks.fases):
            st.session_state[f"fase_{i}"] = fase in TITULADOS

    @staticmethod
    def reset_fases():
        for i, _ in enumerate(Callbacks.fases):
            st.session_state[f"fase_{i}"] = False

    @staticmethod
    def set_uf_all():
        for i, _ in enumerate(Callbacks.ufs):
            st.session_state[f"uf_{i}"] = True

    @staticmethod
    def reset_uf():
        for i, _ in enumerate(Callbacks.ufs):
            st.session_state[f"uf_{i}"] = False


class Filtro:

    def __init__(self, processos):
        Callbacks.configure(processos)
        with st.sidebar:
            self.fases = self.criar_filtro_fases()
            self.ufs = self.criar_filtro_estados()
            self.ultima_arrecadacao = self.criar_filtro_ultima_arrecadacao()
            self.quantidade = self.criar_filtro_quantidade()
            self.altura = self.criar_filtro_altura()
            self.usando_titulares = self.fases == TITULADOS

    def criar_filtro_fases(self):
        with st.popover("Fases", use_container_width=True):
            st.markdown("### Fases")
            NCOLS = 3
            cols = st.columns(NCOLS)
            checkboxes = {}
            for i, fase in enumerate(Callbacks.fases):
                if not hasattr(st.session_state, f"fase_{i}"):
                    st.session_state[f"fase_{i}"] = fase in TITULADOS
                checkboxes[fase] = cols[i % NCOLS].checkbox(
                    fase,
                    key=f"fase_{i}",
                )
            col1, col2, col3 = st.columns(3)
            col1.button("Selecionar todas", on_click=Callbacks.set_fases_all)
            col2.button("Selecionar titulados", on_click=Callbacks.set_fases_titulados)
            col3.button("Desmarcar todas", on_click=Callbacks.reset_fases)

        return {fase for fase, marcado in checkboxes.items() if marcado}

    def criar_filtro_estados(self):
        with st.popover("Estados", use_container_width=True):
            st.markdown("### Estados")
            NCOLS = 4
            uf_cols = st.columns(NCOLS)
            checkboxes = {}
            for i, uf in enumerate(Callbacks.ufs):
                if not hasattr(st.session_state, f"uf_{i}"):
                    st.session_state[f"uf_{i}"] = True
                checkboxes[uf] = uf_cols[i % NCOLS].checkbox(
                    uf,
                    key=f"uf_{i}",
                )
            col1, col2 = st.columns(2)
            col1.button("Selecionar todos", on_click=Callbacks.set_uf_all)
            col2.button("Desmarcar todos", on_click=Callbacks.reset_uf)

        estados = {uf for uf, marcado in checkboxes.items() if marcado}
        return estados

    def criar_filtro_ultima_arrecadacao(self):
        recente = st.checkbox("Filtrar por arrecadação mais recente", value=False)
        if recente:
            return st.date_input(
                "Data de corte",
                value=datetime.now() - timedelta(weeks=12),
                min_value=datetime(1930, 1, 1),
                format="DD/MM/YYYY",
            )

        return None

    def criar_filtro_quantidade(self):
        quantidade = st.number_input(
            "Quantidade de empresas nos gráficos",
            min_value=1,
            max_value=100,
            value=20,
        )

        return quantidade

    def criar_filtro_altura(self):
        return 60 * self.quantidade
