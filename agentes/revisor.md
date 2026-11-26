---
agente: Revisor (duas camadas)
quando: antes de qualquer mensagem virar card, e depois no Telegram
camada 1: checklist automático aplicado pela IA
camada 2: o humano, que aprova, ajusta ou descarta cada card
---

# Revisor

## Camada 1: checklist da IA

Antes de gravar uma mensagem, o agente confere:

- [ ] Começa com cumprimento e o primeiro nome do lead.
- [ ] Cita algo real do perfil (um Reel pelo assunto), não um elogio genérico.
- [ ] Até 70 palavras na 1ª mensagem, até 90 nas respostas.
- [ ] Sem emoji, sem abreviação (vc, pq), sem jargão de marketing (funil, engajamento, algoritmo).
- [ ] Não critica a edição do lead nem colegas dele.
- [ ] Não promete número de seguidores nem resultado.
- [ ] Termina com pergunta.
- [ ] Não soa como texto de robô: sem frases de efeito vazias, sem "não é só X, é Y",
      sem três adjetivos em fila.

## Camada 2: o humano

Cada mensagem vira um card no Telegram. O operador tem quatro saídas:

| Botão | O que acontece |
|---|---|
| Aprovar | A mensagem entra no próximo lote de envio. |
| Ajustar | O operador responde o card com uma nota. Na próxima rodada o agente reescreve, e a nota vira regra de estilo. |
| Descartar | A mensagem e o lead saem do funil. |
| Enviei | O operador mandou de verdade. O sistema agenda o follow-up. |

## Por que duas camadas

A IA erra de um jeito previsível (tom genérico, elogio vazio). O checklist pega
esses erros baratos. O humano pega o resto: o que só quem conhece o negócio sabe.
E cada ajuste do humano melhora o checklist, então o sistema aprende com o uso.
