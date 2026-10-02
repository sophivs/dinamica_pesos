import json
import unicodedata
from pathlib import Path
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


# Classes relativas municipais do ISH (quintis nacionais fornecidos para o projeto).
# Os limites ficam fixos para que um município tenha a mesma classe independentemente
# do estado selecionado no mapa.
CLASSES_ISH_MUNICIPAL = ["Mínimo", "Baixo", "Médio", "Alto", "Máximo"]
LIMITES_ISH_MUNICIPAL = [-float("inf"), 0.595502, 0.639708, 0.673738, 0.704601, float("inf")]
CORES_ISH_MUNICIPAL = {
    "Mínimo": "#d73027",
    "Baixo": "#f46d43",
    "Médio": "#fee08b",
    "Alto": "#1a9850",
    "Máximo": "#4575b4",
}
INTERVALOS_ISH_MUNICIPAL = {
    "Mínimo": "0,294885 a 0,595502",
    "Baixo": "> 0,595502 a 0,639708",
    "Médio": "> 0,639708 a 0,673738",
    "Alto": "> 0,673738 a 0,704601",
    "Máximo": "> 0,704601 a 0,832294",
}

REGIOES_BRASIL = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}

UF_PARA_REGIAO = {
    uf: regiao
    for regiao, ufs in REGIOES_BRASIL.items()
    for uf in ufs
}

CLASSES_ISH_OTTO = ["Mínimo", "Baixo", "Médio", "Alto", "Máximo"]
CORES_ISH_OTTO = CORES_ISH_MUNICIPAL.copy()


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

    # Classificação relativa municipal pelos limites nacionais fornecidos.
    # Não usamos qcut após filtrar a UF, pois isso criaria quintis diferentes
    # para cada estado e impediria a comparação entre municípios do Brasil.
    mapa["Classe relativa"] = pd.cut(
        mapa["ISH com pesos escolhidos"],
        bins=LIMITES_ISH_MUNICIPAL,
        labels=CLASSES_ISH_MUNICIPAL,
        include_lowest=True,
        right=True,
        ordered=True,
    )
    mapa["Intervalo da classe"] = mapa["Classe relativa"].map(INTERVALOS_ISH_MUNICIPAL)

    geojson = json.loads(mapa.to_json())

    # --------------------------------------------------------
    # INFORMAÇÕES EXIBIDAS NO HOVER
    # --------------------------------------------------------
    hover = {
        "_map_id": False,
        "abbrev_state": True,
        "ISH com pesos escolhidos": ":.3f",
        "Classe relativa": True,
        "Intervalo da classe": True,
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
        color="Classe relativa",
        hover_name="name_muni",
        hover_data=hover,
        color_discrete_map=CORES_ISH_MUNICIPAL,
        category_orders={"Classe relativa": CLASSES_ISH_MUNICIPAL},
        labels={
            "abbrev_state": "UF",
            "ISH com pesos escolhidos": "ISH",
            "Classe relativa": "Classe relativa",
            "Intervalo da classe": "Intervalo do ISH",
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
        legend=dict(
            title="Classe relativa",
            traceorder="normal",
        ),
    )

    st.plotly_chart(
        fig,
        width="stretch",
        theme="streamlit",
        config={"displaylogo": False, "scrollZoom": False},
    )

    st.caption(
        "Classes relativas municipais: "
        "Mínimo (0,294885–0,595502) · "
        "Baixo (>0,595502–0,639708) · "
        "Médio (>0,639708–0,673738) · "
        "Alto (>0,673738–0,704601) · "
        "Máximo (>0,704601–0,832294)."
    )
    st.caption(
        f"{len(mapa):,} municípios de {uf_selecionada} representados no mapa."
        .replace(",", ".")
    )


def obter_coluna_wts_pk(df):
    return encontrar_coluna(
        df,
        [
            "wts_pk",
            "WTS_PK",
            "wts pk",
            "ottobacia",
            "otto",
            "id_otto",
            "codigo_otto",
            "cod_otto",
        ],
    )


@st.cache_resource(show_spinner=False)
def carregar_limites_estaduais():
    from geobr import read_state

    estados = read_state(code_state="all", year=2025, simplified=True)
    estados = estados[["abbrev_state", "name_state", "geometry"]].copy()
    estados["regiao"] = estados["abbrev_state"].map(UF_PARA_REGIAO)

    estados = estados.to_crs(epsg=5880)
    estados["geometry"] = estados.geometry.simplify(
        tolerance=300,
        preserve_topology=True,
    )
    estados = estados.to_crs(epsg=4326)
    return estados


@st.cache_resource(show_spinner=False)
def localizar_shapefile_otto():
    candidatos = [
        Path("OTTO_N4_APP_LEVE.shp"),
        Path("./OTTO_N4_APP_LEVE.shp"),
        Path("./dados/OTTO_N4_APP_LEVE.shp"),
        Path("./data/OTTO_N4_APP_LEVE.shp"),
        Path("./assets/OTTO_N4_APP_LEVE.shp"),
        Path("./ish/data/OTTO_N4_APP_LEVE.shp"),
        Path("/mnt/data/OTTO_N4_APP_LEVE.shp"),
    ]

    for caminho in candidatos:
        if caminho.exists():
            return caminho

    raise FileNotFoundError(
        "Não encontrei o shapefile OTTO_N4_APP_LEVE.shp. "
        "Coloque os arquivos .shp, .shx, .dbf, .prj e .cpg na mesma pasta do app "
        "ou em ./dados, ./data, ./assets ou ./ish/data."
    )


@st.cache_resource(show_spinner=False)
def carregar_ottobacias():
    import geopandas as gpd

    caminho = localizar_shapefile_otto()
    otto = gpd.read_file(caminho)

    if "wts_pk" not in otto.columns:
        coluna_wts = encontrar_coluna(otto, ["wts_pk", "WTS_PK", "wts pk"])
        if not coluna_wts:
            raise ValueError(
                "O shapefile de ottobacias precisa ter a coluna wts_pk para o relacionamento com o Excel."
            )
        otto = otto.rename(columns={coluna_wts: "wts_pk"})

    if otto.crs is None:
        otto = otto.set_crs(epsg=4674, allow_override=True)

    if otto.crs.to_epsg() != 4326:
        otto = otto.to_crs(epsg=4326)

    # Simplificação leve para reduzir o GeoJSON enviado ao navegador.
    otto = otto.to_crs(epsg=5880)
    otto["geometry"] = otto.geometry.simplify(
        tolerance=150,
        preserve_topology=True,
    )
    otto = otto.to_crs(epsg=4326)

    otto["wts_pk"] = (
        otto["wts_pk"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.extract(r"(\d+)", expand=False)
    )

    estados = carregar_limites_estaduais()[["abbrev_state", "regiao", "geometry"]].copy()
    pontos = otto[["wts_pk", "geometry"]].copy()
    pontos["geometry"] = pontos.representative_point()

    pontos = pontos.sjoin(
        estados,
        how="left",
        predicate="within",
    )[["wts_pk", "abbrev_state", "regiao"]]

    otto = otto.merge(pontos, on="wts_pk", how="left")
    return otto


def construir_classes_quantis(valores, labels):
    serie = pd.Series(valores).dropna().astype(float)
    if serie.empty:
        return None, None

    quantis = serie.quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0]).tolist()

    limites = [quantis[0]]
    for valor in quantis[1:]:
        if valor <= limites[-1]:
            valor = limites[-1] + 1e-9
        limites.append(valor)

    intervalos = {
        labels[0]: f"{limites[0]:.6f} a {limites[1]:.6f}",
        labels[1]: f"> {limites[1]:.6f} a {limites[2]:.6f}",
        labels[2]: f"> {limites[2]:.6f} a {limites[3]:.6f}",
        labels[3]: f"> {limites[3]:.6f} a {limites[4]:.6f}",
        labels[4]: f"> {limites[4]:.6f} a {limites[5]:.6f}",
    }
    return limites, intervalos


def mapa_ottobacias(df, beta, mapeamento):
    st.subheader("Mapa do ISH por ottobacia")
    st.caption(
        "Selecione uma macrorregião para carregar apenas as ottobacias daquela área. "
        "O mapa usa o shapefile OTTO_N4_APP_LEVE, com fundo do Brasil e divisões estaduais."
    )

    coluna_wts = obter_coluna_wts_pk(df)
    if coluna_wts is None:
        st.warning(
            "Para criar o mapa de ottobacias, a base precisa ter uma coluna wts_pk para o relacionamento com o shapefile."
        )
        return

    regiao = st.selectbox(
        "Selecione a região",
        options=list(REGIOES_BRASIL.keys()),
        index=None,
        placeholder="Escolha Norte, Nordeste, Centro-Oeste, Sudeste ou Sul...",
        key="mapa_otto_regiao",
    )

    if regiao is None:
        st.info("Selecione uma região acima para visualizar as ottobacias no mapa.")
        return

    try:
        with st.spinner(f"Carregando ottobacias da região {regiao}..."):
            otto = carregar_ottobacias().copy()
            estados = carregar_limites_estaduais().copy()
    except Exception as exc:
        st.warning(f"Não foi possível carregar o shapefile das ottobacias: {exc}")
        return

    dados = df.copy()
    dados["_wts_pk"] = (
        dados[coluna_wts]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.extract(r"(\d+)", expand=False)
    )

    limites, intervalos = construir_classes_quantis(
        df["ISH com pesos escolhidos"],
        CLASSES_ISH_OTTO,
    )
    if limites is None:
        st.warning("Não há valores suficientes de ISH para classificar as ottobacias.")
        return

    ufs_regiao = REGIOES_BRASIL[regiao]
    otto_regiao = otto.loc[otto["regiao"] == regiao].copy()
    estados_regiao = estados.loc[estados["abbrev_state"].isin(ufs_regiao)].copy()

    # O shapefile e o Excel normalmente possuem uma coluna chamada wts_pk.
    # Se ambas forem mantidas no merge, o pandas cria wts_pk_x / wts_pk_y e
    # o Plotly deixa de encontrar a coluna canônica "wts_pk". Mantemos o
    # wts_pk do shapefile e usamos apenas _wts_pk como chave auxiliar do Excel.
    dados_merge = dados.drop(
        columns=["geometry", coluna_wts],
        errors="ignore",
    )

    mapa = otto_regiao.merge(
        dados_merge,
        left_on="wts_pk",
        right_on="_wts_pk",
        how="left",
    )
    mapa = mapa.loc[mapa["ISH com pesos escolhidos"].notna()].copy()

    if mapa.empty:
        st.warning(
            f"Nenhuma ottobacia da região {regiao} conseguiu ser associada ao Excel pelo campo wts_pk."
        )
        return

    mapa["Classe relativa"] = pd.cut(
        mapa["ISH com pesos escolhidos"],
        bins=limites,
        labels=CLASSES_ISH_OTTO,
        include_lowest=True,
        right=True,
        ordered=True,
    )
    mapa["Intervalo da classe"] = mapa["Classe relativa"].map(intervalos)

    mapa = mapa.reset_index(drop=True)
    mapa["_map_id"] = mapa.index.astype(str)
    geojson_otto = json.loads(mapa.to_json())

    estados_regiao = estados_regiao.reset_index(drop=True)
    estados_regiao["_state_id"] = estados_regiao.index.astype(str)
    geojson_estados = json.loads(estados_regiao.to_json())

    hover = {
        "_map_id": False,
        "abbrev_state": True,
        "wts_pk": True,
        "ISH com pesos escolhidos": ":.3f",
        "Classe relativa": True,
        "Intervalo da classe": True,
    }

    if beta in mapa.columns:
        hover[beta] = ":.3f"
    if "Diferença vs Beta" in mapa.columns:
        hover["Diferença vs Beta"] = ":+.3f"

    for dimensao in ["Humana", "Econômica", "Ecossistêmica", "Resiliência"]:
        coluna = mapeamento.get(dimensao)
        if coluna and coluna in mapa.columns:
            hover[coluna] = ":.3f"

    fig = px.choropleth(
        mapa,
        geojson=geojson_otto,
        locations="_map_id",
        featureidkey="id",
        color="Classe relativa",
        hover_name="wts_pk",
        hover_data=hover,
        color_discrete_map=CORES_ISH_OTTO,
        category_orders={"Classe relativa": CLASSES_ISH_OTTO},
        labels={
            "abbrev_state": "UF",
            "wts_pk": "wts_pk",
            "ISH com pesos escolhidos": "ISH",
            "Classe relativa": "Classe relativa",
            "Intervalo da classe": "Intervalo do ISH",
            beta: "ISH Beta",
            "Diferença vs Beta": "Diferença",
            mapeamento.get("Humana"): "Humana",
            mapeamento.get("Econômica"): "Econômica",
            mapeamento.get("Ecossistêmica"): "Ecossistêmica",
            mapeamento.get("Resiliência"): "Resiliência",
        },
    )

    fig.update_traces(marker_line_width=0.4, marker_line_color="rgba(60,60,60,0.55)")

    fig.add_trace(
        go.Choropleth(
            geojson=geojson_estados,
            locations=estados_regiao["_state_id"],
            z=[0] * len(estados_regiao),
            featureidkey="id",
            showscale=False,
            hoverinfo="skip",
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            marker_line_color="rgba(0,0,0,0.9)",
            marker_line_width=1.2,
            name="Estados",
        )
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        height=700,
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(title="Classe relativa", traceorder="normal"),
    )

    st.plotly_chart(
        fig,
        width="stretch",
        theme="streamlit",
        config={"displaylogo": False, "scrollZoom": False},
    )

    st.caption(
        "A classificação das ottobacias foi calculada por quintis com base em todos os registros da aba Otto, "
        "mas o mapa renderiza apenas a região selecionada para ficar mais leve."
    )
    st.caption(
        f"{len(mapa):,} ottobacias da região {regiao} representadas no mapa.".replace(",", ".")
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
    eh_otto = (
        "otto" in normalizar_texto(titulo)
        or "otto" in normalizar_texto(prefixo)
    )

    if eh_municipios:
        st.divider()
        mapa_municipios(
            df,
            beta,
            mapeamento,
        )
        st.divider()

    if eh_otto:
        st.divider()
        mapa_ottobacias(
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
