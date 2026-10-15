from itertools import accumulate
from pathlib import Path

import plotly.graph_objects as go
import polars as pl
from geradores.common import (
    COR_2025,
    COR_2026,
    COR_SUBTITULO,
    ETAPAS_FUNIL,
    destacar,
    formatar_milhoes,
    salvar_html,
)


def forecast_q4(negocios: pl.DataFrame, etapas: pl.DataFrame) -> pl.DataFrame:
    # Taxa de ganho da etapa: ganhos ÷ fechados de 2026 que atingiram a etapa
    final_2026 = etapas.filter(pl.col("ano") == 2026).row(0, named=True)
    taxas = pl.DataFrame(
        {
            "etapa_atual": ETAPAS_FUNIL[:-1],
            "taxa": [final_2026["Ganho"] / final_2026[e] for e in ETAPAS_FUNIL[:-1]],
        }
    )
    # Desconto médio dos ganhos de 2026, para o aberto ficar na base do valor fechado
    ganhos_2026 = negocios.filter(
        pl.col("status") == "Ganho", pl.col("data_criacao").dt.year() == 2026
    )
    fator = ganhos_2026.select(
        pl.col("valor_fechado").sum() / pl.col("valor_estimado").sum()
    ).item()
    return (
        negocios.filter(pl.col("status") == "Aberto")
        .group_by("etapa_atual")
        .agg(bruto=pl.col("valor_estimado").sum() * fator)
        .join(taxas, on="etapa_atual")
        # Arredondado a R$ 10 mil, como nos rótulos, para a soma das etapas
        # bater com o total exibido
        .with_columns(ponderado=(pl.col("bruto") * pl.col("taxa") / 1e4).round() * 1e4)
        # Da etapa mais perto do fechamento para a mais distante
        .sort("taxa", descending=True)
    )


def receita_q4_2025(negocios: pl.DataFrame) -> float:
    # Só negócios já abertos em 30/09/2025, para comparar com os abertos de 2026
    return float(
        negocios.filter(
            pl.col("status") == "Ganho",
            pl.col("data_criacao") < pl.date(2025, 10, 1),
            pl.col("data_fechamento").dt.year() == 2025,
            pl.col("data_fechamento").dt.quarter() == 4,
        )["valor_fechado"].sum()
    )


def grafico_forecast_q4(
    forecast: pl.DataFrame, receita_q4: float, caminho: Path
) -> None:
    ponderados = forecast["ponderado"].to_list()
    total = sum(ponderados)
    # Cada etapa começa onde a anterior terminou; as duas barras finais partem do zero
    inicios = [*accumulate(ponderados[:-1], initial=0), 0, 0]
    alturas = [*ponderados, total, receita_q4]
    etapas = forecast.rows(named=True)
    categorias = [
        f"{e['etapa_atual']}<br>{formatar_milhoes(e['bruto'])} × {e['taxa']:.0%}"
        for e in etapas
    ] + ["Previsão<br>Q4 2026", "Realizado<br>Q4 2025"]

    figura = go.Figure(
        go.Bar(
            x=categorias,
            y=[a / 1e6 for a in alturas],
            base=[i / 1e6 for i in inicios],
            width=0.5,
            marker={
                "color": [COR_2026] * (len(etapas) + 1) + [COR_2025],
                "opacity": [0.55] * len(etapas) + [1, 1],
            },
            text=[f"+{formatar_milhoes(p)}" for p in ponderados]
            + [formatar_milhoes(total), formatar_milhoes(receita_q4)],
            textposition=["outside"] * len(etapas) + ["inside", "inside"],
            insidetextanchor="end",
            textfont={
                "size": 14,
                "color": [COR_SUBTITULO] * len(etapas) + ["#FFFFFF", "#FFFFFF"],
            },
            cliponaxis=False,
            hovertext=[
                f"<b>{e['etapa_atual']}</b><br>Em aberto, com desconto médio: "
                f"{formatar_milhoes(e['bruto'])}"
                f"<br>Taxa de conversão em venda: {e['taxa']:.0%}"
                f"<br>Esperado: {formatar_milhoes(e['ponderado'])}"
                for e in etapas
            ]
            + [
                f"<b>Previsão Q4 2026</b><br>{formatar_milhoes(total)}",
                f"<b>Realizado Q4 2025</b><br>{formatar_milhoes(receita_q4)}",
            ],
            hovertemplate="%{hovertext}<extra></extra>",
        )
    )
    # Conectores pontilhados entre o fim de uma etapa e o início da seguinte
    for posicao, nivel in enumerate(accumulate(ponderados)):
        figura.add_shape(
            type="line",
            x0=posicao + 0.25,
            x1=posicao + 0.75,
            y0=nivel / 1e6,
            y1=nivel / 1e6,
            line={"color": COR_2025, "dash": "dot", "width": 1},
        )

    titulo = f"Negócios em aberto têm potencial de {formatar_milhoes(total)} no Q4"
    variacao = total / receita_q4 - 1
    comparacao = f"{abs(variacao):.0%} {'acima' if variacao >= 0 else 'abaixo'}"
    # Quanto da previsão vem das duas etapas mais perto de converter
    seguras = etapas[:2]
    parcela = sum(e["ponderado"] for e in seguras) / total
    subtitulo = (
        f"{destacar(comparacao, variacao)} do que os negócios em aberto renderam "
        f"no Q4 de 2025. Só {parcela:.0%} vem de "
        f"{' e '.join(e['etapa_atual'] for e in seguras)}."
    )

    figura.update_layout(
        title={
            "text": f"<b>{titulo}</b><br><span style='font-size:14px;"
            f"color:{COR_SUBTITULO}'>{subtitulo}</span>",
            "font": {"size": 22, "color": "#000000"},
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
        height=540,
        margin={"t": 75, "l": 40, "r": 40, "b": 70},
    )
    figura.update_xaxes(
        tickfont={"size": 13, "color": COR_SUBTITULO},
        showline=True,
        linecolor=COR_2025,
        linewidth=1,
    )
    figura.update_yaxes(visible=False, range=[0, max(total, receita_q4) * 1.12 / 1e6])
    salvar_html(figura, caminho)
