# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import json
import logging
import os
import time
from dotenv import load_dotenv
import requests

# Carrega as variáveis de ambiente
load_dotenv()

_logger = logging.getLogger(__name__)

class SemanticProcessor(models.AbstractModel):
    _name = 'importar_nfe.semantic.processor'
    _description = 'Processador Semântico para Produtos'

    PROMPT_FARMACIA = """
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

    @api.model
    def _get_openai_api_key(self):
        """Obtém a chave da API da OpenAI das variáveis de ambiente ou parâmetros do sistema"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Tenta obter do parâmetro do sistema
            api_key = self.env['ir.config_parameter'].sudo().get_param('importar_nfe.openai_api_key')
        
        if not api_key:
            raise UserError(_('Chave da API da OpenAI não configurada. Configure nas variáveis de ambiente ou nos parâmetros do sistema.'))
        
        return api_key

    @api.model
    def generate_embedding(self, text, model="text-embedding-3-small"):
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
                
            api_key = self._get_openai_api_key()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "input": text,
                "model": model
            }
            
            response = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()['data'][0]['embedding']
            else:
                _logger.error(f"Erro na API da OpenAI: {response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"Erro ao gerar embedding: {str(e)}")
            return None

    @api.model
    def generate_semantic_description(self, product_name, product_description, ncm_code):
        """
        Gera uma descrição semântica enriquecida usando a API da OpenAI
        
        Args:
            product_name (str): Nome do produto
            product_description (str): Descrição original do produto
            ncm_code (str): Código NCM do produto
            
        Returns:
            str: Descrição semântica enriquecida
        """
        try:
            api_key = self._get_openai_api_key()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            prompt = self.PROMPT_FARMACIA.format(
                nome=product_name,
                descricao=product_description or 'Não disponível',
                ncm=ncm_code or 'Não disponível'
            )
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Você é um especialista em produtos farmacêuticos."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 250,
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                _logger.error(f"Erro na API da OpenAI: {response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"Erro ao gerar descrição semântica: {str(e)}")
            return None

    @api.model
    def generate_pharmacy_description(self, product_name, product_description):
        """
        Gera uma descrição farmacêutica para o produto usando a API da OpenAI
        
        Args:
            product_name (str): Nome do produto
            product_description (str): Descrição original do produto
            
        Returns:
            str: Descrição farmacêutica gerada
        """
        try:
            api_key = self._get_openai_api_key()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            # Garantir que os textos não sejam vazios
            product_name = product_name or "Produto sem nome"
            product_description = product_description or "Sem descrição disponível"
            
            # Preparar o prompt
            prompt = self.PROMPT_FARMACIA.format(
                nome=product_name,
                descricao=product_description
            )
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Você é um especialista em produtos farmacêuticos."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 250,
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                _logger.error(f"Erro na API da OpenAI: {response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"Erro ao gerar descrição farmacêutica: {str(e)}")
            return None

    @api.model
    def process_product(self, product_id):
        """
        Processa um produto específico, gerando embeddings e descrição semântica
        
        Args:
            product_id (int): ID do produto a ser processado
            
        Returns:
            bool: True se o processamento foi bem-sucedido, False caso contrário
        """
        try:
            product = self.env['importar_nfe.produto'].browse(product_id)
            if not product.exists():
                return False
                
            # Prepara o texto para gerar o embedding
            product_text = f"Nome: {product.name or ''}\n"
            product_text += f"Descrição: {product.descricao or ''}\n"
            product_text += f"NCM: {product.ncm or ''}\n"
            product_text += f"CFOP: {product.cfop or ''}\n"
            product_text += f"Unidade: {product.unidade or ''}"
            
            # Gera o embedding
            embedding = self.generate_embedding(product_text)
            if not embedding:
                return False
                
            # Converte o embedding para bytes
            embedding_bytes = base64.b64encode(json.dumps(embedding).encode('utf-8'))
            
            # Gera a descrição farmacêutica
            pharmacy_description = self.generate_pharmacy_description(
                product.name, 
                product.descricao
            )
            
            # Atualiza o produto
            product.write({
                'ncm_vector': embedding_bytes,
                'semantic_descr': pharmacy_description,
                'semantic_ncm': product.ncm,  # Por enquanto, usa o mesmo NCM
                'last_semantic_update': fields.Datetime.now()
            })
            
            return True
            
        except Exception as e:
            _logger.error(f"Erro ao processar produto ID {product_id}: {str(e)}")
            return False

    @api.model
    def process_products_batch(self, product_ids=None, limit=50):
        """
        Processa um lote de produtos, gerando embeddings e descrições semânticas
        
        Args:
            product_ids (list, optional): Lista de IDs de produtos a serem processados
            limit (int, optional): Limite de produtos a serem processados se product_ids não for fornecido
            
        Returns:
            dict: Dicionário com informações sobre o processamento
        """
        try:
            Product = self.env['importar_nfe.produto']
            
            if product_ids:
                products = Product.browse(product_ids)
            else:
                # Busca produtos sem embeddings
                products = Product.search([('ncm_vector', '=', False)], limit=limit)
                
            total = len(products)
            processed = 0
            failed = 0
            
            for product in products:
                try:
                    result = self.process_product(product.id)
                    if result:
                        processed += 1
                    else:
                        failed += 1
                        
                    # Pausa para evitar limites de taxa da API
                    time.sleep(0.5)
                    
                except Exception as e:
                    _logger.error(f"Erro ao processar produto {product.name} (ID: {product.id}): {str(e)}")
                    failed += 1
                    continue
            
            return {
                'total': total,
                'processed': processed,
                'failed': failed
            }
            
        except Exception as e:
            _logger.error(f"Erro ao processar lote de produtos: {str(e)}")
            return {
                'total': 0,
                'processed': 0,
                'failed': 0,
                'error': str(e)
            }

    @api.model
    def generate_embedding_from_semantic(self, product_id):
        """
        Gera embedding a partir da descrição semântica do produto
        
        Args:
            product_id (int): ID do produto
            
        Returns:
            bool: True se o processamento foi bem-sucedido, False caso contrário
        """
        try:
            product = self.env['importar_nfe.produto'].browse(product_id)
            if not product.exists() or not product.semantic_descr:
                return False
                
            # Prepara o texto para gerar o embedding usando a descrição semântica
            # Isso aproveita a densificação que já fizemos
            product_text = f"Nome: {product.name or ''}\n"
            product_text += f"Descrição Semântica: {product.semantic_descr or ''}\n"
            product_text += f"NCM: {product.ncm or ''}\n"
            product_text += f"CFOP: {product.cfop or ''}\n"
            product_text += f"Unidade: {product.unidade or ''}"
            
            # Gera o embedding
            embedding = self.generate_embedding(product_text)
            if not embedding:
                return False
                
            # Converte o embedding para bytes
            embedding_bytes = base64.b64encode(json.dumps(embedding).encode('utf-8'))
            
            # Atualiza o produto
            product.write({
                'ncm_vector': embedding_bytes,
                'last_semantic_update': fields.Datetime.now()
            })
            
            return True
            
        except Exception as e:
            _logger.error(f"Erro ao gerar embedding a partir da descrição semântica para o produto ID {product_id}: {str(e)}")
            return False
            
    @api.model
    def generate_embeddings_from_semantic_batch(self, product_ids=None, limit=50):
        """
        Gera embeddings a partir da descrição semântica para um lote de produtos
        
        Args:
            product_ids (list, optional): Lista de IDs de produtos a serem processados
            limit (int, optional): Limite de produtos a serem processados se product_ids não for fornecido
            
        Returns:
            dict: Dicionário com informações sobre o processamento
        """
        try:
            Product = self.env['importar_nfe.produto']
            
            if product_ids:
                products = Product.browse(product_ids)
            else:
                # Busca produtos com descrição semântica mas sem embeddings
                products = Product.search([
                    ('semantic_descr', '!=', False),
                    ('ncm_vector', '=', False)
                ], limit=limit)
                
            total = len(products)
            processed = 0
            failed = 0
            
            for product in products:
                try:
                    result = self.generate_embedding_from_semantic(product.id)
                    if result:
                        processed += 1
                    else:
                        failed += 1
                        
                    # Pausa para evitar limites de taxa da API
                    time.sleep(0.5)
                    
                except Exception as e:
                    _logger.error(f"Erro ao processar produto {product.name} (ID: {product.id}): {str(e)}")
                    failed += 1
                    continue
            
            return {
                'total': total,
                'processed': processed,
                'failed': failed
            }
            
        except Exception as e:
            _logger.error(f"Erro ao processar lote de produtos: {str(e)}")
            return {
                'total': 0,
                'processed': 0,
                'failed': 0,
                'error': str(e)
            }
