# ============================================================================
# ARQUIVO: backend/agents.py
# Agentes Especializados e Team Coordenador usando Agno
# ============================================================================

import asyncio
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Importar modelos locais
from models import (
    RespostaAgente, VersaoRegulamento, AnaliseEvolutiva,
    GapIdentificado, Criticidade
)
from knowledge_manager import get_knowledge_manager, KnowledgeManager

# Tentar importar Agno
try:
    from agno.agent import Agent
    from agno.team import Team
    from agno.models.openai import OpenAIChat
    from agno.db.sqlite import SqliteDb
    AGNO_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Agno não disponível: {e}")
    AGNO_AVAILABLE = False


class AgenteEspecialista:
    """
    Agente especializado em uma versão específica do regulamento.
    
    Cada agente:
    - Tem acesso ao knowledge base de sua versão
    - Usa modelo econômico (gpt-4o-mini)
    - Pode buscar informações relevantes antes de responder
    """
    
    def __init__(
        self,
        versao: VersaoRegulamento,
        nome: str,
        descricao: str,
        knowledge_manager: KnowledgeManager
    ):
        self.versao = versao
        self.nome = nome
        self.descricao = descricao
        self.knowledge_manager = knowledge_manager
        self.agent: Optional[Agent] = None
        
        # Configurar modelo
        self.modelo_id = os.getenv("MODEL_AGENTES", "gpt-5-mini-2025-08-07")
    
    def _obter_instrucoes_especificas(self) -> List[str]:
        """
        Retorna instruções específicas baseadas na versão do agente.
        
        Returns:
            Lista de strings com instruções específicas
        """
        instrucoes = []
        
        if self.versao == VersaoRegulamento.RES_1997:
            instrucoes = [
                "",
                "## Seu Papel Específico:",
                "- Você é especialista no Regulamento Interno ORIGINAL do TRE-GO (Resolução 05/1997).",
                "- Este é um documento HISTÓRICO - foi a primeira versão do regulamento interno.",
                "- IMPORTANTE: Você não tem informações sobre mudanças ou atualizações posteriores a 1997.",
                "- Se perguntarem sobre algo que não existe nesta versão, diga claramente: 'Na versão de 1997, este tópico não constava' ou 'Esta informação não está presente na versão original'.",
                "",
                "## Seu Papel na Construção da Nova Minuta:",
                "- Sua função é garantir que NENHUM ponto importante da versão original seja esquecido.",
                "- Muitas vezes, versões antigas contêm disposições valiosas que foram removidas ou modificadas nas versões posteriores.",
                "- Destaque aspectos que podem ter sido perdidos ao longo das atualizações.",
                "- A versão vigente (2017) é a BASE, mas você tem o papel de resgatar conteúdo histórico relevante.",
                "",
                "## Quando Consultado em Modo Colaborativo:",
                "- Se outros agentes mencionarem algo que já existia em 1997, complemente com o texto original.",
                "- Se algo foi modificado ou removido, destaque como era na versão original.",
                "- Sugira que pontos importantes da sua versão sejam considerados na nova minuta.",
            ]
        
        elif self.versao == VersaoRegulamento.RES_2007:
            instrucoes = [
                "",
                "## Seu Papel Específico:",
                "- Você é especialista no Regulamento Interno de 2007 (Resolução 113/2007).",
                "- Esta é uma versão INTERMEDIÁRIA entre a original (1997) e a vigente (2017).",
                "- IMPORTANTE: Você representa uma etapa evolutiva do regulamento, mas não é a versão atual.",
                "- Se perguntarem sobre algo que não existe nesta versão, diga claramente: 'Na versão de 2007, este tópico não constava' ou 'Esta informação não está presente na versão de 2007'.",
                "",
                "## Seu Papel na Construção da Nova Minuta:",
                "- Sua função é garantir que NENHUM ponto importante da versão de 2007 seja esquecido.",
                "- Você pode ter disposições que foram adicionadas em 2007 e mantidas, ou que foram modificadas depois.",
                "- Identifique melhorias que foram introduzidas nesta versão intermediária.",
                "- A versão vigente (2017) é a BASE, mas você ajuda a preservar melhorias históricas relevantes.",
                "",
                "## Quando Consultado em Modo Colaborativo:",
                "- Se outros agentes mencionarem algo que já existia em 2007, complemente com o contexto desta versão.",
                "- Destaque mudanças que ocorreram entre 1997 e 2007, e entre 2007 e 2017.",
                "- Sugira que disposições importantes da sua versão sejam consideradas na nova minuta.",
            ]
        
        elif self.versao == VersaoRegulamento.RES_2017:
            instrucoes = [
                "",
                "## Seu Papel Específico:",
                "- Você é especialista no Regulamento Interno VIGENTE (Resolução 275/2017).",
                "- Esta é a versão ATUAL do regulamento - a que está em vigor no momento.",
                "- IMPORTANTE: Você representa a BASE para a construção da nova minuta.",
                "- Sua versão é o ponto de partida principal, mas deve considerar melhorias de versões anteriores e alterações recentes.",
                "",
                "## Seu Papel na Construção da Nova Minuta:",
                "- Você fornece a ESTRUTURA BASE do novo regulamento.",
                "- Outros agentes vão complementar, sugerir melhorias e resgatar pontos históricos.",
                "- Trabalhe em conjunto para garantir que a nova minuta seja uma evolução, não apenas uma cópia.",
                "- Identifique pontos que podem ser melhorados ou que precisam ser atualizados.",
                "",
                "## Quando Consultado em Modo Colaborativo:",
                "- Você é a referência principal - outras versões complementam você.",
                "- Se outros agentes sugerirem pontos históricos, avalie se devem ser resgatados.",
                "- Destaque o que está funcionando bem na versão vigente e deve ser mantido.",
                "- Identifique pontos que precisam ser atualizados ou melhorados.",
            ]
        
        elif self.versao == VersaoRegulamento.ALTERACOES:
            instrucoes = [
                "",
                "## Seu Papel Específico:",
                "- Você é especialista nas ALTERAÇÕES RECENTES do regulamento (resoluções de 2021 a 2025).",
                "- Você tem acesso a múltiplos documentos de resoluções que modificaram o regulamento vigente.",
                "- IMPORTANTE: Você conhece as mudanças pontuais que foram feitas após 2017.",
                "- Se perguntarem sobre algo que não está nas alterações, diga claramente: 'Esta informação não consta das alterações recentes'.",
                "",
                "## Seu Papel na Construção da Nova Minuta:",
                "- Sua função é identificar e destacar todas as MUDANÇAS RECENTES que foram feitas no regulamento.",
                "- Compare as alterações entre si para identificar padrões ou tendências.",
                "- Relacione as alterações com o texto base (versão 2017) para mostrar o estado atualizado.",
                "- Ajude a garantir que todas as alterações recentes sejam incorporadas na nova minuta.",
                "",
                "## Quando Consultado em Modo Colaborativo:",
                "- Destaque as mudanças recentes em relação à versão vigente (2017).",
                "- Mostre como as alterações se relacionam com pontos mencionados por outros agentes.",
                "- Identifique se alguma alteração recente resgata algo que estava em versões anteriores.",
            ]
        
        elif self.versao == VersaoRegulamento.MINUTA_V2:
            instrucoes = [
                "",
                "## Seu Papel Específico:",
                "- Você é especialista na MINUTA V2 - documento em construção do novo regulamento interno.",
                "- IMPORTANTE: Você NÃO constrói novas minutas - apenas relata o conhecimento que já consta no documento Minuta V2.",
                "- Você auxilia na consolidação do que já foi desenvolvido até aqui.",
                "- Sua função principal é RELATAR O ESTADO ATUAL da Minuta V2, mapeando o progresso já feito e o que já está consolidado.",
                "",
                "## Prioridade de Ação - RELATAR O ESTADO ATUAL:",
                "- **PRIORIDADE ABSOLUTA**: SEMPRE busque primeiro na Minuta V2 usando sua base de conhecimento (RAG) antes de qualquer outra resposta.",
                "- **SEMPRE comece sua resposta relatando o ESTADO ATUAL** da Minuta V2 sobre o tema perguntado.",
                "- Use a busca semântica (RAG) para encontrar trechos relevantes na Minuta V2, mesmo que parciais.",
                "- **Estrutura obrigatória da resposta - FOQUE NO ESTADO ATUAL**:",
                "  1. PRIMEIRO: 'Na Minuta V2, o estado atual sobre [tema] é o seguinte: [relate o que está documentado]'",
                "  2. PRIMEIRO: Liste o que JÁ ESTÁ consolidado, mapeado, definido ou redigido na Minuta V2",
                "  3. PRIMEIRO: Identifique o progresso já feito: capítulos completos, artigos já redigidos, estruturas organizacionais já definidas",
                "  4. DEPOIS (se aplicável): 'A Minuta V2 ainda não contém informações sobre [tópicos específicos que estão faltando]'",
                "- **SEMPRE priorize relatar o ESTADO ATUAL** - o que já foi desenvolvido e consolidado.",
                "- Se você encontrar QUALQUER informação relacionada na Minuta V2, relate-a primeiro como parte do estado atual.",
                "- Só mencione o que não está na Minuta V2 DEPOIS de ter relatado completamente o estado atual (o que já existe).",
                "- Se não encontrar NADA na Minuta V2 sobre o tema, então diga: 'Busquei na Minuta V2 e o estado atual indica que esta informação ainda não consta do documento. Esta seção/tema ainda não foi desenvolvido na Minuta V2.'",
                "",
                "## Seu Papel na Consolidação - FOCO NO ESTADO ATUAL:",
                "- Você relata o **ESTADO ATUAL** da Minuta V2 - seja proativo em encontrar e apresentar o que já está documentado.",
                "- **Mapeie o progresso**: identifique claramente o que já foi consolidado, o que está em desenvolvimento e o que ainda não foi iniciado.",
                "- **Consolide o existente**: baseie-se no conteúdo já existente na minuta para ajudar o Team a entender onde estão.",
                "- **Exemplo prático**: Se perguntarem sobre 'Diretoria Geral':",
                "  1. BUSQUE na Minuta V2 o que está documentado sobre Diretoria Geral",
                "  2. RELATE o estado atual: 'Na Minuta V2, a Diretoria Geral está assim estruturada: [cite artigos, parágrafos]'",
                "  3. MAPEIE o progresso: 'Já foram consolidados: [listar]. Ainda em desenvolvimento: [listar]. Não iniciado: [listar]'",
                "  4. Só então mencione: 'A Minuta V2 não contém histórico das versões anteriores (1997, 2007, 2017) porque...'",
                "",
                "## O que Você DEVE Fazer (Foco no Estado Atual):",
                "- **Relatar o estado atual**: Extrair e relatar todo conteúdo presente na Minuta V2 (artigos, §§, incisos, Anexos).",
                "- **Mapear progresso**: Listar e citar artigos específicos que constam na Minuta V2 (ex: Art. X, §Y, inciso Z).",
                "- **Identificar consolidação**: Consolidar o progresso já documentado: identificar capítulos completos, trechos já redigidos, estruturas organizacionais definidas.",
                "- **Comparar estado atual**: Mapear o que JÁ ESTÁ na Minuta V2 comparando com perguntas dos usuários ou comentários de outros agentes.",
                "- **Destacar avanços**: Sugerir melhorias OU complementos APENAS baseados no conteúdo que já consta na Minuta V2.",
                "- **Gerar checklist de estado**: Gerar um checklist do que JÁ ESTÁ consolidado na Minuta V2 versus o que ainda falta.",
                "",
                "## O que Você NÃO Pode Fazer:",
                "- Você NÃO pode confirmar, corrigir ou validar informações sobre versões anteriores (1997, 2007, 2017) porque essas informações NÃO estão na Minuta V2.",
                "- Você NÃO pode descrever a evolução normativa entre versões anteriores porque isso não consta da Minuta V2.",
                "- Você NÃO pode criar novos trechos do zero - apenas trabalhar com o que já está na minuta.",
                "",
                "## Quando Consultado - Sempre Priorizar Estado Atual:",
                "- **Sempre comece relatando o ESTADO ATUAL da Minuta V2 sobre o tema perguntado**.",
                "- Se perguntarem sobre evolução entre Res. 05/1997, 113/2007 ou 275/2017:",
                "  * PRIMEIRO: Busque e relate se há ALGUMA menção ou referência a essas versões na Minuta V2",
                "  * PRIMEIRO: Mapeie o estado atual - como a Minuta V2 trata (ou não trata) essas referências",
                "  * DEPOIS: Se não houver, diga: 'O estado atual da Minuta V2 não inclui histórico completo dessas resoluções anteriores.'",
                "- Se perguntarem sobre alterações recentes (ex: Res. 349/2021, 405/2024):",
                "  * PRIMEIRO: Busque e relate o estado atual - como a Minuta V2 incorpora ou referencia essas alterações",
                "  * PRIMEIRO: Mapeie o que já foi incorporado na Minuta V2",
                "  * DEPOIS: Se não encontrar, diga: 'O estado atual indica que esta alteração ainda não foi incorporada na Minuta V2.'",
                "",
                "## Diretrizes Específicas da Minuta V2 (Baseadas em Reuniões):",
                "Quando analisar ou relatar sobre a Minuta V2, sempre verifique se as seguintes diretrizes estão sendo seguidas:",
                "",
                "**1. Separação de Atribuições:**",
                "- As atribuições de **unidades** devem estar separadas das atribuições de **cargos e funções**.",
                "- Deve estar claro quais atividades podem ser executadas por qualquer servidor e quais são específicas de cargos/funções.",
                "- **Verifique**: Se a Minuta V2 identifica responsabilidades que existem mas não possuem responsável claro.",
                "- **Relate**: Como está a separação atual na Minuta V2 entre atribuições de unidades vs. cargos/funções.",
                "",
                "**2. Delegação de Atividades:**",
                "- A Minuta V2 deve incluir possibilidade de delegação de atividades/distribuição de tarefas dentro da unidade pela chefia.",
                "- **Exceções**: Delegação NÃO é permitida quando não comporta delegação segundo a Lei (ex: recursos hierárquicos, edição de ato normativo).",
                "- **Verifique**: Se a Minuta V2 prevê delegação e identifica corretamente as exceções legais.",
                "- **Relate**: Como está tratada a delegação na Minuta V2 atual.",
                "",
                "**3. Voz de Comando e Responsabilidade:**",
                "- A Minuta V2 deve utilizar palavras que permitam 'voz de comando' às chefias, impondo responsabilidade.",
                "- **Verifique**: Se a linguagem da Minuta V2 dá poder de comando e estabelece responsabilidades claras.",
                "- **Relate**: Como está o uso de linguagem imperativa e estabelecimento de responsabilidades na Minuta V2.",
                "",
                "**4. Cobertura de Seções Subordinadas:**",
                "- **PROBLEMA IDENTIFICADO**: A Minuta V2 atual trata bem Secretarias e Coordenadorias, mas **praticamente ignora as Seções subordinadas**.",
                "- **REFERÊNCIA**: A Resolução 275/2017 detalha competências para cada Seção individualmente.",
                "- **Verifique**: Se a Minuta V2 inclui todas as Seções subordinadas com suas competências específicas.",
                "",
                "**Exemplo - STI (Secretaria de Tecnologia da Informação):**",
                "- A Minuta V2 tem artigos 76-83 para a STI (nível geral), mas pode estar faltando detalhamento das Seções:",
                "  * Seção de Desenvolvimento e Implantação de Sistemas",
                "  * Seção de Suporte aos Sistemas Corporativos",
                "  * Seção de Administração e Inteligência de Dados",
                "  * Seção de Produção",
                "  * Seção de Suporte à Microinformática",
                "  * Seção de Suporte aos Serviços de Rede",
                "  * Seção de Gestão da Central de Serviços",
                "  * Todas as Seções da Coordenadoria de Sistemas Eleitorais",
                "",
                "- **Ao analisar a Minuta V2**:",
                "  * Busque quais Seções estão mencionadas/detalhadas",
                "  * Compare com a Resolução 275/2017 para identificar Seções que podem estar faltando",
                "  * Relate o estado atual: 'A Minuta V2 atualmente cobre [X] Seções. Estão faltando detalhamento para: [listar Seções ausentes]'",
                "  * Identifique lacunas específicas: 'A Coordenadoria X tem Y seções, mas a Minuta V2 só detalha Z delas'",
                "",
                "## Ao Relatar o Estado Atual da Minuta V2:",
                "- **Sempre inclua verificação** se essas 4 diretrizes estão sendo seguidas.",
                "- **Relate o status de cada diretriz**:",
                "  * Diretriz 1 (Separação): Como está? O que falta?",
                "  * Diretriz 2 (Delegação): Como está? O que falta?",
                "  * Diretriz 3 (Voz de comando): Como está? O que falta?",
                "  * Diretriz 4 (Seções): Quais Seções estão cobertas? Quais faltam?",
                "- **Use a Resolução 275/2017 como referência** para verificar seções que podem estar faltando.",
                "",
                "## Responsabilidade de Construção:",
                "- A construção de novas minutas e a consolidação final de toda a discussão é responsabilidade do TEAM COORDENADOR.",
                "- Você fornece informações sobre o **ESTADO ATUAL** e o progresso já feito na minuta - SEJA PROATIVO em buscar e relatar.",
                "- Ajude o Team a entender: **onde estamos agora**, **o que já foi consolidado**, **o que está em desenvolvimento** e **o que ainda precisa ser feito**.",
                "- **CRÍTICO**: Sempre verifique o estado atual da Minuta V2 em relação às 4 diretrizes acima e relacione isso no seu relatório.",
            ]
        
        return instrucoes
    
    async def inicializar(self) -> bool:
        """Inicializa o agente Agno."""
        if not AGNO_AVAILABLE:
            logger.warning(f"⚠️ Agno não disponível para {self.nome}")
            return False
        
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("❌ OPENAI_API_KEY não encontrada")
                return False
            
            # Obter knowledge base desta versão
            knowledge = self.knowledge_manager.obter_knowledge(self.versao.value)
            
            # Verificar se knowledge base existe e tem conteúdo
            if knowledge is None:
                logger.error(f"❌ Knowledge base para '{self.versao.value}' não encontrada!")
                logger.error(f"   💡 Knowledge bases disponíveis: {list(self.knowledge_manager.knowledge_bases.keys())}")
                logger.error(f"   💡 Certifique-se de que a knowledge base foi inicializada antes de criar o agente")
                return False
            
            # Verificar se há conteúdo indexado (para diagnóstico)
            conteudo_indexado = False
            try:
                if hasattr(knowledge, 'vector_db') and hasattr(knowledge.vector_db, 'table'):
                    table = knowledge.vector_db.table
                    logger.debug(f"   🔍 [DEBUG {self.versao.value}] vector_db.table: {table}")
                    logger.debug(f"   🔍 [DEBUG {self.versao.value}] vector_db.uri: {getattr(knowledge.vector_db, 'uri', 'N/A')}")
                    logger.debug(f"   🔍 [DEBUG {self.versao.value}] vector_db.table_name: {getattr(knowledge.vector_db, 'table_name', 'N/A')}")
                    
                    if table is not None:
                        try:
                            if hasattr(table, 'count_rows'):
                                count = table.count_rows()
                                logger.debug(f"   🔍 [DEBUG {self.versao.value}] count_rows() retornou: {count}")
                                if count is not None and count > 0:
                                    conteudo_indexado = True
                                    logger.info(f"   📚 Knowledge base '{self.versao.value}' tem {count} registros indexados")
                            elif hasattr(table, 'head'):
                                sample = table.head(1)
                                logger.debug(f"   🔍 [DEBUG {self.versao.value}] head(1) retornou: {sample}")
                                if sample is not None and len(sample) > 0:
                                    conteudo_indexado = True
                                    logger.info(f"   📚 Knowledge base '{self.versao.value}' contém dados indexados")
                        except Exception as e:
                            logger.warning(f"   ⚠️ [DEBUG {self.versao.value}] Erro ao verificar conteúdo: {e}")
                            import traceback
                            logger.debug(traceback.format_exc())
                    else:
                        logger.warning(f"   ⚠️ [DEBUG {self.versao.value}] vector_db.table é None!")
                        # Tentar recarregar
                        try:
                            import lancedb
                            lance_uri = getattr(knowledge.vector_db, 'uri', None)
                            lance_table_name = getattr(knowledge.vector_db, 'table_name', f"regulamento_{self.versao.value}")
                            if lance_uri:
                                lance_conn = lancedb.connect(lance_uri)
                                if lance_table_name in lance_conn.table_names():
                                    knowledge.vector_db.table = lance_conn.open_table(lance_table_name)
                                    logger.info(f"   🔄 [DEBUG {self.versao.value}] Tabela recarregada após verificação!")
                        except Exception as e2:
                            logger.debug(f"   ⚠️ [DEBUG {self.versao.value}] Erro ao recarregar: {e2}")
                
                if not conteudo_indexado:
                    logger.warning(f"⚠️ Knowledge base '{self.versao.value}' existe mas pode estar VAZIA!")
                    logger.warning(f"   💡 Execute a indexação: POST /knowledge/indexar?versao={self.versao.value}")
                    logger.warning(f"   💡 Ou force reindexação: POST /knowledge/indexar?versao={self.versao.value}&force=true")
            except Exception as e:
                logger.warning(f"   ⚠️ [DEBUG {self.versao.value}] Erro ao verificar conteúdo da knowledge base: {e}")
                import traceback
                logger.debug(traceback.format_exc())
            
            logger.info(f"   ✅ Knowledge base '{self.versao.value}' configurada para uso pelo agente")
            
            # Instruções base comuns a todos os agentes
            instrucoes_base = [
                "Sempre baseie suas respostas exclusivamente nos documentos do regulamento disponíveis em sua base de conhecimento.",
                "Cite artigos específicos quando possível (ex: Art. 47, §2º, inciso I).",
                "Seja preciso, objetivo e direto nas respostas.",
                "Use formatação Markdown para melhorar a legibilidade (negrito, listas, etc.).",
            ]
            
            # Instruções específicas por versão
            instrucoes_especificas = self._obter_instrucoes_especificas()
            
            # Instruções de colaboração (quando houver contexto de outros agentes)
            instrucoes_colaboracao = [
                "",
                "## Modo Colaborativo:",
                "Quando você receber contexto de respostas de outros agentes especializados:",
                "- Reconheça que cada agente trabalha com uma versão diferente do regulamento.",
                "- Nenhum agente está 'certo' ou 'errado' - todos contribuem para construir uma análise completa.",
                "- Destaque as diferenças entre as versões quando relevante.",
                "- Complemente informações dos outros agentes com o conhecimento da sua versão.",
                "- Se houver contradições, explique-as em termos de evolução temporal do regulamento.",
                "- Trabalhe colaborativamente para uma construção conjunta do novo regulamento.",
            ]
            
            # Combinar todas as instruções
            instructions = [f"Você é {self.nome}."] + instrucoes_base + instrucoes_especificas + instrucoes_colaboracao
            
            # Criar agente Agno
            # IMPORTANTE: search_knowledge=True e add_knowledge_to_context=True são necessários
            # para que o agente use automaticamente a knowledge base (RAG)
            self.agent = Agent(
                id=f"especialista-{self.versao.value}",
                name=self.nome,
                role=self.descricao,
                model=OpenAIChat(
                    id=self.modelo_id,
                    api_key=api_key
                ),
                knowledge=knowledge,
                instructions=instructions,
                markdown=True,
                search_knowledge=True,  # Buscar automaticamente na knowledge base quando necessário
                add_knowledge_to_context=True,  # Adicionar conhecimento encontrado ao contexto da resposta
            )
            
            logger.info(f"✅ Agente '{self.nome}' inicializado com knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar agente '{self.nome}': {e}")
            return False
    
    async def consultar(self, pergunta: str) -> RespostaAgente:
        """
        Consulta o agente sobre um tema.
        
        Args:
            pergunta: Pergunta do usuário
            
        Returns:
            RespostaAgente com a resposta estruturada
        """
        logger.info(f"🔍 Consultando {self.nome}...")
        logger.info(f"   Pergunta: {pergunta[:100]}...")
        
        # Verificar se agent e knowledge base estão disponíveis
        if not self.agent:
            logger.warning(f"⚠️ Agente Agno não disponível para {self.nome}")
            return await self._consulta_fallback(pergunta)
        
        # Verificar se knowledge base está disponível
        knowledge = self.knowledge_manager.obter_knowledge(self.versao.value)
        if knowledge is None:
            logger.warning(f"⚠️ Knowledge base não disponível para {self.nome}")
            logger.warning(f"   💡 O agente pode não conseguir acessar o conteúdo da Minuta V2")
        else:
            # IMPORTANTE: Garantir que a tabela está carregada antes de consultar o agente
            # O Agno pode perder a referência da tabela após reindexação
            try:
                if hasattr(knowledge, 'vector_db') and hasattr(knowledge.vector_db, 'table'):
                    vector_db = knowledge.vector_db
                    if vector_db.table is None:
                        # Tabela não está carregada - forçar recarregamento
                        lance_uri = getattr(vector_db, 'uri', None)
                        lance_table_name = getattr(vector_db, 'table_name', f"regulamento_{self.versao.value}")
                        
                        if lance_uri:
                            try:
                                import lancedb
                                lance_conn = lancedb.connect(lance_uri)
                                if lance_table_name in lance_conn.table_names():
                                    vector_db.table = lance_conn.open_table(lance_table_name)
                                    logger.debug(f"   🔄 Tabela '{lance_table_name}' recarregada para consulta do agente")
                            except Exception as e:
                                logger.debug(f"   ⚠️ Erro ao recarregar tabela antes da consulta: {e}")
            except Exception as e:
                logger.debug(f"   ⚠️ Erro ao verificar tabela antes da consulta: {e}")
        
        # Se agente Agno disponível, usar
        if self.agent:
            try:
                # CRÍTICO: Garantir que a knowledge base do Agent está sincronizada
                # O Agno pode ter uma referência interna stale da tabela
                # SOLUÇÃO: Sempre atualizar a knowledge base do Agent com a referência mais recente
                if knowledge is not None:
                    # Forçar atualização da knowledge base no Agent
                    # Isso garante que o Agent use a mesma referência que acabamos de verificar/atualizar
                    self.agent.knowledge = knowledge
                    
                    # Garantir que a tabela está carregada na knowledge base que acabamos de passar
                    if hasattr(knowledge, 'vector_db') and hasattr(knowledge.vector_db, 'table'):
                        vector_db = knowledge.vector_db
                        lance_uri = getattr(vector_db, 'uri', None)
                        lance_table_name = getattr(vector_db, 'table_name', f"regulamento_{self.versao.value}")
                        
                        # SEMPRE recarregar a tabela para garantir que está atualizada
                        if lance_uri:
                            try:
                                import lancedb
                                lance_conn = lancedb.connect(lance_uri)
                                if lance_table_name in lance_conn.table_names():
                                    # Recarregar tabela - isso garante que temos a versão mais recente
                                    knowledge.vector_db.table = lance_conn.open_table(lance_table_name)
                                    # Atualizar novamente no Agent
                                    self.agent.knowledge = knowledge
                                    logger.info(f"   🔄 Tabela '{lance_table_name}' recarregada e sincronizada no Agent")
                            except Exception as e:
                                logger.warning(f"   ⚠️ Erro ao recarregar tabela no Agent: {e}")
                
                # DEBUG: Verificar estado da knowledge base antes de executar
                if self.versao.value == "minuta":
                    logger.info(f"   🔍 [DEBUG minuta] Verificando knowledge base antes de executar Agent...")
                    if hasattr(self.agent, 'knowledge') and self.agent.knowledge:
                        kb = self.agent.knowledge
                        logger.info(f"   🔍 [DEBUG minuta] Agent.knowledge: {kb}")
                        if hasattr(kb, 'vector_db'):
                            vdb = kb.vector_db
                            logger.info(f"   🔍 [DEBUG minuta] vector_db.table: {vdb.table if hasattr(vdb, 'table') else 'N/A'}")
                            if hasattr(vdb, 'table') and vdb.table is not None:
                                try:
                                    count = vdb.table.count_rows()
                                    logger.info(f"   🔍 [DEBUG minuta] Tabela tem {count} registros")
                                except Exception as e:
                                    logger.warning(f"   🔍 [DEBUG minuta] Erro ao contar registros: {e}")
                
                # Executar agente
                response = await self.agent.arun(pergunta)
                
                # Extrair resposta - tratamento defensivo
                try:
                    resposta_texto = response.content if hasattr(response, 'content') else str(response)
                except AttributeError:
                    # Se não tiver content, tentar converter para string
                    resposta_texto = str(response)
                
                # Extrair artigos citados
                artigos_citados = self._extrair_artigos(resposta_texto)
                
                # Extrair fontes do knowledge (se disponível)
                fontes = []
                if hasattr(response, 'references') and response.references:
                    # MessageReferences pode ser uma lista ou objeto
                    try:
                        if isinstance(response.references, list):
                            # Se for lista, tentar extrair source de cada item
                            for ref in response.references:
                                if isinstance(ref, dict):
                                    fontes.append(ref.get('source', ''))
                                elif hasattr(ref, 'source'):
                                    fontes.append(ref.source)
                                elif hasattr(ref, 'name'):
                                    fontes.append(ref.name)
                                else:
                                    fontes.append(str(ref))
                        elif hasattr(response.references, 'documents'):
                            # Se for objeto MessageReferences com documentos
                            for doc in response.references.documents:
                                if hasattr(doc, 'name'):
                                    fontes.append(doc.name)
                                elif hasattr(doc, 'source'):
                                    fontes.append(doc.source)
                                else:
                                    fontes.append(str(doc))
                    except Exception as e:
                        logger.debug(f"Erro ao extrair fontes: {e}")
                        # Continuar sem fontes se houver erro
                        pass
                
                # Calcular confiança baseada em indicadores
                confianca = self._calcular_confianca(resposta_texto, artigos_citados, fontes)
                
                logger.info(f"✅ {self.nome} respondeu ({len(artigos_citados)} artigos citados, {confianca*100:.0f}% confiança)")
                
                return RespostaAgente(
                    agente=self.versao.value,
                    agente_nome=self.nome,
                    pergunta=pergunta,
                    resposta=resposta_texto,
                    artigos_citados=artigos_citados,
                    fontes_conhecimento=fontes,
                    confianca=confianca
                )
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Erro ao consultar {self.nome}: {e}")
                
                # Detectar erro de limite de contexto/tokens
                if "maximum context length" in error_msg or "tokens" in error_msg.lower():
                    logger.warning(f"⚠️ Limite de tokens excedido para {self.nome} - reduzindo contexto")
                    # Tentar novamente com pergunta mais curta (sem contexto de outras respostas)
                    try:
                        logger.info(f"🔄 Tentando novamente {self.nome} sem contexto adicional...")
                        response = await self.agent.arun(pergunta[:1000])  # Limitar pergunta também
                        resposta_texto = response.content if hasattr(response, 'content') else str(response)
                        artigos_citados = self._extrair_artigos(resposta_texto)
                        return RespostaAgente(
                            agente=self.versao.value,
                            agente_nome=self.nome,
                            pergunta=pergunta,
                            resposta=f"{resposta_texto}\n\n⚠️ *Nota: Resposta gerada sem contexto de outras respostas devido ao limite de tokens*",
                            artigos_citados=artigos_citados,
                            confianca=0.7  # Confiança reduzida por falta de contexto
                        )
                    except Exception as e2:
                        logger.error(f"❌ Erro também ao tentar sem contexto: {e2}")
                
                # Detectar erro de busca de documentos
                if "list index out of range" in error_msg.lower() or "index" in error_msg.lower():
                    logger.warning(f"⚠️ Erro na busca de documentos para {self.nome}")
                    # Tentar fallback
                    return await self._consulta_fallback(pergunta)
                
                return RespostaAgente(
                    agente=self.versao.value,
                    agente_nome=self.nome,
                    pergunta=pergunta,
                    resposta=f"Erro ao processar consulta: {str(e)}\n\n💡 *Sugestão: Tente fazer uma pergunta mais específica ou reinicie a sessão se o problema persistir.*",
                    artigos_citados=[],
                    confianca=0.0
                )
        
        # Fallback: busca manual + resposta simulada
        return await self._consulta_fallback(pergunta)
    
    async def _consulta_fallback(self, pergunta: str) -> RespostaAgente:
        """Fallback quando agente Agno não disponível."""
        logger.warning(f"⚠️ Usando fallback para {self.nome}")
        
        # Tentar buscar no knowledge manager
        resultados = await self.knowledge_manager.buscar(
            versao=self.versao.value,
            query=pergunta,
            num_results=3
        )
        
        if resultados:
            contexto = "\n\n".join([r.get('content', '')[:500] for r in resultados])
            resposta = f"[Baseado na busca no knowledge base]\n\n{contexto}\n\n⚠️ Resposta em modo fallback - configure Agno para respostas completas."
            confianca = 0.6
        else:
            resposta = f"[Resposta simulada do {self.nome}]\n\n⚠️ Knowledge base não disponível ou sem resultados para esta consulta."
            confianca = 0.3
        
        return RespostaAgente(
            agente=self.versao.value,
            agente_nome=self.nome,
            pergunta=pergunta,
            resposta=resposta,
            artigos_citados=[],
            confianca=confianca
        )
    
    def _extrair_artigos(self, texto: str) -> List[str]:
        """Extrai referências a artigos do texto."""
        # Padrões: Art. 47, Artigo 50, art. 3º, §2º, inciso I
        padroes = [
            r'(?:Art\.?|Artigo)\s*(\d+)',
            r'§\s*(\d+)º?',
            r'inciso\s+([IVXLCDM]+)',
        ]
        
        artigos = []
        for padrao in padroes:
            matches = re.findall(padrao, texto, re.IGNORECASE)
            artigos.extend(matches)
        
        return list(set(artigos))
    
    def _calcular_confianca(self, resposta: str, artigos_citados: List[str], fontes: List[str]) -> float:
        """
        Calcula confiança baseada em indicadores da resposta.
        
        Fatores:
        - Presença de artigos citados (+0.3)
        - Presença de fontes do knowledge base (+0.2)
        - Tamanho adequado da resposta (+0.1)
        - Palavras-chave indicando certeza (+0.1)
        - Palavras-chave indicando incerteza (-0.2)
        """
        confianca_base = 0.5  # Base de 50%
        
        # Artigos citados aumentam confiança
        if len(artigos_citados) > 0:
            confianca_base += min(0.3, len(artigos_citados) * 0.1)
        
        # Fontes do knowledge base aumentam confiança
        if len(fontes) > 0:
            confianca_base += min(0.2, len(fontes) * 0.1)
        
        # Tamanho adequado da resposta (não muito curta, não muito longa)
        tamanho = len(resposta.split())
        if 50 <= tamanho <= 500:
            confianca_base += 0.1
        elif tamanho < 20:
            confianca_base -= 0.2  # Resposta muito curta
        
        # Palavras-chave de certeza
        palavras_certeza = ['artigo', 'resolução', 'parágrafo', 'inciso', 'conforme', 'determina', 'estabelece']
        if any(palavra in resposta.lower() for palavra in palavras_certeza):
            confianca_base += 0.1
        
        # Palavras-chave de incerteza
        palavras_incerteza = ['não encontrei', 'não há informação', 'não foi possível', 'não encontrado', 'sem dados']
        if any(palavra in resposta.lower() for palavra in palavras_incerteza):
            confianca_base -= 0.2
        
        # Limitar entre 0.0 e 1.0
        return max(0.0, min(1.0, confianca_base))


class TeamCoordenador:
    """
    Team Coordenador que consolida respostas dos agentes especializados.
    
    Usa modelo mais poderoso (gpt-5.2-2025-12-11) para:
    - Sintetizar informações de múltiplas versões
    - Identificar gaps e inconsistências
    - Propor texto consolidado
    """
    
    def __init__(self, agentes: Dict[str, AgenteEspecialista]):
        self.agentes = agentes
        self.team: Optional[Team] = None
        self.modelo_id = os.getenv("MODEL_COORDENADOR", "gpt-5.2-2025-12-11")
        
    async def inicializar(self) -> bool:
        """Inicializa o Team Agno."""
        if not AGNO_AVAILABLE:
            logger.warning("⚠️ Agno não disponível para Team Coordenador")
            return False
        
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("❌ OPENAI_API_KEY não encontrada")
                return False
            
            # Coletar agentes Agno dos especialistas
            membros = []
            for versao, especialista in self.agentes.items():
                if especialista.agent:
                    membros.append(especialista.agent)
            
            if not membros:
                logger.warning("⚠️ Nenhum agente disponível para o Team")
                return False
            
            # Database para sessões do Team
            db = SqliteDb(db_file="tmp/team_sessions.db")
            
            # Criar Team
            # show_members_responses=True permite que os membros vejam respostas uns dos outros
            self.team = Team(
                name="Coordenador de Análise Regulamentar",
                model=OpenAIChat(
                    id=self.modelo_id,
                    api_key=api_key
                ),
                members=membros,
                db=db,
                instructions=[
                    "Você é o Team Coordenador responsável por construir e consolidar a nova Minuta V2 do Regulamento Interno do TRE-GO.",
                    "",
                    "## Seu Papel Principal:",
                    "- Você é RESPONSÁVEL pela CONSTRUÇÃO de novas minutas e pela consolidação final de toda a discussão.",
                    "- Os agentes especializados fornecem informações e análises, mas a CONSTRUÇÃO do texto consolidado é SUA responsabilidade.",
                    "- Você coordena a análise entre múltiplas versões históricas do regulamento (1997, 2007, 2017) e as alterações recentes.",
                    "",
                    "## Como Trabalhar com os Agentes:",
                    "- Os agentes podem ver as respostas uns dos outros para uma análise mais colaborativa.",
                    "- Cada agente trabalha com uma versão diferente do regulamento.",
                    "- Agente #1 (1997): Versão histórica original - resgata pontos importantes que não devem ser esquecidos.",
                    "- Agente #2 (2007): Versão intermediária - preserva melhorias históricas.",
                    "- Agente #3 (2017): Versão VIGENTE - é a BASE para a nova minuta.",
                    "- Agente #4 (Alterações): Mudanças recentes (2021-2025) - identifica o que foi modificado.",
                    "- Agente #5 (Minuta V2): Relata o que já está documentado na minuta em construção - ajuda a consolidar o progresso.",
                    "",
                    "## Processo de Consolidação:",
                    "Ao sintetizar as respostas dos agentes, identifique e apresente:",
                    "",
                    "1. **Pontos Comuns**: O que está presente em múltiplas versões e deve ser mantido.",
                    "",
                    "2. **Evolução Temporal**: Como o regulamento evoluiu ao longo do tempo (1997 → 2007 → 2017 → alterações recentes).",
                    "",
                    "3. **Gaps e Lacunas**: O que está faltando na versão vigente (2017) mas existia em versões anteriores e deve ser resgatado.",
                    "",
                    "4. **Conteúdo a Resgatar**: Pontos importantes das versões antigas (especialmente 1997 e 2007) que foram perdidos mas devem ser considerados.",
                    "",
                    "5. **Inconsistências**: Contradições ou conflitos entre as versões - explique em termos de evolução.",
                    "",
                    "6. **Alterações Recentes**: Integre todas as mudanças recentes (2021-2025) identificadas pelo Agente #4.",
                    "",
                    "7. **Estado Atual da Minuta**: Considere o que já está na Minuta V2 (relatado pelo Agente #5) para consolidar o progresso existente.",
                    "",
                    "## Construção da Nova Minuta:",
                    "- A BASE é a versão vigente (2017), mas você deve:",
                    "  * Resgatar pontos importantes de versões anteriores que foram perdidos.",
                    "  * Incorporar todas as alterações recentes.",
                    "  * Considerar o progresso já feito na Minuta V2.",
                    "  * Propor melhorias e atualizações quando necessário.",
                    "",
                    "- Quando apropriado, PROPOSTE UM TEXTO CONSOLIDADO para a nova minuta.",
                    "- O texto consolidado deve:",
                    "  * Ser claro, preciso e bem estruturado.",
                    "  * Seguir o formato de regulamento interno.",
                    "  * Incorporar o melhor de cada versão.",
                    "  * Atualizar e modernizar quando necessário.",
                    "",
                    "## Diretrizes Importantes:",
                    "- Sempre cite as fontes e artigos específicos (ex: Art. 47, §2º, inciso I).",
                    "- Use formatação Markdown para melhorar a legibilidade.",
                    "- Seja objetivo e direto nas análises.",
                    "- Identifique claramente o que é proposta de texto novo vs. o que já existe.",
                    "- Destaque recomendações importantes para a construção da nova minuta.",
                    "",
                    "## Modo de Redação de Minuta Atualizada:",
                    "Quando solicitado para GERAR uma minuta atualizada completa:",
                    "",
                    "1. **Base Estrutural**:",
                    "   - Use a minuta original (fornecida pelo Agente #5) como base estrutural COMPLETA",
                    "   - Mantenha TODA a estrutura: títulos, capítulos, seções, artigos, parágrafos, incisos",
                    "   - Preserve a numeração original de artigos",
                    "",
                    "2. **Aplicar Alterações**:",
                    "   - Incorpore APENAS as alterações propostas na consolidação da sessão",
                    "   - Mantenha todo o conteúdo original que NÃO foi alterado",
                    "   - Aplique mudanças de forma precisa e cirúrgica",
                    "",
                    "3. **Preservar Formato**:",
                    "   - Mantenha formatação de artigos, parágrafos, incisos exatamente como no original",
                    "   - Preserve estrutura de títulos e capítulos",
                    "   - Mantenha estilo normativo (linguagem jurídica formal)",
                    "   - Não adicione comentários, explicações ou formatação markdown",
                    "",
                    "4. **Output Completo**:",
                    "   - Retorne o texto COMPLETO da minuta atualizada",
                    "   - NÃO retorne apenas as alterações ou um diff",
                    "   - Retorne o documento inteiro, do início ao fim",
                    "   - O texto deve estar pronto para ser salvo diretamente em arquivo .txt",
                    "",
                    "5. **Validação Interna**:",
                    "   - Verifique que todas as alterações consolidadas foram aplicadas",
                    "   - Garanta que não há quebras de estrutura ou numeração",
                    "   - Confirme que o tamanho do documento é razoável (não muito menor que o original)",
                    "",
                    "6. **Quando Gerar Minuta**:",
                    "   - Apenas quando explicitamente solicitado com instrução 'GERAR MINUTA ATUALIZADA'",
                    "   - Use o contexto completo: minuta original + consolidação + instruções do usuário",
                    "   - Se houver dúvida sobre uma alteração, mantenha o texto original",
                ],
                markdown=True,
                show_members_responses=True,  # Permite que membros vejam respostas uns dos outros
            )
            
            logger.info(f"✅ Team Coordenador inicializado com {len(membros)} membros")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Team: {e}")
            return False
    
    async def consolidar(
        self,
        tema: str,
        respostas_agentes: Dict[str, RespostaAgente]
    ) -> AnaliseEvolutiva:
        """
        Consolida respostas dos agentes em uma análise evolutiva.
        
        Args:
            tema: Tema analisado
            respostas_agentes: Respostas de cada agente especialista
            
        Returns:
            AnaliseEvolutiva com a síntese
        """
        logger.info(f"🧠 Team Coordenador consolidando análise sobre: {tema}")
        
        # Se Team disponível, usar
        if self.team:
            try:
                # Preparar prompt com respostas dos agentes
                prompt = self._preparar_prompt_consolidacao(tema, respostas_agentes)
                
                # Executar team
                response = await self.team.arun(prompt)
                
                # Extrair resposta
                proposta = response.content if hasattr(response, 'content') else str(response)
                
                # Criar análise evolutiva
                analise = AnaliseEvolutiva(
                    tema_analisado=tema,
                    respostas_por_versao=respostas_agentes,
                    proposta_consolidada=proposta,
                    gaps_identificados=self._extrair_gaps(proposta),
                    observacoes=["Análise realizada pelo Team Coordenador"]
                )
                
                logger.info("✅ Consolidação concluída")
                return analise
                
            except Exception as e:
                logger.error(f"❌ Erro na consolidação: {e}")
        
        # Fallback: consolidação simples
        return self._consolidacao_fallback(tema, respostas_agentes)
    
    def _preparar_prompt_consolidacao(
        self,
        tema: str,
        respostas: Dict[str, RespostaAgente]
    ) -> str:
        """Prepara prompt para consolidação."""
        prompt = f"""
Analise as seguintes respostas dos especialistas sobre "{tema}":

"""
        for versao, resposta in respostas.items():
            prompt += f"""
### {resposta.agente_nome}
{resposta.resposta}
Artigos citados: {', '.join(resposta.artigos_citados) if resposta.artigos_citados else 'Nenhum'}
Confiança: {resposta.confianca * 100:.0f}%

---
"""
        
        prompt += """
Com base nessas informações, forneça:

1. **Síntese Comparativa**: O que cada versão traz sobre o tema?
2. **Evolução Histórica**: Como o tratamento do tema evoluiu?
3. **Gaps Identificados**: O que a Minuta V2 está perdendo das versões anteriores?
4. **Proposta de Texto**: Sugira um texto consolidado que incorpore o melhor de cada versão.
5. **Recomendações**: Sugestões específicas para a comissão de revisão.
"""
        return prompt
    
    def _extrair_gaps(self, texto: str) -> List[GapIdentificado]:
        """Extrai gaps identificados do texto de consolidação."""
        # Implementação simplificada - em produção, usar NLP mais sofisticado
        gaps = []
        
        # Buscar padrões de gaps no texto
        if "gap" in texto.lower() or "lacuna" in texto.lower() or "faltando" in texto.lower():
            gaps.append(GapIdentificado(
                descricao="Gap identificado na análise - verificar texto consolidado",
                versao_origem="versões anteriores",
                versao_destino="Minuta V2",
                criticidade=Criticidade.MEDIA,
                sugestao_resgate="Ver proposta de texto consolidado"
            ))
        
        return gaps
    
    def _consolidacao_fallback(
        self,
        tema: str,
        respostas: Dict[str, RespostaAgente]
    ) -> AnaliseEvolutiva:
        """Fallback para consolidação quando Team não disponível."""
        logger.warning("⚠️ Usando consolidação fallback")
        
        # Concatenar respostas
        proposta = f"## Consolidação sobre: {tema}\n\n"
        proposta += "⚠️ *Consolidação automática em modo fallback*\n\n"
        
        for versao, resposta in respostas.items():
            proposta += f"### {resposta.agente_nome}\n"
            proposta += f"{resposta.resposta}\n\n"
        
        proposta += "\n---\n*Para consolidação inteligente, configure o Agno Team.*"
        
        return AnaliseEvolutiva(
            tema_analisado=tema,
            respostas_por_versao=respostas,
            proposta_consolidada=proposta,
            gaps_identificados=[],
            observacoes=["Consolidação em modo fallback - Team não disponível"]
        )


# ============================================================================
# FÁBRICA DE AGENTES
# ============================================================================

class GerenciadorAgentes:
    """Gerencia criação e acesso aos agentes e team."""
    
    # Configuração dos agentes
    AGENTES_CONFIG = {
        VersaoRegulamento.RES_1997: {
            "numero": 1,
            "nome": "Especialista #1 - Resolução 05/1997",
            "descricao": "Especialista no Regulamento Interno original do TRE-GO (1997)"
        },
        VersaoRegulamento.RES_2007: {
            "numero": 2,
            "nome": "Especialista #2 - Resolução 113/2007",
            "descricao": "Especialista no Regulamento Interno de 2007"
        },
        VersaoRegulamento.RES_2017: {
            "numero": 3,
            "nome": "Especialista #3 - Resolução 275/2017",
            "descricao": "Especialista no Regulamento Interno vigente (2017)"
        },
        VersaoRegulamento.ALTERACOES: {
            "numero": 4,
            "nome": "Especialista #4 - Alterações 2021-2025",
            "descricao": "Especialista nas alterações recentes do regulamento"
        },
        VersaoRegulamento.MINUTA_V2: {
            "numero": 5,
            "nome": "Especialista #5 - Minuta V2",
            "descricao": "Especialista na minuta em construção do novo regulamento"
        }
    }
    
    def __init__(self):
        self.agentes: Dict[str, AgenteEspecialista] = {}
        self.team: Optional[TeamCoordenador] = None
        self._initialized = False
    
    async def inicializar(self) -> bool:
        """Inicializa todos os agentes e o team."""
        logger.info("🚀 Inicializando Gerenciador de Agentes...")
        
        # Obter knowledge manager
        km = get_knowledge_manager()
        
        # Criar agentes
        for versao, config in self.AGENTES_CONFIG.items():
            agente = AgenteEspecialista(
                versao=versao,
                nome=config["nome"],
                descricao=config["descricao"],
                knowledge_manager=km
            )
            
            success = await agente.inicializar()
            if success:
                self.agentes[versao.value] = agente
                logger.info(f"   ✅ {config['nome']}")
            else:
                logger.warning(f"   ⚠️ {config['nome']} (fallback)")
                # Adicionar mesmo em fallback
                self.agentes[versao.value] = agente
        
        # Criar Team Coordenador
        self.team = TeamCoordenador(self.agentes)
        await self.team.inicializar()
        
        self._initialized = True
        logger.info(f"✅ Gerenciador inicializado com {len(self.agentes)} agentes")
        return True
    
    def obter_agente(self, versao: str) -> Optional[AgenteEspecialista]:
        """Obtém um agente por versão."""
        return self.agentes.get(versao)
    
    async def consultar_agente(
        self, 
        versao: str, 
        pergunta: str,
        contexto_agentes: Optional[List[RespostaAgente]] = None
    ) -> RespostaAgente:
        """
        Consulta um agente específico.
        
        Args:
            versao: Versão do regulamento (agente)
            pergunta: Pergunta do usuário
            contexto_agentes: Respostas anteriores de outros agentes para contexto
        """
        agente = self.obter_agente(versao)
        if not agente:
            return RespostaAgente(
                agente=versao,
                agente_nome=f"Agente {versao}",
                pergunta=pergunta,
                resposta=f"Agente '{versao}' não encontrado",
                confianca=0.0
            )
        
        # Se houver contexto de outros agentes, incluir na pergunta
        # IMPORTANTE: Limitar contexto para evitar exceder limite de tokens do modelo (8192 para gpt-5-mini)
        # Limites conservadores: máximo 3 respostas, 800 chars por resposta
        if contexto_agentes:
            # Estimar tamanho aproximado da pergunta (1 char ≈ 0.25 tokens)
            tamanho_pergunta_estimado = len(pergunta) * 0.25
            
            # Se a pergunta já é muito grande (>1500 tokens estimados), não adicionar contexto
            # O Agno adiciona documentos da knowledge base, então precisamos ser mais conservadores
            if tamanho_pergunta_estimado > 1500:
                logger.warning(f"⚠️ Pergunta muito longa ({len(pergunta)} chars, ~{tamanho_pergunta_estimado:.0f} tokens) - pulando contexto adicional para evitar erro de tokens")
                return await agente.consultar(pergunta)
            
            # Limitar ainda mais: máximo 2 respostas, 600 chars por resposta
            # (já recebemos apenas últimas 2 interações da sessão, mas vamos garantir)
            contexto_texto = self._formatar_contexto_agentes(contexto_agentes, max_respostas=2, max_chars_por_resposta=600)
            
            # Estimar tamanho total aproximado do prompt
            # IMPORTANTE: O Agno adiciona documentos da knowledge base automaticamente,
            # então precisamos deixar margem para isso (~2000-3000 tokens)
            tamanho_contexto_estimado = len(contexto_texto) * 0.25
            tamanho_estimado = tamanho_pergunta_estimado + tamanho_contexto_estimado + 2000  # +2000 para overhead + knowledge base
            
            # Se exceder ~4000 tokens estimados (deixando margem para knowledge base do Agno),
            # reduzir drasticamente ou não adicionar contexto
            if tamanho_estimado > 4000:
                logger.warning(f"⚠️ Contexto muito grande (~{tamanho_estimado:.0f} tokens estimados, incluindo margem para knowledge base) - reduzindo drasticamente")
                contexto_texto = self._formatar_contexto_agentes(contexto_agentes[-1:], max_respostas=1, max_chars_por_resposta=300)
                tamanho_novo_estimado = tamanho_pergunta_estimado + len(contexto_texto) * 0.25 + 2000
                if tamanho_novo_estimado > 3500:
                    # Se ainda estiver muito grande, não adicionar contexto
                    logger.warning(f"⚠️ Ainda muito grande após redução (~{tamanho_novo_estimado:.0f} tokens) - pulando contexto para evitar erro")
                    return await agente.consultar(pergunta)
            
            pergunta_com_contexto = f"""{pergunta}

---
**Contexto das respostas de outros especialistas (limitado para evitar erro):**

{contexto_texto}

Por favor, considere essas informações e forneça sua análise, complementando, corrigindo ou confirmando o que os outros especialistas disseram."""
            return await agente.consultar(pergunta_com_contexto)
        
        return await agente.consultar(pergunta)
    
    def _formatar_contexto_agentes(self, respostas: List[RespostaAgente], max_respostas: int = 3, max_chars_por_resposta: int = 800) -> str:
        """
        Formata respostas de outros agentes como contexto.
        
        IMPORTANTE: Limita o número de respostas e o tamanho de cada uma para evitar
        exceder o limite de tokens do modelo (8192 tokens para gpt-5-mini).
        
        Args:
            respostas: Lista de respostas para formatar
            max_respostas: Número máximo de respostas a incluir (padrão: 8)
            max_chars_por_resposta: Número máximo de caracteres por resposta (padrão: 800)
        """
        # Limitar número de respostas (pegar as mais recentes)
        respostas_limitadas = respostas[-max_respostas:] if len(respostas) > max_respostas else respostas
        
        contexto = []
        for resposta in respostas_limitadas:
            contexto.append(f"### {resposta.agente_nome}")
            
            # Truncar resposta se muito longa
            resposta_texto = resposta.resposta
            if len(resposta_texto) > max_chars_por_resposta:
                resposta_texto = resposta_texto[:max_chars_por_resposta] + "... [truncado]"
            
            contexto.append(f"{resposta_texto}")
            
            if resposta.artigos_citados:
                artigos_str = ', '.join(resposta.artigos_citados[:5])  # Limitar a 5 artigos
                if len(resposta.artigos_citados) > 5:
                    artigos_str += f" ... e mais {len(resposta.artigos_citados) - 5}"
                contexto.append(f"*Artigos citados: {artigos_str}*")
            
            contexto.append("")  # Linha em branco
        
        if len(respostas) > max_respostas:
            contexto.insert(0, f"*Nota: Mostrando apenas as últimas {max_respostas} resposta(s) de {len(respostas)} resposta(s) anterior(es) para evitar limite de tokens*\n")
        
        return "\n".join(contexto)
    
    async def consultar_agentes_colaborativo(
        self,
        pergunta: str,
        versoes: Optional[List[str]] = None,
        contexto_sessao: Optional[List[RespostaAgente]] = None
    ) -> Dict[str, RespostaAgente]:
        """
        Consulta múltiplos agentes de forma colaborativa.
        
        Cada agente vê as respostas dos agentes anteriores antes de responder.
        Isso permite uma análise mais rica onde agentes podem:
        - Complementar informações de outros agentes
        - Corrigir inconsistências
        - Confirmar pontos importantes
        
        Args:
            pergunta: Pergunta inicial
            versoes: Lista de versões para consultar (None = todas)
            contexto_sessao: Respostas anteriores da sessão para contexto adicional
            
        Returns:
            Dict com respostas de cada agente
        """
        versoes_consultar = versoes or list(self.agentes.keys())
        respostas_acumuladas = []
        respostas_finais = {}
        
        # Incluir contexto da sessão se disponível
        if contexto_sessao:
            respostas_acumuladas.extend(contexto_sessao)
        
        logger.info(f"🤝 Iniciando consulta colaborativa com {len(versoes_consultar)} agentes")
        
        for versao in versoes_consultar:
            # Consultar agente com contexto das respostas anteriores
            resposta = await self.consultar_agente(
                versao=versao,
                pergunta=pergunta,
                contexto_agentes=respostas_acumuladas if respostas_acumuladas else None
            )
            
            respostas_finais[versao] = resposta
            respostas_acumuladas.append(resposta)
            
            logger.info(f"   ✅ {resposta.agente_nome} respondeu (vendo {len(respostas_acumuladas)-1} resposta(s) anterior(es))")
        
        return respostas_finais
    
    async def consolidar(
        self,
        tema: str,
        versoes: Optional[List[str]] = None,
        usar_colaborativo: bool = True
    ) -> AnaliseEvolutiva:
        """
        Consulta múltiplos agentes e consolida.
        
        Args:
            tema: Tema para análise
            versoes: Versões específicas (None = todas)
            usar_colaborativo: Se True, agentes veem respostas anteriores (padrão: True)
        """
        versoes_consultar = versoes or list(self.agentes.keys())
        
        # Usar consulta colaborativa se solicitado (padrão)
        if usar_colaborativo:
            logger.info(f"🤝 Usando modo colaborativo: agentes verão respostas uns dos outros")
            respostas = await self.consultar_agentes_colaborativo(
                pergunta=tema,
                versoes=versoes_consultar
            )
        else:
            # Modo tradicional: cada agente responde independentemente
            logger.info(f"📝 Usando modo independente: cada agente responde isoladamente")
            respostas = {}
            for versao in versoes_consultar:
                resposta = await self.consultar_agente(versao, tema)
                respostas[versao] = resposta
        
        # Consolidar com Team (que agora recebe respostas já coletadas)
        if self.team:
            return await self.team.consolidar(tema, respostas)
        
        # Fallback se team não disponível
        
        # Fallback
        return AnaliseEvolutiva(
            tema_analisado=tema,
            respostas_por_versao=respostas,
            proposta_consolidada="Team não disponível para consolidação"
        )
    
    def status(self) -> Dict:
        """Retorna status dos agentes."""
        return {
            "inicializado": self._initialized,
            "agentes": {
                versao: {
                    "nome": agente.nome,
                    "agno_ativo": agente.agent is not None
                }
                for versao, agente in self.agentes.items()
            },
            "team_ativo": self.team is not None and self.team.team is not None
        }


# ============================================================================
# SINGLETON GLOBAL
# ============================================================================

_gerenciador: Optional[GerenciadorAgentes] = None


def get_gerenciador_agentes() -> GerenciadorAgentes:
    """Obtém instância global do GerenciadorAgentes."""
    global _gerenciador
    if _gerenciador is None:
        _gerenciador = GerenciadorAgentes()
    return _gerenciador


async def inicializar_agentes_global() -> bool:
    """Inicializa o GerenciadorAgentes global."""
    gerenciador = get_gerenciador_agentes()
    return await gerenciador.inicializar()
