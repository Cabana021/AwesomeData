from pathlib import Path

import polars as pl
from geradores.conversao_etapas import etapas_atingidas, grafico_conversao_etapas
from geradores.forecast_q4 import forecast_q4, grafico_forecast_q4, receita_q4_2025
from geradores.indicadores_ytd import grafico_indicadores_ytd, indicadores_ytd
from geradores.metricas_grupo import grafico_metricas_grupo, metricas_por_grupo
from geradores.motivos_perda import (
    grafico_motivos_perda,
    motivos_perda,
    perdas_apos_lead,
)
from geradores.receita_ytd import grafico_receita_ytd, receita_ytd
from loguru import logger


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
    indicadores = indicadores_ytd(negocios)
    grafico_indicadores_ytd(indicadores, pasta_graficos / "indicadores_ytd.html")
    etapas = etapas_atingidas(negocios)
    grafico_conversao_etapas(etapas, pasta_graficos / "conversao_etapas.html")
    grafico_forecast_q4(
        forecast_q4(negocios, etapas),
        receita_q4_2025(negocios),
        pasta_graficos / "forecast_q4.html",
    )
    grafico_metricas_grupo(
        metricas_por_grupo(negocios, "canal_origem"), pasta_graficos / "canais.html"
    )
    qualificados = negocios.filter(pl.col("data_entrada_qualificado").is_not_null())
    grafico_metricas_grupo(
        metricas_por_grupo(qualificados, "vendedor"), pasta_graficos / "vendedores.html"
    )
    grafico_motivos_perda(
        motivos_perda(perdas_apos_lead(negocios)),
        pasta_graficos / "motivos_perda.html",
    )
    logger.info("Gráficos criados em {}", pasta_graficos)


if __name__ == "__main__":
    gerar_graficos()
