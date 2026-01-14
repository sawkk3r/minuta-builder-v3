# ============================================================================
# ARQUIVO: backend/models.py
# Modelos Pydantic para validação de dados
# ============================================================================

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class StatusConsulta(str, Enum):
    """Status de uma consulta ou sessão."""
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    ERRO = "erro"


class Criticidade(str, Enum):
    """Nível de criticidade de um gap ou observação."""
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class VersaoRegulamento(str, Enum):
    """Versões do regulamento disponíveis."""
    RES_1997 = "1997"
    RES_2007 = "2007"
    RES_2017 = "2017"
    ALTERACOES = "alteracoes"
    MINUTA_V2 = "minuta"


# ============================================================================
# REQUESTS
# ============================================================================

class CriarSessaoRequest(BaseModel):
    """Request para criar nova sessão de análise."""
    artigo: str = Field(..., description="Artigo ou seção a ser analisado (ex: 'Art. 47')")
    titulo: str = Field(..., description="Título ou descrição do artigo")
    usuario: Optional[str] = Field(default="usuario_padrao", description="ID do usuário")


class ConsultarAgenteRequest(BaseModel):
    """Request para consultar um agente específico."""
    agente: VersaoRegulamento = Field(..., description="Versão do regulamento a consultar")
    pergunta: str = Field(..., min_length=10, description="Pergunta para o agente")


class ConsolidarRequest(BaseModel):
    """Request para consolidar análises com o Team."""
    tema: str = Field(..., description="Tema para consolidação")
    incluir_agentes: Optional[List[VersaoRegulamento]] = Field(
        default=None,
        description="Agentes específicos a incluir (None = todos)"
    )


# ============================================================================
# RESPONSES E ENTIDADES
# ============================================================================

class RespostaAgente(BaseModel):
    """Resposta de um agente especializado."""
    agente: str = Field(..., description="ID do agente que respondeu")
    agente_nome: str = Field(default="", description="Nome legível do agente")
    pergunta: str = Field(..., description="Pergunta original")
    resposta: str = Field(..., description="Resposta do agente")
    artigos_citados: List[str] = Field(default_factory=list, description="Artigos mencionados")
    confianca: float = Field(default=0.0, ge=0.0, le=1.0, description="Nível de confiança")
    fontes_conhecimento: List[str] = Field(default_factory=list, description="Fontes do knowledge base")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GapIdentificado(BaseModel):
    """Um gap ou lacuna identificada na análise."""
    descricao: str = Field(..., description="Descrição do gap")
    versao_origem: str = Field(..., description="Versão onde o conteúdo existia")
    versao_destino: str = Field(..., description="Versão onde está faltando")
    criticidade: Criticidade = Field(default=Criticidade.MEDIA)
    sugestao_resgate: Optional[str] = Field(default=None, description="Sugestão de como resgatar")


class AnaliseEvolutiva(BaseModel):
    """Análise evolutiva de um tema através das versões."""
    tema_analisado: str
    respostas_por_versao: Dict[str, RespostaAgente] = Field(default_factory=dict)
    gaps_identificados: List[GapIdentificado] = Field(default_factory=list)
    proposta_consolidada: Optional[str] = Field(default=None)
    observacoes: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_markdown(self) -> str:
        """Converte análise para formato Markdown."""
        md = f"## Análise: {self.tema_analisado}\n\n"
        md += f"**Data:** {self.timestamp.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        
        # Respostas por versão
        md += "### Respostas por Versão\n\n"
        for versao, resposta in self.respostas_por_versao.items():
            md += f"#### {resposta.agente_nome}\n"
            md += f"**Confiança:** {resposta.confianca * 100:.0f}%\n\n"
            md += f"{resposta.resposta}\n\n"
            if resposta.artigos_citados:
                md += f"**Artigos citados:** {', '.join(resposta.artigos_citados)}\n\n"
            if resposta.fontes_conhecimento:
                md += f"**Fontes:** {', '.join(resposta.fontes_conhecimento)}\n\n"
        
        # Gaps identificados
        if self.gaps_identificados:
            md += "### Gaps Identificados\n\n"
            for gap in self.gaps_identificados:
                md += f"- **{gap.criticidade.value.upper()}**: {gap.descricao}\n"
                md += f"  - De: {gap.versao_origem} → Para: {gap.versao_destino}\n"
                if gap.sugestao_resgate:
                    md += f"  - Sugestão: {gap.sugestao_resgate}\n"
            md += "\n"
        
        # Proposta consolidada
        if self.proposta_consolidada:
            md += "### Proposta Consolidada\n\n"
            md += f"{self.proposta_consolidada}\n\n"
        
        # Observações
        if self.observacoes:
            md += "### Observações\n\n"
            for obs in self.observacoes:
                md += f"- {obs}\n"
        
        return md


class InteracaoAgente(BaseModel):
    """Registro de uma interação com um agente."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agente: str
    agente_nome: str
    pergunta: str
    resposta: str
    artigos_citados: List[str] = Field(default_factory=list)
    fontes_conhecimento: List[str] = Field(default_factory=list)
    confianca: float = Field(default=0.0)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TextoConsolidado(BaseModel):
    """Texto consolidado proposto para a minuta."""
    artigo: str
    titulo: str
    texto_proposto: str
    justificativa: str
    fontes: List[str] = Field(default_factory=list)
    versao: int = Field(default=1)
    aprovado: bool = Field(default=False)
    observacoes: List[str] = Field(default_factory=list)


class SessaoAnalise(BaseModel):
    """Sessão completa de análise de um artigo."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    artigo: str
    titulo: str
    usuario: str = Field(default="usuario_padrao")
    status: StatusConsulta = Field(default=StatusConsulta.EM_ANDAMENTO)
    
    # Histórico completo
    interacoes: List[InteracaoAgente] = Field(default_factory=list)
    analises: List[AnaliseEvolutiva] = Field(default_factory=list)
    
    # Resultado final
    texto_final_minuta: Optional[str] = Field(default=None)
    observacoes_finais: Optional[str] = Field(default=None)
    
    # Metadados
    data_criacao: datetime = Field(default_factory=datetime.now)
    data_atualizacao: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def duracao(self) -> str:
        """Retorna duração da sessão formatada."""
        delta = datetime.now() - self.data_criacao
        horas, resto = divmod(delta.seconds, 3600)
        minutos, segundos = divmod(resto, 60)
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável."""
        return {
            "id": self.id,
            "artigo": self.artigo,
            "titulo": self.titulo,
            "usuario": self.usuario,
            "status": self.status.value,
            "num_interacoes": len(self.interacoes),
            "num_analises": len(self.analises),
            "data_criacao": self.data_criacao.isoformat(),
            "data_atualizacao": self.data_atualizacao.isoformat(),
            "duracao": self.duracao()
        }


# ============================================================================
# WEBSOCKET MESSAGES
# ============================================================================

class WSMessageType(str, Enum):
    """Tipos de mensagens WebSocket."""
    STATUS = "status"
    RESPOSTA_AGENTE = "resposta_agente"
    CONSOLIDACAO = "consolidacao_completa"
    ERRO = "erro"
    SESSAO_FINALIZADA = "sessao_finalizada"
    KNOWLEDGE_STATUS = "knowledge_status"


class WSMessage(BaseModel):
    """Mensagem WebSocket padronizada."""
    tipo: WSMessageType
    dados: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    def to_json(self) -> Dict[str, Any]:
        """Converte para JSON serializável."""
        return {
            "tipo": self.tipo.value,
            **self.dados,
            "timestamp": self.timestamp.isoformat()
        }
