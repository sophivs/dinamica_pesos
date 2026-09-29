"""Configuração do conjunto de dados incluído e dos pesos iniciais."""
from pathlib import Path

PLANILHA = Path(__file__).resolve().parent.parent / "data" / "ISH_2025_DINAMICA_PESOS_VARIAVEIS_E_DIMENSOES.xlsx"
ABAS = {
    "municipios": ("Municípios", "RESULTADOS_MUNICIPIOS"),
    "otto_bacias_n4": ("Otto Bacias N4", "RESULTADOS_OTTO_N4"),
}
DIMENSOES = {
    "Humana": {
        "Abastecimento": "Abastecimento",
        "Potabilidade": "Potabilidade",
        "Perdas (invertida)": "Perdas_inv",
        "Segurança hídrica humana": "Seg_humana_hidrica",
    },
    "Econômica": {
        "PIB": "PIB",
        "Segurança industrial": "Seg_industrial",
        "Segurança agropecuária": "Seg_agro",
    },
    "Ecossistêmica": {
        "Cobertura florestal": "Cobertura_florestal",
        "Segurança associada à DBO": "DBO_inv",
    },
    "Resiliência": {
        "SPI-12": "SPI12",
        "CV pluviométrico": "CV_pluv_inv",
    },
}
PESOS_DIMENSOES_INICIAIS = {dim: 25 for dim in DIMENSOES}
PESOS_VARIAVEIS_INICIAIS = {
    "Humana": {nome: 25 for nome in DIMENSOES["Humana"]},
    "Econômica": dict(zip(DIMENSOES["Econômica"], (34, 33, 33))),
    "Ecossistêmica": {nome: 50 for nome in DIMENSOES["Ecossistêmica"]},
    "Resiliência": {nome: 50 for nome in DIMENSOES["Resiliência"]},
}
Q95 = "Fator Q95"
BETA = "ISH Beta 25/25/25/25"
