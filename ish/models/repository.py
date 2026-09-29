"""Leitura das colunas numéricas de origem na planilha distribuída com o app."""
import pandas as pd
from ish.config import ABAS, BETA, DIMENSOES, PLANILHA, Q95


def carregar_dataset(prefixo):
    if prefixo not in ABAS:
        raise ValueError(f"Conjunto de dados desconhecido: {prefixo}")
    if not PLANILHA.is_file():
        raise FileNotFoundError(f"Planilha não encontrada: {PLANILHA.name}")

    _, aba = ABAS[prefixo]
    variaveis = [coluna for grupo in DIMENSOES.values() for coluna in grupo.values()]
    identificadores = ["cod_ibge", "Município", "UF", "Região"] if prefixo == "municipios" else ["wts_pk"]
    # As colunas calculadas do Excel não têm valores em cache. Lemos só os dados
    # brutos e calculamos as dimensões e o ISH em Python a cada mudança de peso.
    colunas = identificadores + [Q95, BETA] + variaveis
    df = pd.read_excel(PLANILHA, sheet_name=aba, usecols=colunas, dtype={chave: str for chave in identificadores})
    for coluna in [Q95, BETA, *variaveis]:
        valores = pd.to_numeric(df[coluna], errors="coerce")
        invalidos = df[coluna].notna() & valores.isna()
        if invalidos.any():
            raise ValueError(f"A coluna {coluna} da aba {aba} contém {invalidos.sum()} valores não numéricos.")
        df[coluna] = valores
    if df[Q95].isna().any():
        raise ValueError(f"A coluna {Q95} da aba {aba} contém valores ausentes.")
    return df
