# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import glob
import logging

class ImportarNFeWizard(models.TransientModel):
    _name = 'importar_nfe.wizard'
    _description = 'Wizard para importar NFe'

    modo_importacao = fields.Selection([
        ('arquivo_unico', 'Arquivo Único'),
        ('multiplos_arquivos', 'Múltiplos Arquivos'),
        ('pasta', 'Pasta')
    ], string='Modo de Importação', required=True, default='arquivo_unico')

    arquivo_xml = fields.Binary(string='Arquivo XML', required=False)
    arquivo_xml_nome = fields.Char(string='Nome do Arquivo XML')
    arquivos_xml = fields.Binary(string='Arquivos XML', required=False)
    arquivos_xml_nomes = fields.Char(string='Nomes dos Arquivos XML')
    pasta_path = fields.Char(string='Caminho da Pasta')
    incluir_subpastas = fields.Boolean(string='Incluir Subpastas', default=True, 
                                      help='Se marcado, buscará arquivos XML em todas as subpastas')

    def action_import(self):
        if self.modo_importacao == 'arquivo_unico':
            if not self.arquivo_xml:
                raise UserError(_('Por favor, selecione um arquivo XML.'))
            return self._importar_arquivo_unico()
        elif self.modo_importacao == 'multiplos_arquivos':
            if not self.arquivos_xml:
                raise UserError(_('Por favor, selecione os arquivos XML.'))
            return self._importar_multiplos_arquivos()
        elif self.modo_importacao == 'pasta':
            if not self.pasta_path:
                raise UserError(_('Por favor, digite o caminho da pasta.'))
            return self._importar_da_pasta()

    def _importar_arquivo_unico(self):
        try:
            xml_content = base64.b64decode(self.arquivo_xml)
            tree = ET.ElementTree(ET.fromstring(xml_content))
            return self.env['importar_nfe.nfe'].importar_xml(tree)
        except Exception as e:
            raise UserError(_('Erro ao importar arquivo: %s') % str(e))

    def _importar_multiplos_arquivos(self):
        try:
            xml_contents = base64.b64decode(self.arquivos_xml)
            # Implementar lógica para processar múltiplos arquivos
            return {'type': 'ir.actions.act_window_close'}
        except Exception as e:
            raise UserError(_('Erro ao importar arquivos: %s') % str(e))

    def _importar_da_pasta(self):
        try:
            if not os.path.exists(self.pasta_path):
                raise UserError(_('A pasta especificada não existe.'))
            
            # Função para encontrar arquivos XML recursivamente
            def encontrar_xmls(pasta, recursivo=True):
                arquivos_encontrados = []
                # Lista todos os itens na pasta
                for item in os.listdir(pasta):
                    caminho_completo = os.path.join(pasta, item)
                    # Se for arquivo com extensão .xml, adiciona à lista
                    if os.path.isfile(caminho_completo) and item.lower().endswith('.xml'):
                        arquivos_encontrados.append(caminho_completo)
                    # Se for diretório e recursivo=True, busca recursivamente
                    elif os.path.isdir(caminho_completo) and recursivo:
                        arquivos_encontrados.extend(encontrar_xmls(caminho_completo, recursivo))
                return arquivos_encontrados
            
            # Encontra todos os arquivos XML na pasta e subpastas se configurado
            caminhos_xml = encontrar_xmls(self.pasta_path, self.incluir_subpastas)
            
            if not caminhos_xml:
                if self.incluir_subpastas:
                    raise UserError(_('Nenhum arquivo XML encontrado na pasta especificada ou suas subpastas.'))
                else:
                    raise UserError(_('Nenhum arquivo XML encontrado na pasta especificada.'))
            
            nfes_importadas = []
            total_arquivos = len(caminhos_xml)
            for i, caminho_completo in enumerate(caminhos_xml, 1):
                try:
                    _logger.info(f'Importando arquivo {i}/{total_arquivos}: {caminho_completo}')
                    with open(caminho_completo, 'rb') as f:
                        xml_content = f.read()
                        tree = ET.ElementTree(ET.fromstring(xml_content))
                        nfe = self.env['importar_nfe.nfe'].importar_xml(tree)
                        nfes_importadas.append(nfe.id)
                except Exception as e:
                    _logger.error(f'Erro ao importar arquivo {caminho_completo}: {str(e)}')
                    # Continua com o próximo arquivo mesmo que haja erro
            
            if not nfes_importadas:
                raise UserError(_('Nenhum arquivo XML foi importado com sucesso. Verifique os logs para mais detalhes.'))
                
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'importar_nfe.nfe',
                'view_mode': 'list,form',
                'domain': [('id', 'in', nfes_importadas)],
                'context': {'create': False},
                'name': _('NFes Importadas (%s)') % len(nfes_importadas),
            }
        except Exception as e:
            raise UserError(_('Erro ao importar da pasta: %s') % str(e))

    def action_selecionar_pasta(self):
        if self.pasta_path:
            return self.action_import()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Selecionar Pasta'),
                'message': _('Por favor, digite o caminho completo da pasta no campo acima.'),
                'type': 'warning',
            }
        }

class ImportarNFeDestinatario(models.Model):
    _name = 'importar_nfe.destinatario'
    _description = 'Destinatário de NFe'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nome', required=True, tracking=True)
    cnpj = fields.Char(string='CNPJ', tracking=True)
    cpf = fields.Char(string='CPF', tracking=True)
    ie = fields.Char(string='Inscrição Estadual', tracking=True)
    email = fields.Char(string='E-mail', tracking=True)
    telefone = fields.Char(string='Telefone', tracking=True)
    logradouro = fields.Char(string='Logradouro', tracking=True)
    numero = fields.Char(string='Número', tracking=True)
    complemento = fields.Char(string='Complemento', tracking=True)
    bairro = fields.Char(string='Bairro', tracking=True)
    municipio = fields.Char(string='Município', tracking=True)
    uf = fields.Char(string='UF', tracking=True)
    cep = fields.Char(string='CEP', tracking=True)
    pais = fields.Char(string='País', default='BRASIL', tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    nfe_ids = fields.One2many('importar_nfe.nfe', 'destinatario_id', string='Notas Fiscais')

    _sql_constraints = [
        ('cnpj_cpf_uniq', 'unique(cnpj,cpf)', 'CNPJ ou CPF deve ser único!')
    ]
    
    def toggle_active(self):
        """Alterna o estado ativo/arquivado do destinatário."""
        for record in self:
            record.active = not record.active

class ImportarNFeEmitente(models.Model):
    _name = 'importar_nfe.emitente'
    _description = 'Emitente de NFe'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nome', required=True, tracking=True)
    cnpj = fields.Char(string='CNPJ', required=True, tracking=True)
    ie = fields.Char(string='Inscrição Estadual', tracking=True)
    email = fields.Char(string='E-mail', tracking=True)
    telefone = fields.Char(string='Telefone', tracking=True)
    logradouro = fields.Char(string='Logradouro', tracking=True)
    numero = fields.Char(string='Número', tracking=True)
    complemento = fields.Char(string='Complemento', tracking=True)
    bairro = fields.Char(string='Bairro', tracking=True)
    municipio = fields.Char(string='Município', tracking=True)
    uf = fields.Char(string='UF', tracking=True)
    cep = fields.Char(string='CEP', tracking=True)
    pais = fields.Char(string='País', default='BRASIL', tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    nfe_ids = fields.One2many('importar_nfe.nfe', 'emitente_id', string='Notas Fiscais')

    _sql_constraints = [
        ('cnpj_uniq', 'unique(cnpj)', 'CNPJ deve ser único!')
    ]
    
    def toggle_active(self):
        """Alterna o estado ativo/arquivado do emitente."""
        for record in self:
            record.active = not record.active

class ImportarNFeProduto(models.Model):
    _name = 'importar_nfe.produto'
    _description = 'Produto'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nome', required=True, tracking=True)
    codigo = fields.Char(string='Código', required=True, tracking=True)
    descricao = fields.Text(string='Descrição', required=True, tracking=True)
    ncm = fields.Char(string='NCM', tracking=True)
    cfop = fields.Char(string='CFOP', tracking=True)
    unidade = fields.Char(string='Unidade', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    
    nfe_item_ids = fields.One2many('importar_nfe.item', 'produto_id', string='Itens de NFe')
    
    _sql_constraints = [
        ('codigo_uniq', 'unique(codigo)', 'O código do produto deve ser único!')
    ]
    
    def toggle_active(self):
        """Alterna o estado ativo/arquivado do produto."""
        for record in self:
            record.active = not record.active

class ImportarNFeItem(models.Model):
    _name = 'importar_nfe.item'
    _description = 'Item de NFe'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    nfe_id = fields.Many2one('importar_nfe.nfe', string='NFe', required=True, ondelete='cascade')
    produto_id = fields.Many2one('importar_nfe.produto', string='Produto', required=True)
    numero_item = fields.Integer(string='Número do Item', required=True)
    quantidade = fields.Float(string='Quantidade', digits=(16, 4))
    valor_unitario = fields.Float(string='Valor Unitário', digits=(16, 2))
    valor_total = fields.Float(string='Valor Total', digits=(16, 2))
    valor_desconto = fields.Float(string='Valor do Desconto', digits=(16, 2))
    
    # Campos adicionais referenciados nas views
    codigo = fields.Char(related='produto_id.codigo', string='Código', store=True)
    descricao = fields.Text(related='produto_id.descricao', string='Descrição', store=True)
    ncm = fields.Char(related='produto_id.ncm', string='NCM', store=True)
    cfop = fields.Char(related='produto_id.cfop', string='CFOP', store=True)
    unidade = fields.Char(related='produto_id.unidade', string='Unidade', store=True)
    
    # Campos de impostos
    valor_icms = fields.Float(string='Valor do ICMS', digits=(16, 2))
    valor_ipi = fields.Float(string='Valor do IPI', digits=(16, 2))
    valor_pis = fields.Float(string='Valor do PIS', digits=(16, 2))
    valor_cofins = fields.Float(string='Valor do COFINS', digits=(16, 2))

    @api.model
    def create(self, vals):
        # Verifica se já existe um produto com o mesmo código
        if vals.get('codigo'):
            produto = self.env['importar_nfe.produto'].search([('codigo', '=', vals['codigo'])], limit=1)
            if not produto:
                # Cria um novo produto
                produto = self.env['importar_nfe.produto'].create({
                    'name': vals.get('descricao', ''),
                    'codigo': vals.get('codigo'),
                    'descricao': vals.get('descricao', ''),
                    'ncm': vals.get('ncm'),
                    'cfop': vals.get('cfop'),
                    'unidade': vals.get('unidade'),
                })
            vals['produto_id'] = produto.id
        return super(ImportarNFeItem, self).create(vals)

class ImportarNFeItemRel(models.Model):
    _name = 'importar_nfe.nfe.item'
    _description = 'Item de NFe (Relacionamento)'

    nfe_id = fields.Many2one('importar_nfe.nfe', string='NFe', required=True, ondelete='cascade')
    item_id = fields.Many2one('importar_nfe.item', string='Item', required=True)
    numero_item = fields.Integer(string='Número do Item', required=True)
    quantidade = fields.Float(string='Quantidade', digits=(16, 4))
    valor_unitario = fields.Float(string='Valor Unitário', digits=(16, 2))
    valor_total = fields.Float(string='Valor Total', digits=(16, 2))
    valor_desconto = fields.Float(string='Valor do Desconto', digits=(16, 2))

class ImportarNFe(models.Model):
    _name = 'importar_nfe.nfe'
    _description = 'Nota Fiscal Eletrônica'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'data_emissao desc, name desc'

    name = fields.Char(string='Número', required=True, tracking=True)
    chave_acesso = fields.Char(string='Chave de Acesso', required=True, tracking=True)
    data_emissao = fields.Datetime(string='Data de Emissão', required=True, tracking=True)
    data_entrada = fields.Datetime(string='Data de Entrada', tracking=True)
    numero = fields.Char(string='Número', tracking=True)
    serie = fields.Char(string='Série', tracking=True)
    modelo = fields.Char(string='Modelo', tracking=True)
    tipo_operacao = fields.Selection([
        ('0', 'Entrada'),
        ('1', 'Saída'),
    ], string='Tipo de Operação', tracking=True)
    
    emitente_id = fields.Many2one('importar_nfe.emitente', string='Emitente', required=True, tracking=True)
    destinatario_id = fields.Many2one('importar_nfe.destinatario', string='Destinatário', required=True, tracking=True)
    
    item_ids = fields.One2many('importar_nfe.item', 'nfe_id', string='Itens')
    quantidade_itens = fields.Integer(string='Quantidade de Itens', compute='_compute_quantidade_itens', store=True)
    
    valor_produtos = fields.Float(string='Valor dos Produtos', digits=(16, 2), tracking=True)
    valor_frete = fields.Float(string='Valor do Frete', digits=(16, 2), tracking=True)
    valor_seguro = fields.Float(string='Valor do Seguro', digits=(16, 2), tracking=True)
    valor_desconto = fields.Float(string='Valor do Desconto', digits=(16, 2), tracking=True)
    valor_outros = fields.Float(string='Outros Valores', digits=(16, 2), tracking=True)
    
    valor_ipi = fields.Float(string='Valor do IPI', digits=(16, 2), tracking=True)
    valor_icms = fields.Float(string='Valor do ICMS', digits=(16, 2), tracking=True)
    valor_pis = fields.Float(string='Valor do PIS', digits=(16, 2), tracking=True)
    valor_cofins = fields.Float(string='Valor do COFINS', digits=(16, 2), tracking=True)
    valor_total = fields.Float(string='Valor Total', digits=(16, 2), tracking=True)
    
    active = fields.Boolean(default=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('imported', 'Importado'),
        ('processed', 'Processado'),
        ('cancelled', 'Cancelado')
    ], string='Status', default='draft', tracking=True)
    
    _sql_constraints = [
        ('chave_acesso_uniq', 'unique(chave_acesso)', 'A chave de acesso deve ser única!')
    ]
    
    @api.depends('item_ids')
    def _compute_quantidade_itens(self):
        for record in self:
            record.quantidade_itens = len(record.item_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Novo')) == _('Novo'):
            vals['name'] = self.env['ir.sequence'].next_by_code('importar_nfe.nfe') or _('Novo')
        return super(ImportarNFe, self).create(vals)

    @api.model
    def importar_xml(self, tree):
        try:
            root = tree.getroot()
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

            # Extrair dados básicos da NFe
            ide = root.find('.//nfe:ide', ns)
            emit = root.find('.//nfe:emit', ns)
            dest = root.find('.//nfe:dest', ns)
            total = root.find('.//nfe:total/nfe:ICMSTot', ns)

            if ide is None or emit is None or dest is None or total is None:
                raise UserError(_('XML inválido. Estrutura incompleta.'))

            # Extrair a chave de acesso
            chave_acesso = ide.find('nfe:chNFe', ns)
            if chave_acesso is None:
                # Tenta alternativas para a chave de acesso
                inf_nfe = root.find('.//nfe:infNFe', ns)
                if inf_nfe is not None and 'Id' in inf_nfe.attrib:
                    chave_acesso_text = inf_nfe.attrib['Id']
                    # Remove o prefixo NFe se existir
                    if chave_acesso_text.startswith('NFe'):
                        chave_acesso_text = chave_acesso_text[3:]
                else:
                    raise UserError(_('Não foi possível encontrar a chave de acesso no XML.'))
            else:
                chave_acesso_text = chave_acesso.text

            # Verificar se a NFe já existe
            nfe_existente = self.search([('chave_acesso', '=', chave_acesso_text)], limit=1)
            if nfe_existente:
                return nfe_existente

            # Criar ou buscar emitente
            emitente_vals = {
                'name': emit.find('nfe:xNome', ns).text if emit.find('nfe:xNome', ns) is not None else 'Sem Nome',
                'cnpj': emit.find('nfe:CNPJ', ns).text if emit.find('nfe:CNPJ', ns) is not None else '00000000000000',
                'ie': emit.find('nfe:IE', ns).text if emit.find('nfe:IE', ns) is not None else False,
                'logradouro': emit.find('.//nfe:xLgr', ns).text if emit.find('.//nfe:xLgr', ns) is not None else False,
                'numero': emit.find('.//nfe:nro', ns).text if emit.find('.//nfe:nro', ns) is not None else False,
                'complemento': emit.find('.//nfe:xCpl', ns).text if emit.find('.//nfe:xCpl', ns) is not None else False,
                'bairro': emit.find('.//nfe:xBairro', ns).text if emit.find('.//nfe:xBairro', ns) is not None else False,
                'municipio': emit.find('.//nfe:xMun', ns).text if emit.find('.//nfe:xMun', ns) is not None else False,
                'uf': emit.find('.//nfe:UF', ns).text if emit.find('.//nfe:UF', ns) is not None else False,
                'cep': emit.find('.//nfe:CEP', ns).text if emit.find('.//nfe:CEP', ns) is not None else False,
            }
            emitente = self.env['importar_nfe.emitente'].search([('cnpj', '=', emitente_vals['cnpj'])], limit=1)
            if not emitente:
                emitente = self.env['importar_nfe.emitente'].create(emitente_vals)

            # Criar ou buscar destinatário
            destinatario_vals = {
                'name': dest.find('nfe:xNome', ns).text if dest.find('nfe:xNome', ns) is not None else 'Sem Nome',
                'cnpj': dest.find('nfe:CNPJ', ns).text if dest.find('nfe:CNPJ', ns) is not None else False,
                'cpf': dest.find('nfe:CPF', ns).text if dest.find('nfe:CPF', ns) is not None else False,
                'ie': dest.find('nfe:IE', ns).text if dest.find('nfe:IE', ns) is not None else False,
                'logradouro': dest.find('.//nfe:xLgr', ns).text if dest.find('.//nfe:xLgr', ns) is not None else False,
                'numero': dest.find('.//nfe:nro', ns).text if dest.find('.//nfe:nro', ns) is not None else False,
                'complemento': dest.find('.//nfe:xCpl', ns).text if dest.find('.//nfe:xCpl', ns) is not None else False,
                'bairro': dest.find('.//nfe:xBairro', ns).text if dest.find('.//nfe:xBairro', ns) is not None else False,
                'municipio': dest.find('.//nfe:xMun', ns).text if dest.find('.//nfe:xMun', ns) is not None else False,
                'uf': dest.find('.//nfe:UF', ns).text if dest.find('.//nfe:UF', ns) is not None else False,
                'cep': dest.find('.//nfe:CEP', ns).text if dest.find('.//nfe:CEP', ns) is not None else False,
            }
            
            # Se não tiver CNPJ nem CPF, cria um valor padrão para evitar erro de unicidade
            if not destinatario_vals['cnpj'] and not destinatario_vals['cpf']:
                destinatario_vals['cnpj'] = f"TEMP_{chave_acesso_text[-8:]}"
                
            domain = []
            if destinatario_vals['cnpj']:
                domain = [('cnpj', '=', destinatario_vals['cnpj'])]
            elif destinatario_vals['cpf']:
                domain = [('cpf', '=', destinatario_vals['cpf'])]
            else:
                domain = [('cnpj', '=', destinatario_vals['cnpj'])]
                
            destinatario = self.env['importar_nfe.destinatario'].search(domain, limit=1)
            if not destinatario:
                destinatario = self.env['importar_nfe.destinatario'].create(destinatario_vals)

            # Extrair número e série da NFe
            numero_nfe = ide.find('nfe:nNF', ns).text if ide.find('nfe:nNF', ns) is not None else 'SN'
            serie_nfe = ide.find('nfe:serie', ns).text if ide.find('nfe:serie', ns) is not None else '0'

            # Construir identificador único para a NFe
            nfe_name = f"NFe {serie_nfe}-{numero_nfe}"

            # Extrair data de emissão
            data_emissao_text = ide.find('nfe:dhEmi', ns).text if ide.find('nfe:dhEmi', ns) is not None else None
            if data_emissao_text:
                # Verificar formato da data
                if 'T' in data_emissao_text:
                    try:
                        data_emissao = datetime.strptime(data_emissao_text.split('-0')[0], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        try:
                            data_emissao = datetime.strptime(data_emissao_text.split('+')[0], '%Y-%m-%dT%H:%M:%S')
                        except ValueError:
                            # Último recurso: usar a data atual
                            data_emissao = datetime.now()
                else:
                    try:
                        data_emissao = datetime.strptime(data_emissao_text, '%Y-%m-%d')
                    except ValueError:
                        # Último recurso: usar a data atual
                        data_emissao = datetime.now()
            else:
                data_emissao = datetime.now()

            # Valores default para campos numéricos
            def safe_float(element, xpath, default=0.0):
                node = element.find(xpath, ns) if element else None
                if node is not None and node.text:
                    try:
                        return float(node.text)
                    except (ValueError, TypeError):
                        return default
                return default

            # Criar NFe
            nfe_vals = {
                'name': nfe_name,
                'chave_acesso': chave_acesso_text,
                'serie': serie_nfe,
                'numero': numero_nfe,
                'data_emissao': data_emissao,
                'data_entrada': datetime.now(),
                'emitente_id': emitente.id,
                'destinatario_id': destinatario.id,
                'valor_total': safe_float(total, 'nfe:vNF'),
                'valor_produtos': safe_float(total, 'nfe:vProd'),
                'valor_frete': safe_float(total, 'nfe:vFrete'),
                'valor_seguro': safe_float(total, 'nfe:vSeg'),
                'valor_desconto': safe_float(total, 'nfe:vDesc'),
                'valor_outros': safe_float(total, 'nfe:vOutro'),
                'valor_icms': safe_float(total, 'nfe:vICMS'),
                'valor_ipi': safe_float(total, 'nfe:vIPI'),
                'valor_pis': safe_float(total, 'nfe:vPIS'),
                'valor_cofins': safe_float(total, 'nfe:vCOFINS'),
                'state': 'imported',
            }

            nfe = self.create(nfe_vals)

            # Processar itens
            for det in root.findall('.//nfe:det', ns):
                prod = det.find('nfe:prod', ns)
                imposto = det.find('nfe:imposto', ns)
                
                if prod is None:
                    continue  # Pula este item se prod não existir
                
                # Valores default para campos de produto
                def safe_text(element, xpath, default=''):
                    node = element.find(xpath, ns) if element else None
                    return node.text if node is not None and node.text else default
                
                # Buscar ou criar produto
                codigo_produto = safe_text(prod, 'nfe:cProd', f'PROD{det.get("nItem", "0")}')
                nome_produto = safe_text(prod, 'nfe:xProd', f'Produto {det.get("nItem", "0")}')
                
                produto_vals = {
                    'name': nome_produto,
                    'codigo': codigo_produto,
                    'descricao': nome_produto,
                    'ncm': safe_text(prod, 'nfe:NCM'),
                    'cfop': safe_text(prod, 'nfe:CFOP'),
                    'unidade': safe_text(prod, 'nfe:uCom'),
                }
                
                produto = self.env['importar_nfe.produto'].search([
                    ('codigo', '=', produto_vals['codigo'])
                ], limit=1)
                
                if not produto:
                    produto = self.env['importar_nfe.produto'].create(produto_vals)
                
                # Criar item de NFe
                item_vals = {
                    'nfe_id': nfe.id,
                    'produto_id': produto.id,
                    'numero_item': int(det.get('nItem', '0')),
                    'quantidade': safe_float(prod, 'nfe:qCom', 1.0),
                    'valor_unitario': safe_float(prod, 'nfe:vUnCom'),
                    'valor_total': safe_float(prod, 'nfe:vProd'),
                    'valor_desconto': safe_float(prod, 'nfe:vDesc'),
                }
                
                # Extrair valores de impostos se disponíveis
                if imposto is not None:
                    item_vals['valor_icms'] = safe_float(imposto, './/nfe:ICMS//nfe:vICMS')
                    item_vals['valor_ipi'] = safe_float(imposto, './/nfe:IPI//nfe:vIPI')
                    item_vals['valor_pis'] = safe_float(imposto, './/nfe:PIS//nfe:vPIS')
                    item_vals['valor_cofins'] = safe_float(imposto, './/nfe:COFINS//nfe:vCOFINS')
                
                self.env['importar_nfe.item'].create(item_vals)

            return nfe
        except Exception as e:
            _logger.error(f"Erro ao importar XML: {str(e)}")
            raise UserError(_('Erro ao importar XML: %s') % str(e))

    def toggle_active(self):
        """Alterna o estado ativo/arquivado da NFe."""
        for record in self:
            record.active = not record.active
            
    def action_draft(self):
        """Altera o estado para Rascunho."""
        for record in self:
            record.state = 'draft'
            
    def action_process(self):
        """Altera o estado para Processado."""
        for record in self:
            record.state = 'processed'
            
    def action_cancel(self):
        """Altera o estado para Cancelado."""
        for record in self:
            record.state = 'cancelled'
