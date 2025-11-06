@echo off
echo ============================================================================
echo VANDA CHATBOT - Setup e Installazione Dipendenze
echo ============================================================================
echo.

echo [1/5] Verifica Python...
python --version
if errorlevel 1 (
    echo ERRORE: Python non trovato! Installa Python 3.11+ da python.org
    pause
    exit /b 1
)
echo.

echo [2/5] Aggiornamento pip...
python -m pip install --upgrade pip
echo.

echo [3/5] Aggiornamento setuptools e wheel (risolve problemi compatibilita)...
python -m pip install --upgrade setuptools wheel
echo.

echo [4/5] Installazione dipendenze critiche...
python -m pip install fastapi uvicorn python-dotenv pydantic pydantic-settings
if errorlevel 1 (
    echo ERRORE: Installazione dipendenze base fallita!
    pause
    exit /b 1
)
echo.

echo [5/5] Installazione dipendenze complete da requirements.txt...
pip install -r requirements.txt
echo.

if errorlevel 1 (
    echo.
    echo ============================================================================
    echo ATTENZIONE: Alcune dipendenze potrebbero aver dato errore
    echo ============================================================================
    echo.
    echo Possibili cause:
    echo   - Python 3.14 e troppo recente (alcuni pacchetti non compatibili)
    echo   - Connessione internet instabile
    echo.
    echo SOLUZIONE 1: Installa manualmente le dipendenze essenziali
    echo   python -m pip install openai supabase numpy loguru httpx
    echo.
    echo SOLUZIONE 2: Usa Python 3.11 o 3.12 (piu stabili)
    echo   Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ============================================================================
    echo Setup completato con successo!
    echo ============================================================================
    echo.
    echo Puoi ora eseguire i test:
    echo   python test_rag_simple.py
    echo   python test_rag_detailed.py
    echo.
    echo Oppure avviare il server FastAPI:
    echo   uvicorn app.main:app --reload
    echo.
    pause
)
