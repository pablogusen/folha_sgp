import json
from PyPDF2 import PdfReader

# Carregar dados
with open('dados_folhas_backup.json', 'r', encoding='utf-8') as f:
    dados = json.load(f)

print('Exemplos de matrícula extraída do JSON:')
print('='*80)
for i, d in enumerate(dados[:5]):
    print(f"{i+1}. {d['nome'][:40]:40} | Matrícula: {d['matricula']}")

print('\n\nExtraindo diretamente do PDF para comparar:')
print('='*80)

pdf = PdfReader('Download_Folha/FolhaAtivos_CompNov25.pdf')
for i in [0, 10, 20, 30, 40]:
    text = pdf.pages[i].extract_text()
    lines = text.split('\n')
    
    nome = ''
    matricula = ''
    banco_agencia_conta = ''
    
    for line in lines[:10]:
        if 'Matrícula:' in line and 'CPF:' in line:
            nome = line.split(' ')[0:3]
            nome = ' '.join(nome)
        
        if 'Bc./Ag./Cta.:' in line:
            parts = line.split('Bc./Ag./Cta.:')
            if len(parts) > 1 and parts[1].strip():
                banco_agencia_conta = parts[1].strip()
        
        if 'Nasc' in line and '/' in line:
            import re
            mat = re.search(r'(\d+/\d+-\d+/\d+-\d+)', line)
            if mat:
                matricula = mat.group(1)
    
    print(f"\nPágina {i}:")
    print(f"  Nome: {nome}")
    print(f"  Matrícula extraída: {matricula}")
    print(f"  Banco/Ag/Conta: {banco_agencia_conta if banco_agencia_conta else '(vazio)'}")
