from collections.abc import Callable
from pathlib import Path

import polars as pl
from geradores.common import (
    COR_2025,
    COR_QUEDA,
    COR_SUBTITULO,
    COR_TOTAL,
    ULTIMO_MES,
    formatar_milhoes,
    formatar_pp,
    salvar_html,
)
from plotly.subplots import make_subplots


# Abaixo de R$ 1M em mil, para variações pequenas não virarem "R$ 0,03M"
def formatar_reais(valor: float) -> str:
    return formatar_milhoes(valor) if valor >= 1e6 else f"R$ {valor / 1e3:.0f} mil"


def formatar_variacao(valor: float) -> str:
    return f"{'+' if valor >= 0 else '-'}{formatar_reais(abs(valor))}"


def metricas_por_grupo(negocios: pl.DataFrame, coluna: str) -> pl.DataFrame:
    periodo = (pl.col("ano").is_in([2025, 2026]), pl.col("mes") <= ULTIMO_MES)
    corte = (
        negocios.with_columns(
            ano=pl.col("data_criacao").dt.year(),
            mes=pl.col("data_criacao").dt.month(),
        )
        .filter(*periodo)
        .group_by(coluna, "ano")
        .agg(
            criados=pl.len(),
            conversao=(pl.col("status") == "Ganho").sum()
            / (pl.col("status") != "Aberto").sum(),
        )
    )
    ganhos = (
        negocios.filter(pl.col("status") == "Ganho")
        .with_columns(
            ano=pl.col("data_fechamento").dt.year(),
            mes=pl.col("data_fechamento").dt.month(),
        )
        .filter(*periodo)
        .group_by(coluna, "ano")
        .agg(
            ticket=pl.col("valor_fechado").mean(),
            receita=pl.col("valor_fechado").sum(),
        )
    )
    return (
        corte.join(ganhos, on=[coluna, "ano"])
        .pivot(
            "ano", index=coluna, values=["criados", "conversao", "ticket", "receita"]
        )
        .rename({coluna: "grupo"})
        .with_columns(
            var_criados=pl.col("criados_2026") / pl.col("criados_2025") - 1,
            var_conversao=pl.col("conversao_2026") - pl.col("conversao_2025"),
            var_ticket=pl.col("ticket_2026") / pl.col("ticket_2025") - 1,
            var_receita=pl.col("receita_2026") - pl.col("receita_2025"),
        )
        # Maior perda de receita no topo do eixo Y
        .sort("var_receita")
    )


def grafico_metricas_grupo(metricas: pl.DataFrame, caminho: Path) -> None:
    # Por métrica: título, formato do valor e formato da variação
    fatores: dict[str, tuple[str, Callable[[float], str], Callable[[float], str]]] = {
        "criados": ("Volume", lambda v: f"{v:.0f} negócios", lambda v: f"{v:+.0%}"),
        "conversao": (
            "Conversão",
            lambda v: f"{v:.1%}".replace(".", ","),
            formatar_pp,
        ),
        "ticket": (
            "Ticket médio",
            lambda v: f"R$ {v / 1e3:.1f} mil".replace(".", ","),
            lambda v: f"{v:+.0%}",
        ),
        "receita": ("Receita", formatar_reais, formatar_variacao),
    }
    pior = metricas.row(0, named=True)
    fator_dor = min(
        list(fatores)[:-1],
        key=lambda fator: pior[f"{fator}_2026"] / pior[f"{fator}_2025"],
    )
    # Só o grupo da dor ganha destaque no eixo Y
    categorias = [
        f"<b><span style='color:{COR_QUEDA}'>{grupo}</span></b>"
        if grupo == pior["grupo"]
        else grupo
        for grupo in metricas["grupo"]
    ]

    figura = make_subplots(
        rows=1,
        cols=len(fatores),
        shared_yaxes=True,
        horizontal_spacing=0.06,
        subplot_titles=[f"<b>{titulo}</b>" for titulo, *_ in fatores.values()],
    )
    figura.update_annotations(yshift=8, font_color=COR_SUBTITULO)
    for coluna, (fator, (titulo, formatar, formatar_var)) in enumerate(
        fatores.items(), start=1
    ):
        variacoes = metricas[f"var_{fator}"]
        # A causa e a perda de receita do grupo da dor em vermelho
        cores = [
            COR_QUEDA
            if grupo == pior["grupo"] and fator in (fator_dor, "receita")
            else COR_TOTAL
            if fator == "receita"
            else COR_2025
            for grupo in metricas["grupo"]
        ]
        figura.add_bar(
            x=variacoes,
            y=categorias,
            orientation="h",
            width=0.6,
            marker_color=cores,
            text=[formatar_var(v) for v in variacoes],
            textposition="outside",
            textfont={"size": 12, "color": COR_SUBTITULO},
            cliponaxis=False,
            hovertext=[
                f"<b>{linha['grupo']} · {titulo}</b>"
                f"<br>2025: {formatar(linha[f'{fator}_2025'])}"
                f"<br>2026: {formatar(linha[f'{fator}_2026'])}"
                for linha in metricas.rows(named=True)
            ],
            hovertemplate="%{hovertext}<extra></extra>",
            row=1,
            col=coluna,
        )
        # Cada painel na própria escala, centrado no zero, com folga para os rótulos
        limite = max(abs(v) for v in variacoes)
        figura.update_xaxes(range=[-limite * 1.8, limite * 1.8], row=1, col=coluna)

    nome_dor, formatar_dor, formatar_var_dor = fatores[fator_dor]
    queda = formatar_var_dor(abs(pior[f"var_{fator_dor}"])).lstrip("+")
    titulo = (
        f"{pior['grupo']} perde {formatar_reais(abs(pior['var_receita']))} "
        f"com {nome_dor.lower()} {queda} menor<br>em comparação com o ano passado"
    )
    # Volume maior mostra que a perda não vem de demanda
    contraste = (
        f", mesmo com volume {pior['var_criados']:.0%} maior"
        if fator_dor != "criados" and pior["var_criados"] > 0
        else ""
    )
    subtitulo = (
        f"{nome_dor} caiu de {formatar_dor(pior[f'{fator_dor}_2025'])} para "
        f"{formatar_dor(pior[f'{fator_dor}_2026'])}{contraste}."
    )

    figura.update_layout(
        title={
            "text": f"<b>{titulo}</b><br><span style='font-size:14px;"
            f"color:{COR_SUBTITULO}'>{subtitulo}</span>",
            "font": {"size": 22, "color": "#000000"},
            # Alinhado à borda, não ao início dos painéis, por causa dos rótulos
            "xref": "container",
            "x": 0.02,
            "xanchor": "left",
            "y": 0.96,
            "yanchor": "top",
        },
        showlegend=False,
        separators=",.",
        template="plotly_white",
        width=1100,
        height=500,
        margin={"t": 140, "l": 160, "r": 40, "b": 30},
    )
    figura.update_xaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=True,
        zerolinecolor=COR_2025,
        zerolinewidth=1,
    )
    figura.update_yaxes(
        autorange="reversed",
        tickfont={"size": 13, "color": COR_SUBTITULO},
        ticklabelstandoff=8,
    )
    salvar_html(figura, caminho)
