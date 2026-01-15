# ============================================================================
# ARQUIVO: backend/api.py
# API FastAPI com WebSockets para interação em tempo real
# ============================================================================

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from contextlib import asynccontextmanager
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import os
from dotenv import load_dotenv
import secrets

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Reduzir verbosidade de bibliotecas externas
# Mostrar apenas erros, não cada requisição bem-sucedida
logging.getLogger("httpx").setLevel(logging.WARNING)  # Requisições HTTP (embeddings, etc)
logging.getLogger("httpcore").setLevel(logging.WARNING)  # Cliente HTTP de baixo nível
logging.getLogger("openai").setLevel(logging.WARNING)  # SDK da OpenAI
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Cliente HTTP urllib3

# Carregar variáveis de ambiente
load_dotenv()

# Configurações de segurança
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-in-production")
DISABLE_DOCS_IN_PRODUCTION = os.getenv("DISABLE_DOCS_IN_PRODUCTION", "true").lower() == "true"

# Autenticação básica para endpoints administrativos
security = HTTPBasic()

# Importar módulos locais
# Ajustar sys.path para garantir que os imports funcionem
import sys
from pathlib import Path

# Adicionar diretório backend ao path se não estiver
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models import (
    CriarSessaoRequest, ConsultarAgenteRequest, ConsolidarRequest,
    VersaoRegulamento, StatusConsulta, InteracaoAgente, RespostaAgente,
    WSMessageType, WSMessage
)
from session_manager import get_gerenciador_sessoes, GerenciadorSessoes
from agents import get_gerenciador_agentes, inicializar_agentes_global, GerenciadorAgentes
from knowledge_manager import get_knowledge_manager, inicializar_knowledge_global, KnowledgeManager
from minuta_memory import MinutaMemory
from minuta_generator import MinutaGenerator


# ============================================================================
# LIFECYCLE E INICIALIZAÇÃO
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    logger.info("🚀 Iniciando TRE-GO Minuta Builder API...")
    
    # Log de variáveis de ambiente importantes
    auto_index_env = os.getenv("AUTO_INDEX_ON_STARTUP", "false")
    logger.info(f"🔍 Variáveis de ambiente: AUTO_INDEX_ON_STARTUP={auto_index_env}")
    
    # Variável para armazenar versões que precisam ser indexadas
    versoes_para_indexar = []
    
    # Inicializar Knowledge Manager
    logger.info("📚 Inicializando Knowledge Manager...")
    km = get_knowledge_manager()
    km_ok = await inicializar_knowledge_global()
    
    if km_ok:
        logger.info("   ✅ Knowledge Manager pronto")
        
        # Verificação RÁPIDA: apenas checar se tabelas têm dados (não processa arquivos)
        # Isso é muito mais rápido que verificar cada arquivo individualmente
        logger.info("📄 Verificando status das knowledge bases (verificação rápida)...")
        try:
            versoes_sem_dados = []
            for versao in ["1997", "2007", "2017", "alteracoes", "minuta"]:
                knowledge = km.obter_knowledge(versao)
                if knowledge and hasattr(knowledge, 'vector_db') and hasattr(knowledge.vector_db, 'table'):
                    table = knowledge.vector_db.table
                    if table:
                        try:
                            count = table.count_rows()
                            if count is None or count == 0:
                                versoes_sem_dados.append(versao)
                        except:
                            versoes_sem_dados.append(versao)
                    else:
                        versoes_sem_dados.append(versao)
                else:
                    versoes_sem_dados.append(versao)
            
            if versoes_sem_dados:
                logger.warning(f"   ⚠️ {len(versoes_sem_dados)} knowledge base(s) sem dados: {', '.join(versoes_sem_dados)}")
                
                # Indexação automática no startup (se habilitada)
                # IMPORTANTE: Indexação em background para não bloquear startup (Render precisa detectar porta)
                auto_index_env = os.getenv("AUTO_INDEX_ON_STARTUP", "false")
                auto_index = auto_index_env.lower() == "true"
                logger.info(f"   🔍 AUTO_INDEX_ON_STARTUP={auto_index_env} (detectado: {auto_index})")
                
                if auto_index:
                    logger.info("   🔄 AUTO_INDEX_ON_STARTUP=true - Indexação será iniciada em background após servidor subir")
                    logger.info("   ⏳ Isso pode levar alguns minutos. Servidor já está pronto para receber requisições.")
                    
                    # Armazenar versões para indexação em background
                    versoes_para_indexar = versoes_sem_dados.copy()
                else:
                    logger.info("   💡 Execute POST /knowledge/indexar para indexar quando necessário")
                    logger.info("   💡 Ou configure AUTO_INDEX_ON_STARTUP=true para indexação automática")
                    logger.info("   💡 O servidor já está pronto - indexação pode ser feita depois")
            else:
                logger.info("   ✅ Todas as knowledge bases têm dados indexados")
        except Exception as e:
            logger.debug(f"   ⚠️ Erro na verificação rápida: {e}")
            logger.info("   💡 Execute POST /knowledge/indexar para indexar quando necessário")
    else:
        logger.warning("   ⚠️ Knowledge Manager em modo fallback")
    
    # Inicializar Agentes
    logger.info("🤖 Inicializando Agentes...")
    agentes_ok = await inicializar_agentes_global()
    
    if agentes_ok:
        logger.info("   ✅ Agentes prontos")
    else:
        logger.warning("   ⚠️ Agentes em modo fallback")
    
    # Inicializar Gerenciador de Sessões
    logger.info("📁 Inicializando Gerenciador de Sessões...")
    sessoes = get_gerenciador_sessoes()
    logger.info(f"   ✅ {sessoes.status()['total_sessoes']} sessões carregadas")
    
    logger.info("✅ API pronta para receber requisições!")
    
    # Indexação automática em background (após servidor estar pronto)
    # Isso garante que o Render detecte a porta antes da indexação começar
    if versoes_para_indexar:
        async def indexar_automaticamente_background():
            try:
                await asyncio.sleep(2)  # Pequeno delay para garantir que servidor está rodando
                logger.info("   📚 Iniciando indexação automática em background...")
                
                agentes = get_gerenciador_agentes()
                
                # Indexar versão por versão e recarregar agentes incrementalmente
                for v in versoes_para_indexar:
                    try:
                        logger.info(f"   📄 Indexando versão '{v}'...")
                        resultados = await km.indexar_documentos(versao=v, force=False)
                        logger.info(f"   ✅ Versão '{v}' indexada: {resultados.get(v, False)}")
                        
                        # Recarregar knowledge base após indexação
                        knowledge = km.obter_knowledge(v)
                        if knowledge and hasattr(knowledge, 'vector_db') and hasattr(knowledge.vector_db, 'uri'):
                            import lancedb
                            lance_uri = knowledge.vector_db.uri
                            lance_table_name = getattr(knowledge.vector_db, 'table_name', f"regulamento_{v}")
                            lance_conn = lancedb.connect(lance_uri)
                            if lance_table_name in lance_conn.table_names():
                                knowledge.vector_db.table = lance_conn.open_table(lance_table_name)
                                logger.info(f"   ✅ Knowledge base '{v}' recarregada")
                                
                                # Atualizar agente correspondente
                                agente = agentes.obter_agente(v)
                                if agente and hasattr(agente, 'agent') and agente.agent:
                                    agente.agent.knowledge = knowledge
                                    logger.info(f"   🔄 Agente '{v}' atualizado com conhecimento indexado")
                    except Exception as e:
                        logger.error(f"   ❌ Erro ao indexar versão '{v}': {e}")
                
                logger.info("   ✅ Indexação automática concluída!")
            except Exception as e:
                logger.error(f"   ❌ Erro na indexação automática em background: {e}")
        
        # Executar em background (não bloqueia startup)
        import asyncio
        asyncio.create_task(indexar_automaticamente_background())
    
    yield
    
    # Cleanup
    logger.info("🔄 Encerrando API...")


# ============================================================================
# APLICAÇÃO FASTAPI
# ============================================================================

# Configurar documentação (desabilitar em produção se configurado)
docs_url = "/docs" if not (ENVIRONMENT == "production" and DISABLE_DOCS_IN_PRODUCTION) else None
redoc_url = "/redoc" if not (ENVIRONMENT == "production" and DISABLE_DOCS_IN_PRODUCTION) else None
openapi_url = "/openapi.json" if not (ENVIRONMENT == "production" and DISABLE_DOCS_IN_PRODUCTION) else None

app = FastAPI(
    title="TRE-GO Minuta Builder API",
    description="""
    Sistema colaborativo para construção da Minuta V2 do Regulamento Interno do TRE-GO.
    
    ## Funcionalidades
    
    - **Agentes Especializados**: Consulte especialistas em cada versão do regulamento
    - **Knowledge Base**: Busca semântica nos documentos originais (PDFs)
    - **Team Coordenador**: Consolidação inteligente de análises
    - **Sessões Persistentes**: Histórico completo de interações
    - **Exportação**: Markdown e documentos consolidados
    
    ## Versões Disponíveis
    
    - 1997: Resolução 05/1997 (Original)
    - 2007: Resolução 113/2007
    - 2017: Resolução 275/2017 (Vigente)
    - alteracoes: Alterações 2021-2025
    - minuta: Minuta V2 (Em construção)
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url
)

# CORS - Configurar origens permitidas
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if "*" in ALLOWED_ORIGINS and ENVIRONMENT == "production":
    logger.warning("⚠️ CORS permitindo todas as origens em produção! Configure ALLOWED_ORIGINS no .env")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================================
# GERENCIADOR DE CONEXÕES WEBSOCKET
# ============================================================================

class ConnectionManager:
    """Gerencia conexões WebSocket ativas."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"✅ WebSocket conectado: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"❌ WebSocket desconectado: {session_id}")
    
    async def send_message(self, session_id: str, message: WSMessage):
        """Envia mensagem para uma sessão específica."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message.to_json())
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para {session_id}: {e}")
    
    async def broadcast(self, message: WSMessage):
        """Envia mensagem para todas as conexões."""
        for session_id in self.active_connections:
            await self.send_message(session_id, message)


manager = ConnectionManager()


# ============================================================================
# AUTENTICAÇÃO E SEGURANÇA
# ============================================================================

def verify_admin(credentials: HTTPBasicCredentials = Security(security)):
    """Verifica credenciais de administrador."""
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ============================================================================
# ENDPOINTS REST - STATUS E INFO
# ============================================================================

@app.get("/api")
@app.get("/api/info")
async def root():
    """Endpoint com informações da API."""
    return {
        "sistema": "TRE-GO Minuta Builder",
        "versao": "2.0.0",
        "status": "online",
        "documentacao": "/docs",
        "endpoints": {
            "sessoes": "/sessao",
            "agentes": "/agente",
            "knowledge": "/knowledge",
            "websocket": "/ws/{session_id}"
        }
    }


@app.get("/status")
async def status():
    """Status completo do sistema."""
    km = get_knowledge_manager()
    agentes = get_gerenciador_agentes()
    sessoes = get_gerenciador_sessoes()
    
    return {
        "api": "online",
        "timestamp": datetime.now().isoformat(),
        "knowledge_manager": km.status(),
        "agentes": agentes.status(),
        "sessoes": sessoes.status(),
        "websocket_conexoes": len(manager.active_connections)
    }


# ============================================================================
# ENDPOINTS REST - SESSÕES
# ============================================================================

@app.post("/sessao/criar")
async def criar_sessao(request: CriarSessaoRequest):
    """Cria nova sessão de análise."""
    sessoes = get_gerenciador_sessoes()
    
    sessao = await sessoes.criar_sessao(
        artigo=request.artigo,
        titulo=request.titulo,
        usuario=request.usuario
    )
    
    return {
        "id": sessao.id,
        "artigo": sessao.artigo,
        "titulo": sessao.titulo,
        "usuario": sessao.usuario,
        "status": sessao.status.value,
        "criada_em": sessao.data_criacao.isoformat()
    }


@app.get("/sessao/{session_id}")
async def obter_sessao(session_id: str):
    """Obtém dados de uma sessão."""
    sessoes = get_gerenciador_sessoes()
    sessao = await sessoes.obter_sessao(session_id)
    
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return sessao.to_dict()


@app.get("/sessao/{session_id}/interacoes")
async def listar_interacoes(session_id: str):
    """Lista interações de uma sessão."""
    sessoes = get_gerenciador_sessoes()
    sessao = await sessoes.obter_sessao(session_id)
    
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return {
        "session_id": session_id,
        "total": len(sessao.interacoes),
        "interacoes": [
            {
                "id": i.id,
                "agente": i.agente,
                "agente_nome": i.agente_nome,
                "pergunta": i.pergunta,
                "resposta": i.resposta[:500] + "..." if len(i.resposta) > 500 else i.resposta,
                "artigos_citados": i.artigos_citados,
                "confianca": i.confianca,
                "timestamp": i.timestamp.isoformat()
            }
            for i in sessao.interacoes
        ]
    }


@app.get("/sessao/{session_id}/exportar")
async def exportar_sessao(session_id: str):
    """Exporta sessão como Markdown."""
    sessoes = get_gerenciador_sessoes()
    filepath = await sessoes.exportar_markdown(session_id)
    
    if not filepath:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return FileResponse(
        filepath,
        media_type="text/markdown",
        filename=Path(filepath).name
    )


@app.get("/sessao/{session_id}/documento-consolidado")
async def gerar_documento_consolidado(session_id: str):
    """Gera documento consolidado no formato de regulamento."""
    sessoes = get_gerenciador_sessoes()
    filepath = await sessoes.gerar_documento_consolidado(session_id)
    
    if not filepath:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return FileResponse(
        filepath,
        media_type="text/markdown",
        filename=Path(filepath).name
    )


@app.post("/sessao/{session_id}/gerar-minuta")
async def gerar_minuta_atualizada(
    session_id: str,
    instrucoes: Optional[str] = None
):
    """
    Gera minuta atualizada baseada nas interações da sessão.
    
    Fluxo:
    1. Obtém sessão e consolidação
    2. Agente #5 fornece contexto da minuta original
    3. Team gera minuta atualizada
    4. Salva como minuta{session_id}.txt
    
    Args:
        session_id: ID da sessão
        instrucoes: Instruções adicionais do usuário (opcional)
    """
    try:
        # Obter gerenciadores
        sessoes = get_gerenciador_sessoes()
        agentes = get_gerenciador_agentes()
        
        # Obter sessão
        sessao = await sessoes.obter_sessao(session_id)
        if not sessao:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        # Obter última consolidação da sessão
        if not sessao.analises:
            raise HTTPException(
                status_code=400,
                detail="Sessão não possui consolidação. Execute a consolidação primeiro."
            )
        
        consolidacao = sessao.analises[-1]  # Última consolidação
        
        # Obter Agente #5 (Minuta V2)
        agente_minuta = agentes.obter_agente(VersaoRegulamento.MINUTA_V2.value)
        if not agente_minuta:
            raise HTTPException(status_code=500, detail="Agente Minuta V2 não disponível")
        
        # Obter Team Coordenador
        team = agentes.team
        if not team:
            raise HTTPException(status_code=500, detail="Team Coordenador não disponível")
        
        # Criar gerador de minuta
        generator = MinutaGenerator(
            team_coordenador=team,
            agente_minuta=agente_minuta
        )
        
        # Gerar minuta atualizada
        resultado = await generator.gerar_minuta_atualizada(
            session_id=session_id,
            sessao=sessao,
            consolidacao=consolidacao,
            instrucoes_usuario=instrucoes
        )
        
        if not resultado.get("sucesso"):
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao gerar minuta: {resultado.get('erro', 'Erro desconhecido')}"
            )
        
        return JSONResponse(content=resultado)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao gerar minuta atualizada: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.get("/sessoes")
async def listar_sessoes(
    usuario: Optional[str] = None,
    status: Optional[str] = None,
    limite: int = 50
):
    """Lista sessões com filtros opcionais."""
    sessoes_manager = get_gerenciador_sessoes()
    
    status_enum = None
    if status:
        try:
            status_enum = StatusConsulta(status)
        except ValueError:
            pass
    
    sessoes = await sessoes_manager.listar_sessoes(
        usuario=usuario,
        status=status_enum,
        limite=limite
    )
    
    return {
        "total": len(sessoes),
        "sessoes": [s.to_dict() for s in sessoes]
    }


# ============================================================================
# ENDPOINTS REST - AGENTES
# ============================================================================

@app.get("/agentes")
async def listar_agentes():
    """Lista agentes disponíveis."""
    agentes = get_gerenciador_agentes()
    return agentes.status()


@app.post("/agente/consultar")
async def consultar_agente(request: ConsultarAgenteRequest):
    """Consulta um agente específico (endpoint síncrono)."""
    agentes = get_gerenciador_agentes()
    
    resposta = await agentes.consultar_agente(
        versao=request.agente.value,
        pergunta=request.pergunta
    )
    
    return {
        "agente": resposta.agente,
        "agente_nome": resposta.agente_nome,
        "resposta": resposta.resposta,
        "artigos_citados": resposta.artigos_citados,
        "fontes_conhecimento": resposta.fontes_conhecimento,
        "confianca": resposta.confianca,
        "timestamp": resposta.timestamp.isoformat()
    }


@app.post("/agente/consolidar")
async def consolidar_analises(request: ConsolidarRequest):
    """Consolida análises de múltiplos agentes."""
    agentes = get_gerenciador_agentes()
    
    versoes = [v.value for v in request.incluir_agentes] if request.incluir_agentes else None
    
    analise = await agentes.consolidar(
        tema=request.tema,
        versoes=versoes
    )
    
    return {
        "tema": analise.tema_analisado,
        "proposta_consolidada": analise.proposta_consolidada,
        "gaps": [
            {
                "descricao": g.descricao,
                "versao_origem": g.versao_origem,
                "versao_destino": g.versao_destino,
                "criticidade": g.criticidade.value,
                "sugestao": g.sugestao_resgate
            }
            for g in analise.gaps_identificados
        ],
        "observacoes": analise.observacoes,
        "timestamp": analise.timestamp.isoformat()
    }


# ============================================================================
# ENDPOINTS REST - KNOWLEDGE
# ============================================================================

@app.get("/knowledge/status")
async def knowledge_status():
    """Status das bases de conhecimento."""
    km = get_knowledge_manager()
    status_info = km.status()
    
    # Adicionar informações detalhadas sobre cada knowledge base
    detalhes = {}
    for versao in ["1997", "2007", "2017", "alteracoes", "minuta"]:
        knowledge = km.obter_knowledge(versao)
        if knowledge and hasattr(knowledge, 'vector_db') and hasattr(knowledge.vector_db, 'table'):
            table = knowledge.vector_db.table
            if table:
                try:
                    count = table.count_rows()
                    detalhes[versao] = {
                        "indexado": count is not None and count > 0,
                        "total_registros": count if count is not None else 0
                    }
                except Exception as e:
                    detalhes[versao] = {
                        "indexado": False,
                        "erro": str(e)
                    }
            else:
                detalhes[versao] = {"indexado": False, "erro": "Tabela não carregada"}
        else:
            detalhes[versao] = {"indexado": False, "erro": "Knowledge base não encontrada"}
    
    status_info["detalhes_versoes"] = detalhes
    return status_info


@app.post("/knowledge/indexar")
async def indexar_knowledge(
    versao: Optional[str] = None,
    force: bool = False,
    background_tasks: BackgroundTasks = None,
    username: str = Depends(verify_admin)
):
    """
    Indexa documentos nas bases de conhecimento.
    
    Args:
        versao: Versão específica para indexar (None = todas)
                Valores possíveis: "1997", "2007", "2017", "alteracoes", "minuta"
        force: Se True, força reindexação mesmo se já indexado
        
    Exemplos:
        - POST /knowledge/indexar?versao=minuta&force=true (reindexar minuta após alterar arquivos)
        - POST /knowledge/indexar?versao=2017&force=true (reindexar versão 2017)
        - POST /knowledge/indexar?force=true (reindexar todas as versões)
    """
    km = get_knowledge_manager()
    agentes = get_gerenciador_agentes()
    
    # Executar em background para não bloquear
    async def indexar():
        resultados = await km.indexar_documentos(versao=versao, force=force)
        logger.info(f"Indexação concluída: {resultados}")
        
        # CRÍTICO: Recarregar knowledge bases nos agentes após indexação
        versoes_para_recarregar = [versao] if versao else ["1997", "2007", "2017", "alteracoes", "minuta"]
        
        for v in versoes_para_recarregar:
            try:
                knowledge = km.obter_knowledge(v)
                if knowledge:
                    # Recarregar tabela no knowledge
                    if hasattr(knowledge, 'vector_db') and hasattr(knowledge.vector_db, 'uri'):
                        import lancedb
                        lance_uri = knowledge.vector_db.uri
                        lance_table_name = getattr(knowledge.vector_db, 'table_name', f"regulamento_{v}")
                        lance_conn = lancedb.connect(lance_uri)
                        if lance_table_name in lance_conn.table_names():
                            knowledge.vector_db.table = lance_conn.open_table(lance_table_name)
                            logger.info(f"   🔄 Knowledge base '{v}' recarregada após indexação")
                            
                            # Atualizar no agente correspondente
                            agente = agentes.obter_agente(v)
                            if agente and hasattr(agente, 'agent') and agente.agent:
                                agente.agent.knowledge = knowledge
                                logger.info(f"   🔄 Agente '{v}' atualizado com nova knowledge base")
            except Exception as e:
                logger.warning(f"   ⚠️ Erro ao recarregar agente '{v}' após indexação: {e}")
    
    if background_tasks:
        background_tasks.add_task(indexar)
        return {
            "status": "indexação iniciada em background",
            "versao": versao or "todas",
            "force": force,
            "mensagem": f"Indexação de '{versao or 'todas as versões'}' iniciada em background"
        }
    else:
        resultados = await km.indexar_documentos(versao=versao, force=force)
        
        # Recarregar agentes após indexação síncrona
        versoes_para_recarregar = [versao] if versao else ["1997", "2007", "2017", "alteracoes", "minuta"]
        for v in versoes_para_recarregar:
            try:
                knowledge = km.obter_knowledge(v)
                if knowledge and hasattr(knowledge, 'vector_db') and hasattr(knowledge.vector_db, 'uri'):
                    import lancedb
                    lance_uri = knowledge.vector_db.uri
                    lance_table_name = getattr(knowledge.vector_db, 'table_name', f"regulamento_{v}")
                    lance_conn = lancedb.connect(lance_uri)
                    if lance_table_name in lance_conn.table_names():
                        knowledge.vector_db.table = lance_conn.open_table(lance_table_name)
                        agente = agentes.obter_agente(v)
                        if agente and hasattr(agente, 'agent') and agente.agent:
                            agente.agent.knowledge = knowledge
            except Exception as e:
                logger.warning(f"   ⚠️ Erro ao recarregar agente '{v}': {e}")
        
        return {"status": "concluído", "resultados": resultados}


@app.post("/knowledge/atualizar")
async def atualizar_knowledge(
    versao: str,
    background_tasks: BackgroundTasks = None,
    username: str = Depends(verify_admin)
):
    """
    Endpoint conveniente para atualizar a indexação de uma versão específica após alterar arquivos.
    
    Use este endpoint quando você modificar arquivos de qualquer versão.
    Ele força a reindexação da versão especificada.
    
    Args:
        versao: Versão para atualizar. Valores possíveis:
                - "1997": Resolução 05/1997 (arquivos: 1997_Resolucao_05.txt/pdf)
                - "2007": Resolução 113/2007 (arquivos: 2007_Resolucao_113.txt/pdf)
                - "2017": Resolução 275/2017 (arquivos: 2017_Resolucao_275.txt/pdf)
                - "alteracoes": Alterações 2021-2025 (arquivos em alteracoes_menores/)
                - "minuta": Minuta V2 (arquivos: minuta.txt/pdf)
    
    Exemplos:
        - POST /knowledge/atualizar?versao=minuta (atualizar minuta após editar minuta.txt)
        - POST /knowledge/atualizar?versao=2017 (atualizar versão 2017 após editar arquivo)
        - POST /knowledge/atualizar?versao=alteracoes (atualizar alterações após adicionar/modificar PDFs)
    """
    versoes_validas = ["1997", "2007", "2017", "alteracoes", "minuta"]
    
    if versao not in versoes_validas:
        raise HTTPException(
            status_code=400,
            detail=f"Versão inválida: '{versao}'. Versões válidas: {', '.join(versoes_validas)}"
        )
    
    km = get_knowledge_manager()
    agentes = get_gerenciador_agentes()
    
    async def indexar():
        resultados = await km.indexar_documentos(versao=versao, force=True)
        logger.info(f"Atualização de '{versao}' concluída: {resultados}")
        
        # CRÍTICO: Recarregar knowledge base no agente correspondente após indexação
        try:
            knowledge = km.obter_knowledge(versao)
            if knowledge:
                # Recarregar tabela no knowledge
                if hasattr(knowledge, 'vector_db') and hasattr(knowledge.vector_db, 'uri'):
                    import lancedb
                    lance_uri = knowledge.vector_db.uri
                    lance_table_name = getattr(knowledge.vector_db, 'table_name', f"regulamento_{versao}")
                    lance_conn = lancedb.connect(lance_uri)
                    if lance_table_name in lance_conn.table_names():
                        knowledge.vector_db.table = lance_conn.open_table(lance_table_name)
                        logger.info(f"   🔄 Knowledge base '{versao}' recarregada após indexação")
                
                # Atualizar no agente correspondente
                agente = agentes.obter_agente(versao)
                if agente and hasattr(agente, 'agent') and agente.agent:
                    agente.agent.knowledge = knowledge
                    logger.info(f"   🔄 Agente '{versao}' atualizado com nova knowledge base")
        except Exception as e:
            logger.warning(f"   ⚠️ Erro ao recarregar agente após indexação: {e}")
        
        return resultados
    
    if background_tasks:
        background_tasks.add_task(indexar)
        return {
            "status": "atualização iniciada em background",
            "versao": versao,
            "mensagem": f"Versão '{versao}' está sendo reindexada. Aguarde alguns segundos/minutos.",
            "force": True
        }
    else:
        resultados = await indexar()
        return {
            "status": "concluído",
            "versao": versao,
            "resultados": resultados,
            "mensagem": f"Versão '{versao}' atualizada com sucesso!"
        }


@app.get("/knowledge/buscar")
async def buscar_knowledge(
    versao: str,
    query: str,
    num_results: int = 5
):
    """Busca semântica em uma base de conhecimento."""
    km = get_knowledge_manager()
    
    resultados = await km.buscar(
        versao=versao,
        query=query,
        num_results=num_results
    )
    
    return {
        "versao": versao,
        "query": query,
        "total": len(resultados),
        "resultados": resultados
    }


# ============================================================================
# WEBSOCKET - INTERAÇÃO EM TEMPO REAL
# ============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket para interação em tempo real com agentes.
    
    Ações suportadas:
    - consultar_agente: Consulta um agente específico
    - consolidar: Consolida análises com Team
    - finalizar: Finaliza e exporta sessão
    """
    await manager.connect(websocket, session_id)
    
    # Obter managers
    sessoes = get_gerenciador_sessoes()
    agentes = get_gerenciador_agentes()
    
    try:
        while True:
            # Receber mensagem
            data = await websocket.receive_json()
            acao = data.get("acao")
            
            logger.info(f"📨 WS [{session_id}] Ação: {acao}")
            
            if acao == "consultar_agente":
                await handle_consultar_agente(
                    websocket=websocket,
                    session_id=session_id,
                    agente=data.get("agente"),
                    pergunta=data.get("pergunta"),
                    sessoes=sessoes,
                    agentes=agentes
                )
            
            elif acao == "consolidar":
                await handle_consolidar(
                    websocket=websocket,
                    session_id=session_id,
                    tema=data.get("tema"),
                    versoes=data.get("versoes"),
                    sessoes=sessoes,
                    agentes=agentes
                )
            
            elif acao == "consultar_colaborativo":
                # Nova ação: consulta colaborativa onde todos os agentes respondem vendo uns aos outros
                await handle_consultar_colaborativo(
                    websocket=websocket,
                    session_id=session_id,
                    pergunta=data.get("pergunta"),
                    versoes=data.get("versoes"),
                    sessoes=sessoes,
                    agentes=agentes
                )
            
            elif acao == "finalizar":
                await handle_finalizar(
                    websocket=websocket,
                    session_id=session_id,
                    texto_final=data.get("texto_final"),
                    observacoes=data.get("observacoes"),
                    sessoes=sessoes
                )
            
            elif acao == "gerar_minuta":
                await handle_gerar_minuta(
                    websocket=websocket,
                    session_id=session_id,
                    instrucoes=data.get("instrucoes"),
                    sessoes=sessoes,
                    agentes=agentes
                )
            
            else:
                await websocket.send_json({
                    "tipo": "erro",
                    "mensagem": f"Ação desconhecida: {acao}",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"❌ Erro WebSocket [{session_id}]: {e}")
        try:
            await websocket.send_json({
                "tipo": "erro",
                "mensagem": str(e),
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass
        manager.disconnect(session_id)


async def handle_consultar_agente(
    websocket: WebSocket,
    session_id: str,
    agente: str,
    pergunta: str,
    sessoes: GerenciadorSessoes,
    agentes: GerenciadorAgentes
):
    """Handler para consulta de agente via WebSocket."""
    
    # Validar agente
    if agente not in [v.value for v in VersaoRegulamento]:
        await websocket.send_json({
            "tipo": "erro",
            "mensagem": f"Agente '{agente}' não encontrado",
            "timestamp": datetime.now().isoformat()
        })
        return
    
    # Enviar status
    await websocket.send_json({
        "tipo": "status",
        "mensagem": f"🔍 Consultando especialista {agente}...",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        # Obter respostas anteriores da sessão para contexto colaborativo
        # IMPORTANTE: Limitar drasticamente para evitar crescimento exponencial do prompt
        # Incluir apenas as últimas 2 interações (apenas de outros agentes)
        sessao = await sessoes.obter_sessao(session_id)
        contexto_agentes = None
        if sessao and sessao.interacoes:
            # Pegar apenas as últimas 2 interações de outros agentes
            interacoes_outros_agentes = [
                interacao for interacao in sessao.interacoes
                if interacao.agente != agente
            ][-2:]  # Últimas 2 apenas!
            
            if interacoes_outros_agentes:
                logger.info(f"📚 Incluindo {len(interacoes_outros_agentes)} interação(ões) anterior(es) como contexto (limitado para evitar erro de tokens)")
                
                # Converter interações anteriores em RespostaAgente para contexto
                contexto_agentes = [
                    RespostaAgente(
                        agente=interacao.agente,
                        agente_nome=interacao.agente_nome,
                        pergunta=interacao.pergunta,
                        resposta=interacao.resposta,
                        artigos_citados=interacao.artigos_citados,
                        fontes_conhecimento=interacao.fontes_conhecimento,
                        confianca=interacao.confianca,
                        timestamp=interacao.timestamp
                    )
                    for interacao in interacoes_outros_agentes
                ]
            else:
                logger.debug(f"Nenhuma interação anterior de outros agentes para incluir no contexto")
        
        # Consultar agente (com contexto de outros agentes se disponível)
        resposta = await agentes.consultar_agente(
            versao=agente,
            pergunta=pergunta,
            contexto_agentes=contexto_agentes if contexto_agentes else None
        )
        
        # Enviar resposta
        await websocket.send_json({
            "tipo": "resposta_agente",
            "agente": resposta.agente,
            "agente_nome": resposta.agente_nome,
            "resposta": resposta.resposta,
            "artigos": resposta.artigos_citados,
            "fontes": resposta.fontes_conhecimento,
            "confianca": resposta.confianca,
            "timestamp": resposta.timestamp.isoformat()
        })
        
        # Salvar interação na sessão
        interacao = InteracaoAgente(
            agente=resposta.agente,
            agente_nome=resposta.agente_nome,
            pergunta=pergunta,
            resposta=resposta.resposta,
            artigos_citados=resposta.artigos_citados,
            fontes_conhecimento=resposta.fontes_conhecimento,
            confianca=resposta.confianca
        )
        
        await sessoes.adicionar_interacao(session_id, interacao)
        
        # NOVO: Adicionar insight à memória da minuta (exceto se for o próprio agente #5)
        # Isso permite que o agente #5 consulte essas informações depois sem precisar de contexto no prompt
        if agente != "minuta":
            try:
                memory = MinutaMemory(session_id=session_id)
                km = get_knowledge_manager()
                await memory.adicionar_insight(interacao, knowledge_manager=km)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao adicionar insight à memória da minuta: {e}")
                # Não bloquear a resposta se houver erro na memória
        
        logger.info(f"✅ Consulta {agente} concluída para sessão {session_id}")
        
    except Exception as e:
        logger.error(f"❌ Erro na consulta: {e}", exc_info=True)
        await websocket.send_json({
            "tipo": "erro",
            "mensagem": f"Erro ao processar consulta: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })


async def handle_consolidar(
    websocket: WebSocket,
    session_id: str,
    tema: str,
    versoes: Optional[List[str]],
    sessoes: GerenciadorSessoes,
    agentes: GerenciadorAgentes
):
    """Handler para consolidação via WebSocket."""
    
    # PROBLEMA 2 CORRIGIDO: Se tema estiver vazio, consolidar toda a conversa
    sessao = await sessoes.obter_sessao(session_id)
    
    if not tema or tema.strip() == "":
        # Se não há tema específico, consolidar toda a conversa da sessão
        if sessao and sessao.interacoes:
            # Criar um tema genérico baseado nas perguntas da sessão
            perguntas = [interacao.pergunta for interacao in sessao.interacoes if interacao.pergunta]
            if perguntas:
                tema = f"Consolidação geral da sessão sobre: {', '.join(set(perguntas[:3]))}"  # Limitar a 3 perguntas
            else:
                tema = "Consolidação geral da sessão"
        else:
            tema = "Consolidação geral da sessão"
        
        await websocket.send_json({
            "tipo": "status",
            "mensagem": "🧠 Team Coordenador consolidando toda a conversa da sessão...",
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"📋 Consolidando toda a conversa (sem tema específico)")
    else:
        await websocket.send_json({
            "tipo": "status",
            "mensagem": f"🧠 Team Coordenador consolidando com instrução: {tema}",
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"📋 Consolidando com tema específico: {tema}")
    
    try:
        # Obter respostas anteriores da sessão para contexto colaborativo
        # IMPORTANTE: Limitar para evitar crescimento exponencial do prompt
        contexto_sessao = None
        if sessao and sessao.interacoes:
            # Limitar a últimas 3 interações apenas (no modo consolidar, pode ter mais contexto)
            interacoes_limitadas = sessao.interacoes[-3:] if len(sessao.interacoes) > 3 else sessao.interacoes
            
            # Converter interações anteriores em RespostaAgente
            contexto_sessao = [
                RespostaAgente(
                    agente=interacao.agente,
                    agente_nome=interacao.agente_nome,
                    pergunta=interacao.pergunta,
                    resposta=interacao.resposta,
                    artigos_citados=interacao.artigos_citados,
                    fontes_conhecimento=interacao.fontes_conhecimento,
                    confianca=interacao.confianca,
                    timestamp=interacao.timestamp
                )
                for interacao in interacoes_limitadas
            ]
            if len(sessao.interacoes) > 3:
                logger.info(f"📚 Usando apenas as últimas {len(contexto_sessao)} de {len(sessao.interacoes)} interação(ões) como contexto (limitado para evitar erro de tokens)")
            else:
                logger.info(f"📚 Usando {len(contexto_sessao)} resposta(s) anterior(es) como contexto")
        
        # Consolidar (modo colaborativo por padrão)
        # Os agentes verão as respostas uns dos outros durante a consolidação
        analise = await agentes.consolidar(
            tema=tema, 
            versoes=versoes,
            usar_colaborativo=True  # Modo colaborativo: agentes conversam entre si
        )
        
        # Salvar análise
        await sessoes.adicionar_analise(session_id, analise)
        
        # Enviar resultado
        await websocket.send_json({
            "tipo": "consolidacao_completa",
            "tema": analise.tema_analisado,
            "proposta_texto": analise.proposta_consolidada,
            "gaps": [
                {
                    "descricao": g.descricao,
                    "criticidade": g.criticidade.value,
                    "sugestao": g.sugestao_resgate
                }
                for g in analise.gaps_identificados
            ],
            "observacoes": analise.observacoes,
            "timestamp": analise.timestamp.isoformat()
        })
        
        logger.info(f"✅ Consolidação concluída para sessão {session_id}")
        
    except Exception as e:
        logger.error(f"❌ Erro na consolidação: {e}")
        await websocket.send_json({
            "tipo": "erro",
            "mensagem": f"Erro na consolidação: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })


async def handle_consultar_colaborativo(
    websocket: WebSocket,
    session_id: str,
    pergunta: str,
    versoes: Optional[List[str]],
    sessoes: GerenciadorSessoes,
    agentes: GerenciadorAgentes
):
    """Handler para consulta colaborativa via WebSocket."""
    
    await websocket.send_json({
        "tipo": "status",
        "mensagem": "🤝 Iniciando consulta colaborativa - agentes verão respostas uns dos outros...",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        # Obter contexto da sessão (limitado para evitar crescimento exponencial)
        sessao = await sessoes.obter_sessao(session_id)
        contexto_sessao = None
        if sessao and sessao.interacoes:
            # Limitar a últimas 3 interações apenas
            interacoes_limitadas = sessao.interacoes[-3:] if len(sessao.interacoes) > 3 else sessao.interacoes
            
            contexto_sessao = [
                RespostaAgente(
                    agente=interacao.agente,
                    agente_nome=interacao.agente_nome,
                    pergunta=interacao.pergunta,
                    resposta=interacao.resposta,
                    artigos_citados=interacao.artigos_citados,
                    fontes_conhecimento=interacao.fontes_conhecimento,
                    confianca=interacao.confianca,
                    timestamp=interacao.timestamp
                )
                for interacao in interacoes_limitadas
            ]
            if len(sessao.interacoes) > 3:
                logger.info(f"📚 Modo colaborativo: usando apenas as últimas {len(contexto_sessao)} de {len(sessao.interacoes)} interação(ões) como contexto (limitado para evitar erro de tokens)")
        
        # Consulta colaborativa
        respostas = await agentes.consultar_agentes_colaborativo(
            pergunta=pergunta,
            versoes=versoes,
            contexto_sessao=contexto_sessao
        )
        
        # Enviar cada resposta conforme chega
        for versao, resposta in respostas.items():
            # Enviar resposta individual
            await websocket.send_json({
                "tipo": "resposta_agente",
                "agente": resposta.agente,
                "agente_nome": resposta.agente_nome,
                "resposta": resposta.resposta,
                "artigos": resposta.artigos_citados,
                "fontes": resposta.fontes_conhecimento,
                "confianca": resposta.confianca,
                "timestamp": resposta.timestamp.isoformat(),
                "colaborativo": True  # Flag indicando que foi em modo colaborativo
            })
            
            # Salvar interação
            interacao = InteracaoAgente(
                agente=resposta.agente,
                agente_nome=resposta.agente_nome,
                pergunta=pergunta,
                resposta=resposta.resposta,
                artigos_citados=resposta.artigos_citados,
                fontes_conhecimento=resposta.fontes_conhecimento,
                confianca=resposta.confianca
            )
            await sessoes.adicionar_interacao(session_id, interacao)
        
        await websocket.send_json({
            "tipo": "status",
            "mensagem": f"✅ Consulta colaborativa concluída - {len(respostas)} agente(s) responderam",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"✅ Consulta colaborativa concluída para sessão {session_id}")
        
    except Exception as e:
        logger.error(f"❌ Erro na consulta colaborativa: {e}", exc_info=True)
        await websocket.send_json({
            "tipo": "erro",
            "mensagem": f"Erro na consulta colaborativa: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })


async def handle_finalizar(
    websocket: WebSocket,
    session_id: str,
    texto_final: Optional[str],
    observacoes: Optional[str],
    sessoes: GerenciadorSessoes
):
    """Handler para finalização de sessão via WebSocket."""
    
    try:
        # Finalizar sessão
        await sessoes.finalizar_sessao(
            session_id=session_id,
            texto_final=texto_final,
            observacoes=observacoes
        )
        
        # Exportar
        filepath = await sessoes.exportar_markdown(session_id)
        
        await websocket.send_json({
            "tipo": "sessao_finalizada",
            "arquivo": filepath,
            "mensagem": "✅ Sessão finalizada e exportada com sucesso!",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"✅ Sessão {session_id} finalizada")
        
    except Exception as e:
        logger.error(f"❌ Erro ao finalizar: {e}")
        await websocket.send_json({
            "tipo": "erro",
            "mensagem": f"Erro ao finalizar sessão: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })


async def handle_gerar_minuta(
    websocket: WebSocket,
    session_id: str,
    instrucoes: Optional[str],
    sessoes: GerenciadorSessoes,
    agentes: GerenciadorAgentes
):
    """Handler para geração de minuta atualizada via WebSocket."""
    
    await websocket.send_json({
        "tipo": "status",
        "mensagem": "🚀 Iniciando geração de minuta atualizada...",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        # Obter sessão
        sessao = await sessoes.obter_sessao(session_id)
        if not sessao:
            raise ValueError("Sessão não encontrada")
        
        # Verificar se há consolidação
        if not sessao.analises:
            await websocket.send_json({
                "tipo": "erro",
                "mensagem": "Sessão não possui consolidação. Execute a consolidação primeiro.",
                "timestamp": datetime.now().isoformat()
            })
            return
        
        await websocket.send_json({
            "tipo": "status",
            "mensagem": "📄 Obtendo minuta original via Agente #5...",
            "timestamp": datetime.now().isoformat()
        })
        
        # Obter Agente #5 e Team
        agente_minuta = agentes.obter_agente(VersaoRegulamento.MINUTA_V2.value)
        if not agente_minuta:
            raise ValueError("Agente Minuta V2 não disponível")
        
        team = agentes.team
        if not team:
            raise ValueError("Team Coordenador não disponível")
        
        # Criar gerador
        generator = MinutaGenerator(
            team_coordenador=team,
            agente_minuta=agente_minuta
        )
        
        consolidacao = sessao.analises[-1]
        
        await websocket.send_json({
            "tipo": "status",
            "mensagem": "🧠 Team Coordenador gerando minuta atualizada...",
            "timestamp": datetime.now().isoformat()
        })
        
        # Gerar minuta
        resultado = await generator.gerar_minuta_atualizada(
            session_id=session_id,
            sessao=sessao,
            consolidacao=consolidacao,
            instrucoes_usuario=instrucoes
        )
        
        if not resultado.get("sucesso"):
            await websocket.send_json({
                "tipo": "erro",
                "mensagem": f"Erro ao gerar minuta: {resultado.get('erro', 'Erro desconhecido')}",
                "timestamp": datetime.now().isoformat()
            })
            return
        
        # Enviar resultado
        await websocket.send_json({
            "tipo": "minuta_gerada",
            "arquivo": resultado["arquivo"],
            "tamanho": resultado["tamanho"],
            "linhas": resultado["linhas"],
            "validacao": resultado["validacao"],
            "mensagem": f"✅ Minuta atualizada gerada: {Path(resultado['arquivo']).name}",
            "timestamp": resultado["timestamp"]
        })
        
        logger.info(f"✅ Minuta gerada para sessão {session_id}: {resultado['arquivo']}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar minuta: {e}", exc_info=True)
        await websocket.send_json({
            "tipo": "erro",
            "mensagem": f"Erro ao gerar minuta: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })


# ============================================================================
# SERVIR FRONTEND ESTÁTICO (deve ser o último, após todos os endpoints)
# ============================================================================

# Servir frontend estático (apenas em produção ou se configurado)
# IMPORTANTE: Deve ser adicionado DEPOIS de todos os outros endpoints
# para que as rotas da API tenham prioridade sobre o frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
SERVE_FRONTEND = os.getenv("SERVE_FRONTEND", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

# Servir frontend se: SERVE_FRONTEND=true OU se estiver em produção
if FRONTEND_DIR.exists() and (SERVE_FRONTEND or ENVIRONMENT == "production"):
    # Montar frontend na raiz, mas apenas para rotas que não começam com /api, /docs, /ws, etc.
    # FastAPI já prioriza rotas definidas antes do mount
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    logger.info(f"📱 Frontend será servido de: {FRONTEND_DIR}")
else:
    logger.info(f"📱 Frontend não será servido (SERVE_FRONTEND={SERVE_FRONTEND}, ENVIRONMENT={ENVIRONMENT})")


# ============================================================================
# EXECUTAR
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Obter configurações de ambiente
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("ENVIRONMENT", "development") == "development"
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
