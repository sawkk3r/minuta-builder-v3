#!/bin/bash
# ============================================================================
# TRE-GO Minuta Builder - Setup Script
# ============================================================================

set -e

echo "🏛️ TRE-GO Minuta Builder - Setup"
echo "================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar Python
echo "📋 Verificando requisitos..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado. Instale o Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✅ Python $PYTHON_VERSION encontrado${NC}"

# Criar ambiente virtual
if [ ! -d "venv" ]; then
    echo ""
    echo "🐍 Criando ambiente virtual..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Ambiente virtual criado${NC}"
fi

# Ativar ambiente
echo ""
echo "🔄 Ativando ambiente virtual..."
source venv/bin/activate

# Instalar dependências
echo ""
echo "📦 Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

# Verificar instalação do Agno
echo ""
echo "🤖 Verificando Agno..."
if python3 -c "import agno" 2>/dev/null; then
    echo -e "${GREEN}✅ Agno instalado corretamente${NC}"
else
    echo -e "${YELLOW}⚠️ Instalando Agno com extras...${NC}"
    pip install "agno[openai,lancedb]"
fi

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Criando arquivo .env..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️ IMPORTANTE: Edite o arquivo .env e adicione sua OPENAI_API_KEY${NC}"
fi

# Criar diretórios necessários
echo ""
echo "📁 Criando diretórios..."
mkdir -p tmp exports logs files/regulamentos/alteracoes_menores

# Verificar arquivos de regulamento
echo ""
echo "📄 Verificando arquivos de regulamento..."
FILES_COUNT=$(ls -1 files/regulamentos/*.pdf 2>/dev/null | wc -l || echo "0")
if [ "$FILES_COUNT" -eq "0" ]; then
    echo -e "${YELLOW}⚠️ Nenhum PDF encontrado em files/regulamentos/${NC}"
    echo "   Adicione os PDFs dos regulamentos para usar o Knowledge Base"
else
    echo -e "${GREEN}✅ $FILES_COUNT arquivos PDF encontrados${NC}"
fi

# Resumo
echo ""
echo "================================="
echo -e "${GREEN}✅ Setup concluído!${NC}"
echo ""
echo "📋 Próximos passos:"
echo ""
echo "1. Configure a API key no .env:"
echo "   ${YELLOW}nano .env${NC}"
echo ""
echo "2. Adicione os PDFs em files/regulamentos/"
echo ""
echo "3. Inicie o servidor:"
echo "   ${YELLOW}cd backend && python api.py${NC}"
echo ""
echo "4. Abra o frontend:"
echo "   ${YELLOW}open frontend/index.html${NC}"
echo ""
echo "5. (Opcional) Indexar documentos:"
echo "   ${YELLOW}curl -X POST http://localhost:8000/knowledge/indexar${NC}"
echo ""
