# Calculadora ISH 2025

Aplicação Streamlit para recalcular o ISH com pesos definidos por especialistas. Aceita GeoPackage (`.gpkg`) ou Excel (`.xlsx`, `.xls`) para Municípios e Otto Bacias N4.

## Instalação

Requer Python 3.10 ou superior. No terminal, dentro desta pasta:

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Se o PowerShell bloquear a ativação, execute `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` e `.\.venv\Scripts\python.exe -m streamlit run app.py` diretamente.

## Uso

1. Envie o arquivo de Municípios ou de Otto Bacias N4 na barra lateral.
2. Para Excel com várias abas, selecione a aba; `RESULTADOS_MUNICIPIOS` e `RESULTADOS_OTTO_N4` são detectadas automaticamente quando correspondem ao painel.
3. Mapeie as cinco colunas numéricas exigidas caso seus nomes não sejam reconhecidos. A coluna ISH Beta é opcional.
4. Ajuste os quatro pesos até somarem 100%. Consulte indicadores e gráficos e baixe os resultados em CSV ou Excel.

O cálculo é `ISH = (Humana × peso_H + Econômica × peso_E + Ecossistêmica × peso_Ec + Resiliência × peso_R) / 100 × Fator Q95`. Se houver coluna Beta, a diferença é `ISH recalculado − ISH Beta`. Os valores do Excel entram diretamente no cálculo, sem depender do GeoPackage. O arquivo exportado contém as colunas de entrada e as colunas calculadas; a geometria não é exportada.

## Estrutura

- `app.py`: ponto de entrada, configuração e fluxo da aplicação.
- `ish/models/calculations.py`: validação e regras de cálculo sem interface.
- `ish/models/repository.py`: leitura de GeoPackage e Excel.
- `ish/controllers/files.py`: upload, escolha da aba e coordenação da leitura.
- `ish/views/components.py`: controles, mapeamento e exportação Excel.
- `ish/views/dashboard.py`: painéis, gráficos e tabela.
- `ish/views/styles.py`: estilos visuais.
- `ish/config.py`: nomes de colunas e cores.

Execute sempre a partir da raiz desta pasta com `python -m streamlit run app.py`.
