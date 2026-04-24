"""
main.py — CLI para rodar sem interface web (opcional)
Para a interface web use: python app.py
"""

import sys
import time
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def main():
    parser = argparse.ArgumentParser(description="Agente Gemini — CLI")
    parser.add_argument("--tema", "-t", type=str, default=None)
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]🤖 Agente Gemini — Pipeline Multi-Agente[/bold cyan]\n"
        "[dim]Pesquisador → Analista → Redator → Gerente[/dim]",
        border_style="cyan", padding=(1,4)
    ))

    tema = args.tema or console.input("[bold]📌 Tema:[/bold] [cyan]➜  [/cyan]").strip()
    if not tema: sys.exit(1)

    from crew import executar
    inicio = time.time()

    try:
        with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"), console=console, transient=True) as p:
            p.add_task("Executando pipeline...", total=None)
            executar(tema)

        console.print(f"\n[dim]⏱ {time.time()-inicio:.1f}s[/dim]")

        for nome in ["relatorio_revisado.md", "relatorio_final.md"]:
            p = Path(f"output/{nome}")
            if p.exists():
                console.print(Panel(f"[green]Salvo em:[/green] output/{nome}", border_style="green"))
                console.print(Markdown(p.read_text(encoding="utf-8")))
                break

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrompido.[/yellow]")

if __name__ == "__main__":
    main()
