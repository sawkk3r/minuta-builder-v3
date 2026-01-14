# 📊 Arquitetura do Sistema - TRE-GO Minuta Builder v2.0

## Visão Geral

O sistema utiliza o **Agno Framework** para criar agentes especializados com acesso a bases de conhecimento (Knowledge) indexadas com LanceDB e persistência de sessões via SQLite.

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (index.html)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  • Interface responsiva HTML5/CSS3/JavaScript                       │    │
│  │  • WebSocket para comunicação em tempo real                         │    │
│  │  • Cards de agentes interativos                                     │    │
│  │  • Chat em tempo real com respostas dos agentes                     │    │
│  │  • Painel de histórico de interações                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    HTTP REST + WebSocket (ws://)
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                                    │
│                                                                              │
│  ┌──────────────────────┐                                                   │
│  │      api.py          │ ◄── Endpoints REST + WebSocket                    │
│  │                      │     • /sessao/* - CRUD de sessões                 │
│  │  • Lifespan events   │     • /agente/* - Consultas a agentes             │
│  │  • ConnectionManager │     • /knowledge/* - Status e indexação           │
│  │  • WS handlers       │     • /ws/{session_id} - Tempo real               │
│  └──────────────────────┘                                                   │
│            │                                                                 │
│            ├─────────────────┬─────────────────┬─────────────────┐          │
│            ▼                 ▼                 ▼                 ▼          │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────┐   │
│  │ session_manager │ │     agents      │ │knowledge_manager│ │ models  │   │
│  │                 │ │                 │ │                 │ │         │   │
│  │ • Criar sessão  │ │ • Agente 1997   │ │ • LanceDB       │ │Pydantic │   │
│  │ • Persistir     │ │ • Agente 2007   │ │ • Embeddings    │ │Schemas  │   │
│  │ • Exportar MD   │ │ • Agente 2017   │ │ • PDF parsing   │ │         │   │
│  │ • Histórico     │ │ • Agente Alter. │ │ • Busca vetorial│ │         │   │
│  │                 │ │ • Agente Minuta │ │                 │ │         │   │
│  │                 │ │ • Team Coord.   │ │                 │ │         │   │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └─────────┘   │
│           │                   │                   │                         │
│           ▼                   ▼                   ▼                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      AGNO FRAMEWORK                                  │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │    Agent     │  │     Team     │  │  Knowledge   │               │   │
│  │  │              │  │              │  │              │               │   │
│  │  │ • model      │  │ • members    │  │ • vector_db  │               │   │
│  │  │ • knowledge  │  │ • model      │  │ • contents_db│               │   │
│  │  │ • instructions│ │ • delegate   │  │ • embedder   │               │   │
│  │  │ • search_kb  │  │ • consolidate│  │ • search     │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐                                 │   │
│  │  │   SqliteDb   │  │   LanceDb    │                                 │   │
│  │  │              │  │              │                                 │   │
│  │  │ • sessions   │  │ • vectors    │                                 │   │
│  │  │ • memories   │  │ • embeddings │                                 │   │
│  │  │ • history    │  │ • similarity │                                 │   │
│  │  └──────────────┘  └──────────────┘                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STORAGE                                            │
│                                                                              │
│  ┌─────────────────────┐     ┌─────────────────────────────────────────┐   │
│  │      SQLite         │     │              LanceDB                     │   │
│  │                     │     │                                          │   │
│  │ tmp/sessoes.db      │     │ tmp/lancedb_1997/                       │   │
│  │ • sessoes_analise   │     │ tmp/lancedb_2007/                       │   │
│  │ • interacoes        │     │ tmp/lancedb_2017/                       │   │
│  │ • analises          │     │ tmp/lancedb_alteracoes/                 │   │
│  │                     │     │ tmp/lancedb_minuta/                     │   │
│  │ tmp/contents_*.db   │     │                                          │   │
│  │ • metadados PDFs    │     │ (Vetores com embeddings OpenAI)         │   │
│  └─────────────────────┘     └─────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────┐     ┌─────────────────────────────────────────┐   │
│  │  files/regulamentos │     │            exports/                      │   │
│  │                     │     │                                          │   │
│  │ • PDFs originais    │     │ • Sessões exportadas (.md)              │   │
│  │ • Resoluções        │     │ • Documentos consolidados               │   │
│  │ • Minuta V2         │     │ • Audit trails                          │   │
│  └─────────────────────┘     └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OpenAI API                                         │
│                                                                              │
│  • gpt-5-mini-2025-08-07 → Agentes especializados (ECONÔMICO)              │
│  • gpt-5.2-2025-12-11   → Team Coordenador (REASONING ~$0.10/consolidação) │
│  • text-embedding-3-small → Embeddings para Knowledge (~$0.001/embedding)   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados

### 1. Criação de Sessão

```
Usuario → POST /sessao/criar → SessionManager → SQLite
                                    │
                                    └→ Retorna session_id
                                    
Usuario → WebSocket /ws/{session_id} → ConnectionManager → Connected
```

### 2. Consulta a Agente com RAG

```
Usuario → WS: consultar_agente
              │
              ▼
        GerenciadorAgentes
              │
              ▼
        AgenteEspecialista
              │
              ├─► Knowledge.search(pergunta)
              │         │
              │         ▼
              │   LanceDB → Embedding → Similar chunks
              │         │
              │         └─► Contexto relevante
              │
              ▼
        Agno Agent.arun(pergunta + contexto)
              │
              ▼
        OpenAI gpt-4o-mini
              │
              └─► Resposta com citações
                        │
                        ▼
                SessionManager.adicionar_interacao()
                        │
                        ▼
                WS → resposta_agente → Frontend
```

### 3. Consolidação com Team

```
Usuario → WS: consolidar
              │
              ▼
        TeamCoordenador
              │
              ├─► Coleta respostas anteriores
              │
              ▼
        Agno Team.arun(prompt consolidação)
              │
              ├─► Delega para agentes membros (opcional)
              │
              ▼
        OpenAI gpt-4o (reasoning)
              │
              ├─► Sintetiza informações
              ├─► Identifica gaps
              └─► Propõe texto consolidado
                        │
                        ▼
                SessionManager.adicionar_analise()
                        │
                        ▼
                WS → consolidacao_completa → Frontend
```

### 4. Exportação

```
Usuario → GET /sessao/{id}/exportar
              │
              ▼
        SessionManager.exportar_markdown()
              │
              ├─► Compila todas interações
              ├─► Formata em Markdown estruturado
              └─► Salva em exports/
                        │
                        ▼
                FileResponse → Download
```

## Componentes Principais

### 1. Knowledge Manager (`knowledge_manager.py`)

Responsável por:
- Criar bases de conhecimento separadas por versão do regulamento
- Indexar PDFs usando embeddings OpenAI
- Realizar buscas semânticas para RAG

```python
# Exemplo de uso
km = get_knowledge_manager()
await km.inicializar()
await km.indexar_documentos()
resultados = await km.buscar("1997", "competências do gabinete", num_results=5)
```

### 2. Gerenciador de Agentes (`agents.py`)

Cria e gerencia:
- 5 agentes especializados (um por versão)
- 1 Team Coordenador para consolidação

```python
# Cada agente tem acesso ao seu Knowledge
agente = AgenteEspecialista(
    versao=VersaoRegulamento.RES_1997,
    knowledge_manager=km
)
resposta = await agente.consultar("Quais as competências do Corregedor?")
```

### 3. Session Manager (`session_manager.py`)

Gerencia:
- Criação e recuperação de sessões
- Persistência em SQLite + JSON backup
- Histórico de interações
- Exportação de documentos

```python
# Sessões persistem entre reinícios
sessao = await sessoes.criar_sessao("Art. 47", "Gabinete da Presidência")
await sessoes.adicionar_interacao(session_id, interacao)
filepath = await sessoes.exportar_markdown(session_id)
```

## Modelos de Dados

### SessaoAnalise

```python
class SessaoAnalise:
    id: str                          # UUID4
    artigo: str                      # "Art. 47"
    titulo: str                      # "Gabinete da Presidência"
    usuario: str                     # ID do usuário
    status: StatusConsulta           # em_andamento, concluida, erro
    interacoes: List[InteracaoAgente]  # Histórico completo
    analises: List[AnaliseEvolutiva]   # Consolidações
    texto_final_minuta: Optional[str]  # Proposta final
    data_criacao: datetime
    data_atualizacao: datetime
```

### InteracaoAgente

```python
class InteracaoAgente:
    id: str
    agente: str                      # "1997", "2007", etc.
    agente_nome: str                 # "Especialista Res. 05/1997"
    pergunta: str
    resposta: str
    artigos_citados: List[str]       # ["47", "48", "50"]
    fontes_conhecimento: List[str]   # Chunks recuperados do RAG
    confianca: float                 # 0.0 a 1.0
    timestamp: datetime
```

## Estimativa de Custos por Operação

| Operação | Tokens (est.) | Custo |
|----------|---------------|-------|
| Embedding da pergunta | ~20 tokens | $0.000002 |
| Busca LanceDB | Local | $0.00 |
| Agente gpt-4o-mini | ~2000 tokens | $0.01 |
| Team gpt-4o | ~5000 tokens | $0.10 |

**Total por artigo completo (5 consultas + consolidação):** ~$0.16

## Configurações de Ambiente

```env
# Modelos
MODEL_AGENTES=gpt-5-mini-2025-08-07    # Econômico para agentes
MODEL_COORDENADOR=gpt-5.2-2025-12-11   # Poderoso para Team (com reasoning)
EMBEDDING_MODEL=text-embedding-3-small

# Diretórios
FILES_DIR=files/regulamentos
DB_DIR=tmp
EXPORTS_DIR=exports
```

## Segurança

| Item | Status |
|------|--------|
| Validação Pydantic | ✅ Implementado |
| CORS configurado | ✅ Implementado |
| API keys em .env | ✅ Implementado |
| Session IDs UUID4 | ✅ Implementado |
| Autenticação JWT | ⏳ TODO |
| Rate limiting | ⏳ TODO |
| HTTPS | ⏳ TODO (produção) |

## Extensibilidade

O sistema foi projetado para fácil extensão:

1. **Novos agentes**: Adicione em `AGENTES_CONFIG` no `agents.py`
2. **Novas fontes**: Adicione em `VERSOES_ARQUIVOS` no `knowledge_manager.py`
3. **Novos modelos**: Configure via variáveis de ambiente
4. **Novo storage**: Agno suporta PostgreSQL, MongoDB, etc.
