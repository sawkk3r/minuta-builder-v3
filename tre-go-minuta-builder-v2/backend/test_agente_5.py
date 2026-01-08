#!/usr/bin/env python3
"""
Teste isolado para o Agente #5 (Minuta V2)
Compara comportamento com um agente que funciona (Agente #1)
"""
import asyncio
import sys
import os

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Tentar carregar dotenv
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    print("⚠️  dotenv não disponível - usando variáveis de ambiente do sistema")

from knowledge_manager import get_knowledge_manager
from agents import AgenteEspecialista, VersaoRegulamento
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_knowledge_base(versao: str, nome: str):
    """Testa a knowledge base diretamente."""
    print(f"\n{'='*60}")
    print(f"TESTE: Knowledge Base '{versao}' ({nome})")
    print(f"{'='*60}")
    
    km = get_knowledge_manager()
    await km.inicializar()
    
    knowledge = km.obter_knowledge(versao)
    if not knowledge:
        print(f"❌ Knowledge base '{versao}' não encontrada!")
        return False
    
    print(f"✅ Knowledge base encontrada: {knowledge.name}")
    
    # Verificar vector_db
    if hasattr(knowledge, 'vector_db'):
        vdb = knowledge.vector_db
        print(f"   URI: {getattr(vdb, 'uri', 'N/A')}")
        print(f"   Table name: {getattr(vdb, 'table_name', 'N/A')}")
        
        # Verificar tabela
        if hasattr(vdb, 'table'):
            table = vdb.table
            if table is not None:
                try:
                    count = table.count_rows()
                    print(f"   ✅ Tabela carregada: {count} registros")
                    
                    # Testar busca direta
                    print(f"\n   🔍 Testando busca direta...")
                    try:
                        results = await knowledge.async_search(query="Diretoria", max_results=3)
                        print(f"   Resultados: {len(results)} documentos encontrados")
                        if results:
                            for i, r in enumerate(results[:2]):
                                content = str(r.content if hasattr(r, 'content') else r)[:150]
                                print(f"      [{i+1}] {content}...")
                        else:
                            print(f"   ❌ Nenhum resultado encontrado!")
                    except Exception as e:
                        print(f"   ❌ Erro na busca: {e}")
                        import traceback
                        traceback.print_exc()
                except Exception as e:
                    print(f"   ❌ Erro ao contar registros: {e}")
            else:
                print(f"   ❌ Tabela é None!")
        else:
            print(f"   ❌ vector_db não tem atributo 'table'")
    
    return True

async def test_agente(versao: VersaoRegulamento, nome: str, pergunta: str):
    """Testa um agente específico."""
    print(f"\n{'='*60}")
    print(f"TESTE: {nome}")
    print(f"{'='*60}")
    
    km = get_knowledge_manager()
    await km.inicializar()
    
    # Criar agente
    agente = AgenteEspecialista(
        versao=versao,
        nome=nome,
        descricao=f"Teste {nome}",
        knowledge_manager=km
    )
    
    # Inicializar
    print(f"\n1. Inicializando agente...")
    success = await agente.inicializar()
    if not success:
        print(f"   ❌ Falha na inicialização")
        return False
    
    print(f"   ✅ Agente inicializado")
    
    # Verificar knowledge base do agent
    if hasattr(agente, 'agent') and agente.agent:
        if hasattr(agente.agent, 'knowledge'):
            kb = agente.agent.knowledge
            print(f"   Agent.knowledge: {kb.name if hasattr(kb, 'name') else kb}")
            
            if hasattr(kb, 'vector_db') and hasattr(kb.vector_db, 'table'):
                table = kb.vector_db.table
                if table:
                    try:
                        count = table.count_rows()
                        print(f"   Agent.knowledge.vector_db.table: {count} registros")
                    except:
                        print(f"   Agent.knowledge.vector_db.table: erro ao contar")
    
    # Consultar agente
    print(f"\n2. Consultando agente...")
    print(f"   Pergunta: {pergunta}")
    
    try:
        resposta = await agente.consultar(pergunta)
        print(f"\n   ✅ Resposta recebida:")
        print(f"   Confiança: {resposta.confianca*100:.0f}%")
        print(f"   Artigos citados: {len(resposta.artigos_citados)}")
        print(f"   Fontes: {len(resposta.fontes_conhecimento)}")
        print(f"\n   Resposta (primeiros 500 chars):")
        print(f"   {resposta.resposta[:500]}...")
        
        if len(resposta.fontes_conhecimento) == 0 and resposta.confianca < 0.5:
            print(f"\n   ⚠️  ATENÇÃO: Nenhuma fonte encontrada e confiança baixa!")
            print(f"   Isso indica que a busca RAG não funcionou.")
        
        return True
    except Exception as e:
        print(f"   ❌ Erro ao consultar: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("="*60)
    print("TESTE ISOLADO: Agente #5 vs Agente #1")
    print("="*60)
    
    # Teste 1: Knowledge Base direta
    print("\n" + "="*60)
    print("FASE 1: Testando Knowledge Bases diretamente")
    print("="*60)
    
    await test_knowledge_base("1997", "Agente #1 (funciona)")
    await test_knowledge_base("minuta", "Agente #5 (não funciona)")
    
    # Teste 2: Agentes
    print("\n" + "="*60)
    print("FASE 2: Testando Agentes")
    print("="*60)
    
    pergunta = "Me fale sobre a Diretoria Geral"
    
    await test_agente(
        VersaoRegulamento.RES_1997,
        "Especialista #1 - Resolução 05/1997",
        pergunta
    )
    
    await test_agente(
        VersaoRegulamento.MINUTA_V2,
        "Especialista #5 - Minuta V2",
        pergunta
    )
    
    # Comparação final
    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    print("""
    Se o Agente #1 encontrou documentos mas o #5 não:
    - O problema está específico na knowledge base 'minuta' ou no Agent do Agno
    - Pode ser bug do Agno ou problema de referência interna
    
    Se ambos não encontraram:
    - O problema é mais geral (configuração, API key, etc.)
    
    Se ambos encontraram:
    - O problema pode estar na inicialização do servidor ou timing
    """)

if __name__ == "__main__":
    asyncio.run(main())
