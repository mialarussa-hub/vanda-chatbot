@echo off
REM ============================================================================
REM VANDA Chatbot - Deploy Script per Google Cloud Run
REM ============================================================================
REM Uso: deploy.bat
REM ============================================================================

echo ================================================================================
echo VANDA CHATBOT - DEPLOY SU GOOGLE CLOUD RUN
echo ================================================================================
echo.

REM Verifica gcloud installato
echo Verifica Google Cloud SDK...
where gcloud >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] gcloud non trovato!
    echo.
    echo Installa Google Cloud SDK da:
    echo https://cloud.google.com/sdk/docs/install
    echo.
    pause
    exit /b 1
)

echo [OK] gcloud trovato
echo.

REM Verifica progetto configurato
echo Verifica progetto Google Cloud...
for /f "tokens=*" %%i in ('gcloud config get-value project 2^>nul') do set PROJECT=%%i
if "%PROJECT%"=="" (
    echo [ERRORE] Nessun progetto configurato!
    echo.
    echo Configura progetto con:
    echo   gcloud config set project TUO_PROJECT_ID
    echo.
    pause
    exit /b 1
)

echo [OK] Progetto: %PROJECT%
echo.

REM Conferma deploy
echo Stai per deployare su:
echo   Progetto: %PROJECT%
echo   Regione: europe-west1
echo   Servizio: vanda-chatbot
echo.
set /p CONFIRM="Continuare? (s/n): "
if /i not "%CONFIRM%"=="s" (
    echo Deploy annullato.
    pause
    exit /b 0
)
echo.

REM Deploy
echo ================================================================================
echo AVVIO DEPLOY...
echo ================================================================================
echo.
echo Questo richiedera 3-5 minuti...
echo.

gcloud run deploy vanda-chatbot ^
  --source . ^
  --platform managed ^
  --region europe-west1 ^
  --allow-unauthenticated ^
  --memory 1Gi ^
  --cpu 1 ^
  --timeout 60s ^
  --max-instances 10 ^
  --min-instances 0 ^
  --set-env-vars "ENV=production,LOG_LEVEL=INFO,SUPABASE_TABLE_NAME=documents,RAG_DEFAULT_MATCH_COUNT=3,RAG_DEFAULT_MATCH_THRESHOLD=0.60,LLM_DEFAULT_MODEL=gpt-4o-mini,LLM_DEFAULT_TEMPERATURE=0.5,LLM_MAX_TOKENS=500,LLM_STREAM_ENABLED=true" ^
  --set-secrets "OPENAI_API_KEY=openai-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================================
    echo [OK] DEPLOY COMPLETATO CON SUCCESSO!
    echo ================================================================================
    echo.

    REM Ottieni URL servizio
    echo Recupero URL servizio...
    for /f "tokens=*" %%i in ('gcloud run services describe vanda-chatbot --region europe-west1 --format="value(status.url)" 2^>nul') do set SERVICE_URL=%%i

    if not "%SERVICE_URL%"=="" (
        echo.
        echo Service URL:
        echo   %SERVICE_URL%
        echo.
        echo Test rapido:
        echo   curl %SERVICE_URL%/health
        echo.
        echo Test chat:
        echo   curl -X POST "%SERVICE_URL%/api/chat" -H "Content-Type: application/json" -d "{\"message\":\"Ciao!\",\"stream\":false}"
        echo.
        echo Docs:
        echo   %SERVICE_URL%/docs
        echo.
    )
) else (
    echo.
    echo ================================================================================
    echo [ERRORE] DEPLOY FALLITO
    echo ================================================================================
    echo.
    echo Verifica:
    echo   1. Secrets configurati: gcloud secrets list
    echo   2. APIs abilitate: gcloud services list --enabled
    echo   3. Permessi: gcloud projects get-iam-policy %PROJECT%
    echo.
)

pause
