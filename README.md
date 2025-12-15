# 🚀 Sistema de Análise de Margem Consignável - ALMT

Sistema completo para análise de folhas de pagamento conforme **Resolução Administrativa nº 14/2025**, desenvolvido para a Assembleia Legislativa de Mato Grosso.

## 📋 Estrutura do Projeto

```
Folha_SGP/
├── src/                      # Código-fonte
│   ├── gerar_relatorio.py           # Script principal
│   ├── comparar_criticos_novo.py    # Análises auxiliares
│   └── converter_excel_sqlite.py    # Utilitário de conversão
├── data/
│   ├── parametros/           # Configurações e parâmetros
│   │   ├── Descricao_Comp_Rend.xlsx # Classificação eventos
│   │   └── eventos.db               # Banco SQLite (opcional)
│   ├── backup/               # Backups JSON gerais
│   └── competencias/         # 📅 Histórico por competência
│       ├── 2025-11/
│       │   ├── holerites/          # PDFs desta competência
│       │   ├── resultado.json      # Dados processados
│       │   └── relatorio.html      # Relatório específico
│       └── 2025-12/
│           ├── holerites/
│           ├── resultado.json
│           └── relatorio.html
├── output/                   # Relatórios gerais
│   └── index.html
├── docs/                     # Documentação
│   ├── CONHECIMENTO_BASE.md
│   └── README.md
├── tests/                    # Testes automatizados
│   └── test_classificacao.py
├── logs/                     # Logs de execução
├── .github/
│   └── workflows/
│       └── sync-pages.yml    # Automação GitHub
├── requirements.txt          # Dependências Python
└── .gitignore

```

## 🎯 Funcionalidades

### ✅ Implementadas
1. **Processamento de PDFs**: Extração automática de dados dos holerites
2. **Classificação Automática**: 137 eventos classificados (Compulsórios/Facultativos)
3. **Cálculo Legal**: Margem consignável conforme Resolução 14/2025 (35% da RLM)
4. **4 Seções de Alerta**:
   - 🔴 Críticos (>100% do limite)
   - 🔵 Rescisão contratual
   - 🟠 Servidores cedidos
   - 🟡 Casos atípicos
5. **Relatório HTML Interativo**: Com dashboard e gráficos (Chart.js)
6. **Sistema de Logs**: Rastreamento completo de execução
7. **Testes Automatizados**: Validação de cálculos e classificações
8. **GitHub Actions**: Sincronização automática
9. **Banco SQLite**: Alternativa otimizada ao Excel
10. **Versionamento de Dados**: Histórico por competência

### 📊 Dashboard Interativo
- Gráficos de distribuição por status
- Totalizações financeiras
- Comparativos de beneficiários por faixa de risco
- Filtros e exportações

## 🚀 Como Usar

### 1. Preparar Ambiente
```powershell
# Instalar dependências
pip install -r requirements.txt

# (Opcional) Converter Excel para SQLite
python src/converter_excel_sqlite.py
```

### 2. Processar Folha
```powershell
# Colocar PDFs na pasta data/competencias/AAAA-MM/holerites/
# Exemplo: data/competencias/2025-12/holerites/*.pdf

# Executar processamento (detecta automaticamente a competência mais recente)
cd src
python gerar_relatorio.py
```

**O sistema irá:**
- Detectar automaticamente competências disponíveis
- Processar a mais recente por padrão
- Salvar resultado.json e relatorio.html na pasta da competência
- Atualizar index.html na raiz (para GitHub Pages)
- Manter backup geral em data/backup/

### 3. Visualizar Relatório
- Abrir `output/index.html` no navegador
- Ou acessar: https://pablogusen.github.io/folha_sgp/

### 4. Testes
```powershell
# Executar testes
python -m pytest tests/

# Ou com unittest
python tests/test_classificacao.py
```

## 📚 Base Legal

**Resolução Administrativa nº 14/2025 - Art. 5º**
- Limite consignável: **35% da RLM**
- RLM = Proventos - Descontos Compulsórios
- Percentual = (Descontos Facultativos / Limite Ideal) × 100

## 🎨 Classificação de Status

| Status | Faixa | Cor | Ação |
|--------|-------|-----|------|
| SAUDÁVEL | < 57% | 🟢 Verde | Nenhuma |
| ATENÇÃO | 57-86% | 🟡 Amarelo | Monitorar |
| RISCO | 86-100% | 🟠 Laranja | Orientar |
| CRÍTICO | > 100% | 🔴 Vermelho | **Ação Imediata** |

## 📦 Dependências

- Python 3.8+
- PyPDF2 3.0.1 (extração PDF)
- pandas 2.1.4 (manipulação dados)
- openpyxl 3.1.2 (leitura Excel)
- unidecode 1.3.7 (normalização texto)

## 🔧 Extensões VS Code Recomendadas

- Pylance (IntelliSense)
- Python Debugger (Debug visual)
- GitLens (Histórico Git)
- Excel Viewer (Visualizar XLSX)

## 📈 Performance

- **647 holerites** processados em ~110 segundos
- **137 eventos** classificados automaticamente
- **4 categorias** de alertas especiais

## 🌐 GitHub Pages

Relatório disponível online: https://pablogusen.github.io/folha_sgp/

GitHub Actions sincroniza automaticamente ao fazer push de `index.html`.

## 📝 Logs

Logs detalhados salvos em `logs/relatorio_YYYYMMDD_HHMMSS.log`:
- Quantidade de PDFs processados
- Eventos não classificados
- Tempo de execução
- Erros e avisos

## 🧪 Casos Especiais Detectados

### Cedidos
- Servidor tem REPRESENTACAO
- **E** não tem SUBSÍDIO código 1

### Rescisão
- Código inicia com '13'
- **OU** descrição contém 'RESCIS'

### Atípicos
- Margem ≤ 0
- **OU** Proventos = 0 com descontos
- **OU** |RLM - Líquido| > R$ 0,10

## 👨‍💻 Autor

**Pablo Gusen** - Assembleia Legislativa de Mato Grosso
- GitHub: [@pablogusen](https://github.com/pablogusen)
- Repositório: [folha_sgp](https://github.com/pablogusen/folha_sgp)

## 📄 Licença

Uso interno - ALMT

---

**Última atualização**: 15/12/2025
**Versão**: 2.0 (Refatoração completa com 10 melhorias implementadas)
