# ============================================================================
# VANDA Chatbot - Dockerfile per Google Cloud Run
# ============================================================================
#
# Build:
#   docker build -t vanda-chatbot .
#
# Run locale:
#   docker run -p 8080:8080 --env-file .env vanda-chatbot
#
# Deploy Cloud Run:
#   gcloud run deploy vanda-chatbot --source .
#
# ============================================================================

# Base image: Python 3.11 slim (leggera, ottimizzata)
FROM python:3.11-slim

# Metadata
LABEL maintainer="VANDA Designers"
LABEL description="RAG Chatbot for Vanda Designers - Interior Design"
LABEL version="1.0.0"

# Variabili di build
ARG DEBIAN_FRONTEND=noninteractive

# ============================================================================
# SYSTEM DEPENDENCIES
# ============================================================================

# Update system e installa dipendenze minime
RUN apt-get update && apt-get install -y \
    # Build essentials per alcune librerie Python
    gcc \
    g++ \
    # Cleanup per ridurre dimensione immagine
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# PYTHON ENVIRONMENT
# ============================================================================

# Set working directory
WORKDIR /app

# Copia requirements PRIMA del resto (per layer caching Docker)
# Se requirements.txt non cambia, Docker riusa la cache
COPY requirements.txt .

# Installa dipendenze Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# APPLICATION CODE
# ============================================================================

# Copia tutto il codice dell'applicazione
COPY . .

# ============================================================================
# RUNTIME CONFIGURATION
# ============================================================================

# Espone porta 8080 (standard Cloud Run)
EXPOSE 8080

# Variabili ambiente per Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# User non-root per sicurezza (best practice)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# ============================================================================
# STARTUP COMMAND
# ============================================================================

# Comando di avvio
# Cloud Run passa automaticamente PORT env var, default 8080
CMD exec uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --workers 1 \
    --log-level info \
    --no-access-log
