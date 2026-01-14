# 🏛️ TRE-GO Minuta Builder v2.0

Sistema colaborativo para construção da Minuta V2 do Regulamento Interno do Tribunal Regional Eleitoral de Goiás.

## ⚠️ Requisitos do Sistema

- **Python**: 3.10, 3.11 ou 3.12 (recomendado)
- **⚠️ NÃO use Python 3.13** - pode ter incompatibilidades com algumas dependências
- **Ambiente Virtual**: Sempre use um venv para isolar as dependências

## ✨ Funcionalidades

- **🤖 Agentes Especializados**: Consulte especialistas em cada versão do regulamento (1997, 2007, 2017, Alterações, Minuta V2)
- **🤝 Comunicação Colaborativa**: Agentes podem ver e responder às respostas uns dos outros, permitindo análises mais ricas e complementares
- **📚 Knowledge Base com RAG**: Busca semântica nos documentos originais (PDFs) usando LanceDB
- **🧠 Team Coordenador**: Consolidação inteligente de análises com GPT-5.2 (reasoning) e coordenação de conversas entre agentes
- **💾 Sessões Persistentes**: Histórico completo de interações com SQLite
- **📄 Exportação**: Markdown e documentos consolidados no formato de regulamento
- **🌐 Deploy Online**: Pronto para deploy na internet (Render, Railway, Fly.io, etc.)

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (HTML/JS)                       │
│                    WebSocket + REST API                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Session   │  │   Agents    │  │    Knowledge        │  │
│  │   Manager   │  │   Manager   │  │    Manager          │  │
│  │  (SQLite)   │  │  (Agno)     │  │  (LanceDB + Agno)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      OpenAI API                              │
│  • gpt-5-mini-2025-08-07 (Agentes - econômico)             │
│  • gpt-5.2-2025-12-11 (Team Coordenador - reasoning)       │
│  • text-embedding-3-small (Embeddings)                      │
└─────────────────────────────────────────────────────────────┘
```

## 🌐 Deploy Online (Novo!)

O sistema está pronto para deploy na internet! Seus colegas podem usar o MVP online.

**📖 Guias de Deploy:**
- **Deploy Rápido (5 minutos)**: Veja [`DEPLOY_RAPIDO.md`](DEPLOY_RAPIDO.md)
- **Guia Completo**: Veja [`DEPLOY.md`](DEPLOY.md) com todas as opções

**Opções disponíveis:**
- ✅ **Render.com** (recomendado - grátis)
- ✅ **Railway.app** (fácil - $5 grátis/mês)
- ✅ **Fly.io** (rápido - plano gratuito)
- ✅ **Docker Compose** (VPS próprio)

**Recursos incluídos:**
- ✅ Dockerfile pronto para produção
- ✅ Frontend detecta automaticamente a URL da API
- ✅ Configuração de variáveis de ambiente
- ✅ Health checks e monitoramento
- ✅ **Segurança**: Swagger desabilitado em produção, autenticação para endpoints administrativos

**🔒 Segurança:**
- **Guia de Segurança**: Veja [`SEGURANCA.md`](SEGURANCA.md) para proteger sua aplicação
- Swagger desabilitado em produção por padrão
- Autenticação básica para endpoints de indexação
- CORS configurável

---

## 🚀 Instalação Local

### 1. Clonar e configurar ambiente

```bash
# Clonar repositório (se necessário)
# git clone https://github.com/sawkk3r/rev_reg_int_tre.git
cd rev_reg_int_tre/tre-go-minuta-builder-v2

# IMPORTANTE: Verificar versão do Python (recomendado: Python 3.10-3.12)
# ⚠️ ATENÇÃO: Use "python3" (sem espaço), não "python 3"!
python3 --version  # ou: python --version

# Criar ambiente virtual
# Use python3 explicitamente para evitar conflitos
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Verificar que está usando o Python do venv (deve mostrar caminho com /venv/)
which python  # Linux/Mac
# ou: where python  # Windows

# Atualizar pip
pip install --upgrade pip

# Instalar dependências
pip install -r requirements.txt

# Verificar instalação (testar imports críticos)
python -c "import pandas, fastapi, agno; print('✅ Dependências instaladas corretamente!')"
```

### 2. Configurar variáveis de ambiente

```bash
# Copiar arquivo de exemplo
#cp .env.example .env

# Editar com sua API key
#nano .env  # ou use seu editor preferido
```

**Configurações importantes no `.env`:**

```env
# OBRIGATÓRIO
OPENAI_API_KEY=sk-sua-chave-aqui

# Modelos (opcional - defaults razoáveis)
MODEL_AGENTES=gpt-5-mini-2025-08-07       # Econômico para agentes
MODEL_COORDENADOR=gpt-5.2-2025-12-11        # Poderoso para consolidação (com reasoning)
EMBEDDING_MODEL=text-embedding-3-small

# Segurança (OBRIGATÓRIO em produção)
ADMIN_USERNAME=seu-usuario-forte          # Para proteger endpoints administrativos
ADMIN_PASSWORD=sua-senha-muito-forte      # Mínimo 16 caracteres recomendado
ALLOWED_ORIGINS=https://seu-dominio.com   # Origens permitidas (não use * em produção)
DISABLE_DOCS_IN_PRODUCTION=true           # Desabilitar Swagger em produção (padrão: true)
```

**⚠️ IMPORTANTE - Segurança:**
- Configure `ADMIN_USERNAME` e `ADMIN_PASSWORD` fortes em produção
- Não use `ALLOWED_ORIGINS=*` em produção
- Veja [`SEGURANCA.md`](SEGURANCA.md) para mais detalhes

### 3. Adicionar documentos

Coloque os PDFs dos regulamentos na pasta `files/regulamentos/`:

```
files/regulamentos/
├── 1997_Resolucao_05.pdf      # Nome específico (veja abaixo)
├── 2007_Resolucao_113.pdf     # Nome específico
├── 2017_Resolucao_275.pdf     # Nome específico
├── Minuta_V2.pdf              # Nome específico
└── alteracoes_menores/
    ├── Res_349_2021.pdf       # Qualquer nome funciona!
    ├── Res_405_2024.pdf       # Qualquer nome funciona!
    ├── Res_432_2025.pdf       # Qualquer nome funciona!
    └── qualquer_nome.pdf      # ✅ Também funciona!
```

**📋 Regras de nomenclatura:**

1. **Arquivos principais** (1997, 2007, 2017, Minuta V2):
   - Devem ter os nomes exatos listados acima
   - O sistema procura por esses nomes específicos
   - Extensões `.pdf` ou `.txt` são aceitas

2. **Arquivos de alterações** (`alteracoes_menores/`):
   - ✅ **Qualquer nomenclatura funciona!**
   - O sistema busca automaticamente **TODOS** os arquivos `.pdf` e `.txt` neste diretório
   - Você pode adicionar novos arquivos sem precisar alterar o código
   - Exemplos que funcionam: `Res_500_2025.pdf`, `nova_resolucao.pdf`, `alteracao_2025.txt`

**🔄 Indexação:**

- ⚡ **Servidor inicia rapidamente**: A indexação automática foi desabilitada no startup para inicialização rápida
- ✅ **Verificação rápida**: O servidor verifica apenas se as tabelas têm dados (sem processar arquivos)
- 📋 **Status claro**: Você verá quais knowledge bases precisam ser indexadas nos logs
- 🔧 **Indexação manual**: Execute a indexação quando necessário (veja seção "Atualizando Arquivos" abaixo)

### 4. Indexar documentos (primeira vez ou após alterações)

⚠️ **IMPORTANTE**: Após adicionar ou modificar arquivos, você precisa indexá-los para que os agentes possam acessá-los.

#### Primeira vez (indexação inicial)

Na primeira vez ou se você deletou os bancos de dados em `tmp/`, execute:

**🌐 Para produção (deploy online):**

Se você fez deploy na internet (Render, Railway, etc.), use uma das opções abaixo:

**Opção 1: Via Swagger (Recomendado - Mais fácil)** ✨

1. Acesse a documentação da API: `https://sua-url.onrender.com/docs`
2. Procure pelo endpoint: `POST /knowledge/indexar`
3. Clique em "Try it out"
4. Configure os parâmetros:
   - `force`: `true` (para forçar reindexação completa)
   - `versao`: deixe vazio (para indexar todas) ou especifique uma versão
5. Clique em "Execute"
6. Aguarde a resposta confirmando que a indexação foi iniciada

**Opção 2: Via PowerShell (Windows)**

```powershell
# Indexar todas as versões
Invoke-RestMethod -Uri "https://sua-url.onrender.com/knowledge/indexar?force=true" -Method POST

# OU indexar apenas uma versão específica
Invoke-RestMethod -Uri "https://sua-url.onrender.com/knowledge/indexar?versao=minuta&force=true" -Method POST
Invoke-RestMethod -Uri "https://sua-url.onrender.com/knowledge/indexar?versao=2017&force=true" -Method POST
```

**Opção 3: Via Terminal Linux/Mac ou Git Bash (Windows)**

```bash
# Indexar todas as versões
curl -X POST "https://sua-url.onrender.com/knowledge/indexar?force=true"

# OU indexar apenas uma versão específica
curl -X POST "https://sua-url.onrender.com/knowledge/indexar?versao=minuta&force=true"
curl -X POST "https://sua-url.onrender.com/knowledge/indexar?versao=2017&force=true"
```

**💻 Para desenvolvimento local:**

```bash
# Indexar todas as versões
curl -X POST "http://localhost:8000/knowledge/indexar?force=true"

# OU indexar apenas uma versão específica
curl -X POST "http://localhost:8000/knowledge/indexar?versao=minuta&force=true"
curl -X POST "http://localhost:8000/knowledge/indexar?versao=2017&force=true"
# etc...
```

**📊 Verificar status da indexação:**

Após iniciar a indexação, você pode verificar o status:

```bash
# Via Swagger: GET /knowledge/status
# Via PowerShell:
Invoke-RestMethod -Uri "https://sua-url.onrender.com/knowledge/status" -Method GET
# Via curl:
curl "https://sua-url.onrender.com/knowledge/status"
```

#### Após modificar arquivos

Quando você editar, modificar ou atualizar qualquer arquivo, use o endpoint de atualização:

```bash
# Atualizar versão específica após editar arquivos
curl -X POST "http://localhost:8000/knowledge/atualizar?versao=<versao>"
```

**Exemplos práticos:**

| Você editou... | Comando para atualizar |
|----------------|------------------------|
| `minuta.txt` ou `minuta.pdf` | `curl -X POST "http://localhost:8000/knowledge/atualizar?versao=minuta"` |
| `2017_Resolucao_275.txt` | `curl -X POST "http://localhost:8000/knowledge/atualizar?versao=2017"` |
| `1997_Resolucao_05.pdf` | `curl -X POST "http://localhost:8000/knowledge/atualizar?versao=1997"` |
| Qualquer PDF em `alteracoes_menores/` | `curl -X POST "http://localhost:8000/knowledge/atualizar?versao=alteracoes"` |

**Mapeamento de versões:**

| Parâmetro `versao` | Arquivos afetados |
|--------------------|-------------------|
| `1997` | `1997_Resolucao_05.txt`, `1997_Resolucao_05.pdf` |
| `2007` | `2007_Resolucao_113.txt`, `2007_Resolucao_113.pdf` |
| `2017` | `2017_Resolucao_275.txt`, `2017_Resolucao_275.pdf` |
| `alteracoes` | Todos os arquivos em `alteracoes_menores/` |
| `minuta` | `minuta.txt`, `minuta.pdf` |

**💡 Dica**: Você também pode usar o navegador acessando:
- `http://localhost:8000/knowledge/atualizar?versao=minuta` (POST)

**⏱️ Tempo de indexação:**
- Arquivo pequeno (< 10 páginas): ~10-30 segundos
- Arquivo médio (10-50 páginas): ~1-3 minutos
- Arquivo grande (50+ páginas): ~3-10 minutos

A indexação acontece em background - o servidor continua respondendo normalmente!

### 5. Iniciar o servidor backend

⚠️ **IMPORTANTE**: Certifique-se de que o ambiente virtual está ativado antes de iniciar o servidor!

```bash
# Opção 1: Usar o script de execução (recomendado)
# Na raiz do projeto (tre-go-minuta-builder-v2)
./run.sh

# Opção 2: Ativar venv manualmente
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Verificar que está usando o Python correto
which python  # Deve mostrar: .../tre-go-minuta-builder-v2/venv/bin/python

# Entrar na pasta backend e executar
cd backend
python api.py

# Ou com uvicorn diretamente
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

⏳ **Aguarde a inicialização completa!** O servidor precisa:
1. ✅ Inicializar o Knowledge Manager
2. ✅ Verificar status das knowledge bases (verificação rápida)
3. ✅ Inicializar os Agentes
4. ✅ Carregar as sessões existentes

**Você saberá que está pronto quando ver:**
```
✅ API pronta para receber requisições!
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 6. Abrir o frontend

⚠️ **IMPORTANTE**: Só abra o frontend **APÓS** ver a mensagem "✅ API pronta para receber requisições!"

```bash
# Opção 1: Python (servidor HTTP local)
cd frontend
python -m http.server 3000

# Depois acesse no navegador:
# http://localhost:3000

# Opção 2: Abrir diretamente (mais simples)
open frontend/index.html  # Mac
start frontend/index.html  # Windows
# ou simplesmente arraste o arquivo index.html para o navegador
```

**Nota**: Se você abrir o frontend antes do backend estar pronto, pode ver erros de conexão. Basta aguardar o backend inicializar e recarregar a página do frontend (F5).

## 📝 Atualizando Arquivos

### Quando você precisa atualizar a indexação

Você precisa reindexar quando:
- ✅ **Primeira vez usando o sistema** (ainda não há embeddings)
- ✅ **Você modificou/editar qualquer arquivo** (minuta.txt, PDFs, etc.)
- ✅ **Você adicionou novos arquivos** (ex: novo PDF em alteracoes_menores/)
- ✅ **Você deletou os bancos** em `tmp/` (reconstrução completa)

### Como atualizar

#### Opção 1: Endpoint de atualização (recomendado) ✨

Use este endpoint quando você **editou** arquivos e precisa atualizar a indexação:

```bash
curl -X POST "http://localhost:8000/knowledge/atualizar?versao=<versao>"
```

**Exemplos práticos:**

| Você editou | Comando |
|-------------|---------|
| `minuta.txt` ou `minuta.pdf` | `curl -X POST "http://localhost:8000/knowledge/atualizar?versao=minuta"` |
| `2017_Resolucao_275.txt` | `curl -X POST "http://localhost:8000/knowledge/atualizar?versao=2017"` |
| `2007_Resolucao_113.pdf` | `curl -X POST "http://localhost:8000/knowledge/atualizar?versao=2007"` |
| `1997_Resolucao_05.txt` | `curl -X POST "http://localhost:8000/knowledge/atualizar?versao=1997"` |
| Qualquer arquivo em `alteracoes_menores/` | `curl -X POST "http://localhost:8000/knowledge/atualizar?versao=alteracoes"` |

#### Opção 2: Endpoint genérico com force

Para forçar reindexação completa:

```bash
# Indexar uma versão específica
curl -X POST "http://localhost:8000/knowledge/indexar?versao=minuta&force=true"

# Indexar todas as versões
curl -X POST "http://localhost:8000/knowledge/indexar?force=true"
```

### Mapeamento completo de versões

| Parâmetro `versao` | Descrição | Arquivos afetados |
|--------------------|-----------|-------------------|
| `1997` | Resolução 05/1997 (Original) | `1997_Resolucao_05.txt`, `1997_Resolucao_05.pdf` |
| `2007` | Resolução 113/2007 | `2007_Resolucao_113.txt`, `2007_Resolucao_113.pdf` |
| `2017` | Resolução 275/2017 (Vigente) | `2017_Resolucao_275.txt`, `2017_Resolucao_275.pdf` |
| `alteracoes` | Alterações 2021-2025 | Todos os arquivos em `alteracoes_menores/` |
| `minuta` | Minuta V2 (Em construção) | `minuta.txt`, `minuta.pdf` |

### Fluxo completo de atualização

**Exemplo: Você editou `minuta.txt`**

1. **Edite o arquivo**:
   ```bash
   nano files/regulamentos/minuta.txt
   # Faça suas alterações e salve
   ```

2. **Atualize a indexação**:
   ```bash
   curl -X POST "http://localhost:8000/knowledge/atualizar?versao=minuta"
   ```

3. **Aguarde alguns segundos/minutos** (veja os logs do servidor):
   ```
   📄 Indexando documentos para: Minuta V2
   📥 Processando: minuta.txt (forçado)
   ✅ minuta.txt processado e indexado com sucesso
   Indexação concluída: {'minuta': True}
   ```

4. **Teste o Agente #5** - ele agora terá acesso às informações atualizadas!

### Tempo estimado de indexação

| Tamanho do arquivo | Tempo estimado |
|-------------------|----------------|
| Pequeno (< 10 páginas) | 10-30 segundos |
| Médio (10-50 páginas) | 1-3 minutos |
| Grande (50+ páginas) | 3-10 minutos |

**Nota**: A indexação acontece em **background** - o servidor continua respondendo normalmente durante o processo!

### Verificar status da indexação

**💻 Para desenvolvimento local:**

```bash
# Ver status de todas as knowledge bases
curl http://localhost:8000/knowledge/status

# Ver status geral do sistema
curl http://localhost:8000/status
```

**🌐 Para produção (deploy online):**

**Via Swagger (Recomendado):**
1. Acesse: `https://sua-url.onrender.com/docs`
2. Procure por: `GET /knowledge/status` ou `GET /status`
3. Clique em "Try it out" → "Execute"

**Via PowerShell (Windows):**
```powershell
# Status das knowledge bases
Invoke-RestMethod -Uri "https://sua-url.onrender.com/knowledge/status" -Method GET

# Status geral do sistema
Invoke-RestMethod -Uri "https://sua-url.onrender.com/status" -Method GET
```

**Via Terminal Linux/Mac ou Git Bash:**
```bash
# Status das knowledge bases
curl "https://sua-url.onrender.com/knowledge/status"

# Status geral do sistema
curl "https://sua-url.onrender.com/status"
```

## 📖 Como Usar

### 1. Criar Sessão

1. Preencha o **Artigo** (ex: "Art. 47") e **Título** (ex: "Competências do Gabinete")
2. Clique em **Criar Sessão**
3. O WebSocket será conectado automaticamente

### 2. Consultar Agentes

Existem **três modos** de consulta:

#### 📝 Modo Individual (Padrão)

1. Selecione um agente clicando no card correspondente
2. Digite sua pergunta no campo de chat
3. Pressione Enter ou clique no botão de enviar
4. O agente **verá automaticamente** as respostas anteriores de outros agentes da sessão antes de responder
5. Isso permite que ele complemente, corrija ou confirme informações já ditas

**Exemplo:**
```
Você consulta Agente #1 (1997) → Resposta sobre Art. 47
Depois consulta Agente #2 (2017) → Ele já vê a resposta do Agente #1 e pode comentar sobre as diferenças
```

#### 🤝 Modo Colaborativo (Nova funcionalidade)

1. Digite sua pergunta no campo de chat
2. Clique no botão **"🤝 Consultar Todos (Colaborativo)"**
3. Todos os agentes serão consultados **em sequência**
4. Cada agente **vê as respostas dos anteriores** antes de responder
5. Isso cria uma "conversa" entre agentes onde eles podem:
   - Complementar informações
   - Corrigir inconsistências
   - Confirmar pontos importantes
   - Identificar divergências entre versões

**Exemplo:**
```
Pergunta: "Quais são as competências do Gabinete?"

Agente #1 (1997) responde primeiro
  ↓
Agente #2 (2007) vê resposta do #1 e comenta as mudanças
  ↓
Agente #3 (2017) vê ambas respostas e destaca o que está vigente
  ↓
Agente #4 (Alterações) complementa com alterações recentes
  ↓
Agente #5 (Minuta) propõe melhorias baseado em todas as versões anteriores
```

#### 🧠 Consolidação com Team Coordenador

O Team Coordenador também usa modo colaborativo automaticamente:
1. Após consultar múltiplos agentes, clique em **"🧠 Consolidar com Team"**
2. O Team Coordenador:
   - Coordena uma conversa entre os agentes (eles veem respostas uns dos outros)
   - Sintetiza todas as respostas
   - Identifica gaps entre versões
   - Detecta inconsistências ou contradições
   - Propõe texto consolidado

### 3. Exportar Resultados

- **Exportar Markdown**: Gera arquivo com histórico completo
- **Gerar Documento**: Cria documento no formato de regulamento

## 🔧 API Endpoints

### REST

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Info da API |
| `/status` | GET | Status completo |
| `/sessao/criar` | POST | Criar sessão |
| `/sessao/{id}` | GET | Obter sessão |
| `/sessao/{id}/exportar` | GET | Exportar Markdown |
| `/sessao/{id}/documento-consolidado` | GET | Gerar documento |
| `/sessoes` | GET | Listar sessões |
| `/agentes` | GET | Status dos agentes |
| `/agente/consultar` | POST | Consultar agente |
| `/knowledge/status` | GET | Status do knowledge |
| `/knowledge/indexar` | POST | Indexar documentos |
| `/knowledge/atualizar` | POST | Atualizar versão específica após editar arquivos |
| `/knowledge/buscar` | GET | Busca semântica em uma base |

### WebSocket

Conectar em: `ws://localhost:8000/ws/{session_id}`

**Ações disponíveis:**

```javascript
// Consultar agente individual (com contexto automático de outras respostas)
{ "acao": "consultar_agente", "agente": "1997", "pergunta": "..." }

// Consulta colaborativa (todos os agentes em sequência, vendo respostas anteriores)
{ "acao": "consultar_colaborativo", "pergunta": "...", "versoes": ["1997", "2017", "minuta"] }

// Consolidar com Team Coordenador (usando modo colaborativo)
{ "acao": "consolidar", "tema": "Art. 47", "versoes": ["1997", "2007", "2017"] }

// Finalizar sessão
{ "acao": "finalizar", "texto_final": "...", "observacoes": "..." }
```

**Nota sobre comunicação entre agentes:**
- No modo **individual**: Cada agente vê automaticamente todas as respostas anteriores de outros agentes da sessão
- No modo **colaborativo**: Os agentes são consultados em sequência, e cada um vê as respostas dos anteriores
- No modo **consolidação**: O Team Agno coordena a conversa com `show_members_responses=True`, permitindo que os membros vejam respostas uns dos outros durante a execução do Team

## 📊 Estrutura do Projeto

```
tre-go-minuta-builder/
├── backend/
│   ├── __init__.py
│   ├── api.py              # FastAPI + WebSockets
│   ├── models.py           # Modelos Pydantic
│   ├── agents.py           # Agentes Agno + Team
│   ├── knowledge_manager.py # Knowledge + LanceDB
│   └── session_manager.py  # Sessões + SQLite
│
├── frontend/
│   └── index.html          # Interface web
│
├── files/
│   └── regulamentos/       # PDFs dos regulamentos
│
├── tmp/                    # Databases (gerado)
├── exports/                # Arquivos exportados
├── logs/                   # Logs (opcional)
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 💰 Estimativa de Custos

| Operação | Custo Estimado |
|----------|----------------|
| Consulta individual a 1 agente | ~$0.01 |
| Consulta colaborativa (5 agentes) | ~$0.06 (contexto adicional aumenta um pouco) |
| Consolidação com Team (colaborativo) | ~$0.12 |
| **Total por artigo** | **~$0.19** |
| **Minuta completa (80 artigos)** | **~$15** |

**Nota**: O modo colaborativo pode ter um custo ligeiramente maior porque cada agente recebe mais contexto (respostas dos outros agentes), mas o resultado é significativamente mais rico e preciso.

## 🔒 Segurança

- ✅ Validação Pydantic em todos os inputs
- ✅ CORS configurado
- ✅ API keys em variáveis de ambiente
- ✅ Session IDs com UUID4
- ⚠️ TODO: Autenticação JWT
- ⚠️ TODO: Rate limiting

## 🐛 Troubleshooting

### "No module named 'pandas'" ou "ModuleNotFoundError"

⚠️ **Problema comum**: Dependências instaladas no Python errado ou ambiente virtual não ativado.

**Solução:**
```bash
# 1. Certifique-se de que o venv está ativado
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# 2. Verifique qual Python está sendo usado
which python  # Deve mostrar: .../venv/bin/python

# 3. Verifique a versão do Python no venv
python --version

# 4. Se houver mistura de versões Python no venv, recrie:
deactivate  # Desative o venv atual
rm -rf venv  # Remova o venv antigo
python3 -m venv venv  # Recrie com Python 3.10-3.12
source venv/bin/activate  # Reative

# 5. Reinstale todas as dependências
pip install --upgrade pip
pip install -r requirements.txt

# 6. Verifique se pandas está instalado corretamente
python -c "import pandas; print(f'Pandas {pandas.__version__} OK')"
```

### "Agno não disponível"

```bash
# Com o venv ativado
pip install agno[openai,lancedb]
```

### "OPENAI_API_KEY não encontrada"

Verifique se o arquivo `.env` existe e contém a chave válida.

### "Knowledge base vazia" ou agentes não encontram documentos

Execute a indexação dos documentos:

```bash
# Indexar todas as versões
curl -X POST http://localhost:8000/knowledge/indexar?force=true

# OU indexar apenas uma versão específica
curl -X POST http://localhost:8000/knowledge/indexar?versao=minuta&force=true
```

**Nota**: O servidor não indexa automaticamente no startup (para subir rápido). Você precisa indexar manualmente na primeira vez ou após alterar arquivos.

### WebSocket não conecta

1. Verifique se o servidor está rodando
2. Confirme que a sessão foi criada antes de conectar
3. Verifique o console do navegador para erros

### Muitas chamadas HTTP para embeddings (logs repetitivos)

⚠️ **Isso é comportamento normal durante a indexação!**

Durante a indexação de PDFs, você verá muitas requisições HTTP sendo feitas para a API de embeddings da OpenAI:

**Por que acontece:**
- Cada PDF é dividido em múltiplos "chunks" (pedaços de texto)
- Cada chunk precisa de um embedding (vetor de números que representa o significado do texto)
- Um PDF de 50 páginas pode gerar 100-200 chunks
- Cada chunk = 1 chamada à API de embeddings

**Exemplo:**
- PDF de 50 páginas → ~150 chunks → 150 chamadas à API
- 5 PDFs × 150 chunks = 750 chamadas durante a indexação

**Isso é esperado e normal!** O sistema precisa criar embeddings para cada pedaço de texto para que a busca semântica funcione.

**Solução:** Os logs de requisições HTTP bem-sucedidas estão silenciados por padrão. Você verá apenas:
- Mensagens importantes do sistema
- Erros (se houver)
- Progresso da indexação

**Nota sobre custos:** Cada embedding custa ~$0.00002. 750 embeddings ≈ $0.015 (muito barato)

### Os embeddings são recriados toda vez que reinicio?

**Não!** ✅ Os embeddings são salvos permanentemente no disco e **NÃO são recriados** em reinicializações subsequentes.

**Como funciona:**

1. **Na primeira indexação**:
   - Quando você executa a indexação pela primeira vez, o sistema:
     - Divide os PDFs em chunks (pedaços de texto)
     - Cria embeddings para cada chunk (chamadas à API da OpenAI)
     - Salva tudo no LanceDB em `tmp/lancedb_*` (persistente no disco)

2. **Nas próximas reinicializações**:
   - O servidor sobe rapidamente (sem indexar)
   - O LanceDB carrega os embeddings já salvos do disco
   - A verificação rápida mostra quais bases têm dados
   - **Zero chamadas à API** (economiza tempo e dinheiro!)

3. **Quando você modifica arquivos**:
   - Execute `/knowledge/atualizar?versao=<versao>`
   - O sistema detecta mudanças pelo `content_hash`
   - Reindexa apenas o que foi modificado
   - Atualiza os embeddings no banco

**Você verá no log ao iniciar o servidor:**
```
📄 Verificando status das knowledge bases (verificação rápida)...
   ✅ Todas as knowledge bases têm dados indexados
```

**Você só precisará recriar embeddings se:**
- Deletar os arquivos em `tmp/lancedb_*`
- Modificar um arquivo e executar a atualização
- Limpar manualmente o diretório `tmp/`
- Usar `force=true` explicitamente na API

**Onde ficam salvos:**
```
tmp/
├── lancedb_1997/       # Embeddings da versão 1997
├── lancedb_2007/       # Embeddings da versão 2007
├── lancedb_2017/       # Embeddings da versão 2017
├── lancedb_alteracoes/ # Embeddings das alterações
└── lancedb_minuta/     # Embeddings da minuta
```

**Dica**: Se quiser fazer backup dos embeddings, basta copiar a pasta `tmp/`! Eles são portáveis.

### Mensagem "Deleted X records with content_hash..."

⚠️ **Isso é comportamento normal!**

Quando você atualiza a indexação de um arquivo que já foi indexado antes, o LanceDB/Agno automaticamente:
1. **Deleta** os registros antigos com o mesmo `content_hash` 
2. **Insere** os novos registros atualizados

Isso evita duplicatas e garante que você tenha apenas a versão mais recente do conteúdo indexado.

**Quando acontece:**
- Ao executar `/knowledge/atualizar?versao=<versao>` após modificar arquivos
- Ao chamar `/knowledge/indexar?force=true`
- Quando o arquivo foi modificado e você atualizou a indexação

**É seguro e esperado!** O sistema está substituindo os dados antigos pelos novos.

### Agente #5 (Minuta V2) não encontra documentos

**Sintoma**: O Agente #5 retorna "Found 0 documents" mesmo após indexação.

**Causa**: Bug conhecido do Agno onde usar `contents_db` junto com `vector_db` impede a criação de embeddings (vetores ficam None).

**Solução aplicada**: O código já foi corrigido para usar apenas `vector_db` para a knowledge base da minuta (workaround do bug).

**Se ainda não funcionar:**
1. Delete as tabelas da minuta: `rm -rf tmp/lancedb_minuta tmp/contents_minuta.db`
2. Reinicie o servidor
3. Reindexe: `curl -X POST "http://localhost:8000/knowledge/atualizar?versao=minuta"`
4. Verifique os vetores foram criados (use o script `backend/verificar_vetores.py`)

### Adicionar novos arquivos de alterações

**Pergunta**: Se eu adicionar um novo PDF em `files/regulamentos/alteracoes_menores/`, como indexo?

**Resposta**: Adicione o arquivo e execute a atualização:

1. **Para alterações (`alteracoes_menores/`)**: 
   - O sistema busca **automaticamente TODOS** os arquivos `.pdf` e `.txt` neste diretório
   - **Qualquer nomenclatura funciona** (não precisa seguir padrão específico)
   - Execute a atualização após adicionar o arquivo

2. **Para arquivos principais** (1997, 2007, 2017, Minuta):
   - Devem ter os nomes específicos definidos no código
   - Se você quiser adicionar novos arquivos principais, precisará atualizar `VERSOES_ARQUIVOS` em `knowledge_manager.py`

**Exemplo de uso:**
```bash
# 1. Adicione um novo arquivo
cp nova_resolucao.pdf files/regulamentos/alteracoes_menores/

# 2. Atualize a indexação
curl -X POST "http://localhost:8000/knowledge/atualizar?versao=alteracoes"
```

**Verificar se foi indexado:**
```bash
# Ver status
curl http://localhost:8000/knowledge/status

# Ou verifique os logs do servidor durante a indexação
```

### Bibliotecas não encontradas mesmo após instalação

**Causa**: Ambiente virtual não ativado ou usando Python errado.

**Solução**:
```bash
# Sempre ative o venv antes de executar o servidor
source venv/bin/activate

# Use o script run.sh que faz isso automaticamente
./run.sh
```

### Problemas de versão do Python

**Requisitos**:
- Python 3.10, 3.11 ou 3.12 (recomendado)
- **NÃO use Python 3.13** - pode ter incompatibilidades com algumas dependências

**Verificar versão**:
```bash
# ⚠️ Use "python3" (sem espaço), não "python 3"!
python3 --version
```

**Se precisar instalar Python 3.12**:
```bash
# Mac (com Homebrew)
brew install python@3.12

# Depois criar venv com versão específica
python3.12 -m venv venv
```

## 📝 Licença

MIT License - Uso interno TRE-GO

## 👥 Contribuidores

- Equipe de TI do TRE-GO
- Comissão de Revisão do Regulamento Interno

---

Desenvolvido com ❤️ usando [Agno Framework](https://docs.agno.com)
