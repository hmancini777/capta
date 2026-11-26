# 6. Como rodar de verdade

Para só ver o sistema funcionando, a demo basta: `python demo/demo.py`.
Este guia é para ligar a versão real, com Telegram e agentes agendados.

## Requisitos

- Python 3.10 ou mais novo (nenhuma biblioteca extra).
- Uma conta no Telegram.
- [Claude Code](https://claude.com/claude-code) para rodar os agentes, com acesso ao navegador.

## 1. Criar o bot no Telegram

1. No Telegram, fale com o **@BotFather**, mande `/newbot` e siga as instruções.
2. Ele devolve um token (algo como `123456:ABC...`).
3. Copie `.env.exemplo` para `.env` e cole o token em `TELEGRAM_TOKEN`.
   O `.env` está no `.gitignore` e nunca vai para o GitHub.
4. Mande `/start` para o seu bot e rode:

```bash
python capta/bot.py parear
```

Isso grava o seu chat no `.env`. Daqui em diante o bot só obedece a você.

## 2. Testar e ligar

```bash
python capta/bot.py teste    # chega um card de teste no Telegram
python capta/bot.py rodar    # liga o bot (deixe rodando)
```

No Windows, para rodar sem janela: `pythonw capta/bot.py rodar`.

## 3. Conferir a skill e os agentes

Abra o Claude Code na pasta do projeto (`claude`) e aceite a pergunta de confiar na
pasta. Sem isso, as rodadas agendadas ignoram as permissões de `.claude/settings.json`.
O Claude Code acha sozinho a skill
`capta-prospeccao` e os subagentes em `.claude/`. Para conferir, digite `/agents`: os
três (`capta-pesquisador`, `capta-atendente`, `capta-revisor`) devem aparecer.

Para usar a skill no Claude.ai em vez do Claude Code, compacte a pasta
`.claude/skills/capta-prospeccao/` num `.zip` e envie na área de Skills das configurações.

O pesquisador usa o navegador. Para ele abrir o Maps e o Instagram, o Claude Code
precisa de uma ferramenta de navegador conectada (por exemplo, a extensão Claude in Chrome).

## 4. Agendar os agentes

| Tarefa | Horário | Prompt | Comando |
|---|---|---|---|
| Captação | dias úteis, 11h | [`automacao/captacao-11h.md`](../automacao/captacao-11h.md) | `automacao/rodar.ps1 captacao-11h` |
| Respostas | seg a sáb, 17h | [`automacao/respostas-17h.md`](../automacao/respostas-17h.md) | `automacao/rodar.ps1 respostas-17h` |

No Windows, registre no Agendador de Tarefas (os comandos `schtasks` estão no topo de
`rodar.ps1`). No Linux ou Mac, use o cron (as linhas estão no topo de `rodar.sh`).

Antes de agendar, rode uma vez à mão e confira o resultado em `dados/automacao.log`:

```bash
powershell -File automacao/rodar.ps1 captacao-11h
```

## 5. Primeiros dias

1. Deixe o modo em `revisao` (o padrão). Leia cada card e use **Ajustar** sem dó:
   cada nota vira regra no `estilo-escrita.md` da skill.
2. Quando os textos estiverem do seu jeito, mande `/modo envio`.
3. Envie, aperte **Enviei**, e use `/resp @usuario <texto>` sempre que alguém responder.
4. Para ver o funil: `/status` no Telegram ou `python capta/crm.py resumo`.

## Comandos úteis

```bash
python capta/crm.py pendentes        # o que a próxima rodada vai fazer
python capta/crm.py lote             # manda o lote agora, sem esperar as 12h
python capta/crm.py resumo           # funil em números
python -m unittest discover testes   # roda os testes
```
