# Versionamento de Dados por Competência

Esta pasta organiza os dados históricos por competência (ano-mês).

## 📂 Estrutura:
```
competencias/
├── 2025-11/
│   ├── holerites/          # ← COLOQUE OS PDFs AQUI
│   ├── resultado.json      # Dados processados (gerado automaticamente)
│   └── relatorio.html      # Relatório HTML (gerado automaticamente)
├── 2025-12/
│   ├── holerites/
│   ├── resultado.json
│   └── relatorio.html
└── 2026-01/
    ├── holerites/
    ├── resultado.json
    └── relatorio.html
```

## 🚀 Como Usar:
1. **Criar pasta da competência**: `data/competencias/2025-12/holerites/`
2. **Colocar PDFs**: Copiar holerites para a pasta criada
3. **Executar**: `python src/gerar_relatorio.py`
4. **Sistema detecta automaticamente** a competência mais recente com PDFs

## 📊 Benefícios:
- ✅ **Histórico completo** de todas as competências processadas
- ✅ **Reprocessamento fácil** de meses anteriores
- ✅ **Comparações temporais** entre competências
- ✅ **Organização profissional** para auditoria
- ✅ **Backup automático** por competência

## 💡 Exemplo de Uso:
```powershell
# Para processar Dezembro/2025:
mkdir data\competencias\2025-12\holerites
# Copiar PDFs para data\competencias\2025-12\holerites\
python src\gerar_relatorio.py
# Sistema detecta 2025-12 automaticamente e processa
```
