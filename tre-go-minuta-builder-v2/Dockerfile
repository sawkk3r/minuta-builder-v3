# ============================================================================
# Dockerfile para TRE-GO Minuta Builder v2.0
# ============================================================================

FROM python:3.12-slim

# Metadados
LABEL maintainer="TRE-GO TI"
LABEL description="Sistema colaborativo para construção da Minuta V2 do Regulamento Interno do TRE-GO"

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro (cache layer)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar código da aplicação
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY files/ ./files/

# Criar diretórios necessários
RUN mkdir -p tmp exports logs

# Variáveis de ambiente padrão (podem ser sobrescritas)
ENV API_HOST=0.0.0.0 \
    API_PORT=8000 \
    PYTHONPATH=/app \
    SERVE_FRONTEND=true \
    ENVIRONMENT=production

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/status')" || exit 1

# Comando para iniciar a aplicação
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
