# ============================================================================
# VANDA Chatbot - Deploy Script per Google Cloud Run
# ============================================================================
# Uso: .\deploy.ps1
# ============================================================================

Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "VANDA CHATBOT - DEPLOY SU GOOGLE CLOUD RUN" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Verifica gcloud installato
Write-Host "Verifica Google Cloud SDK..." -ForegroundColor Yellow
try {
    $gcloudVersion = gcloud --version 2>&1 | Select-Object -First 1
    Write-Host "✓ gcloud trovato: $gcloudVersion" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "✗ gcloud non trovato!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installa Google Cloud SDK da:" -ForegroundColor Yellow
    Write-Host "https://cloud.google.com/sdk/docs/install" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

# Verifica progetto configurato
Write-Host "Verifica progetto Google Cloud..." -ForegroundColor Yellow
$project = gcloud config get-value project 2>$null
if (-not $project) {
    Write-Host "✗ Nessun progetto configurato!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Configura progetto con:" -ForegroundColor Yellow
    Write-Host "  gcloud config set project TUO_PROJECT_ID" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}
Write-Host "✓ Progetto: $project" -ForegroundColor Green
Write-Host ""

# Conferma deploy
Write-Host "Stai per deployare su:" -ForegroundColor Yellow
Write-Host "  Progetto: $project" -ForegroundColor White
Write-Host "  Regione: europe-west1" -ForegroundColor White
Write-Host "  Servizio: vanda-chatbot" -ForegroundColor White
Write-Host ""
$confirm = Read-Host "Continuare? (s/n)"
if ($confirm -ne "s" -and $confirm -ne "S") {
    Write-Host "Deploy annullato." -ForegroundColor Yellow
    exit 0
}
Write-Host ""

# Deploy
Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "AVVIO DEPLOY..." -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

Write-Host "Questo richiederà 3-5 minuti..." -ForegroundColor Yellow
Write-Host ""

# Comando deploy
$deployCommand = @"
gcloud run deploy vanda-chatbot `
  --source . `
  --platform managed `
  --region europe-west1 `
  --allow-unauthenticated `
  --memory 1Gi `
  --cpu 1 `
  --timeout 60s `
  --max-instances 10 `
  --min-instances 0 `
  --set-env-vars "ENV=production,LOG_LEVEL=INFO,SUPABASE_TABLE_NAME=documents,RAG_DEFAULT_MATCH_COUNT=3,RAG_DEFAULT_MATCH_THRESHOLD=0.60,LLM_DEFAULT_MODEL=gpt-4o-mini,LLM_DEFAULT_TEMPERATURE=0.5,LLM_MAX_TOKENS=500,LLM_STREAM_ENABLED=true,ALLOWED_ORIGINS=[`"https://www.agentika.io`",`"https://agentika.io`",`"http://localhost:3000`"]" `
  --set-secrets "OPENAI_API_KEY=openai-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest"
"@

# Esegui deploy
Invoke-Expression $deployCommand

# Check risultato
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=" -ForegroundColor Green -NoNewline
    Write-Host ("=" * 79) -ForegroundColor Green
    Write-Host "✓ DEPLOY COMPLETATO CON SUCCESSO!" -ForegroundColor Green
    Write-Host ("=" * 80) -ForegroundColor Green
    Write-Host ""

    # Ottieni URL servizio
    Write-Host "Recupero URL servizio..." -ForegroundColor Yellow
    $serviceUrl = gcloud run services describe vanda-chatbot --region europe-west1 --format="value(status.url)" 2>$null

    if ($serviceUrl) {
        Write-Host ""
        Write-Host "Service URL:" -ForegroundColor Cyan
        Write-Host "  $serviceUrl" -ForegroundColor White
        Write-Host ""

        Write-Host "Test rapido:" -ForegroundColor Cyan
        Write-Host "  curl $serviceUrl/health" -ForegroundColor White
        Write-Host ""

        Write-Host "Test chat:" -ForegroundColor Cyan
        Write-Host "  curl -X POST `"$serviceUrl/api/chat`" -H `"Content-Type: application/json`" -d '{`"message`":`"Ciao!`",`"stream`":false}'" -ForegroundColor White
        Write-Host ""
    }

    Write-Host "Docs:" -ForegroundColor Cyan
    Write-Host "  $serviceUrl/docs" -ForegroundColor White
    Write-Host ""

} else {
    Write-Host ""
    Write-Host "=" -ForegroundColor Red -NoNewline
    Write-Host ("=" * 79) -ForegroundColor Red
    Write-Host "✗ DEPLOY FALLITO" -ForegroundColor Red
    Write-Host ("=" * 80) -ForegroundColor Red
    Write-Host ""
    Write-Host "Verifica:" -ForegroundColor Yellow
    Write-Host "  1. Secrets configurati: gcloud secrets list" -ForegroundColor White
    Write-Host "  2. APIs abilitate: gcloud services list --enabled" -ForegroundColor White
    Write-Host "  3. Permessi: gcloud projects get-iam-policy $project" -ForegroundColor White
    Write-Host ""
    exit 1
}
