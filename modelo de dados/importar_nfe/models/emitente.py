# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ImportarNFeEmitente(models.Model):
    _name = 'importar_nfe.emitente'
    _description = 'Emitente de NFe'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Nome', required=True, tracking=True)
    cnpj = fields.Char(string='CNPJ', required=True, tracking=True)
    ie = fields.Char(string='Inscrição Estadual', tracking=True)
    
    # Informações de contato
    telefone = fields.Char(string='Telefone', tracking=True)
    email = fields.Char(string='E-mail', tracking=True)
    
    # Endereço
    logradouro = fields.Char(string='Logradouro', tracking=True)
    numero = fields.Char(string='Número', tracking=True)
    complemento = fields.Char(string='Complemento', tracking=True)
    bairro = fields.Char(string='Bairro', tracking=True)
    municipio = fields.Char(string='Município', tracking=True)
    uf = fields.Char(string='UF', tracking=True)
    cep = fields.Char(string='CEP', tracking=True)
    pais = fields.Char(string='País', default='BRASIL', tracking=True)
    
    # Relacionamentos
    nfe_ids = fields.One2many('importar_nfe.nfe', 'emitente_id', string='Notas Fiscais')
    
    # Restrições
    _sql_constraints = [
        ('cnpj_uniq', 'unique(cnpj)', 'CNPJ deve ser único!')
    ]
    
    # Campos de controle
    active = fields.Boolean(default=True, tracking=True)
