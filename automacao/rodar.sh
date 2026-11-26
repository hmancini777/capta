#!/usr/bin/env bash
# Roda uma tarefa do Capta com o Claude Code, sem ninguém na frente do computador.
# Quem chama este script é o cron, no horário da tarefa.
#
# Uso:  ./automacao/rodar.sh captacao-11h
#       ./automacao/rodar.sh respostas-17h
#
# Para agendar, rode "crontab -e" e acrescente:
#   0 11 * * 1-5  /caminho/capta/automacao/rodar.sh captacao-11h
#   0 17 * * 1-6  /caminho/capta/automacao/rodar.sh respostas-17h
set -euo pipefail

TAREFA="${1:-captacao-11h}"
case "$TAREFA" in
  captacao-11h|respostas-17h) ;;
  *) echo "Tarefa desconhecida: $TAREFA" >&2; exit 1 ;;
esac

# Roda a partir da raiz do projeto: é lá que o Claude Code acha a skill e os subagentes (.claude/)
cd "$(dirname "$0")/.."
mkdir -p dados

INICIO="$(date '+%Y-%m-%d %H:%M')"
# claude -p = modo não interativo. As permissões estão em .claude/settings.json.
SAIDA="$(claude -p "$(cat "automacao/$TAREFA.md")" --output-format text)"

printf '=== %s · %s ===\n%s\n\n' "$INICIO" "$TAREFA" "$SAIDA" >> dados/automacao.log
