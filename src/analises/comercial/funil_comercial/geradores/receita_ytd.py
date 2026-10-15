from pathlib import Path

import plotly.graph_objects as go
import polars as pl
from geradores.common import (
    COR_2025,
    COR_2026,
    COR_SUBTITULO,
    MESES,
    ULTIMO_MES,
    destacar,
    formatar_milhoes,
    salvar_html,
)


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
    alta = diferenca >= 0
    setembro_abaixo = mensal_2026 < mensal_2025
    variacao = f"{'supera em' if alta else 'fica'} {abs(diferenca) / total_2025:.0%}"
    subtitulo = (
        f"O acumulado {destacar(variacao, diferenca)} "
        f"{'o' if alta else 'abaixo do'} de 2025 "
        f"({'+' if alta else '-'}{formatar_milhoes(abs(diferenca))}), "
        f"{'mesmo com' if alta == setembro_abaixo else 'com'} "
        f"setembro {'abaixo' if setembro_abaixo else 'acima'} do ano passado."
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
    salvar_html(figura, caminho)
