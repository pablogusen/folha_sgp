# 📊 Sistema de Análise de Folha de Pagamento - ALMT

Sistema automatizado para processamento de folhas de pagamento em PDF da Assembleia Legislativa de Mato Grosso, gerando relatórios HTML interativos com análise detalhada de saúde financeira dos beneficiários.

**🌐 Versão Online:** https://pablogusen.github.io/folha_sgp/  
**Última atualização:** 11/12/2025

---

## 🚀 Início Rápido

### Pré-requisitos
```bash
pip install PyPDF2 pandas openpyxl
```

### Uso

1. Coloque o arquivo PDF na pasta `Download_Folha/`
2. Execute: `python gerar_relatorio.py`
3. Abra `index.html` no navegador

---

## 📋 Funcionalidades

### ✨ Processamento
- ✅ ~650 holerites em ~105 segundos (6/seg)
- ✅ Barra de progresso em tempo real
- ✅ Consolidação automática multi-página
- ✅ Extração automática de competência

### 📊 Análise Financeira
- 💰 Proventos totais
- ⚖️ Descontos obrigatórios (INSS, IR, pensão)
- 💳 Descontos extras (consignados, cartões)
- 🧮 Cálculo de margem consignável
- 🚨 Identificação de situação crítica (>35%)

### 🔍 Relatório HTML Interativo
- 🔎 Busca por nome ou CPF
- 📱 Design responsivo
- 📈 **Composição de Rendimentos** (137 eventos classificados)
- 👤 Relatórios individuais detalhados
- ℹ️ **Eventos Informativos** (omitidos do cálculo de margem)
- 🚨 Tabela de beneficiários críticos com 9 colunas detalhadas

---

## ⚙️ Parametrização

**Descricao_Comp_Rend.xlsx** - 137 eventos classificados em 4 tipos:
**Descricao_Comp_Rend.xlsx** - 137 eventos classificados em 4 tipos:

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| 🟢 Provento | Rendimentos | SUBSIDIO, GRATIFICAÇÃO |
| 🟡 Desconto Compulsório | INSS, IR, pensão | Base para margem |
| 🔴 Desconto Facultativo | Consignados | Comprometem margem |
| ⚪ Omitir do Cálculo | Informativos | Auxílios, adiantamentos |

**Vantagem:** Edite o Excel, não o código!

---

## 📈 Estatísticas (NOV/2025)

- **Servidores:** 647
- **Proventos:** R$ 5.867.869,86
- **Descontos Obrig:** R$ 1.716.018,09
- **Descontos Extras:** R$ 1.411.204,37
- **Líquido Total:** R$ 5.145.024,80
- **Situação Crítica:** 181 (28%)
- **Processamento:** 105s

---

## 📁 Estrutura

```
Folha_SGP/
├── gerar_relatorio.py          # Script principal (2,402 linhas)
├── Descricao_Comp_Rend.xlsx    # Parametrização (137 eventos + ordem eliminação)
├── index.html                  # Relatório gerado (1,363 KB)
├── dados_folhas_backup.json    # Backup estruturado
├── CONHECIMENTO_BASE.md        # Documentação técnica
├── README.md                   # Este arquivo
├── sync_github.ps1             # Script de sync
└── Download_Folha/             # PDFs de entrada
```

---

## 🔄 Deploy GitHub Pages

```bash
python gerar_relatorio.py  # Gera index.html
# Ao final, confirme sincronização com 's'
# Ou manualmente:
git add .
git commit -m "Atualização folha"
git push origin main
```

Acesse: https://pablogusen.github.io/folha_sgp/

---

## 🎯 Destaques da Versão Atual

### ✅ Recentemente Implementado

**11/12/2025 - Sistema de Detecção Automática**
1. **Notificação de Eventos Não Classificados**
   - Detecta automaticamente eventos novos nos holerites
   - Gera arquivo `EVENTOS_NAO_CLASSIFICADOS.txt` com lista
   - Alerta no console e banner visual no HTML
   - Instruções claras para classificação

2. **Proteção contra Erros de Classificação**
   - Fallback temporário: eventos não mapeados → "Provento"
   - Evita crashes no sistema
   - Garante que relatório seja gerado mesmo com eventos novos

**11/12/2025 - Ordem de Eliminação Parametrizada**
1. **Nova Planilha Excel**: "Ordem de Eliminação"
   - 80 eventos com prioridades 1-4
   - Hierarquia institucional definida via Excel
   
2. **Algoritmo Inteligente de Otimização**
   - Prioridade 1: Elimina TODOS os cartões (obrigatório)
   - Prioridades 2-4: Melhor combinação matemática
   - Testa até 32.768 combinações para maximizar líquido
   - Busca percentual mais próximo de 35%

3. **Sem Hardcode**
   - Ordem totalmente parametrizável
   - Mudanças via Excel (sem mexer no código)
   - Flexibilidade para ajustes institucionais

**10/12/2025 - Transparência e Correções**

1. **Seção Composição de Rendimentos**
   - 4 tabelas visuais com todos os 137 eventos
   - Códigos coloridos por tipo

2. **Eventos Informativos**
   - Nova seção mostrando eventos "Omitir do cálculo"
   - Explicações sobre por que não afetam margem
   - Exemplo: Auxílio Alimentação, Auxílio Saúde

3. **Tabela de Críticos Corrigida**
   - 9 colunas detalhadas
   - **Margem Consignável** = Proventos - Desc. Obrig ✅
   - **% sobre Margem** calculado corretamente ✅

4. **Otimização**
   - Removidas seções redundantes (~33 KB)
   - Código mais limpo e eficiente

---

## 📚 Documentação

- **CONHECIMENTO_BASE.md** - Arquitetura, lições aprendidas, histórico
- **README.md** - Este guia rápido

---

## ⚠️ Pontos Importantes

1. **Margem Consignável** = Proventos - Descontos Obrigatórios
2. **Percentual Crítico** = Descontos Extras ÷ Margem Consignável × 100
3. **Eventos "Omitir"** não afetam margem (decisão institucional)
4. **Líquido PDF** considera TODOS os eventos (incluindo informativos)
5. Excel atualizado = Sistema atualizado (sem mexer no código)

---

**Sistema desenvolvido para ALMT - Assembleia Legislativa de Mato Grosso**
