# Funil comercial

## Pergunta de negócio

> O comercial está melhor ou pior que em 2025? Em qual etapa do funil perdemos negócios, por quê, e o que esperar do Q4?

## Cenário

Empresa B2B de software de gestão para PMEs. No fechamento de setembro de 2026, o diretor comercial compara o ano
com 2025 e decide onde agir no Q4 e no planejamento de 2027.

Etapas do funil: Lead → Qualificado → Proposta → Negociação → Ganho ou Perdido.

## Dados simulados

`gerar_dados.py` cria `dados/negocios.csv`, no formato de uma exportação de CRM: uma linha por negócio, UTF-8,
datas em ISO e valores em reais.

- **Período:** negócios criados em 2025 e, em 2026, até 30/09. Volume e conversão comparam jan–set dos dois anos.
  Os criados de out a dez/2025 dão a receita realizada do Q4 de 2025.
- **Carga inicial:** os criados de out a dez/2024 só dão receita a janeiro de 2025 e ficam fora de volume e conversão.
- **Corte:** o que não fechou até 30/09/2026 segue com status Aberto.
- **Calendário:** todas as datas caem em dias úteis.
- **Volume:** mensal, com sazonalidade de fim de trimestre.
- **Semente fixa:** a execução é reproduzível.

| Grupo         | Colunas                                                                                                                                    |
|---------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| Identificação | `id`, `nome_negocio`, `empresa`                                                                                                            |
| Contato       | `nome_contato`, `cargo_contato` (Sócio, Diretor, Gerente, Analista), `email_contato`, `celular_contato`                                    |
| Empresa       | `segmento`, `porte`, `uf`                                                                                                                  |
| Classificação | `tipo_negocio` (Novo, Expansão, Reativação), `plano` (Starter, Pro, Enterprise)                                                            |
| Origem        | `canal_origem` (Indicação, Site, Mídia paga, Evento, Outbound), `campanha_origem`                                                          |
| Responsáveis  | `sdr`, `vendedor`                                                                                                                          |
| Situação      | `etapa_atual`, `status` (Aberto, Ganho, Perdido)                                                                                           |
| Valores       | `valor_estimado`, `desconto_percentual`, `valor_fechado`                                                                                   |
| Datas         | `data_criacao`, `data_entrada_qualificado`, `data_entrada_proposta`, `data_entrada_negociacao`, `data_fechamento`, `data_ultima_atividade` |
| Atividade     | `foi_contatado`, `qtd_reunioes`, `status_ultima_reuniao` (Realizada, Agendada, Não compareceu, Sem reunião)                                |
| Perda         | `motivo_perda` (Preço, Concorrente, Sem orçamento, Sem retorno, Fora do perfil, Timing)                                                    |

Regras dos dados:

- Campos ficam vazios apenas quando não se aplicam: datas de etapas não atingidas, `desconto_percentual` antes de
  Proposta, `valor_fechado` fora dos ganhos e `motivo_perda` fora dos perdidos.
- `id` é único e não sequencial. A empresa é identificada pelo nome.
- `etapa_atual` traz a última etapa atingida, inclusive nos fechados.
- `tipo_negocio` segue o histórico da empresa: Novo cria a empresa, Expansão vem de empresa com ganho anterior e
  Reativação, de empresa cujo último negócio foi perdido há algum tempo. Empresa com negócio em curso não recebe outro.
- Cada empresa tem um contato fixo. O e-mail usa o domínio da empresa, o celular traz o DDD da `uf` e o cargo tende a
  Sócio nos portes menores.
- `foi_contatado` é falso apenas para o negócio que ficou em Lead e sem reunião.
- Preço e Concorrente só aparecem como `motivo_perda` de Qualificado em diante.
- O porte Micro não contrata o plano Enterprise.

## Métricas

| Métrica             | Definição                                                                       |
|---------------------|---------------------------------------------------------------------------------|
| Receita             | Soma de `valor_fechado` dos ganhos, por mês de `data_fechamento`.               |
| Negócios criados    | Contagem por mês de `data_criacao`.                                             |
| Conversão           | Ganhos ÷ (ganhos + perdidos), na corte de criação. Negócios abertos ficam fora. |
| Ticket médio        | Receita ÷ ganhos.                                                               |
| Conversão por etapa | Percentual que atingiu a etapa seguinte, entre os negócios fechados da corte.   |
| Tempo por etapa     | Mediana de dias entre as datas de entrada.                                      |
| YtD                 | Acumulado de janeiro até o mês, comparando 2025 e 2026 no mesmo período.        |
| Previsão do Q4      | `valor_estimado` dos abertos por etapa × taxa de ganho da etapa no YtD de 2026. |

## Perguntas e gráficos

`gerar_grafico.py` salva um gráfico Plotly em HTML por pergunta, em `graficos/`. O título de cada gráfico traz a
conclusão, calculada a partir dos dados.

| # | Pergunta                            | Gráfico                                                |
|---|-------------------------------------|--------------------------------------------------------|
| 1 | Estamos melhor ou pior que 2025?    | Receita mensal e acumulada YtD, 2025 × 2026.           |
| 2 | O que explica a diferença?          | Variação % de volume, conversão e ticket médio no YtD. |
| 3 | Em qual etapa a conversão mudou?    | Conversão etapa a etapa, 2025 × 2026.                  |
| 4 | Quais canais e vendedores mudaram?  | Conversão e receita por canal e por vendedor.          |
| 5 | Por que perdemos?                   | Motivos de perda, 2025 × 2026.                         |
| 6 | O que esperar do Q4?                | Pipeline aberto por etapa, bruto e ponderado.          |

## História esperada

Mais volume, menos eficiência.

- Os negócios criados crescem em 2026.
- A conversão cai, concentrada em Proposta → Negociação.
- Evento cresce em volume, converte mal e perde por preço.
- Indicação converte melhor e tem ticket maior.
- Um vendedor concentra a piora.
- A receita cresce no YtD, mas menos que o volume.
- O pipeline ponderado cobre apenas parte da receita do Q4 de 2025.

## Como executar

Na raiz do projeto:

```sh
uv run python src/analises/comercial/funil_comercial/gerar_dados.py
uv run python src/analises/comercial/funil_comercial/analisar.py
uv run python src/analises/comercial/funil_comercial/gerar_grafico.py
```

`analisar.py` lê `dados/negocios.csv` com Polars e salva as tabelas de cada pergunta em `saidas/`.
