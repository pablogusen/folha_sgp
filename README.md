# 📊 Sistema de Análise de Folha de Pagamento - ALMT# 📊 Sistema de Análise de Folha de Pagamento# 🚀 Sistema de Análise de Folhas de Pagamento



Sistema automatizado para análise de folhas de pagamento de servidores públicos da Assembleia Legislativa de Mato Grosso.



**Última atualização:** 03/11/2025  Sistema automatizado para processamento e análise de folhas de pagamento em PDF, gerando relatórios HTML interativos com análises detalhadas.Sistema automatizado para processar centenas de folhas de pagamento em PDF e gerar relatórios HTML interativos.

**Competência processada:** Outubro/2025



---

---## 📋 Funcionalidades

## 🚀 Scripts Principais



### 1. **gerar_relatorio.py** 

Processa PDFs e gera relatório HTML interativo completo.## 🚀 Início Rápido### ✨ Processamento em Lote



```bash- ✅ Processa **centenas de PDFs automaticamente**

python gerar_relatorio.py

```### Pré-requisitos- ✅ **Barra de progresso** visual em tempo real



**Saídas:**- Python 3.14+- ✅ **Estatísticas detalhadas** do processamento

- `Relatorio_Folha_Pagamento.html` - Relatório interativo

- `dados_folhas_backup.json` - Dados estruturados- PyPDF2 instalado- ✅ **Velocidade**: ~24 arquivos/segundo



**Recursos:**

- ✅ Extração automática de competência do PDF

- ✅ Análise de saúde financeira (margem consignável)### Instalação### 📊 Análise Completa

- ✅ Classificação automática de eventos

- ✅ Consolidação de holerites multi-página```bash- 💰 **Proventos** (entradas)

- ✅ Busca por beneficiário (nome ou CPF)

pip install PyPDF2- ⚖️ **Descontos Obrigatórios** (Previdência, IR)

---

```- 💳 **Descontos Extras** (Empréstimos, Consignados)

### 2. **gerar_planilha_cartoes.py**

Gera planilha Excel com beneficiários que possuem cartões de crédito consignados.- 🧮 **Cálculo do Líquido** com percentuais



```bash### Uso

python gerar_planilha_cartoes.py

```1. Coloque o arquivo PDF na pasta `Download_Folha/`### 📈 Dados Extraídos



**Saída:**2. Execute:- Nome completo

- `Relatorio_Cartoes_Consignados.xlsx`

```bash- CPF

**Colunas:**

- CPF | Matrícula | Nome | BIGCARD | EAGLE | NIO DIGITAL | TOTAL CARTÕESpython gerar_relatorio.py- Matrícula



**Resultado (Outubro/2025):**```- Data de nascimento e idade

- 68 beneficiários com cartões

- R$ 106.099,71 em descontos mensais3. Abra `Relatorio_Folha_Pagamento.html` no navegador- Situação (Pensionista/Aposentado)



---- Todos os proventos e descontos detalhados



### 3. **analise_suspensao_cartoes.py**---

Analisa impacto da suspensão de cartões em beneficiários críticos (>35% margem).

### 🎨 Relatório Interativo

```bash

python analise_suspensao_cartoes.py## 📁 Estrutura de Arquivos- **Busca por nome ou CPF**

```

- **Ordenação automática** por valor (maior → menor)

**Saída:**

- `Analise_Suspensao_Cartoes.xlsx` (4 abas)```- **Barras visuais de impacto**



**Análise dos 143 críticos:**Folha/- **Percentuais calculados** em cada etapa

- 🔴 34 permanecem críticos (outros consignados)

- ✅ 26 saem de crítico (normalizam com suspensão)├── gerar_relatorio.py                    # ⭐ Script principal- Design responsivo e profissional

- ⚠️ 83 críticos sem cartões (outras medidas)

├── dados_folhas_backup.json             # Backup dos dados processados

**Impacto:** R$ 50.803,94/mês podem ser liberados

├── Relatorio_Folha_Pagamento.html       # Relatório HTML gerado## 🔧 Como Usar

---

├── CONHECIMENTO_CONSOLIDADO.md          # 📚 Conhecimento técnico detalhado

## 📁 Estrutura de Arquivos

├── CONFIGURACOES.md                     # ⚙️ Configurações e ajustes### 1️⃣ Preparação

### **Scripts:**

```├── GUIA_RAPIDO_ATUALIZADO.md           # 📖 Guia de usoColoque todos os arquivos PDF de folhas de pagamento na pasta:

gerar_relatorio.py              # Principal - Relatório HTML

gerar_relatorio_backup.py       # Backup do principal├── README_PROJETO.md                    # 📋 Documentação do projeto```

gerar_planilha_cartoes.py       # Planilha de cartões

analise_suspensao_cartoes.py    # Análise de suspensão├── diagnostico_sicoob_completo.py       # 🔍 Ferramenta de validação SICOOBc:\Users\41870\Desktop\VSCODE\Folha\Download_Folha\

```

├── verificar_consolidacao_sicoob.py     # ✅ Validação consolidação SICOOB```

### **Documentação:**

```├── verificar_consolidacao_obrigatorios.py # ✅ Validação consolidação obrigatórios

README.md                       # Este arquivo

CONHECIMENTO_CONSOLIDADO.md    # Base de conhecimento técnico└── Download_Folha/                      # 📂 Pasta com PDFs para processar### 2️⃣ Executar o Script

ATUALIZACAO_03_NOV_2025.md     # Atualizações recentes

`````````powershell



### **Dados de Entrada:**cd "c:\Users\41870\Desktop\VSCODE\Folha"

```

Download_Folha/                 # PDFs da folha de pagamento---python gerar_relatorio.py

Margem Emprestimo...pdf         # Referência legal (35%)

``````



### **Saídas Geradas:**## 📊 Funcionalidades

```

Relatorio_Folha_Pagamento.html          # Relatório interativo### 3️⃣ Aguardar o Processamento

dados_folhas_backup.json                # Dados estruturados

Relatorio_Cartoes_Consignados.xlsx      # Planilha de cartões### ✅ Processamento AutomáticoO sistema irá:

Analise_Suspensao_Cartoes.xlsx          # Análise de impacto

```- Extração de dados de PDF de folha de pagamento- 📂 Buscar todos os PDFs



---- Consolidação de holerites multi-página- 📊 Exibir barra de progresso



## 📊 Resultados da Última Análise (Outubro/2025)- Classificação automática de eventos (proventos, descontos obrigatórios, descontos extras)- 📈 Mostrar estatísticas



### **Totais Gerais:**- Processamento de ~600 holerites em ~2 minutos- 💾 Gerar relatório HTML

- **Beneficiários:** 604

- **Proventos:** R$ 10.848.835,69

- **Descontos Obrigatórios:** R$ 2.603.081,43

- **Descontos Extras:** R$ 1.597.224,44### 📈 Análises Incluídas### 4️⃣ Visualizar Resultados

- **Líquido:** R$ 6.648.529,82

1. **Visão Geral** - Estatísticas principais da folhaAbra o arquivo gerado:

### **Saúde Financeira:**

- 🚨 **143 críticos** (>35% margem consignável)2. **Situação Funcional e Faixa Etária** - Análise demográfica```

- ✅ **461 normais** (≤35%)

3. **Saúde Financeira** - Taxa de comprometimento de rendaDownload_Folha/Relatorio_Folha_Pagamento.html

### **Cartões de Crédito:**

- 68 beneficiários4. **Impacto por Proventos** - Detalhamento por tipo de provento```

- EAGLE: R$ 70.804,71 (67%)

- BIGCARD: R$ 28.593,04 (27%)5. **Impacto por Desconto Obrigatório** - IRRF, ISSSPL, etc.

- NIO DIGITAL: R$ 6.701,96 (6%)

6. **Impacto por Desconto Facultativo** - Bancos, cooperativas, etc.## 📁 Arquivos Gerados

---

7. **Busca de Beneficiários** - Sistema de busca interativo

## 🎯 Recomendações de Ação

### `Relatorio_Folha_Pagamento.html`

### **Prioridade 1 - URGENTE:**

✅ Suspender cartões de **26 beneficiários**### 🎯 Consolidações InteligentesRelatório interativo principal com todos os beneficiários

- Lista na Aba 2 de `Analise_Suspensao_Cartoes.xlsx`

- Libera R$ 50.803,94/mês

- Normaliza margem para <35%

#### Descontos Facultativos### `dados_folhas_backup.json`

### **Prioridade 2 - Investigação:**

🔍 Analisar **34 beneficiários** que continuam críticos- **BANCO DO BRASIL** - Agrupa todas variações de consignado BBBackup completo dos dados em formato JSON

- Verificar outros consignados (Sicoob, Bradesco, BB)

- Avaliar renegociação- **SICOOB** - Inclui CREDLEGIS (388 lançamentos, R$ 279.609,09)



### **Prioridade 3 - Casos Especiais:**- **BANCOOB** - Separado do SICOOB (347 lançamentos, R$ 267.447,94)### `log_erros_processamento.txt`

⚠️ **83 beneficiários** sem cartões

- Análise individualizada necessária- **MT SAUDE** - Agrupa Padrão, Especial e Co-participaçãoLista de arquivos com problemas de processamento

- Orientação financeira

- **BRADESCO**, **EAGLE**, **SICREDI**, **BIGCARD**, etc.

---

## 📊 Exemplo de Saída

## 🛠️ Requisitos Técnicos

#### Descontos Obrigatórios

### **Bibliotecas Python:**

```bash- **IRRF IMPOSTO DE RENDA**```

pip install PyPDF2 openpyxl

```- **ISSSPL-PREVIDENCIA**================================================================================



### **Versão Python:**- **ABATIMENTO DO TETO**🚀 SISTEMA DE ANÁLISE DE FOLHAS DE PAGAMENTO

- Python 3.8 ou superior

- **PENSÃO ALIMENTÍCIA**================================================================================

---

- **DESCONTOS JUDICIAIS**

## 📖 Documentação Adicional

📂 Pasta: c:\Users\41870\Desktop\VSCODE\Folha\Download_Folha

- **CONHECIMENTO_CONSOLIDADO.md** - Detalhes técnicos, bugs resolvidos, estrutura do sistema

- **ATUALIZACAO_03_NOV_2025.md** - Novidades e funcionalidades recentes---📄 Arquivos PDF encontrados: 650



---



## ⚡ Comandos Rápidos## 🔧 Scripts Auxiliares================================================================================



```bash📊 PROCESSANDO FOLHAS DE PAGAMENTO...

# Processar folha completa

python gerar_relatorio.py### Validação SICOOB================================================================================



# Gerar planilha de cartões```bash

python gerar_planilha_cartoes.py

python verificar_consolidacao_sicoob.py[██████████████████████████████████████████████████] 650/650 (100.0%)

# Análise de suspensão

python analise_suspensao_cartoes.py```

```

Valida a consolidação de SICOOB + CREDLEGIS================================================================================

---

📈 ESTATÍSTICAS DO PROCESSAMENTO

## 🔒 Classificação de Eventos

### Validação Descontos Obrigatórios================================================================================

### **Proventos:**

- PROVENTOS, PENSAO INFORMADA, URV, VPNI, AUXILIO SAUDE, etc.```bash



### **Descontos Obrigatórios:**python verificar_consolidacao_obrigatorios.py✅ Processados com sucesso: 645/650

- Imposto de Renda, ISSSPL-Previdência, Abatimento Teto, Pensão Alimentícia

```⚠️  Sem dados extraídos: 3/650

### **Descontos Facultativos:**

- Cartões: BIGCARD, EAGLE, NIO DIGITALValida o agrupamento dos descontos obrigatórios❌ Com erros: 2/650

- Empréstimos: SICOOB, BANCOOB, Bradesco, Banco do Brasil

- Outros: MT SAUDE, SINDAL, ASAPAL



---### Diagnóstico Completo SICOOB💰 Total de Proventos: R$ 8,245,673.80



## ✅ Status do Sistema```bash⚖️  Total Descontos Obrigatórios: R$ 1,892,341.25



**Sistema validado e em produção**python diagnostico_sicoob_completo.py💳 Total Descontos Extras: R$ 2,103,562.15



- ✅ Extração de dados: 100% de precisão```💵 Total Líquido: R$ 4,249,770.40

- ✅ Classificação automática: Validada

- ✅ Consolidação multi-página: FuncionandoAnálise detalhada comparando JSON vs PDF para SICOOB

- ✅ Competência: Extraída do PDF

- ✅ Performance: ~5.5 holerites/segundo⏱️  Tempo de processamento: 27.08 segundos



------⚡ Velocidade: 24.0 arquivos/segundo



**Desenvolvido para:** Assembleia Legislativa de Mato Grosso  ```

**Departamento:** Recursos Humanos - Folha de Pagamento  

**Contato:** Gestor de RH especializado em folha de servidor público## 📈 Performance



---## 🛠️ Requisitos



*Última atualização: 03/11/2025*- **Velocidade:** ~5.5 holerites/segundo


- **Taxa de sucesso:** 100% (603/603 beneficiários)- Python 3.14+

- **Tempo médio:** ~110 segundos para processar folha completa- PyPDF2

- **Precisão:** Validada com contagens manuais- pandas

- openpyxl

---

## ⚡ Performance

## 🛠️ Configurações

- **Velocidade**: ~24 arquivos/segundo

Para ajustar consolidações ou classificações, edite `gerar_relatorio.py`:- **600 PDFs**: ~25 segundos

- **1000 PDFs**: ~42 segundos

### Adicionar nova variante de banco

```python## 🔍 Tratamento de Erros

mapa_consolidacao_facultativos = {

    'NOVA VARIANTE': 'NOME CONSOLIDADO',O sistema automaticamente:

    # ...- ✅ Identifica arquivos problemáticos

}- ✅ Continua o processamento mesmo com erros

```- ✅ Gera log detalhado de problemas

- ✅ Fornece estatísticas de sucesso

### Adicionar novo tipo de desconto obrigatório

```python## 💡 Dicas

palavras_desconto_obrigatorio = [

    'NOVO TERMO',### Para melhor performance:

    # ...1. Use PDFs no formato padrão Crystal Reports

]2. Mantenha os PDFs em uma única pasta

```3. Remova arquivos não relacionados (logos, etc)



Veja `CONFIGURACOES.md` para detalhes completos.### Em caso de problemas:

1. Verifique o arquivo `log_erros_processamento.txt`

---2. Confirme que os PDFs estão legíveis

3. Verifique se há espaço em disco suficiente

## 📚 Documentação Completa

## 📞 Suporte

- **CONHECIMENTO_CONSOLIDADO.md** - Problemas resolvidos, soluções e lições aprendidas

- **CONFIGURACOES.md** - Guia de configuração e customizaçãoEm caso de dúvidas ou problemas:

- **GUIA_RAPIDO_ATUALIZADO.md** - Tutorial passo a passo- Verifique o log de erros

- **README_PROJETO.md** - Documentação técnica detalhada- Confirme o formato dos PDFs

- Teste com um pequeno lote primeiro

---

---

## ✅ Valores Validados (Última Execução)

**Desenvolvido para processar centenas de folhas de pagamento de forma rápida e eficiente! 🚀**

### Totais Gerais
- 💰 **Total Proventos:** R$ 10.848.835,69
- ⚖️ **Descontos Obrigatórios:** R$ 2.603.081,43
- 💳 **Descontos Extras:** R$ 1.597.224,44
- 💵 **Total Líquido:** R$ 6.648.529,82

### Casos de Teste
- ✅ NIO DIGITAL: 9 ocorrências = R$ 6.701,96
- ✅ SICOOB (com CREDLEGIS): 388 lançamentos = R$ 279.609,09
- ✅ Beneficiários processados: 603

---

## 🐛 Problemas Conhecidos e Soluções

### Holerite dividido em múltiplas páginas
**✅ RESOLVIDO** - Sistema detecta e consolida automaticamente quando mesmo CPF aparece em páginas consecutivas.

### Eventos após "Totalizações" não eram capturados
**✅ RESOLVIDO** - Sistema agora processa eventos até o fim da página.

### Classificação incorreta de eventos
**✅ RESOLVIDO** - Listas de classificação completas e mapa de consolidação implementado.

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Consulte `CONHECIMENTO_CONSOLIDADO.md` para problemas conhecidos
2. Execute os scripts de diagnóstico
3. Verifique os logs no terminal

---

## 📝 Changelog

### v2.0 (23/10/2025)
- ✅ Corrigido bug de eventos após separadores visuais
- ✅ Implementada consolidação multi-página
- ✅ Corrigidos erros de classificação (CONSIG BB, DESCONTO JUDICIAL)
- ✅ Implementados mapas de consolidação para facultativos e obrigatórios
- ✅ Removida seção KPIs do relatório
- ✅ Removida coluna "Média Salarial Bruta"
- ✅ Sistema 100% validado e em produção

### v1.0 (Anterior)
- Versão inicial com extração básica

---

**Sistema pronto para produção - Taxa de precisão: 100%** ✅

*Última atualização: 23/10/2025*
