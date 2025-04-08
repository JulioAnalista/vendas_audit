#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para gerar embeddings a partir de descrições semânticas de produtos do módulo Importar NFe
Utiliza a API da OpenAI para gerar embeddings com o modelo text-embedding-3-small
"""

import os
import sys
import base64
import logging
import argparse
from dotenv import load_dotenv
import json
import time
import numpy as np
from openai import OpenAI

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adiciona o diretório pai ao path para importar módulos do Odoo
sys.path.append('/Users/juliocesar/Dev/OdooVSC/ODOO18-MODULE-DEVELPMENT')

# Carrega as variáveis de ambiente
load_dotenv()

# Configuração do cliente OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text, model="text-embedding-3-small"):
    """
    Gera embedding usando a API da OpenAI
    
    Args:
        text (str): Texto para gerar o embedding
        model (str): Modelo de embedding a ser usado
        
    Returns:
        list: Vetor de embedding
    """
    try:
        # Garantir que o texto não seja vazio
        if not text or text.strip() == '':
            text = "produto sem descrição"
            
        # Limitar o tamanho do texto para evitar exceder limites da API
        if len(text) > 8000:
            text = text[:8000]
            
        response = openai_client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Erro ao gerar embedding: {str(e)}")
        return None

def connect_to_odoo():
    """
    Conecta ao Odoo usando o framework do Odoo
    
    Returns:
        object: Ambiente do Odoo
    """
    try:
        import odoo
        from odoo.api import Environment
        
        # Inicializa o servidor Odoo
        odoo.tools.config.parse_config([])
        odoo.cli.server.report_configuration()
        
        # Conecta ao banco de dados
        db_name = os.getenv("ODOO_DB", "odoo18")
        odoo.service.db._create_empty_database(db_name)
        
        registry = odoo.modules.registry.Registry(db_name)
        with registry.cursor() as cr:
            env = Environment(cr, odoo.SUPERUSER_ID, {})
            return env
    except ImportError:
        logger.error("Não foi possível importar os módulos do Odoo")
        return None
    except Exception as e:
        logger.error(f"Erro ao conectar ao Odoo: {str(e)}")
        return None

def process_products(env, limit=None, force_update=False):
    """
    Processa os produtos do módulo Importar NFe, gerando embeddings a partir das descrições semânticas
    
    Args:
        env (object): Ambiente do Odoo
        limit (int, optional): Limite de produtos a serem processados
        force_update (bool, optional): Força a atualização mesmo se já tiver embeddings
        
    Returns:
        int: Número de produtos processados
    """
    if not env:
        logger.error("Ambiente Odoo não disponível")
        return 0
    
    try:
        # Obtém o modelo de produtos
        Product = env['importar_nfe.produto']
        
        # Define o domínio de busca
        domain = [('semantic_descr', '!=', False)]  # Produtos com descrição semântica
        if not force_update:
            # Apenas produtos sem embeddings
            domain.append(('ncm_vector', '=', False))
        
        # Busca os produtos
        products = Product.search(domain, limit=limit)
        logger.info(f"Encontrados {len(products)} produtos com descrição semântica para processamento")
        
        count = 0
        for product in products:
            try:
                # Prepara o texto para gerar o embedding usando a descrição semântica
                product_text = f"Nome: {product.name or ''}\n"
                product_text += f"Descrição Semântica: {product.semantic_descr or ''}\n"
                product_text += f"NCM: {product.ncm or ''}\n"
                product_text += f"CFOP: {product.cfop or ''}\n"
                product_text += f"Unidade: {product.unidade or ''}"
                
                # Gera o embedding
                embedding = get_embedding(product_text)
                if embedding:
                    # Converte o embedding para bytes
                    embedding_bytes = base64.b64encode(json.dumps(embedding).encode('utf-8'))
                    
                    # Atualiza o produto
                    product.write({
                        'ncm_vector': embedding_bytes,
                        'last_semantic_update': env['fields.Datetime'].now(),
                    })
                    
                    count += 1
                    logger.info(f"Produto {product.name} (ID: {product.id}) processado com sucesso")
                    
                    # Pausa para evitar limites de taxa da API
                    time.sleep(0.5)
                    
                    # Commit a cada 10 produtos
                    if count % 10 == 0:
                        env.cr.commit()
                        logger.info(f"Commit realizado após {count} produtos")
                
            except Exception as e:
                logger.error(f"Erro ao processar produto {product.name} (ID: {product.id}): {str(e)}")
                continue
        
        # Commit final
        env.cr.commit()
        logger.info(f"Total de {count} produtos processados com sucesso")
        return count
        
    except Exception as e:
        logger.error(f"Erro ao processar produtos: {str(e)}")
        return 0

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Gerar embeddings a partir de descrições semânticas para produtos do módulo Importar NFe')
    parser.add_argument('--limit', type=int, default=None, help='Limite de produtos a serem processados')
    parser.add_argument('--force', action='store_true', help='Força a atualização mesmo se já tiver embeddings')
    args = parser.parse_args()
    
    logger.info("Iniciando processamento de embeddings a partir de descrições semânticas")
    
    # Conecta ao Odoo
    env = connect_to_odoo()
    if not env:
        logger.error("Não foi possível conectar ao Odoo")
        return
    
    # Processa os produtos
    count = process_products(env, limit=args.limit, force_update=args.force)
    logger.info(f"Processamento concluído. {count} produtos processados.")

if __name__ == "__main__":
    main()
