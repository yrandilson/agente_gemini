"""
crew.py — Pipeline multi-agente com suporte a log_callback (SSE web)
"""

from agents import criar_pesquisador, criar_analista, criar_redator, criar_gerente


TAREFAS = {
    "pesquisa": lambda tema: (
        f"Pesquise extensivamente: **{tema}**\n"
        "Faça 3+ buscas distintas, registre data/hora, "
        "organize em: Contexto, Situação Atual, Dados, Tendências, Fontes. "
        "Mínimo 600 palavras."
    ),
    "analise": lambda tema: (
        f"Analise o material de pesquisa sobre: **{tema}**\n"
        "Use analisar_texto, liste 5 insights, tabela oportunidades/riscos, "
        "relevância por subtema (1-10), lacunas de informação."
    ),
    "redacao": lambda tema: (
        f"Escreva o relatório executivo completo sobre: **{tema}**\n"
        "Use toda a pesquisa e análise do contexto. Estrutura de 8 seções. "
        "Salve como 'relatorio_final.md'."
    ),
    "revisao": lambda tema: (
        f"Revise e aprove o relatório sobre: **{tema}**\n"
        "Aplique checklist, corrija, adicione seção de aprovação. "
        "Salve como 'relatorio_revisado.md'."
    ),
}

ETAPAS = [
    ("pesquisa", criar_pesquisador),
    ("analise",  criar_analista),
    ("redacao",  criar_redator),
    ("revisao",  criar_gerente),
]


def executar(tema: str, log_callback=None) -> dict:
    """
    Executa o pipeline completo.
    log_callback(dict): chamado a cada evento de log (para SSE).
    Retorna dict com output de cada etapa.
    """
    contexto   = ""
    resultados = {}

    for chave, factory in ETAPAS:
        agente = factory()
        if log_callback:
            agente.log_callback = log_callback
            log_callback({"agente": agente.nome, "emoji": agente.emoji,
                          "msg": f"Etapa iniciada", "tipo": "stage_start"})

        resultado = agente.executar(
            tarefa=TAREFAS[chave](tema),
            contexto=contexto,
        )
        resultados[chave]  = resultado
        contexto          += f"\n\n### OUTPUT — {agente.nome} ###\n{resultado}"

        if log_callback:
            log_callback({"agente": agente.nome, "emoji": agente.emoji,
                          "msg": "Etapa concluída", "tipo": "stage_done",
                          "output": resultado[:300] + "..."})

    return resultados
