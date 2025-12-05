# Script para sincronizar automaticamente com GitHub
# Execute após gerar o relatório

Write-Host "🔄 Sincronizando com GitHub..." -ForegroundColor Cyan

# Copiar o relatório para index.html
Copy-Item "Relatorio_Folha_Pagamento.html" "index.html" -Force
Write-Host "✅ Arquivo copiado para index.html" -ForegroundColor Green

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
