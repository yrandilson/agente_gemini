"""
agents/base_agent.py — Motor agentico usando google-genai (SDK novo)
Com retry automático para erro 429 RESOURCE_EXHAUSTED (rate limit).
"""

import re
import time
from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted
from config import GEMINI_API_KEY, GEMINI_MODEL, VERBOSE
from tools import TOOLS_SCHEMA, executar_ferramenta

client = genai.Client(api_key=GEMINI_API_KEY)

# ── Delay entre chamadas para não estourar free tier (5 req/min) ────────────
# Free tier = 5 req/min → 1 req a cada 12s com margem
DELAY_ENTRE_CHAMADAS = 15  # segundos entre cada chamada à API


def _build_tools(tools_permitidas: list[str]):
    declarations = []
    for t in TOOLS_SCHEMA:
        if t["name"] in tools_permitidas:
            declarations.append(
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=t["parameters"],
                )
            )
    return [types.Tool(function_declarations=declarations)] if declarations else None


def _extrair_retry_delay(erro: Exception) -> int:
    """Tenta extrair o tempo de espera sugerido pelo erro 429."""
    texto = str(erro)
    # Procura "retry in Xs" no JSON da resposta
    match = re.search(r'retry[^\d]+(\d+(?:\.\d+)?)\s*s', texto, re.IGNORECASE)
    if match:
        return int(float(match.group(1))) + 5  # adiciona 5s de margem
    return 65  # fallback conservador


def _chamar_api_com_retry(fn, max_tentativas: int = 5, log_fn=None):
    """
    Executa fn() com retry automático em caso de 429.
    Usa o tempo de espera sugerido pelo próprio erro.
    """
    for tentativa in range(1, max_tentativas + 1):
        try:
            return fn()
        except ResourceExhausted as e:
            espera = _extrair_retry_delay(e)
            msg = f"⏳ Rate limit (429). Aguardando {espera}s antes de tentar novamente... (tentativa {tentativa}/{max_tentativas})"
            if log_fn:
                log_fn({"agente": "Sistema", "emoji": "⚙️", "msg": msg, "tipo": "warn"})
            if VERBOSE:
                from rich.console import Console
                Console().print(f"  [yellow]{msg}[/yellow]")
            time.sleep(espera)
        except Exception as e:
            raise e  # outros erros sobem normalmente
    raise RuntimeError(f"Falha após {max_tentativas} tentativas por rate limit.")


class Agente:
    def __init__(
        self,
        nome: str,
        emoji: str,
        system_prompt: str,
        tools_permitidas: list[str],
        max_iteracoes: int = 10,
    ):
        self.nome             = nome
        self.emoji            = emoji
        self.system_prompt    = system_prompt
        self.tools_permitidas = tools_permitidas
        self.max_iteracoes    = max_iteracoes
        self.gemini_tools     = _build_tools(tools_permitidas)
        self.log_callback     = None

    def _log(self, msg: str, tipo: str = "info"):
        if VERBOSE:
            from rich.console import Console
            Console().print(f"  [dim]{self.emoji} [{self.nome}][/dim] {msg}")
        if self.log_callback:
            self.log_callback({"agente": self.nome, "emoji": self.emoji,
                               "msg": msg, "tipo": tipo})

    def executar(self, tarefa: str, contexto: str = "") -> str:
        conteudo = tarefa
        if contexto:
            conteudo = (
                f"=== CONTEXTO DAS ETAPAS ANTERIORES ===\n{contexto}\n\n"
                f"=== SUA TAREFA ===\n{tarefa}"
            )

        self._log(f"Iniciando: {tarefa[:80]}...", "start")

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            tools=self.gemini_tools,
        )

        # Inicia chat (sem chamar API ainda)
        chat = client.chats.create(model=GEMINI_MODEL, config=config)

        # Primeira chamada com retry
        response = _chamar_api_com_retry(
            lambda: chat.send_message(conteudo),
            log_fn=self.log_callback
        )

        for iteracao in range(self.max_iteracoes):

            fn_calls = [
                p.function_call
                for p in response.candidates[0].content.parts
                if p.function_call and p.function_call.name
            ]

            if not fn_calls:
                texto = response.text or ""
                self._log(f"Concluído em {iteracao + 1} iteração(ões) ✅", "done")
                return texto

            # Executa ferramentas (sem chamar API)
            fn_responses = []
            for fc in fn_calls:
                nome   = fc.name
                params = dict(fc.args)
                self._log(f"🔧 {nome}({list(params.values())[0] if params else ''})", "tool")
                resultado = executar_ferramenta(nome, params)
                self._log(f"   ↳ {str(resultado)[:100]}", "tool_result")
                fn_responses.append(
                    types.Part.from_function_response(
                        name=nome,
                        response={"result": resultado},
                    )
                )

            # Aguarda antes de chamar API novamente (respeita free tier)
            self._log(f"⏱ Aguardando {DELAY_ENTRE_CHAMADAS}s (free tier)...", "info")
            time.sleep(DELAY_ENTRE_CHAMADAS)

            # Envia resultados das ferramentas com retry
            response = _chamar_api_com_retry(
                lambda r=fn_responses: chat.send_message(r),
                log_fn=self.log_callback
            )

        try:
            return response.text or ""
        except Exception:
            return "Agente não produziu resposta final."
