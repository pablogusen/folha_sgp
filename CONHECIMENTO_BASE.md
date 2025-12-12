# 📚 BASE DE CONHECIMENTO - SISTEMA FOLHA SGP

**Sistema:** Análise de Folha de Pagamento - ALMT  
**Criado:** 23/10/2025  
**Última atualização:** 12/12/2025

---

## 🎯 VISÃO GERAL DO SISTEMA

### Objetivo
Processar arquivos PDF de folha de pagamento da Assembleia Legislativa de Mato Grosso, extraindo dados estruturados e gerando relatórios HTML interativos com análises de margem consignável e saúde financeira dos beneficiários conforme **Resolução Administrativa nº 14/2025, Art. 5º**.

### Arquivos Principais
- **gerar_relatorio.py** (2634 linhas) - Script principal de processamento
- **Descricao_Comp_Rend.xlsx** - Planilha de parametrização com 137 eventos classificados
- **index.html** - Relatório HTML gerado automaticamente (sincronizado com GitHub Pages)
- **dados_folhas_backup.json** - Backup estruturado dos dados extraídos

### Capacidade
- Processa ~650 holerites em ~110 segundos (6 holerites/segundo)
- Extração automática de competência do PDF
- Consolidação de holerites multi-página
- Análise de margem consignável com limite legal de 35%
- Identificação de 4 categorias de situação financeira

---

## ⚖️ BASE LEGAL

### Resolução Administrativa nº 14/2025, Art. 5º
> "As consignações facultativas não poderão exceder ao valor da margem consignável, equivalente a **35% (trinta e cinco por cento)** da remuneração líquida mensal do consignado, sendo limitadas a até 5 (cinco) empréstimos por servidor e até 120 (cento e vinte) parcelas por operação."

**Implicações:**
- Limite legal: 35% da RLM (Remuneração Líquida Mensal)
- RLM = Proventos - Descontos Compulsórios (Obrigatórios)
- Limite Ideal = RLM × 0,35
- Percentual = (Descontos Facultativos / Limite Ideal) × 100
- Crítico: Percentual > 100% (descontos > 35% da RLM)

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

### Cálculo de Margem Consignável (ATUALIZADO - Dez/2025)

```python
# FÓRMULA OFICIAL (conforme Resolução Administrativa nº 14/2025)
# Base: RLM (Remuneração Líquida Mensal)

# 1. Calcular RLM (Base Margem)
RLM = total_proventos - total_descontos_obrigatorios

# 2. Calcular Limite Ideal (35% da RLM)
limite_ideal = RLM * 0.35

# 3. Calcular Percentual sobre o Limite
percentual = (descontos_facultativos / limite_ideal) * 100

# 4. Classificar Saúde Financeira
if percentual < 57:      # < 20% da RLM
    status = "SAUDÁVEL"
elif percentual < 86:    # 20-30% da RLM
    status = "ATENÇÃO"
elif percentual <= 100:  # 30-35% da RLM
    status = "RISCO"
else:                    # > 35% da RLM (ILEGAL)
    status = "CRÍTICO"
```

**Mudança conceitual importante:**
- ❌ Antes: Percentual sobre líquido final
- ✅ Agora: Percentual sobre limite ideal de 35%
- 🎯 Foco: Capacidade de endividamento consignado disponível

---

## 📊 PARAMETRIZAÇÃO (Descricao_Comp_Rend.xlsx)

### Estrutura

**Sheet 1: "Composição de Rendimentos"**
- Código | Descrição Eventos | Tipo
- 137 eventos mapeados
- **IMPORTANTE:** Lookup por tupla `(codigo, descricao)` - mesmo evento pode ter classificação diferente por código

**Sheet 2: "Ordem de Eliminação"**
- Define prioridade para eliminação de descontos facultativos
- 4 níveis: Prioridade Máxima → Nível 2 → Nível 3 → Nível 4
- Usado na seção "AJUSTE DE MARGEM CONSIGNÁVEL"

### Tipos de Classificação

1. **Provento** - Entradas/receitas que compõem a RLM
2. **Desconto Compulsório (obrigatório)** - Reduzem a RLM (INSS, IR, pensão)
3. **Desconto Facultativo (extra)** - Consomem o limite de 35% (consignados, cartões)
4. **Omitir do cálculo** - Informativos, não impactam margem (auxílios, adiantamentos, rescisões)

### Regras Especiais de Classificação

**SUBSÍDIO pode ter 2 tratamentos:**
- Código **1**: Provento (entra no cálculo)
- Código **22**: Omitir do cálculo (não entra)

**CONSOLIDAÇÃO REMOVIDA (Dez/2025):**
- ❌ Não consolidar bancos (ex: "CONSIG BCO BRASIL" → "BANCO DO BRASIL")
- ✅ Registrar lançamento por lançamento (cada código é único)
- 🎯 Motivo: Cada lançamento pode ter código diferente

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

## 🆕 ATUALIZAÇÕES CONSOLIDADAS (DEZEMBRO/2025)

### 📊 Relatório HTML - 4 Seções de Alerta

**1. BENEFICIÁRIOS EM SITUAÇÃO CRÍTICA** (Vermelho 🚨)
- > 100% do limite legal (> 35% da RLM)
- 6 colunas: Nome, Situação, Base Margem, Limite (35%), Descontos Facultativos, % do Limite
- Link clicável para relatório individual

**2. BENEFICIÁRIOS COM RESCISÃO DE TRABALHO** (Azul 📋)
- Detecta evento "13" + "RESCIS" em proventos ou informativos
- 2 colunas: Nome, Desconto Facultativo (Sim/Não)
- Não estarão na próxima competência

**3. SERVIDORES CEDIDOS** (Laranja 👤)
- Regra: TEM "REPRESENTACAO CONF LC 04/90 - ART. 59" E NÃO TEM "SUBSÍDIO" código 1
- Remuneração paga pelo órgão de origem
- Margem pode estar baseada em eventos omitidos

**4. CASOS ATÍPICOS** (Amarelo ⚡)
- **Critério 1:** Margem ≤ 0 (não rescisão, não cedido)
- **Critério 2:** Proventos = 0 mas com descontos
- **Critério 3:** RLM ≠ Líquido sem descontos facultativos (diferença > R$ 0,10)
- 4 colunas: Nome, Situação, Margem (RLM), Motivo

### 📈 Classificação Unificada de Saúde Financeira

**Thresholds padronizados** (baseados no limite ideal de 35%):

| Categoria | Threshold | Equivalência | Contador Geral | Barra Individual |
|-----------|-----------|--------------|----------------|------------------|
| SAUDÁVEL | < 57% | < 20% da RLM | ✅ | ✅ SAUDÁVEL |
| ATENÇÃO | 57-86% | 20-30% da RLM | ✅ | ✅ ATENÇÃO |
| RISCO | 86-100% | 30-35% da RLM | ✅ | ✅ RISCO |
| CRÍTICO | > 100% | > 35% da RLM | ✅ | ✅ CRÍTICO |

**Consistência:** Mesma categoria no relatório geral e individual.

### 🔧 Nomenclatura Padronizada

| Anterior | Atual |
|----------|-------|
| Descontos Obrigatórios | Descontos Compulsórios (Obrigatórios) |
| Descontos Extras | Descontos Facultativos |
| CÁLCULO DO VALOR LÍQUIDO | EXTRATO DA MARGEM |
| Margem Consignável | RLM (Base Margem) |
| % sobre Líquido Final | % do Limite |

### ⚙️ Mudanças Técnicas

**Remoção de Consolidação:**
- ❌ Não consolidar bancos (CONSIG BCO BRASIL → BANCO DO BRASIL)
- ❌ Não consolidar MT SAUDE (manter PADRAO, ESPECIAL, CO-PARTICIPACAO separados)
- ✅ Cada lançamento mantém seu código único

**Detecção de Rescisão Flexibilizada:**
```python
# Antes: busca exata '13º SALÁRIO FIXO RESCISÃO'
# Agora: busca '13' E 'RESCIS' (flexível)
tem_rescisao = any('13' in desc and 'RESCIS' in desc 
                   for desc in proventos + eventos_informativos)
```

**Sistema de Notificação:**
- Alerta amarelo no topo quando eventos não mapeados aparecem
- Arquivo `EVENTOS_NAO_CLASSIFICADOS.txt` (se houver)
- 🔔 **LEMBRETE:** Ao processar nova competência, verificar se há novos eventos!

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
- Script agora gera diretamente `index.html` (sem necessidade de cópia)

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

### 11/12/2025 - Sistema de Detecção de Eventos Não Classificados

#### 🔍 Nova Funcionalidade: Notificação Automática

O sistema agora detecta **automaticamente** eventos novos que aparecem nos holerites mas não estão classificados na planilha Excel.

**Problema Resolvido:**
- Holerites de competências futuras (ex: Dezembro/2025) podem trazer novos eventos
- Sem detecção, esses eventos seriam classificados incorretamente como "Provento" (fallback)
- Usuário não seria notificado sobre a necessidade de classificação

**Solução Implementada:**

**1. Detecção Durante Processamento**
```python
# Global set para rastrear eventos não mapeados
EVENTOS_NAO_MAPEADOS = set()

# Durante extração de cada evento:
tipo_evento = MAPEAMENTO_EVENTOS.get((codigo, descricao_upper), None)

if tipo_evento is None:
    EVENTOS_NAO_MAPEADOS.add((codigo, descricao_upper, descricao_original))
    # Fallback: classificar como Provento temporariamente
```

**2. Arquivo de Notificação** (`EVENTOS_NAO_CLASSIFICADOS.txt`)

Gerado automaticamente quando eventos não mapeados são detectados:
```
================================================================================
⚠️  EVENTOS NÃO CLASSIFICADOS - AÇÃO NECESSÁRIA
================================================================================
Data/Hora: 11/12/2025 14:30:15
Total de eventos não classificados: 3

📋 INSTRUÇÕES:
1. Abra a planilha: Descricao_Comp_Rend.xlsx
2. Acesse a sheet: 'Composição de Rendimentos'
3. Adicione cada evento com sua classificação
4. Se for 'Desconto Facultativo', adicione na 'Ordem de Eliminação' (1-4)
5. Salve e execute o script novamente

📊 EVENTOS NÃO CLASSIFICADOS:

Código: 999
Descrição: BONIFICAÇÃO ESPECIAL NATAL
Descrição Normalizada: BONIFICAÇÃO ESPECIAL NATAL
--------------------------------------------------------------------------------
```

**3. Notificação no Console**

```
================================================================================
⚠️  ATENÇÃO: EVENTOS NÃO CLASSIFICADOS DETECTADOS!
================================================================================

🔍 Foram encontrados 3 eventos novos que não estão na planilha Excel.
📋 Esses eventos foram classificados como 'Provento' por padrão (fallback).
📝 Você precisa classificá-los manualmente na planilha!

📄 Lista completa salva em: EVENTOS_NAO_CLASSIFICADOS.txt

================================================================================
🚨 EVENTOS NÃO CLASSIFICADOS:
================================================================================

1. Código 999 - BONIFICAÇÃO ESPECIAL NATAL
2. Código 1000 - AUXÍLIO TRANSPORTE ESPECIAL
3. Código 1001 - GRATIFICAÇÃO FINAL DE ANO

================================================================================
⚠️  AÇÃO NECESSÁRIA:
================================================================================
1. Abra: Descricao_Comp_Rend.xlsx
2. Classifique cada evento acima
3. Se for 'Desconto Facultativo', defina a ordem de eliminação (1-4)
4. Salve e execute o script novamente
```

**4. Alerta Visual no HTML**

Quando há eventos não classificados, um banner de alerta é exibido no topo do relatório HTML:

```html
⚠️ EVENTOS NÃO CLASSIFICADOS DETECTADOS

🔍 Foram encontrados 3 eventos novos que não estão na planilha Excel!

Esses eventos foram classificados como "Provento" por padrão (fallback), 
mas isso pode estar incorreto. Verifique o arquivo EVENTOS_NAO_CLASSIFICADOS.txt

Exemplos:
• Código 999: BONIFICAÇÃO ESPECIAL NATAL
• Código 1000: AUXÍLIO TRANSPORTE ESPECIAL
• Código 1001: GRATIFICAÇÃO FINAL DE ANO

📋 AÇÃO NECESSÁRIA:
1. Abra: Descricao_Comp_Rend.xlsx
2. Classifique os eventos na sheet "Composição de Rendimentos"
3. Se for "Desconto Facultativo", defina ordem (1-4) na sheet "Ordem de Eliminação"
4. Salve e execute o script novamente
```

**Fluxo de Trabalho:**

```
1. Novo PDF de Dezembro/2025 é processado
   ↓
2. Sistema detecta evento não mapeado: "BONIFICAÇÃO ESPECIAL NATAL"
   ↓
3. Evento é adicionado a EVENTOS_NAO_MAPEADOS (set global)
   ↓
4. Temporariamente classificado como "Provento" (fallback)
   ↓
5. Ao final do processamento:
   - Gera arquivo EVENTOS_NAO_CLASSIFICADOS.txt
   - Exibe alerta no console (com lista)
   - Adiciona banner no HTML
   ↓
6. Usuário abre Descricao_Comp_Rend.xlsx
   ↓
7. Adiciona linha com:
   - CÓDIGO: 999
   - DESCRIÇÃO EVENTOS: BONIFICAÇÃO ESPECIAL NATAL
   - TIPO: Provento (ou outro)
   ↓
8. Se for "Desconto Facultativo", adiciona também em "Ordem de Eliminação":
   - Prioridade 1, 2, 3 ou 4
   ↓
9. Salva planilha e executa script novamente
   ↓
10. Sistema agora classifica corretamente ✅
```

**Vantagens:**

1. ✅ **Detecção Proativa** - Não passa despercebido
2. ✅ **Arquivo Detalhado** - Lista completa para referência
3. ✅ **Alerta Visual** - Impossível ignorar (console + HTML)
4. ✅ **Instruções Claras** - Passo a passo do que fazer
5. ✅ **Fallback Seguro** - Classificação temporária evita crash
6. ✅ **Sem Duplicatas** - Usa `set()` para eventos únicos

**Código Implementado:**

```python
# gerar_relatorio.py - Linha 81
EVENTOS_NAO_MAPEADOS = set()  # Global tracking

# Durante extração (linha 204-206)
if tipo_evento is None:
    EVENTOS_NAO_MAPEADOS.add((codigo, descricao_upper, descricao))

# Após processamento (linhas 2267-2334)
if EVENTOS_NAO_MAPEADOS:
    # Gerar arquivo TXT
    # Exibir no console
    # Adicionar alerta no HTML
```

**Exemplo Real:**

Se dezembro/2025 trouxer "13º COMPLEMENTAR" (código 4999):
- ✅ Detectado automaticamente
- ✅ Arquivo criado com instruções
- ✅ Console alerta o usuário
- ✅ Banner laranja no HTML
- ✅ Usuário adiciona na planilha
- ✅ Próxima execução: classificado corretamente

---

### 11/12/2025 - Ordem de Eliminação Parametrizada

#### 🎯 Nova Funcionalidade: Ordem de Eliminação via Excel

**Planilha "Ordem de Eliminação" adicionada ao Descricao_Comp_Rend.xlsx**

A ordem de eliminação de descontos para ajuste de margem consignável agora é **totalmente parametrizável via Excel**, eliminando hardcode no sistema.

**Estrutura da Planilha:**
| Coluna | Descrição |
|--------|-----------|
| CÓDIGO | Código do evento (mesmo da folha) |
| DESCRIÇÃO EVENTOS | Nome exato do evento (UPPERCASE) |
| TIPO | Desconto Facultativo (extra) |
| ORDEM | Prioridade de eliminação (1 a 4) |

**Hierarquia de Eliminação:**

🔴 **Prioridade 1 - Prioridade Máxima** (Eliminação obrigatória de TODOS)
- 7 eventos: Cartões de crédito/benefício
- Estratégia: Eliminar **100% dos cartões** automaticamente
- Exemplos: BIG CARD, EAGLE, NIO, BMG, MTXCARD, SUDACRED

🟠 **Prioridade 2 - Facultativo Nível 2** (Otimização inteligente)
- 56 eventos: Consignações bancárias e CREDLEGIS
- Estratégia: **Melhor combinação** para atingir ≤35%
- Algoritmo: Testa até 32.768 combinações para encontrar o ponto ideal mais próximo de 35%
- Exemplos: Consignações B.BRASIL, BANCOOB, BRADESCO, CEF, DAYCOVAL, SICOOB, SICREDI, SUDACRED

🟡 **Prioridade 3 - Facultativo Nível 3** (Secundário)
- 5 eventos: Associações e sindicatos
- Estratégia: **Melhor combinação** dentro do grupo
- Exemplos: APRALE, ASLEM, ASSALMAT, SINDAL, UNALE

🔵 **Prioridade 4 - Analisar Suspensão** (Medida extrema)
- 12 eventos: Planos de saúde e previdência complementar
- Estratégia: **Melhor combinação** apenas se necessário
- Exemplos: GEAP SAÚDE, MT SAUDE, UNIMED, PREVCOM

**Lógica de Processamento:**

```javascript
// 1. Carregar ordem de eliminação do Excel
const ordemEliminacao = {...}; // Carregado via Python

// 2. Classificar cada desconto do servidor
obterOrdem(descricao) → {ordem: 1-4, nome_ordem: "texto"}

// 3. Agrupar descontos por ordem
descontosPorOrdem = {
  1: [cartões],
  2: [consignações],
  3: [associações],
  4: [saúde/previdência]
}

// 4. Processar em sequência: 1 → 2 → 3 → 4
Para cada ordem:
  - Se ordem == 1: eliminar TODOS
  - Se ordem >= 2: encontrarMelhorCombinacao()
  - Se percentual <= 35%: PARAR
```

**Algoritmo de Melhor Combinação:**

```javascript
encontrarMelhorCombinacao(descontos, descontosAtuais) {
  // Testa todas combinações possíveis (até 32.768)
  // Objetivo: percentual <= 35% mais próximo de 35%
  
  Para cada combinação:
    novoPercentual = (descontosRestantes / margem) * 100
    
    Se novoPercentual <= 35:
      distancia = 35 - novoPercentual
      Se distancia < melhorDistancia:
        melhorCombinacao = combinação atual
  
  // Se nenhuma atinge <=35%, elimina TODOS do grupo
  return melhorCombinacao ou todosDoGrupo
}
```

**Vantagens:**

1. ✅ **Flexibilidade Total** - Basta editar Excel para mudar prioridades
2. ✅ **Sem Código** - Não precisa mexer em gerar_relatorio.py
3. ✅ **Otimização Matemática** - Elimina apenas o necessário (exceto prioridade 1)
4. ✅ **Transparência** - Ordem clara e documentada na planilha
5. ✅ **Institucional** - Decisões técnicas centralizadas no Excel

**Exemplo Prático:**

Servidor com 50% de margem comprometida:
1. **Elimina** todos os 2 cartões (R$ 500) → 42%
2. **Testa** 1.024 combinações de 10 consignações
3. **Seleciona** 3 consignações específicas (R$ 800) → 34.8% ✅
4. **Não toca** em associações (já atingiu meta)
5. **Preserva** plano de saúde

**Código Implementado:**

```python
# gerar_relatorio.py - Linhas 34-77
def carregar_ordem_eliminacao():
    df_ordem = pd.read_excel('Descricao_Comp_Rend.xlsx', 
                              sheet_name='Ordem de Eliminação')
    
    prioridades = {}
    for _, row in df_ordem.iterrows():
        descricao = str(row['DESCRIÇÃO EVENTOS']).upper()
        ordem_texto = str(row['ORDEM'])
        
        # Extrair número 1, 2, 3 ou 4
        if '1 -' in ordem_texto: ordem_num = 1
        elif '2 -' in ordem_texto: ordem_num = 2
        # ... etc
        
        prioridades[descricao] = {
            'ordem': ordem_num,
            'nome_ordem': ordem_texto
        }
    
    return prioridades

# Carregar na inicialização
ORDEM_ELIMINACAO = carregar_ordem_eliminacao()
```

---

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
