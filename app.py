# app.py
import json

import streamlit as st
import subprocess
import sys
import os
import pandas as pd
import plotly.express as px
from processamento import carregar_base
from sklearn.linear_model import LinearRegression 
import numpy as np
import io
import time

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="Painel de OS, Peças, Regiões e Estações",
    layout="wide"
)
# Remove elementos do Streamlit
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        /* Widget de status com a animacao do "boneco correndo" e botao Parar */
        [data-testid="stStatusWidget"] {display: none !important;}
        [data-testid="stToolbar"] {display: none !important;}
        [data-testid="stDecoration"] {display: none !important;}
        [data-testid="stAppDeployButton"] {display: none !important;}
        .stDeployButton {display: none !important;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("📊 Painel de Ocorrências de Uso de Peças, Regiões e Estações do Ano")
st.caption(
    "Cada linha com data válida representa uma ocorrência de uso de peça. "
    "A numeração da coluna Casos não é somada. Os totais não representam "
    "quantidades físicas de peças nem atendimentos distintos; as projeções "
    "também são expressas em ocorrências."
)

st.markdown(
    """
    <style>
        :root {
            color-scheme: dark;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ======================================================
# CARREGAR BASE
# ======================================================
_carregamento = st.empty()
_barra = st.progress(0)

for _pct in range(0, 41):
    _carregamento.write(f"Carregando dados... {_pct:02d}%")
    _barra.progress(_pct)
    time.sleep(0.01)

try:
    df = carregar_base()
except (ValueError, FileNotFoundError, PermissionError) as erro:
    _carregamento.empty()
    _barra.empty()
    st.error(f"Não foi possível carregar a base de dados: {erro}")
    st.stop()

for _pct in range(41, 101):
    _carregamento.write(f"Carregando dados... {_pct:02d}%")
    _barra.progress(_pct)
    time.sleep(0.01)

_carregamento.empty()
_barra.empty()

# ======================================================
# SIDEBAR – FILTROS
# ======================================================
st.sidebar.header("🔎 Filtros")

modelos = ["Todos"] + sorted(df["Modelo"].astype(str).unique())
pecas = ["Todos"] + sorted(df["Peça"].astype(str).unique())
estados = ["Todos"] + sorted(df["Estado"].astype(str).unique())
estacoes = ["Todos"] + sorted(df["Estação"].astype(str).unique())

f_modelo = st.sidebar.selectbox("Modelo", modelos)
f_peca = st.sidebar.selectbox("Peça", pecas)
f_estado = st.sidebar.selectbox("Estado", estados)
f_estacao = st.sidebar.selectbox("Estação do ano", estacoes)

df_filtro = df.copy()

if f_modelo != "Todos":
    df_filtro = df_filtro[df_filtro["Modelo"] == f_modelo]

if f_peca != "Todos":
    df_filtro = df_filtro[df_filtro["Peça"] == f_peca]

if f_estado != "Todos":
    df_filtro = df_filtro[df_filtro["Estado"] == f_estado]

if f_estacao != "Todos":
    df_filtro = df_filtro[df_filtro["Estação"] == f_estacao]

# ======================================================
# PAINEL 1 — DADOS CONSOLIDADOS
# ======================================================
st.header("Painel 1 — Dados Consolidados")

# --- Gráfico 1: Modelos x Ocorrências de Uso de Peças por Estado ---
st.subheader("Gráfico 1 — Modelos e Ocorrências de Uso de Peças por Estado")

graf1 = df_filtro.groupby(["Modelo", "Estado"])["Ocorrências"].sum().reset_index()

# Pivotar: Modelo nas linhas, Estados nas colunas
pivot_g1 = graf1.pivot_table(index="Modelo", columns="Estado", values="Ocorrências", fill_value=0)

# Ordenar colunas (estados) do maior para menor volume total
ordem_estados = pivot_g1.sum().sort_values(ascending=False).index.tolist()
pivot_g1 = pivot_g1[ordem_estados]

# Adicionar coluna Total e ordenar modelos do maior para menor
pivot_g1["Total"] = pivot_g1.sum(axis=1)
pivot_g1 = pivot_g1.sort_values("Total", ascending=False).reset_index()

st.dataframe(
    pivot_g1,
    use_container_width=True,
    column_config={
        "Modelo": st.column_config.TextColumn("Modelo", pinned=True),
        "Total": st.column_config.NumberColumn("Total", help="Total de ocorrências nos estados"),
    }
)

# --- Gráfico 2: Tabela de Peças com meses/ano ---
st.subheader("Gráfico 2 — Ocorrências de Uso de Peças por Mês/Ano")

df_pivot = df_filtro.copy()
df_pivot["AnoMes"] = df_pivot["Data"].dt.to_period("M").astype(str)

# Agrupar por CódigoPeça, Peça e AnoMes
pivot = df_pivot.groupby(["CódigoPeça", "Peça", "AnoMes"])["Ocorrências"].sum().reset_index()
pivot = pivot.pivot_table(index=["CódigoPeça", "Peça"], columns="AnoMes", values="Ocorrências", fill_value=0)

# Ordenar colunas (meses) em ordem crescente
pivot = pivot[sorted(pivot.columns)]
pivot = pivot.reset_index()

# Colunas de meses (todas exceto CódigoPeça e Peça)
colunas_meses = [c for c in pivot.columns if c not in ["CódigoPeça", "Peça"]]

# Coluna Total
pivot["Total"] = pivot[colunas_meses].sum(axis=1)

# Projeção para os próximos 2 anos (12 + 12 meses) usando regressão linear

def projetar_consumo_ano(row, colunas_meses, inicio=0, n_meses=12):
    valores = row[colunas_meses].values.astype(float)
    n = len(valores)
    if n < 2 or valores.sum() == 0:
        return 0
    X = np.arange(n).reshape(-1, 1)
    y = valores
    modelo_lr = LinearRegression()
    modelo_lr.fit(X, y)
    X_futuro = np.arange(n + inicio, n + inicio + n_meses).reshape(-1, 1)
    previsao = modelo_lr.predict(X_futuro)
    previsao = np.maximum(previsao, 0)
    return int(round(previsao.sum()))

pivot["Projeção 1º ano"] = pivot.apply(lambda row: projetar_consumo_ano(row, colunas_meses, inicio=0, n_meses=12), axis=1)
pivot["Projeção 2º ano"] = pivot.apply(lambda row: projetar_consumo_ano(row, colunas_meses, inicio=12, n_meses=12), axis=1)
pivot["Projeção 3º ano"] = pivot.apply(lambda row: projetar_consumo_ano(row, colunas_meses, inicio=24, n_meses=12), axis=1)
pivot["Projeção 4º ano"] = pivot.apply(lambda row: projetar_consumo_ano(row, colunas_meses, inicio=36, n_meses=12), axis=1)
pivot["Projeção 5º ano"] = pivot.apply(lambda row: projetar_consumo_ano(row, colunas_meses, inicio=48, n_meses=12), axis=1)
pivot["Total Projeções"] = pivot[["Projeção 1º ano", "Projeção 2º ano", "Projeção 3º ano", "Projeção 4º ano", "Projeção 5º ano"]].sum(axis=1)

# Ordenar do maior para o menor consumo total
pivot = pivot.sort_values("Total", ascending=False).reset_index(drop=True)

# Exibir com colunas fixas (CódigoPeça e Peça congeladas)
st.dataframe(
    pivot,
    use_container_width=True,
    column_config={
        "CódigoPeça": st.column_config.TextColumn("CódigoPeça", pinned=True),
        "Peça": st.column_config.TextColumn("Peça", pinned=True),
        "Total": st.column_config.NumberColumn("Total", help="Total de ocorrências nos meses"),
        "Projeção 1º ano": st.column_config.NumberColumn("Projeção 1º ano", help="Projeção próximos 12 meses"),
        "Projeção 2º ano": st.column_config.NumberColumn("Projeção 2º ano", help="Projeção 13º ao 24º mês"),
        "Projeção 3º ano": st.column_config.NumberColumn("Projeção 3º ano", help="Projeção 25º ao 36º mês"),
        "Projeção 4º ano": st.column_config.NumberColumn("Projeção 4º ano", help="Projeção 37º ao 48º mês"),
        "Projeção 5º ano": st.column_config.NumberColumn("Projeção 5º ano", help="Projeção 49º ao 60º mês"),
        "Total Projeções": st.column_config.NumberColumn("Total Projeções", help="Soma de todas as projeções (5 anos)"),
    }
)

# ======================================================
# PAINEL 2 — MAPA DE CALOR POR ESTADO
# ======================================================
st.markdown("---")
st.header("Painel 2 — Mapa de Calor por Estado")

heat = df_filtro.groupby("Estado")["Ocorrências"].sum().reset_index()

_base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_base_dir, "br_states.geojson"), "r", encoding="utf-8") as f:
    geojson_data = json.load(f)
    
fig = px.choropleth(
    heat,
    geojson=geojson_data,
    locations="Estado",
    featureidkey="properties.sigla",
    color="Ocorrências",
    color_continuous_scale="Reds",
    title="Mapa de Calor — Ocorrências de Uso de Peças por Estado",
)

fig.update_geos(
    fitbounds="geojson",
    visible=False,
    showcountries=True,
    showcoastlines=True,
    projection_type="mercator"
)

fig.update_layout(
    height=550,
    margin={"r":0, "t":30, "l":0, "b":0}
)

st.plotly_chart(fig, use_container_width=True)

# ======================================================
# PAINEL 3 — LINHA DO TEMPO HISTÓRICA
# ======================================================
st.markdown("---")
st.header("Painel 3 — Linha do Tempo de Ocorrências")

df_filtro["AnoMes"] = df_filtro["Data"].dt.to_period("M").astype(str)
linha = df_filtro.groupby("AnoMes")["Ocorrências"].sum().reset_index()

fig_linha = px.line(
    linha,
    x="AnoMes",
    y="Ocorrências",
    markers=True,
    title="Evolução Mensal das Ocorrências de Uso de Peças"
)

st.plotly_chart(fig_linha, use_container_width=True)


# ======================================================
# PAINEL 4 — COMPARAÇÃO POR ESTAÇÃO
# ======================================================
st.markdown("---")
st.header("Painel 4 — Ocorrências por Estação do Ano")

estacao = df_filtro.groupby("Estação")["Ocorrências"].sum().reset_index()

fig_bar = px.bar(
    estacao,
    x="Estação",
    y="Ocorrências",
    color="Estação",
    title="Comparação de Ocorrências por Estação"
)

st.plotly_chart(fig_bar, use_container_width=True)


# ======================================================
# PAINEL 5 — PREVISÃO SIMPLES (REGRESSÃO)
# ======================================================

st.markdown("---")
st.header("Painel 5 — Previsão de Ocorrências (Regressão Linear Simplificada)")

import numpy as np

# Agrupa por mês
df_prev = df_filtro.groupby("AnoMes")["Ocorrências"].sum().reset_index()

# Se não houver dados suficientes, exibe aviso
if len(df_prev) < 2:
    st.warning("Dados insuficientes para gerar previsão. É necessário pelo menos 2 períodos.")
else:
    # Índice numérico (0,1,2,...)
    df_prev["AnoMesNum"] = range(len(df_prev))

    X = df_prev["AnoMesNum"].values
    y = df_prev["Ocorrências"].values

    # Regressão linear usando numpy
    coef = np.polyfit(X, y, 1)
    trend = np.poly1d(coef)

    # Gera previsão
    df_prev["Previsão"] = trend(X)

    # Gráfico
    fig_prev = px.line(
        df_prev,
        x="AnoMes",
        y=["Ocorrências", "Previsão"],
        markers=True,
        title="📈 Previsão Linear de Ocorrências"
    )

    st.plotly_chart(fig_prev, use_container_width=True)

# ======================================================
# PAINEL 6 — PREVISÃO DA ESTAÇÃO DO ANO (CORRIGIDO)
# ======================================================
st.markdown("---")
st.header("Painel 7 — Previsão de Ocorrências por Estação do Ano")

import numpy as np

df_station = df_filtro.copy()
df_station["Ano"] = df_station["Data"].dt.year

if df_station.empty:
    st.warning("Nenhum dado disponível para previsão por estação com os filtros atuais.")
else:
    # Agrupamento por ano + estação
    station_group = (
        df_station.groupby(["Ano", "Estação"])["Ocorrências"]
        .sum()
        .reset_index()
        .sort_values(["Estação", "Ano"])
    )

    estacoes_unicas = station_group["Estação"].unique()

    # CORREÇÃO: converter para lista
    abas = st.tabs(list(estacoes_unicas))

    for aba, estacao in zip(abas, estacoes_unicas):
        with aba:

            st.subheader(f"📈 Previsão da estação: **{estacao}**")

            df_e = station_group[station_group["Estação"] == estacao]

            if len(df_e) < 2:
                st.warning(f"Estação {estacao}: dados insuficientes para previsão.")
                continue

            df_e = df_e.copy()
            df_e["Idx"] = range(len(df_e))

            X = df_e["Idx"].values
            y = df_e["Ocorrências"].values

            coef = np.polyfit(X, y, 1)
            trend = np.poly1d(coef)

            df_e["Previsão"] = trend(X)

            fig_est = px.line(
                df_e,
                x="Ano",
                y=["Ocorrências", "Previsão"],
                markers=True,
                title=f"Previsão Linear de Ocorrências — Estação {estacao}"
            )

            st.plotly_chart(fig_est, use_container_width=True)

            # Insight
            antes = y[0]
            agora = y[-1]
            direcao = "📈 Crescente" if agora > antes else "📉 Decrescente"

            st.info(
                f"**Tendência:** {direcao}\n\n"
                f"Ano inicial: {antes} ocorrências\n"
                f"Ano final: {agora} ocorrências"
            )

# ======================================================
# PAINEL 7 — INSIGHTS AUTOMÁTICOS (Machine Learning Simples)
# ======================================================
st.markdown("---")
st.header("Painel 6 — Insights Inteligentes da Operação")

df_insight = df_filtro.copy()

if df_insight.empty:
    st.warning("Nenhum dado encontrado com os filtros atuais.")
else:
    # 1 — Cidade com mais volume
    cidade_top = (
        df_insight.groupby("Cidade")["Ocorrências"]
        .sum()
        .sort_values(ascending=False)
        .head(1)
    )

    cidade_nome = cidade_top.index[0]
    cidade_qtd = int(cidade_top.values[0])

    st.subheader("🏙️ 1. Cidade com mais ocorrências nos filtros selecionados")
    st.write(f"**{cidade_nome}** é a cidade com maior número de ocorrências de uso de peças, com **{cidade_qtd} ocorrências**.")

    # 2 — Cidade com mais volume por estação
    cidade_estacao = (
        df_insight.groupby(["Estação", "Cidade"])["Ocorrências"]
        .sum()
        .reset_index()
    )

    top_estacao = (
        cidade_estacao.sort_values("Ocorrências", ascending=False)
        .head(1)
    )

    est = top_estacao.iloc[0]["Estação"]
    cid = top_estacao.iloc[0]["Cidade"]
    qtd = int(top_estacao.iloc[0]["Ocorrências"])

    st.subheader("❄️ 2. Cidade líder por estação do ano")
    st.write(f"Na estação **{est}**, a cidade com maior volume é **{cid}**, com **{qtd} ocorrências**.")

    # 3 — Modelo com mais ocorrências
    modelo_top = (
        df_insight.groupby("Modelo")["Ocorrências"]
        .sum()
        .sort_values(ascending=False)
        .head(1)
    )

    st.subheader("⚠️ 3. Modelo com mais ocorrências")
    st.write(f"Modelo com mais ocorrências: **{modelo_top.index[0]}** com **{int(modelo_top.values[0])} ocorrências**.")

    # 4 — Tendência (crescendo ou caindo)
    df_trend = (
        df_insight.groupby("AnoMes")["Ocorrências"]
        .sum()
        .reset_index()
    )

    if len(df_trend) > 1:
        antes = df_trend["Ocorrências"].iloc[0]
        agora = df_trend["Ocorrências"].iloc[-1]

        tendencia = "📈 Crescente" if agora > antes else "📉 Decrescente"

        st.subheader("📊 4. Tendência das ocorrências")
        st.write(f"A tendência das ocorrências é: **{tendencia}**.")
    else:
        st.write("Dados insuficientes para calcular tendência.")

    # 5 — Top 5 estados por ocorrências
    top_estados = (
        df_insight.groupby("Estado")["Ocorrências"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )

    st.subheader("🗺️ 5. Estados com mais ocorrências (Top 5)")
    st.dataframe(top_estados.reset_index(), use_container_width=True)

    # 6 — Participação histórica por estação
    prob_estacao = (
        df_insight.groupby("Estação")["Ocorrências"]
        .sum()
    )

    prob_estacao = prob_estacao / prob_estacao.sum()

    st.subheader("🎯 6. Participação histórica das ocorrências por estação")
    st.bar_chart(prob_estacao)


# ======================================================
# PAINEL 8 — PREVISÃO FUTURA (Próximo Ano, 3 Anos, Peça, Modelo) — CORRIGIDO
# ======================================================
st.markdown("---")
st.header("Painel 8 — Projeção Futura de Ocorrências (Regressão Linear)")

import numpy as np

df_future = df_filtro.copy()
df_future["Ano"] = df_future["Data"].dt.year

if df_future.empty:
    st.warning("Nenhum dado disponível para previsões futuras com os filtros atuais.")
else:

    base_year = df_future["Ano"].max()
    next_year = base_year + 1
    next_3_year = base_year + 3

    # -----------------------------
    # PREVISÃO POR ESTAÇÃO
    # -----------------------------
    st.subheader("📅 Previsão por Estação do Ano")

    estacoes = df_future["Estação"].unique()

    for est in estacoes:
        df_e = df_future[df_future["Estação"] == est]
        df_e = df_e.groupby("Ano")["Ocorrências"].sum().reset_index()

        if len(df_e) < 2:
            st.info(f"Estação **{est}** — dados insuficientes para previsão.")
            continue

        df_e["Idx"] = range(len(df_e))
        X = df_e["Idx"].values
        y = df_e["Ocorrências"].values

        coef = np.polyfit(X, y, 1)
        trend = np.poly1d(coef)

        # Previsões arredondadas (CORRIGIDO)
        previsao_1 = round(trend(len(X)))
        previsao_3 = round(trend(len(X) + 3))

        st.write(f"**{est}:**")
        st.write(f"- Previsão para {next_year}: **{previsao_1} ocorrências**")
        st.write(f"- Previsão para {next_3_year}: **{previsao_3} ocorrências**")
        st.write("---")

    # -----------------------------
    # PREVISÃO POR PEÇA (Próximo Ano)
    # -----------------------------
    st.subheader("🔧 Previsão de Ocorrências por Peça (Próximo Ano)")

    pecas = df_future["Peça"].unique()
    lista_pecas_prev = []

    for p in pecas:
        df_p = df_future[df_future["Peça"] == p]
        df_p = df_p.groupby("Ano")["Ocorrências"].sum().reset_index()

        if len(df_p) < 2:
            continue

        df_p["Idx"] = range(len(df_p))
        coef = np.polyfit(df_p["Idx"].values, df_p["Ocorrências"].values, 1)
        trend = np.poly1d(coef)

        previsao_p = round(trend(len(df_p)))   # CORRIGIDO

        lista_pecas_prev.append([p, previsao_p])

    df_prev_peca = pd.DataFrame(lista_pecas_prev, columns=["Peça", "Previsão Próximo Ano"])
    st.dataframe(df_prev_peca.sort_values("Previsão Próximo Ano", ascending=False))

    # -----------------------------
    # PREVISÃO POR MODELO (Próximo Ano)
    # -----------------------------
    st.subheader("📦 Previsão de Ocorrências por Modelo (Próximo Ano)")

    modelos = df_future["Modelo"].unique()
    lista_modelos_prev = []

    for m in modelos:
        df_m = df_future[df_future["Modelo"] == m]
        df_m = df_m.groupby("Ano")["Ocorrências"].sum().reset_index()

        if len(df_m) < 2:
            continue

        df_m["Idx"] = range(len(df_m))
        coef = np.polyfit(df_m["Idx"].values, df_m["Ocorrências"].values, 1)
        trend = np.poly1d(coef)

        previsao_m = round(trend(len(df_m)))  # CORRIGIDO

        lista_modelos_prev.append([m, previsao_m])

    df_prev_modelo = pd.DataFrame(lista_modelos_prev, columns=["Modelo", "Previsão Próximo Ano"])
    st.dataframe(df_prev_modelo.sort_values("Previsão Próximo Ano", ascending=False))
                
# ======================================================
# EXPORTAÇÃO
# ======================================================
st.markdown("---")
st.header("Exportar Dados")

# Exportar para Excel
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_filtro.to_excel(writer, index=False, sheet_name="Dados")

st.download_button(
    label="⬇️ Baixar Dados Filtrados (Excel)",
    data=buffer.getvalue(),
    file_name="dados_filtrados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)