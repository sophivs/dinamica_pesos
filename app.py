"""Ponto de entrada do dashboard ISH."""
import streamlit as st

from ish.config import (
    ABAS,
    DIMENSOES,
    PESOS_DIMENSOES_INICIAIS,
    PESOS_VARIAVEIS_INICIAIS,
)
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


# ============================================================
# CHAVES DO SESSION STATE
# ============================================================

def chave_dimensao(nome):
    return f"dim_{list(DIMENSOES).index(nome)}"


def chave_variavel(dim, nome):
    return (
        f"var_{list(DIMENSOES).index(dim)}_"
        f"{list(DIMENSOES[dim]).index(nome)}"
    )


# ============================================================
# RESTAURAR PESOS
# ============================================================

def restaurar_pesos():
    for dim, valor in PESOS_DIMENSOES_INICIAIS.items():
        st.session_state[chave_dimensao(dim)] = valor

    for dim, grupo in PESOS_VARIAVEIS_INICIAIS.items():
        for nome, valor in grupo.items():
            st.session_state[chave_variavel(dim, nome)] = valor


# ============================================================
# INICIALIZAÇÃO DOS PESOS
# ============================================================

for dim, valor in PESOS_DIMENSOES_INICIAIS.items():
    if chave_dimensao(dim) not in st.session_state:
        st.session_state[chave_dimensao(dim)] = valor

for dim, grupo in PESOS_VARIAVEIS_INICIAIS.items():
    for nome, valor in grupo.items():
        if chave_variavel(dim, nome) not in st.session_state:
            st.session_state[chave_variavel(dim, nome)] = valor


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("Pesos do ISH (%)")

    st.caption(
        "Ajuste os pesos utilizados no cálculo do Índice de Segurança "
        "Hídrica. Use o slider ou os botões −/+ para alterar de 1 em 1."
    )

    st.subheader("Dimensões")

    for dim in DIMENSOES:
        controle_peso(
            dim,
            chave_dimensao(dim),
        )

    pesos_dimensoes = {
        dim: st.session_state[chave_dimensao(dim)]
        for dim in DIMENSOES
    }

    soma = sum(pesos_dimensoes.values())

    if soma == 100:
        st.success(f"Soma das dimensões: {soma}%")
    else:
        st.error(
            f"Soma das dimensões: {soma}% — ajuste para 100%"
        )

    st.divider()

    st.subheader("Variáveis por dimensão")

    st.caption(
        "Expanda cada dimensão para alterar o peso das variáveis "
        "que a compõem."
    )

    pesos_variaveis = {}

    for dim, variaveis in DIMENSOES.items():

        with st.expander(dim):

            for nome in variaveis:
                controle_peso(
                    nome,
                    chave_variavel(dim, nome),
                )

            pesos_variaveis[dim] = {
                nome: st.session_state[
                    chave_variavel(dim, nome)
                ]
                for nome in variaveis
            }

            total = sum(
                pesos_variaveis[dim].values()
            )

            if total == 100:
                st.success(
                    f"Soma: {total}%"
                )
            else:
                st.error(
                    f"Soma: {total}% — ajuste para 100%"
                )

    st.divider()

    st.button(
        "Restaurar pesos iniciais",
        on_click=restaurar_pesos,
        width="stretch",
    )


# ============================================================
# CABEÇALHO
# ============================================================

st.title("Calculadora do ISH 2025")

st.caption(
    "Dinâmica de Ponderação por Especialistas — "
    "dimensões e variáveis"
)


# ============================================================
# VALIDAÇÃO DOS PESOS
# ============================================================

pesos_estao_validos = pesos_validos(
    pesos_dimensoes,
    pesos_variaveis,
)


# ============================================================
# ABAS
# ============================================================

titulos_resultados = [
    titulo
    for titulo, _ in ABAS.values()
]

tabas = st.tabs(
    [
        "Início",
        *titulos_resultados,
        "Registro dos especialistas",
    ]
)


# ============================================================
# ABA 1 - INÍCIO
# ============================================================

with tabas[0]:

    st.header("Sobre a aplicação")

    st.markdown(
        """
        Esta aplicação foi desenvolvida para apoiar a **dinâmica de
        ponderação do Índice de Segurança Hídrica (ISH)** por especialistas.

        A ferramenta permite modificar os pesos atribuídos às
        **dimensões do ISH** e às **variáveis que compõem cada dimensão**,
        possibilitando avaliar como diferentes combinações de pesos
        influenciam os resultados do índice.

        O objetivo é permitir que cada especialista analise os componentes
        do ISH, teste diferentes cenários de ponderação e registre a
        combinação que considera mais adequada com base em sua experiência
        e conhecimento técnico.
        """
    )

    st.divider()

    st.subheader("Como utilizar o aplicativo")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            ### 1. Ajuste os pesos

            Utilize o **menu lateral esquerdo** para definir os pesos.

            Primeiro são apresentados os pesos das grandes dimensões
            do ISH.

            A soma dos pesos das dimensões deve ser sempre igual a
            **100%**.
            """
        )

    with col2:
        st.markdown(
            """
            ### 2. Ajuste as variáveis

            Logo abaixo das dimensões estão as
            **variáveis que compõem cada dimensão**.

            Clique sobre o nome da dimensão para expandir o grupo e
            alterar seus pesos.

            Dentro de cada dimensão, a soma dos pesos das variáveis
            também deve ser igual a **100%**.
            """
        )

    with col3:
        st.markdown(
            """
            ### 3. Analise e registre

            Após ajustar os pesos, consulte os resultados nas abas
            disponíveis.

            Quando considerar que encontrou a combinação mais adequada,
            acesse **Registro dos especialistas** e registre sua escolha.
            """
        )

    st.divider()

    st.subheader("Resultados")

    st.markdown(
        """
        As abas de resultados apresentam o ISH recalculado de acordo
        com os pesos definidos pelo especialista.

        As alterações realizadas no menu lateral são aplicadas
        automaticamente aos cálculos e às visualizações da aplicação.

        Dessa forma, é possível comparar diferentes configurações antes
        de definir a combinação final.
        """
    )

    st.divider()

    st.subheader("Registro dos especialistas")

    st.markdown(
        """
        Depois de finalizar sua avaliação, acesse a aba
        **Registro dos especialistas**.

        Nessa seção, o especialista deverá informar sua identificação,
        sua área de atuação e, opcionalmente, uma justificativa técnica
        para a escolha realizada.

        No momento do envio, a aplicação registra automaticamente a
        combinação de pesos que estiver configurada no menu lateral,
        incluindo os pesos das dimensões e os pesos das respectivas
        variáveis.

        As respostas já registradas também podem ser consultadas nessa
        mesma aba.
        """
    )

    st.info(
        "Importante: antes de analisar os resultados ou registrar uma "
        "resposta, verifique se a soma das dimensões e das variáveis de "
        "cada grupo está igual a 100%."
    )

    st.divider()

    st.subheader("Configuração atual")

    if pesos_estao_validos:
        st.success(
            "Os pesos configurados atualmente são válidos. "
            "Você já pode analisar os resultados e registrar sua escolha."
        )
    else:
        st.warning(
            "A configuração atual ainda não é válida. "
            "Utilize o menu lateral esquerdo para ajustar a soma das "
            "dimensões e das variáveis para 100%."
        )


# ============================================================
# ABAS DE RESULTADOS
# ============================================================

for (
    prefixo,
    (titulo, _)
), aba in zip(
    ABAS.items(),
    tabas[1:-1],
):

    with aba:

        if not pesos_estao_validos:

            st.warning(
                "Para visualizar os resultados, ajuste os pesos no "
                "menu lateral esquerdo."
            )

            st.info(
                "A soma das dimensões e a soma das variáveis dentro "
                "de cada dimensão devem ser iguais a 100%."
            )

        else:

            dashboard_dataset(
                titulo,
                prefixo,
                pesos_dimensoes,
                pesos_variaveis,
            )


# ============================================================
# ABA - REGISTRO DOS ESPECIALISTAS
# ============================================================

with tabas[-1]:

    if not pesos_estao_validos:

        st.warning(
            "Antes de registrar sua escolha, ajuste os pesos no "
            "menu lateral esquerdo."
        )

        st.info(
            "A soma das dimensões e a soma das variáveis dentro "
            "de cada dimensão devem ser iguais a 100%."
        )

    else:

        renderizar_registro_especialistas(
            pesos_dimensoes=pesos_dimensoes,
            pesos_variaveis=pesos_variaveis,
        )