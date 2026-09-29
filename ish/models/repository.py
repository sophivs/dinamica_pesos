import os
import geopandas as gpd
import pandas as pd
import streamlit as st

@st.cache_data(show_spinner=False)
def carregar_gpkg(caminho):
    return gpd.read_file(caminho)

@st.cache_data(show_spinner=False)
def carregar_excel(caminho, sheet_name=0):
    return pd.read_excel(caminho, sheet_name=sheet_name)


def carregar_dados(caminho, extensao, aba=0):
    if extensao == ".gpkg":
        return carregar_gpkg(caminho), "GeoPackage"
    if extensao in (".xlsx", ".xls"):
        df = carregar_excel(caminho, aba).dropna(axis=1, how="all")
        return df, f"Excel — {aba}"
    raise ValueError("Formato não suportado. Envie .gpkg, .xlsx ou .xls.")


def listar_abas(caminho):
    return pd.ExcelFile(caminho).sheet_names
