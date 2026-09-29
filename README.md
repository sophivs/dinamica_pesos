# Calculadora ISH 2025

Aplicação Streamlit para simular pesos das quatro dimensões e das 11 variáveis do ISH. A planilha de Municípios e Otto Bacias N4 já está incluída em `data/`; quem usa o aplicativo só precisa ajustar os pesos.

## Executar localmente

Requer Python 3.10 ou superior. Na pasta que contém `app.py`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

No Linux/macOS, use `.venv/bin/python` no lugar de `.\.venv\Scripts\python.exe`.

## Usar

Ajuste os pesos das **dimensões** na barra lateral. Abra cada dimensão em **Variáveis por dimensão** para ajustar os pesos internos. Os sliders e botões −/+ mudam de 1 em 1 ponto percentual. A soma das quatro dimensões e a soma das variáveis em cada dimensão precisam ser 100%. Enquanto alguma soma estiver diferente, o cálculo fica suspenso. O botão **Restaurar pesos iniciais** retorna ao cenário inicial.

A dimensão Econômica começa em **34% / 33% / 33%**: três pesos exatamente iguais seriam 33⅓% cada, incompatíveis com ajustes inteiros de 1%. As demais variáveis começam com pesos iguais. O valor **ISH Beta** vem da planilha original e é mantido como referência; portanto, o cenário inicial pode ter uma pequena diferença em relação a ele.

Para cada registro: `Dimensão = Σ (variável normalizada × peso interno / 100)` e `ISH = Σ (dimensão × peso da dimensão / 100) × Fator Q95`. `Diferença vs Beta = ISH recalculado − ISH Beta`. As colunas `Perdas_inv`, `DBO_inv` e `CV_pluv_inv` já são invertidas na planilha e não são invertidas novamente. O aplicativo recalcula as dimensões a partir das variáveis de origem, pois as colunas de fórmulas do Excel não contêm resultados armazenados. É possível baixar as tabelas calculadas em CSV ou Excel.

Células vazias de variáveis contribuem com zero na soma ponderada, seguindo `SUMPRODUCT` da planilha original. Elas permanecem vazias nas colunas brutas exportadas. Quando o ISH Beta está vazio, a diferença também fica vazia.

## Estrutura

- `app.py`: entrada e controles de pesos.
- `data/ISH_2025_DINAMICA_PESOS_VARIAVEIS_E_DIMENSOES.xlsx`: fonte fixa incluída no pacote.
- `ish/config.py`: dimensões, variáveis, colunas e pesos iniciais.
- `ish/models/repository.py`: leitura das duas abas com dados brutos.
- `ish/models/calculations.py`: cálculo e validação dos pesos.
- `ish/views/components.py`: controles e exportação.
- `ish/views/dashboard.py`: indicadores, gráficos e tabela.

## Deploy no Streamlit Community Cloud

Publique **todo o conteúdo desta pasta** na raiz do repositório, incluindo `data/`, `ish/`, `app.py` e `requirements.txt`. Escolha a branch publicada e informe `app.py` como caminho do arquivo principal. O aplicativo não faz upload de dados em tempo de execução. A interface usa os componentes e as cores do tema do Streamlit, acompanhando o modo claro ou escuro.
