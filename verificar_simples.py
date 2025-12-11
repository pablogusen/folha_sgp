import pandas as pd
import json
from unidecode import unidecode
import re

def normalizar_nome(nome):
    nome = str(nome).upper().strip()
    nome = unidecode(nome)
    nome = re.sub(r'[^A-Z\s]', '', nome)
    return re.sub(r'\s+', ' ', nome).strip()

# Ler planilha
df = pd.read_excel('Comparacao_Criticos_vs_Relatorio.xlsx', sheet_name='Apenas Planilha Consigno')
nomes_planilha = {normalizar_nome(row['NOME DO SERVIDOR']): row['NOME DO SERVIDOR'] for _, row in df.iterrows()}

# Ler JSON
with open('dados_folhas_backup.json', 'r', encoding='utf-8') as f:
    dados = json.load(f)

nomes_folha = {normalizar_nome(d['Nome']): d['Nome'] for d in dados if d.get('Nome')}

# Encontrar correspondências
encontrados = [nomes_planilha[n] for n in nomes_planilha if n in nomes_folha]

print(f'\n📋 Total na "Apenas Planilha Consigno": {len(nomes_planilha)}')
print(f'✅ Encontrados na folha SGP: {len(encontrados)}\n')

if encontrados:
    print("Nomes encontrados:")
    for i, nome in enumerate(encontrados, 1):
        print(f'{i}. {nome}')
else:
    print("Nenhum nome encontrado na folha.")
