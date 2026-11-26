# Teste com o Claude de verdade

Este é um teste feito em 26/11/2026 com o Claude Code, na pasta do projeto, para
mostrar a skill e um subagente funcionando juntos. O lead é fictício e nada foi gravado.

## Comando

```bash
claude -p 'Use a skill capta-prospeccao para escrever a 1a mensagem de abordagem para
este lead ficticio: {"nome": "Dra. Beatriz Nunes", "instagram": "dra.beatriz.exemplo",
"bairro": "Vila Mariana", "seguidores": 2400, "pontos": 7, "sinais": "Lente de contato
dental; 2 Reels em novembro com legenda automatica", "reel": "lente de contato dental
doi?, nov/2026, 1,1 mil views"}. Depois passe o texto pelo subagente capta-revisor e use
a versao que ele devolver. NAO rode comandos e NAO grave nada no CRM. Responda so com:
(1) skill usada, (2) subagente usado e o veredito dele, (3) o texto final.'
```

## Resposta do Claude

> 1. **Skill:** `capta-prospeccao`. Usei o modelo da 1ª mensagem e as regras de
>    `referencias/estilo-escrita.md`. Também segui a correção do operador que pede para
>    falar do problema do paciente e não abrir com "gostei".
>
> 2. **Subagente:** `capta-revisor`. Veredito: **APROVADO**, sem alterações.
>
> 3. **Texto final (64 palavras):**
>
> > Boa tarde, Dra. Beatriz, tudo certo? Me chamo Henrique e trabalho com vídeo e
> > estratégia de Instagram para profissionais de saúde. Vi seu Reel sobre se lente de
> > contato dental dói, que é o medo que faz muito paciente adiar a avaliação. Fiz uma
> > análise rápida do seu perfil, com 3 pontos que seguram paciente novo e 3 ideias de
> > vídeo. Posso te mandar?

## O que o teste mostra

- **A skill foi achada e carregada sozinha**, só pelo nome e pela descrição.
- **O subagente revisor rodou** e conferiu o texto contra o checklist.
- **O sistema aprende:** o Claude aplicou uma correção que está registrada na seção
  "Correções do operador" do `estilo-escrita.md` ("não abrir com 'gostei', falar do
  problema do paciente"). Ninguém repetiu essa instrução no comando.
- A mensagem tem 64 palavras (limite: 70), cita o Reel pelo assunto, liga o tema ao
  medo do paciente e termina com pergunta.
