---
description: Registra o handoff da sessão em handoffs/HANDOFF.md para outra sessão continuar o trabalho. Use ao encerrar uma sessão, trocar de contexto ou quando o usuário pedir handoff.
argument-hint: "[informação a adicionar]"
disable-model-invocation: true
---

## Estado do repositório

```!
git status --short
git log -5 --oneline
```

## Instruções

Arquivo de destino: `handoffs/HANDOFF.md`. Escreva em pt-BR, com frases curtas e sem informação que o código ou o git já registram.

**Sem argumento** (`$ARGUMENTS` vazio): sobrescreva o arquivo com o resumo da sessão, usando as seções:

- **Objetivo:** o que a sessão buscava.
- **Feito:** o que foi concluído, com caminhos de arquivos.
- **Decisões:** escolhas do usuário e o motivo.
- **Pendências:** o que ficou em aberto ou falhou.
- **Próximos passos:** o que fazer primeiro na próxima sessão.
- **Como executar:** comandos para rodar e validar.

**Com argumento**: não sobrescreva. 
Leia o arquivo e acrescente `$ARGUMENTS` na seção mais adequada, ou em uma seção **Adições** no fim, com a data. 
Se o arquivo não existir, crie-o e avise.

Ao terminar, informe apenas o caminho do arquivo e se ele foi sobrescrito ou atualizado e com a mensagem abaixo:

`Leia handoffs/HANDOFF.md e entenda o que foi feito a partir deste documento.`
