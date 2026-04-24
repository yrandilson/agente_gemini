"""
app.py — Servidor Flask com SSE para streaming de logs em tempo real
"""

import json
import queue
import threading
import os
from pathlib import Path

from flask import Flask, render_template, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Estado global por execução ───────────────────────────────────────────────
_run_queue: queue.Queue = queue.Queue()
_running = False


def _log_to_queue(evento: dict):
    _run_queue.put(json.dumps(evento, ensure_ascii=False))


# ── Rotas ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def run_pipeline():
    global _running, _run_queue

    data = request.get_json()
    tema = (data or {}).get("tema", "").strip()

    if not tema:
        return jsonify({"error": "Tema não pode estar vazio"}), 400

    if _running:
        return jsonify({"error": "Já há uma execução em andamento"}), 409

    # Limpa fila anterior
    _run_queue = queue.Queue()
    _running   = True

    def run():
        global _running
        try:
            from crew import executar
            _log_to_queue({"tipo": "pipeline_start", "tema": tema,
                           "msg": f"Iniciando pipeline para: {tema}"})
            resultados = executar(tema, log_callback=_log_to_queue)
            _log_to_queue({"tipo": "pipeline_done", "msg": "Pipeline concluído!"})
        except Exception as e:
            _log_to_queue({"tipo": "error", "msg": str(e)})
        finally:
            _running = False
            _run_queue.put("__END__")

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/stream")
def stream():
    """SSE endpoint — envia eventos de log em tempo real."""
    def generate():
        yield "data: {\"tipo\": \"connected\"}\n\n"
        while True:
            try:
                item = _run_queue.get(timeout=30)
                if item == "__END__":
                    yield "data: {\"tipo\": \"end\"}\n\n"
                    break
                yield f"data: {item}\n\n"
            except queue.Empty:
                yield "data: {\"tipo\": \"ping\"}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/report")
def get_report():
    """Retorna o relatório final em Markdown."""
    for nome in ["relatorio_revisado.md", "relatorio_final.md"]:
        p = Path(f"output/{nome}")
        if p.exists():
            return jsonify({"content": p.read_text(encoding="utf-8"), "file": nome})
    return jsonify({"content": "", "file": None})


@app.route("/api/status")
def status():
    return jsonify({"running": _running})


if __name__ == "__main__":
    from config import PORT
    print(f"\n🤖 Agente Gemini — Interface Web")
    print(f"   Acesse: http://localhost:{PORT}\n")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
