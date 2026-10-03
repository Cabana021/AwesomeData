from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
from loguru import logger
from xlsxwriter import Workbook


def comparar_metas(
    vendas: pl.DataFrame, metas: pl.DataFrame, codigo: str
) -> pl.DataFrame:
    faturamento = vendas.group_by(codigo).agg(
        pl.col("faturamento_liquido").sum().round(2)
    )
    return (
        metas.unique(subset=[codigo])
        .join(faturamento, on=codigo, how="left")
        .with_columns(pl.col("faturamento_liquido").fill_null(0))
        .with_columns(
            (pl.col("faturamento_liquido") - pl.col("meta_faturamento_liquido"))
            .round(2)
            .alias("diferenca_meta"),
            (pl.col("faturamento_liquido") / pl.col("meta_faturamento_liquido")).alias(
                "atingimento_meta"
            ),
        )
        .sort("faturamento_liquido", descending=True)
    )


def criar_planilha() -> Path:
    hoje = datetime.now(UTC).astimezone().date()
    periodo_inicio = hoje - timedelta(days=7)
    pasta_base = Path(__file__).resolve().parent
    pasta_dados = pasta_base / "dados"
    caminhos = [
        pasta_dados
        / f"consolidado_vendas-{periodo_inicio + timedelta(days=dia):%d-%m-%Y}.xlsx"
        for dia in range(7)
    ]
    faltantes = [caminho.name for caminho in caminhos if not caminho.is_file()]
    if faltantes:
        raise FileNotFoundError(f"Planilhas diárias ausentes: {', '.join(faltantes)}")

    vendas_diarias = []
    metas_vendedores = []
    metas_produtos = []
    for caminho in caminhos:
        abas = pl.read_excel(caminho, sheet_id=0)
        vendas_diarias.append(abas["Vendas"])
        metas_vendedores.append(abas["Vendedores"])
        metas_produtos.append(abas["Produtos"])

    vendas = pl.concat(vendas_diarias).sort("data_venda", descending=True)
    vendedores = comparar_metas(vendas, pl.concat(metas_vendedores), "codigo_vendedor")
    produtos = comparar_metas(
        vendas, pl.concat(metas_produtos), "codigo_produto"
    ).with_row_index("ranking", offset=1)

    pasta_saidas = pasta_base / "saidas"
    pasta_saidas.mkdir(exist_ok=True)
    caminho_saida = pasta_saidas / f"resumo_gerencial-{hoje:%d-%m-%Y}.xlsx"

    formato_reais = "R$ #,##0.00;[Red]-R$ #,##0.00"
    with Workbook(str(caminho_saida)) as workbook:
        formato_abaixo = workbook.add_format(
            {"bg_color": "#FFC7CE", "font_color": "#9C0006"}
        )
        formato_atingiu = workbook.add_format(
            {"bg_color": "#C6EFCE", "font_color": "#006100"}
        )
        vendas.write_excel(
            workbook=workbook,
            worksheet="Vendas",
            dtype_formats={pl.Date: "dd/mm/yyyy"},
            column_formats={
                coluna: formato_reais
                for coluna in (
                    "preco_unitario",
                    "faturamento_bruto",
                    "desconto_total",
                    "faturamento_liquido",
                )
            },
            autofit=True,
            freeze_panes=(1, 0),
        )
        for nome, dados in {"Vendedores": vendedores, "Produtos": produtos}.items():
            dados.write_excel(
                workbook=workbook,
                worksheet=nome,
                dtype_formats={pl.Date: "dd/mm/yyyy"},
                column_formats={
                    "faturamento_liquido": formato_reais,
                    "meta_faturamento_liquido": formato_reais,
                    "diferenca_meta": formato_reais,
                    "atingimento_meta": "0.0%",
                },
                conditional_formats={
                    "diferenca_meta": [
                        {
                            "type": "cell",
                            "criteria": "<",
                            "value": 0,
                            "format": formato_abaixo,
                        },
                        {
                            "type": "cell",
                            "criteria": ">=",
                            "value": 0,
                            "format": formato_atingiu,
                        },
                    ]
                },
                autofit=True,
                freeze_panes=(1, 0),
            )

    logger.info("Resumo gerencial criado: {}", caminho_saida)
    return caminho_saida


if __name__ == "__main__":
    criar_planilha()
