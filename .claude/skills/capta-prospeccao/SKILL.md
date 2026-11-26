---
name: capta-prospeccao
description: Prospecção de clientes para um estúdio de vídeo que atende dentistas e clínicas de harmonização em São Paulo. Use quando for qualificar um lead (dar nota de 0 a 10), escrever a 1ª mensagem de abordagem no Instagram ou WhatsApp, escrever follow-up, responder um lead que respondeu, montar o diagnóstico grátis do perfil (3 travas e 3 roteiros) ou falar de preço. Também use ao gravar ou ler leads no CRM do Capta (capta/crm.py). Gatilhos: "prospectar", "lead", "DM de abordagem", "follow-up", "diagnóstico do perfil", "responder o lead", "qualificar clínica".
---

# Capta · prospecção

Esta skill ensina o Claude a prospectar do jeito do estúdio: achar a clínica certa,
escrever uma mensagem que soa pessoal e nunca enviar nada sem um humano aprovar.

## Regra que vale para tudo

**Você escreve rascunhos. Quem envia é o humano.** Nunca envie mensagem, nunca siga,
curta ou comente perfis, nunca prometa resultado e nunca invente preço. Todo texto vai
para o CRM e vira um card no Telegram, onde o operador aprova, ajusta ou descarta.

## O que fazer em cada situação

| Situação | Leia antes | Entregue |
|---|---|---|
| Decidir se um perfil é bom lead | [`referencias/criterios-lead.md`](referencias/criterios-lead.md) | Nota de 0 a 10 e 1 a 3 sinais com dado concreto. Entra com 6 ou mais. |
| Escrever a 1ª mensagem | [`referencias/estilo-escrita.md`](referencias/estilo-escrita.md) | Até 70 palavras, cita um Reel real, oferece a análise grátis, termina com "Posso te mandar?" |
| Escrever follow-up | [`referencias/estilo-escrita.md`](referencias/estilo-escrita.md) | fu1 (3º dia): até 40 palavras, lembra a análise. fu2 (7º dia): leve, deixa a porta aberta. Nunca repete a 1ª. |
| Lead aceitou a análise | [`referencias/diagnostico.md`](referencias/diagnostico.md) | Resposta curta + diagnóstico: 3 travas e 3 roteiros, com dados reais do perfil. |
| Lead perguntou preço | [`referencias/ofertas.md`](referencias/ofertas.md) | Os pacotes em linguagem simples e o convite para conversa no sábado. |
| Lead disse não | — | Resposta curta e educada, sem insistir. Marcar como `perdido`. |
| Dúvida que você não sabe responder | — | Não invente. Peça ao operador: `python capta/crm.py aviso "<pergunta>"`. |

## Modelo da 1ª mensagem

> Boa tarde, Dra. [primeiro nome], tudo certo? Me chamo [operador] e trabalho com vídeo
> e estratégia de Instagram para profissionais de saúde. [Uma frase sobre um Reel real
> dela, pelo assunto, ligada à dúvida do paciente.] Fiz uma análise rápida do seu perfil,
> com 3 pontos que seguram paciente novo e 3 ideias de vídeo. Posso te mandar?

A frase do meio é o que faz a mensagem parecer escrita para aquela pessoa. Ela muda
sempre; o resto é fixo.

## Antes de entregar qualquer texto

Confira o checklist (é o mesmo que o subagente `capta-revisor` usa):

- [ ] Cumprimento com o primeiro nome.
- [ ] Cita algo real do perfil, não elogio genérico.
- [ ] Dentro do limite de palavras.
- [ ] Sem emoji, sem abreviação, sem jargão (funil, engajamento, algoritmo, autoridade).
- [ ] Não critica a edição do lead nem colegas.
- [ ] Não promete seguidor nem resultado.
- [ ] Termina com pergunta.

## Como gravar no CRM

Os comandos estão no topo de `capta/crm.py`. Os principais:

```bash
python capta/crm.py pendentes                 # a pauta: ajustes, follow-ups vencidos, respostas
python capta/crm.py novos-leads leads.json    # grava leads novos com a 1ª mensagem
python capta/crm.py mensagem msg.json         # follow-up, resposta ou diagnóstico
```

Formato de um lead novo:

```json
[{"nome": "Dra. Camila Rocha", "instagram": "dra.camila.exemplo", "bairro": "Moema",
  "seguidores": 3200, "pontos": 8, "sinais": "3 Reels em outubro, legenda automática...",
  "mensagem": {"canal": "instagram", "texto": "Boa tarde, Dra. Camila...",
               "contexto": "Reel citado: clareamento (out/2026, 2,1 mil views)"}}]
```

## Quando o operador corrige

Se `pendentes` trouxer itens em "ajustar", a nota do operador manda: reescreva seguindo
a nota e grave com `"substitui": <msg_id>`. Depois acrescente a correção, com data, em
"Correções do operador" de `referencias/estilo-escrita.md`. Se a mesma correção aparecer
duas vezes, suba para a seção "Regras". É assim que a skill aprende com o uso.
