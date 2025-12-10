# 📊 Sistema de Análise de Folha de Pagamento - ALMT

Sistema automatizado para processamento de folhas de pagamento em PDF da Assembleia Legislativa de Mato Grosso, gerando relatórios HTML interativos com análise detalhada de saúde financeira dos beneficiários.

**Última atualização:** 09/12/2025

---

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.14+
- PyPDF2, pandas, openpyxl

```bash
pip install PyPDF2 pandas openpyxl
```

### Uso

1. Coloque o arquivo PDF na pasta `Download_Folha/`
2. Execute:
```bash
python gerar_relatorio.py
```
3. Abra `index.html` no navegador

---

## 📋 Funcionalidades

### ✨ Processamento Automático
- ✅ Extrai dados de centenas de holerites automaticamente (~6 holerites/segundo)
- ✅ Barra de progresso em tempo real
- ✅ Consolidação automática de holerites multi-página
- ✅ Extração automática da competência do PDF

### 📊 Análise Financeira
- 💰 **Proventos totais** - Todas as receitas do servidor
- ⚖️ **Descontos obrigatórios** - Previdência, IR, pensão alimentícia
- 💳 **Descontos extras** - Consignados, cartões, planos de saúde
- 🧮 **Cálculo de margem consignável** - Percentual comprometido
- 🚨 **Identificação de situação crítica** - Servidores com >35% de comprometimento

### 🔍 Recursos do Relatório HTML
- Busca por nome ou CPF
- Visualização detalhada de cada beneficiário
- Tabelas responsivas com todos os eventos
- Seção especial para servidores em situação crítica
- **Ajuste de margem:** Recomendações personalizadas de eliminação de descontos

---

## 🎯 Dados Extraídos

Para cada beneficiário:
- Nome completo, CPF, matrícula
- Data de nascimento e idade
- Situação (Ativo/Aposentado/Pensionista)
- Competência da folha
- **Composição completa de rendimentos:**
  - Código e descrição de cada evento
  - Classificação automática (Provento/Desconto)
  - Valores detalhados
- **Análise de margem:**
  - Base de cálculo
  - Percentual comprometido
  - Status (Normal/Crítico)
  - Recomendações de ajuste (se >35%)

---

## ⚙️ Parametrização

### Descricao_Comp_Rend.xlsx

**Planilha de classificação de eventos** - 137 eventos mapeados

**Sheet 1: "Composição de Rendimentos"**
| Código | Descrição Eventos | Tipo |
|--------|------------------|------|
| 1 | SUBSIDIO | Provento |
| 100 | PREVIDENCIA MUNICIPAL | Desconto Compulsório obrigatório |
| 121 | CONSIGNAÇÃO DAYCOVAL | Desconto Facultativo extra |

**Sheet 2: "Regra de Aplicação"**
- **Provento** - Entradas/receitas
- **Desconto Compulsório obrigatório** - Entram no cálculo da base
- **Desconto Facultativo extra** - Consignações que comprometem a margem
- **Omitir do cálculo** - Eventos informativos

**Vantagem:** Qualquer mudança na classificação = edita Excel, sem mexer no código!

---

## 📈 Saídas Geradas

### index.html
Relatório HTML interativo completo com:
- Estatísticas gerais da folha
- Lista de todos os beneficiários
- Busca e filtros
- Detalhamento individual
- Seção de servidores críticos
- Recomendações de ajuste

### dados_folhas_backup.json
Backup estruturado de todos os dados extraídos em formato JSON (útil para validações e integrações).

---

## 🔄 Integração GitHub

```bash
# Sincronização manual
git add index.html CONHECIMENTO_BASE.md
git commit -m "Atualização folha de pagamento"
git push origin main
```

Ou use o script PowerShell:
```powershell
.\sync_github.ps1
```

---

## 📊 Estatísticas Recentes (NOV/2025)

- **Servidores processados:** 647
- **Proventos totais:** R$ 5.867.869,86
- **Descontos obrigatórios:** R$ 1.716.018,09
- **Descontos extras:** R$ 1.411.204,37
- **Líquido total:** R$ 5.145.024,80
- **Servidores em situação crítica (>35%):** 181 (28%)
- **Tempo de processamento:** ~105 segundos

---

## 🛠️ Manutenção

### Como adicionar novo evento

1. Abra `Descricao_Comp_Rend.xlsx`
2. Na sheet "Composição de Rendimentos", adicione:
   - **Código:** Extraído da coluna "Cód." do PDF
   - **Descrição Eventos:** Texto EXATO do PDF (UPPERCASE)
   - **Tipo:** Escolha entre os 4 tipos da sheet "Regra de Aplicação"
3. Salve e execute `gerar_relatorio.py`

### Como alterar limite crítico

Arquivo `gerar_relatorio.py` - procure por:
```python
if percentual > 35:  # ← Alterar aqui (padrão: 35%)
```

---

## 📚 Documentação Completa

Consulte `CONHECIMENTO_BASE.md` para:
- Arquitetura detalhada do sistema
- Histórico de bugs resolvidos
- Funcionalidades implementadas
- Lições aprendidas
- Referências técnicas

---

## 📁 Estrutura do Projeto

```
Folha_SGP/
├── gerar_relatorio.py          # Script principal (2460 linhas)
├── Descricao_Comp_Rend.xlsx    # Planilha de parametrização (137 eventos)
├── index.html                  # Relatório HTML gerado
├── dados_folhas_backup.json    # Backup estruturado
├── CONHECIMENTO_BASE.md        # Documentação técnica completa
├── README.md                   # Este arquivo
├── sync_github.ps1             # Script de sincronização
└── Download_Folha/             # PDFs de entrada
    └── FolhaAtivos_CompNov25.pdf
```

---

## 🎯 Análise de Ajuste de Margem

Para servidores com margem >35%, o sistema exibe automaticamente:

### Hierarquia de Eliminação
1. 🔴 **Cartões** (Prioridade Máxima) - BIGCARD, EAGLE, NIO, MTX
2. 🟠 **Consignações** - Bancos diversos
3. 🟡 **Associações** - CREDLEGIS, sindicatos
4. 🔵 **Planos de Saúde** (Medida Extrema)

### Informações Exibidas
- Valor exato que precisa ser reduzido
- Tabela de descontos recomendados para eliminação
- Novo percentual após cada eliminação
- Ganho líquido mensal após ajustes
- Status: "✅ Meta atingida" ou "Resta eliminar R$ X"

---

## ⚠️ Pontos Importantes

1. **Encoding UTF-8:** Sistema força UTF-8 para compatibilidade Windows PowerShell
2. **Espaços no PDF:** Descrições são normalizadas automaticamente
3. **Multi-página:** Holerites longos são consolidados automaticamente
4. **Atualização em tempo real:** Sistema lê Excel a cada execução
5. **Backup JSON:** Use para validações (fonte da verdade)

---

## 📞 Suporte

Para dúvidas técnicas ou bugs, consulte:
- **Documentação técnica:** `CONHECIMENTO_BASE.md`
- **Repositório GitHub:** pablogusen/folha_sgp

---

**Sistema desenvolvido para otimizar a análise de folha de pagamento e auxiliar na gestão financeira dos beneficiários da ALMT.**
