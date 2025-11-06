# Dockerfile for Vanda Chatbot Admin Panel (Streamlit)
# Build context must be project root: vanda-chatbot/
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl for healthcheck
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy parent app directory (needed for config_service)
COPY app /app/app

# Copy admin files
COPY admin/requirements.txt .
COPY admin/app.py .
COPY admin/.streamlit /app/.streamlit

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
