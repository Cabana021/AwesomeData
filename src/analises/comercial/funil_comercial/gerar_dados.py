import calendar
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from random import Random
from typing import Any, NamedTuple

import polars as pl
from faker import Faker
from loguru import logger

DATA_CORTE = date(2026, 9, 30)
# 2025 vai até dezembro para ter a receita realizada do Q4. Out a dez/2024 existe só
# para que janeiro de 2025 não comece sem negócios em andamento
MESES_POR_ANO = {2024: range(10, 13), 2025: range(1, 13), 2026: range(1, 10)}
CRESCIMENTO_VOLUME_2026 = 1.25

ETAPAS = ("Lead", "Qualificado", "Proposta", "Negociação")

# probabilidade de avançar de uma etapa para a seguinte
PROBABILIDADE_LEAD_QUALIFICADO = 0.55
PROBABILIDADE_QUALIFICADO_PROPOSTA = 0.65
PROBABILIDADE_PROPOSTA_NEGOCIACAO = 0.73
PROBABILIDADE_NEGOCIACAO_GANHO = 0.88

# prazo em dias (mínimo, máximo) entre as etapas e até o fechamento
PRAZOS_ETAPA = ((2, 8), (3, 10), (5, 14))
PRAZO_GANHO = (5, 18)
PRAZO_PERDA = (2, 10)

# canal, fator de conversão em Proposta → Negociação, fator de ticket, campanhas
CANAIS = (
    ("Indicação", 1.3, 1.3, ("Programa de indicação",)),
    ("Site", 0.95, 1.0, ("Blog", "Newsletter", "Teste grátis")),
    ("Mídia paga", 0.9, 1.0, ("Google Ads", "LinkedIn Ads", "Meta Ads")),
    ("Evento", 0.9, 0.9, ("Feira Gestão PME", "Congresso de Varejo", "Webinar")),
    ("Outbound", 0.9, 1.0, ("Cadência outbound",)),
)
PESOS_CANAIS = {2025: (20, 25, 20, 10, 25), 2026: (18, 22, 18, 20, 22)}
# Expansão vem da base de clientes e não entra no sorteio de canais
CANAL_EXPANSAO = ("Base de clientes", 1.0, 1.0, ("Upgrade de plano",))

# plano, valor estimado mínimo e máximo
PLANOS = (
    ("Starter", 7_000, 11_000),
    ("Pro", 22_000, 36_000),
    ("Enterprise", 70_000, 110_000),
)
NOMES_PLANOS = tuple(nome for nome, _, _ in PLANOS)
PESOS_PLANOS = (55, 35, 10)
# porte Micro não contrata Enterprise
QTD_PLANOS_MICRO = 2

TIPOS_NEGOCIO = ("Novo", "Expansão", "Reativação")
PESOS_TIPOS_NEGOCIO = (60, 30, 10)
# Reativação: empresa cujo último negócio foi perdido há pelo menos esse prazo
DIAS_REATIVACAO = 90
# Expansão: empresa cujo último ganho ocorreu há pelo menos esse prazo
DIAS_MINIMOS_EXPANSAO = 30

SEGMENTOS = ("Varejo", "Indústria", "Serviços", "Saúde", "Educação", "Logística")
FATOR_PORTE = {"Micro": 0.8, "Pequena": 1.0, "Média": 1.3}
UFS = ("SP", "RJ", "MG", "PR", "RS", "SC", "BA", "GO")
DDDS = {"SP": 11, "RJ": 21, "MG": 31, "PR": 41, "RS": 51, "SC": 48, "BA": 71, "GO": 62}
CARGOS = ("Sócio", "Diretor", "Gerente", "Analista")
PESOS_CARGOS = {
    "Micro": (80, 10, 5, 5),
    "Pequena": (50, 25, 15, 10),
    "Média": (15, 35, 35, 15),
}
FORMATOS_EMPRESA = {
    "Varejo": ("Mercado {}", "Magazine {}", "{} Comércio"),
    "Indústria": ("Metalúrgica {}", "Plásticos {}", "{} Indústria"),
    "Serviços": ("{} Consultoria", "{} Contabilidade", "{} Engenharia"),
    "Saúde": ("Clínica {}", "Laboratório {}", "Centro Médico {}"),
    "Educação": ("Colégio {}", "Escola {}", "Instituto {}"),
    "Logística": ("Transportes {}", "{} Logística", "{} Transportes"),
}
SUFIXOS_PORTE = {
    "Micro": ("ME", "EI"),
    "Pequena": ("Ltda.",),
    "Média": ("Ltda.", "S/A"),
}

QTD_SDRS = 3
QTD_VENDEDORES = 6
# vendedor que concentra a piora de conversão em 2026
INDICE_VENDEDOR_EM_QUEDA = 2
FATOR_VENDEDOR_EM_QUEDA = 0.55

DESCONTOS = (0, 5, 10, 15, 20)
PESOS_DESCONTOS = (30, 20, 25, 15, 10)

MOTIVOS_PERDA = (
    "Preço",
    "Concorrente",
    "Sem orçamento",
    "Sem retorno",
    "Fora do perfil",
    "Timing",
)
# negócio perdido ainda como Lead não chegou a falar de preço nem de concorrente
PESOS_MOTIVOS_LEAD = (0, 0, 15, 45, 25, 15)
# perdido de Qualificado em diante
PESOS_MOTIVOS = {2025: (22, 25, 15, 18, 5, 15), 2026: (32, 25, 12, 14, 4, 13)}
PESOS_MOTIVOS_EVENTO = (65, 10, 8, 7, 0, 10)

# mínimo e máximo de reuniões por etapa atingida
REUNIOES_ETAPA = ((0, 1), (1, 2), (2, 4), (3, 5))
STATUS_REUNIAO = ("Realizada", "Agendada", "Não compareceu")
PESOS_STATUS_REUNIAO = {
    "Ganho": (100, 0, 0),
    "Perdido": (80, 0, 20),
    "Aberto": (60, 25, 15),
}


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
    vendedor: str
    # do último negócio da empresa
    status: str
    fechamento: date | None
    # índice em PLANOS e data do último ganho; -1 e None enquanto não há ganho
    plano_ganho: int
    data_ganho: date | None


def nome_pessoa(fake: Faker) -> str:
    return f"{fake.first_name()} {fake.last_name()}"


def slug(texto: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(letra for letra in ascii_.lower() if letra.isalnum())


def gerar_id(rng_ids: Random, ids_usados: set[int]) -> int:
    """ID numérico de 11 dígitos, sem relação com a ordem de criação."""
    id_novo = rng_ids.randint(10**10, 10**11 - 1)
    while id_novo in ids_usados:
        id_novo = rng_ids.randint(10**10, 10**11 - 1)
    ids_usados.add(id_novo)
    return id_novo


def criar_empresa(
    fake: Faker,
    rng_contatos: Random,
    nomes_usados: set[str],
    dominios_usados: set[str],
) -> Empresa:
    rng = fake.random
    segmento = rng.choice(SEGMENTOS)
    porte = rng.choice(tuple(FATOR_PORTE))
    nome = ""
    while not nome or nome in nomes_usados:
        formato = rng.choice(FORMATOS_EMPRESA[segmento])
        sufixo = rng.choice(SUFIXOS_PORTE[porte])
        nome_fantasia = formato.format(fake.last_name())
        nome = f"{nome_fantasia} {sufixo}"
    nomes_usados.add(nome)
    uf = rng.choice(UFS)
    contato = nome_pessoa(fake)

    # nomes-fantasia iguais em empresas diferentes ganham UF e número no domínio
    dominio = slug(nome_fantasia)
    if dominio in dominios_usados:
        dominio += uf.lower()
    dominio_base, sequencia = dominio, 2
    while dominio in dominios_usados:
        dominio = f"{dominio_base}{sequencia}"
        sequencia += 1
    dominios_usados.add(dominio)

    primeiro_nome, *_, sobrenome = contato.split()
    email = f"{slug(primeiro_nome)}.{slug(sobrenome)}@{dominio}.com.br"
    celular = (
        f"({DDDS[uf]}) 9{rng_contatos.randint(6000, 9999)}-"
        f"{rng_contatos.randint(0, 9999):04d}"
    )
    cargo = rng_contatos.choices(CARGOS, weights=PESOS_CARGOS[porte])[0]
    return Empresa(nome, segmento, porte, uf, contato, email, celular, cargo)


def qtd_planos(empresa: Empresa) -> int:
    return QTD_PLANOS_MICRO if empresa.porte == "Micro" else len(PLANOS)


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
            # só sobe de plano: Enterprise e o maior plano do porte não recebem Expansão
            elegivel = (
                historico.data_ganho is not None
                and historico.data_ganho <= dia - timedelta(days=DIAS_MINIMOS_EXPANSAO)
                and historico.plano_ganho < qtd_planos(empresa) - 1
            )
        else:
            elegivel = (
                historico.status == "Perdido"
                and historico.fechamento <= dia - timedelta(days=DIAS_REATIVACAO)
            )
        if elegivel:
            elegiveis.append(empresa)
    return elegiveis


def proximo_dia_util(dia: date) -> date:
    while dia.weekday() >= 5:
        dia += timedelta(days=1)
    return dia


def simular_negocio(
    fake: Faker,
    ano: int,
    data_criacao: date,
    empresa: Empresa,
    tipo_negocio: str,
    sdrs: list[str],
    vendedores: list[str],
    historico: Historico | None,
) -> dict[str, Any]:
    rng = fake.random

    if tipo_negocio == "Expansão":
        canal, fator_conversao, fator_ticket, campanhas = CANAL_EXPANSAO
    else:
        canal, fator_conversao, fator_ticket, campanhas = rng.choices(
            CANAIS, weights=PESOS_CANAIS[ano]
        )[0]
    # Expansão contrata plano acima do último ganho
    primeiro_plano = 0
    if historico and tipo_negocio == "Expansão":
        primeiro_plano = historico.plano_ganho + 1
    ultimo_plano = qtd_planos(empresa)
    plano, valor_minimo, valor_maximo = rng.choices(
        PLANOS[primeiro_plano:ultimo_plano],
        weights=PESOS_PLANOS[primeiro_plano:ultimo_plano],
    )[0]
    # a empresa mantém o vendedor do primeiro negócio
    vendedor = historico.vendedor if historico else rng.choice(vendedores)

    fator_vendedor = 1.0
    if ano == 2026 and vendedor == vendedores[INDICE_VENDEDOR_EM_QUEDA]:
        fator_vendedor = FATOR_VENDEDOR_EM_QUEDA

    # etapa_final: quantas transições o negócio concluiu (4 = ganho)
    etapa_final = 0
    for probabilidade in (
        PROBABILIDADE_LEAD_QUALIFICADO,
        PROBABILIDADE_QUALIFICADO_PROPOSTA,
        min(0.95, PROBABILIDADE_PROPOSTA_NEGOCIACAO * fator_conversao * fator_vendedor),
        PROBABILIDADE_NEGOCIACAO_GANHO,
    ):
        if rng.random() >= probabilidade:
            break
        etapa_final += 1
    ganho = etapa_final == len(ETAPAS)

    entradas = [data_criacao]
    for prazo in PRAZOS_ETAPA[: min(etapa_final, len(ETAPAS) - 1)]:
        entradas.append(
            proximo_dia_util(entradas[-1] + timedelta(days=rng.randint(*prazo)))
        )
    prazo_fechamento = PRAZO_GANHO if ganho else PRAZO_PERDA
    fechamento = proximo_dia_util(
        entradas[-1] + timedelta(days=rng.randint(*prazo_fechamento))
    )

    # o que não fechou até o corte segue aberto
    aberto = fechamento > DATA_CORTE
    if aberto:
        entradas = [entrada for entrada in entradas if entrada <= DATA_CORTE]
    indice_etapa = len(entradas) - 1
    etapa_atual = ETAPAS[indice_etapa]
    datas: list[date | None] = [*entradas, *[None] * (len(ETAPAS) - len(entradas))]

    if aberto:
        status = "Aberto"
        data_fechamento = None
        data_ultima_atividade = min(
            DATA_CORTE,
            proximo_dia_util(entradas[-1] + timedelta(days=rng.randint(0, 30))),
        )
    else:
        status = "Ganho" if ganho else "Perdido"
        data_fechamento = fechamento
        data_ultima_atividade = fechamento

    valor_estimado = round(
        rng.uniform(valor_minimo, valor_maximo)
        * FATOR_PORTE[empresa.porte]
        * fator_ticket,
        -2,
    )
    desconto = None
    if indice_etapa >= ETAPAS.index("Proposta"):
        desconto = rng.choices(DESCONTOS, weights=PESOS_DESCONTOS)[0]

    motivo_perda = None
    if status == "Perdido":
        if indice_etapa == 0:
            pesos_motivos = PESOS_MOTIVOS_LEAD
        elif canal == "Evento":
            pesos_motivos = PESOS_MOTIVOS_EVENTO
        else:
            pesos_motivos = PESOS_MOTIVOS[ano]
        motivo_perda = rng.choices(MOTIVOS_PERDA, weights=pesos_motivos)[0]
        # quem some deixa de ter atividade logo após a última etapa
        if motivo_perda == "Sem retorno":
            data_ultima_atividade = entradas[-1]

    valor_fechado = None
    if desconto is not None and status == "Ganho":
        valor_fechado = round(valor_estimado * (1 - desconto / 100), 2)

    qtd_reunioes = rng.randint(*REUNIOES_ETAPA[indice_etapa])
    # a partir de Qualificado há sempre reunião; só fica sem contato quem parou em Lead
    foi_contatado = qtd_reunioes > 0
    status_reuniao = "Sem reunião"
    if foi_contatado:
        status_reuniao = rng.choices(
            STATUS_REUNIAO, weights=PESOS_STATUS_REUNIAO[status]
        )[0]

    return {
        "nome_negocio": f"{tipo_negocio} {plano} - {empresa.nome}",
        "empresa": empresa.nome,
        "nome_contato": empresa.contato,
        "cargo_contato": empresa.cargo,
        "email_contato": empresa.email,
        "celular_contato": empresa.celular,
        "segmento": empresa.segmento,
        "porte": empresa.porte,
        "uf": empresa.uf,
        "tipo_negocio": tipo_negocio,
        "plano": plano,
        "canal_origem": canal,
        "campanha_origem": rng.choice(campanhas),
        "sdr": rng.choice(sdrs),
        "vendedor": vendedor,
        "etapa_atual": etapa_atual,
        "status": status,
        "valor_estimado": valor_estimado,
        "desconto_percentual": desconto,
        "valor_fechado": valor_fechado,
        "data_criacao": data_criacao,
        "data_entrada_qualificado": datas[1],
        "data_entrada_proposta": datas[2],
        "data_entrada_negociacao": datas[3],
        "data_fechamento": data_fechamento,
        "data_ultima_atividade": data_ultima_atividade,
        "foi_contatado": foi_contatado,
        "qtd_reunioes": qtd_reunioes,
        "status_ultima_reuniao": status_reuniao,
        "motivo_perda": motivo_perda,
    }


def gerar_dados() -> Path:
    fake = Faker("pt_BR")
    fake.seed_instance(27)
    rng = fake.random

    sdrs = [nome_pessoa(fake) for _ in range(QTD_SDRS)]
    vendedores = [nome_pessoa(fake) for _ in range(QTD_VENDEDORES)]
    # as empresas nascem no primeiro negócio Novo; o histórico define o tipo dos seguintes
    empresas: list[Empresa] = []
    nomes_usados: set[str] = set()
    historicos: dict[str, Historico] = {}
    dominios_usados: set[str] = set()
    # geradores próprios, para IDs e celulares não alterarem o restante dos dados
    rng_ids = Random(27)
    rng_contatos = Random(28)
    ids_usados: set[int] = set()

    # fim de trimestre (mar, jun, set e dez) cria mais negócios
    quantidades = {
        ano: [
            rng.randint(184, 190) if mes % 3 == 0 else rng.randint(150, 158)
            for mes in meses
        ]
        for ano, meses in MESES_POR_ANO.items()
        if ano < 2026
    }
    quantidades[2026] = [
        round(q * CRESCIMENTO_VOLUME_2026)
        for q in quantidades[2025][: len(MESES_POR_ANO[2026])]
    ]

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
                    empresa = criar_empresa(
                        fake, rng_contatos, nomes_usados, dominios_usados
                    )
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
                data_ganho = anterior.data_ganho if anterior else None
                if negocio["status"] == "Ganho":
                    plano_ganho = NOMES_PLANOS.index(negocio["plano"])
                    data_ganho = negocio["data_fechamento"]
                historicos[empresa.nome] = Historico(
                    negocio["vendedor"],
                    negocio["status"],
                    negocio["data_fechamento"],
                    plano_ganho,
                    data_ganho,
                )
                negocios.append({"id": gerar_id(rng_ids, ids_usados), **negocio})

    negocios.sort(key=lambda negocio: str(negocio["data_criacao"]))

    pasta_dados = Path(__file__).resolve().parent / "dados"
    pasta_dados.mkdir(exist_ok=True)
    caminho = pasta_dados / "negocios.csv"
    pl.DataFrame(negocios, infer_schema_length=None).write_csv(caminho)

    logger.info("Base de negócios criada: {} ({} negócios)", caminho, len(negocios))
    return caminho


if __name__ == "__main__":
    gerar_dados()
