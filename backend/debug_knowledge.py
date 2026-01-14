#!/usr/bin/env python3
"""
Script de debug para verificar a knowledge base da minuta
"""
import asyncio
import sys
import os

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Tentar carregar dotenv (opcional)
try:
    from dotenv import load_dotenv
    # Carregar do diretório raiz do projeto
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()  # Tentar carregar do diretório atual
except ImportError:
    print("⚠️  dotenv não disponível - usando variáveis de ambiente do sistema")

async def main():
    print("=" * 60)
    print("DEBUG: Verificando Knowledge Base da Minuta")
    print("=" * 60)
    
    from knowledge_manager import get_knowledge_manager
    
    km = get_knowledge_manager()
    print(f"\n1. Inicializando Knowledge Manager...")
    await km.inicializar()
    print(f"   Status: {km.status()}")
    
    # Verificar knowledge base da minuta
    print(f"\n2. Obtendo knowledge base 'minuta'...")
    knowledge = km.obter_knowledge("minuta")
    
    if knowledge is None:
        print("   ❌ Knowledge base 'minuta' não encontrada!")
        return
    
    print(f"   ✅ Knowledge base encontrada: {knowledge}")
    print(f"   Nome: {knowledge.name if hasattr(knowledge, 'name') else 'N/A'}")
    
    # Verificar vector_db
    print(f"\n3. Verificando vector_db...")
    if hasattr(knowledge, 'vector_db'):
        vdb = knowledge.vector_db
        print(f"   Vector DB: {vdb}")
        print(f"   URI: {vdb.uri if hasattr(vdb, 'uri') else 'N/A'}")
        print(f"   Table name: {vdb.table_name if hasattr(vdb, 'table_name') else 'N/A'}")
        
        # Verificar tabela
        if hasattr(vdb, 'table'):
            table = vdb.table
            print(f"   Table object: {table}")
            if table is not None:
                try:
                    if hasattr(table, 'count_rows'):
                        count = table.count_rows()
                        print(f"   ✅ Contagem de registros: {count}")
                    if hasattr(table, 'head'):
                        sample = table.head(3)
                        print(f"   Amostra (3 primeiros):")
                        print(f"   {sample}")
                except Exception as e:
                    print(f"   ⚠️ Erro ao acessar tabela: {e}")
            else:
                print("   ❌ Table é None!")
        else:
            print("   ❌ vector_db não tem atributo 'table'")
    else:
        print("   ❌ Knowledge não tem atributo 'vector_db'")
    
    # Testar busca direta
    print(f"\n4. Testando busca direta...")
    try:
        results = await knowledge.async_search(query="Diretoria", max_results=3)
        print(f"   Resultados: {results}")
        if results:
            for i, r in enumerate(results):
                print(f"   [{i}] {r}")
        else:
            print("   ❌ Nenhum resultado retornado!")
    except Exception as e:
        print(f"   ❌ Erro na busca: {e}")
        import traceback
        traceback.print_exc()
    
    # Testar busca via km.buscar
    print(f"\n5. Testando busca via km.buscar()...")
    try:
        results = await km.buscar(versao="minuta", query="Diretoria", num_results=3)
        print(f"   Resultados: {results}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Verificar se a tabela está abrindo corretamente
    print(f"\n6. Verificando conexão LanceDB direta...")
    try:
        import lancedb
        db_path = "/Users/vcr/Documents/GitHub/rev_reg_int_tre/tre-go-minuta-builder-v2/tmp/lancedb_minuta"
        db = lancedb.connect(db_path)
        tables = db.table_names()
        print(f"   Tabelas disponíveis: {tables}")
        
        if "regulamento_minuta" in tables:
            table = db.open_table("regulamento_minuta")
            count = table.count_rows()
            print(f"   ✅ Tabela 'regulamento_minuta' tem {count} registros")
            
            # Mostrar schema
            print(f"   Schema: {table.schema}")
            
            # Mostrar amostra
            sample = table.head(2).to_pandas()
            print(f"   Colunas: {list(sample.columns)}")
            if 'content' in sample.columns:
                print(f"   Amostra de conteúdo:")
                for i, row in sample.iterrows():
                    content = str(row.get('content', ''))[:100]
                    print(f"      [{i}] {content}...")
        else:
            print(f"   ❌ Tabela 'regulamento_minuta' não encontrada!")
    except Exception as e:
        print(f"   ❌ Erro ao conectar LanceDB: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("DEBUG CONCLUÍDO")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
