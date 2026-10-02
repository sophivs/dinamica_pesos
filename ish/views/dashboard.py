import json
import unicodedata
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

def normalizar_texto(valor):
    """Remove acentos e padroniza texto para comparações."""
    if pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()

    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )


def encontrar_coluna(df, candidatos):
    """Procura uma coluna usando nomes alternativos."""
    colunas_normalizadas = {
        normalizar_texto(coluna): coluna
        for coluna in df.columns
    }

    for candidato in candidatos:
        candidato_normalizado = normalizar_texto(candidato)

        if candidato_normalizado in colunas_normalizadas:
            return colunas_normalizadas[candidato_normalizado]

    return None


# Código IBGE dos estados. Usado para descobrir a UF quando a base possui
# apenas o código do município, sem uma coluna UF explícita.
CODIGOS_UF_IBGE = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
    "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}
CODIGO_IBGE_PARA_UF = {codigo: uf for uf, codigo in CODIGOS_UF_IBGE.items()}

NOMES_UF_PARA_SIGLA = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM", "bahia": "BA",
    "ceara": "CE", "distrito federal": "DF", "espirito santo": "ES", "goias": "GO",
    "maranhao": "MA", "mato grosso": "MT", "mato grosso do sul": "MS", "minas gerais": "MG",
    "para": "PA", "paraiba": "PB", "parana": "PR", "pernambuco": "PE", "piaui": "PI",
    "rio de janeiro": "RJ", "rio grande do norte": "RN", "rio grande do sul": "RS",
    "rondonia": "RO", "roraima": "RR", "santa catarina": "SC", "sao paulo": "SP",
    "sergipe": "SE", "tocantins": "TO",
}


def normalizar_uf(valor):
    """Converte sigla ou nome de estado para uma sigla UF válida."""
    if pd.isna(valor):
        return None

    texto_original = str(valor).strip()
    sigla = texto_original.upper()

    if sigla in CODIGOS_UF_IBGE:
        return sigla

    codigo = texto_original.replace(".0", "")
    if codigo.isdigit():
        return CODIGO_IBGE_PARA_UF.get(codigo.zfill(2))

    return NOMES_UF_PARA_SIGLA.get(normalizar_texto(texto_original))


@st.cache_resource(show_spinner=False)
def carregar_malha_estado(uf):
    """Carrega e simplifica somente a malha municipal da UF selecionada."""
    from geobr import read_municipality

    # O geobr aceita a sigla do estado em code_muni, evitando carregar o Brasil inteiro.
    municipios = read_municipality(
        code_muni=uf,
        year=2025,
        simplified=True,
    )

    municipios = municipios[
        [
            "code_muni",
            "name_muni",
            "abbrev_state",
            "geometry",
        ]
    ].copy()

    # Simplificação adicional em metros: como o mapa exibe somente uma UF,
    # 200 m preserva bem o desenho e reduz ainda mais o GeoJSON enviado ao navegador.
    municipios = municipios.to_crs(epsg=5880)
    municipios["geometry"] = municipios.geometry.simplify(
        tolerance=200,
        preserve_topology=True,
    )
    municipios = municipios.to_crs(epsg=4326)

    municipios["code_muni"] = (
        municipios["code_muni"]
        .astype(int)
        .astype(str)
        .str.zfill(7)
    )

    return municipios


def mapa_municipios(df, beta, mapeamento):
    """Renderiza mapa interativo do ISH somente para a UF selecionada."""

    st.subheader("Mapa do ISH por município")
    st.caption(
        "Selecione primeiro um estado. A malha municipal só será carregada depois "
        "da seleção, deixando o dashboard mais leve."
    )

    dados = df.copy()

    # --------------------------------------------------------
    # IDENTIFICAR COLUNAS DA PLANILHA
    # --------------------------------------------------------
    coluna_codigo = encontrar_coluna(
        dados,
        [
            "Código IBGE",
            "Codigo IBGE",
            "Código do Município",
            "Codigo do Municipio",
            "Código Município",
            "Codigo Municipio",
            "Cod IBGE",
            "Cod Municipio",
            "CD_MUN",
            "CD_MUNICIPIO",
            "code_muni",
            "cod_mun",
        ],
    )

    coluna_municipio = encontrar_coluna(
        dados,
        [
            "Município",
            "Municipio",
            "Nome do Município",
            "Nome do Municipio",
            "NM_MUN",
            "name_muni",
        ],
    )

    coluna_uf = encontrar_coluna(
        dados,
        [
            "UF",
            "Sigla UF",
            "Estado",
            "abbrev_state",
        ],
    )

    if coluna_codigo is None and (coluna_municipio is None or coluna_uf is None):
        st.warning(
            "Para criar o mapa é necessário que a base de municípios tenha "
            "uma coluna de Código IBGE ou as colunas Município + UF."
        )
        return

    # --------------------------------------------------------
    # DESCOBRIR UF SEM CARREGAR NENHUMA GEOMETRIA
    # --------------------------------------------------------
    if coluna_uf is not None:
        dados["_uf_mapa"] = dados[coluna_uf].map(normalizar_uf)
    else:
        dados["_uf_mapa"] = None

    # Se também houver Código IBGE, ele serve como fallback para registros
    # cuja coluna UF esteja vazia ou em um formato não reconhecido.
    if coluna_codigo is not None:
        dados["_codigo_municipio"] = (
            dados[coluna_codigo]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.extract(r"(\d+)", expand=False)
        )
        uf_por_codigo = dados["_codigo_municipio"].str[:2].map(CODIGO_IBGE_PARA_UF)
        dados["_uf_mapa"] = dados["_uf_mapa"].fillna(uf_por_codigo)

    ufs_disponiveis = sorted(
        uf for uf in dados["_uf_mapa"].dropna().unique()
        if uf in CODIGOS_UF_IBGE
    )

    if not ufs_disponiveis:
        st.warning("Não foi possível identificar os estados existentes na base de municípios.")
        return

    uf_selecionada = st.selectbox(
        "Selecione o estado",
        options=ufs_disponiveis,
        index=None,
        placeholder="Escolha uma UF para carregar o mapa...",
        key="mapa_municipios_uf",
    )

    # O ponto principal da otimização: nenhuma geometria é carregada antes daqui.
    if uf_selecionada is None:
        st.info("Selecione um estado acima para visualizar os municípios no mapa.")
        return

    dados = dados.loc[dados["_uf_mapa"] == uf_selecionada].copy()

    try:
        with st.spinner(f"Carregando municípios de {uf_selecionada}..."):
            municipios = carregar_malha_estado(uf_selecionada).copy()
    except Exception as exc:
        st.warning(
            f"Não foi possível carregar a malha municipal de {uf_selecionada}: {exc}"
        )
        return

    # --------------------------------------------------------
    # CRIAR CHAVE PARA LIGAR DADOS E MALHA
    # --------------------------------------------------------
    if coluna_codigo is not None:
        if "_codigo_municipio" not in dados.columns:
            dados["_codigo_municipio"] = (
                dados[coluna_codigo]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.extract(r"(\d+)", expand=False)
            )

        municipios["_codigo_7"] = (
            municipios["code_muni"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.extract(r"(\d+)", expand=False)
            .str.zfill(7)
        )
        municipios["_codigo_6"] = municipios["_codigo_7"].str[:6]

        comprimentos = dados["_codigo_municipio"].dropna().str.len()

        if not comprimentos.empty and comprimentos.median() <= 6:
            municipios["_chave"] = municipios["_codigo_6"]
            dados["_chave"] = dados["_codigo_municipio"].str.zfill(6)
        else:
            municipios["_chave"] = municipios["_codigo_7"]
            dados["_chave"] = dados["_codigo_municipio"].str.zfill(7)

    else:
        # A base já foi filtrada pela UF selecionada; por isso usamos a UF
        # normalizada na chave, inclusive quando "Estado" contém o nome por extenso.
        dados["_chave"] = (
            dados[coluna_municipio].map(normalizar_texto)
            + "-"
            + dados["_uf_mapa"].str.lower()
        )
        municipios["_chave"] = (
            municipios["name_muni"].map(normalizar_texto)
            + "-"
            + municipios["abbrev_state"].str.lower()
        )

    # --------------------------------------------------------
    # JUNTAR SOMENTE OS MUNICÍPIOS DO ESTADO SELECIONADO
    # --------------------------------------------------------
    dados_merge = dados.drop(columns=["geometry"], errors="ignore")

    mapa = municipios.merge(
        dados_merge,
        on="_chave",
        how="left",
    )

    mapa = mapa.loc[mapa["ISH com pesos escolhidos"].notna()].copy()

    if mapa.empty:
        st.warning(
            f"Nenhum município de {uf_selecionada} conseguiu ser associado à malha do IBGE. "
            "Verifique o Código IBGE ou as colunas Município/UF."
        )
        return

    mapa = mapa.reset_index(drop=True)
    mapa["_map_id"] = mapa.index.astype(str)
    geojson = json.loads(mapa.to_json())

    # --------------------------------------------------------
    # INFORMAÇÕES EXIBIDAS NO HOVER
    # --------------------------------------------------------
    hover = {
        "_map_id": False,
        "abbrev_state": True,
        "ISH com pesos escolhidos": ":.3f",
    }

    if beta in mapa.columns:
        hover[beta] = ":.3f"

    if "Diferença vs Beta" in mapa.columns:
        hover["Diferença vs Beta"] = ":+.3f"

    for dimensao in ["Humana", "Econômica", "Ecossistêmica", "Resiliência"]:
        coluna = mapeamento.get(dimensao)
        if coluna and coluna in mapa.columns:
            hover[coluna] = ":.3f"

    # --------------------------------------------------------
    # MAPA
    # --------------------------------------------------------
    fig = px.choropleth(
        mapa,
        geojson=geojson,
        locations="_map_id",
        featureidkey="id",
        color="ISH com pesos escolhidos",
        hover_name="name_muni",
        hover_data=hover,
        color_continuous_scale="RdYlGn",
        range_color=(0, 1),
        labels={
            "abbrev_state": "UF",
            "ISH com pesos escolhidos": "ISH",
            beta: "ISH Beta",
            "Diferença vs Beta": "Diferença",
            mapeamento.get("Humana"): "Humana",
            mapeamento.get("Econômica"): "Econômica",
            mapeamento.get("Ecossistêmica"): "Ecossistêmica",
            mapeamento.get("Resiliência"): "Resiliência",
        },
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
    )

    fig.update_layout(
        height=650,
        margin=dict(l=0, r=0, t=20, b=0),
        coloraxis_colorbar=dict(
            title="ISH",
            thickness=15,
        ),
    )

    st.plotly_chart(
        fig,
        width="stretch",
        theme="streamlit",
        config={"displaylogo": False, "scrollZoom": False},
    )

    st.caption(
        f"{len(mapa):,} municípios de {uf_selecionada} representados no mapa."
        .replace(",", ".")
    )


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
    # MAPA - SOMENTE MUNICÍPIOS
    # --------------------------------------------------------

    eh_municipios = (
        "municip" in normalizar_texto(titulo)
        or "municip" in normalizar_texto(prefixo)
    )

    if eh_municipios:
        st.divider()
        mapa_municipios(
            df,
            beta,
            mapeamento,
        )
        st.divider()

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
