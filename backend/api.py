#!/usr/bin/env python3.11
"""
Swift NPS — Backend API
Serve a API de dados E o frontend estático na mesma porta.
"""

import re
from pathlib import Path
from collections import Counter
import os

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
FRONTEND   = BASE_DIR.parent / "frontend"
DATA_DIR   = BASE_DIR.parent.parent / "BasesDadosUtilizadas"
FILE_NPS   = BASE_DIR / "nps.csv"
FILE_LOJAS = BASE_DIR / "lojas.csv"

app = Flask(__name__, static_folder=str(FRONTEND), static_url_path="")
CORS(app)

# ── Rota principal — serve o index.html ───────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(FRONTEND), "index.html")

# ── Cache simples ─────────────────────────────────────────────────────────────
_cache = {}

def load_data():
    if "data" in _cache:
        return _cache["data"]

    df       = pd.read_csv(FILE_NPS, parse_dates=["Mes Ano", "Data Avaliação"])
    df_lojas = pd.read_csv(FILE_LOJAS, parse_dates=["Mes Ano"])

    df_valid = df[df["classificacao"].isin(["promotor", "neutro", "detrator"])].copy()
    df_valid["ano_mes"] = df_valid["Mes Ano"].dt.to_period("M").astype(str)

    df_merged = df_valid.merge(
        df_lojas[["CentroNv2", "Mes Ano", "Regiao_IM"]].drop_duplicates(),
        on=["CentroNv2", "Mes Ano"],
        how="left",
    )
    df_merged["Regiao_IM"] = df_merged["Regiao_IM"].fillna("Não informado")
    df_merged["ano_mes"]   = df_merged["Mes Ano"].dt.to_period("M").astype(str)

    result = (df_valid, df_merged, df_lojas)
    _cache["data"] = result
    return result

# ── Helpers ───────────────────────────────────────────────────────────────────
STOPWORDS_PT = {
    "a","ao","aos","as","até","com","como","da","das","de","do","dos","e","é",
    "em","essa","esse","esta","este","eu","foi","há","isso","isto","já","mas",
    "me","meu","minha","muito","na","nas","não","nao","nem","no","nos","o","os",
    "ou","para","pela","pelo","que","se","sem","ser","seu","sua","são","ta","tá",
    "tem","ter","um","uma","vai","vc","você","vocês","loja","swift","sempre",
    "tudo","bem","boa","bom","cada","coisa","dia","faz","fui","ja","la","mais",
    "melhor","menos","mesmo","né","ok","pra","quando","só","vez","vezes","mt",
    "pq","q","msm","por","tb","ainda","assim","compra","comprei","comprar",
}

def limpar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.lower()
    texto = re.sub(r"http\S+", "", texto)
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\d+", "", texto)
    return texto

def nome_curto(centro):
    return re.sub(r"^L\d+-", "", centro).split("(")[0].strip()

def calc_nps(p, d, t):
    if t == 0:
        return 0.0
    return round((p - d) / t * 100, 1)

def apply_filters(df, date_from=None, date_to=None, flag=None):
    if date_from:
        df = df[df["ano_mes"] >= date_from]
    if date_to:
        df = df[df["ano_mes"] <= date_to]
    if flag and flag in ("REGULAR", "TOCADORA") and "Flag" in df.columns:
        df = df[df["Flag"] == flag]
    return df

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/big-numbers")
def big_numbers():
    df, _, _ = load_data()
    df = apply_filters(df, request.args.get("from"), request.args.get("to"), request.args.get("flag"))
    P  = int(df[df["classificacao"] == "promotor"]["qtd_clientes"].sum())
    N  = int(df[df["classificacao"] == "neutro"]["qtd_clientes"].sum())
    De = int(df[df["classificacao"] == "detrator"]["qtd_clientes"].sum())
    T  = P + N + De
    return jsonify({
        "nps_geral":        calc_nps(P, De, T),
        "total_avaliacoes": T,
        "total_lojas":      int(df["CentroNv2"].nunique()),
        "pct_promotor":     round(P  / T * 100, 1) if T else 0,
        "pct_neutro":       round(N  / T * 100, 1) if T else 0,
        "pct_detrator":     round(De / T * 100, 1) if T else 0,
    })

@app.route("/api/nps-mensal")
def nps_mensal():
    df, _, _ = load_data()
    df = apply_filters(df, request.args.get("from"), request.args.get("to"), request.args.get("flag"))
    mensal = (
        df.groupby(["ano_mes", "classificacao"])["qtd_clientes"]
        .sum().unstack(fill_value=0).reset_index()
    )
    mensal.columns.name = None
    for c in ["promotor", "neutro", "detrator"]:
        if c not in mensal.columns:
            mensal[c] = 0
    mensal["total"]        = mensal["promotor"] + mensal["neutro"] + mensal["detrator"]
    mensal["nps"]          = mensal.apply(lambda r: calc_nps(r["promotor"], r["detrator"], r["total"]), axis=1)
    mensal["pct_promotor"] = (mensal["promotor"] / mensal["total"] * 100).round(1)
    mensal["pct_neutro"]   = (mensal["neutro"]   / mensal["total"] * 100).round(1)
    mensal["pct_detrator"] = (mensal["detrator"] / mensal["total"] * 100).round(1)
    cols = ["ano_mes","nps","pct_promotor","pct_neutro","pct_detrator","total","promotor","neutro","detrator"]
    return jsonify(mensal[cols].rename(columns={"ano_mes":"label"}).to_dict(orient="records"))

@app.route("/api/volume-mensal")
def volume_mensal():
    df, _, _ = load_data()
    df = apply_filters(df, request.args.get("from"), request.args.get("to"), request.args.get("flag"))
    vol = df.groupby("ano_mes")["qtd_clientes"].sum().reset_index()
    return jsonify(vol.rename(columns={"ano_mes":"label","qtd_clientes":"total"}).to_dict(orient="records"))

@app.route("/api/ranking-lojas")
def ranking_lojas():
    df, _, _ = load_data()
    df = apply_filters(df, request.args.get("from"), request.args.get("to"), request.args.get("flag"))
    counts = df.groupby(["CentroNv2","classificacao"]).size().unstack(fill_value=0).reset_index()
    for c in ["promotor","neutro","detrator"]:
        if c not in counts.columns:
            counts[c] = 0
    counts["T"]          = counts["promotor"] + counts["neutro"] + counts["detrator"]
    counts["nps"]        = counts.apply(lambda r: calc_nps(r["promotor"], r["detrator"], r["T"]), axis=1)
    counts["nome_curto"] = counts["CentroNv2"].map(nome_curto)
    top5 = counts.nlargest(5,  "nps")[["nome_curto","nps"]].to_dict(orient="records")
    bot5 = counts.nsmallest(5, "nps")[["nome_curto","nps"]].to_dict(orient="records")
    return jsonify({"top5": top5, "bot5": bot5})

@app.route("/api/volume-lojas")
def volume_lojas():
    df, _, _ = load_data()
    vol = df.groupby("CentroNv2")["qtd_clientes"].sum().reset_index()
    vol["nome_curto"] = vol["CentroNv2"].map(nome_curto)
    top5 = vol.nlargest(5,  "qtd_clientes")[["nome_curto","qtd_clientes"]].rename(columns={"qtd_clientes":"total"}).to_dict(orient="records")
    bot5 = vol.nsmallest(5, "qtd_clientes")[["nome_curto","qtd_clientes"]].rename(columns={"qtd_clientes":"total"}).to_dict(orient="records")
    return jsonify({"top5": top5, "bot5": bot5})

@app.route("/api/detratores-regiao")
def detratores_regiao():
    _, df_merged, _ = load_data()
    det = df_merged[df_merged["classificacao"]=="detrator"].groupby("Regiao_IM")["qtd_clientes"].sum().reset_index()
    tot = df_merged.groupby("Regiao_IM")["qtd_clientes"].sum().reset_index().rename(columns={"qtd_clientes":"total"})
    result = det.merge(tot, on="Regiao_IM")
    result["pct_detrator"] = (result["qtd_clientes"] / result["total"] * 100).round(1)
    result = result[result["Regiao_IM"] != "Não informado"].sort_values("pct_detrator", ascending=False)
    return jsonify(result.rename(columns={"Regiao_IM":"regiao","qtd_clientes":"detratores"}).to_dict(orient="records"))

@app.route("/api/flag-comparison")
def flag_comparison():
    df, _, _ = load_data()
    result = {}
    if "Flag" not in df.columns:
        return jsonify(result)
    for flag in ["REGULAR","TOCADORA"]:
        sub = df[df["Flag"] == flag]
        P  = int(sub[sub["classificacao"]=="promotor"]["qtd_clientes"].sum())
        N  = int(sub[sub["classificacao"]=="neutro"]["qtd_clientes"].sum())
        De = int(sub[sub["classificacao"]=="detrator"]["qtd_clientes"].sum())
        T  = P + N + De
        result[flag] = {
            "nps":          calc_nps(P, De, T),
            "total":        T,
            "pct_promotor": round(P  / T * 100, 1) if T else 0,
            "pct_neutro":   round(N  / T * 100, 1) if T else 0,
            "pct_detrator": round(De / T * 100, 1) if T else 0,
        }
    return jsonify(result)

@app.route("/api/word-cloud")
def word_cloud():
    df, _, _ = load_data()
    det = df[(df["classificacao"]=="detrator") & df["Comentario"].notna() & ~df["Comentario"].isin(["-",""])]
    palavras = Counter()
    for txt in det["Comentario"].dropna():
        tokens = limpar_texto(txt).split()
        palavras.update(t for t in tokens if t not in STOPWORDS_PT and len(t) > 2)
    return jsonify([{"word": w, "count": c} for w, c in palavras.most_common(80)])

@app.route("/api/temas")
def temas():
    return jsonify([
        {"categoria":"Preços e Experiência Geral","pct":19.9,"count":9958, "nps_perfil":"90,6% promotores"},
        {"categoria":"Atendimento Positivo",       "pct":15.4,"count":7707, "nps_perfil":"97,9% promotores"},
        {"categoria":"Qualidade dos Produtos",     "pct":13.4,"count":6679, "nps_perfil":"56,9% promotores"},
        {"categoria":"Operações da Loja",          "pct":11.9,"count":5941, "nps_perfil":"50,2% promotores"},
        {"categoria":"Marca Swift",                "pct": 4.8,"count":2413, "nps_perfil":"69,0% promotores"},
        {"categoria":"Canal Digital",              "pct": 2.4,"count":1213, "nps_perfil":"72,3% promotores"},
        {"categoria":"Elogios Gerais",             "pct": 1.3,"count": 654, "nps_perfil":"79,0% promotores"},
        {"categoria":"Outros/Inclassificável",     "pct":30.9,"count":15433,"nps_perfil":"77,3% promotores"},
    ])

@app.route("/api/comprimento-comentarios")
def comprimento_comentarios():
    df, _, _ = load_data()
    com = df[df["Comentario"].notna() & ~df["Comentario"].isin(["-",""])].copy()
    com["n_palavras"] = com["Comentario"].str.split().str.len()
    stats = (
        com.groupby("classificacao")["n_palavras"]
        .agg(["mean","median","count"])
        .reset_index()
        .rename(columns={"mean":"media","median":"mediana","count":"total"})
        .round(1)
    )
    return jsonify(stats.to_dict(orient="records"))

@app.route("/api/cobertura-comentarios")
def cobertura_comentarios():
    df, _, _ = load_data()
    total   = df.groupby("classificacao")["qtd_clientes"].sum()
    com_cnt = df[df["Comentario"].notna() & ~df["Comentario"].isin(["-",""])].groupby("classificacao")["qtd_clientes"].sum()
    result = []
    for cls in ["detrator","neutro","promotor"]:
        t = int(total.get(cls, 0))
        c = int(com_cnt.get(cls, 0))
        result.append({
            "classificacao":        cls,
            "pct_com_comentario":   round(c / t * 100, 1) if t else 0,
            "total":                t,
            "com_comentario":       c,
        })
    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
