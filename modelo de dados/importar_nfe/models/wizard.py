# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import xml.etree.ElementTree as ET
import os
import glob
import logging
import tempfile
import datetime
import gc

_logger = logging.getLogger(__name__)

class ImportarNFeWizard(models.TransientModel):
    _name = 'importar_nfe.wizard'
    _description = 'Wizard para importar NFe'

    modo_importacao = fields.Selection([
        ('arquivo_unico', 'Arquivo Único'),
        ('multiplos_arquivos', 'Múltiplos Arquivos'),
        ('pasta', 'Pasta')
    ], string='Modo de Importação', required=True, default='arquivo_unico')

    arquivo_xml = fields.Binary(string='Arquivo XML')
    arquivo_xml_nome = fields.Char(string='Nome do Arquivo XML')
    arquivos_xml = fields.Binary(string='Arquivos XML')
    arquivos_xml_nomes = fields.Char(string='Nomes dos Arquivos XML')
    pasta_path = fields.Char(string='Caminho da Pasta')
    incluir_subpastas = fields.Boolean(string='Incluir Subpastas', default=True,
                                      help='Se marcado, buscará arquivos XML em todas as subpastas')
    
    # Campos informativos
    total_importados = fields.Integer(string='Total Importados', readonly=True, default=0)
    total_erros = fields.Integer(string='Total Erros', readonly=True, default=0)
    mensagem_log = fields.Text(string='Log de Importação', readonly=True)

    @api.onchange('modo_importacao')
    def _onchange_modo_importacao(self):
        """Limpa os campos não utilizados quando o modo de importação muda"""
        if self.modo_importacao == 'arquivo_unico':
            self.arquivos_xml = False
            self.arquivos_xml_nomes = False
            self.pasta_path = False
        elif self.modo_importacao == 'multiplos_arquivos':
            self.arquivo_xml = False
            self.arquivo_xml_nome = False
            self.pasta_path = False
        elif self.modo_importacao == 'pasta':
            self.arquivo_xml = False
            self.arquivo_xml_nome = False
            self.arquivos_xml = False
            self.arquivos_xml_nomes = False

    def action_import(self):
        # Validar campos obrigatórios
        if self.modo_importacao == 'arquivo_unico' and not self.arquivo_xml:
            raise UserError(_('Por favor, selecione um arquivo XML.'))
        elif self.modo_importacao == 'multiplos_arquivos' and not self.arquivos_xml:
            raise UserError(_('Por favor, selecione os arquivos XML.'))
        elif self.modo_importacao == 'pasta' and not self.pasta_path:
            raise UserError(_('Por favor, digite o caminho da pasta.'))
            
        # Reiniciar contadores e log
        self.total_importados = 0
        self.total_erros = 0
        self.mensagem_log = ''
        
        # Chamar o método de importação adequado
        if self.modo_importacao == 'arquivo_unico':
            return self._importar_arquivo_unico()
        elif self.modo_importacao == 'multiplos_arquivos':
            return self._importar_multiplos_arquivos()
        elif self.modo_importacao == 'pasta':
            return self._importar_da_pasta()

    def _adicionar_log(self, mensagem):
        """Adiciona uma mensagem ao log de importação"""
        # Se a mensagem já tem formatação HTML completa, adicionar diretamente
        if mensagem.startswith('<div') or mensagem.startswith('<span'):
            html_mensagem = mensagem + '\n'
        else:
            # Adicionar timestamp para mensagens regulares
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            
            # Formatar a mensagem com HTML para melhor visualização
            if mensagem.startswith(' Erro') or 'Erro ao processar' in mensagem:
                html_mensagem = f'<span style="color: red;">[{timestamp}] {mensagem}</span><br/>\n'
            elif mensagem.startswith(' Arquivo') and 'importado com sucesso' in mensagem:
                html_mensagem = f'<span style="color: green;">[{timestamp}] {mensagem}</span><br/>\n'
            elif 'Progresso:' in mensagem:
                html_mensagem = f'<span style="color: blue; font-weight: bold;">[{timestamp}] {mensagem}</span><br/>\n'
            elif '<strong>' in mensagem:
                # Já tem formatação, só adicionar timestamp
                html_mensagem = f'[{timestamp}] {mensagem}<br/>\n'
            else:
                html_mensagem = f'[{timestamp}] {mensagem}<br/>\n'
        
        self.mensagem_log = (self.mensagem_log or '') + html_mensagem
        _logger.info(mensagem.replace('<strong>', '').replace('</strong>', '').replace('<br/>', ''))

    def _importar_xml_seguro(self, xml_content, nome_arquivo=''):
        """Importa um XML de forma segura, tratando exceções"""
        try:
            tree = ET.ElementTree(ET.fromstring(xml_content))
            # Passar parâmetro para desativar mensagens durante importações em massa
            nfe = self.env['importar_nfe.nfe'].importar_xml(tree, disable_messaging=True)
            self.total_importados += 1
            self._adicionar_log(f' Arquivo {nome_arquivo} importado com sucesso: NFe {nfe.name} - Chave {nfe.chave_acesso}')
            return nfe
        except Exception as e:
            self.total_erros += 1
            erro_msg = str(e)
            self._adicionar_log(f' Erro ao importar arquivo {nome_arquivo}: {erro_msg}')
            _logger.error(f"Erro ao importar arquivo {nome_arquivo}: {erro_msg}", exc_info=True)
            return False

    def _importar_arquivo_unico(self):
        try:
            nome_arquivo = self.arquivo_xml_nome or 'arquivo.xml'
            self._adicionar_log(f'Iniciando importação do arquivo {nome_arquivo}')
            
            xml_content = base64.b64decode(self.arquivo_xml)
            nfe = self._importar_xml_seguro(xml_content, nome_arquivo)
            
            if not nfe:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'importar_nfe.wizard',
                    'view_mode': 'form',
                    'res_id': self.id,
                    'target': 'new',
                    'context': {'default_mensagem_log': self.mensagem_log}
                }
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'importar_nfe.nfe',
                'view_mode': 'form',
                'res_id': nfe.id,
                'target': 'current',
            }
        except Exception as e:
            raise UserError(_('Erro ao importar arquivo: %s') % str(e))

    def _importar_multiplos_arquivos(self):
        try:
            self._adicionar_log('Iniciando importação de múltiplos arquivos')
            
            # Criar diretório temporário para salvar os arquivos
            temp_dir = tempfile.mkdtemp()
            self._adicionar_log(f'Diretório temporário criado: {temp_dir}')
            
            # Extrair arquivos do campo binário
            xml_content = base64.b64decode(self.arquivos_xml)
            
            # Salvar o conteúdo em um arquivo temporário
            temp_zip = os.path.join(temp_dir, 'arquivos.zip')
            with open(temp_zip, 'wb') as f:
                f.write(xml_content)
            
            # Tentar descompactar se for um arquivo zip
            try:
                import zipfile
                with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                self._adicionar_log('Arquivos ZIP extraídos com sucesso')
            except:
                self._adicionar_log('Não foi possível extrair como ZIP, tentando processar como XML único')
                # Se não for um ZIP, tenta processar como um único XML
                with open(temp_zip, 'rb') as f:
                    xml_content = f.read()
                    self._importar_xml_seguro(xml_content, 'arquivo.xml')
            
            # Procurar por arquivos XML no diretório temporário
            arquivos_xml = glob.glob(os.path.join(temp_dir, '**', '*.xml'), recursive=True)
            self._adicionar_log(f'Encontrados {len(arquivos_xml)} arquivos XML')
            
            nfes_importadas = []
            for arquivo in arquivos_xml:
                try:
                    with open(arquivo, 'rb') as f:
                        xml_content = f.read()
                        nfe = self._importar_xml_seguro(xml_content, os.path.basename(arquivo))
                        if nfe:
                            nfes_importadas.append(nfe.id)
                except Exception as e:
                    self._adicionar_log(f' Erro ao processar arquivo {os.path.basename(arquivo)}: {str(e)}')
            
            # Limpar diretório temporário
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            self._adicionar_log(f'Importação concluída. Total importados: {self.total_importados}. Total erros: {self.total_erros}')
            
            if not nfes_importadas:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'importar_nfe.wizard',
                    'view_mode': 'form',
                    'res_id': self.id,
                    'target': 'new',
                    'context': {'default_mensagem_log': self.mensagem_log}
                }
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'importar_nfe.nfe',
                'view_mode': 'list,form',
                'domain': [('id', 'in', nfes_importadas)],
                'target': 'current',
            }
        except Exception as e:
            raise UserError(_('Erro ao importar arquivos: %s') % str(e))

    def _importar_da_pasta(self):
        try:
            if not os.path.exists(self.pasta_path):
                raise UserError(_('A pasta especificada não existe.'))
            
            self._adicionar_log(f'Iniciando importação da pasta: {self.pasta_path}')
            
            # Procurar por arquivos XML na pasta e subpastas
            self._adicionar_log(f'Buscando arquivos XML na pasta{" e subpastas" if self.incluir_subpastas else ""}...')
            
            try:
                arquivos_xml = glob.glob(os.path.join(self.pasta_path, '**', '*.xml'), recursive=self.incluir_subpastas)
            except Exception as e:
                self._adicionar_log(f'<span style="color: red;">Erro ao buscar arquivos: {str(e)}</span>')
                raise UserError(_('Erro ao buscar arquivos XML: %s') % str(e))
            
            if not arquivos_xml:
                if self.incluir_subpastas:
                    raise UserError(_('Nenhum arquivo XML encontrado na pasta especificada ou suas subpastas.'))
                else:
                    raise UserError(_('Nenhum arquivo XML encontrado na pasta especificada.'))
            
            # Ordenar arquivos para processamento mais previsível
            arquivos_xml.sort()
            
            total_arquivos = len(arquivos_xml)
            self._adicionar_log(f'<strong>Encontrados {total_arquivos} arquivos XML</strong>')
            
            # Iniciar importação em lotes com tratamento de erros aprimorado
            try:
                return self._importar_em_lotes(arquivos_xml)
            except Exception as e:
                self._adicionar_log(f'<span style="color: red;">Erro durante o processamento em lotes: {str(e)}</span>')
                _logger.error("Erro durante processamento em lotes: %s", str(e), exc_info=True)
                
                # Se houver algum problema com o processamento em lotes, 
                # retornar para o usuário o que já foi processado
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'importar_nfe.wizard',
                    'view_mode': 'form',
                    'res_id': self.id,
                    'target': 'new',
                    'context': {'default_mensagem_log': self.mensagem_log}
                }
            
        except Exception as e:
            self._adicionar_log(f'<span style="color: red;">Erro ao importar da pasta: {str(e)}</span>')
            raise UserError(_('Erro ao importar da pasta: %s') % str(e))
    
    def _importar_em_lotes(self, arquivos_xml):
        """Importa arquivos XML em lotes para melhor gerenciamento de memória e performance"""
        tamanho_lote = 1000  # Tamanho do lote fixo
        total_arquivos = len(arquivos_xml)
        total_lotes = (total_arquivos + tamanho_lote - 1) // tamanho_lote  # Arredonda para cima
        
        self._adicionar_log(f'<strong>Iniciando importação em {total_lotes} lotes de {tamanho_lote} arquivos</strong>')
        
        nfes_importadas = []
        
        # Processar cada lote
        for num_lote in range(total_lotes):
            inicio_lote = num_lote * tamanho_lote
            fim_lote = min((num_lote + 1) * tamanho_lote, total_arquivos)
            
            lote_atual = arquivos_xml[inicio_lote:fim_lote]
            
            # Informações sobre o lote
            self._adicionar_log(f'<div style="background-color: #f0f0f0; padding: 5px; margin: 10px 0; border-left: 3px solid #875A7B;">')
            self._adicionar_log(f'<strong>Processando lote {num_lote + 1}/{total_lotes}</strong>')
            self._adicionar_log(f'Arquivos: {inicio_lote + 1} a {fim_lote} de {total_arquivos}')
            self._adicionar_log(f'</div>')
            
            try:
                # Processar arquivos do lote atual
                nfes_lote = self._processar_lote(lote_atual, inicio_lote)
                nfes_importadas.extend(nfes_lote)
                
                # Limpar cache e liberar memória
                self._limpar_recursos()
                
                # Adicionar resumo do lote
                self._adicionar_log(f'<div style="background-color: #f0f0f0; padding: 5px; margin: 10px 0; border-left: 3px solid #28a745;">')
                self._adicionar_log(f'<strong>Lote {num_lote + 1} concluído com sucesso</strong>')
                self._adicionar_log(f'NFes importadas no lote: {len(nfes_lote)}')
                self._adicionar_log(f'Total importadas até agora: {len(nfes_importadas)}')
                self._adicionar_log(f'</div>')
                
            except Exception as e:
                # Adicionar informação do erro
                self._adicionar_log(f'<div style="background-color: #f0f0f0; padding: 5px; margin: 10px 0; border-left: 3px solid #dc3545;">')
                self._adicionar_log(f'<strong>Erro no lote {num_lote + 1}</strong>')
                self._adicionar_log(f'Detalhes: {str(e)}')
                self._adicionar_log(f'</div>')
                
                _logger.error(f"Erro ao processar lote {num_lote + 1}: {str(e)}", exc_info=True)
        
        # Resumo final
        self._adicionar_log(f'<div style="background-color: #f0f0f0; padding: 10px; margin: 10px 0; border-left: 5px solid #17a2b8;">')
        self._adicionar_log(f'<strong>Importação concluída</strong>')
        self._adicionar_log(f'Total de lotes processados: {total_lotes}')
        self._adicionar_log(f'Total de arquivos: {total_arquivos}')
        self._adicionar_log(f'Total de NFes importadas: {len(nfes_importadas)}')
        self._adicionar_log(f'Total de sucessos: {self.total_importados}')
        self._adicionar_log(f'Total de erros: {self.total_erros}')
        self._adicionar_log(f'</div>')
        
        if not nfes_importadas:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'importar_nfe.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
                'context': {'default_mensagem_log': self.mensagem_log}
            }
                
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'importar_nfe.nfe',
            'view_mode': 'list,form',
            'domain': [('id', 'in', nfes_importadas)],
            'target': 'current',
        }
    
    def _processar_lote(self, arquivos_lote, offset_inicial):
        """Processa um lote de arquivos XML"""
        nfes_lote = []
        
        for i, arquivo in enumerate(arquivos_lote):
            try:
                indice_global = offset_inicial + i + 1
                
                with open(arquivo, 'rb') as f:
                    xml_content = f.read()
                    nome_arquivo = os.path.basename(arquivo)
                    
                    # Atualizar o log com informações do progresso
                    if i % 10 == 0 or i == len(arquivos_lote) - 1:
                        self._adicionar_log(f'Processando arquivo {indice_global}/{len(arquivos_lote) + offset_inicial}: {nome_arquivo}')
                    
                    # Importar o XML
                    nfe = self._importar_xml_seguro(xml_content, nome_arquivo)
                    if nfe:
                        nfes_lote.append(nfe.id)
                        
                        # A cada 100 arquivos processados dentro do lote, atualizar o log
                        if len(nfes_lote) % 100 == 0:
                            self._adicionar_log(f'Progresso intermediário: {len(nfes_lote)} NFes importadas no lote atual')
                            
            except Exception as e:
                self._adicionar_log(f'<span style="color: red;">Erro ao processar arquivo {os.path.basename(arquivo)}: {str(e)}</span>')
                _logger.error(f"Erro ao processar arquivo {os.path.basename(arquivo)}: {str(e)}", exc_info=True)
        
        return nfes_lote
    
    def _limpar_recursos(self):
        """Limpa cache e libera memória após processamento de um lote"""
        # Limpar cache do ORM para evitar crescimento excessivo de memória, mas sem fechar o cursor
        self.env.cache.clear()
        
        # Sugestão para o garbage collector fazer seu trabalho
        gc.collect()
        
        # Registrar no log
        self._adicionar_log('Cache limpo e memória liberada')

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
