# ============================================================================
# ARQUIVO: backend/session_manager.py
# Gerenciador de Sessões com persistência SQLite via Agno
# ============================================================================

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

from models import (
    SessaoAnalise, InteracaoAgente, AnaliseEvolutiva,
    StatusConsulta, TextoConsolidado
)

# Tentar importar Agno para persistência
try:
    from agno.db.sqlite import SqliteDb
    AGNO_DB_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Agno DB não disponível. Usando persistência em arquivo JSON.")
    AGNO_DB_AVAILABLE = False


class GerenciadorSessoes:
    """
    Gerencia sessões de análise com persistência.
    
    Funcionalidades:
    - Criar, obter, atualizar sessões
    - Persistir em SQLite (via Agno) ou JSON (fallback)
    - Exportar sessões em Markdown
    - Histórico completo de interações
    """
    
    def __init__(
        self,
        db_dir: str = "tmp",
        exports_dir: str = "exports"
    ):
        self.db_dir = Path(db_dir)
        self.exports_dir = Path(exports_dir)
        
        # Criar diretórios
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache em memória
        self._sessoes_cache: Dict[str, SessaoAnalise] = {}
        
        # Database SQLite
        self.db: Optional[SqliteDb] = None
        self._json_file = self.db_dir / "sessoes_backup.json"
        
        # Inicializar
        self._inicializar_db()
    
    def _inicializar_db(self):
        """Inicializa conexão com database."""
        if AGNO_DB_AVAILABLE:
            try:
                self.db = SqliteDb(
                    db_file=str(self.db_dir / "sessoes.db"),
                    session_table="sessoes_analise"
                )
                logger.info("✅ SQLite inicializado para sessões")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar SQLite: {e}")
                self.db = None
        
        # Carregar sessões existentes
        self._carregar_sessoes()
    
    def _carregar_sessoes(self):
        """Carrega sessões do armazenamento."""
        # Tentar carregar do JSON (backup)
        if self._json_file.exists():
            try:
                with open(self._json_file, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                
                for sessao_data in dados.get('sessoes', []):
                    try:
                        sessao = SessaoAnalise(**sessao_data)
                        self._sessoes_cache[sessao.id] = sessao
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao carregar sessão: {e}")
                
                logger.info(f"📂 {len(self._sessoes_cache)} sessões carregadas do backup")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao carregar sessões do JSON: {e}")
    
    def _salvar_backup_json(self):
        """Salva backup das sessões em JSON."""
        try:
            dados = {
                'atualizado_em': datetime.now().isoformat(),
                'sessoes': []
            }
            
            for sessao in self._sessoes_cache.values():
                # Serializar sessão
                sessao_dict = {
                    'id': sessao.id,
                    'artigo': sessao.artigo,
                    'titulo': sessao.titulo,
                    'usuario': sessao.usuario,
                    'status': sessao.status.value,
                    'data_criacao': sessao.data_criacao.isoformat(),
                    'data_atualizacao': sessao.data_atualizacao.isoformat(),
                    'texto_final_minuta': sessao.texto_final_minuta,
                    'observacoes_finais': sessao.observacoes_finais,
                    'interacoes': [
                        {
                            'id': i.id,
                            'agente': i.agente,
                            'agente_nome': i.agente_nome,
                            'pergunta': i.pergunta,
                            'resposta': i.resposta,
                            'artigos_citados': i.artigos_citados,
                            'fontes_conhecimento': i.fontes_conhecimento,
                            'confianca': i.confianca,
                            'timestamp': i.timestamp.isoformat()
                        }
                        for i in sessao.interacoes
                    ],
                    'analises': []  # Simplificado por agora
                }
                dados['sessoes'].append(sessao_dict)
            
            with open(self._json_file, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"💾 Backup JSON salvo: {len(dados['sessoes'])} sessões")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar backup JSON: {e}")
    
    async def criar_sessao(
        self,
        artigo: str,
        titulo: str,
        usuario: str = "usuario_padrao"
    ) -> SessaoAnalise:
        """
        Cria nova sessão de análise.
        
        Args:
            artigo: Identificador do artigo (ex: "Art. 47")
            titulo: Título descritivo
            usuario: ID do usuário
            
        Returns:
            Nova sessão criada
        """
        sessao = SessaoAnalise(
            artigo=artigo,
            titulo=titulo,
            usuario=usuario
        )
        
        # Salvar em cache
        self._sessoes_cache[sessao.id] = sessao
        
        # Persistir
        self._salvar_backup_json()
        
        logger.info(f"📝 Sessão criada: {sessao.id} - {artigo}")
        return sessao
    
    async def obter_sessao(self, session_id: str) -> Optional[SessaoAnalise]:
        """Obtém sessão por ID."""
        return self._sessoes_cache.get(session_id)
    
    async def listar_sessoes(
        self,
        usuario: Optional[str] = None,
        status: Optional[StatusConsulta] = None,
        limite: int = 50
    ) -> List[SessaoAnalise]:
        """Lista sessões com filtros opcionais."""
        sessoes = list(self._sessoes_cache.values())
        
        # Filtrar por usuário
        if usuario:
            sessoes = [s for s in sessoes if s.usuario == usuario]
        
        # Filtrar por status
        if status:
            sessoes = [s for s in sessoes if s.status == status]
        
        # Ordenar por data (mais recente primeiro)
        sessoes.sort(key=lambda s: s.data_atualizacao, reverse=True)
        
        return sessoes[:limite]
    
    async def adicionar_interacao(
        self,
        session_id: str,
        interacao: InteracaoAgente
    ) -> bool:
        """Adiciona interação a uma sessão."""
        sessao = await self.obter_sessao(session_id)
        if not sessao:
            logger.warning(f"⚠️ Sessão não encontrada: {session_id}")
            return False
        
        sessao.interacoes.append(interacao)
        sessao.data_atualizacao = datetime.now()
        
        # Persistir
        self._salvar_backup_json()
        
        logger.info(f"📊 Interação adicionada à sessão {session_id}")
        return True
    
    async def adicionar_analise(
        self,
        session_id: str,
        analise: AnaliseEvolutiva
    ) -> bool:
        """Adiciona análise evolutiva a uma sessão."""
        sessao = await self.obter_sessao(session_id)
        if not sessao:
            return False
        
        sessao.analises.append(analise)
        sessao.data_atualizacao = datetime.now()
        
        self._salvar_backup_json()
        return True
    
    async def atualizar_status(
        self,
        session_id: str,
        status: StatusConsulta
    ) -> bool:
        """Atualiza status de uma sessão."""
        sessao = await self.obter_sessao(session_id)
        if not sessao:
            return False
        
        sessao.status = status
        sessao.data_atualizacao = datetime.now()
        
        self._salvar_backup_json()
        return True
    
    async def finalizar_sessao(
        self,
        session_id: str,
        texto_final: Optional[str] = None,
        observacoes: Optional[str] = None
    ) -> bool:
        """Finaliza uma sessão."""
        sessao = await self.obter_sessao(session_id)
        if not sessao:
            return False
        
        sessao.status = StatusConsulta.CONCLUIDA
        sessao.texto_final_minuta = texto_final
        sessao.observacoes_finais = observacoes
        sessao.data_atualizacao = datetime.now()
        
        self._salvar_backup_json()
        logger.info(f"✅ Sessão finalizada: {session_id}")
        return True
    
    async def exportar_markdown(self, session_id: str) -> Optional[str]:
        """
        Exporta sessão como arquivo Markdown.
        
        Returns:
            Caminho do arquivo gerado ou None se erro
        """
        sessao = await self.obter_sessao(session_id)
        if not sessao:
            return None
        
        # Gerar Markdown
        md = self._gerar_markdown_sessao(sessao)
        
        # Salvar arquivo
        filename = f"{sessao.artigo.replace(' ', '_').replace('.', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = self.exports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
        
        logger.info(f"💾 Sessão exportada: {filepath}")
        return str(filepath)
    
    def _gerar_markdown_sessao(self, sessao: SessaoAnalise) -> str:
        """Gera conteúdo Markdown de uma sessão."""
        md = f"""# Análise da Minuta V2 - TRE-GO

## {sessao.artigo} - {sessao.titulo}

**Sessão ID:** `{sessao.id}`  
**Usuário:** {sessao.usuario}  
**Data de criação:** {sessao.data_criacao.strftime('%d/%m/%Y %H:%M:%S')}  
**Última atualização:** {sessao.data_atualizacao.strftime('%d/%m/%Y %H:%M:%S')}  
**Duração:** {sessao.duracao()}  
**Status:** {sessao.status.value}  
**Total de interações:** {len(sessao.interacoes)}

---

"""
        
        # Histórico de interações
        if sessao.interacoes:
            md += """## 📝 Histórico de Interações

"""
            for i, interacao in enumerate(sessao.interacoes, 1):
                md += f"""### Interação #{i} - {interacao.agente_nome}

**Data/Hora:** {interacao.timestamp.strftime('%d/%m/%Y %H:%M:%S')}  
**Confiança:** {interacao.confianca * 100:.0f}%

**Pergunta:**
> {interacao.pergunta}

**Resposta:**

{interacao.resposta}

"""
                if interacao.artigos_citados:
                    md += f"**Artigos citados:** {', '.join(interacao.artigos_citados)}\n\n"
                
                if interacao.fontes_conhecimento:
                    md += f"**Fontes consultadas:** {', '.join(interacao.fontes_conhecimento)}\n\n"
                
                md += "---\n\n"
        
        # Análises evolutivas
        if sessao.analises:
            md += """## 📊 Análises Evolutivas

"""
            for i, analise in enumerate(sessao.analises, 1):
                md += f"### Análise #{i}\n\n"
                md += analise.to_markdown()
                md += "\n---\n\n"
        
        # Consolidação final
        if sessao.texto_final_minuta:
            md += f"""## ✅ Texto Final Proposto

{sessao.texto_final_minuta}

---

"""
        
        if sessao.observacoes_finais:
            md += f"""## 📌 Observações Finais

{sessao.observacoes_finais}

---

"""
        
        # Rodapé
        md += f"""
---

*Documento gerado automaticamente pelo Sistema TRE-GO Minuta Builder*  
*Data de exportação: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}*
"""
        
        return md
    
    async def gerar_documento_consolidado(self, session_id: str) -> Optional[str]:
        """
        Gera documento consolidado no formato de regulamento.
        
        Returns:
            Caminho do arquivo ou None
        """
        sessao = await self.obter_sessao(session_id)
        if not sessao:
            return None
        
        md = f"""# REGULAMENTO INTERNO DO TRIBUNAL REGIONAL ELEITORAL DE GOIÁS

## Documento de Trabalho - Versão Consolidada

**Baseado em:** {sessao.artigo} - {sessao.titulo}  
**Sessão:** `{sessao.id}`  
**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

---

## PREÂMBULO

Este documento consolida as análises realizadas sobre o tema "{sessao.titulo}" através de consulta aos especialistas nas diferentes versões do Regulamento Interno do TRE-GO.

**Versões consultadas:**
- Resolução 05/1997 (Regulamento Original)
- Resolução 113/2007
- Resolução 275/2017 (Vigente)
- Alterações 2021-2025
- Minuta V2 (Em construção)

---

"""
        
        # Agrupar interações por agente
        por_agente = {}
        for interacao in sessao.interacoes:
            if interacao.agente not in por_agente:
                por_agente[interacao.agente] = []
            por_agente[interacao.agente].append(interacao)
        
        # Seção por agente
        md += """## ANÁLISE COMPARATIVA

"""
        
        for agente_id, interacoes in por_agente.items():
            agente_nome = interacoes[0].agente_nome if interacoes else agente_id
            md += f"""### {agente_nome}

"""
            for interacao in interacoes:
                md += f"""**Consulta ({interacao.timestamp.strftime('%H:%M:%S')}):**
> {interacao.pergunta}

**Resposta:**
{interacao.resposta}

"""
                if interacao.artigos_citados:
                    md += f"*Referências: {', '.join(interacao.artigos_citados)}*\n\n"
        
        # Proposta de texto
        md += """---

## PROPOSTA DE TEXTO

"""
        
        if sessao.texto_final_minuta:
            md += f"""{sessao.texto_final_minuta}

"""
        else:
            # Usar análise mais recente se houver
            if sessao.analises:
                ultima_analise = sessao.analises[-1]
                if ultima_analise.proposta_consolidada:
                    md += f"""{ultima_analise.proposta_consolidada}

"""
            else:
                md += """*Texto consolidado ainda não definido. Use a funcionalidade de consolidação para gerar proposta.*

"""
        
        # Disposições finais
        md += """---

## OBSERVAÇÕES PARA REVISÃO

"""
        
        if sessao.observacoes_finais:
            md += f"""{sessao.observacoes_finais}

"""
        else:
            md += """- Este documento foi gerado automaticamente
- Recomenda-se revisão cuidadosa antes da versão final
- Consulte a comissão de revisão para validação

"""
        
        md += f"""
---

**Metadados:**
- Sessão: `{sessao.id}`
- Criação: {sessao.data_criacao.strftime('%d/%m/%Y %H:%M:%S')}
- Duração: {sessao.duracao()}
- Interações: {len(sessao.interacoes)}
- Agentes consultados: {len(por_agente)}

*Sistema TRE-GO Minuta Builder v2.0*
"""
        
        # Salvar
        filename = f"consolidado_{sessao.artigo.replace(' ', '_').replace('.', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = self.exports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
        
        logger.info(f"📄 Documento consolidado gerado: {filepath}")
        return str(filepath)
    
    def status(self) -> Dict:
        """Retorna status do gerenciador."""
        return {
            "total_sessoes": len(self._sessoes_cache),
            "sessoes_ativas": len([s for s in self._sessoes_cache.values() 
                                   if s.status == StatusConsulta.EM_ANDAMENTO]),
            "db_disponivel": self.db is not None,
            "diretorio_exports": str(self.exports_dir)
        }


# ============================================================================
# SINGLETON GLOBAL
# ============================================================================

_gerenciador_sessoes: Optional[GerenciadorSessoes] = None


def get_gerenciador_sessoes() -> GerenciadorSessoes:
    """Obtém instância global do GerenciadorSessoes."""
    global _gerenciador_sessoes
    if _gerenciador_sessoes is None:
        _gerenciador_sessoes = GerenciadorSessoes()
    return _gerenciador_sessoes
