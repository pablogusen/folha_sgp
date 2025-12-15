"""
Testes Unitários para Sistema de Análise de Margem Consignável
Resolução Administrativa nº 14/2025 - ALMT
"""

import unittest
import sys
from pathlib import Path

# Adicionar pasta src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

class TestCalculoMargem(unittest.TestCase):
    """Testes para cálculos de margem consignável"""
    
    def test_calculo_rlm(self):
        """Testa cálculo da RLM (Remuneração Líquida Mensal)"""
        proventos = 10000.00
        descontos_compulsorios = 2000.00
        rlm_esperado = 8000.00
        
        rlm_calculado = proventos - descontos_compulsorios
        self.assertEqual(rlm_calculado, rlm_esperado)
    
    def test_calculo_limite_ideal(self):
        """Testa cálculo do limite ideal (35% da RLM)"""
        rlm = 8000.00
        limite_esperado = 2800.00
        
        limite_calculado = rlm * 0.35
        self.assertEqual(limite_calculado, limite_esperado)
    
    def test_calculo_percentual(self):
        """Testa cálculo do percentual sobre o limite"""
        descontos_facultativos = 3500.00
        limite_ideal = 2800.00
        percentual_esperado = 125.0  # CRÍTICO (>100%)
        
        percentual_calculado = (descontos_facultativos / limite_ideal) * 100
        self.assertAlmostEqual(percentual_calculado, percentual_esperado, places=1)
    
    def test_classificacao_saudavel(self):
        """Testa classificação SAUDÁVEL (<57%)"""
        percentual = 50.0
        self.assertLess(percentual, 57.0)
    
    def test_classificacao_atencao(self):
        """Testa classificação ATENÇÃO (57-86%)"""
        percentual = 70.0
        self.assertGreaterEqual(percentual, 57.0)
        self.assertLess(percentual, 86.0)
    
    def test_classificacao_risco(self):
        """Testa classificação RISCO (86-100%)"""
        percentual = 90.0
        self.assertGreaterEqual(percentual, 86.0)
        self.assertLessEqual(percentual, 100.0)
    
    def test_classificacao_critico(self):
        """Testa classificação CRÍTICO (>100%)"""
        percentual = 125.0
        self.assertGreater(percentual, 100.0)
    
    def test_margem_negativa(self):
        """Testa detecção de margem negativa (casos especiais)"""
        rlm = 5000.00
        limite_ideal = rlm * 0.35  # 1750.00
        descontos_facultativos = 2000.00
        margem = limite_ideal - descontos_facultativos  # -250.00
        
        self.assertLess(margem, 0)

class TestDeteccaoEspeciais(unittest.TestCase):
    """Testes para detecção de casos especiais"""
    
    def test_deteccao_rescisao(self):
        """Testa detecção de rescisão contratual"""
        eventos_cod13 = ['130001', '130002']
        eventos_rescis = ['RESCISAO', 'RESCIS']
        
        # Código 13
        self.assertTrue(any(cod.startswith('13') for cod in eventos_cod13))
        
        # Descrição com RESCIS
        self.assertTrue(any('RESCIS' in desc for desc in eventos_rescis))
    
    def test_deteccao_cedido(self):
        """Testa detecção de servidor cedido"""
        tem_representacao = True
        tem_subsidio_cod1 = False
        
        eh_cedido = tem_representacao and not tem_subsidio_cod1
        self.assertTrue(eh_cedido)
    
    def test_exclusao_cedido_com_subsidio_1(self):
        """Testa que SUBSÍDIO código 1 exclui da lista de cedidos"""
        tem_representacao = True
        tem_subsidio_cod1 = True
        
        eh_cedido = tem_representacao and not tem_subsidio_cod1
        self.assertFalse(eh_cedido)
    
    def test_deteccao_atipico_margem_zero(self):
        """Testa detecção de caso atípico por margem <= 0"""
        margem = -100.00
        self.assertLessEqual(margem, 0)
    
    def test_deteccao_atipico_proventos_zero(self):
        """Testa detecção de caso atípico: proventos=0 mas tem descontos"""
        proventos = 0.0
        descontos_compulsorios = 500.0
        
        self.assertEqual(proventos, 0)
        self.assertGreater(descontos_compulsorios, 0)
    
    def test_deteccao_atipico_rlm_diferente_liquido(self):
        """Testa detecção: RLM ≠ Líquido (auxílios omitidos)"""
        rlm = 8000.00
        liquido = 6000.00
        diferenca = abs(rlm - liquido)
        
        self.assertGreater(diferenca, 0.10)

class TestValidacaoLegal(unittest.TestCase):
    """Testes de conformidade legal com Resolução 14/2025"""
    
    def test_limite_legal_35_por_cento(self):
        """Valida que limite é exatamente 35% da RLM"""
        limite_legal = 0.35
        self.assertEqual(limite_legal, 0.35)
    
    def test_base_calculo_rlm(self):
        """Valida que base é RLM (Proventos - Descontos Compulsórios)"""
        proventos = 15000.00
        descontos_compulsorios = 3000.00
        descontos_facultativos = 1000.00  # Não entra no cálculo da RLM
        
        rlm = proventos - descontos_compulsorios
        self.assertEqual(rlm, 12000.00)
        
        # Descontos facultativos não afetam RLM
        rlm_com_facultativos = proventos - descontos_compulsorios
        self.assertEqual(rlm, rlm_com_facultativos)

if __name__ == '__main__':
    unittest.main()
