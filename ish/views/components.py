import io
import pandas as pd
import streamlit as st
from ish.config import COLUNAS_PADRAO

def alterar_peso(chave, delta):
    st.session_state[chave] = max(0, min(100, st.session_state[chave] + delta))

def resetar_pesos():
    for chave in ["peso_h", "peso_e", "peso_ec", "peso_r"]:
        st.session_state[chave] = 25

def controle_peso(label, chave):
    st.markdown(f"**{label}**")
    c_slider, c_minus, c_val, c_plus = st.columns([6, 1, 1.4, 1])

    with c_slider:
        st.slider(
            label,
            0,
            100,
            step=1,
            key=chave,
            label_visibility="collapsed",
        )

    with c_minus:
        st.button(
            "−",
            key=f"{chave}_menos",
            on_click=alterar_peso,
            args=(chave, -1),
            use_container_width=True,
        )

    with c_val:
        st.markdown(
            f"<div style='text-align:center;padding-top:7px;font-weight:700'>"
            f"{st.session_state[chave]}%</div>",
            unsafe_allow_html=True,
        )

    with c_plus:
        st.button(
            "+",
            key=f"{chave}_mais",
            on_click=alterar_peso,
            args=(chave, 1),
            use_container_width=True,
        )

# ============================================================
# DADOS
# ============================================================

def interface_mapeamento(gdf, prefixo):
    colunas = [c for c in gdf.columns if c != "geometry"]

    # Aceita tanto os nomes técnicos do GeoPackage quanto os nomes amigáveis
    # usados no Excel da dinâmica de ponderação.
    aliases = {
        "Humana": ["ISH_humana_V2", "Humana"],
        "Econômica": ["ISH_economica_BETA_2025", "Econômica", "Economica"],
        "Ecossistêmica": ["ISH_ecossistemica_BETA_2025", "Ecossistêmica", "Ecossistemica"],
        "Resiliência": ["ISH_resiliencia_BETA_2025", "Resiliência", "Resiliencia"],
        "Fator Q95": ["fator_Q95", "Fator Q95", "Fator_Q95"],
        "ISH Beta Original": ["ISH_Q95_BETA_2025", "ISH Beta 25/25/25/25", "ISH Beta"],
    }

    detectado = {}
    for campo, candidatos in aliases.items():
        detectado[campo] = next((c for c in candidatos if c in colunas), None)

    campos_obrigatorios = ["Humana", "Econômica", "Ecossistêmica", "Resiliência", "Fator Q95"]
    if all(detectado[c] is not None for c in campos_obrigatorios):
        if detectado["ISH Beta Original"] is None:
            detectado["ISH Beta Original"] = "Não calcular diferença"
        return detectado

    obrigatorias = {
        k: v for k, v in COLUNAS_PADRAO.items()
        if k != "ISH Beta Original"
    }

    if all(v in colunas for v in obrigatorias.values()):
        resultado = COLUNAS_PADRAO.copy()
        if resultado["ISH Beta Original"] not in colunas:
            resultado["ISH Beta Original"] = "Não calcular diferença"
        return resultado

    st.warning("Algumas colunas padrão não foram encontradas. Faça o mapeamento.")

    with st.expander("Mapeamento de colunas", expanded=True):
        c1, c2, c3 = st.columns(3)

        def seletor(container, titulo, nome):
            padrao = COLUNAS_PADRAO[nome]
            indice = colunas.index(padrao) if padrao in colunas else 0
            with container:
                return st.selectbox(
                    titulo,
                    colunas,
                    index=indice,
                    key=f"{prefixo}_{nome}",
                )

        humana = seletor(c1, "Dimensão Humana", "Humana")
        economica = seletor(c2, "Dimensão Econômica", "Econômica")
        ecossistemica = seletor(c3, "Dimensão Ecossistêmica", "Ecossistêmica")
        resiliencia = seletor(c1, "Dimensão Resiliência", "Resiliência")
        q95 = seletor(c2, "Fator Q95", "Fator Q95")

        opcoes_beta = ["Não calcular diferença"] + colunas
        beta_padrao = COLUNAS_PADRAO["ISH Beta Original"]
        beta_idx = opcoes_beta.index(beta_padrao) if beta_padrao in opcoes_beta else 0
        with c3:
            beta = st.selectbox(
                "ISH Beta Original",
                opcoes_beta,
                index=beta_idx,
                key=f"{prefixo}_beta",
            )

    return {
        "Humana": humana,
        "Econômica": economica,
        "Ecossistêmica": ecossistemica,
        "Resiliência": resiliencia,
        "Fator Q95": q95,
        "ISH Beta Original": beta,
    }


def excel_bytes(df):
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Resultados", index=False)
        ws = writer.book["Resultados"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        for col_cells in ws.columns:
            tamanho = max(
                len(str(cell.value)) if cell.value is not None else 0
                for cell in col_cells
            )
            ws.column_dimensions[col_cells[0].column_letter].width = min(tamanho + 2, 35)

    return buffer.getvalue()

def layout_grafico(fig, altura=330):
    fig.update_layout(
        height=altura,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=25, r=20, t=55, b=35),
        font=dict(size=11, color="#334e68"),
        title_font=dict(size=15, color="#102a43"),
        legend=dict(orientation="h", y=1.08, x=0),
    )
    fig.update_xaxes(gridcolor="#edf2f7")
    fig.update_yaxes(gridcolor="#edf2f7")
    return fig


