# ============================================================
# PROCESSAR TRANSCRIÇÃO FACTORIAL
# ============================================================
# Coloque este arquivo na pasta do cliente e execute:
# .\processar-transcricao-simples.ps1
#
# Ou passe o arquivo como parâmetro:
# .\processar-transcricao-simples.ps1 "transcricao.txt"
# ============================================================

$scriptPython = "C:\Users\victo\SEGLife\Novo Projeto\mcp_tarefas_factorial.py"

# Se passou arquivo como parâmetro
if ($args.Count -gt 0) {
    $arquivo = $args[0]
} else {
    # Procura .txt na pasta atual
    $txtFiles = Get-ChildItem -Path . -Filter "*.txt"
    if ($txtFiles.Count -eq 0) {
        Write-Host "❌ Nenhum arquivo .txt na pasta atual!" -ForegroundColor Red
        Write-Host "   Use: .\processar-transcricao-simples.ps1 'arquivo.txt'" -ForegroundColor Yellow
        exit 1
    }
    $arquivo = $txtFiles[0].FullName
    if ($txtFiles.Count -gt 1) {
        Write-Host "⚠️  Usando: $(Split-Path $arquivo -Leaf)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "🚀 Processando transcrição..." -ForegroundColor Green
Write-Host ""

python $scriptPython $arquivo

