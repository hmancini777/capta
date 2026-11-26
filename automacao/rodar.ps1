# Roda uma tarefa do Capta com o Claude Code, sem ninguém na frente do computador.
# Quem chama este script é o Agendador de Tarefas do Windows, no horário da tarefa.
#
# Uso:  powershell -File automacao\rodar.ps1 captacao-11h
#       powershell -File automacao\rodar.ps1 respostas-17h
#
# Para agendar (uma vez só):
#   schtasks /Create /TN "Capta 11h" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 11:00 /TR "powershell -File C:\caminho\capta\automacao\rodar.ps1 captacao-11h"
#   schtasks /Create /TN "Capta 17h" /SC WEEKLY /D MON,TUE,WED,THU,FRI,SAT /ST 17:00 /TR "powershell -File C:\caminho\capta\automacao\rodar.ps1 respostas-17h"
param(
    [ValidateSet("captacao-11h", "respostas-17h")]
    [string]$Tarefa = "captacao-11h"
)

# Roda a partir da raiz do projeto: é lá que o Claude Code acha a skill e os subagentes (.claude/)
Set-Location (Split-Path -Parent $PSScriptRoot)
New-Item -ItemType Directory -Force "dados" | Out-Null

$prompt = Get-Content "automacao\$Tarefa.md" -Raw -Encoding UTF8
$inicio = Get-Date -Format "yyyy-MM-dd HH:mm"

# claude -p = modo não interativo: recebe o prompt, trabalha até o fim e imprime o resultado.
# As permissões (o que ele pode rodar sem perguntar) estão em .claude/settings.json.
$saida = claude -p $prompt --output-format text

"=== $inicio · $Tarefa ===`n$saida`n" | Out-File -Append -Encoding utf8 "dados\automacao.log"
