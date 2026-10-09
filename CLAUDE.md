# Awesome Data

## Sobre o projeto

AwesomeData é um projeto de portfólio que simula rotinas operacionais do dia a dia corporativo com Python.

- Demonstre ganhos práticos com pequenas automações.
- Implemente apenas o necessário para o case. Não amplie o escopo sem solicitação.
- Prefira código curto, direto e legível. Não reduza linhas à custa da clareza.
- Não adicione abstrações, camadas ou dependências sem necessidade concreta do case.
- Não trate casos extremos fora do cenário simulado.
- Não crie testes unitários, salvo solicitação explícita.

## Stack

- **Linguagem:** Python >= 3.13.
- **Manipulação e análise de dados:** `polars>=1.44.2`.
- **Visualização de dados:** `matplotlib>=3.11.2` e `plotly>=7.1.0`.
- **Geração de dados:** `faker>=40.39.0`.
- **Geração de planilhas Excel:** `xlsxwriter>=3.2.9`.
- **Logs:** `loguru` para registrar eventos e erros durante a execução.
- **Qualidade de código:** `ruff>=0.16.9` para lint e formatação; `mypy>=2.3.1` para verificação estática de tipos;
  `pre-commit` para executar verificações automáticas antes dos commits.

## Quality gates

- Após toda e qualquer alteração em código, execute obrigatoriamente os comandos abaixo na raiz do projeto.
- Corrija todos os achados de tipagem, lint e formatação e execute novamente todos os comandos após as correções.
- Não ignore achados nem desative verificações para obter aprovação.
- Só conclua a tarefa quando todos os comandos terminarem com sucesso e não houver achados pendentes.

```sh
uv run mypy .
uv run ruff check .
uv run ruff format --check .
```

## Documentação

- Use a documentação oficial como fonte principal para APIs e configurações.
- Confirme a compatibilidade dos exemplos com a versão utilizada no projeto.
- Consulte a referência em caso de dúvida. Não presuma nomes de métodos, parâmetros ou comportamentos.

Referências por categoria:

- **Linguagem:** [Python](https://docs.python.org/3/tutorial/index.html).
- **Manipulação e análise de dados:** [Polars — guia](https://docs.pola.rs/) e
  [referência da API Python](https://docs.pola.rs/api/python/stable/reference/index.html).
- **Visualização de dados:** [Matplotlib](https://matplotlib.org/stable/index.html) e
  [Plotly](https://plotly.com/python/).
- **Geração de dados:** [Faker](https://faker.readthedocs.io/en/master/).
- **Geração de planilhas Excel:** [XlsxWriter](https://xlsxwriter.readthedocs.io/).
- **Logs:** [Loguru](https://loguru.readthedocs.io/en/stable/).
- **Qualidade de código:** [Ruff](https://docs.astral.sh/ruff/),
  [mypy](https://mypy.readthedocs.io/en/stable/) e [pre-commit](https://pre-commit.com/).

## Linguagem

- Escreva sempre em pt-BR. Preserve nomes técnicos, identificadores e comandos.
- Use UTF-8 em todos os arquivos de texto criados ou editados.
- Vá direto ao ponto: informe o problema ou a situação, a solução e como executar.
- Use frases curtas e inclua apenas informações necessárias à tarefa.
- Não use elogios, introduções genéricas, repetições, divagações ou conclusões redundantes.
- Só detalhe conceitos e alternativas quando solicitado ou necessário para a execução.
