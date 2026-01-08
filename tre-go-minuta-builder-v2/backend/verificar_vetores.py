#!/usr/bin/env python3
"""Script simples para verificar se os vetores da minuta foram criados"""
import sys
import os

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

try:
    import lancedb
    from pathlib import Path
    
    base_dir = Path(__file__).resolve().parent.parent
    lance_path = base_dir / "tmp" / "lancedb_minuta"
    
    if not lance_path.exists():
        print("❌ Diretório lancedb_minuta não existe!")
        print(f"   Caminho esperado: {lance_path}")
        sys.exit(1)
    
    db = lancedb.connect(str(lance_path))
    
    if "regulamento_minuta" not in db.table_names():
        print("❌ Tabela 'regulamento_minuta' não existe!")
        sys.exit(1)
    
    table = db.open_table("regulamento_minuta")
    count = table.count_rows()
    
    print(f"✅ Tabela encontrada: {count} registros")
    
    if count == 0:
        print("❌ Tabela está vazia!")
        sys.exit(1)
    
    # Verificar vetores
    sample = table.head(3).to_pandas()
    vetores_ok = 0
    vetores_none = 0
    
    for i, row in sample.iterrows():
        vector = row.get('vector')
        if vector is None:
            vetores_none += 1
        else:
            vec_array = list(vector) if hasattr(vector, '__iter__') else vector
            if vec_array and len(vec_array) > 0 and any(abs(v) > 0.0001 for v in vec_array[:10]):
                vetores_ok += 1
    
    print(f"\nVerificando vetores (amostra de 3 registros):")
    print(f"  ✅ Vetores OK: {vetores_ok}")
    print(f"  ❌ Vetores None: {vetores_none}")
    
    if vetores_ok > 0:
        print("\n🎉 SUCESSO! Vetores foram criados corretamente!")
        print("   O Agente #5 deve funcionar agora.")
        sys.exit(0)
    else:
        print("\n❌ PROBLEMA: Vetores ainda são None!")
        print("   Os embeddings não foram criados.")
        print("   Verifique os logs da indexação.")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    print("   Certifique-se de estar no venv correto:")
    print("   cd /Users/vcr/Documents/GitHub/rev_reg_int_tre/tre-go-minuta-builder-v2")
    print("   source venv/bin/activate")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
