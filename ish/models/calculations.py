import pandas as pd

def pesos_validos(pesos):
    return sum(pesos.values()) == 100

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


