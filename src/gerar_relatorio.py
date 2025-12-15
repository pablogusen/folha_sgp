import PyPDF2
import re
import json
import os
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd

# Configurar logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def detectar_competencias_disponiveis():
    """Detecta competências disponíveis com holerites"""
    caminho_base = Path(__file__).parent.parent
    pasta_competencias = caminho_base / "data" / "competencias"
    
    competencias = []
    for item in pasta_competencias.iterdir():
        if item.is_dir() and re.match(r'^\d{4}-\d{2}$', item.name):
            pasta_holerites = item / "holerites"
            if pasta_holerites.exists():
                pdfs = list(pasta_holerites.glob('*.pdf'))
                if pdfs:
                    competencias.append({
                        'pasta': item.name,
                        'caminho': pasta_holerites,
                        'quantidade_pdfs': len(pdfs)
                    })
    
    return sorted(competencias, key=lambda x: x['pasta'], reverse=True)

def selecionar_competencia():
    """Permite usuário selecionar competência ou usa mais recente"""
    competencias = detectar_competencias_disponiveis()
    
    if not competencias:
        logger.error("❌ Nenhuma competência com holerites encontrada!")
        logger.info("💡 Coloque os PDFs em: data/competencias/AAAA-MM/holerites/")
        return None
    
    logger.info("\n📅 Competências disponíveis:")
    for i, comp in enumerate(competencias, 1):
        logger.info(f"   {i}. {comp['pasta']} ({comp['quantidade_pdfs']} holerites)")
    
    # Usar mais recente por padrão
    competencia_selecionada = competencias[0]
    logger.info(f"\n✅ Usando competência mais recente: {competencia_selecionada['pasta']}")
    
    return competencia_selecionada

# Carregar mapeamento de eventos da planilha Descricao_Comp_Rend.xlsx
def carregar_mapeamento_eventos():
    """
    Carrega o mapeamento de código/descrição → tipo de evento
    da planilha Descricao_Comp_Rend.xlsx
    """
    try:
        caminho_planilha = Path(__file__).parent.parent / 'data' / 'parametros' / 'Descricao_Comp_Rend.xlsx'
        df_eventos = pd.read_excel(caminho_planilha, sheet_name='Composição de Rendimentos')
        
        mapeamento = {}
        for _, row in df_eventos.iterrows():
            codigo = str(row['CÓDIGO']).strip()
            descricao = str(row['DESCRIÇÃO EVENTOS']).strip().upper()
            tipo = str(row['TIPO']).strip()
            mapeamento[(codigo, descricao)] = tipo
        
        return mapeamento
    except Exception as e:
        print(f"⚠️  Aviso: Não foi possível carregar o mapeamento de eventos: {e}")
        print("   O sistema usará a classificação padrão.")
        return {}

def carregar_ordem_eliminacao():
    """
    Carrega a ordem de eliminação da planilha Descricao_Comp_Rend.xlsx
    Retorna dicionário: {descricao_normalizada: ordem_numero}
    """
    try:
        caminho_planilha = Path(__file__).parent.parent / 'data' / 'parametros' / 'Descricao_Comp_Rend.xlsx'
        df_ordem = pd.read_excel(caminho_planilha, sheet_name='Ordem de Eliminação')
        
        # Criar dicionário de prioridades
        prioridades = {}
        for _, row in df_ordem.iterrows():
            descricao = str(row['DESCRIÇÃO EVENTOS']).strip().upper()
            ordem_texto = str(row['ORDEM']).strip()
            
            # Extrair número da ordem (1, 2, 3 ou 4)
            if '1 -' in ordem_texto:
                ordem_num = 1
            elif '2 -' in ordem_texto:
                ordem_num = 2
            elif '3 -' in ordem_texto:
                ordem_num = 3
            elif '4 -' in ordem_texto:
                ordem_num = 4
            else:
                ordem_num = 5  # Fallback para desconhecidos
            
            prioridades[descricao] = {
                'ordem': ordem_num,
                'nome_ordem': ordem_texto
            }
        
        return prioridades
    except Exception as e:
        print(f"⚠️  Aviso: Não foi possível carregar ordem de eliminação: {e}")
        return {}

# Carregar mapeamentos globais
MAPEAMENTO_EVENTOS = carregar_mapeamento_eventos()
ORDEM_ELIMINACAO = carregar_ordem_eliminacao()

# Lista global para rastrear eventos não mapeados
EVENTOS_NAO_MAPEADOS = set()  # Usar set para evitar duplicatas

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
        'eventos_informativos': [],  # NOVO: eventos que não entram no cálculo da margem
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
                        
                        # === NOVA CLASSIFICAÇÃO BASEADA NA PLANILHA Descricao_Comp_Rend.xlsx ===
                        descricao_upper = descricao.upper()
                        
                        # Buscar tipo do evento no mapeamento
                        tipo_evento = MAPEAMENTO_EVENTOS.get((codigo, descricao_upper), None)
                        
                        # Se não encontrou, registrar como não mapeado
                        if tipo_evento is None:
                            EVENTOS_NAO_MAPEADOS.add((codigo, descricao_upper, descricao))
                        
                        evento_obj = {
                            'descricao': descricao,
                            'valor': valor_evento,
                            'base_calculo': base_calculo,
                            'referencia': referencia,
                            'codigo': codigo
                        }
                        
                        # Classificar baseado no tipo da planilha
                        if tipo_evento == 'Provento':
                            dados['proventos'].append(evento_obj)
                            dados['total_proventos'] += valor_evento
                        elif tipo_evento == 'Desconto Compulsório (obrigatório)':
                            dados['descontos_obrigatorios'].append(evento_obj)
                            dados['total_descontos_obrigatorios'] += valor_evento
                            dados['total_descontos'] += valor_evento
                        elif tipo_evento == 'Desconto Facultativo (extra)':
                            dados['descontos_extras'].append(evento_obj)
                            dados['total_descontos_extras'] += valor_evento
                            dados['total_descontos'] += valor_evento
                        elif tipo_evento == 'Omitir do cálculo':
                            # Armazenar como evento informativo (não entra no cálculo da margem)
                            dados['eventos_informativos'].append(evento_obj)
                        else:
                            # Se não encontrou no mapeamento, assumir provento (fallback)
                            # NOTA: Este evento será listado no relatório de não mapeados
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
            desc = desconto['descricao']
            valor = desconto['valor']
            # Sem consolidação - registrar lançamento por lançamento
            if desc not in tipos_descontos_obrigatorios:
                tipos_descontos_obrigatorios[desc] = {'aposentados': [], 'pensionistas': [], 'outros': []}
            
            if eh_aposentado:
                tipos_descontos_obrigatorios[desc]['aposentados'].append(valor)
            elif eh_pensionista:
                tipos_descontos_obrigatorios[desc]['pensionistas'].append(valor)
            else:
                tipos_descontos_obrigatorios[desc]['outros'].append(valor)
        
        for desconto in folha.get('descontos_extras', []):
            desc = desconto['descricao']
            valor = desconto['valor']
            # Sem consolidação - registrar lançamento por lançamento
            if desc not in tipos_descontos_facultativos:
                tipos_descontos_facultativos[desc] = {'aposentados': [], 'pensionistas': [], 'outros': []}
            
            if eh_aposentado:
                tipos_descontos_facultativos[desc]['aposentados'].append(valor)
            elif eh_pensionista:
                tipos_descontos_facultativos[desc]['pensionistas'].append(valor)
            else:
                tipos_descontos_facultativos[desc]['outros'].append(valor)
    
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análise da Margem Consignável - SGP/ALMT - {competencia_formatada}</title>
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
            
            /* Tabelas no mobile: transformar em cards */
            table {{
                font-size: 11px;
            }}
            
            table thead {{
                display: none;
            }}
            
            table, table tbody, table tr, table td {{
                display: block;
                width: 100%;
            }}
            
            table tr {{
                background: white;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                margin-bottom: 15px;
                padding: 15px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            
            table td {{
                text-align: left !important;
                padding: 8px 0;
                border: none;
                position: relative;
                padding-left: 50%;
            }}
            
            table td:before {{
                content: attr(data-label);
                position: absolute;
                left: 0;
                width: 45%;
                padding-right: 10px;
                font-weight: bold;
                color: #2c3e50;
                text-align: left;
            }}
            
            /* Links de beneficiários como botões */
            table td a {{
                display: inline-block;
                background: #2c3e50;
                color: white !important;
                padding: 8px 15px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                margin-top: 5px;
            }}
            
            table td a:hover {{
                background: #34495e;
            }}
            
            /* Ocultar colunas menos importantes no mobile */
            table td:nth-child(2),  /* CPF */
            table td:nth-child(3)   /* Data Nascimento */
            {{
                display: none;
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
            
            /* Cards de detalhes individuais */
            .card-indice {{
                padding: 25px;
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
            
            /* Melhorar legibilidade de valores */
            .valor {{
                word-break: break-word;
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
                font-size: 10px;
            }}
            
            table td {{
                padding-left: 45%;
                font-size: 11px;
            }}
            
            table td:before {{
                font-size: 10px;
                width: 40%;
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
        
        {'<div style="background: linear-gradient(135deg, #fff3cd 0%, #ffe5b4 100%); border: 3px solid #ff9800; border-radius: 12px; padding: 25px; margin: 20px 0; box-shadow: 0 4px 15px rgba(255, 152, 0, 0.3);"><h3 style="color: #e65100; margin: 0 0 15px 0; display: flex; align-items: center; gap: 10px;"><span style="font-size: 1.8em;">⚠️</span><span>EVENTOS NÃO CLASSIFICADOS DETECTADOS</span></h3><div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 15px;"><p style="color: #e65100; font-weight: 600; font-size: 1.1em; margin: 0 0 15px 0;">🔍 Foram encontrados <strong>' + str(len(EVENTOS_NAO_MAPEADOS)) + ' eventos novos</strong> que não estão na planilha Excel!</p><p style="color: #666; margin: 0 0 10px 0; line-height: 1.6;">Esses eventos foram classificados como <strong>"Provento"</strong> por padrão (fallback), mas isso pode estar incorreto. Verifique o arquivo <code>EVENTOS_NAO_CLASSIFICADOS.txt</code> para detalhes.</p><p style="color: #666; margin: 0; line-height: 1.6;"><strong>Exemplos:</strong></p><ul style="color: #666; margin: 10px 0 0 20px; line-height: 1.8;">' + ''.join([f'<li><strong>Código {cod}:</strong> {desc[:50]}{"..." if len(desc) > 50 else ""}</li>' for cod, _, desc in sorted(list(EVENTOS_NAO_MAPEADOS), key=lambda x: int(x[0]) if x[0].isdigit() else x[0])[:5]]) + '</ul></div><div style="background: rgba(230, 81, 0, 0.1); padding: 15px; border-radius: 8px; border-left: 4px solid #e65100;"><strong style="color: #e65100;">📋 AÇÃO NECESSÁRIA:</strong><ol style="color: #666; margin: 10px 0 0 20px; line-height: 1.8;"><li>Abra: <code>Descricao_Comp_Rend.xlsx</code></li><li>Classifique os eventos na sheet <strong>"Composição de Rendimentos"</strong></li><li>Se for "Desconto Facultativo", defina ordem (1-4) na sheet <strong>"Ordem de Eliminação"</strong></li><li>Salve e execute o script novamente</li></ol></div></div>' if EVENTOS_NAO_MAPEADOS else ''}
        
        <nav id="navegacao" style="display: none;">
            <button onclick="mostrarSecao('indice')">🏠 Início</button>
            <button onclick="mostrarSecao('geral')">📈 Relatório Geral</button>
            <button onclick="mostrarSecao('composicao')">📋 Composição</button>
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
                    <div class="card-indice" onclick="mostrarSecao('composicao')">
                        <i>📋</i>
                        <h2>Composição de Rendimentos</h2>
                        <p>Lista completa de eventos classificados</p>
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
    saudavel = 0  # Descontos facultativos < 20% da remuneração líquida
    atencao = 0   # Descontos facultativos entre 20-30% da remuneração líquida
    risco = 0     # Descontos facultativos entre 30-35% da remuneração líquida
    critico = 0   # Descontos facultativos > 35% da remuneração líquida
    sem_descontos = 0
    
    beneficiarios_criticos = []  # Lista para armazenar beneficiários em situação crítica (>35%)
    beneficiarios_rescisao = []  # Lista para armazenar beneficiários em rescisão
    servidores_cedidos = []  # Lista para armazenar servidores cedidos
    casos_atipicos = []  # Lista para armazenar casos atípicos
    
    for dados in dados_folhas:
        descontos_extras = dados.get('total_descontos_extras', 0)
        liquido_final = dados.get('liquido', 0)
        
        # Calcular margem consignável (base de cálculo para empréstimos)
        margem_consignavel = dados.get('total_proventos', 0) - dados.get('total_descontos_obrigatorios', 0)
        
        # Verificar se há evento de rescisão (busca flexível)
        tem_rescisao = any(
            '13' in evento.get('descricao', '').upper() and 'RESCIS' in evento.get('descricao', '').upper()
            for evento in dados.get('proventos', []) + dados.get('eventos_informativos', [])
        )
        
        # Verificar se é servidor cedido
        # Regra: TEM "REPRESENTACAO CONF LC 04/90 - ART. 59" E NÃO TEM "SUBSIDIO" código 1
        tem_representacao = any(
            'REPRESENTACAO CONF LC 04/90' in evento.get('descricao', '').upper() or 'ART. 59' in evento.get('descricao', '').upper()
            for evento in dados.get('proventos', []) + dados.get('eventos_informativos', [])
        )
        tem_subsidio_1 = any(
            evento.get('codigo') == '1' and 'SUBSID' in evento.get('descricao', '').upper()
            for evento in dados.get('proventos', [])
        )
        eh_cedido = tem_representacao and not tem_subsidio_1
        
        # Se é servidor cedido, adicionar à lista
        if eh_cedido:
            servidores_cedidos.append({
                'nome': dados.get('nome', 'N/A'),
                'cpf': dados.get('cpf', 'N/A'),
                'situacao': dados.get('situacao', 'N/A')
            })
        
        # DETECÇÃO DE CASOS ATÍPICOS (múltiplos critérios)
        motivo_atipico = None
        
        # Critério 1: Margem negativa/zero E não é rescisão E não é cedido
        if margem_consignavel <= 0 and not tem_rescisao and not eh_cedido:
            motivo_atipico = 'Margem negativa ou zero'
        
        # Critério 2: Proventos zerados mas com descontos
        elif dados.get('total_proventos', 0) == 0 and dados.get('total_descontos', 0) > 0 and not tem_rescisao and not eh_cedido:
            motivo_atipico = 'Proventos zerados mas com descontos'
        
        # Critério 3: Diferença entre RLM e Líquido quando NÃO há descontos facultativos
        elif descontos_extras == 0 and not tem_rescisao and not eh_cedido:
            liquido_final = dados.get('liquido', 0)
            diferenca = abs(margem_consignavel - liquido_final)
            # Tolerância de R$ 0.10 para arredondamento
            if diferenca > 0.10:
                motivo_atipico = f'Diferença entre RLM e Líquido: R$ {diferenca:.2f}'
        
        # Adicionar aos casos atípicos se algum critério foi atendido
        if motivo_atipico:
            casos_atipicos.append({
                'nome': dados.get('nome', 'N/A'),
                'cpf': dados.get('cpf', 'N/A'),
                'situacao': dados.get('situacao', 'N/A'),
                'margem': margem_consignavel,
                'motivo': motivo_atipico
            })
        
        # Se tem rescisão, adicionar à lista de rescisões
        if tem_rescisao:
            beneficiarios_rescisao.append({
                'nome': dados.get('nome', 'N/A'),
                'cpf': dados.get('cpf', 'N/A'),
                'tem_desconto_facultativo': 'Sim' if descontos_extras > 0 else 'Não'
            })
        
        if descontos_extras == 0:
            sem_descontos += 1
        elif margem_consignavel > 0:
            # Calcular o limite ideal (35% da margem consignável)
            # Base legal: Resolução Administrativa nº 14/2025, Art. 5º
            limite_ideal = margem_consignavel * 0.35
            
            # Percentual sobre o limite ideal de 35%
            # Exemplo: Se limite = 580,69 e descontos = 2.884,42, então 2.884,42 / 580,69 = 497%
            percentual = (descontos_extras / limite_ideal) * 100 if limite_ideal > 0 else 0
            
            # Classificar baseado no percentual sobre o limite ideal (35%)
            # Thresholds alinhados com a capacidade de endividamento consignado:
            # - < 57% do limite = < 20% da margem (SAUDÁVEL)
            # - 57-86% do limite = 20-30% da margem (ATENÇÃO)
            # - 86-100% do limite = 30-35% da margem (RISCO)
            # - > 100% do limite = > 35% da margem (CRÍTICO - acima do limite legal)
            
            if percentual < 57:
                saudavel += 1
            elif percentual < 86:
                atencao += 1
            elif percentual <= 100:
                risco += 1
            else:
                critico += 1
            
            # Adicionar à lista de beneficiários críticos quando ultrapassar 100% do limite (descontos > 35% da margem)
            if percentual > 100:
                beneficiarios_criticos.append({
                    'nome': dados.get('nome', 'N/A'),
                    'cpf': dados.get('cpf', 'N/A'),
                    'situacao': dados.get('situacao', 'N/A'),
                    'total_proventos': dados.get('total_proventos', 0),
                    'total_descontos_obrigatorios': dados.get('total_descontos_obrigatorios', 0),
                    'margem_consignavel': margem_consignavel,
                    'liquido_final': liquido_final,
                    'descontos_extras': descontos_extras,
                    'percentual': percentual,
                    'rescisao': 'Sim' if tem_rescisao else 'Não'
                })
    
    html += f"""
                    <div class="grid-stats">
                        <div style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px;">
                            <div style="font-size: 14px; color: #155724; margin-bottom: 5px;">✅ Saudável</div>
                            <div style="font-size: 28px; font-weight: bold; color: #28a745;">{saudavel + sem_descontos}</div>
                            <small style="color: #666;">Sem descontos extras ou < 57% do limite (< 20% da margem)</small>
                        </div>
                        <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; border-radius: 8px;">
                            <div style="font-size: 14px; color: #856404; margin-bottom: 5px;">⚠️ Atenção</div>
                            <div style="font-size: 28px; font-weight: bold; color: #ffc107;">{atencao}</div>
                            <small style="color: #666;">57-86% do limite (20-30% da margem consignável)</small>
                        </div>
                        <div style="background: #ffe5d0; border-left: 4px solid #ff9800; padding: 20px; border-radius: 8px;">
                            <div style="font-size: 14px; color: #e65100; margin-bottom: 5px;">⚠️ Risco</div>
                            <div style="font-size: 28px; font-weight: bold; color: #ff9800;">{risco}</div>
                            <small style="color: #666;">86-100% do limite (30-35% da margem) - Próximo do limite legal</small>
                        </div>
                        <div style="background: #f5c6cb; border-left: 4px solid #a71d2a; padding: 20px; border-radius: 8px;">
                            <div style="font-size: 14px; color: #491217; margin-bottom: 5px;">🚨 Crítico</div>
                            <div style="font-size: 28px; font-weight: bold; color: #a71d2a;">{critico}</div>
                            <small style="color: #666;">> 100% do limite (> 35% da margem) - ACIMA DO LIMITE LEGAL</small>
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
                            Os seguintes beneficiários ultrapassaram o limite ideal de 35% da margem consignável (RLM). O percentual mostra quanto do limite permitido está sendo utilizado:
                        </p>
                        <table style="font-size: 0.95em;">
                            <thead>
                                <tr>
                                    <th>Nome</th>
                                    <th>Situação</th>
                                    <th>Base Margem</th>
                                    <th>Limite (35%)</th>
                                    <th>Descontos Facultativos<br><small>(Comprometido)</small></th>
                                    <th>% do Limite</th>
                                </tr>
                            </thead>
                            <tbody>
"""
        
        for benef in sorted(beneficiarios_criticos, key=lambda x: x['percentual'], reverse=True):
            html += f"""                                <tr>
                                    <td data-label="Nome"><strong><a href="javascript:void(0);" onclick="abrirBeneficiario('{benef.get('cpf', '')}')" style="color: #a71d2a; text-decoration: none; border-bottom: 1px dashed #a71d2a; cursor: pointer;" title="Clique para ver detalhes de {benef['nome']}">{benef['nome']}</a></strong></td>
                                    <td data-label="Situação">{benef['situacao']}</td>
                                    <td data-label="Base Margem" style="color: #3498db; font-weight: bold;">R$ {formatar_moeda_br(benef['margem_consignavel'])}</td>
                                    <td data-label="Limite (35%)" style="color: #9b59b6; font-weight: bold;">R$ {formatar_moeda_br(benef['margem_consignavel'] * 0.35)}</td>
                                    <td data-label="Descontos Facultativos" style="color: #e74c3c; font-weight: bold;">R$ {formatar_moeda_br(benef['descontos_extras'])}</td>
                                    <td data-label="% do Limite" style="color: #a71d2a; font-weight: bold; font-size: 1.1em;">{benef['percentual']:.1f}%</td>
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
    
    # Se houver beneficiários em rescisão, mostrar tabela detalhada
    if beneficiarios_rescisao:
        html += f"""
                    <div style="background: #e3f2fd; border: 2px solid #2196f3; padding: 20px; border-radius: 10px; margin-top: 25px;">
                        <h4 style="color: #0d47a1; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.5em;">📋</span>
                            BENEFICIÁRIOS COM RESCISÃO DE TRABALHO NESTA COMPETÊNCIA: {len(beneficiarios_rescisao)} pessoa(s)
                        </h4>
                        <p style="color: #1565c0; margin-bottom: 15px; font-size: 0.95em;">
                            Os seguintes beneficiários apresentam rescisão de contrato de trabalho na competência {competencia_formatada}. Estes não estarão presentes na folha da competência seguinte.
                        </p>
                        <table style="font-size: 0.95em;">
                            <thead>
                                <tr>
                                    <th>Nome</th>
                                    <th style="text-align: center; width: 180px;">Desconto Facultativo</th>
                                </tr>
                            </thead>
                            <tbody>
"""
        
        for benef in sorted(beneficiarios_rescisao, key=lambda x: x['nome']):
            tem_desconto = benef.get('tem_desconto_facultativo', 'Não')
            cor_desconto = '#e74c3c' if tem_desconto == 'Sim' else '#27ae60'
            icone_desconto = '✓' if tem_desconto == 'Sim' else '✗'
            
            html += f"""                                <tr>
                                    <td data-label="Nome"><strong><a href="javascript:void(0);" onclick="abrirBeneficiario('{benef.get('cpf', '')}')" style="color: #2196f3; text-decoration: none; border-bottom: 1px dashed #2196f3; cursor: pointer;" title="Clique para ver detalhes de {benef['nome']}">{benef['nome']}</a></strong></td>
                                    <td data-label="Desconto Facultativo" style="text-align: center; color: {cor_desconto}; font-weight: bold; font-size: 1.05em;">{icone_desconto} {tem_desconto}</td>
                                </tr>
"""
        
        html += """                            </tbody>
                        </table>
                        <div style="margin-top: 15px; padding: 15px; background: rgba(33, 150, 243, 0.15); border-radius: 6px; border-left: 4px solid #2196f3;">
                            <strong>ℹ️ INFORMAÇÃO:</strong>
                            <ul style="margin: 10px 0 0 20px; line-height: 1.8;">
                                <li>Beneficiários com rescisão não estarão na próxima competência</li>
                                <li>Descontos facultativos indicados com "Sim" podem requerer atenção para encerramento</li>
                                <li>Verifique se há necessidade de notificar instituições financeiras sobre o desligamento</li>
                            </ul>
                        </div>
                    </div>
"""
    
    # Se houver servidores cedidos, mostrar tabela detalhada
    if servidores_cedidos:
        html += f"""
                    <div style="background: #fff3e0; border: 2px solid #ff9800; padding: 20px; border-radius: 10px; margin-top: 25px;">
                        <h4 style="color: #e65100; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.5em;">👤</span>
                            SERVIDORES CEDIDOS: {len(servidores_cedidos)} pessoa(s)
                        </h4>
                        <p style="color: #ef6c00; margin-bottom: 15px; font-size: 0.95em;">
                            Os seguintes servidores são cedidos de outros órgãos (Poder Executivo ou Judiciário) ao Poder Legislativo. 
                            A margem consignável pode estar baseada em eventos omitidos do cálculo (ex: "REPRESENTACAO CONF LC 04/90 - ART. 59").
                        </p>
                        <table style="font-size: 0.95em;">
                            <thead>
                                <tr>
                                    <th>Nome</th>
                                    <th style="text-align: center; width: 180px;">Situação</th>
                                </tr>
                            </thead>
                            <tbody>
"""
        
        for servidor in sorted(servidores_cedidos, key=lambda x: x['nome']):
            html += f"""                                <tr>
                                    <td data-label="Nome"><strong><a href="javascript:void(0);" onclick="abrirBeneficiario('{servidor.get('cpf', '')}')" style="color: #ff9800; text-decoration: none; border-bottom: 1px dashed #ff9800; cursor: pointer;" title="Clique para ver detalhes de {servidor['nome']}">{servidor['nome']}</a></strong></td>
                                    <td data-label="Situação" style="text-align: center; color: #e65100; font-weight: 600;">{servidor['situacao']}</td>
                                </tr>
"""
        
        html += """                            </tbody>
                        </table>
                        <div style="margin-top: 15px; padding: 15px; background: rgba(255, 152, 0, 0.15); border-radius: 6px; border-left: 4px solid #ff9800;">
                            <strong>⚠️ OBSERVAÇÃO:</strong>
                            <ul style="margin: 10px 0 0 20px; line-height: 1.8;">
                                <li>Servidores cedidos têm remuneração paga pelo órgão de origem</li>
                                <li>Eventos de representação/gratificação podem estar omitidos do cálculo da margem</li>
                                <li>Verifique se há restrições para concessão de empréstimos consignados</li>
                            </ul>
                        </div>
                    </div>
"""
    
    # Se houver casos atípicos, mostrar tabela detalhada
    if casos_atipicos:
        html += f"""
                    <div style="background: #fff9c4; border: 2px solid #fbc02d; padding: 20px; border-radius: 10px; margin-top: 25px;">
                        <h4 style="color: #f57f17; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.5em;">⚡</span>
                            CASOS ATÍPICOS: {len(casos_atipicos)} pessoa(s)
                        </h4>
                        <p style="color: #f9a825; margin-bottom: 15px; font-size: 0.95em;">
                            Os seguintes beneficiários apresentam situações atípicas que requerem atenção especial, como margem consignável negativa ou zerada, 
                            valores inconsistentes, ou outras anomalias detectadas automaticamente.
                        </p>
                        <table style="font-size: 0.95em;">
                            <thead>
                                <tr>
                                    <th>Nome</th>
                                    <th style="text-align: center; width: 180px;">Situação</th>
                                    <th style="text-align: right; width: 150px;">Margem (RLM)</th>
                                    <th style="width: 200px;">Motivo</th>
                                </tr>
                            </thead>
                            <tbody>
"""
        
        for caso in sorted(casos_atipicos, key=lambda x: x['margem']):
            cor_margem = '#c62828' if caso['margem'] < 0 else '#f57f17'
            html += f"""                                <tr>
                                    <td data-label="Nome"><strong><a href="javascript:void(0);" onclick="abrirBeneficiario('{caso.get('cpf', '')}')" style="color: #fbc02d; text-decoration: none; border-bottom: 1px dashed #fbc02d; cursor: pointer;" title="Clique para ver detalhes de {caso['nome']}">{caso['nome']}</a></strong></td>
                                    <td data-label="Situação" style="text-align: center; color: #f57f17; font-weight: 600;">{caso['situacao']}</td>
                                    <td data-label="Margem" style="text-align: right; color: {cor_margem}; font-weight: bold;">R$ {formatar_moeda_br(caso['margem'])}</td>
                                    <td data-label="Motivo" style="color: #666; font-style: italic;">{caso['motivo']}</td>
                                </tr>
"""
        
        html += """                            </tbody>
                        </table>
                        <div style="margin-top: 15px; padding: 15px; background: rgba(251, 192, 45, 0.15); border-radius: 6px; border-left: 4px solid #fbc02d;">
                            <strong>🔍 ATENÇÃO NECESSÁRIA:</strong>
                            <ul style="margin: 10px 0 0 20px; line-height: 1.8;">
                                <li>Verifique individualmente cada caso para entender a causa da inconsistência</li>
                                <li>Pode incluir: substituições temporárias, comissionados com variação mensal, erros de processamento</li>
                                <li>Analise o relatório individual completo clicando no nome do beneficiário</li>
                                <li>Considere ajustes na planilha de classificação se necessário</li>
                            </ul>
                        </div>
                    </div>
"""
    
    html += """                </div>
            </div>
            
            <!-- COMPOSIÇÃO DE RENDIMENTOS -->
            <div id="composicao" class="secao">
                <h2 style="color: #2c3e50; margin-bottom: 30px;">📋 Composição de Rendimentos - Eventos Classificados</h2>
                
                <div style="background: #e3f2fd; padding: 20px; border-radius: 10px; margin-bottom: 30px; border-left: 5px solid #2196f3;">
                    <p style="color: #1565c0; margin: 0; line-height: 1.6;">
                        <strong>📌 Sobre esta lista:</strong> Estes são todos os eventos (proventos e descontos) cadastrados no sistema, 
                        classificados conforme a planilha <code>Descricao_Comp_Rend.xlsx</code>. 
                        A classificação determina como cada evento é contabilizado no cálculo da margem consignável.
                    </p>
                </div>
"""
    
    # Organizar eventos por tipo
    eventos_por_tipo = {
        'Provento': [],
        'Desconto Compulsório (obrigatório)': [],
        'Desconto Facultativo (extra)': [],
        'Omitir do cálculo': []
    }
    
    for (codigo, descricao), tipo in sorted(MAPEAMENTO_EVENTOS.items()):
        eventos_por_tipo[tipo].append((codigo, descricao))
    
    # Gerar HTML para cada tipo
    cores_tipo = {
        'Provento': {'bg': '#d4edda', 'border': '#28a745', 'icon': '💰'},
        'Desconto Compulsório (obrigatório)': {'bg': '#fff3cd', 'border': '#ffc107', 'icon': '⚖️'},
        'Desconto Facultativo (extra)': {'bg': '#f8d7da', 'border': '#dc3545', 'icon': '💳'},
        'Omitir do cálculo': {'bg': '#e2e3e5', 'border': '#6c757d', 'icon': '⊘'}
    }
    
    for tipo, eventos in eventos_por_tipo.items():
        if not eventos:
            continue
            
        cor = cores_tipo.get(tipo, {'bg': '#f8f9fa', 'border': '#6c757d', 'icon': '📄'})
        
        html += f"""
                <div class="estatistica">
                    <div style="background: {cor['bg']}; padding: 15px; border-radius: 8px; border-left: 5px solid {cor['border']}; margin-bottom: 15px;">
                        <h3 style="margin: 0; color: #2c3e50;">
                            <span style="font-size: 1.3em; margin-right: 10px;">{cor['icon']}</span>
                            {tipo}
                            <span style="font-size: 0.8em; color: #666; font-weight: normal;">({len(eventos)} evento{'s' if len(eventos) != 1 else ''})</span>
                        </h3>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 100px;">Código</th>
                                <th>Descrição do Evento</th>
                            </tr>
                        </thead>
                        <tbody>
"""
        
        for codigo, descricao in sorted(eventos, key=lambda x: int(x[0]) if x[0].isdigit() else 9999):
            html += f"""                            <tr>
                                <td style="text-align: center; font-weight: bold; color: #2c3e50;">{codigo}</td>
                                <td>{descricao}</td>
                            </tr>
"""
        
        html += """                        </tbody>
                    </table>
                </div>
"""
    
    html += """            </div>
            
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
        
        // Ordem de eliminação da planilha Excel
        const ordemEliminacao = """ + json.dumps(ORDEM_ELIMINACAO, ensure_ascii=False) + """;
        
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
                        <div class="stat-box">
                            <div class="label">Cargo</div>
                            <div class="valor" style="font-size: 1em;">${beneficiario.cargo || 'Não informado'}</div>
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
                                <span style="font-size: 1.5em;">⚠️</span>
                                <span>DESCONTOS COMPULSÓRIOS (OBRIGATÓRIOS) - Saídas</span>
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
                                    <td style="padding: 15px;">TOTAL DESCONTOS COMPULSÓRIOS</td>
                                    <td style="text-align: right; padding: 15px;">R$ ${(beneficiario.total_descontos_obrigatorios || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                    <td style="text-align: right; padding: 15px;">100%</td>
                                    <td style="text-align: center; padding: 15px;">⚖️</td>
                                </tr>
                            </tbody>
                        </table>
                        </div>
                        
                        <div style="background: linear-gradient(135deg, #ffebee 0%, #fef5f6 100%); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 5px solid #e74c3c;">
                            <h4 style="color: #e74c3c; margin: 0 0 20px 0; display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 1.5em;">💳</span>
                                <span>DESCONTOS FACULTATIVOS - Saídas</span>
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
                                    <td style="padding: 15px;">TOTAL DESCONTOS FACULTATIVOS</td>
                                    <td style="text-align: right; padding: 15px;">R$ ${(beneficiario.total_descontos_extras || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                    <td style="text-align: right; padding: 15px;">100%</td>
                                    <td style="text-align: center; padding: 15px;">💳</td>
                                </tr>
                            </tbody>
                        </table>
                        </div>
                        
                        ${beneficiario.eventos_informativos && beneficiario.eventos_informativos.length > 0 ? `
                        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #f1f8fc 100%); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 5px solid #2196f3;">
                            <h4 style="color: #1976d2; margin: 0 0 10px 0; display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 1.5em;">ℹ️</span>
                                <span>OUTROS EVENTOS INFORMATIVOS</span>
                            </h4>
                            <p style="color: #0d47a1; margin-bottom: 20px; font-size: 0.95em; line-height: 1.6;">
                                <strong>⚠️ Atenção:</strong> Os eventos abaixo <strong>não entram no cálculo da margem consignável</strong>. 
                                São valores informativos, adiantamentos já incluídos, ou eventos que não afetam a base de cálculo conforme 
                                as regras da instituição.
                            </p>
                            <table style="background: white;">
                                <thead>
                                    <tr>
                                        <th style="text-align: left;">Descrição</th>
                                        <th style="text-align: right; width: 120px;">Valor</th>
                                        <th style="text-align: center; width: 80px;">Código</th>
                                    </tr>
                                </thead>
                                <tbody>
                        ` : ''}
                        ${beneficiario.eventos_informativos && beneficiario.eventos_informativos.length > 0 ? 
                            beneficiario.eventos_informativos.map(e => `
                                    <tr>
                                        <td style="font-weight: 500; color: #555;">${e.descricao}</td>
                                        <td style="text-align: right; color: #2196f3; font-weight: 600;">R$ ${e.valor.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                        <td style="text-align: center; color: #999; font-family: monospace;">${e.codigo}</td>
                                    </tr>
                            `).join('') : ''
                        }
                        ${beneficiario.eventos_informativos && beneficiario.eventos_informativos.length > 0 ? `
                                </tbody>
                            </table>
                            <div style="background: rgba(33, 150, 243, 0.1); padding: 15px; border-radius: 8px; margin-top: 15px;">
                                <p style="margin: 0; color: #0d47a1; font-size: 0.9em; line-height: 1.6;">
                                    <strong>📌 Por que esses eventos não entram no cálculo?</strong><br>
                                    Podem incluir: adiantamentos de 13º salário, férias já computadas, 
                                    rescisões (que têm tratamento específico), eventos já incluídos em outros lançamentos, 
                                    ou valores puramente informativos que não afetam a margem disponível para consignações.
                                </p>
                            </div>
                        </div>
                        ` : ''}
                        
                        <div style="background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; padding: 30px; border-radius: 15px; margin: 25px 0; box-shadow: 0 8px 20px rgba(0,0,0,0.2);">
                            <h4 style="margin: 0 0 25px 0; font-size: 1.3em; display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 1.3em;">🧮</span>
                                <span>EXTRATO DA MARGEM</span>
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
                                    <span>⚠️ Descontos Compulsórios (Obrigatórios):</span>
                                    <div style="text-align: right;">
                                        <div style="font-weight: bold; color: #ff9800;">- R$ ${(beneficiario.total_descontos_obrigatorios || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                        <div style="font-size: 0.85em; opacity: 0.8; color: #ff9800;">(${beneficiario.total_proventos > 0 ? ((beneficiario.total_descontos_obrigatorios || 0) / beneficiario.total_proventos * 100).toFixed(1) : 0}% dos proventos)</div>
                                    </div>
                                </div>
                                <div style="height: 1px; background: rgba(255,255,255,0.2); margin: 5px 20px;"></div>
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(255,255,255,0.1); border-radius: 8px; font-style: italic;">
                                    <span>RLM (Base Margem):</span>
                                    <div style="text-align: right;">
                                        <div style="font-weight: bold; color: #3498db;">R$ ${(beneficiario.total_proventos - (beneficiario.total_descontos_obrigatorios || 0)).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                        <div style="font-size: 0.85em; opacity: 0.8; color: #3498db;">(${beneficiario.total_proventos > 0 ? ((beneficiario.total_proventos - (beneficiario.total_descontos_obrigatorios || 0)) / beneficiario.total_proventos * 100).toFixed(1) : 0}% dos proventos)</div>
                                    </div>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(231, 76, 60, 0.15); border-radius: 8px; border-left: 4px solid #e74c3c;">
                                    <span>💳 Descontos Facultativos:</span>
                                    <div style="text-align: right;">
                                        <div style="font-weight: bold; color: #e74c3c;">- R$ ${(beneficiario.total_descontos_extras || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                        <div style="font-size: 0.85em; opacity: 0.8; color: #e74c3c;">(${(beneficiario.total_proventos - (beneficiario.total_descontos_obrigatorios || 0)) > 0 ? ((beneficiario.total_descontos_extras || 0) / (beneficiario.total_proventos - (beneficiario.total_descontos_obrigatorios || 0)) * 100).toFixed(1) : 0}% da RLM)</div>
                                    </div>
                                </div>
                                
                                ${(() => {
                                    const proventos = beneficiario.total_proventos;
                                    const descontosObrig = beneficiario.total_descontos_obrigatorios || 0;
                                    const descontosExtras = beneficiario.total_descontos_extras || 0;
                                    
                                    const baseCalculo = proventos - descontosObrig;
                                    const limiteIdeal = baseCalculo * 0.35;
                                    const percentualUtilizado = limiteIdeal > 0 ? (descontosExtras / limiteIdeal * 100) : 0;
                                    
                                    let status, cor, icone, alerta;
                                    if (percentualUtilizado === 0) {
                                        status = 'SAUDÁVEL';
                                        cor = '#27ae60';
                                        icone = '✅';
                                        alerta = 'Margem consignável 100% disponível';
                                    } else if (percentualUtilizado < 57) {  // < 57% do limite = < 20% da margem
                                        status = 'SAUDÁVEL';
                                        cor = '#2ecc71';
                                        icone = '✔️';
                                        alerta = 'Margem consignável saudável, uso consciente';
                                    } else if (percentualUtilizado < 86) {  // 57-86% do limite = 20-30% da margem
                                        status = 'ATENÇÃO';
                                        cor = '#f39c12';
                                        icone = '⚠️';
                                        alerta = 'Atenção: 20-30% da margem consignável comprometida';
                                    } else if (percentualUtilizado <= 100) {  // 86-100% do limite = 30-35% da margem
                                        status = 'RISCO';
                                        cor = '#ff9800';
                                        icone = '⚠️';
                                        alerta = 'Risco: próximo do limite legal de 35%';
                                    } else {  // > 100% do limite = > 35% da margem
                                        status = 'CRÍTICO';
                                        cor = '#e74c3c';
                                        icone = '🚨';
                                        alerta = 'CRÍTICO: ACIMA DO LIMITE LEGAL DE 35% (Resolução Administrativa nº 14/2025)';
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
                const limiteIdeal = baseCalculo * 0.35;
                const percentualAtual = limiteIdeal > 0 ? (descontosExtras / limiteIdeal * 100) : 0;
                
                // Só mostrar se estiver acima de 100% (ou seja, descontos extras > limite de 35%)
                if (percentualAtual > 100) {
                    const valorAReduzir = descontosExtras - limiteIdeal;
                    
                    // Função para obter ordem de eliminação de um desconto
                    const obterOrdem = (descricao) => {
                        const descUpper = descricao.toUpperCase().trim();
                        
                        // Buscar correspondência exata
                        if (ordemEliminacao[descUpper]) {
                            return ordemEliminacao[descUpper];
                        }
                        
                        // Buscar correspondência parcial
                        for (const [key, value] of Object.entries(ordemEliminacao)) {
                            if (descUpper.includes(key) || key.includes(descUpper)) {
                                return value;
                            }
                        }
                        
                        // Se não encontrou, retornar ordem 5 (última)
                        return { ordem: 5, nome_ordem: 'Não classificado' };
                    };
                    
                    // Agrupar descontos por ordem de eliminação
                    const descontosPorOrdem = {};
                    beneficiario.descontos_extras.forEach(desc => {
                        const infoOrdem = obterOrdem(desc.descricao);
                        const ordem = infoOrdem.ordem;
                        
                        if (!descontosPorOrdem[ordem]) {
                            descontosPorOrdem[ordem] = {
                                nome_ordem: infoOrdem.nome_ordem,
                                descontos: []
                            };
                        }
                        
                        descontosPorOrdem[ordem].descontos.push(desc);
                    });
                    
                    // Função para encontrar melhor combinação dentro de um grupo
                    const encontrarMelhorCombinacao = (descontos, descontosAtuais) => {
                        if (descontos.length === 0) return [];
                        
                        const percentualAtualCalc = baseCalculo > 0 ? (descontosAtuais / baseCalculo * 100) : 0;
                        if (percentualAtualCalc <= 35) return []; // Já atingiu meta
                        
                        let melhorCombinacao = [];
                        let melhorPercentual = percentualAtualCalc;
                        let melhorDistancia = Infinity;
                        
                        // Limitar combinações para performance
                        const maxCombinacoes = Math.min(Math.pow(2, descontos.length), 32768);
                        
                        for (let i = 1; i < maxCombinacoes; i++) {
                            let somaTemp = 0;
                            let combinacaoTemp = [];
                            
                            for (let j = 0; j < Math.min(descontos.length, 15); j++) {
                                if (i & (1 << j)) {
                                    somaTemp += descontos[j].valor;
                                    combinacaoTemp.push(descontos[j]);
                                }
                            }
                            
                            const novoDescontoTotal = descontosAtuais - somaTemp;
                            const novoPercentual = baseCalculo > 0 ? (novoDescontoTotal / baseCalculo * 100) : 0;
                            
                            // Preferir combinação que chegue mais próximo de 35% (sem ultrapassar para baixo)
                            if (novoPercentual <= 35) {
                                const distancia = 35 - novoPercentual;
                                if (distancia < melhorDistancia) {
                                    melhorDistancia = distancia;
                                    melhorCombinacao = [...combinacaoTemp];
                                    melhorPercentual = novoPercentual;
                                }
                            }
                        }
                        
                        // Se nenhuma combinação atingiu <= 35%, pega todos do grupo
                        if (melhorCombinacao.length === 0 && descontos.length > 0) {
                            return descontos;
                        }
                        
                        return melhorCombinacao;
                    };
                    
                    // Processar eliminações seguindo a ordem: 1, 2, 3, 4
                    let descontosParaEliminar = [];
                    let descontosRestantes = descontosExtras;
                    
                    for (let ordemAtual = 1; ordemAtual <= 5; ordemAtual++) {
                        if (!descontosPorOrdem[ordemAtual]) continue;
                        
                        const grupoAtual = descontosPorOrdem[ordemAtual];
                        const percentualAtualCalc = baseCalculo > 0 ? (descontosRestantes / baseCalculo * 100) : 0;
                        
                        // Se já atingiu <= 35%, parar
                        if (percentualAtualCalc <= 35) break;
                        
                        // Se ordem 1 (Prioridade Máxima), eliminar TODOS
                        if (ordemAtual === 1) {
                            grupoAtual.descontos.forEach(desc => {
                                descontosParaEliminar.push({
                                    descricao: desc.descricao,
                                    valor: desc.valor,
                                    prioridade: grupoAtual.nome_ordem
                                });
                                descontosRestantes -= desc.valor;
                            });
                        } else {
                            // Para ordens 2, 3, 4: encontrar melhor combinação
                            const melhorCombinacao = encontrarMelhorCombinacao(grupoAtual.descontos, descontosRestantes);
                            melhorCombinacao.forEach(desc => {
                                descontosParaEliminar.push({
                                    descricao: desc.descricao,
                                    valor: desc.valor,
                                    prioridade: grupoAtual.nome_ordem
                                });
                                descontosRestantes -= desc.valor;
                            });
                        }
                    }
                    
                    const totalEliminado = descontosExtras - descontosRestantes;
                    const novoTotalExtras = descontosRestantes;
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
                                        <strong>RLM (Base Margem):</strong> R$ ${baseCalculo.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
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
                        
                        // Definir cor baseada no texto da prioridade
                        let corCategoria = '#6c757d'; // Cinza padrão
                        if (desc.prioridade.includes('1 -') || desc.prioridade.includes('Prioridade Máxima')) {
                            corCategoria = '#dc3545'; // Vermelho para prioridade 1
                        } else if (desc.prioridade.includes('2 -') || desc.prioridade.includes('Facultativo Nível 2')) {
                            corCategoria = '#fd7e14'; // Laranja para prioridade 2
                        } else if (desc.prioridade.includes('3 -') || desc.prioridade.includes('Facultativo Nível 3')) {
                            corCategoria = '#ffc107'; // Amarelo para prioridade 3
                        } else if (desc.prioridade.includes('4 -') || desc.prioridade.includes('Analisar suspensão')) {
                            corCategoria = '#17a2b8'; // Azul para prioridade 4
                        }
                        
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
                                    Entre em contato com o servidor para orientar sobre a necessidade de renegociação ou cancelamento dos contratos listados acima.<br>
                                    <strong>A ordem de eliminação segue a hierarquia institucional:</strong><br>
                                    🔴 <strong>Prioridade 1:</strong> Cartões (eliminação obrigatória de todos)<br>
                                    🟠 <strong>Prioridade 2:</strong> Consignações bancárias (melhor combinação para atingir 35%)<br>
                                    🟡 <strong>Prioridade 3:</strong> Associações e sindicatos<br>
                                    🔵 <strong>Prioridade 4:</strong> Planos de saúde e previdência complementar (medida extrema)
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

# Configurar encoding para UTF-8 no Windows
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logger.info("="*80)
logger.info("🚀 SISTEMA DE ANÁLISE DE FOLHAS DE PAGAMENTO")
logger.info("="*80)

# Selecionar competência
competencia = selecionar_competencia()
if not competencia:
    exit(1)

# Configurações
caminho_base = Path(__file__).parent.parent
caminho_pasta = competencia['caminho']
competencia_nome = competencia['pasta']

# Caminhos de saída para a competência
pasta_competencia = caminho_base / "data" / "competencias" / competencia_nome
caminho_output_comp = pasta_competencia / "relatorio.html"
caminho_backup_comp = pasta_competencia / "resultado.json"

# Caminhos gerais (raiz)
caminho_output = caminho_base / "output" / "index.html"
caminho_index_raiz = caminho_base / "index.html"
caminho_backup = caminho_base / "data" / "backup" / "dados_folhas_backup.json"

# Buscar todos os PDFs
arquivos_pdf = [f.name for f in caminho_pasta.glob('*.pdf') if 'Logo' not in f.name]

logger.info(f"\n📂 Pasta: {caminho_pasta}")
logger.info(f"📄 Arquivos PDF encontrados: {len(arquivos_pdf)}")

logger.info("\n" + "="*80)
logger.info("📊 PROCESSANDO FOLHAS DE PAGAMENTO...")
logger.info("="*80 + "\n")

dados_todas_folhas = []
inicio = datetime.now()

# Processar cada PDF
for arquivo in arquivos_pdf:
    caminho_completo = caminho_pasta / arquivo
    
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

logger.info("\n\n" + "="*80)
logger.info("📈 ESTATÍSTICAS DO PROCESSAMENTO")
logger.info("="*80)

# Gerar estatísticas
stats = gerar_relatorio_estatisticas(dados_todas_folhas)

logger.info(f"\n✅ Processados com sucesso: {stats['com_sucesso']}/{stats['total']}")
logger.info(f"⚠️  Sem dados extraídos: {stats['sem_dados']}/{stats['total']}")
logger.info(f"❌ Com erros: {stats['com_erro']}/{stats['total']}")

logger.info(f"\n💰 Total de Proventos: R$ {formatar_moeda_br(stats['total_proventos'])}")
logger.info(f"⚠️  Total Descontos Compulsórios (Obrigatórios): R$ {formatar_moeda_br(stats['total_descontos_obrigatorios'])}")
logger.info(f"💳 Total Descontos Facultativos: R$ {formatar_moeda_br(stats['total_descontos_extras'])}")
logger.info(f"💵 Total Líquido: R$ {formatar_moeda_br(stats['total_liquido'])}")

tempo_decorrido = (datetime.now() - inicio).total_seconds()
logger.info(f"\n⏱️  Tempo de processamento: {tempo_decorrido:.2f} segundos")
if len(dados_todas_folhas) > 0:
    print(f"⚡ Velocidade: {len(dados_todas_folhas)/tempo_decorrido:.1f} holerites/segundo")

# Salvar log de erros se houver
salvar_log_erros(dados_todas_folhas, caminho_pasta)

# Gerar relatório de eventos não mapeados
if EVENTOS_NAO_MAPEADOS:
    print("\n" + "="*80)
    print("⚠️  ATENÇÃO: EVENTOS NÃO CLASSIFICADOS DETECTADOS!")
    print("="*80)
    print(f"\n🔍 Foram encontrados {len(EVENTOS_NAO_MAPEADOS)} eventos novos que não estão na planilha Excel.")
    print("📋 Esses eventos foram classificados como 'Provento' por padrão (fallback).")
    print("📝 Você precisa classificá-los manualmente na planilha 'Descricao_Comp_Rend.xlsx'!\n")
    
    # Gerar arquivo de eventos não mapeados
    pasta_raiz = os.path.dirname(caminho_pasta)
    caminho_nao_mapeados = os.path.join(pasta_raiz, "EVENTOS_NAO_CLASSIFICADOS.txt")
    
    with open(caminho_nao_mapeados, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("⚠️  EVENTOS NÃO CLASSIFICADOS - AÇÃO NECESSÁRIA\n")
        f.write("="*80 + "\n")
        f.write(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write(f"Total de eventos não classificados: {len(EVENTOS_NAO_MAPEADOS)}\n")
        f.write("="*80 + "\n\n")
        
        f.write("📋 INSTRUÇÕES:\n")
        f.write("-" * 80 + "\n")
        f.write("1. Abra a planilha: Descricao_Comp_Rend.xlsx\n")
        f.write("2. Acesse a sheet: 'Composição de Rendimentos'\n")
        f.write("3. Adicione cada evento abaixo com sua classificação:\n")
        f.write("   - Provento\n")
        f.write("   - Desconto Compulsório (obrigatório)\n")
        f.write("   - Desconto Facultativo (extra)\n")
        f.write("   - Omitir do cálculo\n")
        f.write("4. Se for 'Desconto Facultativo', adicione também na sheet 'Ordem de Eliminação'\n")
        f.write("   com a prioridade correta (1, 2, 3 ou 4)\n")
        f.write("5. Salve a planilha e execute o script novamente\n")
        f.write("="*80 + "\n\n")
        
        f.write("📊 EVENTOS NÃO CLASSIFICADOS:\n")
        f.write("="*80 + "\n\n")
        
        # Ordenar por código
        eventos_ordenados = sorted(EVENTOS_NAO_MAPEADOS, key=lambda x: int(x[0]) if x[0].isdigit() else x[0])
        
        for codigo, descricao_upper, descricao_original in eventos_ordenados:
            f.write(f"Código: {codigo}\n")
            f.write(f"Descrição: {descricao_original}\n")
            f.write(f"Descrição Normalizada: {descricao_upper}\n")
            f.write("-" * 80 + "\n\n")
        
        f.write("="*80 + "\n")
        f.write("💡 DICA: Copie as informações acima e cole na planilha Excel\n")
        f.write("="*80 + "\n")
    
    print(f"📄 Lista completa salva em: {caminho_nao_mapeados}")
    print("\n" + "="*80)
    print("🚨 EVENTOS NÃO CLASSIFICADOS:")
    print("="*80 + "\n")
    
    eventos_ordenados = sorted(EVENTOS_NAO_MAPEADOS, key=lambda x: int(x[0]) if x[0].isdigit() else x[0])
    for i, (codigo, descricao_upper, descricao_original) in enumerate(eventos_ordenados, 1):
        print(f"{i}. Código {codigo} - {descricao_original}")
    
    print("\n" + "="*80)
    print("⚠️  AÇÃO NECESSÁRIA:")
    print("="*80)
    print("1. Abra: Descricao_Comp_Rend.xlsx")
    print("2. Classifique cada evento acima")
    print("3. Se for 'Desconto Facultativo', defina a ordem de eliminação (1-4)")
    print("4. Salve e execute o script novamente")
    print("="*80 + "\n")

# Gerar HTML
logger.info("\n" + "="*80)
logger.info("📝 GERANDO RELATÓRIO HTML...")
logger.info("="*80 + "\n")

html_final = gerar_html_relatorio(dados_todas_folhas)

# Salvar na pasta da competência
with open(caminho_output_comp, 'w', encoding='utf-8') as f:
    f.write(html_final)
    
with open(caminho_backup_comp, 'w', encoding='utf-8') as f:
    json.dump(dados_todas_folhas, f, ensure_ascii=False, indent=2)

logger.info(f"✅ Relatório da competência {competencia_nome} salvo!")
logger.info(f"📁 HTML: {caminho_output_comp}")
logger.info(f"📁 JSON: {caminho_backup_comp}")

# Salvar também nas pastas gerais (output/ e raiz)
with open(caminho_output, 'w', encoding='utf-8') as f:
    f.write(html_final)

with open(caminho_index_raiz, 'w', encoding='utf-8') as f:
    f.write(html_final)

logger.info(f"\n✅ Relatório geral atualizado!")
logger.info(f"📁 Output: {caminho_output}")
logger.info(f"📁 GitHub Pages: {caminho_index_raiz}")

# Backup geral
with open(caminho_backup, 'w', encoding='utf-8') as f:
    json.dump(dados_todas_folhas, f, ensure_ascii=False, indent=2)
logger.info(f"💾 Backup geral: {caminho_backup}")

logger.info("\n" + "="*80)
logger.info("🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
logger.info("="*80)
print("\n🌐 Abra o arquivo HTML no navegador para visualizar o relatório!")
print(f"   → {caminho_index}\n")

# ============================================
# SINCRONIZAÇÃO AUTOMÁTICA COM GITHUB
# ============================================
print("="*80)
print("🔄 SINCRONIZAÇÃO COM GITHUB")
print("="*80)

try:
    import subprocess
    
    print(f"✅ Arquivo index.html pronto para sincronização!")
    
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
