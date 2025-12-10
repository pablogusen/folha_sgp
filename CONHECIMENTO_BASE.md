# 📚 BASE DE CONHECIMENTO - SISTEMA FOLHA SGP

**Sistema:** Análise de Folha de Pagamento - ALMT  
**Criado:** 23/10/2025  
**Última atualização:** 10/12/2025

---

## 🎯 VISÃO GERAL DO SISTEMA

### Objetivo
Processar arquivos PDF de folha de pagamento da Assembleia Legislativa de Mato Grosso, extraindo dados estruturados e gerando relatórios HTML interativos com análises de saúde financeira dos beneficiários.

### Arquivos Principais
- **gerar_relatorio.py** (2460 linhas) - Script principal de processamento
- **Descricao_Comp_Rend.xlsx** - Planilha de parametrização com 137 eventos classificados
- **index.html** - Relatório HTML gerado automaticamente (sincronizado com GitHub)
- **dados_folhas_backup.json** - Backup estruturado dos dados extraídos

### Capacidade
- Processa ~650 holerites em ~105 segundos (6 holerites/segundo)
- Extração automática de competência do PDF
- Consolidação de holerites multi-página
- Análise de margem consignável e identificação de situações críticas

---

## 🔧 ARQUITETURA DO SISTEMA

### Pipeline de Processamento

```
PDF Input → Extração Dados → Classificação Eventos → Cálculo Margem → HTML Output
              (PyPDF2)       (Excel Lookup)        (35% limite)     (index.html)
```

### Fluxo de Classificação de Eventos

1. **Extração do PDF:** Código (Cód.) + Descrição do evento
2. **Normalização:** Remove espaços duplos, converte para uppercase
3. **Lookup na planilha:** Busca tupla `(codigo, descricao)` em `Descricao_Comp_Rend.xlsx`
4. **Classificação:** Atribui tipo (Provento, Desconto Obrigatório, Desconto Facultativo, Omitir)

### Cálculo de Margem Consignável

```python
# Base para cálculo do percentual
liquido_final = dados['liquido']  # Valor que o servidor efetivamente recebe

# Eventos que entram no cálculo (conforme planilha)
proventos = eventos classificados como "Provento"
descontos_obrigatorios = eventos "Desconto Compulsório obrigatório"
descontos_extras = eventos "Desconto Facultativo extra"

# Percentual de comprometimento
percentual_margem = (descontos_extras / liquido_final) * 100

# Situação crítica
if percentual_margem > 35%:
    status = "CRÍTICO"
```

---

## 📊 PARAMETRIZAÇÃO (Descricao_Comp_Rend.xlsx)

### Estrutura

**Sheet 1: "Composição de Rendimentos"**
- Código | Descrição Eventos | Tipo
- 137 eventos mapeados

**Sheet 2: "Regra de Aplicação"**
- Define 4 tipos de classificação:
  1. **Provento** - Entradas/receitas
  2. **Desconto Compulsório obrigatório** - Previdência, IR, pensão alimentícia
  3. **Desconto Facultativo extra** - Consignados, cartões, planos
  4. **Omitir do cálculo** - Eventos informativos (não entram na margem)

### Eventos Especiais Adicionados

Eventos com espaçamento irregular no PDF (7 eventos):
- LEGISLATIV A (código 34)
- INV ALIDEZ (código 50)
- DAYCOV AL (código 121)
- CONSTITUCIONA L (código 100)
- CEDLEGIS  (código 31) - 2 espaços
- FAMI  LIA (código 52) - 2 espaços
- CONT A  CAPITAL (código 122) - 2 espaços

---

## 🐛 BUGS CRÍTICOS RESOLVIDOS

### 1. Eventos após separadores visuais (OUT/2025)

**Problema:** Eventos após linhas "Proventos:", "Descontos:", "Totalizações" eram perdidos.

**Causa:** `break` na linha 147 parava processamento prematuramente.

**Solução:**
```python
# ANTES (ERRADO)
if linha.strip().startswith('Proventos:'):
    break  # Para tudo

# DEPOIS (CORRETO)
if linha.strip().startswith('Proventos:'):
    continue  # Pula linha mas continua
```

**Impacto:** Recuperou R$ 707,00 em descontos não capturados (NIO DIGITAL).

---

### 2. Espaços duplos em descrições (DEZ/2025)

**Problema:** "CONSIGNAÇÃO  B.BRASIL" (2 espaços) não dava match com "CONSIGNAÇÃO B.BRASIL".

**Solução:**
```python
descricao = re.sub(r'\s+', ' ', descricao)  # Normaliza espaços
```

**Impacto:** Reclassificou R$ 228.563,76 de proventos incorretos para descontos facultativos.

---

### 3. Cálculo incorreto de margem crítica (DEZ/2025)

**Problema:** Sistema exibia 273 servidores críticos quando correto era 181.

**Causa:** Usava `remuneracao_liquida` (proventos - descontos obrigatórios) como base, mas correto é `liquido_final` (valor que servidor recebe).

**Solução:**
```python
# ANTES (ERRADO) - linhas 1026-1065
remuneracao_liquida = total_prov - descontos_obrig
percentual = (descontos_extras / remuneracao_liquida) * 100

# DEPOIS (CORRETO)
liquido_final = dados.get('liquido', 0)
percentual = (descontos_extras / liquido_final) * 100
```

**Impacto:** Correção crítica no cálculo - agora usa valor líquido real como denominador.

---

## 💡 FUNCIONALIDADES IMPLEMENTADAS

### 1. Extração Automática de Competência (NOV/2025)

Busca campo "Competência: Mês/Ano" nas primeiras 20 linhas do PDF.

```python
for linha in linhas[:20]:
    if 'Competência:' in linha:
        comp_match = re.search(r'Competência:\s*([A-Za-zç]+/\d{4})', linha)
```

---

### 2. Consolidação Multi-página (OUT/2025)

Holerites longos ocupam 2 páginas consecutivas - sistema detecta e consolida automaticamente.

```python
if pagina_atual + 1 < num_paginas:
    dados_pagina2 = extrair_dados_pdf(pdf, pagina_atual + 1)
    if dados_pagina2['cpf'] == dados_pagina1['cpf']:
        # Mescla composição de rendimentos
```

---

### 3. Seção de Ajuste de Margem (DEZ/2025)

Para servidores >35%, exibe:
- **Situação Atual:** Base, percentual comprometido, valor a reduzir
- **Descontos Recomendados:** Tabela com hierarquia de eliminação
  - 🔴 Cartões (prioridade máxima)
  - 🟠 Consignações
  - 🟡 Associações
  - 🔵 Planos de saúde (medida extrema)
- **Situação Após Ajustes:** Novo percentual, ganho líquido mensal

**Algoritmo:** Elimina progressivamente descontos até atingir ≤35%, priorizando cartões.

---

### 4. Sistema de Parametrização Dinâmica (DEZ/2025)

**Antes:** Listas hardcoded no código (difícil manutenção).

**Depois:** Lookup em planilha Excel.

```python
# Carrega mapeamento do Excel
def carregar_mapeamento_eventos():
    df = pd.read_excel('Descricao_Comp_Rend.xlsx', sheet_name=0)
    mapeamento = {}
    for _, row in df.iterrows():
        codigo = str(row['Código']).strip()
        descricao = str(row['Descrição Eventos']).strip().upper()
        tipo = str(row['Tipo']).strip()
        mapeamento[(codigo, descricao)] = tipo
    return mapeamento

# Uso
tipo_evento = MAPEAMENTO_EVENTOS.get((codigo, descricao_upper), None)
```

**Vantagem:** Qualquer mudança na classificação = edita Excel, sem tocar no código.

---

## 📈 DADOS ESTATÍSTICOS (NOV/2025)

### Última Folha Processada
- **Competência:** Novembro/2025
- **Total de servidores:** 647
- **Proventos totais:** R$ 5.867.869,86
- **Descontos obrigatórios:** R$ 1.716.018,09
- **Descontos extras:** R$ 1.411.204,37
- **Líquido total:** R$ 5.145.024,80
- **Servidores em situação crítica (>35%):** 181 (28%)

### Distribuição de Cartões Consignados
- **Total de beneficiários com cartões:** 68
- **BIGCARD:** R$ 28.593,04
- **EAGLE:** R$ 70.804,71
- **NIO DIGITAL:** R$ 6.701,96
- **Total mensal:** R$ 106.099,71

---

## 🔄 INTEGRAÇÃO GITHUB

### Sincronização Automática

```powershell
# Script: sync_github.ps1
git add index.html
git commit -m "Atualização automática - $(Get-Date -Format 'dd/MM/yyyy HH:mm')"
git push origin main
```

**Arquivo sincronizado:** `index.html` (único arquivo de saída, substitui duplicatas anteriores)

---

## 🛠️ MANUTENÇÃO

### Como Adicionar Novo Evento

1. Abra `Descricao_Comp_Rend.xlsx`
2. Na sheet "Composição de Rendimentos", adicione linha:
   - **Código:** Extraído do PDF (coluna "Cód.")
   - **Descrição Eventos:** Texto EXATO do PDF (uppercase)
   - **Tipo:** Escolha entre os 4 tipos da sheet "Regra de Aplicação"
3. Salve e execute `gerar_relatorio.py`

### Como Alterar Limite de Margem Crítica

Arquivo: `gerar_relatorio.py` - linhas 1026-1065

```python
if liquido_final > 0:
    percentual = (descontos_extras / liquido_final) * 100
    if percentual > 35:  # ← Alterar aqui (atual: 35%)
        beneficiarios_criticos.append({...})
```

---

## 🧹 LIMPEZA DE CÓDIGO

### Arquivos Temporários Removidos
- ~~atualizar_descricao_comp_rend.py~~
- ~~validar_descricao_comp_rend.py~~
- ~~comparar_planilha_com_pdf.py~~
- ~~verificar_faltantes_txt.py~~
- ~~adicionar_eventos_faltantes.py~~
- ~~analisar_nova_regra_margem.py~~
- ~~comparar_situacao_critica.py~~

### Arquivos Duplicados Eliminados
- ~~Relatorio_Folha_Pagamento.html~~ → Agora gera apenas `index.html`

---

## 📝 REFERÊNCIAS TÉCNICAS

### Dependências Python
```python
import PyPDF2       # Extração de texto do PDF
import re           # Expressões regulares para parsing
import json         # Backup estruturado
import pandas       # Leitura do Excel de parametrização
import openpyxl     # Manipulação de planilhas
from datetime import datetime
```

### Estrutura de Dados (JSON)

```json
{
  "nome": "NOME COMPLETO",
  "cpf": "000.000.000-00",
  "matricula": "123456",
  "situacao": "Ativo/Pensionista",
  "competencia": "Novembro/2025",
  "proventos": 10000.00,
  "descontos_obrigatorios": 2000.00,
  "descontos_extras": 3500.00,
  "liquido": 4500.00,
  "percentual_margem": 77.78,
  "critico": true,
  "composicao": [
    {"codigo": "1", "descricao": "SUBSIDIO", "tipo": "Provento", "valor": 10000.00}
  ]
}
```

---

## ⚠️ PONTOS DE ATENÇÃO

1. **Encoding:** Forçar UTF-8 no Windows PowerShell (linhas 2185-2195)
2. **Espaços no PDF:** Sempre normalizar com `re.sub(r'\s+', ' ', texto)`
3. **Páginas consecutivas:** Verificar se mesmo CPF para consolidar
4. **Excel atualizado:** Sistema lê planilha a cada execução (mudanças aplicam imediatamente)
5. **Backup JSON:** Sempre validar com JSON antes de confiar no HTML

---

## 🎓 LIÇÕES APRENDIDAS

1. **Não use break em loops de extração:** Use `continue` para pular linhas indesejadas
2. **Base de cálculo importa:** Margem deve usar valor líquido final, não intermediário
3. **PDFs são inconsistentes:** Espaços duplos, quebras de página, formatação variável
4. **Parametrização externa:** Excel é melhor que hardcode para regras de negócio
5. **Validação cruzada:** JSON backup é fonte da verdade, HTML pode ter bugs de exibição

---

## 📅 ATUALIZAÇÕES - DEZEMBRO 2025

### 10/12/2025 - Otimização e Correções Críticas

#### 🎯 Melhorias Implementadas

**1. Remoção de Seções Redundantes**
- ❌ Removidas 4 seções de "Impacto Financeiro" (por provento/desconto)
- ❌ Removido Chart.js (210 linhas) - gráfico de pizza não utilizado
- ✅ Redução: ~33 KB no HTML final (1.110 KB → 1.077 KB)

**2. Nova Seção: Composição de Rendimentos**
- ✅ 137 eventos classificados em 4 tabelas visuais
- 🟢 Proventos (rendimentos)
- 🟡 Descontos Obrigatórios (INSS, IR, pensão)
- 🔴 Descontos Facultativos (consignados, empréstimos)
- ⚪ Omitir do Cálculo (informativos)

**3. Transparência nos Relatórios Individuais**
- ✅ Nova seção "OUTROS EVENTOS INFORMATIVOS"
- ℹ️ Exibe eventos marcados como "Omitir do cálculo"
- 📝 Explicações claras sobre por que não afetam margem
- Exemplos: Auxílio Alimentação, Auxílio Saúde, adiantamentos

**4. Correção da Tabela de Beneficiários Críticos**
- ❌ ANTES: Mostrava `liquido_final` duplicado em colunas erradas
- ✅ AGORA: 9 colunas detalhadas e corretas:
  - Proventos Brutos (verde)
  - Descontos Obrigatórios (laranja)
  - **Margem Consignável** = Proventos - Desc. Obrig (azul) ⬅️ CORRIGIDO
  - Descontos Extras comprometidos (vermelho)
  - **% sobre Margem** (percentual correto) ⬅️ CORRIGIDO
  - Líquido Final recebido
  - Indicador de Rescisão

#### 🔍 Validações Realizadas

**Caso de Teste: CLAUDIANO ALMEIDA**
```
Proventos:                    R$ 1,518.00
Descontos Obrigatórios:       R$   113.85
Margem Consignável:           R$ 1,404.15  ⬅️ Base correta
Descontos Extras:             R$   775.47
% sobre Margem:               55.2% CRÍTICO ✅
Eventos Informativos:         R$ 2,000.00 (não contam)
Líquido Final:                R$ 2,628.68 ✅
```

#### 📊 Dados Estruturais Adicionados

```python
# Novo campo no dicionário de dados
'eventos_informativos': []  # Eventos que não afetam margem

# Novo campo em beneficiarios_criticos
{
    'total_proventos': 0,
    'total_descontos_obrigatorios': 0,
    'margem_consignavel': 0,  # Calculada corretamente
    'percentual_sobre_margem': 0  # % correto
}
```

#### 🎯 Princípios Validados

1. **Classificação no Excel é CORRETA** - decisão institucional do usuário
2. **Eventos "Omitir do cálculo"** não afetam margem consignável (por design)
3. **Líquido do PDF** = Proventos - Todos Descontos + Informativos ✅
4. **Margem Consignável** = Proventos - Descontos Obrigatórios ✅
5. **% Crítico** = Descontos Extras ÷ Margem Consignável × 100 ✅

#### 📝 Arquivos Modificados

- `gerar_relatorio.py` (2,381 linhas após otimização)
  - Linha 54: Adicionado `eventos_informativos: []`
  - Linha 181: Roteamento de eventos "Omitir"
  - Linhas 1059-1073: Cálculo correto de `margem_consignavel` e `percentual_sobre_margem`
  - Linhas 1165-1220: Seção Composição de Rendimentos
  - Linhas 1570-1620: Seção Eventos Informativos (individual)
  - Linhas 1105-1145: Tabela críticos corrigida (9 colunas)

---

**FIM DA BASE DE CONHECIMENTO**

*Este documento consolida todo o aprendizado do projeto desde outubro/2025.*
