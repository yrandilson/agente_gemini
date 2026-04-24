# 📖 Manual Completo — Agente Gemini

Documentação técnica detalhada do sistema multi-agente com Google Gemini.

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Estrutura de Arquivos](#2-estrutura-de-arquivos)
3. [Como Funciona — Fluxo Completo](#3-como-funciona--fluxo-completo)
4. [config.py](#4-configpy)
5. [tools/custom_tools.py](#5-toolscustom_toolspy)
6. [agents/base_agent.py](#6-agentsbase_agentpy)
7. [agents/agentes.py](#7-agentsagentespy)
8. [crew.py](#8-crewpy)
9. [app.py — Servidor Web](#9-apppy--servidor-web)
10. [templates/index.html — Interface Web](#10-templatesindexhtml--interface-web)
11. [main.py — CLI](#11-mainpy--cli)
12. [Erro 429 — Rate Limit](#12-erro-429--rate-limit)
13. [Configuração do .env](#13-configuração-do-env)
14. [Perguntas Frequentes](#14-perguntas-frequentes)

---

## 1. Visão Geral

O sistema é um **pipeline de 4 agentes de IA** que trabalham em sequência para pesquisar um tema, analisar os dados, escrever um relatório e revisar a qualidade — tudo de forma automática.

```
Usuário fornece um TEMA
         ↓
  🔍 PESQUISADOR  →  busca dados na internet (DuckDuckGo)
         ↓  (repassa resultado)
  📊 ANALISTA     →  analisa métricas e extrai insights
         ↓  (repassa resultado)
  ✍️  REDATOR     →  escreve relatório executivo em Markdown
         ↓  (repassa resultado)
  🎯 GERENTE      →  revisa, aprova e salva relatório final
         ↓
  output/relatorio_revisado.md
```

Cada agente recebe o contexto completo de todos os anteriores, garantindo coerência no relatório final.

**Tecnologias usadas:**

| Componente | Tecnologia |
|---|---|
| LLM | Google Gemini (via `google-genai`) |
| Busca web | DuckDuckGo (sem API key) |
| Servidor web | Flask + SSE (Server-Sent Events) |
| Interface | HTML/CSS/JS puro (sem framework) |
| CLI | Python + Rich |

---

## 2. Estrutura de Arquivos

```
agente_gemini/
│
├── app.py                  ← Servidor web Flask
├── main.py                 ← CLI (linha de comando)
├── crew.py                 ← Orquestra o pipeline completo
├── config.py               ← Lê variáveis do .env
├── requirements.txt        ← Dependências Python
├── .env.example            ← Modelo do arquivo de configuração
│
├── agents/
│   ├── __init__.py         ← Exporta as funções de criação
│   ├── base_agent.py       ← Motor de um agente (loop Gemini)
│   └── agentes.py          ← Define os 4 agentes
│
├── tools/
│   ├── __init__.py         ← Exporta TOOLS_SCHEMA e executar_ferramenta
│   └── custom_tools.py     ← Implementação das 4 ferramentas
│
├── templates/
│   └── index.html          ← Interface web completa (1 arquivo)
│
└── output/                 ← Relatórios gerados ficam aqui
    ├── relatorio_final.md
    └── relatorio_revisado.md
```

---

## 3. Como Funciona — Fluxo Completo

### 3.1 Interface Web (app.py)

```
Usuário digita tema e clica Executar
            ↓
  Navegador faz POST /api/run  {"tema": "..."}
            ↓
  Flask inicia uma Thread em background (crew.executar)
            ↓
  Navegador abre SSE: GET /api/stream
  (conexão persistente que recebe eventos em tempo real)
            ↓
  Enquanto os agentes rodam, eventos chegam:
    {"tipo": "stage_start", "agente": "Pesquisador", ...}
    {"tipo": "tool",        "agente": "Pesquisador", "msg": "🔧 busca_web(...)"}
    {"tipo": "stage_done",  "agente": "Pesquisador", ...}
    ... (para cada agente)
    {"tipo": "end"}
            ↓
  Navegador faz GET /api/report → renderiza Markdown
```

### 3.2 Loop Agentico (base_agent.py)

O coração do sistema. Para cada agente:

```
1. Cria um chat Gemini com system_prompt do agente
2. Envia a tarefa + contexto dos agentes anteriores
3. Gemini responde com:
   a) Texto final  → fim, retorna texto
   b) Function call → executa ferramenta, envia resultado, volta ao passo 3
4. Repete até sem function calls ou max_iteracoes
```

**Exemplo real de uma iteração:**

```
[Pesquisador] → "Pesquise sobre SaaS para barbearias"
    ↓
Gemini decide usar busca_web("SaaS barbearias Brasil")
    ↓
Sistema executa DuckDuckGo, retorna 5 resultados
    ↓
Gemini recebe resultados, decide buscar mais:
busca_web("agendamento online barbearia nordeste")
    ↓
Sistema executa novamente
    ↓
Gemini recebe, decide buscar mais:
busca_web("mercado barbershop software gestão")
    ↓
Gemini recebe todos os resultados e escreve o documento
    ↓
Retorna texto (sem mais function calls) → fim
```

---

## 4. config.py

```python
import os
from dotenv import load_dotenv

load_dotenv()  # lê o arquivo .env

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
PORT           = int(os.getenv("PORT", 5000))
VERBOSE        = os.getenv("VERBOSE", "true").lower() == "true"
```

**O que faz:** Centraliza todas as configurações. Qualquer outro arquivo importa daqui.  
`load_dotenv()` lê o `.env` e coloca os valores em variáveis de ambiente.  
Se `GEMINI_API_KEY` estiver vazio, lança erro imediatamente com mensagem clara.

---

## 5. tools/custom_tools.py

Define as **ferramentas que os agentes podem usar**.

### TOOLS_SCHEMA

Lista de dicionários descrevendo cada ferramenta para o Gemini:

```python
TOOLS_SCHEMA = [
    {
        "name": "busca_web",
        "description": "Pesquisa informações na internet...",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termos de busca"}
            },
            "required": ["query"]
        }
    },
    # ... mais ferramentas
]
```

O Gemini lê esse schema e decide **quando** e **como** chamar cada ferramenta.

### As 4 ferramentas

| Ferramenta | O que faz | Parâmetros |
|---|---|---|
| `busca_web` | Busca no DuckDuckGo, retorna 5 resultados | `query: str` |
| `analisar_texto` | Conta palavras, sentenças, top 10 termos | `texto: str` |
| `salvar_arquivo` | Salva .md em output/ | `nome_arquivo, conteudo` |
| `data_hora_atual` | Retorna data/hora atual | nenhum |

### executar_ferramenta

```python
def executar_ferramenta(nome: str, params: dict) -> str:
    if nome == "busca_web":       return busca_web(params["query"])
    if nome == "analisar_texto":  return analisar_texto(params["texto"])
    if nome == "salvar_arquivo":  return salvar_arquivo(...)
    if nome == "data_hora_atual": return data_hora_atual()
```

Dispatcher central — recebe nome e parâmetros, chama a função certa.

---

## 6. agents/base_agent.py

O arquivo mais importante. Implementa o **loop agentico com Gemini**.

### _build_tools

```python
def _build_tools(tools_permitidas: list[str]):
    declarations = []
    for t in TOOLS_SCHEMA:
        if t["name"] in tools_permitidas:
            declarations.append(
                types.FunctionDeclaration(name=t["name"], ...)
            )
    return [types.Tool(function_declarations=declarations)]
```

Converte o schema JSON para objetos `FunctionDeclaration` que o SDK do Gemini entende.  
Cada agente só recebe as ferramentas que precisa (ex: Pesquisador não recebe `salvar_arquivo`).

### _chamar_api_com_retry *(novo)*

```python
def _chamar_api_com_retry(fn, max_tentativas=5, log_fn=None):
    for tentativa in range(1, max_tentativas + 1):
        try:
            return fn()             # tenta executar
        except ResourceExhausted:   # erro 429
            espera = _extrair_retry_delay(e)   # lê tempo do erro
            time.sleep(espera)      # espera e tenta de novo
```

Captura o erro 429 (rate limit), extrai o tempo de espera sugerido pelo Google no próprio JSON do erro, aguarda e tenta novamente. Até 5 tentativas.

### classe Agente

**`__init__`:** Recebe nome, emoji, system_prompt, lista de ferramentas e monta a config do Gemini.

**`executar(tarefa, contexto)`:**

```python
def executar(self, tarefa, contexto=""):
    # 1. Monta mensagem com contexto anterior + tarefa atual
    conteudo = f"CONTEXTO:\n{contexto}\n\nTAREFA:\n{tarefa}"

    # 2. Cria chat Gemini com system_prompt
    chat = client.chats.create(model=GEMINI_MODEL, config=config)

    # 3. Envia primeira mensagem (com retry se 429)
    response = _chamar_api_com_retry(lambda: chat.send_message(conteudo))

    # 4. Loop: processa function calls até ter resposta final
    for iteracao in range(max_iteracoes):
        fn_calls = [p.function_call for p in response.parts if p.function_call]

        if not fn_calls:
            return response.text  # ← SAÍDA: texto final do agente

        # Executa ferramentas
        fn_responses = [executar_ferramenta(fc.name, fc.args) for fc in fn_calls]

        # Aguarda para não estourar rate limit
        time.sleep(DELAY_ENTRE_CHAMADAS)

        # Envia resultados de volta ao Gemini
        response = _chamar_api_com_retry(lambda: chat.send_message(fn_responses))
```

---

## 7. agents/agentes.py

Define a personalidade e especialidade de cada agente via `system_prompt`.

### Por que system_prompt importa?

O `system_prompt` é a instrução permanente que molda o comportamento do Gemini para aquele agente. É como contratar um especialista e dar sua descrição de cargo.

```python
def criar_pesquisador() -> Agente:
    return Agente(
        nome="Pesquisador",
        emoji="🔍",
        tools_permitidas=["busca_web", "data_hora_atual"],
        system_prompt="""Você é um Pesquisador Especialista...
        - Realize PELO MENOS 3 buscas diferentes
        - Organize em: Contexto, Situação Atual, Dados, Tendências, Fontes
        - Produza documento com mínimo 600 palavras"""
    )
```

Cada agente tem ferramentas restritas ao que precisa, evitando que o Pesquisador, por exemplo, salve arquivos antes da hora.

---

## 8. crew.py

Orquestra o pipeline completo. Define as tarefas e conecta os agentes em sequência.

```python
ETAPAS = [
    ("pesquisa", criar_pesquisador),
    ("analise",  criar_analista),
    ("redacao",  criar_redator),
    ("revisao",  criar_gerente),
]

def executar(tema, log_callback=None):
    contexto = ""  # ← começa vazio

    for chave, factory in ETAPAS:
        agente    = factory()
        agente.log_callback = log_callback  # ← conecta logs para SSE

        resultado = agente.executar(
            tarefa=TAREFAS[chave](tema),
            contexto=contexto,      # ← passa tudo que veio antes
        )

        contexto += f"\n\n### {agente.nome} ###\n{resultado}"
        #              ↑ acumula contexto para o próximo agente
```

**Contexto acumulado** é a chave do sistema: o Redator recebe a pesquisa + análise completas, então produz um relatório coerente com tudo que foi descoberto.

O parâmetro `log_callback` é uma função injetada pela interface web para receber logs em tempo real via SSE.

---

## 9. app.py — Servidor Web

### Rotas

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/` | Serve o index.html |
| `POST` | `/api/run` | Inicia o pipeline em background |
| `GET` | `/api/stream` | SSE — stream de logs em tempo real |
| `GET` | `/api/report` | Retorna o relatório final em Markdown |
| `GET` | `/api/status` | Informa se pipeline está rodando |

### SSE (Server-Sent Events)

SSE é uma conexão HTTP persistente onde o servidor envia dados ao cliente quando quiser, sem o cliente precisar pedir. É como WebSocket, mas mais simples e unidirecional.

```python
def stream():
    def generate():
        yield "data: {\"tipo\": \"connected\"}\n\n"  # ← formato SSE
        while True:
            item = _run_queue.get(timeout=30)   # espera próximo evento
            if item == "__END__":
                yield "data: {\"tipo\": \"end\"}\n\n"
                break
            yield f"data: {item}\n\n"           # envia para o browser

    return Response(generate(), mimetype="text/event-stream")
```

### Thread em background

```python
def run():
    from crew import executar
    executar(tema, log_callback=_log_to_queue)  # coloca logs na fila
    _run_queue.put("__END__")

threading.Thread(target=run, daemon=True).start()
```

O pipeline roda em uma thread separada para não bloquear o servidor Flask. Cada log é colocado em uma `queue.Queue`. O SSE lê da fila e envia ao browser.

---

## 10. templates/index.html — Interface Web

### Estrutura visual

```
┌────────────────────────────────────────────────────┐
│  Header: Logo + Status pill                        │
├────────────────────────────────────────────────────┤
│  Input bar: [tema.....................] [Executar]  │
├──────────────────────┬─────────────┬───────────────┤
│  Sidebar             │  Log ao     │  Relatório    │
│  🔍 Pesquisador IDLE │  vivo       │  (Markdown    │
│  📊 Analista    IDLE │             │   renderizado)│
│  ✍️  Redator    IDLE │             │               │
│  🎯 Gerente     IDLE │             │               │
└──────────────────────┴─────────────┴───────────────┘
```

### SSE no JavaScript

```javascript
function startSSE() {
    evtSource = new EventSource('/api/stream');  // abre conexão

    evtSource.onmessage = (e) => {
        const data = JSON.parse(e.data);

        if (data.tipo === 'stage_start') {
            setAgentState(data.agente, 'active');  // muda cor do card
        }
        if (data.tipo === 'stage_done') {
            setAgentState(data.agente, 'done');
            setProgress(...);                      // avança barra
        }
        if (data.tipo === 'end') {
            loadReport();  // busca e renderiza relatório
        }
        addLog(data.tipo, data.agente, data.msg);  // adiciona linha no log
    };
}
```

### Renderização Markdown

Usa a biblioteca `marked.js` (CDN) para converter o Markdown do relatório em HTML:

```javascript
async function loadReport() {
    const res  = await fetch('/api/report');
    const data = await res.json();
    document.getElementById('reportBody').innerHTML = marked.parse(data.content);
}
```

---

## 11. main.py — CLI

Alternativa à interface web. Roda o mesmo pipeline no terminal com visual via Rich.

```bash
python main.py -t "SaaS para barbearias no Nordeste"
# ou interativo:
python main.py
```

---

## 12. Erro 429 — Rate Limit

### O que é

O free tier do Gemini permite **5 requisições por minuto** por modelo. O pipeline faz múltiplas chamadas por agente (uma por iteração do loop), então estoura o limite facilmente.

### Solução implementada (nova versão)

**1. Retry automático com backoff:**

```python
def _chamar_api_com_retry(fn, max_tentativas=5):
    for tentativa in range(max_tentativas):
        try:
            return fn()
        except ResourceExhausted as e:
            espera = _extrair_retry_delay(e)  # ex: 52s (do JSON do erro)
            time.sleep(espera)                # espera e tenta de novo
```

O Google informa exatamente quanto esperar no corpo do erro:
```json
"retryDelay": "52s"
```
O código extrai esse número com regex e usa como tempo de espera.

**2. Delay preventivo entre chamadas:**

```python
DELAY_ENTRE_CHAMADAS = 15  # segundos

# Antes de cada chamada pós-tool:
time.sleep(DELAY_ENTRE_CHAMADAS)
```

Com 5 req/min = 1 req a cada 12s. Usar 15s garante margem de segurança.

### Alternativas se continuar ocorrendo

**Opção A — Trocar para gemini-2.0-flash** (limites diferentes):
```env
GEMINI_MODEL=gemini-2.0-flash
```

**Opção B — Adicionar billing** no Google AI Studio (aumenta para 1000+ req/min):
- Acesse: https://aistudio.google.com/
- Ative faturamento (tem free tier generoso com billing ativo)

**Opção C — Reduzir chamadas** (menos buscas por agente):
- Edite o system_prompt do Pesquisador: `"Faça 1 busca"` em vez de `"3 buscas"`

### Tabela de limites do free tier

| Modelo | Req/min | Tokens/min |
|---|---|---|
| gemini-2.5-flash | 5 | 250.000 |
| gemini-2.5-pro | 5 | 250.000 |
| gemini-2.0-flash | 15 | 1.000.000 |

---

## 13. Configuração do .env

```env
# Chave da API (obrigatório)
# Crie grátis em: https://aistudio.google.com/apikey
GEMINI_API_KEY=AIzaSy...

# Modelo — recomendado para free tier:
# gemini-2.0-flash  → 15 req/min (melhor para free tier)
# gemini-2.5-flash  → 5 req/min  (mais inteligente)
# gemini-2.5-pro    → 5 req/min  (melhor qualidade)
GEMINI_MODEL=gemini-2.0-flash

# Porta do servidor web
PORT=5000

# true = mostra raciocínio dos agentes no terminal
# false = silencioso
VERBOSE=true
```

> **Dica:** Para o free tier, use `gemini-2.0-flash` — tem 15 req/min em vez de 5.

---

## 14. Perguntas Frequentes

**P: Por que o pipeline demora tanto?**  
R: O delay de 15s entre chamadas é intencional para respeitar o rate limit do free tier. Com billing ativo no Google, pode reduzir `DELAY_ENTRE_CHAMADAS` para 1-2s.

**P: Posso adicionar um 5º agente?**  
R: Sim. Crie uma função em `agentes.py`, adicione à lista `ETAPAS` no `crew.py` e defina a tarefa em `TAREFAS`.

**P: Como trocar o DuckDuckGo por outro buscador?**  
R: Edite `busca_web()` em `tools/custom_tools.py`. Pode usar SerpAPI, Tavily, ou qualquer outra.

**P: Posso usar outro LLM além do Gemini?**  
R: Sim. Reescreva `base_agent.py` para usar a API desejada (OpenAI, Anthropic, etc.). O resto do código não muda.

**P: O relatório pode ser gerado em PDF?**  
R: Não nativamente. Mas você pode abrir o `.md` em um editor Markdown e exportar como PDF, ou adicionar uma ferramenta `gerar_pdf` usando `weasyprint` ou `reportlab`.

**P: Como rodar em produção (servidor)?**  
R: Troque `app.run(debug=False)` por um servidor WSGI como `gunicorn`:
```bash
pip install gunicorn
gunicorn app:app -w 1 -b 0.0.0.0:5000
```
Use `-w 1` (1 worker) para não ter conflito com a fila global de SSE.
