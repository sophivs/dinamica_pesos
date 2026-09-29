import os
import tempfile
import streamlit as st
from ish.models.repository import carregar_dados, listar_abas

def salvar_upload(uploaded_file, state_key):
    if uploaded_file is None:
        return None

    assinatura = (uploaded_file.name, uploaded_file.size)
    sig_key = f"{state_key}_sig"

    if (
        st.session_state.get(sig_key) == assinatura
        and st.session_state.get(state_key)
        and os.path.exists(st.session_state[state_key])
    ):
        return st.session_state[state_key]

    anterior = st.session_state.get(state_key)
    if anterior and os.path.exists(anterior):
        try:
            os.unlink(anterior)
        except OSError:
            pass

    try:
        suffix = os.path.splitext(uploaded_file.name)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            st.session_state[state_key] = tmp.name
            st.session_state[sig_key] = assinatura
            return tmp.name
    except Exception as exc:
        st.error(f"Erro ao processar o arquivo: {exc}")
        return None


def selecionar_e_carregar(caminho, uploaded_file, prefixo):
    extensao = os.path.splitext(uploaded_file.name)[1].lower()
    aba = 0
    if extensao in (".xlsx", ".xls"):
        abas = listar_abas(caminho)
        preferida = {"municipios": "RESULTADOS_MUNICIPIOS", "otto_bacias_n4": "RESULTADOS_OTTO_N4"}.get(prefixo)
        if preferida in abas:
            aba = preferida
            st.caption(f"Aba detectada automaticamente: {aba}")
        elif len(abas) > 1:
            aba = st.selectbox("Planilha do Excel", abas, key=f"aba_excel_{prefixo}")
        else:
            aba = abas[0]
    return carregar_dados(caminho, extensao, aba)
