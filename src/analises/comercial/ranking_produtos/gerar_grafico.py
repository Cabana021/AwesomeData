from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import matplotlib.pyplot as plt
import polars as pl
from loguru import logger
from matplotlib.ticker import FuncFormatter, MultipleLocator


def formatar_reais(valor: float) -> str:
    return f"R$ {valor:,.0f}".replace(",", ".")


def formatar_percentual(valor: float) -> str:
    return f"{valor:.1%}".replace(".", ",")


def grafico_volume_vendas(vendas: pl.DataFrame, caminho: Path, periodo: str) -> None:
    volume = (
        vendas.group_by("data_venda")
        .agg(pl.col("quantidade_vendida").sum())
        .sort("data_venda")
    )
    datas = [data.strftime("%d/%m") for data in volume["data_venda"].to_list()]
    quantidades = volume["quantidade_vendida"].to_list()

    figura, eixo = plt.subplots(figsize=(9, 4))
    eixo.plot(datas, quantidades, color="#2563A6", marker="o", linewidth=2)
    eixo.set(title="Volume diário de vendas", ylabel="Vendas realizadas")
    eixo.margins(y=0.2)
    eixo.spines["top"].set_visible(False)
    eixo.spines["right"].set_visible(False)

    # Gambiarra manual para organizar o posicionamento dos valores
    deslocamentos = {
        "21/09": (0, -14),
        "22/09": (0, 14),
        "23/09": (12, 8),
        "24/09": (0, -14),
    }
    for data, quantidade in zip(datas, quantidades, strict=True):
        eixo.annotate(
            str(quantidade),
            (data, quantidade),
            xytext=deslocamentos.get(data, (0, 8)),
            textcoords="offset points",
            ha="center",
        )

    figura.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(figura)


def grafico_produtos_mais_vendidos(
    vendas: pl.DataFrame, caminho: Path, periodo: str
) -> None:
    produtos = (
        vendas.group_by("produto")
        .agg(pl.col("quantidade_vendida", "faturamento_liquido").sum())
        .with_columns(
            milesimos=pl.col("faturamento_liquido")
            / pl.col("faturamento_liquido").sum()
            * 1000
        )
        .with_columns(
            truncado=pl.col("milesimos").floor(),
            resto=pl.col("milesimos") - pl.col("milesimos").floor(),
        )
        .with_columns(
            participacao=(
                pl.col("truncado")
                + (
                    pl.col("resto").rank("ordinal", descending=True)
                    <= 1000 - pl.col("truncado").sum()
                ).cast(pl.Int64)
            )
            / 1000
        )
        .sort("quantidade_vendida", descending=True)
    )
    # Destaca os dois produtos que mais pesam no faturamento
    destaques = produtos.sort("faturamento_liquido", descending=True)["produto"][:2]
    nomes = produtos["produto"].to_list()
    cores = ["#2A9D8F" if nome in destaques else "#B8B8B8" for nome in nomes]
    quantidades = produtos["quantidade_vendida"].to_list()
    faturamentos = produtos["faturamento_liquido"].to_list()
    rotulos_faturamento = [
        f"{formatar_reais(faturamento)} ({formatar_percentual(participacao)})"
        for faturamento, participacao in zip(
            faturamentos, produtos["participacao"], strict=True
        )
    ]

    figura, (eixo_unidades, eixo_faturamento) = plt.subplots(
        1, 2, figsize=(11, 5), sharey=True
    )
    barras = eixo_unidades.barh(nomes, quantidades, color=cores)
    eixo_unidades.bar_label(barras, padding=4)
    eixo_unidades.set_xlim(0, max(quantidades) * 1.2)
    eixo_unidades.set_title("Unidades vendidas", color="#555555", fontweight="bold")
    barras = eixo_faturamento.barh(nomes, faturamentos, color=cores)
    eixo_faturamento.bar_label(barras, labels=rotulos_faturamento, padding=4)
    eixo_faturamento.set_xlim(0, max(faturamentos) * 1.6)
    eixo_faturamento.set_title(
        "Faturamento líquido", color="#555555", fontweight="bold"
    )
    eixo_unidades.invert_yaxis()
    for eixo in (eixo_unidades, eixo_faturamento):
        eixo.xaxis.set_visible(False)
        eixo.tick_params(length=0)
        for lado in ("top", "right", "bottom", "left"):
            eixo.spines[lado].set_visible(False)
    figura.suptitle(
        "Lápis lidera em unidades, mas mochila e garrafa fazem 71% do faturamento",
        fontweight="bold",
        y=1.04,
    )
    figura.text(0.5, 0.97, periodo, ha="center", color="#777777")

    figura.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(figura)


def grafico_faturamento_meta_vendedores(
    vendedores: pl.DataFrame, caminho: Path, periodo: str
) -> None:
    vendedores = vendedores.sort("atingimento_meta", descending=True)
    posicoes = list(range(vendedores.height))
    atingimentos = [atingimento * 100 for atingimento in vendedores["atingimento_meta"]]
    diferencas = vendedores["diferenca_meta"].to_list()
    cores = ["#2A9D8F" if diferenca >= 0 else "#B8B8B8" for diferenca in diferencas]

    figura, eixo = plt.subplots(figsize=(9, 4))
    eixo.barh(posicoes, atingimentos, color=cores)
    # Fundo branco no rótulo para não cruzar com a linha da meta
    for posicao, atingimento in zip(posicoes, atingimentos, strict=True):
        eixo.annotate(
            formatar_percentual(atingimento / 100),
            (atingimento, posicao),
            xytext=(6, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            color="#333333",
            fontweight="bold",
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1},
        )
    eixo.axvline(100, color="#999999", linewidth=1, linestyle="--")
    eixo.annotate(
        "Meta",
        (100, 1),
        xycoords=("data", "axes fraction"),
        xytext=(0, 4),
        textcoords="offset points",
        ha="center",
        va="bottom",
        color="#777777",
        fontweight="bold",
    )
    eixo.set_yticks(posicoes, vendedores["vendedor"].to_list())
    eixo.invert_yaxis()
    eixo.set_xlim(0, max(atingimentos) * 1.15)
    eixo.xaxis.set_major_locator(MultipleLocator(20))
    eixo.xaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:.0f}%"))
    eixo.tick_params(length=0)
    eixo.tick_params(axis="x", colors="#777777")
    eixo.grid(axis="x", alpha=0.25)
    eixo.set_axisbelow(True)
    eixo.set_title(
        "A equipe bateu a meta, mas só um vendedor bateu a meta",
        fontweight="bold",
        pad=24,
    )
    for lado in ("top", "right", "bottom", "left"):
        eixo.spines[lado].set_visible(False)

    figura.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(figura)


def grafico_faturamento_meta_produtos(produtos: pl.DataFrame, caminho: Path) -> None:
    produtos = produtos.sort("diferenca_meta")
    diferencas = produtos["diferenca_meta"].to_list()
    rotulos = [
        f"{'+' if diferenca >= 0 else '-'}{formatar_reais(abs(diferenca))}"
        for diferenca in diferencas
    ]
    cores = ["#2A9D8F" if diferenca >= 0 else "#D66A5E" for diferenca in diferencas]

    figura, eixo = plt.subplots(figsize=(9, 5))
    barras = eixo.barh(produtos["produto"].to_list(), diferencas, color=cores)
    eixo.invert_yaxis()
    eixo.axvline(0, color="#555555", linewidth=1)
    eixo.bar_label(barras, labels=rotulos, padding=4)
    limite = max(abs(diferenca) for diferenca in diferencas) * 1.4
    eixo.set_xlim(-limite, limite)
    eixo.set_title(
        "Mochila e garrafa concentram 94% da meta perdida", fontweight="bold"
    )
    eixo.set_xlabel("Diferença para a meta (R$)")
    eixo.spines["top"].set_visible(False)
    eixo.spines["right"].set_visible(False)
    eixo.xaxis.set_major_formatter(
        FuncFormatter(lambda valor, _: f"{valor:,.0f}".replace(",", "."))
    )
    eixo.grid(axis="x", alpha=0.12)
    eixo.set_axisbelow(True)

    figura.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(figura)


def gerar_graficos() -> None:
    pasta_base = Path(__file__).resolve().parent
    hoje = datetime.now(UTC).astimezone().date()
    caminho_resumo = pasta_base / "saidas" / f"resumo_gerencial-{hoje:%d-%m-%Y}.xlsx"
    if not caminho_resumo.is_file():
        raise FileNotFoundError(
            f"Resumo ausente: {caminho_resumo}. Execute criar_planilha.py."
        )

    abas = pl.read_excel(caminho_resumo, sheet_id=0)
    vendas = abas["Vendas"]
    inicio = cast(date, vendas["data_venda"].min())
    fim = cast(date, vendas["data_venda"].max())
    periodo = f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}"
    pasta_graficos = pasta_base / "graficos"
    pasta_graficos.mkdir(exist_ok=True)

    grafico_volume_vendas(vendas, pasta_graficos / "volume_vendas.png", periodo)
    grafico_produtos_mais_vendidos(
        vendas, pasta_graficos / "produtos_mais_vendidos.png", periodo
    )
    grafico_faturamento_meta_vendedores(
        abas["Vendedores"], pasta_graficos / "faturamento_meta_vendedores.png", periodo
    )
    grafico_faturamento_meta_produtos(
        abas["Produtos"], pasta_graficos / "faturamento_meta_produtos.png"
    )
    logger.info("Gráficos criados em {}", pasta_graficos)


if __name__ == "__main__":
    gerar_graficos()
