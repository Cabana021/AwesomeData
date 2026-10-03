from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
from faker import Faker
from loguru import logger
from xlsxwriter import Workbook

# catálogo de produtos
PRODUTOS = (
    ("P001", "Caneta Bic", "Escrita", 350),
    ("P002", "Lápis", "Escrita", 250),
    ("P003", "Borracha", "Escrita", 200),
    ("P004", "Marca-texto", "Escrita", 650),
    ("P005", "Caderno", "Papelaria", 2490),
    ("P006", "Estojo escolar", "Acessórios", 1890),
    ("P007", "Garrafa térmica", "Acessórios", 5990),
    ("P008", "Mochila escolar", "Acessórios", 8990),
)

# por onde o vendedor realizou a venda
CANAIS = ("Loja física", "Online")
DESCONTOS_PERCENTUAIS = (0, 10, 20)


def gerar_dados() -> list[Path]:
    fake = Faker("pt_BR")
    fake.seed_instance(42)

    hoje = datetime.now(UTC).astimezone().date()
    periodo_inicio = hoje - timedelta(days=7)
    periodo_fim = hoje - timedelta(days=1)
    vendedores = [(f"V{indice:03d}", fake.name()) for indice in range(1, 4)]

    metas_vendedores = [
        {
            "periodo_inicio": periodo_inicio,
            "periodo_fim": periodo_fim,
            "codigo_vendedor": codigo,
            "vendedor": nome,
            "meta_faturamento_liquido": fake.random_int(min=1_200_000, max=1_600_000)
            / 100,
        }
        for codigo, nome in vendedores
    ]
    metas_produtos = [
        {
            "periodo_inicio": periodo_inicio,
            "periodo_fim": periodo_fim,
            "codigo_produto": codigo,
            "produto": nome,
            "meta_faturamento_liquido": preco_centavos
            * fake.random_int(min=180, max=260)
            / 100,
        }
        for codigo, nome, _, preco_centavos in PRODUTOS
    ]

    pasta_dados = Path(__file__).resolve().parent / "dados"
    pasta_dados.mkdir(exist_ok=True)
    caminhos = []

    for deslocamento in range(7):
        data_venda = periodo_inicio + timedelta(days=deslocamento)
        vendas = []
        for codigo_vendedor, vendedor in vendedores:
            for codigo_produto, produto, categoria, preco_centavos in PRODUTOS:
                for canal in CANAIS:
                    quantidade = fake.random_int(min=1, max=10)
                    desconto_percentual = DESCONTOS_PERCENTUAIS[
                        fake.random_int(min=0, max=len(DESCONTOS_PERCENTUAIS) - 1)
                    ]
                    bruto_centavos = quantidade * preco_centavos
                    desconto_centavos = bruto_centavos * desconto_percentual // 100
                    vendas.append(
                        {
                            "data_venda": data_venda,
                            "codigo_vendedor": codigo_vendedor,
                            "vendedor": vendedor,
                            "codigo_produto": codigo_produto,
                            "produto": produto,
                            "categoria": categoria,
                            "canal_venda": canal,
                            "quantidade_vendida": quantidade,
                            "preco_unitario": preco_centavos / 100,
                            "faturamento_bruto": bruto_centavos / 100,
                            "desconto_total": desconto_centavos / 100,
                            "faturamento_liquido": (bruto_centavos - desconto_centavos)
                            / 100,
                        }
                    )

        caminho = pasta_dados / f"consolidado_vendas-{data_venda:%d-%m-%Y}.xlsx"
        with Workbook(str(caminho)) as workbook:
            for nome, dados in {
                "Vendas": pl.DataFrame(vendas),
                "Vendedores": pl.DataFrame(metas_vendedores),
                "Produtos": pl.DataFrame(metas_produtos),
            }.items():
                dados.write_excel(
                    workbook=workbook,
                    worksheet=nome,
                    dtype_formats={pl.Date: "dd/mm/yyyy"},
                    autofit=True,
                    freeze_panes=(1, 0),
                )

        logger.info("Planilha diária criada: {}", caminho)
        caminhos.append(caminho)

    return caminhos


if __name__ == "__main__":
    gerar_dados()
