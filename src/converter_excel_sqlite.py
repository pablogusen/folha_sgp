"""
Utilitário para conversão do Excel (Descricao_Comp_Rend.xlsx) para SQLite
Mantém compatibilidade com sistema existente enquanto adiciona performance
"""

import sqlite3
import pandas as pd
from pathlib import Path

def converter_excel_para_sqlite():
    """Converte planilha Excel para banco SQLite"""
    
    # Caminhos
    pasta_base = Path(__file__).parent.parent
    arquivo_excel = pasta_base / 'data' / 'parametros' / 'Descricao_Comp_Rend.xlsx'
    arquivo_db = pasta_base / 'data' / 'parametros' / 'eventos.db'
    
    print("🔄 Convertendo Excel para SQLite...")
    
    # Criar conexão SQLite
    conn = sqlite3.connect(arquivo_db)
    
    try:
        # Ler e converter aba "Composição de Rendimentos"
        print("   📊 Processando: Composição de Rendimentos")
        df_eventos = pd.read_excel(arquivo_excel, sheet_name='Composição de Rendimentos')
        df_eventos.to_sql('eventos', conn, if_exists='replace', index=False)
        
        # Criar índices para performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_codigo ON eventos("CÓDIGO")')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_tipo ON eventos(TIPO)')
        
        # Ler e converter aba "Ordem de Eliminação"
        print("   📊 Processando: Ordem de Eliminação")
        df_ordem = pd.read_excel(arquivo_excel, sheet_name='Ordem de Eliminação')
        df_ordem.to_sql('ordem_eliminacao', conn, if_exists='replace', index=False)
        
        # Criar índice
        conn.execute('CREATE INDEX IF NOT EXISTS idx_desc_ordem ON ordem_eliminacao("DESCRIÇÃO EVENTOS")')
        
        # Confirmar transações
        conn.commit()
        
        # Estatísticas
        cursor = conn.cursor()
        total_eventos = cursor.execute('SELECT COUNT(*) FROM eventos').fetchone()[0]
        total_ordem = cursor.execute('SELECT COUNT(*) FROM ordem_eliminacao').fetchone()[0]
        
        print(f"\n✅ Conversão concluída com sucesso!")
        print(f"   📝 Eventos classificados: {total_eventos}")
        print(f"   📋 Ordem de eliminação: {total_ordem} itens")
        print(f"   💾 Banco criado em: {arquivo_db}")
        
    except Exception as e:
        print(f"❌ Erro na conversão: {e}")
        conn.rollback()
    finally:
        conn.close()

def carregar_mapeamento_eventos_db():
    """
    Função alternativa para carregar eventos do SQLite
    Substitui carregar_mapeamento_eventos() existente
    """
    try:
        pasta_base = Path(__file__).parent.parent
        arquivo_db = pasta_base / 'data' / 'parametros' / 'eventos.db'
        
        if not arquivo_db.exists():
            print("⚠️  Banco SQLite não encontrado. Execute converter_excel_para_sqlite() primeiro.")
            return {}
        
        conn = sqlite3.connect(arquivo_db)
        cursor = conn.cursor()
        
        # Query otimizada com índice
        query = 'SELECT "CÓDIGO", "DESCRIÇÃO EVENTOS", TIPO FROM eventos'
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        mapeamento = {}
        for codigo, descricao, tipo in resultados:
            codigo_str = str(codigo).strip()
            descricao_str = str(descricao).strip().upper()
            tipo_str = str(tipo).strip()
            mapeamento[(codigo_str, descricao_str)] = tipo_str
        
        conn.close()
        return mapeamento
        
    except Exception as e:
        print(f"⚠️  Erro ao carregar do SQLite: {e}")
        return {}

def carregar_ordem_eliminacao_db():
    """
    Função alternativa para carregar ordem de eliminação do SQLite
    Substitui carregar_ordem_eliminacao() existente
    """
    try:
        pasta_base = Path(__file__).parent.parent
        arquivo_db = pasta_base / 'data' / 'parametros' / 'eventos.db'
        
        if not arquivo_db.exists():
            return {}
        
        conn = sqlite3.connect(arquivo_db)
        cursor = conn.cursor()
        
        query = 'SELECT "DESCRIÇÃO EVENTOS", ORDEM FROM ordem_eliminacao'
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        prioridades = {}
        for descricao, ordem_texto in resultados:
            descricao_str = str(descricao).strip().upper()
            ordem_texto_str = str(ordem_texto).strip()
            
            # Extrair número da ordem
            if '1 -' in ordem_texto_str:
                ordem_num = 1
            elif '2 -' in ordem_texto_str:
                ordem_num = 2
            elif '3 -' in ordem_texto_str:
                ordem_num = 3
            elif '4 -' in ordem_texto_str:
                ordem_num = 4
            else:
                ordem_num = 99
            
            prioridades[descricao_str] = ordem_num
        
        conn.close()
        return prioridades
        
    except Exception as e:
        print(f"⚠️  Erro ao carregar ordem: {e}")
        return {}

if __name__ == '__main__':
    # Executar conversão
    converter_excel_para_sqlite()
    
    # Testar leitura
    print("\n🧪 Testando leitura do banco...")
    mapeamento = carregar_mapeamento_eventos_db()
    print(f"   ✅ {len(mapeamento)} eventos carregados")
    
    ordem = carregar_ordem_eliminacao_db()
    print(f"   ✅ {len(ordem)} itens de ordem carregados")
