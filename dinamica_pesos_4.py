import io
import os
import tempfile
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(
    page_title="Calculadora ISH 2025",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLUNAS_PADRAO = {
    "Humana": "ISH_humana_V2",
    "Econômica": "ISH_economica_BETA_2025",
    "Ecossistêmica": "ISH_ecossistemica_BETA_2025",
    "Resiliência": "ISH_resiliencia_BETA_2025",
    "Fator Q95": "fator_Q95",
    "ISH Beta Original": "ISH_Q95_BETA_2025",
}

CORES = {
    "azul": "#0B5CAD",
    "azul_escuro": "#073B74",
    "verde": "#16A36A",
    "vermelho": "#E5484D",
    "laranja": "#F59E0B",
    "roxo": "#7656D6",
    "cinza": "#64748B",
}

# ============================================================
# CSS - DASHBOARD
# ============================================================
st.markdown(
    """
    <style>
    :root {
        --border: #e2e8f0;
        --text: #102a43;
        --muted: #64748b;
        --bg-card: #ffffff;
    }

    .stApp {
        background: #f5f8fc;
    }

    .block-container {
        max-width: 1800px;
        padding-top: 1.15rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #dfe7f1;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem;
    }

    h1, h2, h3, h4 {
        color: #102a43;
    }

    .dashboard-header {
        background: linear-gradient(90deg, #073b74 0%, #0b5cad 55%, #168aad 100%);
        border-radius: 12px;
        padding: 1.15rem 1.4rem;
        margin-bottom: 1rem;
        color: white;
        box-shadow: 0 2px 8px rgba(15, 23, 42, .08);
    }

    .dashboard-header h1 {
        color: white;
        font-size: 1.75rem;
        margin: 0;
        font-weight: 700;
    }

    .dashboard-header p {
        color: rgba(255,255,255,.88);
        margin: .35rem 0 0 0;
        font-size: .95rem;
    }

    .section-label {
        font-size: 1.05rem;
        font-weight: 700;
        color: #102a43;
        margin: .8rem 0 .55rem;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: .9rem 1rem;
        min-height: 105px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, .04);
    }

    div[data-testid="stMetricLabel"] {
        color: #52677e;
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        color: #0b5cad;
        font-weight: 700;
    }

    [data-testid="stPlotlyChart"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: .35rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, .04);
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        overflow: hidden;
    }

    .weight-total-ok {
        padding: .65rem .8rem;
        background: #ecfdf3;
        border: 1px solid #a7e8c4;
        border-radius: 8px;
        color: #087443;
        font-weight: 700;
    }

    .weight-total-bad {
        padding: .65rem .8rem;
        background: #fff1f2;
        border: 1px solid #fecdd3;
        border-radius: 8px;
        color: #b42318;
        font-weight: 700;
    }

    .sidebar-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #102a43;
        margin-bottom: .2rem;
    }

    .sidebar-subtitle {
        color: #64748b;
        font-size: .82rem;
        margin-bottom: 1rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: .4rem;
    }

    .stTabs [data-baseweb="tab"] {
        background: #eef4fb;
        border-radius: 7px 7px 0 0;
        padding-left: 1.3rem;
        padding-right: 1.3rem;
    }

    .stTabs [aria-selected="true"] {
        background: #0b5cad !important;
        color: white !important;
    }

    div.stButton > button,
    div.stDownloadButton > button {
        border-radius: 7px;
    }

    .info-strip {
        padding: .65rem .9rem;
        border: 1px solid #cbdff5;
        border-left: 4px solid #0b5cad;
        border-radius: 7px;
        background: #f0f7ff;
        color: #31516f;
        margin-bottom: .9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SESSION STATE / PESOS
# ============================================================
for chave in ["peso_h", "peso_e", "peso_ec", "peso_r"]:
    if chave not in st.session_state:
        st.session_state[chave] = 25

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
def pesos_validos(pesos):
    return sum(pesos.values()) == 100

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

@st.cache_data(show_spinner=False)
def carregar_gpkg(caminho):
    return gpd.read_file(caminho)

@st.cache_data(show_spinner=False)
def carregar_excel(caminho, sheet_name=0):
    return pd.read_excel(caminho, sheet_name=sheet_name)

def carregar_dados(caminho, uploaded_file, prefixo):
    extensao = os.path.splitext(uploaded_file.name)[1].lower()

    if extensao == ".gpkg":
        return carregar_gpkg(caminho), "GeoPackage"

    if extensao in [".xlsx", ".xls"]:
        xls = pd.ExcelFile(caminho)
        abas = xls.sheet_names

        # Quando o arquivo é a planilha oficial da dinâmica, escolhe
        # automaticamente a aba de resultados correspondente ao dashboard.
        aba_preferida = None
        if prefixo == "municipios" and "RESULTADOS_MUNICIPIOS" in abas:
            aba_preferida = "RESULTADOS_MUNICIPIOS"
        elif prefixo == "otto_bacias_n4" and "RESULTADOS_OTTO_N4" in abas:
            aba_preferida = "RESULTADOS_OTTO_N4"

        if aba_preferida is not None:
            aba = aba_preferida
            st.caption(f"Aba detectada automaticamente: {aba}")
        elif len(abas) > 1:
            aba = st.selectbox("Planilha do Excel", abas, key=f"aba_excel_{prefixo}")
        else:
            aba = abas[0]

        df = carregar_excel(caminho, aba)
        # Remove colunas totalmente vazias geradas por formatação do Excel.
        df = df.dropna(axis=1, how="all")
        return df, f"Excel — {aba}"

    raise ValueError("Formato não suportado. Envie .gpkg, .xlsx ou .xls.")

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

def validar_mapeamento(gdf, mapeamento):
    erros = []
    campos = ["Humana", "Econômica", "Ecossistêmica", "Resiliência", "Fator Q95"]

    for campo in campos:
        coluna = mapeamento[campo]
        if coluna not in gdf.columns:
            erros.append(f"Coluna de {campo} não encontrada.")
        elif not pd.api.types.is_numeric_dtype(gdf[coluna]):
            erros.append(f"A coluna de {campo} precisa ser numérica.")

    beta = mapeamento["ISH Beta Original"]
    if beta != "Não calcular diferença":
        if beta not in gdf.columns or not pd.api.types.is_numeric_dtype(gdf[beta]):
            erros.append("A coluna de ISH Beta precisa ser numérica.")

    return erros

def calcular_ish(gdf, pesos, mapeamento):
    resultado = gdf.copy()

    ponderado = (
        resultado[mapeamento["Humana"]] * pesos["Humana"] / 100
        + resultado[mapeamento["Econômica"]] * pesos["Econômica"] / 100
        + resultado[mapeamento["Ecossistêmica"]] * pesos["Ecossistêmica"] / 100
        + resultado[mapeamento["Resiliência"]] * pesos["Resiliência"] / 100
    )

    resultado["ISH com pesos escolhidos"] = (
        ponderado * resultado[mapeamento["Fator Q95"]]
    )

    beta = mapeamento["ISH Beta Original"]
    if beta != "Não calcular diferença":
        resultado["Diferença vs Beta"] = (
            resultado["ISH com pesos escolhidos"] - resultado[beta]
        )
        resultado["Diferença absoluta"] = resultado["Diferença vs Beta"].abs()

    return resultado

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

def criar_faixas(serie, n=5):
    serie_valida = serie.dropna()

    if serie_valida.nunique() < 2:
        return pd.Series("Faixa única", index=serie.index)

    try:
        return pd.qcut(
            serie,
            q=min(n, serie_valida.nunique()),
            duplicates="drop",
        ).astype(str)
    except ValueError:
        return pd.cut(
            serie,
            bins=min(n, serie_valida.nunique()),
            duplicates="drop",
        ).astype(str)

# ============================================================
# SIDEBAR
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
def dashboard_dataset(uploaded_file, titulo, prefixo):
    if uploaded_file is None:
        st.markdown(
            f'<div class="info-strip">Selecione o arquivo de <b>{titulo}</b> '
            f'na barra lateral para carregar o dashboard.</div>',
            unsafe_allow_html=True,
        )
        return

    caminho = salvar_upload(uploaded_file, f"path_{prefixo}")
    if not caminho:
        return

    try:
        with st.spinner(f"Carregando {titulo}..."):
            gdf, tipo_fonte = carregar_dados(caminho, uploaded_file, prefixo)
    except Exception as exc:
        st.error(f"Não foi possível abrir o arquivo: {exc}")
        return

    if gdf.empty:
        st.warning("O arquivo não contém registros.")
        return

    mapeamento = interface_mapeamento(gdf, prefixo)
    erros = validar_mapeamento(gdf, mapeamento)

    if erros:
        for erro in erros:
            st.error(erro)
        return

    resultado = calcular_ish(gdf, pesos, mapeamento)
    df = resultado.drop(columns="geometry", errors="ignore").copy()
    novo = df["ISH com pesos escolhidos"]

    beta = mapeamento["ISH Beta Original"]
    possui_beta = (
        beta != "Não calcular diferença"
        and beta in df.columns
        and "Diferença vs Beta" in df.columns
    )

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
            use_container_width=True,
        )

    with xlsx_col:
        st.download_button(
            "Baixar Excel",
            excel_bytes(df),
            file_name=f"ISH_{prefixo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------
    st.markdown('<div class="section-label">Visão geral</div>', unsafe_allow_html=True)

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
    st.markdown('<div class="section-label">Análise dos resultados</div>', unsafe_allow_html=True)

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
            color_discrete_sequence=[CORES["azul"]],
        )
        fig_faixa.update_xaxes(title="Faixa de ISH")
        fig_faixa.update_yaxes(title="Quantidade")
        st.plotly_chart(layout_grafico(fig_faixa), use_container_width=True)

    with c2:
        if possui_beta:
            fig_diff = px.histogram(
                df,
                x="Diferença vs Beta",
                nbins=35,
                title="Distribuição das diferenças vs Beta",
                color_discrete_sequence=[CORES["verde"]],
            )
            fig_diff.add_vline(
                x=0,
                line_dash="dash",
                line_color=CORES["vermelho"],
            )
            fig_diff.update_xaxes(title="Diferença (novo ISH − Beta)")
            fig_diff.update_yaxes(title="Quantidade")
        else:
            fig_diff = px.histogram(
                df,
                x="ISH com pesos escolhidos",
                nbins=35,
                title="Distribuição do novo ISH",
                color_discrete_sequence=[CORES["verde"]],
            )
            fig_diff.update_xaxes(title="ISH")
        st.plotly_chart(layout_grafico(fig_diff), use_container_width=True)

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
            marker_color=CORES["azul"],
        )
        fig_acum.add_scatter(
            x=faixa_acum["_Faixa ISH"],
            y=faixa_acum["Acumulado (%)"],
            name="Acumulado (%)",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color=CORES["laranja"], width=3),
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
        st.plotly_chart(layout_grafico(fig_acum), use_container_width=True)

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
            color_discrete_sequence=[CORES["azul"]],
        )
        st.plotly_chart(layout_grafico(fig_medias), use_container_width=True)

    with c5:
        if possui_beta:
            aumentaram = int((df["Diferença vs Beta"] > 0).sum())
            diminuiram = int((df["Diferença vs Beta"] < 0).sum())
            iguais = int((df["Diferença vs Beta"] == 0).sum())

            situacao = pd.DataFrame(
                {
                    "Situação": ["Aumentaram", "Diminuíram", "Sem alteração"],
                    "Quantidade": [aumentaram, diminuiram, iguais],
                }
            )

            fig_pizza = px.pie(
                situacao,
                names="Situação",
                values="Quantidade",
                hole=.58,
                title="Situação em relação ao ISH Beta",
                color="Situação",
                color_discrete_map={
                    "Aumentaram": CORES["verde"],
                    "Diminuíram": CORES["vermelho"],
                    "Sem alteração": CORES["cinza"],
                },
            )
            fig_pizza.update_traces(textposition="inside", textinfo="percent")
            st.plotly_chart(layout_grafico(fig_pizza), use_container_width=True)
        else:
            fig_q95 = px.histogram(
                df,
                x=mapeamento["Fator Q95"],
                nbins=30,
                title="Distribuição do fator Q95",
                color_discrete_sequence=[CORES["laranja"]],
            )
            st.plotly_chart(layout_grafico(fig_q95), use_container_width=True)

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
            color_discrete_sequence=[
                CORES["azul"],
                CORES["verde"],
                CORES["laranja"],
                CORES["roxo"],
            ],
        )
        fig_box.update_layout(showlegend=False)
        st.plotly_chart(layout_grafico(fig_box), use_container_width=True)

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
                color_discrete_sequence=[CORES["azul"]],
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
                    line=dict(dash="dash", color=CORES["vermelho"]),
                )

            st.plotly_chart(layout_grafico(fig_scatter, 430), use_container_width=True)

    # --------------------------------------------------------
    # TABELA
    # --------------------------------------------------------
    st.markdown('<div class="section-label">Dados detalhados</div>', unsafe_allow_html=True)

    tabela = df.drop(columns=["_Faixa ISH"], errors="ignore")

    if busca:
        mascara = tabela.astype(str).apply(
            lambda col: col.str.contains(busca, case=False, na=False)
        ).any(axis=1)
        tabela = tabela.loc[mascara]

    st.caption(f"{len(tabela):,} registros exibidos".replace(",", "."))
    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    with st.expander("Informações do arquivo"):
        a, b, c = st.columns(3)
        a.metric("Registros", len(gdf))
        b.metric("Colunas", len(gdf.columns))
        if isinstance(gdf, gpd.GeoDataFrame):
            c.metric("CRS", str(gdf.crs) if gdf.crs else "Não definido")
        else:
            c.metric("Fonte", tipo_fonte)

tab_mun, tab_otto = st.tabs(["Municípios", "Otto Bacias N4"])

with tab_mun:
    dashboard_dataset(file_municipios, "Municípios", "municipios")

with tab_otto:
    dashboard_dataset(file_otto, "Otto Bacias N4", "otto_bacias_n4")