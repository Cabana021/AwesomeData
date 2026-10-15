from datetime import date, timedelta
from random import Random
from typing import Any

from faker import Faker
from simulacao.common import (
    CANAIS,
    CANAL_EXPANSAO,
    DATA_CORTE,
    DESCONTOS,
    DIAS_MINIMOS_PARADO,
    DIAS_SEM_ATIVIDADE_ABERTO,
    ETAPAS,
    FATOR_ATRASO_MAXIMO,
    FATOR_VENDEDOR_EM_QUEDA,
    FATORES_PRAZO_PLANO,
    INDICE_VENDEDOR_EM_QUEDA,
    JANELA_PARADOS,
    MOTIVOS_PERDA,
    NOMES_PLANOS,
    PESOS_CANAIS,
    PESOS_DESCONTOS,
    PESOS_MOTIVOS,
    PESOS_MOTIVOS_EVENTO,
    PESOS_MOTIVOS_LEAD,
    PESOS_MOTIVOS_SEM_CONTATO,
    PESOS_STATUS_REUNIAO,
    PRAZO_GANHO,
    PRAZO_PERDA,
    PRAZOS_ETAPA,
    PRECOS,
    PROBABILIDADE_LEAD_QUALIFICADO,
    PROBABILIDADE_NEGOCIACAO_GANHO,
    PROBABILIDADE_PARADO,
    PROBABILIDADE_PROPOSTA_NEGOCIACAO,
    PROBABILIDADE_QUALIFICADO_PROPOSTA,
    REUNIOES_PLANO_ETAPA,
    STATUS_REUNIAO,
)
from simulacao.empresas import Empresa, Historico, qtd_planos


def proximo_dia_util(dia: date) -> date:
    while dia.weekday() >= 5:
        dia += timedelta(days=1)
    return dia


def sortear_prazo(rng: Random, prazo: tuple[int, int], fator: float) -> int:
    minimo, maximo = prazo
    moda = (minimo + maximo) / 2
    return round(rng.triangular(minimo, maximo * FATOR_ATRASO_MAXIMO, moda) * fator)


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
