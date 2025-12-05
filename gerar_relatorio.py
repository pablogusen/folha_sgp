import PyPDF2
import re
import json
import os
from datetime import datetime
from pathlib import Path

def formatar_moeda_br(valor):
    """Formata valor monetário no padrão brasileiro: 1.450,15"""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def extrair_dados_ativos(linhas, caminho_pdf, numero_pagina=None):
    """
    Extrai dados de servidores ATIVOS (novo layout)
    """
    dados = {
        'nome': '',
        'cpf': '',
        'matricula': '',
        'data_nascimento': '',
        'idade': '',
        'situacao': 'Ativo',  # Sempre ativo para este layout
        'competencia': '',
        'cargo': '',
        'data_admissao': '',
        'proventos': [],
        'descontos_obrigatorios': [],
        'descontos_extras': [],
        'total_proventos': 0,
        'total_descontos_obrigatorios': 0,
        'total_descontos_extras': 0,
        'total_descontos': 0,
        'liquido': 0,
        'arquivo_origem': os.path.basename(caminho_pdf) + (f" (pág. {numero_pagina+1})" if numero_pagina is not None else ""),
        'erro_processamento': None
    }
    
    try:
        # 1. Extrair competência (linha 1)
        for linha in linhas[:5]:
            if 'Competência:' in linha or 'Competencia:' in linha:
                comp_match = re.search(r'Competência:\s*([A-Za-zç]+/\d{4})', linha, re.IGNORECASE)
                if comp_match:
                    dados['competencia'] = comp_match.group(1)
                    break
        
        # 2. Extrair nome e CPF (linha 2 - formato: "NOME CPF Matrícula: CPF:")
        for linha in linhas[:10]:
            if 'Matrícula:' in linha and 'CPF:' in linha:
                cpf_match = re.search(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', linha)
                if cpf_match:
                    dados['cpf'] = cpf_match.group(1)
                
                # Nome está antes do CPF
                nome_match = re.search(r'^([A-ZÁÉÍÓÚÀÂÊÔÃÕÇ\s\.]+?)\s+\d{3}\.\d{3}\.\d{3}-\d{2}', linha)
                if nome_match:
                    dados['nome'] = nome_match.group(1).strip()
                break
        
        # 3. Extrair cargo e data de admissão (linha 3)
        for linha in linhas[:10]:
            if 'Cargo:' in linha and 'Admissão:' in linha:
                cargo_match = re.search(r'Cargo:\s*(.+?)\s+(\d{2}/\d{2}/\d{4})', linha)
                if cargo_match:
                    dados['cargo'] = cargo_match.group(1).strip()
                    dados['data_admissao'] = cargo_match.group(2)
                break
        
        # 4. Extrair matrícula da linha Loc.Trabalho (último número da linha)
        for linha in linhas[:15]:
            if 'Loc.Trabalho' in linha:
                # A matrícula é o último número da linha (ex: "Loc.Trabalho : 006791001 - GAB DEP GILBERTO CATTANI 0 - 47767")
                matricula_match = re.search(r'-\s+(\d+)\s*$', linha)
                if matricula_match:
                    dados['matricula'] = matricula_match.group(1)
                break
        
        # 5. Extrair data de nascimento
        for linha in linhas[:15]:
            if 'Nasc' in linha:
                # Data de nascimento
                nasc_match = re.search(r'Nasc\s+(\d{2}/\d{2}/\d{4})', linha)
                if nasc_match:
                    dados['data_nascimento'] = nasc_match.group(1)
                    # Calcular idade
                    try:
                        data_nasc = datetime.strptime(dados['data_nascimento'], '%d/%m/%Y')
                        hoje = datetime.now()
                        idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
                        dados['idade'] = f"{idade} anos"
                    except:
                        dados['idade'] = ''
                break
        
        # 6. Extrair eventos (proventos e descontos)
        # Formato: " VALOR1  VALOR2  REF DESCRIÇÃO CÓDIGO"
        # Exemplo: " 1.465,40  1.465,40  30,00 SUBSIDIO 1"
        
        inicio_tabela = False
        for linha in linhas:
            if 'Composição de Rendimentos Mensal' in linha:
                inicio_tabela = True
                continue
            
            if 'Cód. Descrição Eventos' in linha:
                continue
            
            # Pular linhas de totalização mas continuar processando
            if linha.strip().startswith('Proventos:') or linha.strip().startswith('Descontos:') or 'Totalizações' in linha:
                continue
            
            if inicio_tabela and linha.strip():
                # Padrão: valor1 valor2 ref descrição código
                evento_match = re.search(r'^\s*([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+(.+?)\s+(\d+)\s*$', linha)
                
                if evento_match:
                    try:
                        valor1 = float(evento_match.group(1).replace('.', '').replace(',', '.'))
                        valor2 = float(evento_match.group(2).replace('.', '').replace(',', '.'))
                        referencia = float(evento_match.group(3).replace('.', '').replace(',', '.'))
                        descricao = evento_match.group(4).strip()
                        # Normalizar descrição: remover espaços duplos
                        descricao = re.sub(r'\s+', ' ', descricao)
                        codigo = evento_match.group(5)
                        
                        # O valor do evento é sempre o primeiro valor
                        valor_evento = valor1
                        base_calculo = valor2
                        
                        # Classificar o evento
                        descricao_upper = descricao.upper()
                        
                        # PROVENTOS (lista oficial completa)
                        palavras_provento = [
                            '1/3 DE FERIAS', '1/3 FÉRIAS FIXO - RESCISÃO', '1/3 FERIAS PROPORCIONAIS RESCISÃO',
                            '13º SALÁRIO FIXO RESCISÃO', 'ABONO DE PERMANENCIA', 'ADIANTAMENTO 13º SALARIO',
                            'AUXILIO ALIMENTACAO', 'AUXÍLIO ASSESSORIA DE SEGURANÇA LEGISLATIVA',
                            'AUXILIO DOENÇA', 'AUXÍLIO SAÚDE', 'BENEFICIO RES. 812/2007',
                            'CHEFIA RES. N. 4.456/2016', 'COMPLEMENTO SALARIAL', 'DIF. VENC/PROVENTO',
                            'DIFERENÇA DE REMUNERAÇÃO', 'DIFERENCA DE SALARIO POR SUBSTITUICAO',
                            'FERIAS INDENIZADAS', 'FÉRIAS PROPORCIONAL (INDENIZAÇÃO)',
                            'FUNCAO DE CONFIANCA ART 59/7.860', 'GRATIFICAÇÃO POR SUBSTITUIÇÃO',
                            'HORA EXTRA 50 %', 'INDENIZACAO TRABALHISTA', 'INSALUBRIDADE 20%',
                            'LICENÇA MATERNIDADE', 'LICENCA PREMIO', 'REPRESENTACAO CONF LC 04/90 - ART. 59',
                            'SALARIO DE SUBSTITUIÇÃO', 'SALARIO FAMILIA', 'SALDO AFASTAMENTO',
                            'SUBSIDIO', 'VERBAS INDENIZATORIAS', 'VPNI'
                        ]
                        
                        # DESCONTOS OBRIGATÓRIOS (lista oficial completa)
                        palavras_desconto_obrigatorio = [
                            'ABATIMENTO REMUNERAÇÃO - CEDENTE', 'BENEFÍCIO DE PECÚLIO/PENSÃO POR INVALIDEZ',
                            'BENEFÍCIO DE PECÚLIO/PENSÃO POR MORTE', 'CUIABAPREV', 'DESC ADTO FERIAS',
                            'DETERMINAÇÃO JUDICIAL', 'DETERMINACAO JUDICIAL (PERCENTUAL) - 3',
                            'DEVOLUCAO POR PAGAMENTO INDEVIDO', 'FALTAS', 'I R R F',
                            'IMPOSTO DE RENDA PESSOA FISICA', 'INSS - PREVIDENCIA',
                            'INSS 13º SALÁRIO - PREVIDÊNCIA', 'IRRF 13.º SALÁRIO', 'IRRF FÉRIAS',
                            'ISSSPL - PLANO FINANCEIRO', 'ISSSPL - PLANO PREVIDENCIARIO', 'MTPREV',
                            'PENSÃO ALIMENTÍCIA', 'PENSAO ALIMENTICIA SOBRE FERIAS',
                            'PREVCOM CONTRIBUICAO ATIVO ANTERIOR', 'PREVCOM PARTICIPANTE ATIVO MIGRADO',
                            'REDUTOR PEC 41/2003 - TETO CONSTITUCIONA'
                        ]
                        
                        # DESCONTOS FACULTATIVOS (lista oficial completa)
                        palavras_desconto_facultativo = [
                            'APRALE', 'ASLEM', 'BIG CARD - CARTÃO BENEFÍCIO', 'BMG CARTÃO CREDITO',
                            'CONSIGNAÇÃO B.BRASIL', 'CONSIGNAÇÃO BANCOOB', 'CONSIGNAÇÃO BRADESCO',
                            'CONSIGNACAO CEF', 'CONSIGNAÇÃO DAYCOVAL', 'CONSIGNAÇÃO EAGLE',
                            'CONSIGNAÇÃO EAGLE - RESCISÃO', 'CONSIGNAÇÃO SICOOB - RESCISÃO',
                            'CONSIGNAÇÃO SICOOB SERVIDOR', 'CONSIGNAÇÃO SICREDI', 'CONSIGNAÇÃO SUDACRED',
                            'CONSIGNAÇÃO SUDACRED - RESCISÃO', 'CONTA CAPITAL - CREDLEGIS',
                            'EAGLE - CARTÃO BENEFÍCIO', 'EAGLE - CARTÃO CREDITO',
                            'GEAP SAÚDE - COOPARTICIPAÇÃO', 'GEAP SAÚDE - MENSALIDADE', 'MT SAUDE',
                            'MTXCARD - CARTÃO BENEFÍCIO', 'NIO CARTÃO CREDITO', 'SICOOB', 'SINDAL',
                            'SUDACRED - CARTÃO BENEFÍCIO', 'UNALE', 'UNIMED - CO PARTICIPACAO',
                            'UNIMED - MENSALIDADE'
                        ]
                        
                        # Classificar (ordem importa: facultativos primeiro, depois obrigatórios, por último proventos)
                        eh_desconto_facultativo = any(palavra in descricao_upper for palavra in palavras_desconto_facultativo)
                        eh_desconto_obrigatorio = any(palavra in descricao_upper for palavra in palavras_desconto_obrigatorio)
                        eh_provento = any(palavra in descricao_upper for palavra in palavras_provento)
                        
                        evento_obj = {
                            'descricao': descricao,
                            'valor': valor_evento,
                            'base_calculo': base_calculo,
                            'referencia': referencia,
                            'codigo': codigo
                        }
                        
                        # Classificar na ordem correta: facultativos > obrigatórios > proventos
                        if eh_desconto_facultativo:
                            dados['descontos_extras'].append(evento_obj)
                            dados['total_descontos_extras'] += valor_evento
                            dados['total_descontos'] += valor_evento
                        elif eh_desconto_obrigatorio:
                            dados['descontos_obrigatorios'].append(evento_obj)
                            dados['total_descontos_obrigatorios'] += valor_evento
                            dados['total_descontos'] += valor_evento
                        elif eh_provento:
                            dados['proventos'].append(evento_obj)
                            dados['total_proventos'] += valor_evento
                        else:
                            # Se não identificou, assumir provento
                            dados['proventos'].append(evento_obj)
                            dados['total_proventos'] += valor_evento
                    
                    except Exception as e:
                        pass
        
        # 6. Extrair líquido da linha de totalização
        for linha in linhas:
            if 'Totalizações' in linha:
                match_total = re.search(r'([\d\.,]+)\s*Totalizações', linha)
                if match_total:
                    dados['liquido'] = float(match_total.group(1).replace('.', '').replace(',', '.'))
                    break
        
        # Se não encontrou, calcular
        if dados['liquido'] == 0:
            dados['liquido'] = dados['total_proventos'] - dados['total_descontos']
    
    except Exception as e:
        dados['erro_processamento'] = str(e)
    
    return dados

def extrair_dados_pdf(caminho_pdf, numero_pagina=None):
    """
    Extrai dados estruturados do PDF da folha de pagamento de servidores ATIVOS da SGP.
    
    Args:
        caminho_pdf: Caminho do arquivo PDF
        numero_pagina: Número da página específica a processar (None = todas as páginas)
    """
    try:
        with open(caminho_pdf, 'rb') as arquivo:
            leitor = PyPDF2.PdfReader(arquivo)
            texto_completo = ''
            
            # Se numero_pagina foi especificado, processar apenas essa página
            if numero_pagina is not None:
                texto_completo = leitor.pages[numero_pagina].extract_text()
            else:
                # Processar todas as páginas
                for pagina in leitor.pages:
                    texto_completo += pagina.extract_text()
            
            # Extrair informações usando a função específica para servidores ativos
            linhas = texto_completo.split('\n')
            return extrair_dados_ativos(linhas, caminho_pdf, numero_pagina)
    
    except Exception as e:
        # Retornar dados vazios com erro
        return {
            'nome': '',
            'cpf': '',
            'matricula': '',
            'data_nascimento': '',
            'idade': '',
            'situacao': '',
            'competencia': '',
            'proventos': [],
            'descontos_obrigatorios': [],
            'descontos_extras': [],
            'total_proventos': 0,
            'total_descontos_obrigatorios': 0,
            'total_descontos_extras': 0,
            'total_descontos': 0,
            'liquido': 0,
            'arquivo_origem': os.path.basename(caminho_pdf) + (f" (pág. {numero_pagina+1})" if numero_pagina is not None else ""),
            'erro_processamento': str(e)
        }

def gerar_html_relatorio(dados_folhas):
    """Gera o relatório HTML completo"""
    
    # Extrair competência do primeiro registro que tiver essa informação
    competencia_formatada = "Competência não identificada"
    for folha in dados_folhas:
        if folha.get('competencia'):
            competencia_formatada = folha['competencia']
            break
    
    # Se não encontrou competência nos dados, usar a data atual como fallback
    if competencia_formatada == "Competência não identificada":
        data_processamento = datetime.now()
        mes_competencia = data_processamento.strftime('%B')
        ano_competencia = data_processamento.strftime('%Y')
        
        meses_pt = {
            'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
            'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
            'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
            'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
        }
        mes_competencia = meses_pt.get(mes_competencia, mes_competencia)
        competencia_formatada = f"{mes_competencia}/{ano_competencia}"
    
    # Calcular totais gerais
    total_geral_proventos = sum(f['total_proventos'] for f in dados_folhas)
    total_geral_descontos = sum(f['total_descontos'] for f in dados_folhas)
    total_geral_descontos_obrigatorios = sum(f.get('total_descontos_obrigatorios', 0) for f in dados_folhas)
    total_geral_descontos_extras = sum(f.get('total_descontos_extras', 0) for f in dados_folhas)
    total_geral_liquido = total_geral_proventos - total_geral_descontos
    
    # Coletar todos os tipos de proventos e descontos separados por situação
    tipos_proventos = {}
    tipos_descontos_obrigatorios = {}
    tipos_descontos_facultativos = {}
    
    # Mapeamento de consolidação para descontos facultativos
    mapa_consolidacao_facultativos = {
        'CONSIG. BCO BRASIL': 'BANCO DO BRASIL',
        'CONSIG BANCO DO BRASIL': 'BANCO DO BRASIL',
        'CONSIG BANCO BRASIL': 'BANCO DO BRASIL',
        'CONS.BANCO BRASIL': 'BANCO DO BRASIL',
        'CONS.BANCO DO BRASIL': 'BANCO DO BRASIL',
        'CONS BANCO BRASIL': 'BANCO DO BRASIL',
        'BIGCARD': 'BIGCARD',
        'BANCO BRADESCO': 'BANCO BRADESCO',
        'CONSIGNADO BRADESCO': 'BANCO BRADESCO',
        'CONSIGNADO BRADESSCO': 'BANCO BRADESCO',
        'CONSIGNACAO BANCOOB': 'BANCOOB',
        'CONSIGANDO BANCOOB': 'BANCOOB',
        'CONSIGNADO SICOOB': 'SICOOB',
        'CONSIGNAÇÃO SICOOB': 'SICOOB',
        'CREDLEGIS EMPRESTIMO': 'SICOOB',
        'EMPRESTIMO CREDLEGIS': 'SICOOB',
        'CREDLEGIS': 'SICOOB',
        'CREDLEGIS - EMPRESTIMOS': 'SICOOB',
        'DESCONTO CREDLEGIS': 'SICOOB',
        'MT SAUDE PADRAO': 'MT SAUDE',
        'MT SAUDE ESPECIAL': 'MT SAUDE',
        'MT SAUDE CO-PARTICIPACAO': 'MT SAUDE',
        'SINDAL': 'SINDAL',
        'ASAPAL': 'ASAPAL',
        'NIO DIGITAL': 'NIO',
        'CONSIGNADO CARTAO EAGLE': 'EAGLE',
        'CONSIGNADO CARTAO CREDITO EAGLE': 'EAGLE',
        'CONSIGNADO BENEFICIO EAGLE': 'EAGLE',
        'CONSIGNADO SICREDI': 'SICREDI'
    }
    
    # Mapa de consolidação para descontos obrigatórios
    mapa_consolidacao_obrigatorios = {
        'IMPOSTO DE RENDA NA FONTE': 'IRRF IMPOSTO DE RENDA',
        'ISSSPL-PREVIDENCIA': 'ISSSPL-PREVIDENCIA',
        'ABATIMENTO TETO CONSTITUCIONAL': 'ABATIMENTO DO TETO',
        'PENSAO ALIMENTICIA CALCULADA': 'PENSÃO ALIMENTÍCIA',
        'PENSAO ALIMENTICIA': 'PENSÃO ALIMENTÍCIA',
        'DESCONTO DETERMINACAO JUDICIAL': 'DESCONTOS JUDICIAIS',
        'DESCONTO DETERMINAÇAO JUDICIAL': 'DESCONTOS JUDICIAIS',
        'DESCONTO JUDICIAL': 'DESCONTOS JUDICIAIS'
    }
    
    for folha in dados_folhas:
        situacao = folha.get('situacao', '').upper()
        eh_aposentado = 'APOSENTAD' in situacao
        eh_pensionista = 'PENSIONISTA' in situacao
        
        for provento in folha['proventos']:
            desc = provento['descricao']
            if desc not in tipos_proventos:
                tipos_proventos[desc] = {'aposentados': [], 'pensionistas': [], 'outros': []}
            
            if eh_aposentado:
                tipos_proventos[desc]['aposentados'].append(provento['valor'])
            elif eh_pensionista:
                tipos_proventos[desc]['pensionistas'].append(provento['valor'])
            else:
                tipos_proventos[desc]['outros'].append(provento['valor'])
        
        for desconto in folha.get('descontos_obrigatorios', []):
            tipo_original = desconto['descricao']
            valor = desconto['valor']
            # Consolidar usando o mapeamento
            tipo_consolidado = mapa_consolidacao_obrigatorios.get(tipo_original, tipo_original)
            if tipo_consolidado not in tipos_descontos_obrigatorios:
                tipos_descontos_obrigatorios[tipo_consolidado] = {'aposentados': [], 'pensionistas': [], 'outros': []}
            
            if eh_aposentado:
                tipos_descontos_obrigatorios[tipo_consolidado]['aposentados'].append(valor)
            elif eh_pensionista:
                tipos_descontos_obrigatorios[tipo_consolidado]['pensionistas'].append(valor)
            else:
                tipos_descontos_obrigatorios[tipo_consolidado]['outros'].append(valor)
        
        for desconto in folha.get('descontos_extras', []):
            tipo_original = desconto['descricao']
            valor = desconto['valor']
            # Consolidar usando o mapeamento
            tipo_consolidado = mapa_consolidacao_facultativos.get(tipo_original, tipo_original)
            if tipo_consolidado not in tipos_descontos_facultativos:
                tipos_descontos_facultativos[tipo_consolidado] = {'aposentados': [], 'pensionistas': [], 'outros': []}
            
            if eh_aposentado:
                tipos_descontos_facultativos[tipo_consolidado]['aposentados'].append(valor)
            elif eh_pensionista:
                tipos_descontos_facultativos[tipo_consolidado]['pensionistas'].append(valor)
            else:
                tipos_descontos_facultativos[tipo_consolidado]['outros'].append(valor)
    
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análise da Margem Consignável - SGP/ALMT - {competencia_formatada}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        header {{
            background: white;
            color: #2c3e50;
            padding: 30px 40px;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            border-bottom: 3px solid #2c3e50;
        }}
        
        header .logo {{
            max-width: 600px;
            width: 100%;
            height: auto;
            margin-bottom: 20px;
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            color: #2c3e50;
        }}
        
        header p {{
            font-size: 1.2em;
            opacity: 0.8;
            color: #2c3e50;
        }}
        
        nav {{
            display: none;
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 3px solid #2c3e50;
        }}
        
        nav button {{
            background: white;
            border: 2px solid #2c3e50;
            color: #2c3e50;
            padding: 12px 30px;
            margin: 5px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        
        nav button:hover {{
            background: #2c3e50;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(44, 62, 80, 0.3);
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .secao {{
            display: none;
        }}
        
        .secao.ativa {{
            display: block;
            animation: fadeIn 0.5s;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .indice {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-top: 20px;
        }}
        
        .card-indice {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            padding: 40px;
            border-radius: 15px;
            color: white;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .card-indice:hover {{
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }}
        
        .card-indice i {{
            font-size: 3em;
            margin-bottom: 20px;
            display: block;
        }}
        
        .card-indice h2 {{
            font-size: 1.8em;
            margin-bottom: 15px;
        }}
        
        .card-indice p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .estatistica {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 5px solid #2c3e50;
        }}
        
        .estatistica h3 {{
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}
        
        .grid-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat-box {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        .stat-box .label {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        
        .stat-box .valor {{
            color: #2c3e50;
            font-size: 2em;
            font-weight: bold;
        }}
        
        .stat-box.positivo .valor {{
            color: #27ae60;
            font-weight: bold;
        }}
        
        .stat-box.negativo .valor {{
            color: #7f8c8d;
            font-weight: bold;
        }}
        
        .busca {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        
        .busca input {{
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
            transition: all 0.3s;
        }}
        
        .busca input:focus {{
            outline: none;
            border-color: #2c3e50;
            box-shadow: 0 0 0 3px rgba(44, 62, 80, 0.1);
        }}
        
        .resultado-busca {{
            margin-top: 30px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        table thead {{
            background: #2c3e50;
            color: white;
        }}
        
        table th, table td {{
            padding: 15px;
            text-align: left;
        }}
        
        table tbody tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        table tbody tr:hover {{
            background: #e9ecef;
        }}
        
        /* Scroll suave para âncoras */
        html {{
            scroll-behavior: smooth;
        }}
        
        /* Estilo para links de beneficiários críticos */
        a[href^="#beneficiario-"]:hover {{
            color: #721c24 !important;
            border-bottom: 2px solid #721c24 !important;
            text-decoration: none !important;
        }}
        
        /* ============================================ */
        /* RESPONSIVIDADE MOBILE */
        /* ============================================ */
        @media screen and (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .container {{
                border-radius: 10px;
            }}
            
            header {{
                padding: 20px 15px;
            }}
            
            header h1 {{
                font-size: 1.5em;
                line-height: 1.3;
            }}
            
            header p {{
                font-size: 0.9em;
            }}
            
            .content {{
                padding: 20px 15px;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr !important;
                gap: 15px;
            }}
            
            .stat-card {{
                padding: 20px 15px;
            }}
            
            .stat-card h3 {{
                font-size: 0.9em;
            }}
            
            .stat-card .valor {{
                font-size: 1.5em;
            }}
            
            .search-container {{
                padding: 15px;
            }}
            
            .search-container input {{
                font-size: 14px;
                padding: 12px 15px;
            }}
            
            table {{
                font-size: 12px;
                display: block;
                overflow-x: auto;
                white-space: nowrap;
                -webkit-overflow-scrolling: touch;
            }}
            
            table th,
            table td {{
                padding: 8px 6px;
            }}
            
            .alert {{
                padding: 15px;
                font-size: 0.9em;
            }}
            
            nav {{
                padding: 15px 10px;
                text-align: center;
            }}
            
            nav button {{
                padding: 10px 20px;
                font-size: 14px;
                margin: 5px 3px;
            }}
            
            /* Ajustes para seção de Ajuste de Margem */
            .stats-grid[style*="grid-template-columns: repeat(2, 1fr)"] {{
                grid-template-columns: 1fr !important;
            }}
            
            /* Ajuste de títulos menores */
            h2 {{
                font-size: 1.3em;
            }}
            
            h3 {{
                font-size: 1.1em;
            }}
            
            h4 {{
                font-size: 1em;
            }}
            
            h5 {{
                font-size: 0.95em;
            }}
        }}
        
        @media screen and (max-width: 480px) {{
            header h1 {{
                font-size: 1.2em;
            }}
            
            .stat-card .valor {{
                font-size: 1.3em;
            }}
            
            table {{
                font-size: 11px;
            }}
            
            nav button {{
                padding: 8px 15px;
                font-size: 12px;
                display: block;
                width: 100%;
                margin: 5px 0;
            }}
        }}
    </style>

</head>
<body>
    <div class="container">
        <header>
            <h1>Análise da Margem Consignável - SGP/ALMT</h1>
            <p>Competência: {competencia_formatada}</p>
        </header>
        
        <nav id="navegacao" style="display: none;">
            <button onclick="mostrarSecao('indice')">🏠 Início</button>
            <button onclick="mostrarSecao('geral')">📈 Relatório Geral</button>
            <button onclick="mostrarSecao('beneficiario')">👤 Por Beneficiário</button>
        </nav>
        
        <div class="content">
            <!-- ÍNDICE INICIAL -->
            <div id="indice" class="secao ativa">
                <h2 style="text-align: center; color: #2c3e50; margin-bottom: 30px;">Escolha uma opção:</h2>
                <div class="indice">
                    <div class="card-indice" onclick="mostrarSecao('geral')">
                        <i>📈</i>
                        <h2>Relatório Geral</h2>
                        <p>Visão consolidada de todas as folhas de pagamento</p>
                    </div>
                    <div class="card-indice" onclick="mostrarSecao('beneficiario')">
                        <i>👤</i>
                        <h2>Relatório por Beneficiário</h2>
                        <p>Consulte informações individuais por nome ou CPF</p>
                    </div>
                </div>
            </div>
            
            <!-- RELATÓRIO GERAL -->
            <div id="geral" class="secao">
                <h2 style="color: #2c3e50; margin-bottom: 30px;">📈 Relatório Geral - {competencia_formatada}</h2>
                
                <!-- SITUAÇÃO FUNCIONAL E FAIXA ETÁRIA -->
                <div class="estatistica">
                    <h3>👥 SITUAÇÃO FUNCIONAL E FAIXA ETÁRIA</h3>
                    <p style="color: #555; margin-bottom: 20px;">
                        Análise demográfica cruzada para monitoramento estratégico da distribuição etária por situação funcional.
                    </p>
"""
    
    # Análise cruzada: situação x faixa etária
    situacoes_faixas = {}
    faixas_def = {
        '50-59 anos': {'min': 50, 'max': 59},
        '60-69 anos': {'min': 60, 'max': 69},
        '70-79 anos': {'min': 70, 'max': 79},
        '80-89 anos': {'min': 80, 'max': 89},
        '90+ anos': {'min': 90, 'max': 150}
    }
    
    # Coletar dados para análise cruzada
    for dados in dados_folhas:
        sit = dados.get('situacao', 'Não informado')
        
        # Extrair idade
        idade_raw = dados.get('idade', '0')
        if isinstance(idade_raw, str):
            idade = int(idade_raw.split()[0]) if idade_raw else 0
        else:
            idade = int(idade_raw)
        
        # Identificar faixa etária
        faixa_identificada = 'Não identificado'
        for faixa_nome, faixa_range in faixas_def.items():
            if faixa_range['min'] <= idade <= faixa_range['max']:
                faixa_identificada = faixa_nome
                break
        
        # Inicializar estrutura se necessário
        if sit not in situacoes_faixas:
            situacoes_faixas[sit] = {
                'total_qtd': 0,
                'total_proventos': 0,
                'faixas': {faixa: {'qtd': 0, 'total_proventos': 0} for faixa in faixas_def.keys()}
            }
        
        # Acumular dados
        situacoes_faixas[sit]['total_qtd'] += 1
        situacoes_faixas[sit]['total_proventos'] += dados.get('total_proventos', 0)
        if faixa_identificada in situacoes_faixas[sit]['faixas']:
            situacoes_faixas[sit]['faixas'][faixa_identificada]['qtd'] += 1
            situacoes_faixas[sit]['faixas'][faixa_identificada]['total_proventos'] += dados.get('total_proventos', 0)
    
    # Renderizar tabelas por situação
    for situacao in sorted(situacoes_faixas.keys()):
        stats = situacoes_faixas[situacao]
        percentual_total = (stats['total_qtd'] / len(dados_folhas)) * 100
        media_geral_bruta = stats['total_proventos'] / stats['total_qtd'] if stats['total_qtd'] > 0 else 0
        
        html += f"""
                    <div style="margin-bottom: 30px;">
                        <h4 style="color: #2c3e50; margin-bottom: 15px; padding: 15px; background: linear-gradient(90deg, #2c3e50 0%, #34495e 100%); color: white; border-radius: 8px 8px 0 0;">
                            � {situacao} - {stats['total_qtd']} beneficiários ({percentual_total:.1f}% do total)
                        </h4>
                        <table>
                            <thead>
                                <tr>
                                    <th>Faixa Etária</th>
                                    <th>Quantidade</th>
                                    <th>% da Situação</th>
                                    <th>% do Total Geral</th>
                                </tr>
                            </thead>
                            <tbody>
"""
        
        # Renderizar faixas etárias para esta situação
        for faixa_nome in faixas_def.keys():
            faixa_data = stats['faixas'][faixa_nome]
            if faixa_data['qtd'] > 0:
                perc_situacao = (faixa_data['qtd'] / stats['total_qtd'] * 100) if stats['total_qtd'] > 0 else 0
                perc_geral = (faixa_data['qtd'] / len(dados_folhas) * 100)
                media_bruta_faixa = faixa_data['total_proventos'] / faixa_data['qtd'] if faixa_data['qtd'] > 0 else 0
                
                html += f"""                                <tr>
                                    <td>{faixa_nome}</td>
                                    <td><strong>{faixa_data['qtd']}</strong></td>
                                    <td>{perc_situacao:.1f}%</td>
                                    <td>{perc_geral:.1f}%</td>
                                </tr>
"""
        
        # Linha de total para esta situação
        html += f"""                                <tr style="background: #f8f9fa; font-weight: bold; border-top: 2px solid #2c3e50;">
                                    <td>TOTAL {situacao}</td>
                                    <td><strong>{stats['total_qtd']}</strong></td>
                                    <td>100%</td>
                                    <td>{percentual_total:.1f}%</td>
                                </tr>
"""
        
        html += """                            </tbody>
                        </table>
                    </div>
"""
    
    # Resumo consolidado
    html += f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 8px; color: white; margin-top: 20px;">
                        <h4 style="color: white; margin-bottom: 15px; border-bottom: 2px solid rgba(255,255,255,0.3); padding-bottom: 10px;">
                            📊 RESUMO CONSOLIDADO
                        </h4>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                            <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 6px; text-align: center;">
                                <div style="font-size: 12px; opacity: 0.9; margin-bottom: 5px;">Total de Beneficiários</div>
                                <div style="font-size: 28px; font-weight: bold;">{len(dados_folhas)}</div>
                            </div>
                            <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 6px; text-align: center;">
                                <div style="font-size: 12px; opacity: 0.9; margin-bottom: 5px;">Situações Funcionais</div>
                                <div style="font-size: 28px; font-weight: bold;">{len(situacoes_faixas)}</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- SAÚDE FINANCEIRA DOS BENEFICIÁRIOS -->
                <div class="estatistica">
                    <h3>🏥 ANÁLISE DE SAÚDE FINANCEIRA</h3>
                    <p style="color: #555; margin-bottom: 20px;">
                        Avaliação da capacidade financeira e nível de comprometimento da renda dos beneficiários.
                    </p>
"""
    
    # Análise de saúde financeira - baseada na REMUNERAÇÃO LÍQUIDA
    saudavel = 0  # Descontos extras < 20% da remuneração líquida
    atencao = 0   # Descontos extras entre 20-30% da remuneração líquida
    risco = 0     # Descontos extras entre 30-35% da remuneração líquida
    critico = 0   # Descontos extras > 35% da remuneração líquida
    sem_descontos = 0
    
    beneficiarios_criticos = []  # Lista para armazenar beneficiários em situação crítica (>35%)
    
    for dados in dados_folhas:
        total_prov = dados.get('total_proventos', 0)
        descontos_obrig = dados.get('total_descontos_obrigatorios', 0)
        descontos_extras = dados.get('total_descontos_extras', 0)
        
        # Base de cálculo: Remuneração Líquida (Proventos - Descontos Obrigatórios)
        remuneracao_liquida = total_prov - descontos_obrig
        
        if descontos_extras == 0:
            sem_descontos += 1
        elif remuneracao_liquida > 0:
            percentual = (descontos_extras / remuneracao_liquida) * 100
            if percentual < 20:
                saudavel += 1
            elif percentual < 30:
                atencao += 1
            elif percentual < 35:
                risco += 1
            else:
                critico += 1
                # Adicionar à lista de beneficiários críticos (somente >35%)
                valor_liquido_recebido = remuneracao_liquida - descontos_extras
                
                # Verificar se há evento de rescisão
                tem_rescisao = any(
                    '13º SALÁRIO FIXO RESCISÃO' in evento.get('descricao', '').upper()
                    for evento in dados.get('proventos', [])
                )
                
                beneficiarios_criticos.append({
                    'nome': dados.get('nome', 'N/A'),
                    'cpf': dados.get('cpf', 'N/A'),
                    'situacao': dados.get('situacao', 'N/A'),
                    'remuneracao_liquida': remuneracao_liquida,
                    'descontos_extras': descontos_extras,
                    'percentual': percentual,
                    'valor_liquido_recebido': valor_liquido_recebido,
                    'rescisao': 'Sim' if tem_rescisao else 'Não'
                })
    
    html += f"""
                    <div class="grid-stats">
                        <div style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px;">
                            <div style="font-size: 14px; color: #155724; margin-bottom: 5px;">✅ Situação Saudável</div>
                            <div style="font-size: 28px; font-weight: bold; color: #28a745;">{saudavel + sem_descontos}</div>
                            <small style="color: #666;">Sem descontos extras ou < 20% da remuneração líquida</small>
                        </div>
                        <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; border-radius: 8px;">
                            <div style="font-size: 14px; color: #856404; margin-bottom: 5px;">⚠️ Atenção</div>
                            <div style="font-size: 28px; font-weight: bold; color: #ffc107;">{atencao}</div>
                            <small style="color: #666;">20-30% da remuneração líquida comprometida</small>
                        </div>
                        <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 20px; border-radius: 8px;">
                            <div style="font-size: 14px; color: #721c24; margin-bottom: 5px;">🔴 Risco</div>
                            <div style="font-size: 28px; font-weight: bold; color: #dc3545;">{risco}</div>
                            <small style="color: #666;">30-35% da remuneração líquida - Atenção necessária</small>
                        </div>
                        <div style="background: #f5c6cb; border-left: 4px solid #a71d2a; padding: 20px; border-radius: 8px;">
                            <div style="font-size: 14px; color: #491217; margin-bottom: 5px;">🚨 Crítico</div>
                            <div style="font-size: 28px; font-weight: bold; color: #a71d2a;">{critico}</div>
                            <small style="color: #666;">> 35% da remuneração líquida - Intervenção urgente</small>
                        </div>
                    </div>
"""
    
    # Se houver beneficiários em situação crítica, mostrar tabela detalhada
    if beneficiarios_criticos:
        html += f"""
                    <div style="background: #f8d7da; border: 2px solid #a71d2a; padding: 20px; border-radius: 10px; margin-top: 25px;">
                        <h4 style="color: #491217; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.5em;">🚨</span>
                            BENEFICIÁRIOS EM SITUAÇÃO CRÍTICA: {len(beneficiarios_criticos)} pessoa(s)
                        </h4>
                        <p style="color: #721c24; margin-bottom: 15px; font-size: 0.95em;">
                            Os seguintes beneficiários estão comprometendo mais de 35% da sua remuneração líquida com descontos facultativos:
                        </p>
                        <table style="font-size: 0.95em;">
                            <thead>
                                <tr>
                                    <th>Nome</th>
                                    <th>Situação</th>
                                    <th>Margem Consignável</th>
                                    <th>Margem Comprometida</th>
                                    <th>% Comprometido</th>
                                    <th>Valor Líquido Recebido</th>
                                    <th>Rescisão de Contrato</th>
                                </tr>
                            </thead>
                            <tbody>
"""
        
        for benef in sorted(beneficiarios_criticos, key=lambda x: x['percentual'], reverse=True):
            # Criar ID único baseado no CPF para busca
            cpf_limpo = benef.get('cpf', '').replace('.', '').replace('-', '')
            rescisao_style = 'color: #a71d2a; font-weight: bold;' if benef.get('rescisao') == 'Sim' else 'color: #2c3e50;'
            html += f"""                                <tr>
                                    <td><strong><a href="javascript:void(0);" onclick="abrirBeneficiario('{benef.get('cpf', '')}')" style="color: #a71d2a; text-decoration: none; border-bottom: 1px dashed #a71d2a; cursor: pointer;" title="Clique para ver detalhes de {benef['nome']}">{benef['nome']}</a></strong></td>
                                    <td>{benef['situacao']}</td>
                                    <td>R$ {formatar_moeda_br(benef['remuneracao_liquida'])}</td>
                                    <td style="color: #a71d2a; font-weight: bold;">R$ {formatar_moeda_br(benef['descontos_extras'])}</td>
                                    <td style="color: #a71d2a; font-weight: bold; font-size: 1.1em;">{benef['percentual']:.1f}%</td>
                                    <td style="color: #2c3e50; font-weight: bold;">R$ {formatar_moeda_br(benef['valor_liquido_recebido'])}</td>
                                    <td style="{rescisao_style} text-align: center; font-weight: bold;">{benef.get('rescisao', 'Não')}</td>
                                </tr>
"""
        
        html += """                            </tbody>
                        </table>
                        <div style="margin-top: 15px; padding: 15px; background: rgba(169, 29, 42, 0.2); border-radius: 6px; border-left: 4px solid #a71d2a;">
                            <strong>⚠️ RECOMENDAÇÃO URGENTE:</strong>
                            <ul style="margin: 10px 0 0 20px; line-height: 1.8;">
                                <li>Entrar em contato imediatamente com estes beneficiários</li>
                                <li>Avaliar a possibilidade de renegociação dos empréstimos consignados</li>
                                <li>Orientar sobre planejamento financeiro e riscos de endividamento excessivo</li>
                                <li>Considerar encaminhamento para assistência social ou orientação financeira</li>
                            </ul>
                        </div>
                    </div>
"""
    
    html += """                </div>
                
                <!-- IMPACTO FINANCEIRO DETALHADO -->
                <div class="estatistica">
                    <h3>💰 IMPACTO FINANCEIRO POR PROVENTO</h3>
                    <p style="color: #555; margin-bottom: 15px;">Distribuição dos proventos por tipo e seu impacto no orçamento total.</p>
                    <table>
                        <thead>
                            <tr>
                                <th>Tipo de Provento</th>
                                <th>Ocorrências Aposentados</th>
                                <th>Ocorrências Pensionistas</th>
                                <th>Total Ocorrências</th>
                                <th>Valor Aposentados</th>
                                <th>Valor Pensionistas</th>
                                <th>Valor Total</th>
                                <th>% do Orçamento</th>
                            </tr>
                        </thead>
                        <tbody>
"""
    
    for tipo, dados in sorted(tipos_proventos.items(), key=lambda x: sum(x[1]['aposentados']) + sum(x[1]['pensionistas']) + sum(x[1]['outros']), reverse=True):
        qtd_aposentados = len(dados['aposentados'])
        qtd_pensionistas = len(dados['pensionistas'])
        qtd_outros = len(dados['outros'])
        qtd_total = qtd_aposentados + qtd_pensionistas + qtd_outros
        
        valor_aposentados = sum(dados['aposentados'])
        valor_pensionistas = sum(dados['pensionistas'])
        valor_outros = sum(dados['outros'])
        total = valor_aposentados + valor_pensionistas + valor_outros
        
        percentual_orcamento = (total / total_geral_proventos) * 100
        html += f"""                            <tr>
                                <td><strong>{tipo}</strong></td>
                                <td>{qtd_aposentados}</td>
                                <td>{qtd_pensionistas}</td>
                                <td>{qtd_total}</td>
                                <td>R$ {formatar_moeda_br(valor_aposentados)}</td>
                                <td>R$ {formatar_moeda_br(valor_pensionistas)}</td>
                                <td>R$ {formatar_moeda_br(total)}</td>
                                <td>{percentual_orcamento:.1f}%</td>
                            </tr>
"""
    
    html += """                        </tbody>
                    </table>
                </div>
                
                <div class="estatistica">
                    <h3>⚖️ IMPACTO FINANCEIRO POR DESCONTO OBRIGATÓRIO</h3>
                    <p style="color: #555; margin-bottom: 15px;">Descontos compulsórios previstos em lei (Previdência, Imposto de Renda, etc.).</p>
                    <table>
                        <thead>
                            <tr>
                                <th>Tipo de Desconto</th>
                                <th>Ocorrências Aposentados</th>
                                <th>Ocorrências Pensionistas</th>
                                <th>Total Ocorrências</th>
                                <th>Valor Aposentados</th>
                                <th>Valor Pensionistas</th>
                                <th>Valor Total</th>
                                <th>% dos Descontos Obrigatórios</th>
                            </tr>
                        </thead>
                        <tbody>
"""
    
    for tipo, dados in sorted(tipos_descontos_obrigatorios.items(), key=lambda x: sum(x[1]['aposentados']) + sum(x[1]['pensionistas']) + sum(x[1]['outros']), reverse=True):
        qtd_aposentados = len(dados['aposentados'])
        qtd_pensionistas = len(dados['pensionistas'])
        qtd_outros = len(dados['outros'])
        qtd_total = qtd_aposentados + qtd_pensionistas + qtd_outros
        
        valor_aposentados = sum(dados['aposentados'])
        valor_pensionistas = sum(dados['pensionistas'])
        valor_outros = sum(dados['outros'])
        total = valor_aposentados + valor_pensionistas + valor_outros
        
        percentual_descontos_tipo = (total / total_geral_descontos_obrigatorios * 100) if total_geral_descontos_obrigatorios > 0 else 0
        html += f"""                            <tr>
                                <td><strong>{tipo}</strong></td>
                                <td>{qtd_aposentados}</td>
                                <td>{qtd_pensionistas}</td>
                                <td>{qtd_total}</td>
                                <td>R$ {formatar_moeda_br(valor_aposentados)}</td>
                                <td>R$ {formatar_moeda_br(valor_pensionistas)}</td>
                                <td>R$ {formatar_moeda_br(total)}</td>
                                <td>{percentual_descontos_tipo:.1f}%</td>
                            </tr>
"""
    
    html += """                        </tbody>
                    </table>
                </div>
                
                <div class="estatistica">
                    <h3>📉 IMPACTO FINANCEIRO POR DESCONTO FACULTATIVO</h3>
                    <p style="color: #555; margin-bottom: 15px;">Descontos opcionais (Empréstimos Consignados, Planos de Saúde, Associações, etc.).</p>
                    <table>
                        <thead>
                            <tr>
                                <th>Tipo de Desconto</th>
                                <th>Ocorrências Aposentados</th>
                                <th>Ocorrências Pensionistas</th>
                                <th>Total Ocorrências</th>
                                <th>Valor Aposentados</th>
                                <th>Valor Pensionistas</th>
                                <th>Valor Total</th>
                                <th>% dos Descontos Facultativos</th>
                            </tr>
                        </thead>
                        <tbody>
"""
    
    for tipo, dados in sorted(tipos_descontos_facultativos.items(), key=lambda x: sum(x[1]['aposentados']) + sum(x[1]['pensionistas']) + sum(x[1]['outros']), reverse=True):
        qtd_aposentados = len(dados['aposentados'])
        qtd_pensionistas = len(dados['pensionistas'])
        qtd_outros = len(dados['outros'])
        qtd_total = qtd_aposentados + qtd_pensionistas + qtd_outros
        
        valor_aposentados = sum(dados['aposentados'])
        valor_pensionistas = sum(dados['pensionistas'])
        valor_outros = sum(dados['outros'])
        total = valor_aposentados + valor_pensionistas + valor_outros
        
        percentual_descontos_tipo = (total / total_geral_descontos_extras * 100) if total_geral_descontos_extras > 0 else 0
        html += f"""                            <tr>
                                <td><strong>{tipo}</strong></td>
                                <td>{qtd_aposentados}</td>
                                <td>{qtd_pensionistas}</td>
                                <td>{qtd_total}</td>
                                <td>R$ {formatar_moeda_br(valor_aposentados)}</td>
                                <td>R$ {formatar_moeda_br(valor_pensionistas)}</td>
                                <td>R$ {formatar_moeda_br(total)}</td>
                                <td>{percentual_descontos_tipo:.1f}%</td>
                            </tr>
"""
    
    html += f"""                        </tbody>
                    </table>
                    
                    <!-- Gráfico de Pizza dos Descontos Facultativos -->
                    <div style="background: white; padding: 30px; border-radius: 10px; margin-top: 30px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                        <h4 style="color: #2c3e50; margin-bottom: 20px; text-align: center;">📊 Distribuição Visual dos Descontos Facultativos</h4>
                        <div style="max-width: 500px; margin: 0 auto;">
                            <canvas id="graficoDescontosFacultativos"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- RELATÓRIO POR BENEFICIÁRIO -->
            <div id="beneficiario" class="secao">
                <h2 style="color: #2c3e50; margin-bottom: 30px;">👤 Relatório por Beneficiário</h2>
                
                <div class="busca">
                    <label style="display: block; margin-bottom: 10px; font-weight: 600; color: #333;">
                        🔍 Pesquisar por Nome ou CPF:
                    </label>
                    <input type="text" id="campoBusca" placeholder="Digite o nome completo ou parcial (ex: JOÃO DA SILVA) ou CPF..." 
                           onkeyup="buscarBeneficiario()" autocomplete="off">
                </div>
                
                <div id="resultadoBusca" class="resultado-busca"></div>
            </div>
        </div>
    </div>
    
    <script>
        // Dados dos beneficiários
        const dadosBeneficiarios = """ + json.dumps(dados_folhas, ensure_ascii=False) + """;
        
        // Criar gráfico de pizza quando a página carregar
        window.addEventListener('DOMContentLoaded', function() {
            const ctx = document.getElementById('graficoDescontosFacultativos');
            if (ctx) {
                const descontosFacultativos = """ + json.dumps([
                    {'tipo': tipo, 'valor': sum(dados['aposentados']) + sum(dados['pensionistas']) + sum(dados['outros'])} 
                    for tipo, dados in sorted(tipos_descontos_facultativos.items(), 
                                             key=lambda x: sum(x[1]['aposentados']) + sum(x[1]['pensionistas']) + sum(x[1]['outros']), 
                                             reverse=True)
                ], ensure_ascii=False) + """;
                
                const labels = descontosFacultativos.map(d => d.tipo);
                const valores = descontosFacultativos.map(d => d.valor);
                const cores = [
                    '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
                    '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b'
                ];
                
                new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: valores,
                            backgroundColor: cores.slice(0, labels.length),
                            borderColor: '#fff',
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 15,
                                    font: {
                                        size: 12,
                                        family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
                                    }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = context.parsed || 0;
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return label + ': R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' (' + percentage + '%)';
                                    }
                                }
                            }
                        }
                    }
                });
            }
        });
        
        function mostrarSecao(secaoId) {
            // Esconder todas as seções
            document.querySelectorAll('.secao').forEach(s => s.classList.remove('ativa'));
            
            // Mostrar seção selecionada
            document.getElementById(secaoId).classList.add('ativa');
            
            // Mostrar/esconder navegação
            document.getElementById('navegacao').style.display = secaoId === 'indice' ? 'none' : 'block';
            
            // Scroll to top
            window.scrollTo(0, 0);
        }
        
        let beneficiariosEncontrados = [];
        
        // Função para abrir beneficiário específico ao clicar no link
        function abrirBeneficiario(cpf) {
            // Mudar para a seção de busca
            mostrarSecao('beneficiario');
            
            // Buscar o beneficiário diretamente pelo CPF
            const beneficiario = dadosBeneficiarios.find(b => b.cpf === cpf);
            
            if (!beneficiario) {
                document.getElementById('resultadoBusca').innerHTML = '<div style="background: #f8d7da; padding: 20px; border-radius: 8px; color: #721c24;"><strong>❌ Beneficiário não encontrado.</strong><br>CPF buscado: ' + cpf + '</div>';
                return;
            }
            
            // Preencher o campo de busca
            document.getElementById('campoBusca').value = beneficiario.nome;
            
            // Exibir o beneficiário diretamente
            exibirBeneficiario(beneficiario);
            
            // Scroll para o resultado após renderizar
            setTimeout(() => {
                const resultado = document.getElementById('resultadoBusca');
                if (resultado) {
                    resultado.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 200);
        }
        
        function buscarBeneficiario() {
            const termo = document.getElementById('campoBusca').value.toLowerCase().trim();
            const resultado = document.getElementById('resultadoBusca');
            
            if (termo.length === 0) {
                resultado.innerHTML = '<p style="color: #666; text-align: center; padding: 40px;">Digite o nome ou CPF do beneficiário para iniciar a busca...</p>';
                beneficiariosEncontrados = [];
                return;
            }
            
            if (termo.length < 3) {
                resultado.innerHTML = '<p style="color: #666; text-align: center; padding: 40px;">Digite pelo menos 3 caracteres para buscar...</p>';
                beneficiariosEncontrados = [];
                return;
            }
            
            // Filtrar beneficiários: buscar em qualquer parte do nome ou CPF
            beneficiariosEncontrados = dadosBeneficiarios.filter(b => {
                const nomeCompleto = b.nome.toLowerCase();
                const cpfLimpo = b.cpf.replace(/[\\.\\-]/g, '');
                const termoLimpo = termo.replace(/[\\.\\-]/g, '');
                
                // Verificar se o nome contém o termo OU se o CPF contém o termo
                return nomeCompleto.includes(termo) || cpfLimpo.includes(termoLimpo);
            });
            
            if (beneficiariosEncontrados.length === 0) {
                resultado.innerHTML = `
                    <div style="background: #fff3cd; border: 2px solid #ffc107; padding: 30px; border-radius: 12px; text-align: center;">
                        <div style="font-size: 3em; margin-bottom: 15px;">🔍</div>
                        <strong style="font-size: 1.2em; color: #856404;">Nenhum beneficiário encontrado</strong><br>
                        <p style="color: #856404; margin-top: 10px;">Termo buscado: "${termo}"</p>
                        <small style="color: #666;">A busca considera qualquer parte do nome completo ou CPF</small>
                    </div>
                `;
                return;
            }
            
            // Se encontrou apenas 1 resultado, exibir diretamente
            if (beneficiariosEncontrados.length === 1) {
                exibirBeneficiario(beneficiariosEncontrados[0]);
            } else {
                // Se encontrou múltiplos, mostrar lista para seleção
                exibirListaBeneficiarios();
            }
        }
        
        function exibirListaBeneficiarios() {
            const resultado = document.getElementById('resultadoBusca');
            const termo = document.getElementById('campoBusca').value.toLowerCase();
            
            let html = `
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                    <div style="text-align: center;">
                        <div style="font-size: 1.2em; font-weight: bold;">${beneficiariosEncontrados.length} beneficiário(s) encontrado(s)</div>
                        <div style="font-size: 0.9em; opacity: 0.9; margin-top: 5px;">Clique em um nome para ver os detalhes</div>
                    </div>
                </div>
                <div style="display: grid; gap: 15px;">
            `;
            
            beneficiariosEncontrados.forEach((benef, index) => {
                // Destacar o termo buscado no nome
                let nomeDestacado = benef.nome;
                if (termo.length >= 3) {
                    const regex = new RegExp(`(${termo})`, 'gi');
                    nomeDestacado = benef.nome.replace(regex, '<span style="background: #fff3cd; padding: 2px 4px; border-radius: 3px; font-weight: bold;">$1</span>');
                }
                
                html += `
                    <div onclick="exibirBeneficiario(dadosBeneficiarios.find(b => b.cpf === '${benef.cpf}'))" 
                         style="background: white; border: 2px solid #e0e0e0; padding: 20px; border-radius: 8px; cursor: pointer; transition: all 0.3s;"
                         onmouseover="this.style.borderColor='#667eea'; this.style.boxShadow='0 4px 12px rgba(102, 126, 234, 0.2)';" 
                         onmouseout="this.style.borderColor='#e0e0e0'; this.style.boxShadow='none';">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-size: 1.1em; font-weight: bold; color: #2c3e50; margin-bottom: 5px;">${nomeDestacado}</div>
                                <div style="color: #666; font-size: 0.9em;">CPF: ${benef.cpf} | Matrícula: ${benef.matricula}</div>
                            </div>
                            <div style="color: #667eea; font-size: 1.5em;">→</div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            resultado.innerHTML = html;
        }
        
        function exibirBeneficiario(beneficiario) {
            const resultado = document.getElementById('resultadoBusca');
            let html = '';
            
            html += `
                <div class="estatistica">
                    <h3>👤 ${beneficiario.nome}</h3>
                    <div class="grid-stats" style="margin-bottom: 20px;">
                        <div class="stat-box">
                            <div class="label">CPF</div>
                            <div class="valor" style="font-size: 1.2em;">${beneficiario.cpf}</div>
                        </div>
                        <div class="stat-box">
                            <div class="label">Matrícula</div>
                            <div class="valor" style="font-size: 1.2em;">${beneficiario.matricula}</div>
                        </div>
                        <div class="stat-box">
                            <div class="label">Data de Nascimento</div>
                            <div class="valor" style="font-size: 1em;">${beneficiario.data_nascimento}</div>
                            <div class="label" style="margin-top: 5px; font-size: 0.9em;">${beneficiario.idade}</div>
                        </div>
                        <div class="stat-box">
                            <div class="label">Situação</div>
                            <div class="valor" style="font-size: 1em;">${beneficiario.situacao}</div>
                        </div>
            `;
            
            // Verificar se há evento de rescisão
            const temRescisao = beneficiario.proventos.some(p => p.descricao.toUpperCase().includes('13º SALÁRIO FIXO RESCISÃO'));
            
            if (temRescisao) {
                html += `
                        <div class="stat-box" style="background: linear-gradient(135deg, #fff3e0 0%, #fef8f0 100%); border: 2px solid #ff9800;">
                            <div class="label" style="color: #e65100;">⚠️ Rescisão de Contrato</div>
                            <div class="valor" style="font-size: 1.5em; color: #ff9800; font-weight: bold;">SIM</div>
                        </div>
                `;
            }
            
            html += `
                    </div>
                    
                    <div style="background: linear-gradient(135deg, #e8f5e9 0%, #f1f8f4 100%); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 5px solid #27ae60;">
                        <h4 style="color: #27ae60; margin: 0 0 20px 0; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.5em;">💰</span>
                            <span>PROVENTOS (Entradas)</span>
                        </h4>
                        <table style="background: white;">
                            <thead>
                                <tr>
                                    <th style="text-align: left;">Descrição</th>
                                    <th style="text-align: right; width: 120px;">Valor</th>
                                    <th style="text-align: right; width: 100px;">% do Total</th>
                                    <th style="text-align: center; width: 200px;">Impacto Visual</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            // Ordenar proventos por valor (do maior para o menor)
            const proventosOrdenados = [...beneficiario.proventos].sort((a, b) => b.valor - a.valor);
                
                proventosOrdenados.forEach(p => {
                    const percentual = (p.valor / beneficiario.total_proventos * 100).toFixed(1);
                    const barWidth = Math.min(percentual, 100);
                    html += `
                                <tr>
                                    <td style="font-weight: 500;">${p.descricao}</td>
                                    <td style="text-align: right; color: #27ae60; font-weight: 600;">R$ ${p.valor.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                    <td style="text-align: right; font-weight: 600; color: #27ae60;">${percentual}%</td>
                                    <td>
                                        <div style="background: #e8f5e9; border-radius: 10px; height: 20px; position: relative; overflow: hidden;">
                                            <div style="background: linear-gradient(90deg, #27ae60, #2ecc71); height: 100%; width: ${barWidth}%; border-radius: 10px; transition: width 0.3s;"></div>
                                        </div>
                                    </td>
                                </tr>
                    `;
                });
                
                html += `
                                <tr style="background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); color: white; font-weight: bold; font-size: 1.1em;">
                                    <td style="padding: 15px;">TOTAL DE PROVENTOS</td>
                                    <td style="text-align: right; padding: 15px;">R$ ${beneficiario.total_proventos.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                    <td style="text-align: right; padding: 15px;">100%</td>
                                    <td style="text-align: center; padding: 15px;">✓</td>
                                </tr>
                            </tbody>
                        </table>
                        </div>
                        
                        <div style="background: linear-gradient(135deg, #fff3e0 0%, #fef8f0 100%); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 5px solid #ff9800;">
                            <h4 style="color: #ff9800; margin: 0 0 20px 0; display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 1.5em;">⚖️</span>
                                <span>DESCONTOS OBRIGATÓRIOS (Saídas)</span>
                            </h4>
                            <p style="color: #666; font-size: 0.95em; margin-bottom: 15px;">Descontos exigidos por lei (Previdência, Imposto de Renda, etc.)</p>
                            <table style="background: white;">
                                <thead>
                                    <tr>
                                        <th style="text-align: left;">Descrição</th>
                                        <th style="text-align: right; width: 120px;">Valor</th>
                                        <th style="text-align: right; width: 100px;">% do Total</th>
                                        <th style="text-align: center; width: 200px;">Impacto Visual</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                if (beneficiario.descontos_obrigatorios && beneficiario.descontos_obrigatorios.length > 0) {
                    // Ordenar descontos obrigatórios por valor (do maior para o menor)
                    const descontosObrigatoriosOrdenados = [...beneficiario.descontos_obrigatorios].sort((a, b) => b.valor - a.valor);
                    
                    descontosObrigatoriosOrdenados.forEach(d => {
                        const percentual = beneficiario.total_descontos_obrigatorios > 0 ? (d.valor / beneficiario.total_descontos_obrigatorios * 100).toFixed(1) : 0;
                        const barWidth = Math.min(percentual, 100);
                        html += `
                                <tr>
                                    <td style="font-weight: 500;">${d.descricao}</td>
                                    <td style="text-align: right; color: #ff9800; font-weight: 600;">R$ ${d.valor.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                    <td style="text-align: right; font-weight: 600; color: #ff9800;">${percentual}%</td>
                                    <td>
                                        <div style="background: #fff3e0; border-radius: 10px; height: 20px; position: relative; overflow: hidden;">
                                            <div style="background: linear-gradient(90deg, #ff9800, #ffb74d); height: 100%; width: ${barWidth}%; border-radius: 10px; transition: width 0.3s;"></div>
                                        </div>
                                    </td>
                                </tr>
                        `;
                    });
                } else {
                    html += `
                                <tr>
                                    <td colspan="4" style="text-align: center; padding: 20px; color: #999;">Nenhum desconto obrigatório encontrado</td>
                                </tr>
                    `;
                }
                
                html += `
                                <tr style="background: linear-gradient(135deg, #ff9800 0%, #ffb74d 100%); color: white; font-weight: bold; font-size: 1.1em;">
                                    <td style="padding: 15px;">TOTAL DESCONTOS OBRIGATÓRIOS</td>
                                    <td style="text-align: right; padding: 15px;">R$ ${(beneficiario.total_descontos_obrigatorios || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                    <td style="text-align: right; padding: 15px;">100%</td>
                                    <td style="text-align: center; padding: 15px;">⚖️</td>
                                </tr>
                            </tbody>
                        </table>
                        </div>
                        
                        <div style="background: linear-gradient(135deg, #ffebee 0%, #fef5f6 100%); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 5px solid #e74c3c;">
                            <h4 style="color: #e74c3c; margin: 0 0 20px 0; display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 1.5em;">�</span>
                                <span>DESCONTOS EXTRAS (Saídas)</span>
                            </h4>
                            <p style="color: #666; font-size: 0.95em; margin-bottom: 15px;">Descontos opcionais (Empréstimos, Consignados, Planos de Saúde, etc.)</p>
                            <table style="background: white;">
                                <thead>
                                    <tr>
                                        <th style="text-align: left;">Descrição</th>
                                        <th style="text-align: right; width: 120px;">Valor</th>
                                        <th style="text-align: right; width: 100px;">% do Total</th>
                                        <th style="text-align: center; width: 200px;">Impacto Visual</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                if (beneficiario.descontos_extras && beneficiario.descontos_extras.length > 0) {
                    // Ordenar descontos extras por valor (do maior para o menor)
                    const descontosExtrasOrdenados = [...beneficiario.descontos_extras].sort((a, b) => b.valor - a.valor);
                    
                    descontosExtrasOrdenados.forEach(d => {
                        const percentual = beneficiario.total_descontos_extras > 0 ? (d.valor / beneficiario.total_descontos_extras * 100).toFixed(1) : 0;
                        const barWidth = Math.min(percentual, 100);
                        html += `
                                <tr>
                                    <td style="font-weight: 500;">${d.descricao}</td>
                                    <td style="text-align: right; color: #e74c3c; font-weight: 600;">R$ ${d.valor.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                    <td style="text-align: right; font-weight: 600; color: #e74c3c;">${percentual}%</td>
                                    <td>
                                        <div style="background: #ffebee; border-radius: 10px; height: 20px; position: relative; overflow: hidden;">
                                            <div style="background: linear-gradient(90deg, #e74c3c, #e67e73); height: 100%; width: ${barWidth}%; border-radius: 10px; transition: width 0.3s;"></div>
                                        </div>
                                    </td>
                                </tr>
                        `;
                    });
                } else {
                    html += `
                                <tr>
                                    <td colspan="4" style="text-align: center; padding: 20px; color: #999;">Nenhum desconto extra encontrado</td>
                                </tr>
                    `;
                }
                
                html += `
                                <tr style="background: linear-gradient(135deg, #e74c3c 0%, #e67e73 100%); color: white; font-weight: bold; font-size: 1.1em;">
                                    <td style="padding: 15px;">TOTAL DESCONTOS EXTRAS</td>
                                    <td style="text-align: right; padding: 15px;">R$ ${(beneficiario.total_descontos_extras || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                    <td style="text-align: right; padding: 15px;">100%</td>
                                    <td style="text-align: center; padding: 15px;">💳</td>
                                </tr>
                            </tbody>
                        </table>
                        </div>
                        
                        <div style="background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; padding: 30px; border-radius: 15px; margin: 25px 0; box-shadow: 0 8px 20px rgba(0,0,0,0.2);">
                            <h4 style="margin: 0 0 25px 0; font-size: 1.3em; display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 1.3em;">🧮</span>
                                <span>CÁLCULO DO VALOR LÍQUIDO</span>
                            </h4>
                            <div style="display: grid; gap: 15px; font-size: 1.05em;">
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(46, 204, 113, 0.15); border-radius: 8px; border-left: 4px solid #2ecc71;">
                                    <span>💰 Total de Proventos (Entradas):</span>
                                    <div style="text-align: right;">
                                        <div style="font-weight: bold; color: #2ecc71;">R$ ${beneficiario.total_proventos.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                        <div style="font-size: 0.85em; opacity: 0.8; color: #2ecc71;">(100%)</div>
                                    </div>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(255, 152, 0, 0.15); border-radius: 8px; border-left: 4px solid #ff9800;">
                                    <span>⚖️ Descontos Obrigatórios:</span>
                                    <div style="text-align: right;">
                                        <div style="font-weight: bold; color: #ff9800;">- R$ ${(beneficiario.total_descontos_obrigatorios || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                        <div style="font-size: 0.85em; opacity: 0.8; color: #ff9800;">(${beneficiario.total_proventos > 0 ? ((beneficiario.total_descontos_obrigatorios || 0) / beneficiario.total_proventos * 100).toFixed(1) : 0}% dos proventos)</div>
                                    </div>
                                </div>
                                <div style="height: 1px; background: rgba(255,255,255,0.2); margin: 5px 20px;"></div>
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(255,255,255,0.1); border-radius: 8px; font-style: italic;">
                                    <span>= Valor Pós-Descontos Obrigatórios:</span>
                                    <div style="text-align: right;">
                                        <div style="font-weight: bold; color: #3498db;">R$ ${(beneficiario.total_proventos - (beneficiario.total_descontos_obrigatorios || 0)).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                        <div style="font-size: 0.85em; opacity: 0.8; color: #3498db;">(${beneficiario.total_proventos > 0 ? ((beneficiario.total_proventos - (beneficiario.total_descontos_obrigatorios || 0)) / beneficiario.total_proventos * 100).toFixed(1) : 0}% dos proventos)</div>
                                    </div>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(231, 76, 60, 0.15); border-radius: 8px; border-left: 4px solid #e74c3c;">
                                    <span>💳 Descontos Extras:</span>
                                    <div style="text-align: right;">
                                        <div style="font-weight: bold; color: #e74c3c;">- R$ ${(beneficiario.total_descontos_extras || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                        <div style="font-size: 0.85em; opacity: 0.8; color: #e74c3c;">(${(beneficiario.total_proventos - (beneficiario.total_descontos_obrigatorios || 0)) > 0 ? ((beneficiario.total_descontos_extras || 0) / (beneficiario.total_proventos - (beneficiario.total_descontos_obrigatorios || 0)) * 100).toFixed(1) : 0}% pós-obrigatórios)</div>
                                    </div>
                                </div>
                                <div style="height: 2px; background: rgba(255,255,255,0.4); margin: 15px 0;"></div>
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 18px; background: rgba(241, 196, 15, 0.2); border-radius: 10px; font-size: 1.25em; border: 2px solid #f1c40f;">
                                    <span style="font-weight: bold;">💵 VALOR LÍQUIDO A RECEBER:</span>
                                    <div style="text-align: right;">
                                        <div style="font-weight: bold; color: #f1c40f; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">R$ ${beneficiario.liquido.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                        <div style="font-size: 0.75em; opacity: 0.9; color: #f1c40f; margin-top: 5px;">(${beneficiario.total_proventos > 0 ? (beneficiario.liquido / beneficiario.total_proventos * 100).toFixed(1) : 0}% dos proventos)</div>
                                    </div>
                                </div>
                                
                                ${(() => {
                                    const proventos = beneficiario.total_proventos;
                                    const descontosObrig = beneficiario.total_descontos_obrigatorios || 0;
                                    const descontosExtras = beneficiario.total_descontos_extras || 0;
                                    
                                    const baseCalculo = proventos - descontosObrig;
                                    const percentualUtilizado = baseCalculo > 0 ? (descontosExtras / baseCalculo * 100) : 0;
                                    
                                    let status, cor, icone, alerta;
                                    if (percentualUtilizado === 0) {
                                        status = 'EXCELENTE';
                                        cor = '#27ae60';
                                        icone = '✅';
                                        alerta = 'Margem consignável 100% disponível';
                                    } else if (percentualUtilizado < 20) {
                                        status = 'BOM';
                                        cor = '#2ecc71';
                                        icone = '✔️';
                                        alerta = 'Margem consignável saudável, uso consciente';
                                    } else if (percentualUtilizado < 35) {
                                        status = 'ATENÇÃO';
                                        cor = '#f39c12';
                                        icone = '⚠️';
                                        alerta = 'Próximo do limite de 35% da margem consignável';
                                    } else {
                                        status = 'CRÍTICO';
                                        cor = '#e74c3c';
                                        icone = '🚨';
                                        alerta = 'ACIMA DO LIMITE LEGAL DE 35%';
                                    }
                                    
                                    return `
                                <div style="height: 2px; background: rgba(255,255,255,0.4); margin: 20px 0;"></div>
                                <div style="background: ${cor}; padding: 20px; border-radius: 10px; border: 2px solid rgba(255,255,255,0.3); margin-top: 20px;">
                                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;">
                                        <div>
                                            <div style="font-size: 1.2em; font-weight: bold; margin-bottom: 5px; color: white;">${icone} STATUS: ${status}</div>
                                            <div style="font-size: 0.95em; opacity: 0.95; color: white;">${alerta}</div>
                                        </div>
                                        <div style="text-align: right;">
                                            <div style="font-size: 2.5em; font-weight: bold; line-height: 1; color: white;">${percentualUtilizado.toFixed(1)}%</div>
                                            <div style="font-size: 0.85em; opacity: 0.9; color: white;">da margem utilizada</div>
                                        </div>
                                    </div>
                                    <div style="background: rgba(255,255,255,0.3); height: 25px; border-radius: 12px; overflow: hidden; position: relative;">
                                        <div style="background: rgba(255,255,255,0.9); height: 100%; width: ${Math.min(percentualUtilizado, 100)}%; transition: width 0.5s; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; font-weight: bold; color: #2c3e50;">
                                            ${percentualUtilizado > 10 ? percentualUtilizado.toFixed(1) + '%' : ''}
                                        </div>
                                        ${percentualUtilizado <= 10 ? `<div style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%); font-weight: bold;">${percentualUtilizado.toFixed(1)}%</div>` : ''}
                                    </div>
                                </div>
                                    `;
                                })()}
                            </div>
                        </div>
                    </div>
                `;
                
                // ==================== SEÇÃO DE AJUSTE DE MARGEM ====================
                const proventos = beneficiario.total_proventos;
                const descontosObrig = beneficiario.total_descontos_obrigatorios || 0;
                const descontosExtras = beneficiario.total_descontos_extras || 0;
                const baseCalculo = proventos - descontosObrig;
                const percentualAtual = baseCalculo > 0 ? (descontosExtras / baseCalculo * 100) : 0;
                
                // Só mostrar se estiver acima de 35%
                if (percentualAtual > 35) {
                    const limiteIdeal = baseCalculo * 0.35;
                    const valorAReduzir = descontosExtras - limiteIdeal;
                    
                    // Prioridades de exclusão
                    const prioridade1 = [
                        'BIG CARD - CARTÃO BENEFÍCIO', 'BMG CARTÃO CREDITO',
                        'EAGLE - CARTÃO BENEFÍCIO', 'EAGLE - CARTÃO CREDITO',
                        'MTXCARD - CARTÃO BENEFÍCIO', 'NIO CARTÃO CREDITO',
                        'SUDACRED - CARTÃO BENEFÍCIO'
                    ];
                    
                    const prioridade2 = [
                        'CONSIGNAÇÃO B.BRASIL', 'CONSIGNAÇÃO BANCOOB', 'CONSIGNAÇÃO BRADESCO',
                        'CONSIGNACAO CEF', 'CONSIGNAÇÃO DAYCOVAL', 'CONSIGNAÇÃO EAGLE',
                        'CONSIGNAÇÃO EAGLE - RESCISÃO', 'CONSIGNAÇÃO SICOOB - RESCISÃO',
                        'CONSIGNAÇÃO SICOOB SERVIDOR', 'CONSIGNAÇÃO SICREDI',
                        'CONSIGNAÇÃO SUDACRED', 'CONSIGNAÇÃO SUDACRED - RESCISÃO',
                        'CONTA CAPITAL - CREDLEGIS', 'SICOOB'
                    ];
                    
                    const prioridade3 = ['APRALE', 'ASLEM', 'SINDAL', 'UNALE'];
                    
                    const prioridade4 = [
                        'GEAP SAÚDE - COOPARTICIPAÇÃO', 'GEAP SAÚDE - MENSALIDADE',
                        'MT SAUDE', 'UNIMED - CO PARTICIPACAO', 'UNIMED - MENSALIDADE'
                    ];
                    
                    // Função para verificar se um desconto está em uma lista
                    const estaEmLista = (descricao, lista) => {
                        const descUpper = descricao.toUpperCase().trim();
                        return lista.some(item => {
                            const itemUpper = item.toUpperCase().trim();
                            // Verifica correspondência exata ou se contém o item completo
                            return descUpper === itemUpper || 
                                   descUpper.includes(itemUpper) ||
                                   itemUpper.includes(descUpper);
                        });
                    };
                    
                    // Simular eliminações
                    let descontosParaEliminar = [];
                    let totalEliminado = 0;
                    
                    // Função para encontrar melhor combinação dentro de um grupo
                    const encontrarMelhorCombinacao = (descontos, totalJaEliminado) => {
                        if (descontos.length === 0) return [];
                        
                        let melhorCombinacao = [];
                        let melhorPercentual = percentualAtual;
                        let melhorDistancia = Infinity;
                        
                        // Limitar combinações se houver muitos itens (performance)
                        const maxCombinacoes = Math.min(Math.pow(2, descontos.length), 65536);
                        
                        for (let i = 1; i < maxCombinacoes; i++) { // Começa em 1 para evitar combinação vazia
                            let somaTemp = totalJaEliminado;
                            let combinacaoTemp = [];
                            
                            for (let j = 0; j < descontos.length && j < 16; j++) {
                                if (i & (1 << j)) {
                                    somaTemp += descontos[j].valor;
                                    combinacaoTemp.push(descontos[j]);
                                }
                            }
                            
                            const novoDescontoTotal = descontosExtras - somaTemp;
                            const novoPercentual = baseCalculo > 0 ? (novoDescontoTotal / baseCalculo * 100) : 0;
                            
                            // Aceita se <= 35% e é o mais próximo de 35%
                            if (novoPercentual <= 35) {
                                const distancia = 35 - novoPercentual;
                                if (distancia < melhorDistancia) {
                                    melhorDistancia = distancia;
                                    melhorCombinacao = [...combinacaoTemp];
                                    melhorPercentual = novoPercentual;
                                }
                            }
                        }
                        
                        // Se nenhuma combinação atingiu <= 35%, elimina todos do grupo para tentar no próximo
                        if (melhorCombinacao.length === 0 && descontos.length > 0) {
                            return descontos;
                        }
                        
                        return melhorCombinacao;
                    };
                    
                    // ETAPA 1: CARTÕES - ELIMINAÇÃO OBRIGATÓRIA (todos)
                    const cartoesParaEliminar = beneficiario.descontos_extras.filter(desc => 
                        estaEmLista(desc.descricao, prioridade1)
                    );
                    
                    cartoesParaEliminar.forEach(desc => {
                        descontosParaEliminar.push({
                            descricao: desc.descricao,
                            valor: desc.valor,
                            prioridade: 'Cartões (Prioridade Máxima)'
                        });
                        totalEliminado += desc.valor;
                    });
                    
                    // Verificar percentual após eliminar cartões
                    let percentualAtualCalc = baseCalculo > 0 ? ((descontosExtras - totalEliminado) / baseCalculo * 100) : 0;
                    
                    // ETAPA 2: CONSIGNAÇÕES (se ainda > 35%)
                    if (percentualAtualCalc > 35) {
                        const consignacoesDisponiveis = beneficiario.descontos_extras.filter(desc => 
                            estaEmLista(desc.descricao, prioridade2) && 
                            !descontosParaEliminar.some(e => e.descricao === desc.descricao)
                        );
                        
                        const melhorConsignacoes = encontrarMelhorCombinacao(consignacoesDisponiveis, totalEliminado);
                        melhorConsignacoes.forEach(desc => {
                            descontosParaEliminar.push({
                                descricao: desc.descricao,
                                valor: desc.valor,
                                prioridade: 'Consignações'
                            });
                            totalEliminado += desc.valor;
                        });
                        
                        percentualAtualCalc = baseCalculo > 0 ? ((descontosExtras - totalEliminado) / baseCalculo * 100) : 0;
                    }
                    
                    // ETAPA 3: ASSOCIAÇÕES (se ainda > 35%)
                    if (percentualAtualCalc > 35) {
                        const associacoesDisponiveis = beneficiario.descontos_extras.filter(desc => 
                            estaEmLista(desc.descricao, prioridade3) && 
                            !descontosParaEliminar.some(e => e.descricao === desc.descricao)
                        );
                        
                        const melhorAssociacoes = encontrarMelhorCombinacao(associacoesDisponiveis, totalEliminado);
                        melhorAssociacoes.forEach(desc => {
                            descontosParaEliminar.push({
                                descricao: desc.descricao,
                                valor: desc.valor,
                                prioridade: 'Associações'
                            });
                            totalEliminado += desc.valor;
                        });
                        
                        percentualAtualCalc = baseCalculo > 0 ? ((descontosExtras - totalEliminado) / baseCalculo * 100) : 0;
                    }
                    
                    // ETAPA 4: PLANOS DE SAÚDE - MEDIDA EXTREMA (se ainda > 35%)
                    if (percentualAtualCalc > 35) {
                        const saudeDisponiveis = beneficiario.descontos_extras.filter(desc => 
                            estaEmLista(desc.descricao, prioridade4) && 
                            !descontosParaEliminar.some(e => e.descricao === desc.descricao)
                        );
                        
                        const melhorSaude = encontrarMelhorCombinacao(saudeDisponiveis, totalEliminado);
                        melhorSaude.forEach(desc => {
                            descontosParaEliminar.push({
                                descricao: desc.descricao,
                                valor: desc.valor,
                                prioridade: 'Planos de Saúde (Medida Extrema)'
                            });
                            totalEliminado += desc.valor;
                        });
                    }
                    
                    const novoTotalExtras = descontosExtras - totalEliminado;
                    const novoPercentual = baseCalculo > 0 ? (novoTotalExtras / baseCalculo * 100) : 0;
                    const novoLiquido = proventos - descontosObrig - novoTotalExtras;
                    
                    html += `
                        <div style="background: linear-gradient(135deg, #e8f5e9 0%, #fff9e6 100%); padding: 30px; border-radius: 12px; margin: 25px 0; border: 3px solid #f39c12; box-shadow: 0 4px 15px rgba(243, 156, 18, 0.3);">
                            <h4 style="color: #e67e22; margin: 0 0 20px 0; display: flex; align-items: center; gap: 10px; font-size: 1.3em;">
                                <span style="font-size: 1.5em;">⚖️</span>
                                <span>AJUSTE DE MARGEM CONSIGNÁVEL</span>
                            </h4>
                            
                            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #f39c12;">
                                <h5 style="color: #e67e22; margin: 0 0 15px 0;">📊 Situação Atual:</h5>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; color: #856404;">
                                    <div>
                                        <strong>Margem Consignável:</strong> R$ ${baseCalculo.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                                    </div>
                                    <div>
                                        <strong>Percentual Comprometido:</strong> <span style="color: #e74c3c; font-weight: bold;">${percentualAtual.toFixed(2)}%</span>
                                    </div>
                                    <div>
                                        <strong>Limite Ideal (35%):</strong> R$ ${limiteIdeal.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                                    </div>
                                    <div>
                                        <strong style="color: #e74c3c;">Valor a Reduzir:</strong> <span style="color: #e74c3c; font-weight: bold;">R$ ${valorAReduzir.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div style="background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                                <h5 style="color: #e67e22; margin: 0 0 15px 0;">🎯 Descontos Recomendados para Eliminação:</h5>
                                <table style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="background: #f8f9fa;">
                                            <th style="text-align: left; padding: 12px; border-bottom: 2px solid #dee2e6; color: #495057; font-weight: 700;">Descrição</th>
                                            <th style="text-align: center; padding: 12px; border-bottom: 2px solid #dee2e6; color: #495057; font-weight: 700;">Categoria</th>
                                            <th style="text-align: right; padding: 12px; border-bottom: 2px solid #dee2e6; color: #495057; font-weight: 700;">Valor</th>
                                            <th style="text-align: right; padding: 12px; border-bottom: 2px solid #dee2e6; color: #495057; font-weight: 700;">Percentual Ajustado</th>
                                            <th style="text-align: right; padding: 12px; border-bottom: 2px solid #dee2e6; color: #495057; font-weight: 700;">Resta Eliminar</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                    `;
                    
                    let acumuladoEliminado = 0;
                    descontosParaEliminar.forEach((desc, idx) => {
                        acumuladoEliminado += desc.valor;
                        const novoDescontoAposEste = descontosExtras - acumuladoEliminado;
                        const percentualAjustado = baseCalculo > 0 ? (novoDescontoAposEste / baseCalculo * 100) : 0;
                        const restaEliminar = Math.max(0, novoDescontoAposEste - limiteIdeal);
                        
                        let corCategoria = '#dc3545';
                        if (desc.prioridade.includes('Consignações')) corCategoria = '#fd7e14';
                        if (desc.prioridade.includes('Associações')) corCategoria = '#ffc107';
                        if (desc.prioridade.includes('Saúde')) corCategoria = '#17a2b8';
                        
                        html += `
                                        <tr style="border-bottom: 1px solid #dee2e6; ${idx % 2 === 0 ? 'background: #f8f9fa;' : ''}">
                                            <td style="padding: 12px;">${desc.descricao}</td>
                                            <td style="text-align: center; padding: 12px;">
                                                <span style="background: ${corCategoria}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">
                                                    ${desc.prioridade}
                                                </span>
                                            </td>
                                            <td style="text-align: right; padding: 12px; font-weight: 600; color: #dc3545;">
                                                R$ ${desc.valor.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                                            </td>
                                            <td style="text-align: right; padding: 12px; font-weight: 600; color: ${percentualAjustado <= 35 ? '#28a745' : '#ffc107'};">
                                                ${percentualAjustado.toFixed(2)}%
                                            </td>
                                            <td style="text-align: right; padding: 12px; font-weight: 600; color: ${restaEliminar === 0 ? '#28a745' : '#dc3545'};">
                                                ${restaEliminar === 0 ? '✅ Meta atingida' : 'R$ ' + restaEliminar.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                                            </td>
                                        </tr>
                        `;
                    });
                    
                    html += `
                                    </tbody>
                                    <tfoot>
                                        <tr style="background: #f8f9fa; border-top: 3px solid #dee2e6;">
                                            <td style="padding: 15px; color: #495057; font-weight: 700; font-size: 1.1em;" colspan="2">TOTAL A ELIMINAR</td>
                                            <td style="text-align: right; padding: 15px; color: #495057; font-weight: 700; font-size: 1.1em;">R$ ${totalEliminado.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                            <td colspan="2"></td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>
                            
                            <div style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); padding: 25px; border-radius: 10px; border: 2px solid #28a745;">
                                <h5 style="color: #155724; margin: 0 0 20px 0; font-size: 1.2em;">✅ Situação Após Ajustes:</h5>
                                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 20px;">
                                    <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
                                        <div style="color: #6c757d; font-size: 0.9em; margin-bottom: 5px;">Novo Total Descontos Extras</div>
                                        <div style="font-size: 1.5em; font-weight: bold; color: #28a745;">R$ ${novoTotalExtras.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                    </div>
                                    <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
                                        <div style="color: #6c757d; font-size: 0.9em; margin-bottom: 5px;">Novo Percentual da Margem</div>
                                        <div style="font-size: 1.5em; font-weight: bold; color: ${novoPercentual <= 35 ? '#28a745' : '#ffc107'};">${novoPercentual.toFixed(2)}%</div>
                                    </div>
                                    <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
                                        <div style="color: #6c757d; font-size: 0.9em; margin-bottom: 5px;">Novo Valor Líquido</div>
                                        <div style="font-size: 1.5em; font-weight: bold; color: #155724;">R$ ${novoLiquido.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                    </div>
                                    <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
                                        <div style="color: #6c757d; font-size: 0.9em; margin-bottom: 5px;">Ganho Líquido Mensal</div>
                                        <div style="font-size: 1.5em; font-weight: bold; color: #155724;">+ R$ ${totalEliminado.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                    </div>
                                </div>
                                
                                <div style="background: rgba(40, 167, 69, 0.2); padding: 15px; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 1.1em; color: #155724; font-weight: 600;">
                                        ${novoPercentual <= 35 
                                            ? `🎉 A nova margem, após os ajustes, será de ${novoPercentual.toFixed(2)}%, adequando-o ao limite de 35%!` 
                                            : '⚠️ Atenção: Ainda acima de 35%. Considere revisão adicional dos contratos.'}
                                    </div>
                                </div>
                            </div>
                            
                            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #ffc107;">
                                <strong style="color: #856404;">💡 Recomendação:</strong>
                                <p style="color: #856404; margin: 10px 0 0 0; line-height: 1.6;">
                                    Entre em contato com o servidor para orientar sobre a necessidade de renegociação ou cancelamento dos contratos listados acima. 
                                    Priorize sempre a eliminação de cartões de crédito consignados antes de outras modalidades.
                                </p>
                            </div>
                        </div>
                    `;
                }
            
            resultado.innerHTML = html;
        }
    </script>
</body>
</html>
"""
    
    return html

def exibir_progresso(atual, total, largura=50):
    """Exibe uma barra de progresso no console"""
    percentual = (atual / total) * 100
    preenchido = int(largura * atual / total)
    barra = '█' * preenchido + '░' * (largura - preenchido)
    print(f'\r[{barra}] {atual}/{total} ({percentual:.1f}%)', end='', flush=True)

def gerar_relatorio_estatisticas(dados_todas_folhas):
    """Gera estatísticas do processamento"""
    total = len(dados_todas_folhas)
    com_sucesso = len([d for d in dados_todas_folhas if d['nome'] and not d['erro_processamento']])
    com_erro = len([d for d in dados_todas_folhas if d['erro_processamento']])
    sem_dados = len([d for d in dados_todas_folhas if not d['nome'] and not d['erro_processamento']])
    
    total_proventos = sum(d['total_proventos'] for d in dados_todas_folhas)
    total_descontos_obrig = sum(d['total_descontos_obrigatorios'] for d in dados_todas_folhas)
    total_descontos_extras = sum(d['total_descontos_extras'] for d in dados_todas_folhas)
    total_liquido = sum(d['liquido'] for d in dados_todas_folhas)
    
    return {
        'total': total,
        'com_sucesso': com_sucesso,
        'com_erro': com_erro,
        'sem_dados': sem_dados,
        'total_proventos': total_proventos,
        'total_descontos_obrigatorios': total_descontos_obrig,
        'total_descontos_extras': total_descontos_extras,
        'total_liquido': total_liquido
    }

def salvar_log_erros(dados_todas_folhas, caminho_pasta):
    """Salva um arquivo de log com os erros encontrados"""
    erros = [d for d in dados_todas_folhas if d['erro_processamento'] or (not d['nome'] and d['arquivo_origem'])]
    
    if erros:
        # Salvar log na pasta Folha (pasta raiz)
        pasta_raiz = os.path.dirname(caminho_pasta)
        caminho_log = os.path.join(pasta_raiz, "log_erros_processamento.txt")
        with open(caminho_log, 'w', encoding='utf-8') as f:
            f.write(f"LOG DE ERROS - Processamento de Folhas de Pagamento\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Total de arquivos com problemas: {len(erros)}\n")
            f.write("="*80 + "\n\n")
            
            for i, d in enumerate(erros, 1):
                f.write(f"{i}. Arquivo: {d['arquivo_origem']}\n")
                if d['erro_processamento']:
                    f.write(f"   Erro: {d['erro_processamento']}\n")
                else:
                    f.write(f"   Problema: Não foi possível extrair dados básicos (nome, CPF)\n")
                f.write(f"   Matrícula encontrada: {d['matricula'] if d['matricula'] else 'N/A'}\n")
                f.write("\n")
        
        print(f"\n📋 Log de erros salvo em: {caminho_log}")

# ========== PROCESSAMENTO PRINCIPAL ==========

print("="*80)
print("🚀 SISTEMA DE ANÁLISE DE FOLHAS DE PAGAMENTO")
print("="*80)

# Configurações
caminho_pasta = r"c:\Users\41870\Desktop\VSCODE\Folha_SGP\Download_Folha"

# Buscar todos os PDFs
arquivos_pdf = [f for f in os.listdir(caminho_pasta) if f.endswith('.pdf') and 'Logo' not in f]

print(f"\n� Pasta: {caminho_pasta}")
print(f"📄 Arquivos PDF encontrados: {len(arquivos_pdf)}")

if len(arquivos_pdf) == 0:
    print("\n⚠️  Nenhum arquivo PDF encontrado na pasta!")
    exit()

print("\n" + "="*80)
print("📊 PROCESSANDO FOLHAS DE PAGAMENTO...")
print("="*80 + "\n")

dados_todas_folhas = []
inicio = datetime.now()

# Processar cada PDF
for arquivo in arquivos_pdf:
    caminho_completo = os.path.join(caminho_pasta, arquivo)
    
    # Verificar quantas páginas o PDF tem
    try:
        with open(caminho_completo, 'rb') as f:
            leitor = PyPDF2.PdfReader(f)
            num_paginas = len(leitor.pages)
        
        print(f"📄 Arquivo: {arquivo}")
        print(f"   Total de páginas: {num_paginas}")
        print(f"   Processando cada holerite...\n")
        
        # Processar cada página individualmente e consolidar continuações
        pagina_atual = 0
        while pagina_atual < num_paginas:
            # Atualizar barra de progresso
            exibir_progresso(pagina_atual + 1, num_paginas)
            
            # Processar página atual
            dados_pagina1 = extrair_dados_pdf(caminho_completo, numero_pagina=pagina_atual)
            
            # Verificar se a página está vazia (última página ou página sem dados)
            # Página vazia: sem nome, sem CPF, sem eventos
            pagina_vazia = (not dados_pagina1['nome'] and 
                           not dados_pagina1['cpf'] and 
                           len(dados_pagina1['proventos']) == 0 and
                           len(dados_pagina1['descontos_obrigatorios']) == 0 and
                           len(dados_pagina1['descontos_extras']) == 0)
            
            # Se página vazia, pular e não adicionar aos dados
            if pagina_vazia:
                pagina_atual += 1
                continue
            
            # Verificar se próxima página é continuação do mesmo beneficiário
            if pagina_atual + 1 < num_paginas:
                dados_pagina2 = extrair_dados_pdf(caminho_completo, numero_pagina=pagina_atual + 1)
                
                # Se a próxima página tem o mesmo CPF, é continuação
                if (dados_pagina2['cpf'] == dados_pagina1['cpf'] and 
                    dados_pagina2['cpf'] != '' and
                    dados_pagina1['cpf'] != ''):
                    
                    # Consolidar eventos da página 2 na página 1
                    dados_pagina1['proventos'].extend(dados_pagina2['proventos'])
                    dados_pagina1['descontos_obrigatorios'].extend(dados_pagina2['descontos_obrigatorios'])
                    dados_pagina1['descontos_extras'].extend(dados_pagina2['descontos_extras'])
                    
                    # Atualizar totais
                    dados_pagina1['total_proventos'] += dados_pagina2['total_proventos']
                    dados_pagina1['total_descontos_obrigatorios'] += dados_pagina2['total_descontos_obrigatorios']
                    dados_pagina1['total_descontos_extras'] += dados_pagina2['total_descontos_extras']
                    dados_pagina1['total_descontos'] += dados_pagina2['total_descontos']
                    dados_pagina1['liquido'] = dados_pagina1['total_proventos'] - dados_pagina1['total_descontos']
                    
                    # Atualizar origem do arquivo para indicar que usou 2 páginas
                    dados_pagina1['arquivo_origem'] = f"{arquivo} (pág. {pagina_atual+1}-{pagina_atual+2})"
                    
                    # Pular a próxima página (já foi consolidada)
                    pagina_atual += 2
                    exibir_progresso(pagina_atual, num_paginas)  # Atualizar progresso da página pulada
                else:
                    # Não é continuação, processar normalmente
                    pagina_atual += 1
            else:
                # Última página, não tem continuação
                pagina_atual += 1
            
            # Adicionar dados consolidados
            dados_todas_folhas.append(dados_pagina1)
    
    except Exception as e:
        print(f"\n❌ Erro ao processar arquivo {arquivo}: {str(e)}")
        continue

print("\n\n" + "="*80)
print("📈 ESTATÍSTICAS DO PROCESSAMENTO")
print("="*80)

# Gerar estatísticas
stats = gerar_relatorio_estatisticas(dados_todas_folhas)

print(f"\n✅ Processados com sucesso: {stats['com_sucesso']}/{stats['total']}")
print(f"⚠️  Sem dados extraídos: {stats['sem_dados']}/{stats['total']}")
print(f"❌ Com erros: {stats['com_erro']}/{stats['total']}")

print(f"\n💰 Total de Proventos: R$ {formatar_moeda_br(stats['total_proventos'])}")
print(f"⚖️  Total Descontos Obrigatórios: R$ {formatar_moeda_br(stats['total_descontos_obrigatorios'])}")
print(f"💳 Total Descontos Extras: R$ {formatar_moeda_br(stats['total_descontos_extras'])}")
print(f"💵 Total Líquido: R$ {formatar_moeda_br(stats['total_liquido'])}")

tempo_decorrido = (datetime.now() - inicio).total_seconds()
print(f"\n⏱️  Tempo de processamento: {tempo_decorrido:.2f} segundos")
if len(dados_todas_folhas) > 0:
    print(f"⚡ Velocidade: {len(dados_todas_folhas)/tempo_decorrido:.1f} holerites/segundo")

# Salvar log de erros se houver
salvar_log_erros(dados_todas_folhas, caminho_pasta)

# Gerar HTML
print("\n" + "="*80)
print("📝 GERANDO RELATÓRIO HTML...")
print("="*80 + "\n")

html_final = gerar_html_relatorio(dados_todas_folhas)

# Salvar arquivos na pasta Folha (pasta raiz)
pasta_raiz = os.path.dirname(caminho_pasta)

# Salvar arquivo HTML
caminho_saida = os.path.join(pasta_raiz, "Relatorio_Folha_Pagamento.html")
with open(caminho_saida, 'w', encoding='utf-8') as f:
    f.write(html_final)

print(f"✅ Relatório HTML gerado com sucesso!")
print(f"📁 Arquivo salvo em: {caminho_saida}")

# Salvar dados em JSON para backup/análise futura
caminho_json = os.path.join(pasta_raiz, "dados_folhas_backup.json")
with open(caminho_json, 'w', encoding='utf-8') as f:
    json.dump(dados_todas_folhas, f, ensure_ascii=False, indent=2)
print(f"💾 Backup dos dados salvo em: {caminho_json}")

print("\n" + "="*80)
print("🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
print("="*80)
print("\n🌐 Abra o arquivo HTML no navegador para visualizar o relatório!")
print(f"   → {caminho_saida}\n")

# ============================================
# SINCRONIZAÇÃO AUTOMÁTICA COM GITHUB
# ============================================
print("="*80)
print("🔄 SINCRONIZAÇÃO COM GITHUB")
print("="*80)

try:
    import shutil
    import subprocess
    
    # Copiar para index.html
    caminho_index = os.path.join(pasta_raiz, "index.html")
    shutil.copy2(caminho_saida, caminho_index)
    print(f"✅ Arquivo copiado para: index.html")
    
    # Verificar se Git está disponível
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True, cwd=pasta_raiz)
    except:
        print("⚠️  Git não encontrado. Arquivo index.html criado, mas não foi sincronizado.")
        print("💡 Para enviar ao GitHub:")
        print("   1. Abra o terminal no VS Code")
        print("   2. Execute: git add index.html")
        print("   3. Execute: git commit -m 'Atualização'")
        print("   4. Execute: git push origin main")
        print("\n")
        import sys
        sys.exit(0)
    
    # Verificar se há repositório Git
    result = subprocess.run(['git', 'status'], capture_output=True, text=True, cwd=pasta_raiz)
    if result.returncode != 0:
        print("⚠️  Esta pasta não é um repositório Git.")
        print("💡 Execute: git init")
        print("\n")
        import sys
        sys.exit(0)
    
    # Perguntar se deseja fazer push
    print("\n📤 Deseja enviar para o GitHub agora?")
    resposta = input("   Digite 's' para SIM ou qualquer outra tecla para NÃO: ").strip().lower()
    
    if resposta == 's':
        # Adicionar ao Git
        subprocess.run(['git', 'add', 'index.html'], cwd=pasta_raiz, check=True)
        print("✅ Arquivo adicionado ao Git")
        
        # Commit
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        result = subprocess.run(
            ['git', 'commit', '-m', f'Atualização automática - {data_hora}'],
            capture_output=True,
            text=True,
            cwd=pasta_raiz
        )
        
        if "nothing to commit" in result.stdout:
            print("ℹ️  Nenhuma alteração para enviar (arquivo já está atualizado)")
        else:
            print("✅ Commit realizado")
            
            # Pull antes do Push (para sincronizar com remoto)
            print("🔄 Sincronizando com repositório remoto...")
            result_pull = subprocess.run(
                ['git', 'pull', '--rebase', 'origin', 'main'],
                capture_output=True,
                text=True,
                cwd=pasta_raiz
            )
            
            if result_pull.returncode == 0:
                print("✅ Sincronizado com repositório remoto")
            else:
                # Se der erro no pull, tenta sem rebase
                result_pull = subprocess.run(
                    ['git', 'pull', 'origin', 'main'],
                    capture_output=True,
                    text=True,
                    cwd=pasta_raiz
                )
                if result_pull.returncode == 0:
                    print("✅ Sincronizado com repositório remoto")
            
            # Push
            print("📤 Enviando para GitHub...")
            result = subprocess.run(
                ['git', 'push', 'origin', 'main'],
                capture_output=True,
                text=True,
                cwd=pasta_raiz
            )
            
            if result.returncode == 0:
                print("🚀 Enviado para GitHub com sucesso!")
                print("🌐 Disponível em: https://pablogusen.github.io/folha_sgp/")
                print("⏱️  Aguarde 1-2 minutos para o GitHub Pages atualizar.")
            else:
                print("⚠️  Erro ao enviar para GitHub:")
                print(result.stderr)
                print("\n💡 Tente manualmente:")
                print("   git push origin main")
    else:
        print("⏸️  Sincronização cancelada.")
        print("💡 Para enviar depois, execute no terminal:")
        print("   git add index.html")
        print("   git commit -m 'Atualização'")
        print("   git push origin main")
        
except KeyboardInterrupt:
    print("\n\n⏸️  Sincronização cancelada pelo usuário.")
except Exception as e:
    print(f"\n⚠️  Erro na sincronização: {e}")
    print("\n💡 Arquivo index.html foi criado. Para enviar manualmente:")
    print("   git add index.html")
    print("   git commit -m 'Atualização'")
    print("   git push origin main")

print("\n")
