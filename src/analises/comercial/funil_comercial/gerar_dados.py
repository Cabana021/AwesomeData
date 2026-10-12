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
# o prazo sorteado tem cauda longa até esse múltiplo do máximo
CAUDA_PRAZO = 2
# multiplicador de prazo por plano: Starter, Pro e Enterprise
FATORES_PRAZO_PLANO = (1.0, 1.5, 2.5)

# negócio criado nos últimos 90 dias que trava na última etapa e fica Aberto sem atividade
JANELA_PARADOS = 90
PROBABILIDADE_PARADO = 0.2
# o parado precisa estar sem atividade há mais que o limite dos demais abertos
DIAS_SEM_ATIVIDADE_ABERTO = 30
DIAS_MINIMOS_PARADO = 45

# canal, fator de conversão em Proposta → Negociação, probabilidade de o Lead já ter
# sido contatado (de Qualificado em diante é sempre), pesos de plano, campanhas
CANAIS = (
    ("Indicação", 1.3, 0.95, (35, 40, 25), ("Programa de indicação",)),
    ("Site", 0.95, 0.75, (55, 35, 10), ("Blog", "Newsletter", "Teste grátis")),
    ("Mídia paga", 0.9, 0.65, (65, 30, 5), ("Google Ads", "LinkedIn Ads", "Meta Ads")),
    (
        "Evento",
        0.9,
        0.7,
        (65, 30, 5),
        ("Feira Gestão PME", "Congresso de Varejo", "Webinar"),
    ),
    ("Outbound", 0.9, 0.95, (40, 40, 20), ("Cadência outbound",)),
)
PESOS_CANAIS = {2025: (20, 25, 20, 10, 25), 2026: (18, 22, 18, 20, 22)}
# Expansão vem da base de clientes e não entra no sorteio de canais; o cliente é
# sempre contatado
CANAL_EXPANSAO = (
    "Base de clientes",
    1.0,
    1.0,
    (55, 35, 10),
    ("Upgrade de plano",),
)

NOMES_PLANOS = ("Starter", "Pro", "Enterprise")
# valores anuais possíveis por plano e porte; Micro não contrata Enterprise
PRECOS = {
    "Starter": {
        "Micro": (6_000, 7_000, 8_000),
        "Pequena": (9_000, 10_000, 11_000),
        "Média": (12_000, 13_000, 14_000),
    },
    "Pro": {
        "Micro": (20_000, 23_000, 26_000),
        "Pequena": (28_000, 31_000, 34_000),
        "Média": (38_000, 42_000, 46_000),
    },
    "Enterprise": {
        "Pequena": (70_000, 80_000, 90_000),
        "Média": (100_000, 115_000, 130_000),
    },
}
QTD_PLANOS_MICRO = 2

TIPOS_NEGOCIO = ("Novo", "Expansão", "Reativação")
PESOS_TIPOS_NEGOCIO = (60, 30, 10)
# Reativação: empresa que nunca foi cliente e cujo último negócio foi perdido há pelo
# menos esse prazo
DIAS_REATIVACAO = 90
# Expansão: empresa cujo último negócio foi ganho há pelo menos esse prazo
DIAS_MINIMOS_EXPANSAO = 30

SEGMENTOS = ("Varejo", "Indústria", "Serviços", "Saúde", "Educação", "Logística")
PORTES = ("Micro", "Pequena", "Média")
PESOS_PORTES = (40, 40, 20)
UFS = ("SP", "RJ", "MG", "PR", "RS", "SC", "BA", "GO")
PESOS_UFS = (35, 14, 15, 11, 9, 8, 5, 3)
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
# ME e EI só em segmentos de pequeno negócio; os demais portes Micro abrem como Ltda.
SEGMENTOS_ME_EI = ("Varejo", "Serviços", "Logística")
SUFIXOS_ME_EI = ("ME", "EI")
# Média é quase sempre Ltda., e S/A é raro
SUFIXOS_MEDIA = ("Ltda.", "S/A")
PESOS_SUFIXOS_MEDIA = (90, 10)
# parte das Micro usa e-mail de provedor gratuito no lugar do domínio da empresa
PROBABILIDADE_EMAIL_GRATUITO = 0.3
DOMINIOS_GRATUITOS = ("gmail.com", "outlook.com", "hotmail.com", "yahoo.com.br")

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
# Lead perdido sem contato só pode ser fora do perfil
PESOS_MOTIVOS_SEM_CONTATO = (0, 0, 0, 0, 1, 0)
# Lead perdido com contato não chegou a falar de preço nem de concorrente
PESOS_MOTIVOS_LEAD = (0, 0, 15, 45, 0, 15)
# perdido de Qualificado em diante
PESOS_MOTIVOS = {2025: (22, 25, 15, 18, 5, 15), 2026: (32, 25, 12, 14, 4, 13)}
PESOS_MOTIVOS_EVENTO = (65, 10, 8, 7, 0, 10)

# mínimo e máximo de reuniões por plano (Starter, Pro, Enterprise) e etapa atingida;
# o Lead não tem reunião
REUNIOES_PLANO_ETAPA = (
    ((0, 0), (1, 1), (1, 2), (1, 3)),
    ((0, 0), (1, 2), (2, 4), (3, 5)),
    ((0, 0), (2, 3), (3, 5), (4, 7)),
)
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
    # None enquanto a empresa só teve Leads
    vendedor: str | None
    # do último negócio da empresa
    status: str
    fechamento: date | None
    # índice em NOMES_PLANOS do último ganho; -1 enquanto a empresa não é cliente
    plano_ganho: int


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
    # dois sobrenomes distintos, com nome-fantasia único, dão domínio único
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
    usuario = f"{slug(primeiro_nome)}.{slug(sobrenome)}"
    if porte == "Micro" and rng_contatos.random() < PROBABILIDADE_EMAIL_GRATUITO:
        # o número evita o mesmo e-mail em empresas diferentes
        email = (
            f"{usuario}{rng_contatos.randint(10, 99)}"
            f"@{rng_contatos.choice(DOMINIOS_GRATUITOS)}"
        )
    else:
        email = f"{usuario}@{slug(nome_fantasia)}.com.br"
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
            # só o cliente cujo último negócio foi ganho recebe Expansão, que sobe de
            # plano: Enterprise e o maior plano do porte não recebem
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


def proximo_dia_util(dia: date) -> date:
    while dia.weekday() >= 5:
        dia += timedelta(days=1)
    return dia


def sortear_prazo(rng: Random, prazo: tuple[int, int], fator: float) -> int:
    """Prazo em dias, concentrado na primeira metade da faixa e com cauda longa."""
    minimo, maximo = prazo
    moda = (minimo + maximo) / 2
    return round(rng.triangular(minimo, maximo * CAUDA_PRAZO, moda) * fator)


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
        canal, fator_conversao, prob_contato, pesos_planos, campanhas = CANAL_EXPANSAO
    else:
        canal, fator_conversao, prob_contato, pesos_planos, campanhas = rng.choices(
            CANAIS, weights=PESOS_CANAIS[ano]
        )[0]
    # Expansão contrata plano acima do último ganho
    primeiro_plano = 0
    if historico and tipo_negocio == "Expansão":
        primeiro_plano = historico.plano_ganho + 1
    ultimo_plano = qtd_planos(empresa)
    indice_plano = rng.choices(
        range(primeiro_plano, ultimo_plano),
        weights=pesos_planos[primeiro_plano:ultimo_plano],
    )[0]
    plano = NOMES_PLANOS[indice_plano]
    fator_prazo = FATORES_PRAZO_PLANO[indice_plano]
    # a empresa mantém o vendedor do primeiro negócio que passou de Lead
    vendedor_empresa = historico.vendedor if historico else None
    vendedor = vendedor_empresa or rng.choice(vendedores)

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
        dias = sortear_prazo(rng, prazo, fator_prazo)
        entradas.append(proximo_dia_util(entradas[-1] + timedelta(days=dias)))
    prazo_fechamento = PRAZO_GANHO if ganho else PRAZO_PERDA
    dias = sortear_prazo(rng, prazo_fechamento, fator_prazo)
    fechamento = proximo_dia_util(entradas[-1] + timedelta(days=dias))

    # o que não fechou até o corte segue aberto
    aberto = fechamento > DATA_CORTE
    if aberto:
        entradas = [entrada for entrada in entradas if entrada <= DATA_CORTE]
    # o parado trava na última etapa e some do radar, mesmo que fosse fechar
    parado = (
        data_criacao >= DATA_CORTE - timedelta(days=JANELA_PARADOS)
        and entradas[-1] <= DATA_CORTE - timedelta(days=DIAS_MINIMOS_PARADO)
        and rng.random() < PROBABILIDADE_PARADO
    )
    aberto = aberto or parado
    indice_etapa = len(entradas) - 1
    etapa_atual = ETAPAS[indice_etapa]
    datas: list[date | None] = [*entradas, *[None] * (len(ETAPAS) - len(entradas))]

    if aberto:
        status = "Aberto"
        data_fechamento = None
        if parado:
            ultima_atividade = entradas[-1] + timedelta(days=rng.randint(0, 10))
        else:
            # o aberto que não está parado teve atividade nos últimos 30 dias
            inicio = max(
                entradas[-1], DATA_CORTE - timedelta(days=DIAS_SEM_ATIVIDADE_ABERTO)
            )
            ultima_atividade = inicio + timedelta(
                days=rng.randint(0, (DATA_CORTE - inicio).days)
            )
        data_ultima_atividade = min(DATA_CORTE, proximo_dia_util(ultima_atividade))
    else:
        status = "Ganho" if ganho else "Perdido"
        data_fechamento = fechamento
        data_ultima_atividade = fechamento

    valor_estimado = float(rng.choice(PRECOS[plano][empresa.porte]))
    desconto = None
    if indice_etapa >= ETAPAS.index("Proposta"):
        desconto = rng.choices(DESCONTOS, weights=PESOS_DESCONTOS)[0]

    # a partir de Qualificado há sempre contato e reunião
    foi_contatado = indice_etapa > 0 or rng.random() < prob_contato

    motivo_perda = None
    if status == "Perdido":
        if not foi_contatado:
            pesos_motivos = PESOS_MOTIVOS_SEM_CONTATO
        elif indice_etapa == 0:
            pesos_motivos = PESOS_MOTIVOS_LEAD
        elif canal == "Evento":
            pesos_motivos = PESOS_MOTIVOS_EVENTO
        else:
            pesos_motivos = PESOS_MOTIVOS[ano]
        pesos = list(pesos_motivos)
        if tipo_negocio == "Expansão":
            # o cliente já está no perfil
            pesos[MOTIVOS_PERDA.index("Fora do perfil")] = 0
        motivo_perda = rng.choices(MOTIVOS_PERDA, weights=pesos)[0]
        # quem some deixa de ter atividade logo após a última etapa
        if motivo_perda == "Sem retorno":
            data_ultima_atividade = entradas[-1]

    valor_fechado = None
    if desconto is not None and status == "Ganho":
        valor_fechado = round(valor_estimado * (1 - desconto / 100), 2)

    qtd_reunioes = rng.randint(*REUNIOES_PLANO_ETAPA[indice_plano][indice_etapa])
    status_reuniao = "Sem reunião"
    if qtd_reunioes == 1:
        # a única reunião é a que qualificou o negócio
        status_reuniao = "Realizada"
    elif qtd_reunioes > 1:
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
        # Lead de empresa sem vendedor aguarda o primeiro contato
        "vendedor": vendedor if vendedor_empresa or indice_etapa > 0 else None,
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
    fantasias_usadas: set[str] = set()
    historicos: dict[str, Historico] = {}
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
