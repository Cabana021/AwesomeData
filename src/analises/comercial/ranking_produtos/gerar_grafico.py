from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import matplotlib.pyplot as plt
import polars as pl
from loguru import logger
from matplotlib.ticker import FuncFormatter


def formatar_reais(valor: float) -> str:
    return f"R$ {valor:,.0f}".replace(",", ".")


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
        .agg(pl.col("quantidade_vendida").sum())
        .sort("quantidade_vendida", descending=True)
    )
    nomes = produtos["produto"].to_list()
    quantidades = produtos["quantidade_vendida"].to_list()

    figura, eixo = plt.subplots(figsize=(9, 5))
    barras = eixo.barh(nomes, quantidades, color="#2A9D8F")
    eixo.invert_yaxis()
    eixo.bar_label(barras, padding=4)
    eixo.set_xlim(0, max(quantidades) * 1.15)
    eixo.set(title="Produtos mais vendidos", xlabel="Unidades vendidas")
    eixo.grid(axis="x", alpha=0.25)
    eixo.set_axisbelow(True)
    eixo.spines["top"].set_visible(False)
    eixo.spines["right"].set_visible(False)

    figura.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(figura)


def grafico_faturamento_meta_vendedores(
    vendedores: pl.DataFrame, caminho: Path, periodo: str
) -> None:
    vendedores = vendedores.sort("atingimento_meta")
    posicoes = list(range(vendedores.height))
    metas = vendedores["meta_faturamento_liquido"].to_list()
    faturamentos = vendedores["faturamento_liquido"].to_list()

    figura, eixo = plt.subplots(figsize=(10, 4))
    barras_meta = eixo.barh(
        [posicao - 0.2 for posicao in posicoes],
        metas,
        height=0.38,
        label="Meta",
        color="#E9A23B",
    )
    barras_faturamento = eixo.barh(
        [posicao + 0.2 for posicao in posicoes],
        faturamentos,
        height=0.38,
        label="Faturamento líquido",
        color="#2563A6",
    )
    eixo.bar_label(
        barras_meta, labels=[formatar_reais(valor) for valor in metas], padding=3
    )
    eixo.bar_label(
        barras_faturamento,
        labels=[formatar_reais(valor) for valor in faturamentos],
        padding=3,
    )
    eixo.set_yticks(posicoes, vendedores["vendedor"].to_list())
    eixo.invert_yaxis()
    eixo.set_xlim(0, max(metas + faturamentos) * 1.25)
    eixo.set(title="Faturamento x meta por vendedor", xlabel="Valores em R$")
    eixo.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    eixo.grid(axis="x", alpha=0.25)
    eixo.set_axisbelow(True)
    eixo.spines["top"].set_visible(False)
    eixo.spines["right"].set_visible(False)
    eixo.xaxis.set_major_formatter(
        FuncFormatter(lambda valor, _: f"{valor:,.0f}".replace(",", "."))
    )
    figura.subplots_adjust(right=0.78)

    figura.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(figura)


def grafico_faturamento_meta_produtos(produtos: pl.DataFrame, caminho: Path) -> None:
    produtos = produtos.sort("atingimento_meta", descending=True)
    percentuais = [valor * 100 for valor in produtos["atingimento_meta"].to_list()]
    rotulos = [f"{percentual:.1f}%" for percentual in percentuais]
    cores = [
        "#2A9D8F" if percentual >= 100 else "#D66A5E" for percentual in percentuais
    ]

    figura, eixo = plt.subplots(figsize=(9, 5))
    barras = eixo.barh(produtos["produto"].to_list(), percentuais, color=cores)
    eixo.invert_yaxis()
    eixo.axvline(100, color="#555555", linestyle="--", alpha=0.5, label="Meta: 100%")
    eixo.bar_label(barras, labels=rotulos, padding=5)
    eixo.set_xlim(0, max(165, max(percentuais) * 1.45))
    eixo.set(title="Faturamento x meta por produto", xlabel="Meta atingida (%)")
    eixo.spines["top"].set_visible(False)
    eixo.spines["right"].set_visible(False)
    eixo.legend(loc="upper right")
    eixo.grid(axis="x", alpha=0.25)
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
