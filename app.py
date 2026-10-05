"""Ponto de entrada do dashboard ISH."""
import streamlit as st

from ish.config import ABAS, DIMENSOES, PESOS_DIMENSOES_INICIAIS, PESOS_VARIAVEIS_INICIAIS
from ish.models.calculations import pesos_validos
from ish.views.components import controle_peso
from ish.views.dashboard import dashboard_dataset
from ish.views.especialistas import renderizar_registro_especialistas


st.set_page_config(
    page_title="Calculadora ISH 2025",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)


def chave_dimensao(nome):
    return f"dim_{list(DIMENSOES).index(nome)}"


def chave_variavel(dim, nome):
    return f"var_{list(DIMENSOES).index(dim)}_{list(DIMENSOES[dim]).index(nome)}"


def restaurar_pesos():
    for dim, valor in PESOS_DIMENSOES_INICIAIS.items():
        st.session_state[chave_dimensao(dim)] = valor

    for dim, grupo in PESOS_VARIAVEIS_INICIAIS.items():
        for nome, valor in grupo.items():
            st.session_state[chave_variavel(dim, nome)] = valor


for dim, valor in PESOS_DIMENSOES_INICIAIS.items():
    if chave_dimensao(dim) not in st.session_state:
        st.session_state[chave_dimensao(dim)] = valor

for dim, grupo in PESOS_VARIAVEIS_INICIAIS.items():
    for nome, valor in grupo.items():
        if chave_variavel(dim, nome) not in st.session_state:
            st.session_state[chave_variavel(dim, nome)] = valor


with st.sidebar:
    st.header("Pesos do ISH (%)")
    st.caption("Use o slider ou os botões −/+ para ajustar de 1 em 1.")

    st.subheader("Dimensões")
    for dim in DIMENSOES:
        controle_peso(dim, chave_dimensao(dim))

    pesos_dimensoes = {
        dim: st.session_state[chave_dimensao(dim)]
        for dim in DIMENSOES
    }

    soma = sum(pesos_dimensoes.values())
    if soma == 100:
        st.success(f"Soma das dimensões: {soma}%")
    else:
        st.error(f"Soma das dimensões: {soma}% — ajuste para 100%")

    st.divider()
    st.subheader("Variáveis por dimensão")

    pesos_variaveis = {}
    for dim, variaveis in DIMENSOES.items():
        with st.expander(dim):
            for nome in variaveis:
                controle_peso(nome, chave_variavel(dim, nome))

            pesos_variaveis[dim] = {
                nome: st.session_state[chave_variavel(dim, nome)]
                for nome in variaveis
            }

            total = sum(pesos_variaveis[dim].values())
            if total == 100:
                st.success(f"Soma: {total}%")
            else:
                st.error(f"Soma: {total}% — ajuste para 100%")

    st.button(
        "Restaurar pesos iniciais",
        on_click=restaurar_pesos,
        width="stretch",
    )


st.title("Calculadora do ISH 2025")
st.caption("Dinâmica de Ponderação por Especialistas — dimensões e variáveis")

if not pesos_validos(pesos_dimensoes, pesos_variaveis):
    st.warning(
        "Ajuste a soma das dimensões e de cada grupo de variáveis "
        "para 100% na barra lateral."
    )
    st.stop()


titulos_resultados = [titulo for titulo, _ in ABAS.values()]
tabas = st.tabs([*titulos_resultados, "Registro dos especialistas"])

for (prefixo, (titulo, _)), aba in zip(ABAS.items(), tabas[:-1]):
    with aba:
        dashboard_dataset(
            titulo,
            prefixo,
            pesos_dimensoes,
            pesos_variaveis,
        )

with tabas[-1]:
    renderizar_registro_especialistas(
        pesos_dimensoes=pesos_dimensoes,
        pesos_variaveis=pesos_variaveis,
    )
