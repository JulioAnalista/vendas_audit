# -*- coding: utf-8 -*-

import argparse
import base64
import logging
import xmlrpc.client
from pathlib import Path

# --- Configurações de Conexão com o Odoo ---
# Substitua pelos seus dados reais!
ODOO_URL = 'http://localhost:8069'  # URL do seu servidor Odoo
ODOO_DB = 'odoo18'      # Nome do seu banco de dados Odoo
ODOO_USER = 'odoo18'                 # Usuário do Odoo (ou um usuário com permissão)
ODOO_PASSWORD = 'odoo18'         # Senha do usuário (ou chave de API)
# -------------------------------------------

# Configuração básica do logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def connect_odoo(url, db, user, password):
    """Tenta conectar ao Odoo via XML-RPC."""
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        version = common.version()
        logging.info(f"Conectado ao Odoo versão: {version['server_version']}")

        uid = common.authenticate(db, user, password, {})
        if not uid:
            logging.error("Falha na autenticação. Verifique usuário e senha.")
            return None, None

        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        logging.info(f"Autenticado com sucesso. UID: {uid}")
        return uid, models
    except Exception as e:
        logging.error(f"Erro ao conectar ao Odoo: {e}")
        return None, None

def import_xml_to_odoo(models, uid, db, password, xml_path):
    """
    Cria um registro nfe.import no Odoo e tenta processar o XML.

    Args:
        models: Objeto de conexão 'object' do XML-RPC.
        uid: ID do usuário autenticado.
        db: Nome do banco de dados.
        password: Senha ou chave de API do usuário.
        xml_path (Path): Caminho para o arquivo XML.

    Returns:
        int: O ID do registro nfe.import criado e processado, ou None se falhar.
    """
    try:
        logging.info(f"Processando arquivo: {xml_path.name}")

        # Ler o conteúdo binário do arquivo
        with open(xml_path, 'rb') as f:
            xml_content_bytes = f.read()

        # Codificar em base64
        xml_content_b64 = base64.b64encode(xml_content_bytes)

        # Dados para criar o registro nfe.import
        import_vals = {
            'xml_filename': xml_path.name,
            'xml_file': xml_content_b64.decode('utf-8'), # Odoo espera string base64
            # 'name': f"Importação {xml_path.name}" # Opcional, sequência deve cuidar disso
        }

        # 1. Criar o registro nfe.import no estado 'draft'
        import_id = models.execute_kw(db, uid, password,
                                     'nfe.import', 'create',
                                     [import_vals])

        if not import_id:
            logging.error(f"Falha ao criar registro nfe.import para {xml_path.name}")
            return None

        logging.info(f"Registro nfe.import criado com ID: {import_id} para {xml_path.name}")

        # 2. Chamar a ação 'action_import' para processar o XML
        logging.info(f"Chamando action_import para o registro ID: {import_id}")
        models.execute_kw(db, uid, password,
                          'nfe.import', 'action_import',
                          [[import_id]]) # Ação geralmente espera uma lista de IDs

        # 3. (Opcional) Verificar o estado final do registro
        final_state = models.execute_kw(db, uid, password,
                                         'nfe.import', 'read',
                                         [[import_id]], {'fields': ['state']})

        if final_state and final_state[0]['state'] == 'done':
            logging.info(f"Importação de {xml_path.name} (ID: {import_id}) concluída com sucesso.")
        elif final_state:
            logging.warning(f"Importação de {xml_path.name} (ID: {import_id}) finalizada com estado: {final_state[0]['state']}. Verifique os logs no Odoo.")
        else:
             logging.warning(f"Não foi possível verificar o estado final da importação para {xml_path.name} (ID: {import_id}).")

        return import_id

    except xmlrpc.client.Fault as e:
         logging.error(f"Erro RPC ao processar {xml_path.name}: {e.faultString}")
         # Tenta adicionar um log de erro no registro se ele foi criado
         if 'import_id' in locals() and import_id:
             try:
                 models.execute_kw(db, uid, password, 'nfe.import', 'write', [[import_id], {'state': 'error'}])
                 models.execute_kw(db, uid, password, 'nfe.import.log', 'create', [{
                     'nfe_import_id': import_id,
                     'type': 'error',
                     'message': f"Erro RPC durante importação externa: {e.faultString}"
                 }])
             except Exception as log_e:
                 logging.error(f"Erro adicional ao tentar registrar log de erro no Odoo para ID {import_id}: {log_e}")
         return None
    except Exception as e:
        logging.error(f"Erro inesperado ao processar {xml_path.name}: {e}")
        # Tenta adicionar um log de erro no registro se ele foi criado
        if 'import_id' in locals() and import_id:
            try:
                models.execute_kw(db, uid, password, 'nfe.import', 'write', [[import_id], {'state': 'error'}])
                models.execute_kw(db, uid, password, 'nfe.import.log', 'create', [{
                     'nfe_import_id': import_id,
                     'type': 'error',
                     'message': f"Erro inesperado durante importação externa: {str(e)}"
                 }])
            except Exception as log_e:
                logging.error(f"Erro adicional ao tentar registrar log de erro no Odoo para ID {import_id}: {log_e}")
        return None


def main(folder_path_str):
    """Função principal para buscar e importar XMLs."""
    folder_path = Path(folder_path_str)

    if not folder_path.is_dir():
        logging.error(f"O caminho fornecido não é um diretório válido: {folder_path_str}")
        return

    # Conectar ao Odoo
    uid, models = connect_odoo(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)
    if not uid or not models:
        logging.error("Não foi possível conectar ao Odoo. Abortando.")
        return

    logging.info(f"Buscando arquivos .xml no diretório: {folder_path.resolve()}")
    xml_files = list(folder_path.rglob('*.xml'))

    if not xml_files:
        logging.warning(f"Nenhum arquivo .xml encontrado em {folder_path.resolve()}")
        return

    success_count = 0
    fail_count = 0

    for xml_file in xml_files:
        if xml_file.is_file():
            import_id = import_xml_to_odoo(models, uid, ODOO_DB, ODOO_PASSWORD, xml_file)
            if import_id:
                success_count += 1
            else:
                fail_count += 1

    logging.info("-" * 30)
    logging.info(f"Processamento concluído.")
    logging.info(f"Total de arquivos .xml encontrados: {len(xml_files)}")
    logging.info(f"Importações iniciadas (verificar status no Odoo): {success_count}")
    logging.info(f"Falhas ao iniciar importação: {fail_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importa arquivos XML de NFe para o Odoo.")
    parser.add_argument("pasta", help="O caminho para a pasta contendo os arquivos XML.")

    args = parser.parse_args()

    # --- IMPORTANTE: Segurança ---
    # Considere carregar usuário/senha/chave de API de variáveis de ambiente
    # ou de um arquivo de configuração seguro em vez de colocá-los aqui.
    # Ex: ODOO_PASSWORD = os.getenv('ODOO_API_KEY')
    # ---------------------------

    main(args.pasta)