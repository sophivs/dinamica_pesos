import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from ish.config import BETA, Q95, DIMENSOES
from ish.models.repository import carregar_dataset
from ish.models.calculations import calcular_ish, criar_faixas
from ish.views.components import excel_bytes, layout_grafico

@st.cache_data(show_spinner=False)
def dados_fixos(prefixo):
    return carregar_dataset(prefixo)

def dashboard_dataset(titulo, prefixo, pesos_dimensoes, pesos_variaveis):
    try:
        with st.spinner(f"Carregando {titulo}..."):
            origem = dados_fixos(prefixo)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        st.error(f"Não foi possível carregar os dados fixos: {exc}")
        return

    if origem.empty:
        st.warning("A planilha não contém registros.")
        return

    df = calcular_ish(origem, pesos_dimensoes, pesos_variaveis)
    novo = df["ISH com pesos escolhidos"]
    beta = BETA
    possui_beta = True
    mapeamento = {dim: f"{dim} ponderada" for dim in DIMENSOES}
    mapeamento["Fator Q95"] = Q95

    # --------------------------------------------------------
    # FILTROS / AÇÕES
    # --------------------------------------------------------
    filtro_col, csv_col, xlsx_col = st.columns([5, 1.25, 1.25])

    with filtro_col:
        busca = st.text_input(
            "Pesquisar nos resultados",
            placeholder="Pesquisar em qualquer coluna...",
            key=f"busca_{prefixo}",
        )

    csv = df.to_csv(index=False).encode("utf-8-sig")

    with csv_col:
        st.download_button(
            "Baixar CSV",
            csv,
            file_name=f"ISH_{prefixo}.csv",
            mime="text/csv",
            width="stretch",
        )

    with xlsx_col:
        st.download_button(
            "Baixar Excel",
            excel_bytes(df),
            file_name=f"ISH_{prefixo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------
    st.subheader("Visão geral")

    if possui_beta:
        diferenca = df["Diferença vs Beta"]
        aumentaram = int((diferenca > 0).sum())
        diminuiram = int((diferenca < 0).sum())

        kpis = st.columns(7)
        kpis[0].metric("Total de registros", f"{len(df):,}".replace(",", "."))
        kpis[1].metric("ISH médio", f"{novo.mean():.3f}")
        kpis[2].metric("ISH mínimo", f"{novo.min():.3f}")
        kpis[3].metric("ISH máximo", f"{novo.max():.3f}")
        kpis[4].metric("Diferença média", f"{diferenca.mean():+.3f}")
        kpis[5].metric(
            "Aumentaram",
            f"{aumentaram:,}".replace(",", "."),
            f"{aumentaram / len(df) * 100:.1f}%",
        )
        kpis[6].metric(
            "Diminuíram",
            f"{diminuiram:,}".replace(",", "."),
            f"-{diminuiram / len(df) * 100:.1f}%",
            delta_color="inverse",
        )
    else:
        kpis = st.columns(4)
        kpis[0].metric("Total de registros", f"{len(df):,}".replace(",", "."))
        kpis[1].metric("ISH médio", f"{novo.mean():.3f}")
        kpis[2].metric("ISH mínimo", f"{novo.min():.3f}")
        kpis[3].metric("ISH máximo", f"{novo.max():.3f}")

    # --------------------------------------------------------
    # GRÁFICOS - LINHA 1
    # --------------------------------------------------------
    st.subheader("Análise dos resultados")

    df = df.copy()
    df["_Faixa ISH"] = criar_faixas(novo)
    faixa = (
        df.groupby("_Faixa ISH", observed=True)
        .size()
        .reset_index(name="Registros")
    )

    c1, c2, c3 = st.columns([1.1, 1, 1])

    with c1:
        fig_faixa = px.bar(
            faixa,
            x="_Faixa ISH",
            y="Registros",
            title="Registros por faixa de ISH",
            text_auto=True,

        )
        fig_faixa.update_xaxes(title="Faixa de ISH")
        fig_faixa.update_yaxes(title="Quantidade")
        st.plotly_chart(layout_grafico(fig_faixa), width="stretch", theme="streamlit")

    with c2:
        if possui_beta:
            fig_diff = px.histogram(
                df,
                x="Diferença vs Beta",
                nbins=35,
                title="Distribuição das diferenças vs Beta",

            )
            fig_diff.add_vline(
                x=0,
                line_dash="dash",

            )
            fig_diff.update_xaxes(title="Diferença (novo ISH − Beta)")
            fig_diff.update_yaxes(title="Quantidade")
        else:
            fig_diff = px.histogram(
                df,
                x="ISH com pesos escolhidos",
                nbins=35,
                title="Distribuição do novo ISH",

            )
            fig_diff.update_xaxes(title="ISH")
        st.plotly_chart(layout_grafico(fig_diff), width="stretch", theme="streamlit")

    with c3:
        faixa_acum = faixa.copy()
        faixa_acum["Acumulado (%)"] = (
            faixa_acum["Registros"].cumsum() / faixa_acum["Registros"].sum() * 100
        )

        fig_acum = go.Figure()
        fig_acum.add_bar(
            x=faixa_acum["_Faixa ISH"],
            y=faixa_acum["Registros"],
            name="Registros",

        )
        fig_acum.add_scatter(
            x=faixa_acum["_Faixa ISH"],
            y=faixa_acum["Acumulado (%)"],
            name="Acumulado (%)",
            mode="lines+markers",
            yaxis="y2",

        )
        fig_acum.update_layout(
            title="ISH acumulado por faixa",
            yaxis=dict(title="Quantidade"),
            yaxis2=dict(
                title="% acumulado",
                overlaying="y",
                side="right",
                range=[0, 105],
            ),
        )
        st.plotly_chart(layout_grafico(fig_acum), width="stretch", theme="streamlit")

    # --------------------------------------------------------
    # GRÁFICOS - LINHA 2
    # --------------------------------------------------------
    c4, c5, c6 = st.columns([1, 1, 1.35])

    with c4:
        dimensoes = [
            ("Humana", mapeamento["Humana"]),
            ("Econômica", mapeamento["Econômica"]),
            ("Ecossistêmica", mapeamento["Ecossistêmica"]),
            ("Resiliência", mapeamento["Resiliência"]),
        ]

        medias = pd.DataFrame(
            {
                "Dimensão": [x[0] for x in dimensoes],
                "Média": [df[x[1]].mean() for x in dimensoes],
            }
        ).sort_values("Média")

        fig_medias = px.bar(
            medias,
            x="Média",
            y="Dimensão",
            orientation="h",
            title="Média por dimensão",
            text_auto=".3f",

        )
        st.plotly_chart(layout_grafico(fig_medias), width="stretch", theme="streamlit")

    with c5:
        if possui_beta:
            aumentaram = int((df["Diferença vs Beta"] > 0).sum())
            diminuiram = int((df["Diferença vs Beta"] < 0).sum())
            iguais = int((df["Diferença vs Beta"] == 0).sum())
            sem_beta = int(df["Diferença vs Beta"].isna().sum())

            situacao = pd.DataFrame(
                {
                    "Situação": ["Aumentaram", "Diminuíram", "Sem alteração", "Sem Beta"],
                    "Quantidade": [aumentaram, diminuiram, iguais, sem_beta],
                }
            )

            fig_pizza = px.pie(
                situacao,
                names="Situação",
                values="Quantidade",
                hole=.58,
                title="Situação em relação ao ISH Beta",
                color="Situação",
            )
            fig_pizza.update_traces(textposition="inside", textinfo="percent")
            st.plotly_chart(layout_grafico(fig_pizza), width="stretch", theme="streamlit")
        else:
            fig_q95 = px.histogram(
                df,
                x=mapeamento["Fator Q95"],
                nbins=30,
                title="Distribuição do fator Q95",

            )
            st.plotly_chart(layout_grafico(fig_q95), width="stretch", theme="streamlit")

    with c6:
        box_data = pd.DataFrame(
            {
                "Humana": df[mapeamento["Humana"]],
                "Econômica": df[mapeamento["Econômica"]],
                "Ecossistêmica": df[mapeamento["Ecossistêmica"]],
                "Resiliência": df[mapeamento["Resiliência"]],
            }
        ).melt(var_name="Dimensão", value_name="Valor")

        fig_box = px.box(
            box_data,
            x="Dimensão",
            y="Valor",
            color="Dimensão",
            title="Distribuição do ISH por dimensão",

        )
        fig_box.update_layout(showlegend=False)
        st.plotly_chart(layout_grafico(fig_box), width="stretch", theme="streamlit")

    # --------------------------------------------------------
    # COMPARAÇÃO BETA
    # --------------------------------------------------------
    if possui_beta:
        with st.expander("Comparação detalhada: ISH Beta × novo ISH"):
            scatter_df = df[[beta, "ISH com pesos escolhidos"]].dropna()

            fig_scatter = px.scatter(
                scatter_df,
                x=beta,
                y="ISH com pesos escolhidos",
                opacity=.5,
                title="Comparação entre o ISH Beta e o ISH recalculado",

            )

            if not scatter_df.empty:
                minimo = min(scatter_df.min())
                maximo = max(scatter_df.max())
                fig_scatter.add_shape(
                    type="line",
                    x0=minimo,
                    y0=minimo,
                    x1=maximo,
                    y1=maximo,
                    line=dict(dash="dash"),
                )

            st.plotly_chart(layout_grafico(fig_scatter, 430), width="stretch", theme="streamlit")

    # --------------------------------------------------------
    # TABELA
    # --------------------------------------------------------
    st.subheader("Dados detalhados")

    tabela = df.drop(columns=["_Faixa ISH"], errors="ignore")

    if busca:
        mascara = tabela.astype(str).apply(
            lambda col: col.str.contains(busca, case=False, na=False)
        ).any(axis=1)
        tabela = tabela.loc[mascara]

    st.caption(f"{len(tabela):,} registros exibidos".replace(",", "."))
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        height=500,
    )

    with st.expander("Informações dos dados"):
        a, b, c = st.columns(3)
        a.metric("Registros", len(origem))
        b.metric("Colunas de origem", len(origem.columns))
        c.metric("Fonte", "Excel incluído")
