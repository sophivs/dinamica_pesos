"""Controles nativos do Streamlit e exportação de resultados."""
import io
import pandas as pd
import streamlit as st


def alterar_peso(chave, delta):
    st.session_state[chave] = max(0, min(100, st.session_state[chave] + delta))


def controle_peso(label, chave):
    st.markdown(f"**{label}**")
    slider, menos, valor, mais = st.columns([4, 1.5, 1.7, 1.5], gap="small")
    with slider:
        st.slider(label, 0, 100, step=1, key=chave, label_visibility="collapsed")
    with menos:
        st.button("−1", key=f"{chave}_menos", on_click=alterar_peso, args=(chave, -1), width="stretch")
    with valor:
        st.write(f"{st.session_state[chave]}%")
    with mais:
        st.button("+1", key=f"{chave}_mais", on_click=alterar_peso, args=(chave, 1), width="stretch")


def excel_bytes(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Resultados", index=False)
        ws = writer.book["Resultados"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for col_cells in ws.columns:
            tamanho = max(len(str(cell.value)) if cell.value is not None else 0 for cell in col_cells)
            ws.column_dimensions[col_cells[0].column_letter].width = min(tamanho + 2, 35)
    return buffer.getvalue()


def layout_grafico(fig, altura=330):
    fig.update_layout(height=altura, margin=dict(l=25, r=20, t=55, b=35), legend=dict(orientation="h", y=1.08, x=0))
    return fig
