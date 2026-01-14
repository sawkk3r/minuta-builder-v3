#!/bin/bash
# ============================================================================
# Script para executar o servidor com ambiente virtual ativado
# ============================================================================

# Obter o diretório do script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Ativar ambiente virtual
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Ambiente virtual não encontrado!"
    echo "Execute primeiro: ./setup.sh"
    exit 1
fi

# Executar o servidor
echo "🚀 Iniciando servidor..."
cd backend
python api.py
