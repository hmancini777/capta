# 5. Ética e limites

Um sistema de prospecção com IA pode virar uma máquina de spam com muita
facilidade. Estas são as escolhas que impedem isso, e todas estão no código ou
nos prompts, não só neste texto.

## O que o sistema não faz

| Limite | Por quê | Onde está garantido |
|---|---|---|
| Não envia mensagem sozinho | Quem fala com o cliente é uma pessoa, que responde pelo que disse | Não existe código de envio. O bot só mostra o texto e o link. |
| Não segue, curte, comenta nem vê stories | Interação automática é manipulação e bloqueia a conta | Prompts do Pesquisador e do Orquestrador |
| No máximo 15 mensagens novas por dia | Volume baixo permite mensagem pessoal e não sobrecarrega ninguém | `crm.MAX_NOVAS` |
| Nunca contata a mesma pessoa duas vezes | Respeito a quem não respondeu | `instagram UNIQUE` no banco e checagem em `novos_leads()` |
| Para depois de 2 follow-ups | Insistir mais vira incômodo | `bot.SEGUINTE` não tem passo depois do `fu2` |
| Cancela follow-up se o lead respondeu | Ninguém recebe "e aí, viu minha mensagem?" depois de já ter respondido | `crm.registrar_resposta()` |
| Não promete resultado nem número de seguidores | Seria propaganda enganosa | `regras/estilo-escrita.md` |
| Não inventa preço ou condição | O agente só usa a tabela de `regras/ofertas.md`; dúvida vai para o humano | Prompt do Atendente |
| Não convida ninguém para evento na agenda | Convite manda e-mail para fora sem aprovação | Prompt do Atendente |

## Dados pessoais (LGPD)

- **Só dado público de perfil profissional:** nome comercial, bairro, Instagram da
  clínica, telefone publicado no Google Maps. É informação que o próprio profissional
  divulga para ser contatado.
- **Nada de paciente.** O Pesquisador não abre comentários nem perfis pessoais.
- **Finalidade clara:** os dados só servem para uma abordagem comercial B2B, com
  identificação de quem está falando.
- **Fácil de sair:** quem diz "não" vira `perdido` e não recebe mais nada.
- **Este repositório não tem dado real:** os leads da demo são inventados e o banco
  de verdade fica fora do Git (`.gitignore`).

## Regras do conselho de odontologia

Os roteiros que o sistema sugere aos dentistas seguem o Código de Ética da
Odontologia (CFO): sem preço, sem "avaliação grátis" como chamariz, sem promessa
de resultado, sem antes e depois sem autorização. Ver `regras/diagnostico.md`.

## Limites técnicos honestos

- **A IA erra.** Por isso existe o modo revisão e o botão Ajustar.
- **O Instagram muda.** A pesquisa depende de páginas públicas; se o layout mudar,
  o Pesquisador pode trazer menos leads. O resto do sistema continua funcionando.
- **O operador é um gargalo, de propósito.** Se ele não abrir o Telegram, nada sai.
  Esse é o custo de não fazer spam.
- **Sem métrica de conversão automática.** O funil mostra quantos estão em cada
  etapa, mas a resposta do lead é registrada à mão (`/resp`), porque o sistema não
  lê a caixa de mensagens do Instagram.
