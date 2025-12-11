import pandas as pd
import pdfplumber
import os
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

def extrair_texto_pdf(caminho_pdf):
    """Extrai texto de um arquivo PDF"""
    texto = ""
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for page in pdf.pages:
                texto += page.extract_text() + "\n"
    except Exception as e:
        print(f"Erro ao ler {os.path.basename(caminho_pdf)}: {e}")
    return texto

# 1. Ler os nomes da planilha APENAS PLANILHA
print("=" * 80)
print("🔍 VERIFICAÇÃO: Nomes da planilha consigno presentes no PDF da folha")
print("=" * 80)

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

# 2. Ler PDFs da pasta Download_Folha
pasta_pdf = 'Download_Folha'
if not os.path.exists(pasta_pdf):
    print(f"\n❌ Pasta '{pasta_pdf}' não encontrada!")
    exit()

arquivos_pdf = [f for f in os.listdir(pasta_pdf) if f.endswith('.pdf')]
print(f"\n📄 PDFs encontrados: {len(arquivos_pdf)}")

# 3. Procurar cada nome nos PDFs
encontrados = []
nao_encontrados = []

print("\n🔍 Verificando presença dos nomes nos PDFs...\n")

for nome_norm, dados in nomes_planilha.items():
    encontrado_em = []
    
    for pdf_file in arquivos_pdf:
        caminho_completo = os.path.join(pasta_pdf, pdf_file)
        texto_pdf = extrair_texto_pdf(caminho_completo)
        texto_pdf_norm = normalizar_nome(texto_pdf)
        
        if nome_norm in texto_pdf_norm:
            encontrado_em.append(pdf_file)
    
    if encontrado_em:
        encontrados.append({
            'Nome': dados['Nome_Original'],
            'Matrícula': dados['Matrícula'],
            'PDFs': encontrado_em
        })
        print(f"✅ {dados['Nome_Original']}")
        print(f"   Mat: {dados['Matrícula']} | Encontrado em {len(encontrado_em)} PDF(s)")
        for pdf in encontrado_em:
            print(f"      - {pdf}")
    else:
        nao_encontrados.append(dados['Nome_Original'])

# 4. Relatório final
print("\n" + "=" * 80)
print("📊 RESULTADO DA VERIFICAÇÃO")
print("=" * 80)
print(f"\n✅ Nomes encontrados no PDF: {len(encontrados)}")
print(f"❌ Nomes NÃO encontrados no PDF: {len(nao_encontrados)}")

if nao_encontrados:
    print("\n❌ Nomes não encontrados:")
    for i, nome in enumerate(nao_encontrados, 1):
        print(f"   {i}. {nome}")

print("\n" + "=" * 80)
