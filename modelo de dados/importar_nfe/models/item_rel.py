# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ImportarNFeItemRel(models.Model):
    _name = 'importar_nfe.nfe.item'
    _description = 'Item de NFe (Relacionamento)'
    
    # Relacionamentos
    nfe_id = fields.Many2one('importar_nfe.nfe', string='NFe', required=True, ondelete='cascade')
    item_id = fields.Many2one('importar_nfe.item', string='Item', required=True, ondelete='cascade')
    
    # Informações do item
    numero_item = fields.Integer(string='Número do Item', related='item_id.numero_item', store=True)
    produto_id = fields.Many2one('importar_nfe.produto', string='Produto', related='item_id.produto_id', store=True)
    
    # Valores
    quantidade = fields.Float(string='Quantidade', related='item_id.quantidade', store=True)
    valor_unitario = fields.Float(string='Valor Unitário', related='item_id.valor_unitario', store=True)
    valor_total = fields.Float(string='Valor Total', related='item_id.valor_total', store=True)
    valor_desconto = fields.Float(string='Valor do Desconto', related='item_id.valor_desconto', store=True)
