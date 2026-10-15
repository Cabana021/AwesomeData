import calendar
from pathlib import Path
from random import Random

import polars as pl
from faker import Faker
from loguru import logger
from simulacao.common import (
    CRESCIMENTO_VOLUME_2026,
    MESES_POR_ANO,
    NOMES_PLANOS,
    PESOS_TIPOS_NEGOCIO,
    QTD_SDRS,
    QTD_VENDEDORES,
    RUIDO_VOLUME,
    TIPOS_NEGOCIO,
)
from simulacao.empresas import (
    Empresa,
    Historico,
    criar_empresa,
    empresas_elegiveis,
    nome_pessoa,
)
from simulacao.negocios import simular_negocio


def gerar_id(rng_ids: Random, ids_usados: set[int]) -> int:
    id_novo = rng_ids.randint(10**10, 10**11 - 1)
    while id_novo in ids_usados:
        id_novo = rng_ids.randint(10**10, 10**11 - 1)
    ids_usados.add(id_novo)
    return id_novo


def sortear_volumes(rng_volume: Random) -> dict[int, list[int]]:
    # fim de trimestre (mar, jun, set e dez) cria mais negócios
    quantidades = {
        ano: [
            round(
                (
                    rng_volume.randint(184, 190)
                    if mes % 3 == 0
                    else rng_volume.randint(150, 158)
                )
                * (1 + rng_volume.uniform(-RUIDO_VOLUME, RUIDO_VOLUME))
            )
            for mes in meses
        ]
        for ano, meses in MESES_POR_ANO.items()
        if ano < 2026
    }
    quantidades[2026] = [
        round(q * rng_volume.uniform(*CRESCIMENTO_VOLUME_2026))
        for q in quantidades[2025][: len(MESES_POR_ANO[2026])]
    ]
    return quantidades


def gerar_dados() -> Path:
    fake = Faker("pt_BR")
    fake.seed_instance(27)
    rng = fake.random

    sdrs = [nome_pessoa(fake) for _ in range(QTD_SDRS)]
    vendedores = [nome_pessoa(fake) for _ in range(QTD_VENDEDORES)]
    # as empresas nascem no primeiro negócio Novo; o histórico define o tipo dos seguintes
    empresas: list[Empresa] = []
    fantasias_usadas: set[str] = set()
    historicos: dict[str, Historico] = {}
    rng_ids = Random(27)
    rng_contatos = Random(28)
    rng_volume = Random(29)
    ids_usados: set[int] = set()

    quantidades = sortear_volumes(rng_volume)

    negocios = []
    for ano, meses in MESES_POR_ANO.items():
        for mes, quantidade in zip(meses, quantidades[ano], strict=True):
            dias_uteis = [
                dia
                for dia in calendar.Calendar().itermonthdates(ano, mes)
                if dia.month == mes and dia.weekday() < 5
            ]
            # em ordem, para o histórico da empresa estar pronto no negócio seguinte
            dias_criacao = sorted(rng.choice(dias_uteis) for _ in range(quantidade))
            for dia in dias_criacao:
                tipo_negocio = rng.choices(TIPOS_NEGOCIO, weights=PESOS_TIPOS_NEGOCIO)[
                    0
                ]
                elegiveis = empresas_elegiveis(tipo_negocio, empresas, historicos, dia)
                if elegiveis:
                    empresa = rng.choice(elegiveis)
                else:
                    # sem empresa elegível, o negócio abre uma empresa nova
                    tipo_negocio = "Novo"
                    empresa = criar_empresa(fake, rng_contatos, fantasias_usadas)
                    empresas.append(empresa)
                # 2024 segue as regras de 2025
                anterior = historicos.get(empresa.nome)
                negocio = simular_negocio(
                    fake,
                    max(ano, 2025),
                    dia,
                    empresa,
                    tipo_negocio,
                    sdrs,
                    vendedores,
                    anterior,
                )
                plano_ganho = anterior.plano_ganho if anterior else -1
                if negocio["status"] == "Ganho":
                    plano_ganho = NOMES_PLANOS.index(negocio["plano"])
                historicos[empresa.nome] = Historico(
                    negocio["vendedor"],
                    negocio["status"],
                    negocio["data_fechamento"],
                    plano_ganho,
                )
                negocios.append({"id": gerar_id(rng_ids, ids_usados), **negocio})

    negocios.sort(key=lambda negocio: str(negocio["data_criacao"]))

    pasta_dados = Path(__file__).resolve().parent / "dados"
    pasta_dados.mkdir(exist_ok=True)
    caminho = pasta_dados / "negocios.csv"
    pl.DataFrame(negocios, infer_schema_length=None).write_csv(
        caminho, float_precision=2
    )

    logger.info("Base de negócios criada: {} ({} negócios)", caminho, len(negocios))
    return caminho


if __name__ == "__main__":
    gerar_dados()
