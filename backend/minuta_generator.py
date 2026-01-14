# ============================================================================
# ARQUIVO: backend/minuta_generator.py
# Gerador de Minutas Atualizadas por Sessão
# ============================================================================

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

from models import AnaliseEvolutiva, SessaoAnalise
from agents import TeamCoordenador, AgenteEspecialista, VersaoRegulamento


class MinutaGenerator:
    """
    Gerencia a geração de minutas atualizadas baseadas em sessões.
    
    Funcionalidades:
    - Lê minuta original (via Agente #5)
    - Coordena geração com Team Coordenador
    - Salva arquivos minuta{session_id}.txt
    - Valida estrutura e formatação
    """
    
    def __init__(
        self,
        team_coordenador: TeamCoordenador,
        agente_minuta: AgenteEspecialista,
        minuta_original_path: str = "files/regulamentos/minuta.txt",
        output_dir: str = "files/regulamentos/minutas_sessao"
    ):
        self.team = team_coordenador
        self.agente_minuta = agente_minuta
        self.minuta_original_path = Path(minuta_original_path)
        self.output_dir = Path(output_dir)
        
        # Criar diretório de saída
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def obter_minuta_original(self) -> str:
        """
        Obtém o conteúdo completo da minuta original.
        
        Usa o Agente #5 para ler e estruturar o conteúdo.
        
        Returns:
            Conteúdo completo da minuta original
        """
        logger.info("📄 Obtendo minuta original via Agente #5...")
        
        # Consultar Agente #5 para obter contexto completo
        pergunta = """Forneça o conteúdo COMPLETO da Minuta V2 atual, incluindo:
1. Todo o texto do regulamento
2. Estrutura completa (títulos, capítulos, seções)
3. Todos os artigos, parágrafos e incisos
4. Formatação e numeração

Importante: Retorne o texto COMPLETO, não apenas um resumo."""
        
        try:
            resposta = await self.agente_minuta.consultar(pergunta)
            
            # Se a resposta contém o conteúdo, retornar
            # Caso contrário, ler diretamente do arquivo
            if len(resposta.resposta) > 1000:  # Resposta parece completa
                logger.info(f"✅ Minuta original obtida via Agente #5 ({len(resposta.resposta)} chars)")
                return resposta.resposta
            else:
                # Fallback: ler diretamente do arquivo
                logger.warning("⚠️ Resposta do Agente #5 muito curta, lendo arquivo diretamente")
                return await self._ler_arquivo_direto()
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter minuta via Agente #5: {e}")
            logger.info("📄 Tentando ler arquivo diretamente...")
            return await self._ler_arquivo_direto()
    
    async def _ler_arquivo_direto(self) -> str:
        """Lê o arquivo minuta.txt diretamente."""
        try:
            if not self.minuta_original_path.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {self.minuta_original_path}")
            
            with open(self.minuta_original_path, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            logger.info(f"✅ Minuta original lida do arquivo ({len(conteudo)} chars)")
            return conteudo
            
        except Exception as e:
            logger.error(f"❌ Erro ao ler arquivo: {e}")
            raise
    
    async def gerar_minuta_atualizada(
        self,
        session_id: str,
        sessao: SessaoAnalise,
        consolidacao: AnaliseEvolutiva,
        instrucoes_usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gera minuta atualizada baseada na sessão e consolidação.
        
        Args:
            session_id: ID da sessão
            sessao: Objeto da sessão com todas as interações
            consolidacao: Análise consolidada do Team
            instrucoes_usuario: Instruções adicionais do usuário (opcional)
            
        Returns:
            Dict com informações do arquivo gerado
        """
        logger.info(f"🚀 Gerando minuta atualizada para sessão {session_id}...")
        
        try:
            # 1. Obter minuta original
            minuta_original = await self.obter_minuta_original()
            
            # 2. Preparar prompt para o Team
            prompt = self._preparar_prompt_redacao(
                minuta_original=minuta_original,
                consolidacao=consolidacao,
                sessao=sessao,
                instrucoes_usuario=instrucoes_usuario
            )
            
            # 3. Team gera minuta atualizada
            logger.info("🧠 Team Coordenador gerando minuta atualizada...")
            minuta_atualizada = await self._team_gerar_minuta(prompt)
            
            # 4. Validar minuta gerada
            validacao = self._validar_minuta(minuta_atualizada, minuta_original)
            
            # 5. Salvar arquivo
            arquivo_path = await self._salvar_minuta(session_id, minuta_atualizada)
            
            logger.info(f"✅ Minuta atualizada gerada: {arquivo_path}")
            
            return {
                "sucesso": True,
                "arquivo": str(arquivo_path),
                "tamanho": len(minuta_atualizada),
                "linhas": minuta_atualizada.count('\n') + 1,
                "validacao": validacao,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar minuta atualizada: {e}", exc_info=True)
            return {
                "sucesso": False,
                "erro": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _preparar_prompt_redacao(
        self,
        minuta_original: str,
        consolidacao: AnaliseEvolutiva,
        sessao: SessaoAnalise,
        instrucoes_usuario: Optional[str]
    ) -> str:
        """Prepara prompt completo para o Team gerar a minuta."""
        
        prompt = f"""# GERAÇÃO DE MINUTA ATUALIZADA

## INSTRUÇÕES GERAIS:
Você deve gerar uma minuta atualizada baseada na minuta original, incorporando todas as alterações consolidadas da sessão.

## MINUTA ORIGINAL (BASE):
```
{minuta_original[:5000]}...
```
*(Minuta completa com {len(minuta_original)} caracteres)*

## CONSOLIDAÇÃO DA SESSÃO:
**Tema analisado:** {consolidacao.tema_analisado}

**Proposta consolidada:**
{consolidacao.proposta_consolidada or "Nenhuma proposta específica"}

**Gaps identificados:** {len(consolidacao.gaps_identificados)}
{chr(10).join([f"- {g.descricao} ({g.criticidade.value})" for g in consolidacao.gaps_identificados[:5]])}

## INTERAÇÕES DA SESSÃO:
**Total de interações:** {len(sessao.interacoes)}
**Agentes consultados:** {', '.join(set(i.agente_nome for i in sessao.interacoes))}

## INSTRUÇÕES ESPECÍFICAS DO USUÁRIO:
{instrucoes_usuario or "Nenhuma instrução específica. Aplicar todas as alterações consolidadas."}

## TAREFA:
1. **Base**: Use a minuta original como base estrutural completa
2. **Aplicar**: Incorpore todas as alterações propostas na consolidação
3. **Manter**: Preserve estrutura, numeração, formatação e estilo normativo
4. **Validar**: Garanta que todas as alterações foram aplicadas corretamente
5. **Output**: Retorne o texto COMPLETO da minuta atualizada (não apenas alterações)

## FORMATO DE SAÍDA:
Retorne APENAS o texto completo da minuta atualizada, sem comentários ou explicações adicionais.
Mantenha exatamente a mesma formatação e estrutura da minuta original, apenas aplicando as alterações consolidadas.
"""
        
        return prompt
    
    async def _team_gerar_minuta(self, prompt: str) -> str:
        """Usa o Team para gerar a minuta atualizada."""
        if not self.team.team:
            raise RuntimeError("Team Coordenador não está inicializado")
        
        # Executar Team
        response = await self.team.team.arun(prompt)
        
        # Extrair resposta
        minuta_texto = response.content if hasattr(response, 'content') else str(response)
        
        # Limpar resposta (remover markdown se houver)
        minuta_texto = self._limpar_resposta(minuta_texto)
        
        return minuta_texto
    
    def _limpar_resposta(self, texto: str) -> str:
        """Remove formatação markdown e comentários da resposta."""
        # Remover blocos de código markdown se houver
        if "```" in texto:
            # Extrair conteúdo entre blocos de código
            import re
            matches = re.findall(r'```(?:.*?)?\n(.*?)```', texto, re.DOTALL)
            if matches:
                texto = matches[-1]  # Pegar último bloco (geralmente é o conteúdo)
        
        # Remover linhas que parecem ser comentários ou instruções
        linhas = texto.split('\n')
        linhas_limpas = []
        em_conteudo = False
        
        for linha in linhas:
            # Ignorar linhas que parecem ser instruções/comentários
            if linha.strip().startswith('#') and not em_conteudo:
                continue
            if linha.strip().lower().startswith('## instruções'):
                continue
            if linha.strip().lower().startswith('## tarefa'):
                em_conteudo = True
                continue
            
            linhas_limpas.append(linha)
        
        return '\n'.join(linhas_limpas).strip()
    
    def _validar_minuta(self, minuta_atualizada: str, minuta_original: str) -> Dict[str, Any]:
        """Valida a minuta gerada."""
        validacao = {
            "estrutura_ok": True,
            "tamanho_razoavel": True,
            "artigos_presentes": True,
            "avisos": []
        }
        
        # Verificar tamanho (não deve ser muito menor que o original)
        if len(minuta_atualizada) < len(minuta_original) * 0.5:
            validacao["tamanho_razoavel"] = False
            validacao["avisos"].append("Minuta gerada muito menor que a original")
        
        # Verificar presença de artigos
        import re
        artigos_original = len(re.findall(r'Art\.?\s*\d+', minuta_original))
        artigos_atualizada = len(re.findall(r'Art\.?\s*\d+', minuta_atualizada))
        
        if artigos_atualizada < artigos_original * 0.8:
            validacao["artigos_presentes"] = False
            validacao["avisos"].append(f"Poucos artigos encontrados: {artigos_atualizada} vs {artigos_original}")
        
        return validacao
    
    async def _salvar_minuta(self, session_id: str, conteudo: str) -> Path:
        """Salva a minuta atualizada em arquivo."""
        # Nome do arquivo: minuta{session_id}.txt
        # Usar apenas parte do session_id para nome de arquivo válido
        session_id_limpo = session_id.replace('-', '')[:8]  # Primeiros 8 chars sem hífens
        filename = f"minuta_{session_id_limpo}.txt"
        filepath = self.output_dir / filename
        
        # Salvar
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        logger.info(f"💾 Minuta salva: {filepath} ({len(conteudo)} chars)")
        return filepath
