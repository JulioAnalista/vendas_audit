# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import logging

_logger = logging.getLogger(__name__)

class VendasAnalise(models.Model):
    _name = 'visualizacao_vendas.analise'
    _description = 'Análise de Vendas'
    _auto = False
    _order = 'data_emissao desc'
    
    # Campos para agrupamento e filtragem
    name = fields.Char(string='Referência', readonly=True)
    data_emissao = fields.Datetime(string='Data de Emissão', readonly=True)
    data_emissao_dia = fields.Date(string='Dia de Emissão', readonly=True)
    data_emissao_mes = fields.Char(string='Mês de Emissão', readonly=True)
    data_emissao_ano = fields.Char(string='Ano de Emissão', readonly=True)
    
    # Métricas
    quantidade_nfe = fields.Integer(string='Quantidade de NFes', readonly=True)
    valor_produtos = fields.Float(string='Valor dos Produtos', readonly=True)
    valor_frete = fields.Float(string='Valor do Frete', readonly=True)
    valor_total = fields.Float(string='Valor Total', readonly=True)
    
    # Relacionamentos
    emitente_id = fields.Many2one('importar_nfe.emitente', string='Emitente', readonly=True)
    destinatario_id = fields.Many2one('importar_nfe.destinatario', string='Destinatário', readonly=True)
    
    def init(self):
        """Inicializa a view de análise de vendas"""
        tools = self.env['ir.model.tools']
        self._cr.execute("""
            DROP VIEW IF EXISTS visualizacao_vendas_analise CASCADE;
            CREATE VIEW visualizacao_vendas_analise AS (
                SELECT
                    nfe.id as id,
                    nfe.name as name,
                    nfe.data_emissao as data_emissao,
                    DATE(nfe.data_emissao AT TIME ZONE 'UTC') as data_emissao_dia,
                    TO_CHAR(DATE_TRUNC('month', nfe.data_emissao AT TIME ZONE 'UTC'), 'MM/YYYY') as data_emissao_mes,
                    TO_CHAR(DATE_TRUNC('year', nfe.data_emissao AT TIME ZONE 'UTC'), 'YYYY') as data_emissao_ano,
                    1 as quantidade_nfe,
                    nfe.valor_produtos as valor_produtos,
                    nfe.valor_frete as valor_frete,
                    nfe.valor_total as valor_total,
                    nfe.emitente_id as emitente_id,
                    nfe.destinatario_id as destinatario_id
                FROM
                    importar_nfe_nfe nfe
                WHERE
                    nfe.tipo_operacao = 'saida'
                    AND nfe.state = 'processed'
            )
        """)
    
    def action_ver_detalhes(self):
        """Ação para ver os detalhes das NFes"""
        self.ensure_one()
        return {
            'name': _('Detalhes da NFe'),
            'view_mode': 'form',
            'res_model': 'importar_nfe.nfe',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
        }
    
    def action_ver_periodo(self):
        """Ação para ver as NFes de um período específico"""
        self.ensure_one()
        
        # Determinar o período baseado no registro atual
        inicio = False
        fim = False
        
        if self.data_emissao_dia:
            inicio = self.data_emissao_dia
            fim = self.data_emissao_dia + timedelta(days=1)
        elif self.data_emissao_mes:
            mes, ano = self.data_emissao_mes.split('/')
            inicio = datetime(int(ano), int(mes), 1).date()
            if int(mes) == 12:
                fim = datetime(int(ano) + 1, 1, 1).date()
            else:
                fim = datetime(int(ano), int(mes) + 1, 1).date()
        elif self.data_emissao_ano:
            inicio = datetime(int(self.data_emissao_ano), 1, 1).date()
            fim = datetime(int(self.data_emissao_ano) + 1, 1, 1).date()
        
        domain = [
            ('tipo_operacao', '=', 'saida'),
            ('state', '=', 'processed')
        ]
        
        if inicio and fim:
            domain.extend([
                ('data_emissao', '>=', fields.Datetime.to_string(inicio)),
                ('data_emissao', '<', fields.Datetime.to_string(fim))
            ])
        
        return {
            'name': _('NFes do Período'),
            'view_mode': 'tree,form',
            'res_model': 'importar_nfe.nfe',
            'domain': domain,
            'type': 'ir.actions.act_window',
        }
    
    @api.model
    def obter_dados_dashboard(self, periodo=False):
        """Obtém dados para o dashboard de vendas"""
        # Definir período padrão (últimos 30 dias)
        data_fim = fields.Datetime.now()
        data_inicio = data_fim - timedelta(days=30)
        
        if periodo:
            if periodo == 'semana':
                data_inicio = data_fim - timedelta(days=7)
            elif periodo == 'mes':
                data_inicio = data_fim - relativedelta(months=1)
            elif periodo == 'trimestre':
                data_inicio = data_fim - relativedelta(months=3)
            elif periodo == 'ano':
                data_inicio = data_fim - relativedelta(years=1)
        
        # Consultar dados de vendas no período
        domain = [
            ('tipo_operacao', '=', 'saida'),
            ('state', '=', 'processed'),
            ('data_emissao', '>=', fields.Datetime.to_string(data_inicio)),
            ('data_emissao', '<=', fields.Datetime.to_string(data_fim))
        ]
        
        nfes = self.env['importar_nfe.nfe'].search(domain)
        
        # Preparar dados para o dashboard
        total_nfes = len(nfes)
        total_valor = sum(nfes.mapped('valor_total'))
        
        # Dados para gráfico de vendas por dia
        vendas_por_dia = {}
        for nfe in nfes:
            data = fields.Datetime.context_timestamp(self, nfe.data_emissao).date()
            data_str = data.strftime('%d/%m/%Y')
            
            if data_str not in vendas_por_dia:
                vendas_por_dia[data_str] = {
                    'quantidade': 0,
                    'valor': 0.0
                }
            
            vendas_por_dia[data_str]['quantidade'] += 1
            vendas_por_dia[data_str]['valor'] += nfe.valor_total
        
        # Preparar dados para retorno
        return {
            'periodo': periodo or 'mes',
            'total_nfes': total_nfes,
            'total_valor': total_valor,
            'vendas_por_dia': vendas_por_dia
        } 