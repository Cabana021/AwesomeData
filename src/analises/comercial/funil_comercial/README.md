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
- **Volume:** mensal, com sazonalidade de fim de trimestre. Em 2026, cada mês cresce entre 15% e 35%
  sobre o mesmo mês de 2025.
- **Semente fixa:** a execução é reproduzível.

| Grupo         | Colunas                                                                                                                                    |
|---------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| Identificação | `id`, `nome_negocio`, `empresa`                                                                                                            |
| Contato       | `nome_contato`, `cargo_contato` (Sócio, Diretor, Gerente, Analista), `email_contato`, `celular_contato`                                    |
| Empresa       | `segmento`, `porte`, `uf`                                                                                                                  |
| Classificação | `tipo_negocio` (Novo, Expansão, Reativação), `plano` (Starter, Pro, Enterprise)                                                            |
| Origem        | `canal_origem` (Indicação, Site, Mídia paga, Evento, Outbound, Base de clientes), `campanha_origem`                                        |
| Responsáveis  | `sdr`, `vendedor`                                                                                                                          |
| Situação      | `etapa_atual`, `status` (Aberto, Ganho, Perdido)                                                                                           |
| Valores       | `valor_estimado`, `desconto_percentual`, `valor_fechado`                                                                                   |
| Datas         | `data_criacao`, `data_entrada_qualificado`, `data_entrada_proposta`, `data_entrada_negociacao`, `data_fechamento`, `data_ultima_atividade` |
| Atividade     | `foi_contatado`, `qtd_reunioes`, `status_ultima_reuniao` (Realizada, Agendada, Não compareceu, Sem reunião)                                |
| Perda         | `motivo_perda` (Preço, Concorrente, Sem orçamento, Sem retorno, Fora do perfil, Timing)                                                    |

Regras dos dados:

- **Vazios:** só onde não se aplicam: datas de etapas não atingidas, `desconto_percentual` antes de Proposta,
  `valor_fechado` fora dos ganhos, `motivo_perda` fora dos perdidos e `vendedor` no Lead de empresa sem vendedor ainda.
- **Etapa:** `etapa_atual` é a última etapa atingida, inclusive nos fechados.
- **Tipo de negócio:** Novo cria a empresa. Expansão vem de cliente cujo último negócio foi ganho há 30 dias ou mais,
  em plano acima do ganho e no canal Base de clientes, então Enterprise e o maior plano do porte não recebem Expansão.
  Reativação vem de empresa que nunca foi cliente e cujo último negócio foi perdido há 90 dias ou mais. Empresa com
  negócio em curso não recebe outro.
- **Empresa:** o porte Micro não contrata Enterprise. O nome-fantasia é único, com dois sobrenomes. ME e EI só aparecem
  em Varejo, Serviços e Logística, e S/A só no porte Média. O contato é fixo, com e-mail no domínio da empresa (nas
  Micro, parte usa provedor gratuito), celular com o DDD da `uf` e cargo que tende a Sócio nos portes menores.
- **Valores:** `valor_estimado` e `valor_fechado` são o valor anual do contrato (primeiro ano), em reais, com 2 casas.
  O `valor_estimado` vem de uma tabela de preços por plano e porte, sem sobreposição entre planos. O ticket maior da
  Indicação vem do mix, com mais Pro e Enterprise.
- **Ciclo:** os prazos entre etapas e até o fechamento crescem com o plano (Enterprise é o mais lento) e têm cauda longa.
- **Abertos:** a maioria teve atividade nos últimos 30 dias. Cerca de 10% estão parados há mais de 30 dias.
- **Vendedor:** entra a partir de Qualificado, e a empresa o mantém em todos os negócios seguintes.
- **Contato e reunião:** o Lead não tem reunião (`qtd_reunioes` 0, status "Sem reunião"). De Qualificado em diante há
  contato e ao menos uma reunião Realizada. A quantidade de reuniões cresce com o plano e a etapa. A chance de contato
  do Lead varia por canal: alta em Indicação e Outbound, baixa em Mídia paga e Evento.
- **Motivo de perda:** Lead sem contato perde só por Fora do perfil. Lead contatado perde por Sem orçamento, Sem retorno
  ou Timing. Preço e Concorrente só aparecem de Qualificado em diante. A Expansão tem sempre contato e nunca perde por
  Fora do perfil.

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
