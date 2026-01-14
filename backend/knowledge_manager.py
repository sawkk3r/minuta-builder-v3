# ============================================================================
# ARQUIVO: backend/knowledge_manager.py
# Gerenciador de Knowledge Base usando Agno + LanceDB
# ============================================================================

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Tentar importar dependências do Agno
try:
    from agno.knowledge.knowledge import Knowledge
    from agno.knowledge.embedder.openai import OpenAIEmbedder
    from agno.vectordb.lancedb import LanceDb
    from agno.db.sqlite import SqliteDb
    from agno.knowledge.reader.text_reader import TextReader
    from agno.knowledge.reader.pdf_reader import PDFReader
    AGNO_KNOWLEDGE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Agno Knowledge não disponível: {e}")
    logger.warning("   Instale com: pip install agno[lancedb]")
    AGNO_KNOWLEDGE_AVAILABLE = False


class KnowledgeManager:
    """
    Gerencia as bases de conhecimento para cada versão do regulamento.
    
    Estrutura:
    - Uma Knowledge base por versão do regulamento
    - Cada base indexa os PDFs correspondentes
    - Usa LanceDB como vector store (local, sem servidor)
    - Usa SQLite para metadados dos conteúdos
    """
    
    # Mapeamento de versões para arquivos
    # NOTA: O sistema tenta múltiplas extensões e busca automaticamente se necessário
    VERSOES_ARQUIVOS = {
        "1997": {
            "nome": "Resolução 05/1997",
            "descricao": "Regulamento Interno original do TRE-GO",
            "arquivos": ["1997_Resolucao_05.txt", "1997_Resolucao_05.pdf"]  # Tentar ambas extensões
        },
        "2007": {
            "nome": "Resolução 113/2007",
            "descricao": "Regulamento Interno atualizado em 2007",
            "arquivos": ["2007_Resolucao_113.txt", "2007_Resolucao_113.pdf"]
        },
        "2017": {
            "nome": "Resolução 275/2017",
            "descricao": "Regulamento Interno vigente desde 2017",
            "arquivos": ["2017_Resolucao_275.txt", "2017_Resolucao_275.pdf"]
        },
        "alteracoes": {
            "nome": "Alterações 2021-2025",
            "descricao": "Resoluções que alteraram o regulamento entre 2021 e 2025",
            "arquivos": [
                "alteracoes_menores/Res_349_2021.pdf",
                "alteracoes_menores/Res_369_2022.pdf",
                "alteracoes_menores/Res_371_2022.pdf",
                "alteracoes_menores/Res_372_2022.pdf",
                "alteracoes_menores/Res_377_2022.pdf",
                "alteracoes_menores/Res_405_2024.pdf"
            ]
        },
        "minuta": {
            "nome": "Minuta V2",
            "descricao": "Minuta em construção do novo regulamento interno",
            # IMPORTANTE: esta lista precisa ter itens separados; uma string "a, b"
            # faz o indexador procurar um arquivo literalmente com vírgula no nome.
            "arquivos": ["minuta.pdf", "minuta.txt"]
        }
    }
    
    def __init__(
        self,
        files_dir: str = "files/regulamentos",
        db_dir: str = "tmp",
        embedder_model: str = "text-embedding-3-small"
    ):
        """
        Inicializa o gerenciador de knowledge.
        
        Args:
            files_dir: Diretório onde estão os PDFs dos regulamentos
            db_dir: Diretório para armazenar databases (LanceDB + SQLite)
            embedder_model: Modelo de embedding a usar
        """
        # Usar caminho absoluto relativo ao diretório do projeto
        base_dir = Path(__file__).resolve().parent.parent
        self.files_dir = (base_dir / files_dir).resolve()
        self.db_dir = (base_dir / db_dir).resolve()
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedder_model = embedder_model
        self.knowledge_bases: Dict[str, Knowledge] = {}
        self._initialized = False
        
        # Database SQLite compartilhado para metadados
        self.sqlite_db_path = self.db_dir / "knowledge_metadata.db"
        
    async def inicializar(self) -> bool:
        """
        Inicializa todas as bases de conhecimento.
        
        Returns:
            True se inicialização bem-sucedida
        """
        if not AGNO_KNOWLEDGE_AVAILABLE:
            logger.error("❌ Agno Knowledge não está disponível. Não é possível inicializar.")
            return False
        
        logger.info("🚀 Inicializando Knowledge Manager...")
        
        # Verificar API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OPENAI_API_KEY não encontrada no ambiente")
            return False
        
        # Criar embedder compartilhado
        embedder = OpenAIEmbedder(
            id=self.embedder_model,
            api_key=api_key
        )
        
        # Criar knowledge base para cada versão
        for versao, config in self.VERSOES_ARQUIVOS.items():
            try:
                logger.info(f"📚 Criando knowledge base para: {config['nome']}")
                
                # Database SQLite para metadados desta versão
                contents_db = SqliteDb(
                    db_file=str(self.db_dir / f"contents_{versao}.db")
                )
                
                # LanceDB para vetores
                lance_uri = str(self.db_dir / f"lancedb_{versao}")
                lance_table_name = f"regulamento_{versao}"
                
                vector_db = LanceDb(
                    uri=lance_uri,
                    table_name=lance_table_name,
                    embedder=embedder
                )
                
                # IMPORTANTE: Forçar carregamento da tabela existente se houver
                # O Agno às vezes não carrega automaticamente tabelas pré-existentes
                try:
                    import lancedb
                    lance_conn = lancedb.connect(lance_uri)
                    if lance_table_name in lance_conn.table_names():
                        # Tabela existe - forçar carregamento
                        vector_db.table = lance_conn.open_table(lance_table_name)
                        logger.info(f"   📂 Tabela '{lance_table_name}' carregada do disco")
                except Exception as e:
                    logger.debug(f"   ⚠️ Não foi possível carregar tabela existente: {e}")
                
                # Criar Knowledge
                # IMPORTANTE: Há um bug conhecido do Agno onde usar contents_db junto com vector_db
                # pode impedir a criação de embeddings (vetores ficam None).
                # Para a minuta, vamos usar APENAS vector_db como workaround.
                if versao == "minuta":
                    logger.warning(f"   ⚠️ Usando APENAS vector_db para '{versao}' (workaround para bug do Agno)")
                    knowledge = Knowledge(
                        name=f"knowledge_{versao}",
                        description=config["descricao"],
                        vector_db=vector_db
                        # NÃO passar contents_db para minuta
                    )
                else:
                    knowledge = Knowledge(
                        name=f"knowledge_{versao}",
                        description=config["descricao"],
                        vector_db=vector_db,
                        contents_db=contents_db
                    )
                
                self.knowledge_bases[versao] = knowledge
                logger.info(f"   ✅ Knowledge base '{versao}' criada")
                
            except Exception as e:
                logger.error(f"   ❌ Erro ao criar knowledge base '{versao}': {e}")
                continue
        
        self._initialized = True
        logger.info(f"✅ Knowledge Manager inicializado com {len(self.knowledge_bases)} bases")
        return True
    
    async def indexar_documentos(self, versao: Optional[str] = None, force: bool = False) -> Dict[str, bool]:
        """
        Indexa documentos PDF nas bases de conhecimento.
        
        Args:
            versao: Versão específica para indexar (None = todas)
            force: Se True, reindexar mesmo se já existir
                  ⚠️ NOTA: Quando force=True ou ao reindexar, o LanceDB/Agno pode
                  deletar registros existentes com o mesmo content_hash antes de
                  inserir novos. Isso é comportamento normal para evitar duplicatas.
            
        Returns:
            Dicionário com status de indexação por versão
        """
        if not self._initialized:
            logger.warning("⚠️ Knowledge Manager não inicializado. Inicializando...")
            await self.inicializar()
        
        resultados = {}
        versoes_para_indexar = [versao] if versao else list(self.VERSOES_ARQUIVOS.keys())
        
        for v in versoes_para_indexar:
            if v not in self.knowledge_bases:
                logger.warning(f"⚠️ Knowledge base '{v}' não encontrada")
                resultados[v] = False
                continue
            
            config = self.VERSOES_ARQUIVOS[v]
            knowledge = self.knowledge_bases[v]
            
            logger.info(f"📄 Indexando documentos para: {config['nome']}")
            
            try:
                # Tentar arquivos na ordem da lista até encontrar um que exista
                arquivos_encontrados = []
                arquivos_tentados = set()  # Evitar duplicatas
                
                for arquivo in config["arquivos"]:
                    # Normalizar caminho (resolver .. e caminhos relativos)
                    filepath = (self.files_dir / arquivo).resolve()
                    
                    # Verificar se já tentamos este caminho
                    if str(filepath) in arquivos_tentados:
                        continue
                    arquivos_tentados.add(str(filepath))
                    
                    if filepath.exists():
                        arquivos_encontrados.append(arquivo)
                        logger.debug(f"   ✅ Arquivo encontrado: {filepath}")
                    else:
                        logger.debug(f"   ⚠️ Arquivo não encontrado: {filepath}")
                
                # Para "alteracoes", SEMPRE buscar todos os arquivos no diretório alteracoes_menores
                # Isso permite adicionar novos arquivos sem precisar atualizar o código
                if v == "alteracoes":
                    logger.info(f"   🔍 Buscando TODOS os arquivos em alteracoes_menores/...")
                    alteracoes_dir = self.files_dir / "alteracoes_menores"
                    arquivos_ja_adicionados = set(arquivos_encontrados)  # Manter os que já foram encontrados
                    
                    logger.info(f"   📂 Caminho do diretório: {alteracoes_dir}")
                    logger.info(f"   📂 Diretório existe: {alteracoes_dir.exists()}")
                    logger.info(f"   📂 É diretório: {alteracoes_dir.is_dir() if alteracoes_dir.exists() else False}")
                    
                    if alteracoes_dir.exists() and alteracoes_dir.is_dir():
                        # Buscar TODOS os arquivos PDF e TXT no diretório alteracoes_menores
                        arquivos_encontrados_no_dir = []
                        for ext in ['.txt', '.pdf']:
                            pattern = f"*{ext}"
                            logger.info(f"   🔍 Buscando arquivos com padrão: {pattern}")
                            for filepath in alteracoes_dir.glob(pattern):
                                rel_path = filepath.relative_to(self.files_dir)
                                rel_path_str = str(rel_path)
                                arquivos_encontrados_no_dir.append(rel_path_str)
                                logger.info(f"   📄 Arquivo encontrado no diretório: {filepath.name} → {rel_path_str}")
                                
                                # Adicionar apenas se ainda não foi adicionado
                                if rel_path_str not in arquivos_ja_adicionados:
                                    arquivos_encontrados.append(rel_path_str)
                                    arquivos_ja_adicionados.add(rel_path_str)
                                    logger.info(f"   ✅ Adicionado à lista: {rel_path_str}")
                        
                        if not arquivos_encontrados_no_dir:
                            logger.warning(f"   ⚠️ Nenhum arquivo PDF ou TXT encontrado em {alteracoes_dir}")
                            # Listar todos os arquivos no diretório para debug
                            try:
                                todos_arquivos = list(alteracoes_dir.iterdir())
                                logger.info(f"   📋 Arquivos no diretório ({len(todos_arquivos)} total):")
                                for f in todos_arquivos:
                                    logger.info(f"      - {f.name} ({'arquivo' if f.is_file() else 'diretório'})")
                            except Exception as e:
                                logger.warning(f"   ⚠️ Erro ao listar arquivos: {e}")
                    else:
                        logger.error(f"   ❌ Diretório alteracoes_menores não existe ou não é um diretório: {alteracoes_dir}")
                    
                    # Também procurar arquivos que começam com "Res_" na raiz (backward compatibility)
                    for ext in ['.txt', '.pdf']:
                        for filepath in self.files_dir.glob(f"Res_*{ext}"):
                            rel_path = filepath.relative_to(self.files_dir)
                            rel_path_str = str(rel_path)
                            if rel_path_str not in arquivos_ja_adicionados:
                                arquivos_encontrados.append(rel_path_str)
                                arquivos_ja_adicionados.add(rel_path_str)
                                logger.info(f"   ✅ Encontrado na raiz: {rel_path}")
                    
                    if len(arquivos_encontrados) > 0:
                        logger.info(f"   📋 Total de {len(arquivos_encontrados)} arquivo(s) de alterações encontrado(s)")
                    else:
                        logger.error(f"   ❌ NENHUM arquivo de alterações encontrado!")

                # Para "minuta", se o usuário renomear o arquivo (ex: "Minuta V2.txt"),
                # tentamos descobrir automaticamente qualquer *minuta*.{txt,pdf} na pasta base.
                if v == "minuta" and not arquivos_encontrados:
                    logger.info("   🔍 Tentando descobrir arquivos da minuta automaticamente (*minuta*.txt/.pdf)...")
                    candidatos = []
                    for ext in [".txt", ".pdf"]:
                        for filepath in self.files_dir.glob(f"*minuta*{ext}"):
                            rel_path = filepath.relative_to(self.files_dir)
                            candidatos.append(str(rel_path))

                    # Deduplicar preservando ordem
                    vistos = set()
                    for c in candidatos:
                        if c not in vistos:
                            arquivos_encontrados.append(c)
                            vistos.add(c)
                            logger.info(f"   ✅ Encontrado: {c}")
                
                if not arquivos_encontrados:
                    logger.warning(f"   ❌ Nenhum arquivo encontrado para {config['nome']}")
                    logger.warning(f"   💡 Verifique se os arquivos estão em: {self.files_dir}")
                    logger.warning(f"   💡 Para '{v}', estava procurando por: {config['arquivos']}")
                    resultados[v] = False
                    continue
                
                logger.info(f"   📋 Total de {len(arquivos_encontrados)} arquivo(s) encontrado(s) para indexar")
                for arquivo_encontrado in arquivos_encontrados:
                    logger.info(f"      - {arquivo_encontrado}")
                
                # Processar apenas arquivos encontrados
                for arquivo in arquivos_encontrados:
                    filepath = self.files_dir / arquivo
                    
                    # Verificar se já foi indexado (apenas se não forçar)
                    arquivo_ja_indexado = False
                    arquivo_modificado = False
                    
                    if not force:
                        # Verificar se o arquivo foi modificado recentemente
                        try:
                            if filepath.exists():
                                mtime_arquivo = filepath.stat().st_mtime
                                logger.debug(f"   📅 Arquivo modificado em: {mtime_arquivo}")
                                
                                # Verificar se há dados na tabela
                                try:
                                    table = knowledge.vector_db.table if hasattr(knowledge.vector_db, 'table') else None
                                    if table is not None:
                                        try:
                                            # Tentar contar registros
                                            if hasattr(table, 'count_rows'):
                                                count = table.count_rows()
                                                if count is not None and count > 0:
                                                    arquivo_ja_indexado = True
                                                    logger.debug(f"   ✓ Tabela já contém {count} registros")
                                                    
                                                    # IMPORTANTE: Mesmo se já indexado, não pulamos se force=False
                                                    # porque o Agno (skip_if_exists) verifica content_hash
                                                    # Se o arquivo foi modificado, o hash mudou e será reindexado
                                                    logger.info(f"   ⚠️  Arquivo já indexado, mas verificando se foi modificado...")
                                                    logger.info(f"   💡 Se o arquivo foi alterado, será reindexado automaticamente pelo Agno")
                                            # Fallback: tentar ler uma amostra
                                            elif hasattr(table, 'head'):
                                                sample = table.head(1)
                                                if sample is not None and len(sample) > 0:
                                                    arquivo_ja_indexado = True
                                                    logger.debug(f"   ✓ Tabela já contém dados")
                                                    logger.info(f"   ⚠️  Arquivo já indexado, mas verificando se foi modificado...")
                                                    logger.info(f"   💡 Se o arquivo foi alterado, será reindexado automaticamente pelo Agno")
                                        except Exception as e:
                                            logger.debug(f"   ⚠️ Não foi possível verificar tabela: {e}")
                                except Exception as e:
                                    logger.debug(f"   ⚠️ Erro ao acessar tabela: {e}")
                        except Exception as e:
                            logger.debug(f"   ⚠️ Erro ao verificar data de modificação: {e}")
                        
                        # NÃO PULAR o arquivo mesmo se já indexado
                        # O Agno com skip_if_exists=True verifica content_hash
                        # Se o arquivo foi modificado, o hash mudou e será reindexado automaticamente
                        # Se não foi modificado, será pulado pelo Agno (sem custos de API)
                        if arquivo_ja_indexado:
                            logger.info(f"   📋 Arquivo {arquivo} já foi indexado anteriormente")
                            logger.info(f"   🔍 Verificando se houve modificações (Agno verifica content_hash)...")
                            # Continue o processamento - deixe o Agno decidir com skip_if_exists
                    
                    logger.info(f"   📥 Processando: {arquivo}" + (" (forçado)" if force else ""))
                    
                    # Determinar reader baseado na extensão do arquivo
                    reader = None
                    if filepath.suffix.lower() == '.txt':
                        reader = TextReader()
                    elif filepath.suffix.lower() == '.pdf':
                        reader = PDFReader()
                    # Se não especificar reader, o Agno tenta detectar automaticamente
                    
                    # Adicionar conteúdo ao knowledge base
                    # IMPORTANTE: skip_if_exists=True faz o Agno verificar content_hash ANTES de criar embeddings
                    # Se o arquivo já existe (mesmo content_hash), ele não cria novos embeddings
                    # Isso economiza chamadas à API da OpenAI
                    params = {
                        "path": str(filepath),
                        "skip_if_exists": not force  # True = pular se já existe (verifica content_hash)
                    }
                    if reader:
                        params["reader"] = reader
                    
                    # Adicionar metadata para facilitar rastreamento
                    params["metadata"] = {
                        "versao": v,
                        "arquivo": arquivo,
                        "tipo": config.get("nome", v)
                    }
                    
                    try:
                        await knowledge.add_content_async(**params)
                        # Se chegou aqui sem erro, o arquivo foi processado
                        # Se skip_if_exists=True e arquivo não mudou, foi pulado (sem custos)
                        # Se arquivo foi modificado, foi reindexado (novos embeddings criados)
                        if arquivo_ja_indexado:
                            logger.info(f"   ✅ {arquivo} verificado - reindexado se modificado, ou mantido se inalterado")
                        else:
                            logger.info(f"   ✅ {arquivo} processado e indexado com sucesso")
                    except Exception as e:
                        # Se o erro for relacionado a arquivo já existir, é OK (skip_if_exists funcionou)
                        error_msg = str(e).lower()
                        if "already exists" in error_msg or "já existe" in error_msg or "skip" in error_msg:
                            if arquivo_ja_indexado:
                                logger.info(f"   ✅ {arquivo} não foi modificado (mantido no banco - sem custos de API)")
                            else:
                                logger.info(f"   ⏭️  {arquivo} já existe no banco (pulado pelo Agno - sem custos de API)")
                        else:
                            logger.error(f"   ❌ Erro ao processar {arquivo}: {e}")
                            raise
                
                resultados[v] = True
                
            except Exception as e:
                logger.error(f"   ❌ Erro ao indexar '{v}': {e}")
                resultados[v] = False
        
        return resultados
    
    def obter_knowledge(self, versao: str) -> Optional[Knowledge]:
        """
        Obtém a knowledge base de uma versão específica.
        
        Args:
            versao: Versão do regulamento
            
        Returns:
            Knowledge base ou None se não existir
        """
        return self.knowledge_bases.get(versao)
    
    async def buscar(
        self,
        versao: str,
        query: str,
        num_results: int = 5
    ) -> List[Dict]:
        """
        Busca semântica em uma versão específica.
        
        Args:
            versao: Versão do regulamento
            query: Consulta de busca
            num_results: Número de resultados
            
        Returns:
            Lista de resultados relevantes
        """
        knowledge = self.obter_knowledge(versao)
        if not knowledge:
            logger.warning(f"⚠️ Knowledge base '{versao}' não encontrada")
            return []
        
        # IMPORTANTE: Garantir que a tabela está carregada antes de buscar
        # O Agno às vezes perde a referência da tabela, especialmente após reindexação
        try:
            if hasattr(knowledge, 'vector_db') and hasattr(knowledge.vector_db, 'table'):
                vector_db = knowledge.vector_db
                if vector_db.table is None:
                    # Tabela não está carregada - forçar recarregamento
                    lance_uri = vector_db.uri if hasattr(vector_db, 'uri') else str(self.db_dir / f"lancedb_{versao}")
                    lance_table_name = vector_db.table_name if hasattr(vector_db, 'table_name') else f"regulamento_{versao}"
                    
                    try:
                        import lancedb
                        lance_conn = lancedb.connect(lance_uri)
                        if lance_table_name in lance_conn.table_names():
                            vector_db.table = lance_conn.open_table(lance_table_name)
                            logger.debug(f"   🔄 Tabela '{lance_table_name}' recarregada para busca")
                    except Exception as e:
                        logger.debug(f"   ⚠️ Erro ao recarregar tabela: {e}")
        except Exception as e:
            logger.debug(f"   ⚠️ Erro ao verificar tabela antes da busca: {e}")
        
        try:
            # Buscar no knowledge base
            # CORREÇÃO: O método correto é async_search com max_results (não num_documents)
            results = await knowledge.async_search(query=query, max_results=num_results)
            
            # Tratamento defensivo: verificar se results é válido e não vazio
            if not results:
                logger.debug(f"Nenhum resultado encontrado para query: {query[:50]}...")
                return []
            
            # Converter resultados com tratamento de erros
            documentos = []
            for i, r in enumerate(results):
                try:
                    documentos.append({
                        "content": r.content if hasattr(r, 'content') else str(r),
                        "metadata": r.metadata if hasattr(r, 'metadata') else {},
                        "score": r.score if hasattr(r, 'score') else 0.0
                    })
                except (IndexError, AttributeError, KeyError) as e:
                    logger.warning(f"Erro ao processar resultado {i} da busca em '{versao}': {e}")
                    continue  # Pular este resultado e continuar
            
            return documentos
            
        except (IndexError, AttributeError) as e:
            logger.error(f"Error searching for documents in '{versao}': {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"❌ Erro na busca em '{versao}': {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def status(self) -> Dict[str, any]:
        """Retorna status das bases de conhecimento."""
        return {
            "inicializado": self._initialized,
            "bases_disponiveis": list(self.knowledge_bases.keys()),
            "total_bases": len(self.knowledge_bases),
            "diretorio_arquivos": str(self.files_dir),
            "diretorio_db": str(self.db_dir),
            "agno_disponivel": AGNO_KNOWLEDGE_AVAILABLE
        }


# ============================================================================
# SINGLETON GLOBAL
# ============================================================================

_knowledge_manager: Optional[KnowledgeManager] = None


def get_knowledge_manager() -> KnowledgeManager:
    """Obtém instância global do KnowledgeManager."""
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = KnowledgeManager()
    return _knowledge_manager


async def inicializar_knowledge_global() -> bool:
    """Inicializa o KnowledgeManager global."""
    manager = get_knowledge_manager()
    return await manager.inicializar()
