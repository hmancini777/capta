---
tarefa: Respostas 17h
horario: segunda a sábado às 17h (cron "0 17 * * 1-6")
roda_com: automacao/rodar.ps1 respostas-17h  (Windows)  ou  automacao/rodar.sh respostas-17h  (Linux/Mac)
---

Rodada curta do Capta, só para lead que respondeu. Chame o subagente
**`capta-atendente`** e deixe que ele cuide de tudo. Ele lê `crm.py pendentes`,
escreve as respostas e os diagnósticos como rascunho e manda os cards na hora.

Você nunca envia mensagem para lead. Termine com o resumo de 2 linhas que o
atendente devolver.
