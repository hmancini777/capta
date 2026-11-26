# Glossário

| Termo | O que é |
|---|---|
| **Agente** | Um modelo de IA que recebe um objetivo, regras e ferramentas, e executa a tarefa inteira sozinho, decidindo os passos. |
| **Orquestrador** | O agente que coordena os outros: divide o trabalho, junta os resultados e entrega. |
| **Subagente** | Um agente chamado por outro para uma parte da tarefa (aqui, o Pesquisador). |
| **Prompt** | O texto de instruções que o agente recebe. Os prompts do Capta estão em `agentes/`. |
| **Automação** | Código que executa uma regra fixa, sem IA. Ex.: "Enviei agenda o follow-up para daqui a 3 dias". |
| **Tarefa agendada / cron** | Um programa que roda sozinho num horário. `0 11 * * 1-5` = 11h, de segunda a sexta. |
| **Lead** | Um potencial cliente. Aqui, um dentista ou clínica que se encaixa nos critérios. |
| **Qualificar** | Conferir se o lead vale a pena, com critérios objetivos e uma nota. |
| **CRM** | *Customer Relationship Management*: o registro de cada lead e de cada contato com ele. |
| **Funil** | As etapas pelas quais um lead passa, de "achado" a "cliente". Cada etapa tem menos gente que a anterior. |
| **Estágio** | A etapa do funil em que o lead está agora (`enviado`, `respondeu`, `reuniao`...). |
| **DM** | *Direct message*: mensagem privada no Instagram. `dm1` é a primeira mensagem. |
| **Follow-up** | Mensagem de lembrete para quem não respondeu. Aqui são dois: no 3º e no 7º dia. |
| **Isca** | Algo de valor oferecido de graça para começar a conversa. Aqui, o diagnóstico do perfil. |
| **Diagnóstico** | Análise grátis do perfil do lead: 3 pontos que seguram paciente novo e 3 roteiros de vídeo. |
| **Card** | Mensagem no Telegram com o texto que a IA escreveu e botões para o humano decidir. |
| **Lote** | O conjunto de cards mandados de uma vez, ao meio-dia. |
| **Modo revisão / envio** | Revisão: o humano só aprova ou corrige o texto. Envio: o humano envia e confirma. |
| **Human-in-the-loop** | Desenho em que um humano aprova as decisões importantes da IA antes de elas terem efeito. |
| **Idempotente** | Que pode rodar duas vezes sem dar resultado diferente. Apertar Enviei duas vezes não agenda dois follow-ups. |
| **SQLite** | Banco de dados que fica num único arquivo, sem servidor. |
| **Inbound** | Lead que chegou sozinho, sem ter sido abordado. |
