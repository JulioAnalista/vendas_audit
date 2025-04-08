#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para gerar descrições farmacêuticas para produtos do módulo Importar NFe
Utiliza a API da OpenAI para gerar descrições explicativas para produtos de farmácia
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv
import json
import time
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

# Prompt para descrição farmacêutica
PHARMACY_PROMPT = """\
Considere que este produto "{nome}" com a descrição "{descricao}" é vendido numa farmácia.
Crie uma descrição mais explicativa do que é o produto. Lembre-se que farmácias vendem diversos tipos de produtos, 
não apenas medicamentos, mas também cosméticos, produtos de higiene, alimentos, bebidas, doces e outros itens.

Com base no nome e descrição, identifique a categoria mais adequada e forneça:
1. Tipo/categoria do produto (medicamento, cosmético, alimento, bebida, etc.)
2. Principais características e finalidade
3. Informações relevantes para o consumidor
4. Formato de apresentação ou modo de uso, se aplicável

Mantenha a descrição concisa (máximo 3-4 frases) e focada nas informações mais relevantes.
"""

def generate_pharmacy_description(product_name, product_description):
    """
    Gera uma descrição farmacêutica para o produto usando a API da OpenAI
    
    Args:
        product_name (str): Nome do produto
        product_description (str): Descrição original do produto
        
    Returns:
        str: Descrição farmacêutica gerada
    """
    try:
        # Garantir que os textos não sejam vazios
        product_name = product_name or "Produto sem nome"
        product_description = product_description or "Sem descrição disponível"
        
        # Preparar o prompt
        prompt = PHARMACY_PROMPT.format(
            nome=product_name,
            descricao=product_description
        )
        
        response = openai_client.chat.completions.create(
            model="gpt-40-mini",
            messages=[
                {"role": "system", "content": "Você é um especialista em produtos farmacêuticos."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erro ao gerar descrição farmacêutica: {str(e)}")
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
    Processa os produtos do módulo Importar NFe, gerando descrições farmacêuticas
    
    Args:
        env (object): Ambiente do Odoo
        limit (int, optional): Limite de produtos a serem processados
        force_update (bool, optional): Força a atualização mesmo se já tiver descrição semântica
        
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
        domain = []
        if not force_update:
            # Apenas produtos sem descrição semântica
            domain.append(('semantic_descr', '=', False))
        
        # Busca os produtos
        products = Product.search(domain, limit=limit)
        logger.info(f"Encontrados {len(products)} produtos para processamento")
        
        count = 0
        for product in products:
            try:
                # Gera a descrição farmacêutica
                pharmacy_description = generate_pharmacy_description(
                    product.name, 
                    product.descricao
                )
                
                if pharmacy_description:
                    # Atualiza o produto
                    product.write({
                        'semantic_descr': pharmacy_description,
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
    parser = argparse.ArgumentParser(description='Gerar descrições farmacêuticas para produtos do módulo Importar NFe')
    parser.add_argument('--limit', type=int, default=None, help='Limite de produtos a serem processados')
    parser.add_argument('--force', action='store_true', help='Força a atualização mesmo se já tiver descrição semântica')
    args = parser.parse_args()
    
    logger.info("Iniciando processamento de descrições farmacêuticas para produtos")
    
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
