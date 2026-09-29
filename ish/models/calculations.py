"""Regras de ponderação independentes da interface Streamlit."""
import pandas as pd
from ish.config import BETA, DIMENSOES, Q95


def pesos_validos(pesos_dimensoes, pesos_variaveis):
    return (
        sum(pesos_dimensoes.values()) == 100
        and all(sum(grupo.values()) == 100 for grupo in pesos_variaveis.values())
    )


def calcular_ish(df, pesos_dimensoes, pesos_variaveis):
    if not pesos_validos(pesos_dimensoes, pesos_variaveis):
        raise ValueError("Os pesos de cada grupo devem somar 100%.")
    resultado = df.copy()
    for dimensao, variaveis in DIMENSOES.items():
        resultado[f"{dimensao} ponderada"] = sum(
            resultado[coluna].fillna(0) * pesos_variaveis[dimensao][nome] / 100
            for nome, coluna in variaveis.items()
        )
    resultado["ISH com pesos escolhidos"] = sum(
        resultado[f"{dimensao} ponderada"] * pesos_dimensoes[dimensao] / 100
        for dimensao in DIMENSOES
    ) * resultado[Q95]
    resultado["Diferença vs Beta"] = resultado["ISH com pesos escolhidos"] - resultado[BETA]
    resultado["Diferença absoluta"] = resultado["Diferença vs Beta"].abs()
    return resultado


def criar_faixas(serie, n=5):
    serie_valida = serie.dropna()
    if serie_valida.nunique() < 2:
        return pd.Series("Faixa única", index=serie.index)
    try:
        return pd.qcut(serie, q=min(n, serie_valida.nunique()), duplicates="drop").astype(str)
    except ValueError:
        return pd.cut(serie, bins=min(n, serie_valida.nunique()), duplicates="drop").astype(str)
