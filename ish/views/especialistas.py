"""Interface de registro e consulta das escolhas dos especialistas."""
import pandas as pd
import streamlit as st

from ish.models.especialistas_repository import (
    google_sheets_configurado,
    listar_respostas,
    salvar_resposta,
)


def _tabela_pesos_variaveis(pesos_variaveis):
    linhas = []

    for dimensao, variaveis in pesos_variaveis.items():
        for variavel, peso in variaveis.items():
            linhas.append(
                {
                    "Dimensão": dimensao,
                    "Variável": variavel,
                    "Peso (%)": peso,
                }
            )

    return pd.DataFrame(linhas)


def renderizar_registro_especialistas(pesos_dimensoes, pesos_variaveis):
    st.subheader("Registro dos especialistas")
    st.caption(
        "Ajuste os pesos na barra lateral. Quando considerar a combinação adequada, "
        "registre sua escolha aqui. Cada envio é acrescentado ao Google Sheets."
    )

    st.markdown("#### Combinação atual")

    dimensoes_df = pd.DataFrame(
        {
            "Dimensão": list(pesos_dimensoes.keys()),
            "Peso (%)": list(pesos_dimensoes.values()),
        }
    )

    c1, c2 = st.columns([1, 1.7])

    with c1:
        st.dataframe(
            dimensoes_df,
            width="stretch",
            hide_index=True,
            height=180,
        )
        st.caption(
            f"Soma das dimensões: {sum(pesos_dimensoes.values())}%"
        )

    with c2:
        with st.expander("Ver pesos das variáveis", expanded=False):
            st.dataframe(
                _tabela_pesos_variaveis(pesos_variaveis),
                width="stretch",
                hide_index=True,
                height=300,
            )

    st.divider()

    configurado = google_sheets_configurado()

    if not configurado:
        st.warning(
            "O Google Sheets ainda não está configurado. "
            "Adicione as credenciais em st.secrets para habilitar os registros."
        )

    with st.form("form_registro_especialista", clear_on_submit=True):
        f1, f2 = st.columns(2)

        with f1:
            especialista = st.text_input(
                "Especialista / código *",
                max_chars=120,
                placeholder="Ex.: ESP-01 ou nome do especialista",
            )

        with f2:
            area_atuacao = st.text_input(
                "Área de atuação *",
                max_chars=160,
                placeholder="Ex.: Recursos hídricos, saneamento, geoprocessamento...",
            )

        justificativa = st.text_area(
            "Justificativa técnica",
            max_chars=1500,
            placeholder=(
                "Explique brevemente os principais critérios considerados "
                "para chegar a essa combinação."
            ),
        )

        enviar = st.form_submit_button(
            "Registrar combinação",
            type="primary",
            width="stretch",
            disabled=not configurado,
        )

    if enviar:
        if not especialista.strip():
            st.error("Informe o especialista ou código.")
        elif not area_atuacao.strip():
            st.error("Informe a área de atuação.")
        else:
            try:
                with st.spinner("Salvando resposta..."):
                    identificador = salvar_resposta(
                        especialista=especialista,
                        area_atuacao=area_atuacao,
                        justificativa=justificativa,
                        pesos_dimensoes=pesos_dimensoes,
                        pesos_variaveis=pesos_variaveis,
                    )

                st.success(
                    f"Combinação registrada com sucesso. ID: {identificador}"
                )
            except Exception as exc:
                st.error(
                    "Não foi possível salvar a resposta no Google Sheets. "
                    "Verifique o compartilhamento da planilha, as APIs e os Secrets."
                )
                with st.expander("Detalhes técnicos"):
                    st.code(str(exc))

    st.divider()
    st.markdown("#### Respostas registradas")

    if not configurado:
        st.info(
            "Assim que o Google Sheets for configurado, "
            "as respostas aparecerão aqui."
        )
        return

    atualizar = st.button(
        "Atualizar respostas",
        key="atualizar_respostas_especialistas",
    )

    try:
        with st.spinner("Carregando respostas..."):
            respostas = listar_respostas(
                pesos_dimensoes=pesos_dimensoes,
                pesos_variaveis=pesos_variaveis,
            )
    except Exception as exc:
        st.error(
            "Não foi possível ler as respostas do Google Sheets."
        )
        with st.expander("Detalhes técnicos"):
            st.code(str(exc))
        return

    if respostas.empty:
        st.info("Nenhuma resposta registrada ainda.")
        return

    st.caption(
        f"{len(respostas):,} resposta(s) registrada(s).".replace(",", ".")
    )

    # Os campos de identificação e das dimensões ficam primeiro.
    colunas_prioritarias = [
        "Data/hora",
        "Especialista / código",
        "Área de atuação",
        *[f"Dimensão - {dim}" for dim in pesos_dimensoes],
        "Justificativa técnica",
    ]

    colunas_exibicao = [
        coluna
        for coluna in colunas_prioritarias
        if coluna in respostas.columns
    ]

    colunas_exibicao.extend(
        coluna
        for coluna in respostas.columns
        if coluna not in colunas_exibicao
        and coluna not in {"ID", "Soma dimensões"}
        and not coluna.startswith("Soma variáveis - ")
    )

    st.dataframe(
        respostas[colunas_exibicao],
        width="stretch",
        hide_index=True,
        height=520,
    )
