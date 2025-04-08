# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
import re
import html

_logger = logging.getLogger(__name__)

class ImportarNFe(models.Model):
    _name = 'importar_nfe.nfe'
    _description = 'Nota Fiscal Eletrônica'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'data_emissao desc, name desc'
    
    # Campos de identificação
    name = fields.Char(string='Número', required=True, tracking=True, copy=False, default=lambda self: _('Novo'))
    chave_acesso = fields.Char(string='Chave de Acesso', required=True, tracking=True, copy=False)
    numero = fields.Char(string='Número da NFe', tracking=True)
    serie = fields.Char(string='Série', tracking=True)
    modelo = fields.Char(string='Modelo', tracking=True)
    tipo_operacao = fields.Selection([
        ('entrada', 'Entrada'),
        ('saida', 'Saída')
    ], string='Tipo de Operação', default='entrada', tracking=True)
    
    # Datas
    data_emissao = fields.Datetime(string='Data de Emissão', tracking=True)
    data_entrada = fields.Datetime(string='Data de Entrada/Saída', tracking=True)
    
    # Relacionamentos
    emitente_id = fields.Many2one('importar_nfe.emitente', string='Emitente', required=True, tracking=True)
    destinatario_id = fields.Many2one('importar_nfe.destinatario', string='Destinatário', required=True, tracking=True)
    item_ids = fields.One2many('importar_nfe.item', 'nfe_id', string='Itens')
    item_rel_ids = fields.One2many('importar_nfe.nfe.item', 'nfe_id', string='Relacionamento com Itens')
    
    # Valores
    valor_produtos = fields.Float(string='Valor dos Produtos', digits=(16, 2), tracking=True)
    valor_frete = fields.Float(string='Valor do Frete', digits=(16, 2), tracking=True)
    valor_seguro = fields.Float(string='Valor do Seguro', digits=(16, 2), tracking=True)
    valor_desconto = fields.Float(string='Valor do Desconto', digits=(16, 2), tracking=True)
    valor_outros = fields.Float(string='Outros Valores', digits=(16, 2), tracking=True)
    valor_total = fields.Float(string='Valor Total', digits=(16, 2), tracking=True)
    
    # Impostos
    valor_icms = fields.Float(string='Valor ICMS', digits=(16, 2), tracking=True)
    valor_ipi = fields.Float(string='Valor IPI', digits=(16, 2), tracking=True)
    valor_pis = fields.Float(string='Valor PIS', digits=(16, 2), tracking=True)
    valor_cofins = fields.Float(string='Valor COFINS', digits=(16, 2), tracking=True)
    
    # Campos computados
    quantidade_itens = fields.Integer(string='Quantidade de Itens', compute='_compute_quantidade_itens', store=True)
    xml_formatado = fields.Html(string='XML Formatado', compute='_compute_xml_formatado', sanitize=False)
    
    # Status
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('imported', 'Importado'),
        ('processed', 'Processado'),
        ('cancelled', 'Cancelado')
    ], string='Status', default='draft', tracking=True)
    
    # Campos de controle
    active = fields.Boolean(default=True, tracking=True)
    xml_original = fields.Binary(string='XML Original', attachment=True)
    xml_nome = fields.Char(string='Nome do XML')
    
    # Restrições
    _sql_constraints = [
        ('chave_acesso_uniq', 'unique(chave_acesso)', 'A chave de acesso deve ser única!')
    ]
    
    @api.depends('item_ids')
    def _compute_quantidade_itens(self):
        for record in self:
            record.quantidade_itens = len(record.item_ids)
    
    @api.depends('xml_original')
    def _compute_xml_formatado(self):
        """Transforma o XML binário em HTML formatado para exibição"""
        for record in self:
            if not record.xml_original:
                record.xml_formatado = "<p>Nenhum XML disponível</p>"
                continue
            
            try:
                # Decodificar o XML binário
                xml_content = base64.b64decode(record.xml_original)
                
                # Verificar se o conteúdo é válido antes de tentar parsear
                if not xml_content or len(xml_content) < 10:
                    record.xml_formatado = "<p>XML inválido ou vazio</p>"
                    continue
                
                # Parsear o XML
                try:
                    tree = ET.ElementTree(ET.fromstring(xml_content))
                except Exception as parse_error:
                    record.xml_formatado = f"<p>Erro ao parsear XML: {html.escape(str(parse_error))}</p>"
                    continue
                
                # Função para formatar o elemento XML recursivamente
                def format_element(element, level=0):
                    indent = '&nbsp;' * 4 * level
                    tag = element.tag
                    # Remover namespace se presente
                    if '}' in tag:
                        tag = tag.split('}', 1)[1]
                    
                    result = []
                    attrs = ''
                    if element.attrib:
                        attrs = ' ' + ' '.join([f'<span style="color: #0000AA;">{k}</span>=<span style="color: #AA0000;">"{html.escape(v)}"</span>' for k, v in element.attrib.items()])
                    
                    # Abertura da tag
                    result.append(f'{indent}<span style="color: #0000FF;">&lt;{tag}</span>{attrs}<span style="color: #0000FF;">&gt;</span>')
                    
                    # Conteúdo e filhos
                    if element.text and element.text.strip():
                        result.append(f'<span style="color: #000000;">{html.escape(element.text.strip())}</span>')
                        
                    if len(element) > 0:
                        result.append('<br/>')
                        for child in element:
                            result.append(format_element(child, level + 1))
                            result.append('<br/>')
                        result.append(f'{indent}')
                    
                    # Fechamento da tag
                    result.append(f'<span style="color: #0000FF;">&lt;/{tag}&gt;</span>')
                    
                    return ''.join(result)
                
                # Formatar o XML inteiro com sintaxe colorida
                root = tree.getroot()
                html_content = f'<pre style="font-family: monospace; white-space: pre-wrap;">{format_element(root)}</pre>'
                
                record.xml_formatado = html_content
            except Exception as e:
                record.xml_formatado = f"<p>Erro ao renderizar XML: {html.escape(str(e))}</p>"
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Novo')) == _('Novo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('importar_nfe.nfe') or _('Novo')
        return super(ImportarNFe, self).create(vals_list)
    
    def _detectar_namespace(self, root):
        """Detecta automaticamente o namespace do XML da NFe"""
        nsmap = {}
        
        # Verificar se o root já tem o namespace definido
        if hasattr(root, 'nsmap') and root.nsmap:
            for prefix, uri in root.nsmap.items():
                if uri and ('portalfiscal' in uri or 'nfe' in uri):
                    if prefix is None:
                        nsmap['nfe'] = uri
                    else:
                        nsmap[prefix] = uri
        
        # Se não encontrou namespace, tentar detectar pelos elementos
        if not nsmap:
            # Verificar se há namespace no elemento raiz
            match = re.match(r'\{(.*?)\}', root.tag)
            if match:
                ns_uri = match.group(1)
                nsmap['nfe'] = ns_uri
            
            # Tentar encontrar nos filhos
            for child in root:
                match = re.match(r'\{(.*?)\}', child.tag)
                if match:
                    ns_uri = match.group(1)
                    nsmap['nfe'] = ns_uri
                    break
        
        # Se ainda não encontrou, usar um namespace padrão
        if not nsmap:
            _logger.warning("Namespace não detectado, usando namespace padrão")
            nsmap['nfe'] = 'http://www.portalfiscal.inf.br/nfe'
        
        return nsmap
    
    def _extrair_valor_seguro(self, elemento, ns, xpath, default=0.0):
        """Extrai um valor numérico de forma segura, retornando o default em caso de erro"""
        try:
            # Tentar encontrar o elemento com namespace
            valor_elem = elemento.find(xpath, ns)
            if valor_elem is not None and valor_elem.text:
                return float(valor_elem.text.replace(',', '.'))
            
            # Se não encontrou, tentar sem namespace
            xpath_sem_ns = xpath.replace('nfe:', '')
            valor_elem = elemento.find(xpath_sem_ns)
            if valor_elem is not None and valor_elem.text:
                return float(valor_elem.text.replace(',', '.'))
                
            return default
        except (ValueError, AttributeError):
            return default
    
    def _extrair_texto_seguro(self, elemento, ns, xpath, default=False):
        """Extrai um texto de forma segura, retornando o default em caso de erro"""
        try:
            # Tentar encontrar o elemento com namespace
            texto_elem = elemento.find(xpath, ns)
            if texto_elem is not None and texto_elem.text:
                return texto_elem.text.strip()
            
            # Se não encontrou, tentar sem namespace
            xpath_sem_ns = xpath.replace('nfe:', '')
            texto_elem = elemento.find(xpath_sem_ns)
            if texto_elem is not None and texto_elem.text:
                return texto_elem.text.strip()
                
            return default
        except AttributeError:
            return default
    
    def _parsear_data(self, data_str):
        """Converte string de data em objeto datetime"""
        if not data_str:
            return False
            
        # Remover timezone se presente
        data_str = data_str.split('-0')[0].split('+0')[0].strip()
        
        # Verificar se a data contém apenas o ano e mês (formato YYYY-MM)
        if data_str and len(data_str.split('-')) == 2:
            try:
                ano, mes = data_str.split('-')
                if ano.isdigit() and mes.isdigit() and len(ano) == 4 and len(mes) <= 2:
                    return datetime(int(ano), int(mes), 1, 0, 0, 0)
            except ValueError:
                _logger.warning("Não foi possível converter a data de mês-ano: %s", data_str)
        
        # Verificar se a data contém apenas o ano
        if data_str and data_str.isdigit() and len(data_str) == 4:
            # Se for apenas o ano (exemplo: "2024"), usar 1º de janeiro desse ano
            try:
                return datetime(int(data_str), 1, 1, 0, 0, 0)
            except ValueError:
                _logger.warning("Não foi possível converter o ano: %s", data_str)
                return False
        
        # Tentar vários formatos de data
        formatos = [
            '%Y-%m-%dT%H:%M:%S',  # 2023-01-01T10:30:00
            '%Y-%m-%d %H:%M:%S',  # 2023-01-01 10:30:00
            '%d/%m/%Y %H:%M:%S',  # 01/01/2023 10:30:00
            '%d/%m/%Y',           # 01/01/2023
            '%Y%m%d%H%M%S',       # 20230101103000
            '%Y%m%d',             # 20230101
            '%Y-%m-%d',           # 2023-01-01
        ]
        
        for formato in formatos:
            try:
                return datetime.strptime(data_str, formato)
            except ValueError:
                continue
                
        _logger.warning("Não foi possível converter a data: %s", data_str)
        # Em caso de não conseguir converter, retornar a data atual
        return datetime.now()
    
    def _buscar_elemento_recursivo(self, elemento, tag_procurada, ns=None):
        """Busca um elemento recursivamente na árvore XML"""
        if elemento is None:
            return None
            
        # Verificar se o elemento atual é o procurado
        tag_atual = elemento.tag
        if ns:
            # Remover namespace da tag atual se existir
            match = re.match(r'\{.*?\}(.*)', tag_atual)
            if match:
                tag_atual = match.group(1)
        
        if tag_atual == tag_procurada:
            return elemento
            
        # Buscar nos filhos
        for filho in elemento:
            resultado = self._buscar_elemento_recursivo(filho, tag_procurada, ns)
            if resultado is not None:
                return resultado
                
        return None
    
    def _extrair_elemento_seguro(self, root, caminho_elementos, ns=None):
        """Extrai um elemento de forma segura usando um caminho de elementos"""
        elemento_atual = root
        
        for tag in caminho_elementos:
            if elemento_atual is None:
                return None
                
            # Tentar com namespace
            if ns:
                elemento_atual = elemento_atual.find(f'nfe:{tag}', ns)
                
            # Se não encontrou, tentar sem namespace
            if elemento_atual is None:
                elemento_atual = elemento_atual.find(tag)
                
            # Se ainda não encontrou, tentar buscar recursivamente
            if elemento_atual is None:
                elemento_atual = self._buscar_elemento_recursivo(root, tag, ns)
                
        return elemento_atual
    
    def importar_xml(self, tree, disable_messaging=True):
        """Importa os dados de um XML de NFe
        
        Args:
            tree: ElementTree contendo o XML da NFe
            disable_messaging: Se True, desativa mensagens de sistema durante importação em massa
        """
        try:
            # Salvar XML original como string binária
            xml_str = ET.tostring(tree.getroot(), encoding='utf-8', method='xml')
            
            # Converter para base64 válido
            xml_base64 = base64.b64encode(xml_str)
            
            root = tree.getroot()
            # Detectar namespace automaticamente
            ns = self._detectar_namespace(root)
            
            # Verificar se já existe NFe com a mesma chave de acesso
            chave_acesso = None
            
            # Tentar encontrar a chave de acesso em diferentes locais
            # Primeiro no padrão mais comum
            infNFe = root.find('.//nfe:infNFe', ns)
            if infNFe is not None:
                chave_acesso = infNFe.get('Id', '')
                if chave_acesso and chave_acesso.startswith('NFe'):
                    chave_acesso = chave_acesso[3:]  # Remover prefixo 'NFe'
            
            # Se não encontrou, tentar outros caminhos
            if not chave_acesso:
                chave_acesso_elem = root.find('.//nfe:chNFe', ns)
                if chave_acesso_elem is not None and chave_acesso_elem.text:
                    chave_acesso = chave_acesso_elem.text
            
            if not chave_acesso:
                chave_acesso_elem = self._buscar_elemento_recursivo(root, 'chNFe', ns)
                if chave_acesso_elem is not None and chave_acesso_elem.text:
                    chave_acesso = chave_acesso_elem.text
            
            if not chave_acesso:
                raise UserError(_('XML inválido: chave de acesso não encontrada.'))
            
            # Verificar se já existe NFe com esta chave
            nfe_existente = self.search([('chave_acesso', '=', chave_acesso)], limit=1)
            if nfe_existente:
                _logger.info("NFe com chave %s já existe no sistema.", chave_acesso)
                return nfe_existente
            
            # Extrair informações básicas
            if not infNFe:
                # Tentar encontrar em outros locais
                infNFe = self._extrair_elemento_seguro(root, ['NFe', 'infNFe'], ns)
                if not infNFe:
                    infNFe = self._buscar_elemento_recursivo(root, 'infNFe', ns)
                
            if not infNFe:
                raise UserError(_('XML inválido: elemento infNFe não encontrado.'))
            
            # Extrair dados do emitente
            emit = infNFe.find('.//nfe:emit', ns)
            if not emit:
                emit = self._buscar_elemento_recursivo(infNFe, 'emit', ns)
                
            if not emit:
                raise UserError(_('XML inválido: elemento emit não encontrado.'))
            
            # Extrair CNPJ do emitente
            cnpj_emit = self._extrair_texto_seguro(emit, ns, 'nfe:CNPJ')
            if not cnpj_emit:
                raise UserError(_('XML inválido: CNPJ do emitente não encontrado.'))
            
            # Buscar ou criar emitente
            emitente = self.env['importar_nfe.emitente'].search([('cnpj', '=', cnpj_emit)], limit=1)
            if not emitente:
                emitente_vals = {
                    'name': self._extrair_texto_seguro(emit, ns, 'nfe:xNome', 'Emitente'),
                    'cnpj': cnpj_emit,
                    'ie': self._extrair_texto_seguro(emit, ns, 'nfe:IE', ''),
                    'logradouro': self._extrair_texto_seguro(emit, ns, 'nfe:enderEmit/nfe:xLgr', ''),
                    'numero': self._extrair_texto_seguro(emit, ns, 'nfe:enderEmit/nfe:nro', ''),
                    'complemento': self._extrair_texto_seguro(emit, ns, 'nfe:enderEmit/nfe:xCpl', ''),
                    'bairro': self._extrair_texto_seguro(emit, ns, 'nfe:enderEmit/nfe:xBairro', ''),
                    'municipio': self._extrair_texto_seguro(emit, ns, 'nfe:enderEmit/nfe:xMun', ''),
                    'uf': self._extrair_texto_seguro(emit, ns, 'nfe:enderEmit/nfe:UF', ''),
                    'cep': self._extrair_texto_seguro(emit, ns, 'nfe:enderEmit/nfe:CEP', ''),
                    'telefone': self._extrair_texto_seguro(emit, ns, 'nfe:enderEmit/nfe:fone', ''),
                }
                emitente = self.env['importar_nfe.emitente'].create(emitente_vals)
            
            # Extrair dados do destinatário
            dest = infNFe.find('.//nfe:dest', ns)
            if not dest:
                dest = self._buscar_elemento_recursivo(infNFe, 'dest', ns)
            
            # Se não encontrar o destinatário, criar um destinatário padrão
            if not dest:
                _logger.warning("Elemento dest não encontrado no XML. Usando destinatário padrão.")
                destinatario = self.env['importar_nfe.destinatario'].search([('name', '=', 'Destinatário Padrão')], limit=1)
                
                if not destinatario:
                    # Criar destinatário padrão se não existir
                    destinatario_vals = {
                        'name': 'Destinatário Padrão',
                        'cnpj': False,
                        'cpf': False,
                        'ie': '',
                    }
                    destinatario = self.env['importar_nfe.destinatario'].create(destinatario_vals)
            else:
                # Extrair CNPJ ou CPF do destinatário
                cnpj_dest = self._extrair_texto_seguro(dest, ns, 'nfe:CNPJ')
                cpf_dest = self._extrair_texto_seguro(dest, ns, 'nfe:CPF')
                
                if not cnpj_dest and not cpf_dest:
                    _logger.warning("CNPJ/CPF do destinatário não encontrado. Usando identificador alternativo.")
                    # Tentar usar o nome como identificador
                    nome_dest = self._extrair_texto_seguro(dest, ns, 'nfe:xNome', 'Destinatário Desconhecido')
                    destinatario = self.env['importar_nfe.destinatario'].search([('name', '=', nome_dest)], limit=1)
                    
                    if not destinatario:
                        # Criar destinatário com os dados disponíveis
                        destinatario_vals = {
                            'name': nome_dest,
                            'cnpj': False,
                            'cpf': False,
                            'ie': self._extrair_texto_seguro(dest, ns, 'nfe:IE', ''),
                            'logradouro': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:xLgr', ''),
                            'numero': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:nro', ''),
                            'complemento': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:xCpl', ''),
                            'bairro': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:xBairro', ''),
                            'municipio': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:xMun', ''),
                            'uf': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:UF', ''),
                            'cep': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:CEP', ''),
                            'telefone': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:fone', ''),
                        }
                        destinatario = self.env['importar_nfe.destinatario'].create(destinatario_vals)
                else:
                    # Buscar ou criar destinatário
                    domain = []
                    if cnpj_dest:
                        domain = [('cnpj', '=', cnpj_dest)]
                    elif cpf_dest:
                        domain = [('cpf', '=', cpf_dest)]
                    
                    destinatario = self.env['importar_nfe.destinatario'].search(domain, limit=1)
                    if not destinatario:
                        destinatario_vals = {
                            'name': self._extrair_texto_seguro(dest, ns, 'nfe:xNome', 'Destinatário'),
                            'cnpj': cnpj_dest or False,
                            'cpf': cpf_dest or False,
                            'ie': self._extrair_texto_seguro(dest, ns, 'nfe:IE', ''),
                            'logradouro': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:xLgr', ''),
                            'numero': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:nro', ''),
                            'complemento': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:xCpl', ''),
                            'bairro': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:xBairro', ''),
                            'municipio': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:xMun', ''),
                            'uf': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:UF', ''),
                            'cep': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:CEP', ''),
                            'telefone': self._extrair_texto_seguro(dest, ns, 'nfe:enderDest/nfe:fone', ''),
                        }
                        destinatario = self.env['importar_nfe.destinatario'].create(destinatario_vals)
            
            # Extrair identificação da NFe
            ide = infNFe.find('.//nfe:ide', ns)
            if not ide:
                ide = self._buscar_elemento_recursivo(infNFe, 'ide', ns)
                
            if not ide:
                _logger.warning('Elemento ide não encontrado no XML. Usando valores padrão.')
                # Criar um dicionário para armazenar valores padrão que seriam extraídos do ide
                ide_values = {
                    'nNF': 'Novo',
                    'serie': '',
                    'mod': '',
                    'dhEmi': False,
                    'dhSaiEnt': False
                }
                # Função auxiliar para extrair valores do dicionário de valores padrão
                def extrair_de_ide_dict(campo, default):
                    return ide_values.get(campo, default)
            else:
                # Função auxiliar para extrair valores do elemento XML ide
                def extrair_de_ide_dict(campo, default):
                    return self._extrair_texto_seguro(ide, ns, f'nfe:{campo}', default)
            
            # Extrair valores totais
            total = infNFe.find('.//nfe:total', ns)
            if not total:
                total = self._buscar_elemento_recursivo(infNFe, 'total', ns)
                
            if not total:
                _logger.warning('Elemento total não encontrado no XML. Usando valores padrão.')
                # Usar valores zerados para os campos financeiros quando não encontrar o elemento total
                total_values = {
                    'vProd': 0.0,
                    'vFrete': 0.0,
                    'vSeg': 0.0,
                    'vDesc': 0.0,
                    'vOutro': 0.0,
                    'vNF': 0.0,
                    'vICMS': 0.0,
                    'vIPI': 0.0,
                    'vPIS': 0.0,
                    'vCOFINS': 0.0
                }
                # Função auxiliar para extrair valores do dicionário de valores padrão
                def extrair_de_total_dict(xpath, default):
                    campo = xpath.replace('.//nfe:', '').replace('./', '')
                    return total_values.get(campo, default)
            else:
                # Função auxiliar para extrair valores do elemento XML total
                def extrair_de_total_dict(xpath, default):
                    return self._extrair_valor_seguro(total, ns, xpath, default)
            
            # Preparar valores da NFe
            nfe_vals = {
                'name': extrair_de_ide_dict('nNF', 'Novo'),
                'chave_acesso': chave_acesso,
                'numero': extrair_de_ide_dict('nNF', ''),
                'serie': extrair_de_ide_dict('serie', ''),
                'modelo': extrair_de_ide_dict('mod', ''),
                'tipo_operacao': 'entrada',  # Padrão é entrada
                'data_emissao': self._parsear_data(extrair_de_ide_dict('dhEmi', False)),
                'data_entrada': self._parsear_data(extrair_de_ide_dict('dhSaiEnt', False)),
                'emitente_id': emitente.id,
                'destinatario_id': destinatario.id,
                'valor_produtos': extrair_de_total_dict('.//nfe:vProd', 0.0),
                'valor_frete': extrair_de_total_dict('.//nfe:vFrete', 0.0),
                'valor_seguro': extrair_de_total_dict('.//nfe:vSeg', 0.0),
                'valor_desconto': extrair_de_total_dict('.//nfe:vDesc', 0.0),
                'valor_outros': extrair_de_total_dict('.//nfe:vOutro', 0.0),
                'valor_total': extrair_de_total_dict('.//nfe:vNF', 0.0),
                'valor_icms': extrair_de_total_dict('.//nfe:vICMS', 0.0),
                'valor_ipi': extrair_de_total_dict('.//nfe:vIPI', 0.0),
                'valor_pis': extrair_de_total_dict('.//nfe:vPIS', 0.0),
                'valor_cofins': extrair_de_total_dict('.//nfe:vCOFINS', 0.0),
                'state': 'imported',
                'xml_original': xml_base64,
                'xml_nome': f"NFe_{chave_acesso}.xml",
            }
            
            # Criar NFe sem disparar mensagens de sistema se solicitado
            context = self.env.context.copy()
            if disable_messaging:
                context['tracking_disable'] = True
                context['mail_create_nosubscribe'] = True
                context['mail_auto_subscribe_no_notify'] = True
                context['mail_notrack'] = True
                
            nfe = self.with_context(context).create(nfe_vals)
            
            # Verificar se o XML original foi salvo corretamente
            if not nfe.xml_original:
                nfe.write({
                    'xml_original': xml_base64,
                    'xml_nome': f"NFe_{chave_acesso}.xml",
                })
            
            # Processar itens
            itens = infNFe.findall('.//nfe:det', ns)
            if not itens:
                # Tentar encontrar itens sem namespace
                itens = infNFe.findall('.//det')
                
            if not itens:
                _logger.warning("Nenhum item encontrado na NFe %s", chave_acesso)
            
            for det in itens:
                prod = det.find('nfe:prod', ns)
                if not prod:
                    prod = det.find('prod')
                    
                if not prod:
                    _logger.warning("Elemento prod não encontrado no item %s", det.get('nItem', '?'))
                    continue
                    
                # Criar ou buscar produto
                codigo_produto = self._extrair_texto_seguro(prod, ns, 'nfe:cProd', '')
                if not codigo_produto:
                    codigo_produto = 'SEM_CODIGO'
                
                produto_vals = {
                    'name': self._extrair_texto_seguro(prod, ns, 'nfe:xProd', 'Produto'),
                    'codigo': codigo_produto,
                    'descricao': self._extrair_texto_seguro(prod, ns, 'nfe:xProd', ''),
                    'ncm': self._extrair_texto_seguro(prod, ns, 'nfe:NCM', ''),
                    'cfop': self._extrair_texto_seguro(prod, ns, 'nfe:CFOP', ''),
                    'unidade': self._extrair_texto_seguro(prod, ns, 'nfe:uCom', ''),
                }
                
                produto = self.env['importar_nfe.produto'].search([('codigo', '=', codigo_produto)], limit=1)
                if not produto:
                    produto = self.env['importar_nfe.produto'].create(produto_vals)
                
                # Criar item
                item_vals = {
                    'nfe_id': nfe.id,
                    'produto_id': produto.id,
                    'numero_item': int(det.get('nItem', '0')),
                    'quantidade': self._extrair_valor_seguro(prod, ns, 'nfe:qCom', 1.0),
                    'valor_unitario': self._extrair_valor_seguro(prod, ns, 'nfe:vUnCom', 0.0),
                    'valor_total': self._extrair_valor_seguro(prod, ns, 'nfe:vProd', 0.0),
                    'valor_desconto': self._extrair_valor_seguro(prod, ns, 'nfe:vDesc', 0.0),
                }
                
                # Adicionar valores de impostos se disponíveis
                imposto = det.find('nfe:imposto', ns)
                if not imposto:
                    imposto = det.find('imposto')
                    
                if imposto is not None:
                    # ICMS
                    icms = imposto.find('.//nfe:ICMS', ns)
                    if not icms:
                        icms = imposto.find('.//ICMS')
                        
                    if icms is not None:
                        # Tentar encontrar o valor do ICMS em qualquer subgrupo do ICMS
                        for icms_tag in icms:
                            valor_icms = self._extrair_valor_seguro(icms_tag, ns, 'nfe:vICMS', None)
                            if valor_icms is not None:
                                item_vals['valor_icms'] = valor_icms
                                break
                    
                    # IPI
                    ipi = imposto.find('.//nfe:IPI', ns)
                    if not ipi:
                        ipi = imposto.find('.//IPI')
                        
                    if ipi is not None:
                        # Tentar encontrar o valor do IPI em qualquer subgrupo do IPI
                        for ipi_tag in ipi:
                            valor_ipi = self._extrair_valor_seguro(ipi_tag, ns, 'nfe:vIPI', None)
                            if valor_ipi is not None:
                                item_vals['valor_ipi'] = valor_ipi
                                break
                    
                    # PIS
                    pis = imposto.find('.//nfe:PIS', ns)
                    if not pis:
                        pis = imposto.find('.//PIS')
                        
                    if pis is not None:
                        # Tentar encontrar o valor do PIS em qualquer subgrupo do PIS
                        for pis_tag in pis:
                            valor_pis = self._extrair_valor_seguro(pis_tag, ns, 'nfe:vPIS', None)
                            if valor_pis is not None:
                                item_vals['valor_pis'] = valor_pis
                                break
                    
                    # COFINS
                    cofins = imposto.find('.//nfe:COFINS', ns)
                    if not cofins:
                        cofins = imposto.find('.//COFINS')
                        
                    if cofins is not None:
                        # Tentar encontrar o valor do COFINS em qualquer subgrupo do COFINS
                        for cofins_tag in cofins:
                            valor_cofins = self._extrair_valor_seguro(cofins_tag, ns, 'nfe:vCOFINS', None)
                            if valor_cofins is not None:
                                item_vals['valor_cofins'] = valor_cofins
                                break
                
                item = self.env['importar_nfe.item'].create(item_vals)
                
                # Criar relacionamento NFe-Item
                self.env['importar_nfe.nfe.item'].create({
                    'nfe_id': nfe.id,
                    'item_id': item.id,
                })
            
            # Registrar mensagem no chatter apenas se não estiver desabilitado
            if not disable_messaging:
                nfe.message_post(
                    body=_("NFe importada com sucesso. Chave de acesso: %s") % chave_acesso,
                    subject=_("Importação de NFe")
                )
            
            return nfe
        except Exception as e:
            _logger.error("Erro ao importar XML: %s", str(e), exc_info=True)
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
