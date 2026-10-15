from pathlib import Path

import plotly.graph_objects as go

# YtD compara jan–set dos dois anos: 2026 só tem dados até 30/09
ULTIMO_MES = 9
MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set")
COR_2025 = "#9AA0A6"
COR_2026 = "#2563A6"
COR_SUBTITULO = "#202124"
COR_DESTAQUE = "#188038"
COR_QUEDA = "#C5221F"
COR_TOTAL = "#5F6368"
ETAPAS_FUNIL = ("Lead", "Qualificado", "Proposta", "Negociação", "Ganho")


def formatar_milhoes(valor: float) -> str:
    return f"R$ {valor / 1e6:.2f}M".replace(".", ",")


# Formata os pontos percentuais (p.p)
def formatar_pp(valor: float) -> str:
    return f"{valor * 100:+.1f} p.p.".replace(".", ",", 1)


def destacar(texto: str, valor: float) -> str:
    cor = COR_DESTAQUE if valor >= 0 else COR_QUEDA
    return f"<span style='color:{cor}'>{texto}</span>"


def salvar_html(figura: go.Figure, caminho: Path) -> None:
    caminho.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;min-height:100vh;display:flex;"
        "justify-content:center;align-items:center;background:#F4F5F7'>"
        "<div style='background:#FFFFFF;padding:24px;border-radius:12px;"
        "border:1px solid #E3E5E8;box-shadow:0 2px 8px rgba(0,0,0,0.06)'>"
        f"{figura.to_html(full_html=False)}</div></body></html>",
        encoding="utf-8",
    )
