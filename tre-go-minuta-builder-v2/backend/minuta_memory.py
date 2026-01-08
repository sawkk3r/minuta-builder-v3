# ============================================================================
# ARQUIVO: backend/minuta_memory.py
# Sistema de Mini Memória para Minuta V2
# Salva insights relevantes das respostas em arquivos e indexa na knowledge base
# ============================================================================

import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from models import InteracaoAgente, RespostaAgente


class MinutaMemory:
    """
    Sistema de mini memória persistente para Minuta V2.
    
    Funcionalidade:
    - Extrai insights relevantes das respostas dos agentes (exceto agente #5/minuta)
    - Salva em arquivos .txt na pasta files/regulamentos/minuta/
    - Adiciona automaticamente à knowledge base do agente #5
    - Permite que o agente #5 consulte essas informações quando necessário
    """
    
    def __init__(
        self,
        files_dir: str = "files/regulamentos/minuta",
        session_id: Optional[str] = None
    ):
        """
        Inicializa o sistema de memória.
        
        Args:
            files_dir: Diretório onde serão salvos os arquivos de memória
            session_id: ID da sessão atual (para organizar arquivos por sessão)
        """
        # Usar caminho absoluto relativo ao diretório do projeto
        base_dir = Path(__file__).resolve().parent.parent
        self.files_dir = (base_dir / files_dir).resolve()
        self.files_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_id = session_id
        logger.info(f"📝 MinutaMemory inicializado: {self.files_dir}")
    
    def _extrair_insights(
        self,
        interacao: InteracaoAgente,
        agente_nome: str
    ) -> Optional[str]:
        """
        Extrai insights relevantes para a Minuta V2 de uma interação.
        
        Args:
            interacao: Interação do agente
            agente_nome: Nome do agente
            
        Returns:
            Texto com insights formatados ou None se não houver conteúdo relevante
        """
        # Ignorar respostas do próprio agente #5 (minuta)
        if interacao.agente == "minuta":
            return None
        
        # Extrair informações relevantes
        insights = []
        
        # Título/cabeçalho
        timestamp = interacao.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        insights.append(f"# Insights para Minuta V2 - {agente_nome}")
        insights.append(f"**Sessão:** {self.session_id or 'N/A'} | **Data:** {timestamp}")
        insights.append(f"**Artigo/Tema:** {interacao.pergunta[:200] if len(interacao.pergunta) > 200 else interacao.pergunta}")
        insights.append("")
        
        # Resposta do agente (resumida se muito longa)
        resposta_texto = interacao.resposta
        if len(resposta_texto) > 3000:
            resposta_texto = resposta_texto[:3000] + "\n\n[... texto truncado para economizar espaço ...]"
        
        insights.append("## Conteúdo Relevante:")
        insights.append(resposta_texto)
        insights.append("")
        
        # Artigos citados (importante para referência)
        if interacao.artigos_citados:
            insights.append("## Artigos/Dispositivos Citados:")
            for artigo in interacao.artigos_citados[:10]:  # Limitar a 10
                insights.append(f"- {artigo}")
            insights.append("")
        
        # Fontes de conhecimento
        if interacao.fontes_conhecimento:
            insights.append("## Fontes Consultadas:")
            for fonte in interacao.fontes_conhecimento[:5]:  # Limitar a 5
                insights.append(f"- {fonte}")
            insights.append("")
        
        # Informação de confiança
        if interacao.confianca:
            insights.append(f"**Confiança da Resposta:** {interacao.confianca*100:.0f}%")
            insights.append("")
        
        insights.append("---")
        insights.append("")
        
        return "\n".join(insights)
    
    async def adicionar_insight(
        self,
        interacao: InteracaoAgente,
        knowledge_manager=None
    ) -> Optional[Path]:
        """
        Adiciona insight de uma interação à memória da minuta.
        
        Args:
            interacao: Interação do agente
            knowledge_manager: Instância do KnowledgeManager para indexar automaticamente
            
        Returns:
            Caminho do arquivo criado ou None se não foi possível criar
        """
        # Ignorar respostas do próprio agente #5 (minuta) - ele não precisa salvar insights sobre si mesmo
        if interacao.agente == "minuta":
            logger.debug(f"⏭️ Pulando salvamento de insight do agente #5 (minuta)")
            return None
        
        try:
            # Extrair insights
            insight_texto = self._extrair_insights(interacao, interacao.agente_nome)
            
            if not insight_texto:
                return None
            
                # Criar nome do arquivo único baseado em timestamp e agente
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_prefix = f"{self.session_id}_" if self.session_id else ""
            # Usar apenas primeiros caracteres do session_id se muito longo
            session_short = session_id[:8] if session_id and len(session_id) > 8 else (session_id or "")
            filename = f"{session_short}_memoria_{interacao.agente}_{timestamp_str}.txt" if session_short else f"memoria_{interacao.agente}_{timestamp_str}.txt"
            filepath = self.files_dir / filename
            
            # Salvar arquivo
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(insight_texto)
            
            logger.info(f"💾 Insight salvo: {filename} ({len(insight_texto)} caracteres)")
            
            # Se knowledge_manager foi fornecido, indexar automaticamente
            if knowledge_manager:
                try:
                    # Adicionar à knowledge base da minuta
                    knowledge = knowledge_manager.obter_knowledge("minuta")
                    if knowledge:
                        # Adicionar conteúdo à knowledge base usando método assíncrono
                        # Importar TextReader
                        from agno.knowledge.reader.text_reader import TextReader
                        
                        # Usar add_content_async (como no knowledge_manager)
                        await knowledge.add_content_async(
                            path=str(filepath),
                            reader=TextReader(),
                            metadata={
                                "tipo": "memoria_sessao",
                                "session_id": self.session_id or "N/A",
                                "agente_origem": interacao.agente,
                                "timestamp": timestamp_str
                            },
                            skip_if_exists=False  # Sempre adicionar (arquivo único por timestamp)
                        )
                        logger.info(f"✅ Insight indexado na knowledge base da minuta: {filename}")
                    else:
                        logger.warning(f"⚠️ Knowledge base 'minuta' não encontrada - insight salvo mas não indexado")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao indexar insight: {e}", exc_info=True)
                    # Continuar mesmo se não conseguir indexar - arquivo foi salvo
                    logger.info(f"💡 Arquivo salvo em {filepath} - será indexado na próxima reindexação da minuta")
            
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar insight à memória: {e}")
            return None
    
    def listar_insights_sessao(self, session_id: str) -> List[Path]:
        """
        Lista todos os arquivos de insight de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Lista de caminhos dos arquivos
        """
        if not session_id:
            return []
        
        # Usar primeiros 8 caracteres para buscar (nome do arquivo usa versão curta)
        session_short = session_id[:8] if len(session_id) > 8 else session_id
        pattern = f"{session_short}_memoria_*.txt"
        arquivos = list(self.files_dir.glob(pattern))
        return sorted(arquivos)
    
    def limpar_insights_sessao(self, session_id: str) -> int:
        """
        Remove todos os arquivos de insight de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Número de arquivos removidos
        """
        arquivos = self.listar_insights_sessao(session_id)
        removidos = 0
        
        for arquivo in arquivos:
            try:
                arquivo.unlink()
                removidos += 1
            except Exception as e:
                logger.warning(f"⚠️ Erro ao remover arquivo {arquivo}: {e}")
        
        if removidos > 0:
            logger.info(f"🗑️ Removidos {removidos} arquivo(s) de insight da sessão {session_id}")
        
        return removidos
