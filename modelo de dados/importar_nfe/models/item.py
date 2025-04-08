# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ImportarNFeItem(models.Model):
    _name = 'importar_nfe.item'
    _description = 'Item de NFe'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Relacionamentos
    nfe_id = fields.Many2one('importar_nfe.nfe', string='NFe', required=True, ondelete='cascade', tracking=True)
    produto_id = fields.Many2one('importar_nfe.produto', string='Produto', required=True, ondelete='restrict', tracking=True)
    
    # Informações do item
    numero_item = fields.Integer(string='Número do Item', tracking=True)
    codigo = fields.Char(related='produto_id.codigo', string='Código do Produto', store=True)
    descricao = fields.Text(related='produto_id.descricao', string='Descrição', store=True)
    ncm = fields.Char(related='produto_id.ncm', string='NCM', store=True)
    cfop = fields.Char(related='produto_id.cfop', string='CFOP', store=True)
    unidade = fields.Char(related='produto_id.unidade', string='Unidade de Medida', store=True)
    
    # Valores
    quantidade = fields.Float(string='Quantidade', digits=(16, 4), tracking=True)
    valor_unitario = fields.Float(string='Valor Unitário', digits=(16, 4), tracking=True)
    valor_total = fields.Float(string='Valor Total', digits=(16, 2), tracking=True)
    valor_desconto = fields.Float(string='Valor do Desconto', digits=(16, 2), tracking=True)
    
    # Impostos
    valor_icms = fields.Float(string='Valor ICMS', digits=(16, 2), tracking=True)
    valor_ipi = fields.Float(string='Valor IPI', digits=(16, 2), tracking=True)
    valor_pis = fields.Float(string='Valor PIS', digits=(16, 2), tracking=True)
    valor_cofins = fields.Float(string='Valor COFINS', digits=(16, 2), tracking=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Verificar se o item já existe para a NFe
            if 'nfe_id' in vals and 'produto_id' in vals:
                existing_item = self.search([
                    ('nfe_id', '=', vals['nfe_id']),
                    ('produto_id', '=', vals['produto_id']),
                    ('numero_item', '=', vals.get('numero_item', 0))
                ], limit=1)
                
                if existing_item:
                    # Item já existe, não criar duplicado
                    continue
        
        return super(ImportarNFeItem, self).create(vals_list)
