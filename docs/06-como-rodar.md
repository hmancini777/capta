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

## 3. Agendar os agentes

No Claude Code, crie duas tarefas agendadas:

| Tarefa | Horário (cron) | Prompt |
|---|---|---|
| Captação 11h | `0 11 * * 1-5` | conteúdo de `agentes/orquestrador-11h.md` |
| Respostas 17h | `0 17 * * 1-6` | conteúdo de `agentes/atendente-17h.md` |

Rode a primeira à mão uma vez para conferir que ela acha o `crm.py` e grava leads.

## 4. Primeiros dias

1. Deixe o modo em `revisao` (o padrão). Leia cada card e use **Ajustar** sem dó:
   cada nota vira regra em `regras/estilo-escrita.md`.
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
