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

# Configuração do registro de especialistas no Google Sheets

## O que foi alterado

- Foi adicionada uma terceira aba no Streamlit: **Registro dos especialistas**.
- O especialista usa os mesmos sliders da barra lateral para definir:
  - pesos das quatro dimensões;
  - pesos das variáveis dentro de cada dimensão.
- Ao enviar, o app grava uma nova linha no Google Sheets.
- A mesma aba mostra todas as respostas já registradas, com as mais recentes primeiro.
- O app nunca sobrescreve respostas anteriores: cada envio recebe um ID único e um timestamp.

## 1. Crie uma planilha no Google Sheets

Crie uma planilha vazia. O app criará automaticamente a aba
`RESPOSTAS_ESPECIALISTAS` se ela ainda não existir.

Copie o ID da planilha. Em uma URL como:

`https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/edit`

o ID é:

`1AbCdEfGhIjKlMnOpQrStUvWxYz`

## 2. Google Cloud

No Google Cloud Console:

1. Crie ou selecione um projeto.
2. Ative **Google Sheets API**.
3. Ative **Google Drive API**.
4. Crie uma **Service Account**.
5. Crie uma chave JSON para essa conta de serviço.

## 3. Compartilhe a planilha

No JSON da Service Account existe um campo `client_email`.

Compartilhe a planilha do Google Sheets com esse e-mail e dê permissão de
**Editor**.

Sem isso, o app autentica mas não consegue abrir/gravar na planilha.

## 4. Dependência Python

Adicione ao seu `requirements.txt`:

```text
gspread>=6.2,<7
```

## 5. Secrets local

Use `.streamlit/secrets.toml`.

Há um arquivo `secrets.toml.example` neste pacote. Copie-o para
`.streamlit/secrets.toml` e substitua os valores de exemplo pelos valores
reais da chave JSON e pelo ID da planilha.

Nunca envie `secrets.toml` com valores reais para o GitHub.

## 6. Secrets no Streamlit Community Cloud

No app publicado, abra as configurações do aplicativo e cole os mesmos
Secrets usados localmente.

Não é necessário subir o arquivo real `secrets.toml` no repositório.