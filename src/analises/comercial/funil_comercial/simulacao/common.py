from datetime import date

DATA_CORTE = date(2026, 9, 30)
MESES_POR_ANO = {2024: range(1, 13), 2025: range(1, 13), 2026: range(1, 10)}
# variação mensal sobre o volume base
RUIDO_VOLUME = 0.08
# crescimento de cada mês de 2026 sobre o mesmo mês de 2025
CRESCIMENTO_VOLUME_2026 = (1.15, 1.35)

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
# um negócio atrasado pode levar até esse múltiplo do prazo máximo da etapa
FATOR_ATRASO_MAXIMO = 2
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
DIAS_REATIVACAO = 90
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
SUFIXOS_MEDIA = ("Ltda.", "S/A")
PESOS_SUFIXOS_MEDIA = (90, 10)
PROBABILIDADE_EMAIL_GRATUITO = 0.3
DOMINIOS_GRATUITOS = ("gmail.com", "outlook.com", "hotmail.com", "yahoo.com.br")
QTD_SDRS = 3
QTD_VENDEDORES = 6
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

# mínimo e máximo de reuniões por plano (Starter, Pro, Enterprise) e etapa atingida
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
