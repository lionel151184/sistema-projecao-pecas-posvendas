# clima.py
import requests
import pandas as pd

def get_weather(lat, lon, start_date, end_date):
    """
    Consulta clima histórico (sem API key) — Open-Meteo
    """
    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&"
        f"start_date={start_date}&end_date={end_date}&"
        "daily=temperature_2m_max,temperature_2m_min,precipitation_sum&"
        "timezone=America/Sao_Paulo"
    )

    response = requests.get(url)

    if response.status_code != 200:
        raise Exception("Erro na API de clima")

    data = response.json()["daily"]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["time"])
    df.drop(columns=["time"], inplace=True)

    return df
