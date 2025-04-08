# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Adicionar coluna semantic_ncm se não existir
    try:
        cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'importar_nfe_produto' 
            AND column_name = 'semantic_ncm'
        """)
        if not cr.fetchone():
            _logger.info('Adicionando coluna semantic_ncm...')
            cr.execute("""
                ALTER TABLE importar_nfe_produto 
                ADD COLUMN semantic_ncm varchar
            """)
            _logger.info('Coluna semantic_ncm adicionada com sucesso!')
    except Exception as e:
        _logger.error('Erro ao adicionar coluna semantic_ncm: %s', str(e))
    
    # Migrar produtos
    _logger.info('Iniciando migração de produtos...')
    
    # Buscar todos os itens existentes
    old_items = env['importar_nfe.item'].search([])
    
    # Criar produtos únicos
    for item in old_items:
        # Verificar se já existe um produto com o mesmo código
        produto = env['importar_nfe.produto'].search([('codigo', '=', item.codigo)], limit=1)
        
        if not produto:
            # Criar novo produto
            produto = env['importar_nfe.produto'].create({
                'name': item.descricao,
                'codigo': item.codigo,
                'descricao': item.descricao,
                'ncm': item.ncm,
                'cfop': item.cfop,
                'unidade': item.unidade,
            })
        
        # Atualizar o item para referenciar o produto
        item.write({
            'produto_id': produto.id,
        })
    
    _logger.info('Migração de produtos concluída!') 