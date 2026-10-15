from itertools import pairwise
from pathlib import Path

import plotly.graph_objects as go
import polars as pl
from geradores.common import (
    COR_2025,
    COR_2026,
    COR_QUEDA,
    COR_SUBTITULO,
    ETAPAS_FUNIL,
    ULTIMO_MES,
    destacar,
    formatar_pp,
    salvar_html,
)


def etapas_atingidas(negocios: pl.DataFrame) -> pl.DataFrame:
    # Corte de criação jan–set, só fechados: quantos negócios atingiram cada etapa
    return (
        negocios.filter(pl.col("status") != "Aberto")
        .with_columns(
            ano=pl.col("data_criacao").dt.year(),
            mes=pl.col("data_criacao").dt.month(),
        )
        .filter(pl.col("ano").is_in([2025, 2026]), pl.col("mes") <= ULTIMO_MES)
        .group_by("ano")
        .agg(
            Lead=pl.len(),
            Qualificado=pl.col("data_entrada_qualificado").count(),
            Proposta=pl.col("data_entrada_proposta").count(),
            Negociação=pl.col("data_entrada_negociacao").count(),
            Ganho=(pl.col("status") == "Ganho").sum(),
        )
        .sort("ano")
    )


def grafico_conversao_etapas(etapas: pl.DataFrame, caminho: Path) -> None:
    final_2025, final_2026 = etapas.rows(named=True)
    pares = list(pairwise(ETAPAS_FUNIL))
    passagens = [f"{origem} → {destino}" for origem, destino in pares]
    taxas = {
        ano: [final[destino] / final[origem] for origem, destino in pares]
        for ano, final in ((2025, final_2025), (2026, final_2026))
    }
    deltas = [t26 - t25 for t25, t26 in zip(taxas[2025], taxas[2026])]
    pior = deltas.index(min(deltas))
    # Variação em p.p. sob o nome da passagem, na mesma linha para todas;
    # só a pior passagem ganha destaque
    categorias = [
        f"{passagem}<br><b><span style='color:{COR_QUEDA}'>{formatar_pp(delta)}</span></b>"
        if posicao == pior
        else f"{passagem}<br>{formatar_pp(delta)}"
        for posicao, (passagem, delta) in enumerate(zip(passagens, deltas))
    ]

    figura = go.Figure()
    for ano, cor in ((2025, COR_2025), (2026, COR_2026)):
        figura.add_bar(
            x=categorias,
            y=taxas[ano],
            name=str(ano),
            marker_color=cor,
            texttemplate="%{y:.1%}",
            textposition="outside",
            cliponaxis=False,
            customdata=passagens,
            hovertemplate=f"<b>{ano} · %{{customdata}}</b><br>Conversão: %{{y:.1%}}"
            "<extra></extra>",
        )

    origem, destino = pares[pior]
    titulo = f"Perdemos mais negócios entre {origem} e {destino}"
    # Ganhos de 2026 se a passagem pior tivesse a taxa de 2025
    ganhos_perdidos = final_2026["Ganho"] * (taxas[2025][pior] / taxas[2026][pior] - 1)
    total_2025, total_2026 = (
        f"{final['Ganho'] / final['Lead']:.1%}".replace(".", ",")
        for final in (final_2025, final_2026)
    )
    subtitulo = (
        f"Conversão caiu de {total_2025} para {total_2026}. Com a taxa de 2025 nessa "
        f"etapa, seriam {destacar(f'{ganhos_perdidos:.0f} ganhos a mais', -1)}."
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
        barmode="group",
        # Legenda à esquerda, logo abaixo do subtítulo
        legend={
            "orientation": "h",
            "x": 0,
            "xanchor": "left",
            "y": 1.02,
            "yanchor": "bottom",
        },
        separators=",.",
        template="plotly_white",
        width=1100,
        height=560,
        margin={"t": 110, "l": 40, "r": 40, "b": 70},
    )
    figura.update_xaxes(tickfont={"size": 13, "color": COR_SUBTITULO})
    figura.update_yaxes(visible=False, range=[0, 1.05])
    salvar_html(figura, caminho)
