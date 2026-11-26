# 1. Visão geral

## Para quem é

Um estúdio de vídeo que faz conteúdo de Instagram para dentistas e clínicas de
harmonização em São Paulo. O cliente ideal já posta Reels, mas com edição fraca:
acredita em vídeo e só falta acabamento e estratégia.

## O que o sistema faz, num dia normal

| Hora | Quem | O quê |
|---|---|---|
| 11h | Agente Orquestrador + Pesquisador | Lê as correções do dia anterior, acha leads novos no Google Maps e no Instagram, dá nota de 0 a 10 e escreve a 1ª mensagem de cada um. Também escreve os follow-ups que venceram. |
| 12h | Bot (automação) | Manda ao Telegram do operador um card por mensagem, com o texto pronto para copiar e os botões. |
| Ao longo do dia | Operador (humano) | Aprova, ajusta ou descarta. Envia as aprovadas e aperta Enviei. |
| Quando um lead responde | Operador → Bot | `/resp @usuario <texto>`. O follow-up é cancelado e o lead entra na fila do Atendente. |
| 17h | Agente Atendente | Escreve a resposta, o diagnóstico grátis do perfil ou o convite para reunião. Vira card. |

## As três camadas

1. **Inteligência (agentes de IA).** O que exige julgamento: decidir se um perfil
   vale a pena, entender um Reel, escrever uma mensagem que soa pessoal, responder
   uma dúvida. Está em [`agentes/`](../agentes/) e lê [`regras/`](../regras/).
2. **Automação (código sem IA).** O que é regra fixa: não contatar a mesma pessoa
   duas vezes, mandar no máximo 15 mensagens novas por dia, agendar o follow-up no
   3º dia, cancelar o follow-up se o lead respondeu. Está em [`capta/`](../capta/).
3. **Decisão (humano).** Tudo que sai para fora passa por uma pessoa. A IA nunca
   envia mensagem, nunca segue ou curte ninguém e nunca gasta dinheiro.

## Por que separar IA de automação

Se o mesmo agente pesquisasse, escrevesse, agendasse e cobrasse, uma alucinação
podia mandar o mesmo lead duas vezes ou esquecer um follow-up. Separando:

- a parte que **precisa** ser criativa fica com a IA;
- a parte que **precisa** ser exata fica com código simples, testado e previsível;
- as duas conversam só por um banco de dados, com comandos validados (`crm.py`).

O bot do Telegram, por exemplo, não chama IA nenhuma. Ele só leva botões até o
banco e manda o lote no horário. Por isso ele é barato, rápido e nunca "inventa".

## Por que o humano fica no meio

- **Qualidade:** a IA erra o tom de vez em quando. Um card ruim descartado não custa nada; uma mensagem ruim enviada queima o lead.
- **Aprendizado:** cada "Ajustar" vira uma regra escrita em `regras/estilo-escrita.md`. Com o tempo, a IA erra menos.
- **Risco:** envio automático em massa é spam, pode bloquear a conta e não respeita quem recebe.
- **Responsabilidade:** quem fala com o cliente é uma pessoa, com o nome dela.

## O que o sistema não faz (de propósito)

Não envia mensagem sozinho, não segue nem curte perfis, não coleta dado de paciente,
não usa perfil pessoal, não promete resultado. Mais em [Ética e limites](05-etica-e-limites.md).
