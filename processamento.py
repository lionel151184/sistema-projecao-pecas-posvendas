# processamento.py
import pandas as pd
import os
from estacoes import get_estacao_do_ano

def carregar_base():
    # Caminho absoluto do Excel, independente de onde o Streamlit rodar
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "base_os.xlsx"))

    # Carrega o arquivo
    df = pd.read_excel(base_path, engine="openpyxl")

    col_data = "Data de criação"
    obrigatorias = [
        "Casos", "Modelo", col_data, "Descrição da Peça",
        "Código do item: Código", "Estado", "Cidade",
    ]
    ausentes = [coluna for coluna in obrigatorias if coluna not in df.columns]
    if ausentes:
        raise ValueError(
            "Cabeçalhos obrigatórios ausentes em base_os.xlsx: "
            + ", ".join(ausentes)
            + ". Restaure os nomes na primeira linha da planilha."
        )

    # Converte a data — SEM unit, SEM origin
    df["Data"] = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)

    # Remove datas inválidas
    df = df[df["Data"].notna()]

    # Estação do ano
    df["Estação"] = df["Data"].apply(get_estacao_do_ano)

    # Renomeia para padrão simplificado
    df = df.rename(columns={
        "Descrição da Peça": "Peça",
        "Código do item: Código": "CódigoPeça",
    })

    # Casos numera os registros; cada linha válida conta uma ocorrência.
    df["Ocorrências"] = 1

    # Retorna somente colunas relevantes
    return df[[
        "Modelo",
        "Peça",
        "CódigoPeça",
        "Estado",
        "Cidade",
        "Estação",
        "Ocorrências",
        "Data"
    ]]