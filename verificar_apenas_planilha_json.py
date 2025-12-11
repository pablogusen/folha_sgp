import pandas as pd
import json
from unidecode import unidecode
import re

def normalizar_nome(nome):
    """Normaliza nome removendo acentos e caracteres especiais"""
    if pd.isna(nome) or not nome:
        return ""
    nome = str(nome).upper().strip()
    nome = unidecode(nome)
    nome = re.sub(r'[^A-Z\s]', '', nome)
    nome = re.sub(r'\s+', ' ', nome)
    return nome.strip()

print("=" * 80)
print("🔍 VERIFICAÇÃO: Nomes da planilha consigno presentes na folha SGP")
print("=" * 80)

# 1. Ler os nomes da planilha APENAS PLANILHA
df_apenas_planilha = pd.read_excel('Comparacao_Criticos_vs_Relatorio.xlsx', sheet_name='Apenas Planilha Consigno')
print(f"\n📋 Total de nomes na aba 'Apenas Planilha Consigno': {len(df_apenas_planilha)}")

# Normalizar nomes da planilha
nomes_planilha = {}
for _, row in df_apenas_planilha.iterrows():
    nome_original = row['NOME DO SERVIDOR']
    nome_norm = normalizar_nome(nome_original)
    nomes_planilha[nome_norm] = {
        'Nome_Original': nome_original,
        'Matrícula': row['MATRÍCULA']
    }

print(f"✅ Nomes normalizados: {len(nomes_planilha)}")

# 2. Carregar dados do JSON da folha
with open('dados_folhas_backup.json', 'r', encoding='utf-8') as f:
    dados = json.load(f)

print(f"\n📄 Total de registros no JSON: {len(dados)}")

# Criar dicionário de nomes da folha
nomes_folha = {}
for registro in dados:
    nome_original = registro.get('Nome', '')
    if nome_original:
        nome_norm = normalizar_nome(nome_original)
        nomes_folha[nome_norm] = {
            'Nome_Original': nome_original,
            'Matrícula': registro.get('Matricula', ''),
            'Situação': registro.get('Situação', '')
        }

print(f"✅ Nomes da folha normalizados: {len(nomes_folha)}")

# 3. Verificar correspondências
encontrados = []
nao_encontrados = []

print("\n🔍 Verificando presença dos nomes na folha SGP...\n")

for nome_norm, dados_plan in nomes_planilha.items():
    if nome_norm in nomes_folha:
        dados_folha = nomes_folha[nome_norm]
        encontrados.append({
            'Nome': dados_plan['Nome_Original'],
            'Matrícula_Planilha': dados_plan['Matrícula'],
            'Matrícula_Folha': dados_folha['Matrícula'],
            'Situação': dados_folha['Situação']
        })
        print(f"✅ {dados_plan['Nome_Original']}")
        print(f"   Mat Planilha: {dados_plan['Matrícula']} | Mat Folha: {dados_folha['Matrícula']} | Situação: {dados_folha['Situação']}")
    else:
        nao_encontrados.append(dados_plan['Nome_Original'])

# 4. Relatório final
print("\n" + "=" * 80)
print("📊 RESULTADO DA VERIFICAÇÃO")
print("=" * 80)
print(f"\n✅ Nomes encontrados na folha SGP: {len(encontrados)}")
print(f"❌ Nomes NÃO encontrados na folha SGP: {len(nao_encontrados)}")

if nao_encontrados:
    print("\n❌ Nomes não encontrados:")
    for i, nome in enumerate(nao_encontrados, 1):
        print(f"   {i}. {nome}")

print("\n" + "=" * 80)
print("✅ ANÁLISE CONCLUÍDA!")
print("=" * 80)
