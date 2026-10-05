"""Persistência dos registros dos especialistas no Google Sheets."""
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import gspread
import pandas as pd
import streamlit as st
from gspread.exceptions import WorksheetNotFound


FUSO_HORARIO = ZoneInfo("America/Fortaleza")
ABA_PADRAO = "RESPOSTAS_ESPECIALISTAS"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def google_sheets_configurado():
    """Retorna True quando as credenciais mínimas estão disponíveis."""
    try:
        service_account = st.secrets["gcp_service_account"]
        google_sheets = st.secrets["google_sheets"]

        return bool(
            service_account.get("client_email")
            and service_account.get("private_key")
            and google_sheets.get("spreadsheet_id")
        )
    except (KeyError, FileNotFoundError):
        return False


@st.cache_resource(show_spinner=False)
def _cliente_google():
    """Cria e reutiliza o cliente autenticado do gspread."""
    info = dict(st.secrets["gcp_service_account"])

    # Também funciona se a chave tiver sido colada com "\\n" literal.
    if "private_key" in info:
        info["private_key"] = info["private_key"].replace("\\n", "\n")

    return gspread.service_account_from_dict(
        info,
        scopes=SCOPES,
    )


def _spreadsheet():
    spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
    return _cliente_google().open_by_key(spreadsheet_id)


def _nome_worksheet():
    try:
        return st.secrets["google_sheets"].get("worksheet", ABA_PADRAO)
    except (KeyError, FileNotFoundError):
        return ABA_PADRAO


def _cabecalhos(pesos_dimensoes, pesos_variaveis):
    cabecalhos = [
        "ID",
        "Data/hora",
        "Especialista / código",
        "Área de atuação",
        "Justificativa técnica",
    ]

    for dimensao in pesos_dimensoes:
        cabecalhos.append(f"Dimensão - {dimensao}")

    cabecalhos.append("Soma dimensões")

    for dimensao, variaveis in pesos_variaveis.items():
        for variavel in variaveis:
            cabecalhos.append(f"Variável - {dimensao} - {variavel}")
        cabecalhos.append(f"Soma variáveis - {dimensao}")

    return cabecalhos


def _obter_worksheet(cabecalhos):
    """Obtém/cria a aba e garante que todas as colunas necessárias existam."""
    planilha = _spreadsheet()
    nome = _nome_worksheet()

    try:
        worksheet = planilha.worksheet(nome)
    except WorksheetNotFound:
        worksheet = planilha.add_worksheet(
            title=nome,
            rows=1000,
            cols=max(30, len(cabecalhos) + 5),
        )

    existentes = worksheet.row_values(1)

    if not existentes:
        worksheet.update([cabecalhos], "A1")
        return worksheet, cabecalhos

    faltantes = [
        coluna
        for coluna in cabecalhos
        if coluna not in existentes
    ]

    if faltantes:
        inicio = len(existentes) + 1
        fim = inicio + len(faltantes) - 1

        inicio_a1 = gspread.utils.rowcol_to_a1(1, inicio)
        fim_a1 = gspread.utils.rowcol_to_a1(1, fim)

        worksheet.update(
            [faltantes],
            f"{inicio_a1}:{fim_a1}",
        )
        existentes.extend(faltantes)

    return worksheet, existentes


def salvar_resposta(
    especialista,
    area_atuacao,
    justificativa,
    pesos_dimensoes,
    pesos_variaveis,
):
    """Acrescenta uma nova resposta sem sobrescrever as anteriores."""
    cabecalhos = _cabecalhos(pesos_dimensoes, pesos_variaveis)
    worksheet, cabecalhos_worksheet = _obter_worksheet(cabecalhos)

    registro = {
        "ID": uuid4().hex[:12],
        "Data/hora": datetime.now(FUSO_HORARIO).strftime("%Y-%m-%d %H:%M:%S"),
        "Especialista / código": especialista.strip(),
        "Área de atuação": area_atuacao.strip(),
        "Justificativa técnica": justificativa.strip(),
        "Soma dimensões": sum(pesos_dimensoes.values()),
    }

    for dimensao, peso in pesos_dimensoes.items():
        registro[f"Dimensão - {dimensao}"] = int(peso)

    for dimensao, variaveis in pesos_variaveis.items():
        for variavel, peso in variaveis.items():
            registro[f"Variável - {dimensao} - {variavel}"] = int(peso)

        registro[f"Soma variáveis - {dimensao}"] = sum(variaveis.values())

    linha = [
        registro.get(cabecalho, "")
        for cabecalho in cabecalhos_worksheet
    ]

    worksheet.append_row(linha)
    return registro["ID"]


def listar_respostas(pesos_dimensoes, pesos_variaveis):
    """Lê todas as respostas do Google Sheets."""
    cabecalhos = _cabecalhos(pesos_dimensoes, pesos_variaveis)
    worksheet, _ = _obter_worksheet(cabecalhos)

    valores = worksheet.get_all_values()

    if len(valores) <= 1:
        return pd.DataFrame(columns=valores[0] if valores else cabecalhos)

    headers = valores[0]
    linhas = []

    for linha in valores[1:]:
        linha_ajustada = linha + [""] * (len(headers) - len(linha))
        linhas.append(linha_ajustada[:len(headers)])

    df = pd.DataFrame(linhas, columns=headers)

    if "Data/hora" in df.columns:
        df = df.sort_values("Data/hora", ascending=False, kind="stable")

    return df.reset_index(drop=True)
