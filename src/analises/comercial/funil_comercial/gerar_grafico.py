from pathlib import Path

import plotly.graph_objects as go
import polars as pl
from loguru import logger
from plotly.subplots import make_subplots

# YtD compara jan–set dos dois anos: 2026 só tem dados até 30/09
ULTIMO_MES = 9
MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set")
COR_2025 = "#9AA0A6"
COR_2026 = "#2563A6"
COR_SUBTITULO = "#202124"
COR_DESTAQUE = "#188038"
COR_QUEDA = "#C5221F"


def formatar_milhoes(valor: float) -> str:
    return f"R$ {valor / 1e6:.2f}M".replace(".", ",")


def destacar(texto: str, valor: float) -> str:
    cor = COR_DESTAQUE if valor >= 0 else COR_QUEDA
    return f"<span style='font-size:16px;color:{cor}'>{texto}</span>"


def salvar_html(figura: go.Figure, caminho: Path) -> None:
    caminho.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;min-height:100vh;display:flex;"
        "justify-content:center;align-items:center'>"
        f"{figura.to_html(full_html=False)}</body></html>",
        encoding="utf-8",
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


def indicadores_ytd(negocios: pl.DataFrame) -> pl.DataFrame:
    # Criados por data de criação; ganhos e receita por data de fechamento
    periodo = (pl.col("ano").is_in([2025, 2026]), pl.col("mes") <= ULTIMO_MES)
    criados = (
        negocios.with_columns(
            ano=pl.col("data_criacao").dt.year(),
            mes=pl.col("data_criacao").dt.month(),
        )
        .filter(*periodo)
        .group_by("ano", "mes")
        .agg(criados=pl.len())
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
        .with_columns(pl.col("criados", "ganhos", "receita").cum_sum().over("ano"))
        .with_columns(
            conversao=pl.col("ganhos") / pl.col("criados"),
            ticket_mil=pl.col("receita") / pl.col("ganhos") / 1e3,
        )
    )


def grafico_indicadores_ytd(indicadores: pl.DataFrame, caminho: Path) -> None:
    paineis = (
        ("criados", "Negócios criados", {"tickformat": ",d"}, "%{y:,d}"),
        ("conversao", "Conversão", {"tickformat": ".0%"}, "%{y:.1%}"),
        (
            "ticket_mil",
            "Ticket médio",
            {"tickprefix": "R$ ", "ticksuffix": " mil", "tickformat": ".0f"},
            "R$ %{y:.1f} mil",
        ),
    )
    figura = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=[f"{titulo} no acumulado do ano" for _, titulo, _, _ in paineis],
    )
    figura.update_annotations(x=0, xanchor="left")
    for linha, (coluna, titulo, eixo, formato) in enumerate(paineis, start=1):
        for ano, cor in ((2025, COR_2025), (2026, COR_2026)):
            dados = indicadores.filter(pl.col("ano") == ano)
            figura.add_scatter(
                x=[MESES[mes - 1] for mes in dados["mes"]],
                y=dados[coluna],
                name=str(ano),
                mode="lines+markers",
                line={"color": cor, "width": 3},
                hovertemplate=f"<b>{ano} · %{{x}}</b><br>{titulo} no acumulado: "
                f"{formato}<extra></extra>",
                row=linha,
                col=1,
            )
        figura.update_yaxes(eixo, rangemode="tozero", row=linha, col=1)

    final = indicadores.filter(pl.col("mes") == ULTIMO_MES)
    final_2025 = final.filter(pl.col("ano") == 2025).row(0, named=True)
    final_2026 = final.filter(pl.col("ano") == 2026).row(0, named=True)
    # Variações relativas: receita = volume x conversão x ticket médio
    var_receita = final_2026["receita"] / final_2025["receita"] - 1
    variacoes = {
        "o volume": final_2026["criados"] / final_2025["criados"] - 1,
        "a conversão": final_2026["conversao"] / final_2025["conversao"] - 1,
        "o ticket médio": final_2026["ticket_mil"] / final_2025["ticket_mil"] - 1,
    }
    alta = var_receita >= 0
    # a métrica que mais puxa a receita no sentido da variação
    principal = (max if alta else min)(variacoes, key=lambda nome: variacoes[nome])
    volume, conversao, ticket = (
        destacar(f"{valor:+.0%}", valor) for valor in variacoes.values()
    )

    titulo = (
        f"Receita YTD {var_receita:+.0%}: {principal} explica "
        f"{'o crescimento' if alta else 'a queda'}"
    )
    subtitulo = (
        f"Receita = volume ({volume}) × conversão ({conversao}) × "
        f"ticket médio ({ticket}), <span style='color:{COR_2026}'>2026</span> x "
        f"<span style='color:{COR_2025}'>2025</span> até setembro."
    )

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
        margin={"t": 120, "l": 80, "r": 40, "b": 40},
    )
    salvar_html(figura, caminho)


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
    grafico_indicadores_ytd(
        indicadores_ytd(negocios), pasta_graficos / "indicadores_ytd.html"
    )
    logger.info("Gráficos criados em {}", pasta_graficos)


if __name__ == "__main__":
    gerar_graficos()
