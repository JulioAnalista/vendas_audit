# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import json
import logging

_logger = logging.getLogger(__name__)

class ImportarNFeProduto(models.Model):
    _name = 'importar_nfe.produto'
    _description = 'Produto'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Nome', required=True, tracking=True)
    codigo = fields.Char(string='Código', required=True, tracking=True)
    descricao = fields.Text(string='Descrição', tracking=True)
    ncm = fields.Char(string='NCM', tracking=True)
    cfop = fields.Char(string='CFOP', tracking=True)
    unidade = fields.Char(string='Unidade de Medida', tracking=True)
    
    # Campos semânticos para densificação dos produtos
    semantic_ncm = fields.Char(string='NCM Semântico', tracking=True, 
                              help='NCM retornado da busca semântica')
    ncm_vector = fields.Binary(string='Vetor NCM', attachment=True,
                              help='Embeddings vetoriais gerados para o NCM')
    ncm_vector_sample = fields.Char(string='Amostra do Embedding', compute='_compute_ncm_vector_sample',
                                   help='Amostra dos primeiros 10 valores do embedding')
    semantic_descr = fields.Text(string='Descrição Semântica', tracking=True,
                               help='Descrição enriquecida gerada por LLM')
    last_semantic_update = fields.Datetime(string='Última Atualização Semântica', readonly=True)
    
    # Campos de controle
    active = fields.Boolean(default=True, tracking=True)
    
    # Relacionamentos
    nfe_item_ids = fields.One2many('importar_nfe.item', 'produto_id', string='Itens de NFe')
    
    # Restrições
    _sql_constraints = [
        ('codigo_uniq', 'unique(codigo)', 'O código do produto deve ser único!')
    ]
    
    def action_generate_embeddings(self):
        """Gera embeddings e descrição semântica para o produto"""
        self.ensure_one()
        
        try:
            processor = self.env['importar_nfe.semantic.processor']
            result = processor.process_product(self.id)
            
            if result:
                self.write({'last_semantic_update': fields.Datetime.now()})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Sucesso'),
                        'message': _('Informações semânticas geradas com sucesso.'),
                        'sticky': False,
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Erro'),
                        'message': _('Não foi possível gerar as informações semânticas.'),
                        'sticky': False,
                        'type': 'danger',
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erro'),
                    'message': str(e),
                    'sticky': False,
                    'type': 'danger',
                }
            }
    
    def action_generate_pharmacy_description(self):
        """Gera apenas a descrição farmacêutica para o produto"""
        self.ensure_one()
        
        try:
            processor = self.env['importar_nfe.semantic.processor']
            pharmacy_description = processor.generate_pharmacy_description(self.name, self.descricao)
            
            if pharmacy_description:
                self.write({
                    'semantic_descr': pharmacy_description,
                    'last_semantic_update': fields.Datetime.now()
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Sucesso'),
                        'message': _('Descrição farmacêutica gerada com sucesso.'),
                        'sticky': False,
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Erro'),
                        'message': _('Não foi possível gerar a descrição farmacêutica.'),
                        'sticky': False,
                        'type': 'danger',
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erro'),
                    'message': str(e),
                    'sticky': False,
                    'type': 'danger',
                }
            }
    
    def action_generate_embedding_from_semantic(self):
        """Gera embedding a partir da descrição semântica do produto"""
        self.ensure_one()
        
        if not self.semantic_descr:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Aviso'),
                    'message': _('Este produto não possui descrição semântica. Gere a descrição primeiro.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        try:
            processor = self.env['importar_nfe.semantic.processor']
            result = processor.generate_embedding_from_semantic(self.id)
            
            if result:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Sucesso'),
                        'message': _('Embedding gerado com sucesso a partir da descrição semântica.'),
                        'sticky': False,
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Erro'),
                        'message': _('Não foi possível gerar o embedding.'),
                        'sticky': False,
                        'type': 'danger',
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erro'),
                    'message': str(e),
                    'sticky': False,
                    'type': 'danger',
                }
            }
    
    @api.model
    def action_generate_embeddings_from_semantic_batch(self, limit=50):
        """Gera embeddings a partir da descrição semântica para um lote de produtos"""
        try:
            processor = self.env['importar_nfe.semantic.processor']
            result = processor.generate_embeddings_from_semantic_batch(limit=limit)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Processamento em Lote'),
                    'message': _('Total: %(total)s, Processados: %(processed)s, Falhas: %(failed)s') % result,
                    'sticky': False,
                    'type': 'info',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erro'),
                    'message': str(e),
                    'sticky': False,
                    'type': 'danger',
                }
            }
    
    @api.model
    def action_generate_embeddings_batch(self, limit=50):
        """Gera embeddings e descrições semânticas para um lote de produtos"""
        try:
            processor = self.env['importar_nfe.semantic.processor']
            result = processor.process_products_batch(limit=limit)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Processamento em Lote'),
                    'message': _('Total: %(total)s, Processados: %(processed)s, Falhas: %(failed)s') % result,
                    'sticky': False,
                    'type': 'info',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erro'),
                    'message': str(e),
                    'sticky': False,
                    'type': 'danger',
                }
            }
            
    def has_embeddings(self):
        """Verifica se o produto já possui embeddings"""
        self.ensure_one()
        return bool(self.ncm_vector)

    @api.depends('ncm_vector')
    def _compute_ncm_vector_sample(self):
        """
        Extrai uma amostra dos primeiros 10 valores do embedding para exibição na interface
        """
        for record in self:
            if not record.ncm_vector:
                record.ncm_vector_sample = False
                continue
                
            try:
                # Decodifica o embedding armazenado em base64
                embedding_bytes = base64.b64decode(record.ncm_vector)
                embedding = json.loads(embedding_bytes.decode('utf-8'))
                
                # Extrai os primeiros 10 valores (ou menos se o embedding for menor)
                sample_size = min(10, len(embedding))
                sample = embedding[:sample_size]
                
                # Formata os valores para exibição (limitando a 4 casas decimais)
                formatted_sample = [f"{val:.4f}" for val in sample]
                record.ncm_vector_sample = "[" + ", ".join(formatted_sample) + ", ...]"
            except Exception as e:
                _logger.error(f"Erro ao extrair amostra do embedding: {str(e)}")
                record.ncm_vector_sample = "Erro ao processar embedding"
