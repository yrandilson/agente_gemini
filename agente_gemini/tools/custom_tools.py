"""
tools/custom_tools.py — Ferramentas dos agentes (formato Gemini Function Calling)
"""

import json
import datetime
from duckduckgo_search import DDGS


# ─────────────────────────────────────────────
# Schema das ferramentas (formato Gemini)
# ─────────────────────────────────────────────

TOOLS_SCHEMA = [
    {
        "name": "busca_web",
        "description": "Pesquisa informações atualizadas na internet. Use para coletar dados sobre qualquer tema.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termos de busca"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "analisar_texto",
        "description": "Analisa métricas de um texto: palavras, sentenças, parágrafos e top termos.",
        "parameters": {
            "type": "object",
            "properties": {
                "texto": {"type": "string", "description": "Texto a analisar"}
            },
            "required": ["texto"],
        },
    },
    {
        "name": "salvar_arquivo",
        "description": "Salva conteúdo em arquivo .md na pasta output/.",
        "parameters": {
            "type": "object",
            "properties": {
                "nome_arquivo": {"type": "string", "description": "Nome do arquivo (ex: relatorio.md)"},
                "conteudo":     {"type": "string", "description": "Conteúdo a salvar"},
            },
            "required": ["nome_arquivo", "conteudo"],
        },
    },
    {
        "name": "data_hora_atual",
        "description": "Retorna a data e hora atual do sistema.",
        "parameters": {"type": "object", "properties": {}},
    },
]


# ─────────────────────────────────────────────
# Implementações
# ─────────────────────────────────────────────

def busca_web(query: str) -> str:
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=5))
        if not resultados:
            return "Nenhum resultado encontrado."
        linhas = []
        for i, r in enumerate(resultados, 1):
            linhas.append(
                f"[{i}] {r.get('title', '')}\n"
                f"URL: {r.get('href', '')}\n"
                f"Resumo: {r.get('body', '')}\n"
            )
        return "\n".join(linhas)
    except Exception as e:
        return f"Erro na busca: {e}"


def analisar_texto(texto: str) -> str:
    palavras   = texto.split()
    sentencas  = texto.count(".") + texto.count("!") + texto.count("?")
    paragrafos = [p for p in texto.split("\n\n") if p.strip()]
    stopwords  = {
        "de","a","o","que","e","do","da","em","um","para","é","com","uma","os",
        "no","se","na","por","mais","as","dos","como","mas","foi","ao","ele",
        "das","tem","à","seu","sua","ou","ser","quando","muito","há","nos","já",
        "está","eu","também","só","pelo","pela","até","isso","ela","entre","era",
    }
    freq: dict = {}
    for w in palavras:
        wc = w.lower().strip(".,!?;:\"'()[]")
        if wc and wc not in stopwords and len(wc) > 2:
            freq[wc] = freq.get(wc, 0) + 1
    top10 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
    return json.dumps(
        {"total_palavras": len(palavras), "total_sentencas": sentencas,
         "total_paragrafos": len(paragrafos), "top10_palavras": top10},
        ensure_ascii=False, indent=2
    )


def salvar_arquivo(nome_arquivo: str, conteudo: str) -> str:
    try:
        caminho = f"output/{nome_arquivo}"
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        return f"Arquivo salvo: {caminho}"
    except Exception as e:
        return f"Erro ao salvar: {e}"


def data_hora_atual() -> str:
    return datetime.datetime.now().strftime("Data: %d/%m/%Y | Hora: %H:%M:%S")


def executar_ferramenta(nome: str, params: dict) -> str:
    if nome == "busca_web":       return busca_web(params.get("query", ""))
    if nome == "analisar_texto":  return analisar_texto(params.get("texto", ""))
    if nome == "salvar_arquivo":  return salvar_arquivo(params.get("nome_arquivo", "out.md"), params.get("conteudo", ""))
    if nome == "data_hora_atual": return data_hora_atual()
    return f"Ferramenta desconhecida: {nome}"
