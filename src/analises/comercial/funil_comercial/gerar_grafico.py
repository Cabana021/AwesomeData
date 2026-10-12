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
    return f"<span style='color:{cor}'>{texto}</span>"


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
    # Variações relativas: receita = volume x conversão x ticket médio
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
        f"{destacar('mais' if conversao >= 0 else 'menos', conversao)} e vendemos "
        f"{destacar('mais caro' if ticket >= 0 else 'mais barato', ticket)}."
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
