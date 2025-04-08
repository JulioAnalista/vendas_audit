# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class VendasDashboardController(http.Controller):
    
    @http.route('/visualizacao_vendas/dados_dashboard', type='json', auth='user')
    def obter_dados_dashboard(self, **kw):
        """Rota para obter dados do dashboard de vendas"""
        try:
            periodo = kw.get('periodo', False)
            
            VendasAnalise = request.env['visualizacao_vendas.analise']
            dados = VendasAnalise.obter_dados_dashboard(periodo=periodo)
            
            return {
                'status': 'success',
                'data': dados
            }
        except Exception as e:
            _logger.error("Erro ao obter dados do dashboard: %s", str(e))
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @http.route('/visualizacao_vendas/produtos_mais_vendidos', type='json', auth='user')
    def obter_produtos_mais_vendidos(self, **kw):
        """Rota para obter os produtos mais vendidos"""
        try:
            periodo = kw.get('periodo', False)
            limite = int(kw.get('limite', 10))
            
            ProdutosAnalise = request.env['visualizacao_vendas.produtos_analise']
            dados = ProdutosAnalise.obter_produtos_mais_vendidos(periodo=periodo, limite=limite)
            
            return {
                'status': 'success',
                'data': dados
            }
        except Exception as e:
            _logger.error("Erro ao obter produtos mais vendidos: %s", str(e))
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @http.route('/visualizacao_vendas/dashboard', type='http', auth='user')
    def dashboard(self, **kw):
        """Página principal do dashboard"""
        # Modelo usado para verificar permissões
        if not request.env.user.has_group('base.group_user'):
            return request.render('http_routing.403')
            
        return request.render('visualizacao_vendas.dashboard_view', {
            'title': 'Dashboard de Vendas',
            'page_name': 'dashboard_vendas',
            'user': request.env.user
        }) 