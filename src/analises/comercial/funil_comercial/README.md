# Funil comercial

## Pergunta de negócio

> O comercial está melhor ou pior que em 2025? Em qual etapa do funil perdemos negócios, por quê, e o que esperar do Q4?

## Cenário

Empresa B2B de software de gestão para PMEs. No fechamento de setembro de 2026, o diretor comercial compara o ano
com 2025 e decide onde agir no Q4 e no planejamento de 2027.

Etapas do funil: Lead → Qualificado → Proposta → Negociação → Ganho ou Perdido.

## Como executar

Na raiz do projeto:

```sh
uv run python src/analises/comercial/funil_comercial/gerar_dados.py
uv run python src/analises/comercial/funil_comercial/gerar_grafico.py
```

`gerar_dados.py` simula os negócios (código em `simulacao/`) e salva `dados/negocios.csv`. `gerar_grafico.py` lê o CSV
com Polars e salva um gráfico HTML por pergunta em `graficos/` (código em `geradores/`).
