# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ImportarNFeArquivo(models.TransientModel):
    _name = 'importar_nfe.arquivo'
    _description = 'Arquivo XML para importação'
    
    wizard_id = fields.Many2one('importar_nfe.wizard', string='Wizard', ondelete='cascade')
    arquivo = fields.Binary(string='Arquivo XML', required=True)
    nome = fields.Char(string='Nome do Arquivo')
