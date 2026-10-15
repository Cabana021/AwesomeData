from pathlib import Path

import plotly.graph_objects as go
import polars as pl
from geradores.common import (
    COR_2025,
    COR_2026,
    COR_QUEDA,
    COR_SUBTITULO,
    ULTIMO_MES,
    formatar_pp,
    salvar_html,
)


def perdas_apos_lead(negocios: pl.DataFrame) -> pl.DataFrame:
    return (
        negocios.filter(pl.col("status") == "Perdido", pl.col("etapa_atual") != "Lead")
        .with_columns(
            ano=pl.col("data_criacao").dt.year(),
            mes=pl.col("data_criacao").dt.month(),
        )
        .filter(
            pl.col("ano").is_in([2025, 2026]),
            pl.col("mes") <= ULTIMO_MES,
            pl.col("data_fechamento") <= pl.date(pl.col("ano"), 9, 30),
        )
    )


def motivos_perda(perdas: pl.DataFrame) -> pl.DataFrame:
    return (
        perdas.group_by("motivo_perda", "ano")
        .agg(perdas=pl.len())
        # Arredondada como no rótulo (uma casa em %), para a variação em p.p. fechar
        .with_columns(
            participacao=(pl.col("perdas") / pl.col("perdas").sum().over("ano")).round(
                3
            )
        )
        .pivot("ano", index="motivo_perda", values=["perdas", "participacao"])
        .with_columns(var=pl.col("participacao_2026") - pl.col("participacao_2025"))
        # Maior participação em 2026 no topo do eixo Y
        .sort("participacao_2026")
    )


def grafico_motivos_perda(motivos: pl.DataFrame, caminho: Path) -> None:
    linhas = motivos.rows(named=True)
    alta = max(linhas, key=lambda m: m["var"])
    # Só o motivo que mais cresceu ganha destaque
    categorias = [
        f"<b><span style='color:{COR_QUEDA}'>{m['motivo_perda']}</span></b>"
        if m is alta
        else m["motivo_perda"]
        for m in linhas
    ]

    figura = go.Figure()
    # Em barras horizontais agrupadas, o primeiro trace fica embaixo: 2025 em cima
    for ano, cor in ((2026, COR_2026), (2025, COR_2025)):
        figura.add_bar(
            x=motivos[f"participacao_{ano}"],
            y=categorias,
            orientation="h",
            name=str(ano),
            marker_color=cor,
            texttemplate="%{x:.1%}",
            textposition="outside",
            textfont={"color": COR_SUBTITULO},
            cliponaxis=False,
            customdata=motivos["motivo_perda"],
            hovertemplate=f"<b>{ano} · %{{customdata}}</b><br>Participação nas perdas: "
            "%{x:.1%}<extra></extra>",
        )

    teto = max(max(m["participacao_2025"], m["participacao_2026"]) for m in linhas)
    # Variação em coluna à direita das barras, como nos halteres
    figura.add_scatter(
        x=[teto * 1.12] * len(linhas),
        y=categorias,
        mode="text",
        text=[
            f"<b>{formatar_pp(m['var'])}</b>" if m is alta else formatar_pp(m["var"])
            for m in linhas
        ],
        textposition="middle right",
        textfont={
            "size": 13,
            "color": [COR_QUEDA if m is alta else COR_SUBTITULO for m in linhas],
        },
        cliponaxis=False,
        hoverinfo="skip",
        showlegend=False,
    )

    participacao = f"{alta['participacao_2026']:.1%}".replace(".", ",")
    figura.update_layout(
        title={
            "text": f"<b>{alta['motivo_perda']} já explica {participacao} das vendas "
            "perdidas. Estamos desperdiçando volume.</b>",
            "font": {"size": 22, "color": "#000000"},
            "xref": "paper",
            "x": 0,
            "xanchor": "left",
            "y": 0.96,
            "yanchor": "top",
        },
        barmode="group",
        legend={
            "orientation": "h",
            "x": 0,
            "xanchor": "left",
            "y": 1.02,
            "yanchor": "bottom",
            "traceorder": "reversed",
        },
        separators=",.",
        template="plotly_white",
        width=1100,
        height=540,
        margin={"t": 90, "l": 130, "r": 40, "b": 40},
    )
    figura.update_xaxes(visible=False, range=[0, teto * 1.25])
    figura.update_yaxes(
        tickfont={"size": 13, "color": COR_SUBTITULO}, ticklabelstandoff=8
    )
    salvar_html(figura, caminho)
