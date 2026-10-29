# estacoes.py
import datetime

def get_estacao_do_ano(data):
    """
    Retorna a estação do ano (hemisfério sul).
    """
    ano = data.year

    datas = {
        "verao": datetime.date(ano, 12, 21),
        "outono": datetime.date(ano, 3, 21),
        "inverno": datetime.date(ano, 6, 21),
        "primavera": datetime.date(ano, 9, 23),
    }

    d = datetime.date(data.year, data.month, data.day)

    if datas["verao"] <= d or d < datas["outono"]:
        return "Verão"
    elif datas["outono"] <= d < datas["inverno"]:
        return "Outono"
    elif datas["inverno"] <= d < datas["primavera"]:
        return "Inverno"
    else:
        return "Primavera"