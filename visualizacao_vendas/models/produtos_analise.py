# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class ProdutosAnalise(models.Model):
    _name = 'visualizacao_vendas.produtos_analise'
    _description = 'Análise de Produtos Vendidos'
    _auto = False
    _order = 'quantidade_vendida desc, valor_total desc'
    
    # Campos para identificação do produto
    produto_id = fields.Many2one('importar_nfe.produto', string='Produto', readonly=True)
    name = fields.Char(string='Nome do Produto', readonly=True)
    codigo = fields.Char(string='Código do Produto', readonly=True)
    ncm = fields.Char(string='NCM', readonly=True)
    unidade = fields.Char(string='Unidade de Medida', readonly=True)
    
    # Métricas
    quantidade_vendida = fields.Float(string='Quantidade Vendida', readonly=True)
    valor_unitario_medio = fields.Float(string='Valor Unitário Médio', readonly=True)
    valor_total = fields.Float(string='Valor Total', readonly=True)
    
    # Campos para agrupamento e filtragem
    data_emissao_dia = fields.Date(string='Dia de Emissão', readonly=True)
    data_emissao_mes = fields.Char(string='Mês de Emissão', readonly=True)
    data_emissao_ano = fields.Char(string='Ano de Emissão', readonly=True)
    emitente_id = fields.Many2one('importar_nfe.emitente', string='Emitente', readonly=True)
    
    def init(self):
        """Inicializa a view de análise de produtos vendidos"""
        tools = self.env['ir.model.tools']
        self._cr.execute("""
            DROP VIEW IF EXISTS visualizacao_vendas_produtos_analise CASCADE;
            CREATE VIEW visualizacao_vendas_produtos_analise AS (
                SELECT
                    ROW_NUMBER() OVER () as id,
                    item.produto_id as produto_id,
                    produto.name as name,
                    produto.codigo as codigo,
                    produto.ncm as ncm,
                    produto.unidade as unidade,
                    SUM(item.quantidade) as quantidade_vendida,
                    CASE 
                        WHEN SUM(item.quantidade) > 0 
                        THEN SUM(item.valor_total) / SUM(item.quantidade)
                        ELSE 0
                    END as valor_unitario_medio,
                    SUM(item.valor_total) as valor_total,
                    DATE(nfe.data_emissao AT TIME ZONE 'UTC') as data_emissao_dia,
                    TO_CHAR(DATE_TRUNC('month', nfe.data_emissao AT TIME ZONE 'UTC'), 'MM/YYYY') as data_emissao_mes,
                    TO_CHAR(DATE_TRUNC('year', nfe.data_emissao AT TIME ZONE 'UTC'), 'YYYY') as data_emissao_ano,
                    nfe.emitente_id as emitente_id
                FROM
                    importar_nfe_item item
                    JOIN importar_nfe_nfe nfe ON item.nfe_id = nfe.id
                    JOIN importar_nfe_produto produto ON item.produto_id = produto.id
                WHERE
                    nfe.tipo_operacao = 'saida'
                    AND nfe.state = 'processed'
                GROUP BY
                    item.produto_id,
                    produto.name,
                    produto.codigo,
                    produto.ncm,
                    produto.unidade,
                    data_emissao_dia,
                    data_emissao_mes,
                    data_emissao_ano,
                    nfe.emitente_id
            )
        """)
    
    def action_ver_produto(self):
        """Ação para ver os detalhes do produto"""
        self.ensure_one()
        return {
            'name': _('Detalhes do Produto'),
            'view_mode': 'form',
            'res_model': 'importar_nfe.produto',
            'res_id': self.produto_id.id,
            'type': 'ir.actions.act_window',
        }
    
    def action_ver_vendas_produto(self):
        """Ação para ver as vendas de um produto específico"""
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
            ('nfe_id.tipo_operacao', '=', 'saida'),
            ('nfe_id.state', '=', 'processed'),
            ('produto_id', '=', self.produto_id.id)
        ]
        
        if inicio and fim:
            domain.extend([
                ('nfe_id.data_emissao', '>=', fields.Datetime.to_string(inicio)),
                ('nfe_id.data_emissao', '<', fields.Datetime.to_string(fim))
            ])
        
        return {
            'name': _('Vendas do Produto'),
            'view_mode': 'tree,form',
            'res_model': 'importar_nfe.item',
            'domain': domain,
            'type': 'ir.actions.act_window',
        }
    
    @api.model
    def obter_produtos_mais_vendidos(self, periodo=False, limite=10):
        """Obtém os produtos mais vendidos no período especificado"""
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
        
        self._cr.execute("""
            SELECT 
                p.name as nome,
                p.codigo as codigo,
                SUM(i.quantidade) as quantidade,
                SUM(i.valor_total) as valor_total
            FROM 
                importar_nfe_item i
                JOIN importar_nfe_nfe n ON i.nfe_id = n.id
                JOIN importar_nfe_produto p ON i.produto_id = p.id
            WHERE 
                n.tipo_operacao = 'saida'
                AND n.state = 'processed'
                AND n.data_emissao >= %s
                AND n.data_emissao <= %s
            GROUP BY 
                p.name, p.codigo
            ORDER BY 
                quantidade DESC, valor_total DESC
            LIMIT %s
        """, (fields.Datetime.to_string(data_inicio), fields.Datetime.to_string(data_fim), limite))
        
        resultados = self._cr.dictfetchall()
        
        # Formatação para retorno
        produtos = []
        for resultado in resultados:
            produtos.append({
                'nome': resultado['nome'],
                'codigo': resultado['codigo'],
                'quantidade': resultado['quantidade'],
                'valor_total': resultado['valor_total']
            })
        
        return {
            'periodo': periodo or 'mes',
            'produtos': produtos
        } 