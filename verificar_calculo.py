import json

# Carregar dados
with open('dados_folhas_backup.json', encoding='utf-8') as f:
    dados = json.load(f)

# Pegar CLAUDIANO ALMEIDA
beneficiario = [x for x in dados if x['nome'] == 'CLAUDIANO ALMEIDA'][0]

print("="*60)
print(f"ANÁLISE: {beneficiario['nome']}")
print("="*60)

print("\n=== PROVENTOS ===")
total_prov = 0
for p in beneficiario['proventos']:
    print(f"{p['codigo']:>3} - {p['descricao']:<40} R$ {p['valor']:>10.2f}")
    total_prov += p['valor']
print(f"{'':>46} TOTAL: R$ {total_prov:>10.2f}")

print("\n=== DESCONTOS OBRIGATÓRIOS ===")
total_obrig = 0
for d in beneficiario.get('descontos_obrigatorios', []):
    print(f"{d['codigo']:>3} - {d['descricao']:<40} R$ {d['valor']:>10.2f}")
    total_obrig += d['valor']
print(f"{'':>46} TOTAL: R$ {total_obrig:>10.2f}")

print("\n=== DESCONTOS EXTRAS ===")
total_extras = 0
for d in beneficiario.get('descontos_extras', []):
    print(f"{d['codigo']:>3} - {d['descricao']:<40} R$ {d['valor']:>10.2f}")
    total_extras += d['valor']
print(f"{'':>46} TOTAL: R$ {total_extras:>10.2f}")

print("\n=== EVENTOS INFORMATIVOS (Omitir do cálculo) ===")
total_info = 0
for e in beneficiario.get('eventos_informativos', []):
    print(f"{e['codigo']:>3} - {e['descricao']:<40} R$ {e['valor']:>10.2f}")
    total_info += e['valor']
print(f"{'':>46} TOTAL: R$ {total_info:>10.2f}")

print("\n" + "="*60)
print("CÁLCULOS")
print("="*60)
print(f"Total Proventos (sistema):       R$ {beneficiario['total_proventos']:>10.2f}")
print(f"Total Desc. Obrig (sistema):     R$ {beneficiario.get('total_descontos_obrigatorios', 0):>10.2f}")
print(f"Total Desc. Extras (sistema):    R$ {beneficiario.get('total_descontos_extras', 0):>10.2f}")
print(f"Líquido PDF (extraído):          R$ {beneficiario['liquido']:>10.2f}")

calc_manual = total_prov - total_obrig - total_extras
print(f"\nCálculo Manual:")
print(f"  {total_prov:.2f} - {total_obrig:.2f} - {total_extras:.2f} = R$ {calc_manual:>10.2f}")

diferenca = beneficiario['liquido'] - calc_manual
print(f"\nDIFERENÇA: R$ {diferenca:>10.2f}")

if abs(diferenca) > 1:
    print("\n⚠️  DIVERGÊNCIA DETECTADA!")
    print("Possíveis causas:")
    print("  - Eventos classificados como 'Omitir do cálculo'")
    print("  - Eventos não mapeados na planilha Excel")
    print("  - Erro na extração do PDF")
else:
    print("\n✅ Cálculo está correto!")
