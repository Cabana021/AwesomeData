from pathlib import Path

import plotly.graph_objects as go
import polars as pl
from loguru import logger

# YtD compara jan–set dos dois anos: 2026 só tem dados até 30/09
ULTIMO_MES = 9
MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set")
COR_2025 = "#9AA0A6"
COR_2026 = "#2563A6"
COR_SUBTITULO = "#202124"
COR_DESTAQUE = "#188038"


def formatar_milhoes(valor: float) -> str:
    return f"R$ {valor / 1e6:.2f}M".replace(".", ",")


def receita_ytd(negocios: pl.DataFrame) -> pl.DataFrame:
    return (
        negocios.filter(pl.col("status") == "Ganho")
        .with_columns(
            ano=pl.col("data_fechamento").dt.year(),
            mes=pl.col("data_fechamento").dt.month(),
        )
        .filter(pl.col("ano").is_in([2025, 2026]), pl.col("mes") <= ULTIMO_MES)
        .group_by("ano", "mes")
        .agg(receita=pl.col("valor_fechado").sum())
        .sort("ano", "mes")
        .with_columns(receita_acumulada=pl.col("receita").cum_sum().over("ano"))
    )


def grafico_receita_ytd(receita: pl.DataFrame, caminho: Path) -> None:
    receita_2025 = receita.filter(pl.col("ano") == 2025)
    receita_2026 = receita.filter(pl.col("ano") == 2026)
    total_2025 = receita_2025["receita_acumulada"][-1]
    total_2026 = receita_2026["receita_acumulada"][-1]
    diferenca = total_2026 - total_2025

    figura = go.Figure()
    for ano, dados, cor in (
        (2025, receita_2025, COR_2025),
        (2026, receita_2026, COR_2026),
    ):
        figura.add_scatter(
            x=[MESES[mes - 1] for mes in dados["mes"]],
            y=dados["receita"] / 1e6,
            name=str(ano),
            mode="lines+markers",
            line={"color": cor, "width": 3},
            customdata=dados["receita_acumulada"] / 1e6,
            hovertemplate=f"<b>{ano} · %{{x}}</b><br>No mês: R$ %{{y:.2f}}M"
            "<br>Acumulado: R$ %{customdata:.2f}M<extra></extra>",
        )

    mensal_2025 = receita_2025["receita"][-1]
    mensal_2026 = receita_2026["receita"][-1]
    titulo = (
        f"Receita YTD: <span style='color:{COR_2026}'>2026</span> x "
        f"<span style='color:{COR_2025}'>2025</span>"
    )
    subtitulo = (
        "O acumulado "
        f"<span style='font-size:16px;color:{COR_DESTAQUE}'>"
        f"supera em {diferenca / total_2025:.0%}</span> o de 2025 "
        f"(+{formatar_milhoes(diferenca)}), "
        f"{'mesmo com' if mensal_2026 < mensal_2025 else 'com'} "
        f"setembro {'abaixo' if mensal_2026 < mensal_2025 else 'acima'} "
        "do ano passado."
    )

    figura.update_layout(
        title={
            "text": f"<b>{titulo}</b><br><b><span style='font-size:14px;"
            f"color:{COR_SUBTITULO}'>{subtitulo}</span></b>",
            "font": {"size": 24, "color": "#000000"},
            "xref": "paper",
            "x": 0,
            "xanchor": "left",
            "y": 0.96,
            "yanchor": "top",
        },
        showlegend=False,
        separators=",.",
        template="plotly_white",
        width=1100,
        height=600,
        margin={"t": 100, "l": 80, "r": 40, "b": 40},
    )
    figura.update_yaxes(
        title_text="Receita mensal",
        tickprefix="R$ ",
        ticksuffix="M",
        tickformat=".1f",
        rangemode="tozero",
    )
    caminho.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;min-height:100vh;display:flex;"
        "justify-content:center;align-items:center'>"
        f"{figura.to_html(full_html=False)}</body></html>",
        encoding="utf-8",
    )


def gerar_graficos() -> None:
    pasta_base = Path(__file__).resolve().parent
    caminho_dados = pasta_base / "dados" / "negocios.csv"
    if not caminho_dados.is_file():
        raise FileNotFoundError(
            f"Base ausente: {caminho_dados}. Execute gerar_dados.py."
        )

    negocios = pl.read_csv(caminho_dados, try_parse_dates=True)
    pasta_graficos = pasta_base / "graficos"
    pasta_graficos.mkdir(exist_ok=True)

    grafico_receita_ytd(receita_ytd(negocios), pasta_graficos / "receita_ytd.html")
    logger.info("Gráficos criados em {}", pasta_graficos)


if __name__ == "__main__":
    gerar_graficos()
