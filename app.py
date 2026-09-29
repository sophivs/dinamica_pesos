import streamlit as st
from ish.models.calculations import pesos_validos
from ish.views.components import controle_peso, resetar_pesos
from ish.views.dashboard import dashboard_dataset
from ish.views.styles import apply_styles

st.set_page_config(page_title="Calculadora ISH 2025", page_icon="💧", layout="wide", initial_sidebar_state="expanded")
apply_styles()
for chave in ("peso_h", "peso_e", "peso_ec", "peso_r"):
    if chave not in st.session_state:
        st.session_state[chave] = 25

# ============================================================
with st.sidebar:
    st.markdown('<div class="sidebar-title">Calculadora ISH</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sidebar-subtitle">Dados de entrada e ponderação</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Dados de entrada")
    st.caption("Use GeoPackage ou Excel. No Excel, os valores das colunas são usados diretamente como base do cálculo.")

    file_municipios = st.file_uploader(
        "Municípios (.gpkg, .xlsx ou .xls)",
        type=["gpkg", "xlsx", "xls"],
        key="upload_municipios",
    )

    file_otto = st.file_uploader(
        "Otto Bacias N4 (.gpkg, .xlsx ou .xls)",
        type=["gpkg", "xlsx", "xls"],
        key="upload_otto",
    )

    st.divider()
    st.markdown("### Definição dos pesos (%)")
    st.caption("Use o slider ou os botões −/+ para ajustar de 1 em 1.")

    controle_peso("Dimensão Humana", "peso_h")
    controle_peso("Dimensão Econômica", "peso_e")
    controle_peso("Dimensão Ecossistêmica", "peso_ec")
    controle_peso("Dimensão Resiliência", "peso_r")

    pesos = {
        "Humana": st.session_state.peso_h,
        "Econômica": st.session_state.peso_e,
        "Ecossistêmica": st.session_state.peso_ec,
        "Resiliência": st.session_state.peso_r,
    }

    total_pesos = sum(pesos.values())

    if total_pesos == 100:
        st.markdown(
            f'<div class="weight-total-ok">Soma dos pesos: {total_pesos}%</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="weight-total-bad">Soma dos pesos: {total_pesos}% — ajuste para 100%</div>',
            unsafe_allow_html=True,
        )

    st.button(
        "Restaurar pesos iguais (25%)",
        on_click=resetar_pesos,
        use_container_width=True,
    )

# ============================================================
# HEADER
# ============================================================
st.markdown(
    """
    <div class="dashboard-header">
        <h1>Calculadora do ISH 2025</h1>
        <p>Dinâmica de Ponderação por Especialistas — recalcule o ISH e analise o impacto dos novos pesos.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not pesos_validos(pesos):
    st.warning(
        f"A soma atual dos pesos é {total_pesos}%. "
        "Ajuste os quatro pesos na barra lateral até totalizar 100%."
    )
    st.stop()

# ============================================================
# DASHBOARD
# ============================================================

tab_mun, tab_otto = st.tabs(["Municípios", "Otto Bacias N4"])

with tab_mun:
    dashboard_dataset(file_municipios, "Municípios", "municipios", pesos)

with tab_otto:
    dashboard_dataset(file_otto, "Otto Bacias N4", "otto_bacias_n4", pesos)
