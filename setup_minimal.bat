@echo off
echo ============================================================================
echo VANDA CHATBOT - Setup MINIMO (solo dipendenze essenziali)
echo ============================================================================
echo.

echo Questo script installa SOLO le dipendenze essenziali per i test RAG
echo.

echo [1/4] Aggiornamento pip, setuptools, wheel...
python -m pip install --upgrade pip setuptools wheel
echo.

echo [2/4] Installazione FastAPI e Uvicorn...
python -m pip install fastapi==0.104.1 uvicorn[standard]==0.24.0
echo.

echo [3/4] Installazione OpenAI e Supabase...
python -m pip install openai==1.3.0 supabase==2.0.3
echo.

echo [4/4] Installazione utilities...
python -m pip install python-dotenv==1.0.0 pydantic==2.4.2 pydantic-settings==2.0.3 numpy==1.24.3 loguru==0.7.2 httpx==0.25.0
echo.

echo ============================================================================
echo Setup minimo completato!
echo ============================================================================
echo.
echo Puoi ora testare:
echo   python test_rag_simple.py
echo.
pause
