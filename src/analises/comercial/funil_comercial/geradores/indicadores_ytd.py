from pathlib import Path

import polars as pl
from geradores.common import (
    COR_2025,
    COR_2026,
    COR_SUBTITULO,
    MESES,
    ULTIMO_MES,
    destacar,
    salvar_html,
)
from plotly.subplots import make_subplots


def indicadores_ytd(negocios: pl.DataFrame) -> pl.DataFrame:
    periodo = (pl.col("ano").is_in([2025, 2026]), pl.col("mes") <= ULTIMO_MES)
    criados = (
        negocios.with_columns(
            ano=pl.col("data_criacao").dt.year(),
            mes=pl.col("data_criacao").dt.month(),
            # Fechado até 30/09 do próprio ano
            fechado=pl.col("data_fechamento")
            <= pl.date(pl.col("data_criacao").dt.year(), 9, 30),
        )
        .filter(*periodo)
        .group_by("ano", "mes")
        .agg(
            criados=pl.len(),
            fechados=pl.col("fechado").sum(),
            ganhos_criados=((pl.col("status") == "Ganho") & pl.col("fechado")).sum(),
        )
    )
    ganhos = (
        negocios.filter(pl.col("status") == "Ganho")
        .with_columns(
            ano=pl.col("data_fechamento").dt.year(),
            mes=pl.col("data_fechamento").dt.month(),
        )
        .filter(*periodo)
        .group_by("ano", "mes")
        .agg(ganhos=pl.len(), receita=pl.col("valor_fechado").sum())
    )
    return (
        criados.join(ganhos, on=["ano", "mes"], how="left")
        .sort("ano", "mes")
        .with_columns(
            pl.col("criados", "fechados", "ganhos_criados", "ganhos", "receita")
            .cum_sum()
            .over("ano")
        )
        .with_columns(
            conversao=pl.col("ganhos_criados") / pl.col("fechados"),
            ticket_mil=pl.col("receita") / pl.col("ganhos") / 1e3,
        )
    )


def grafico_indicadores_ytd(indicadores: pl.DataFrame, caminho: Path) -> None:
    # Conversão e ticket sem eixo a partir de zero: a diferença entre os anos sumiria
    paineis = (
        (
            "criados",
            "volume",
            "Negócios criados",
            {"tickformat": ",d", "rangemode": "tozero"},
            "%{y:,d}",
        ),
        ("conversao", "conversão", "Conversão", {"tickformat": ".0%"}, "%{y:.1%}"),
        (
            "ticket_mil",
            "ticket",
            "Ticket médio",
            {"tickprefix": "R$ ", "ticksuffix": " mil", "tickformat": ".0f"},
            "R$ %{y:.1f} mil",
        ),
    )
    final_2025, final_2026 = (
        indicadores.filter(pl.col("mes") == ULTIMO_MES).sort("ano").rows(named=True)
    )
    # Variações relativas de cada métrica e da receita
    var_receita = final_2026["receita"] / final_2025["receita"] - 1
    variacoes = {
        nome: final_2026[coluna] / final_2025[coluna] - 1
        for coluna, nome, *_ in paineis
    }

    figura = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=[f"<b>{titulo}</b>" for _, _, titulo, *_ in paineis],
    )
    # Títulos dos painéis afastados do topo do eixo Y
    figura.update_annotations(x=0, xanchor="left", yshift=12, font_color=COR_SUBTITULO)
    for linha, (coluna, nome, titulo, eixo, hover) in enumerate(paineis, start=1):
        for ano, cor in ((2025, COR_2025), (2026, COR_2026)):
            dados = indicadores.filter(pl.col("ano") == ano)
            meses = [MESES[mes - 1] for mes in dados["mes"]]
            figura.add_scatter(
                x=meses,
                y=dados[coluna],
                name=str(ano),
                mode="lines+markers",
                line={"color": cor, "width": 3},
                hovertemplate=f"<b>{ano} · %{{x}}</b><br>{titulo} no acumulado: "
                f"{hover}<extra></extra>",
                row=linha,
                col=1,
            )
            # Rótulo do ano no fim da linha, no lugar da legenda
            figura.add_annotation(
                x=meses[-1],
                y=dados[coluna][-1],
                text=f"<b>{ano}</b>",
                font={"color": cor},
                showarrow=False,
                xanchor="left",
                xshift=10,
                row=linha,
                col=1,
            )
        # Variação em setembro: linha pontilhada entre os pontos de 2025 e 2026,
        # com pontos intermediários para o hover funcionar ao longo de toda a linha
        inicio, fim = final_2025[coluna], final_2026[coluna]
        figura.add_scatter(
            x=[MESES[-1]] * 11,
            y=[inicio + (fim - inicio) * passo / 10 for passo in range(11)],
            mode="lines",
            line={"color": COR_SUBTITULO, "width": 1, "dash": "dot"},
            hovertemplate=f"<b>{titulo}, 2026 x 2025: "
            f"{destacar(f'{variacoes[nome]:+.0%}', variacoes[nome])}</b>"
            "<extra></extra>",
            row=linha,
            col=1,
        )
        figura.update_yaxes(eixo, row=linha, col=1)

    alta = var_receita >= 0
    # Métricas que puxam a receita no sentido da variação x as que compensam
    puxam = [nome for nome, valor in variacoes.items() if (valor >= 0) == alta]
    compensam = [nome for nome, valor in variacoes.items() if (valor >= 0) != alta]
    titulo = (
        f"Receita YTD {var_receita:+.0%}: {'alta' if alta else 'queda'} de "
        f"{' e '.join(puxam)}"
    )
    if compensam:
        titulo += (
            f" supera {'a queda' if alta else 'o ganho'} de {' e '.join(compensam)}"
        )
    # O que as variações significam, sem fórmula
    volume, conversao, ticket = variacoes.values()
    subtitulo = (
        f"Geramos {destacar('mais' if volume >= 0 else 'menos', volume)} "
        f"oportunidades, mas convertemos "
        f"{destacar('mais' if conversao >= 0 else 'menos', conversao)} e cada venda "
        f"vale {destacar('mais' if ticket >= 0 else 'menos', ticket)}."
    )
    if volume >= 0 and not alta:
        subtitulo += " O problema não é demanda, é venda."

    figura.update_layout(
        title={
            "text": f"<b>{titulo}</b><br><b><span style='font-size:14px;"
            f"color:{COR_SUBTITULO}'>{subtitulo}</span></b>",
            "font": {"size": 24, "color": "#000000"},
            "xref": "paper",
            "x": 0,
            "xanchor": "left",
            "y": 0.97,
            "yanchor": "top",
        },
        showlegend=False,
        separators=",.",
        template="plotly_white",
        width=1100,
        height=850,
        margin={"t": 120, "l": 80, "r": 70, "b": 40},
    )
    salvar_html(figura, caminho)
