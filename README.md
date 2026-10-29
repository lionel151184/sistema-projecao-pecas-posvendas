# Sistema Analítico de Projeção de Consumo de Peças em Pós-Vendas

Código-fonte do artigo de conclusão de curso *Sistema analítico de projeção de consumo de peças em pós-vendas com apoio de sazonalidade e estações do ano*, de Lionel Evandro Stremlow.

O sistema lê uma base de ordens de serviço (`base_os.xlsx`) e apresenta, em um painel interativo (Streamlit), ocorrências de uso de peças por estado, período, modelo e estação do ano, com projeção de tendência por regressão linear simples.

## Métrica e formato da base

Cada linha com data válida conta **uma ocorrência de uso de peça**. A coluna `Casos` contém a numeração dos registros: seus valores não são somados e as linhas não são deduplicadas. Três linhas do mesmo código representam três ocorrências, mesmo que a numeração seja 10, 20 e 30.

Os totais, rankings e projeções são expressos em ocorrências, não em unidades físicas de peças nem em atendimentos distintos. A participação por estação é uma proporção histórica das ocorrências, não uma probabilidade de falha.

A primeira aba da planilha deve ter estes cabeçalhos na primeira linha:
`Casos`, `Modelo`, `Data de criação`, `Descrição da Peça`, `Código do item: Código`, `Estado` e `Cidade`.
Não é mais necessária a coluna `Qtd_peças_SVO`. Ao anonimizar, preserve os cabeçalhos, as datas e as siglas dos estados. Linhas com datas inválidas são excluídas da análise.

> A base `base_os.xlsx` deste repositório foi anonimizada e serve apenas para demonstração.

## Como executar (Windows)

1. Instale o [Python 3.12 ou superior](https://www.python.org/downloads/) e marque **Add Python to PATH** durante a instalação.
2. Baixe o projeto em **Code → Download ZIP** e **extraia** a pasta (não execute de dentro do ZIP).
3. Dê duplo clique em **`INICIAR_APP.bat`**.

Na primeira execução, o arquivo cria um ambiente virtual e instala as dependências (requer internet e leva alguns minutos). O navegador abre automaticamente com o painel. Para encerrar, feche a janela preta.

## Execução manual (qualquer sistema)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python run_app.py
```

Se o navegador não abrir, acesse o endereço exibido no terminal (normalmente http://localhost:8501).

## Estrutura

| Arquivo | Função |
|---|---|
| `app.py` | Interface e painéis (Streamlit/Plotly) |
| `processamento.py` | Leitura e tratamento da base de ordens de serviço |
| `estacoes.py` | Classificação por estação do ano (hemisfério sul) |
| `clima.py` | Consulta a dados climáticos históricos (Open-Meteo) |
| `utils.py` | Funções auxiliares |
| `run_app.py` | Inicia o servidor e abre o navegador |
| `INICIAR_APP.bat` | Preparação do ambiente e execução com duplo clique |
| `base_os.xlsx` | Base de dados (anonimizada) |
| `br_states.geojson` | Geometria dos estados brasileiros para o mapa |

## Tecnologias

Python, Pandas, NumPy, Plotly, Streamlit, scikit-learn.
