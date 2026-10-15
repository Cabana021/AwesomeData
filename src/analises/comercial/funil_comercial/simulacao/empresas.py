import unicodedata
from datetime import date, timedelta
from random import Random
from typing import NamedTuple

from faker import Faker
from simulacao.common import (
    CARGOS,
    DDDS,
    DIAS_MINIMOS_EXPANSAO,
    DIAS_REATIVACAO,
    DOMINIOS_GRATUITOS,
    FORMATOS_EMPRESA,
    NOMES_PLANOS,
    PESOS_CARGOS,
    PESOS_PORTES,
    PESOS_SUFIXOS_MEDIA,
    PESOS_UFS,
    PORTES,
    PROBABILIDADE_EMAIL_GRATUITO,
    QTD_PLANOS_MICRO,
    SEGMENTOS,
    SEGMENTOS_ME_EI,
    SUFIXOS_ME_EI,
    SUFIXOS_MEDIA,
    UFS,
)


class Empresa(NamedTuple):
    nome: str
    segmento: str
    porte: str
    uf: str
    contato: str
    email: str
    celular: str
    cargo: str


class Historico(NamedTuple):
    # None enquanto a empresa só teve Leads
    vendedor: str | None
    # do último negócio da empresa
    status: str
    fechamento: date | None
    plano_ganho: int


def nome_pessoa(fake: Faker) -> str:
    return f"{fake.first_name()} {fake.last_name()}"


def normalizar_para_email(texto: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(letra for letra in ascii_.lower() if letra.isalnum())


def sufixo_empresa(rng: Random, segmento: str, porte: str) -> str:
    if porte == "Micro":
        return rng.choice(SUFIXOS_ME_EI) if segmento in SEGMENTOS_ME_EI else "Ltda."
    if porte == "Média":
        return rng.choices(SUFIXOS_MEDIA, weights=PESOS_SUFIXOS_MEDIA)[0]
    return "Ltda."


def criar_empresa(
    fake: Faker,
    rng_contatos: Random,
    fantasias_usadas: set[str],
) -> Empresa:
    rng = fake.random
    segmento = rng.choice(SEGMENTOS)
    porte = rng.choices(PORTES, weights=PESOS_PORTES)[0]
    nome_fantasia = ""
    while not nome_fantasia or nome_fantasia in fantasias_usadas:
        sobrenome_1, sobrenome_2 = fake.last_name(), fake.last_name()
        if sobrenome_1 == sobrenome_2:
            continue
        formato = rng.choice(FORMATOS_EMPRESA[segmento])
        nome_fantasia = formato.format(f"{sobrenome_1} & {sobrenome_2}")
    fantasias_usadas.add(nome_fantasia)
    nome = f"{nome_fantasia} {sufixo_empresa(rng, segmento, porte)}"
    uf = rng.choices(UFS, weights=PESOS_UFS)[0]
    contato = nome_pessoa(fake)

    celular = (
        f"({DDDS[uf]}) 9{rng_contatos.randint(6000, 9999)}-"
        f"{rng_contatos.randint(0, 9999):04d}"
    )
    cargo = rng_contatos.choices(CARGOS, weights=PESOS_CARGOS[porte])[0]

    primeiro_nome, *_, sobrenome = contato.split()
    usuario = (
        f"{normalizar_para_email(primeiro_nome)}.{normalizar_para_email(sobrenome)}"
    )
    if porte == "Micro" and rng_contatos.random() < PROBABILIDADE_EMAIL_GRATUITO:
        # o número evita o mesmo e-mail em empresas diferentes
        email = (
            f"{usuario}{rng_contatos.randint(10, 99)}"
            f"@{rng_contatos.choice(DOMINIOS_GRATUITOS)}"
        )
    else:
        email = f"{usuario}@{normalizar_para_email(nome_fantasia)}.com.br"
    return Empresa(nome, segmento, porte, uf, contato, email, celular, cargo)


def qtd_planos(empresa: Empresa) -> int:
    return QTD_PLANOS_MICRO if empresa.porte == "Micro" else len(NOMES_PLANOS)


def empresas_elegiveis(
    tipo_negocio: str,
    empresas: list[Empresa],
    historicos: dict[str, Historico],
    dia: date,
) -> list[Empresa]:
    if tipo_negocio == "Novo":
        return []

    elegiveis = []
    for empresa in empresas:
        historico = historicos[empresa.nome]
        # empresa com negócio em curso não recebe outro
        if historico.fechamento is None or historico.fechamento >= dia:
            continue
        if tipo_negocio == "Expansão":
            # só o cliente cujo último negócio foi ganho recebe Expansão
            elegivel = (
                historico.status == "Ganho"
                and historico.fechamento <= dia - timedelta(days=DIAS_MINIMOS_EXPANSAO)
                and historico.plano_ganho < qtd_planos(empresa) - 1
            )
        else:
            # quem já foi cliente não é reativado
            elegivel = (
                historico.status == "Perdido"
                and historico.plano_ganho == -1
                and historico.fechamento <= dia - timedelta(days=DIAS_REATIVACAO)
            )
        if elegivel:
            elegiveis.append(empresa)
    return elegiveis
