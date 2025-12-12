# Script para sincronizar automaticamente com GitHub
# Execute após gerar o relatório

Write-Host "🔄 Sincronizando com GitHub..." -ForegroundColor Cyan

# Verificar se index.html existe
if (-Not (Test-Path "index.html")) {
    Write-Host "❌ Arquivo index.html não encontrado! Execute gerar_relatorio.py primeiro." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Arquivo index.html encontrado" -ForegroundColor Green

# Adicionar ao Git
git add index.html
Write-Host "✅ Arquivo adicionado ao Git" -ForegroundColor Green

# Fazer commit com data/hora
$dataHora = Get-Date -Format "dd/MM/yyyy HH:mm:ss"
git commit -m "Atualização automática - $dataHora"
Write-Host "✅ Commit realizado" -ForegroundColor Green

# Enviar para GitHub
git push origin main
Write-Host "🚀 Enviado para GitHub!" -ForegroundColor Green
Write-Host "🌐 Acesse: https://pablogusen.github.io/folha_sgp/" -ForegroundColor Yellow
