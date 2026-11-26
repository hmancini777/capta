# 3. A automação

Automação aqui é tudo que segue **regra fixa** e por isso não precisa de IA.
Está em [`capta/bot.py`](../capta/bot.py) e [`capta/crm.py`](../capta/crm.py),
em Python puro, sem nenhuma biblioteca externa.

## O que roda sozinho

| Gatilho | O que acontece | Onde no código |
|---|---|---|
| Dia útil, 11h | Tarefa agendada acorda o Agente Orquestrador | `agentes/orquestrador-11h.md` (cron `0 11 * * 1-5`) |
| Dia útil, entre 12h e 18h, uma vez | Bot manda o lote de cards | `bot.relogio()` → `crm.lote()` |
| Botão "Enviei" na 1ª mensagem | Lead vira "enviado"; follow-up 1 agendado para daqui a 3 dias | `bot.sincronizar()`, tabela `SEGUINTE` |
| Botão "Enviei" no follow-up 1 | Follow-up 2 agendado para mais 4 dias (7º dia) | `bot.sincronizar()` |
| Botão "Enviei" no follow-up 2 | Para de insistir | `bot.sincronizar()` |
| `/resp @usuario` | Follow-ups pendentes cancelados; lead vai para a fila do Atendente | `crm.registrar_resposta()` |
| Resposta a um card com texto | A nota é salva e a mensagem volta para reescrita | `bot.tratar_mensagem()` |
| Texto solto no chat | Vira "recado" para o agente ler na próxima rodada | `bot.tratar_mensagem()` |
| Lead novo com @ que já existe | Recusado, nunca recebe 2ª abordagem | `crm.novos_leads()` |
| Seg a sáb, 17h | Tarefa agendada acorda o Agente Atendente | `agentes/atendente-17h.md` |

## Os cards

Um card é uma mensagem no Telegram com o texto que a IA escreveu e botões embaixo.

```
┌──────────────────────────────────────────────
│ Mensagem nova 1/3 · Dra. Camila Rocha
│
│ @dra.camila.exemplo · Moema · 3.200 seguidores · 8/10
│ Reel citado: clareamento (out/2026, 2,1 mil views)
│
│ Boa tarde, Dra. Camila, tudo certo? Me chamo ...
│ [Aprovar]  [Ajustar]  [Descartar]
│ <Abrir a DM>  <Ver o perfil>
└──────────────────────────────────────────────
```

- O texto vem num bloco que, no celular, se copia com um toque.
- "Abrir a DM" abre a conversa do Instagram direto (ou o WhatsApp com o texto já colado).
- Depois do clique, os botões somem e aparece "Aprovado às 12:41", para não clicar duas vezes.

## Os dois modos

| Modo | Botões | Para quê |
|---|---|---|
| `revisao` (padrão) | Aprovar, Ajustar, Descartar | Fase de calibrar: o operador lê tudo e corrige o estilo da IA. Não conta no limite diário. |
| `envio` | Enviei, Pular, Ajustar, Descartar | Fase de operação: o operador envia e confirma. Máximo de 15 novas por dia. |

Troca com `/modo envio` ou `/modo revisao` no chat.

## A ordem do lote

1. Respostas e diagnósticos (lead quente, sai na hora e não conta no limite).
2. Follow-ups vencidos.
3. Mensagens novas: primeiro as já aprovadas, depois as de maior pontuação.

## Por que o bot não usa IA

- **Custo:** o bot fica ligado o dia todo. Chamar IA a cada clique seria caro e lento.
- **Previsibilidade:** "Enviei agenda o follow-up para daqui a 3 dias" é uma regra.
  Código faz isso igual todas as vezes; um modelo de linguagem pode variar.
- **Teste:** dá para provar que a regra funciona. Ver [`testes/`](../testes/).

## Proteções

- **Trava de instância:** só um bot por vez (porta 47613). Dois bots brigariam pelas mensagens.
- **Só o dono:** o bot só obedece ao chat pareado (`TELEGRAM_CHAT_ID`).
- **Idempotência:** apertar o mesmo botão duas vezes não agenda dois follow-ups.
- **Lote uma vez por dia:** a data do último lote fica no banco (`estado.lote_dia`) e é gravada antes de mandar.
