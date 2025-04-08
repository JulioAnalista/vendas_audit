import pandas as pd
import weaviate
from openai import OpenAI
import os
from dotenv import load_dotenv
import time
import numpy as np
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import json
import psycopg2

# Carrega as variáveis de ambiente
load_dotenv()

# Configuração do cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuração do cliente Weaviate - versão v4
client_weaviate = weaviate.WeaviateClient("http://localhost:8080")

def get_embedding(text):
    """Gera embedding usando a API da OpenAI"""
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def create_ncm_schema():
    # Define o schema da classe NCM
    class_obj = {
        "class": "NCM",
        "description": "Classificação NCM de produtos",
        "properties": [
            {
                "name": "codigo",
                "dataType": ["text"],
                "description": "Código NCM",
            },
            {
                "name": "descricao",
                "dataType": ["text"],
                "description": "Descrição do produto",
            }
        ],
        "vectorizer": "none",  # Usaremos embeddings da OpenAI
        "vectorIndexConfig": {
            "distance": "cosine"
        }
    }
    
    # Cria a classe no Weaviate
    try:
        client_weaviate.schema.create({"classes": [class_obj]})
        print("Schema NCM criado/atualizado com sucesso!")
    except Exception as e:
        if "already exists" in str(e):
            print("Schema NCM já existe!")
        else:
            raise e

def process_excel():
    # Lê o arquivo Excel começando da linha 5
    excel_path = ".github/data/Tabela_NCM_Vigente_20250222.xlsx"
    print(f"\nLendo arquivo: {excel_path}")
    df = pd.read_excel(excel_path, skiprows=4)
    
    # Configura o log de processamento
    import logging
    logging.basicConfig(filename="processamento.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Início do processamento do Excel.")
    
    # Seleciona apenas as colunas que precisamos
    df = df[['Código', 'Descrição']]
    
    # Renomeia as colunas para facilitar o acesso
    df.columns = ['codigo', 'descricao']
    
    # Remove linhas vazias e espaços extras
    df = df.dropna()
    df['descricao'] = df['descricao'].str.strip()
    
    # Conecta ao banco de dados Postgres
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "bumerangue"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            host=os.getenv("POSTGRES_HOS", "localhost")
        )
        cursor = conn.cursor()
        msg = "Conexão com o banco de dados Postgres estabelecida."
        print(msg)
        logging.info(msg)
    except Exception as e:
        msg = f"Erro ao conectar com o Postgres: {str(e)}"
        print(msg)
        logging.error(msg)
        return

    # Inicializa contadores para log
    total_registros = 0
    novos_registros = 0
    registros_atualizados = 0
    erros = 0

    # Processa cada linha
    for index, row in df.iterrows():
        total_registros += 1
        try:
            codigo = str(row['codigo'])
            descricao = row['descricao']
            msg = f"Processando registro {codigo}."
            print(msg)
            logging.info(msg)
            # Cria o objeto de dados
            data_object = {
                "codigo": codigo,
                "descricao": descricao
            }
            # Verifica se o registro já foi processado no Weaviate
            exists = False
            try:
                res = client_weaviate.query.get("NCM", ["codigo"]).with_where({
                    "path": ["codigo"],
                    "operator": "Equal",
                    "valueText": codigo
                }).do()
                if res.get("data", {}).get("Get", {}).get("NCM", []):
                    exists = True
            except Exception as check_err:
                logging.error(f"Erro ao verificar Weaviate para registro {codigo}: {str(check_err)}")
            
            if not exists:
                try:
                    embedding = get_embedding(descricao)
                    client_weaviate.data_object.create(
                        data_object=data_object,
                        class_name="NCM",
                        vector=embedding,
                        uuid=codigo
                    )
                    msg = f"Registro {codigo} criado no Weaviate."
                    print(msg)
                    logging.info(msg)
                    novos_registros += 1
                except Exception as create_err:
                    msg = f"Erro ao criar registro {codigo} no Weaviate: {str(create_err)}"
                    print(msg)
                    logging.error(msg)
                    erros += 1
            else:
                msg = f"Registro {codigo} já processado no Weaviate, pulando criação."
                print(msg)
                logging.info(msg)
                registros_atualizados += 1
            
            # Insere ou atualiza o registro na tabela ncm do Postgres
            cursor.execute(
                """
                INSERT INTO ncm (codigo, descricao)
                VALUES (%s, %s)
                ON CONFLICT (codigo) DO UPDATE SET descricao = EXCLUDED.descricao;
                """,
                (codigo, descricao)
            )
            conn.commit()
            msg = f"Registro {codigo} inserido/atualizado no Postgres."
            print(msg)
            logging.info(msg)
            
            # Pequena pausa para não sobrecarregar a API
            time.sleep(0.1)
            
            if (index + 1) % 100 == 0:
                msg = f"Processados {index + 1} registros..."
                print(msg)
                logging.info(msg)
                
        except Exception as e:
            msg = f"Erro ao processar linha {index + 1} (Registro {codigo}): {str(e)}"
            print(msg)
            logging.error(msg)
            erros += 1
            continue

    # Fecha a conexão com o banco de dados
    cursor.close()
    conn.close()
    msg = "Conexão com o Postgres encerrada."
    print(msg)
    logging.info(msg)
    
    # Log final do processamento
    summary = (f"Processamento concluído: Total registros: {total_registros}, "
               f"Novos registros criados no Weaviate: {novos_registros}, "
               f"Registros já existentes atualizados: {registros_atualizados}, "
               f"Erros: {erros}.")
    print(summary)
    logging.info(summary)

def buscar_ncm_similar(descricao_produto, limit=5):
    """
    Busca NCMs similares para uma descrição de produto
    Retorna uma lista de tuplas (código, descrição, similaridade)
    """
    # Gera o embedding da descrição do produto
    embedding = get_embedding(descricao_produto)
    
    # Busca no Weaviate usando similaridade vetorial
    result = (
        client_weaviate.query
        .get("NCM", ["codigo", "descricao"])
        .with_near_vector({
            "vector": embedding,
            "certainty": 0.7
        })
        .with_limit(limit)
        .with_additional(["certainty"])
        .do()
    )
    
    # Processa os resultados
    ncm_similares = []
    for item in result["data"]["Get"]["NCM"]:
        similaridade = item["_additional"]["certainty"]
        ncm_similares.append((item["codigo"], item["descricao"], similaridade))
    
    return ncm_similares

def verificar_ncm_nota(descricao_produto, ncm_informado=None):
    """
    Verifica se o NCM informado está correto para a descrição do produto
    Se não houver NCM informado, retorna os NCMs mais prováveis
    """
    ncm_similares = buscar_ncm_similar(descricao_produto)
    
    if ncm_informado is None:
        print(f"\nNCMs mais prováveis para: {descricao_produto}")
        for codigo, descricao, similaridade in ncm_similares:
            print(f"NCM: {codigo} - Similaridade: {similaridade:.2%}")
            print(f"Descrição: {descricao}\n")
    else:
        print(f"\nVerificando NCM {ncm_informado} para: {descricao_produto}")
        ncm_correto = ncm_similares[0][0]
        similaridade = ncm_similares[0][2]
        
        if ncm_informado == ncm_correto:
            print(f"✅ NCM correto! (Similaridade: {similaridade:.2%})")
        else:
            print(f"❌ NCM incorreto!")
            print(f"NCM sugerido: {ncm_correto} (Similaridade: {similaridade:.2%})")
            print(f"Descrição do NCM sugerido: {ncm_similares[0][1]}")

def buscar_ncm_por_codigo(codigo_ncm):
    """
    Busca um NCM específico pelo código
    """
    try:
        result = (
            client_weaviate.query
            .get("NCM", ["codigo", "descricao"])
            .with_where({
                "path": ["codigo"],
                "operator": "Equal",
                "valueText": str(codigo_ncm)
            })
            .do()
        )
        
        if result["data"]["Get"]["NCM"]:
            ncm = result["data"]["Get"]["NCM"][0]
            print(f"\nNCM encontrado:")
            print(f"Código: {ncm['codigo']}")
            print(f"Descrição: {ncm['descricao']}")
        else:
            print(f"\nNCM {codigo_ncm} não encontrado no Weaviate")
            
    except Exception as e:
        print(f"Erro ao buscar NCM: {str(e)}")

def atualizar_ncm_especifico(codigo_ncm, nova_descricao):
    """
    Atualiza um NCM específico no Weaviate com uma nova descrição
    """
    try:
        # Gera o embedding da nova descrição
        embedding = get_embedding(nova_descricao)
        
        # Cria o objeto de dados com o embedding
        data_object = {
            "codigo": str(codigo_ncm),
            "descricao": nova_descricao
        }
        
        # Atualiza o objeto no Weaviate
        client_weaviate.data_object.update(
            data_object=data_object,
            class_name="NCM",
            uuid=str(codigo_ncm),
            vector=embedding
        )
        
        print(f"\nNCM {codigo_ncm} atualizado com sucesso!")
        print(f"Nova descrição: {nova_descricao}")
        
        # Mostra o registro atualizado
        buscar_ncm_por_codigo(codigo_ncm)
        
    except Exception as e:
        print(f"Erro ao atualizar NCM: {str(e)}")

def upload_to_google_drive(file_path, file_name):
    """
    Faz upload de um arquivo para o Google Drive
    """
    try:
        # Inicializa a autenticação do Google
        gauth = GoogleAuth()
        
        # Tenta carregar as credenciais salvas ou abre o navegador para autenticação
        gauth.LocalWebserverAuth()
        
        # Cria a instância do Google Drive
        drive = GoogleDrive(gauth)
        
        # Cria o arquivo no Google Drive
        gfile = drive.CreateFile({'title': file_name})
        gfile.SetContentFile(file_path)
        gfile.Upload()
        
        print(f"\nArquivo '{file_name}' foi enviado com sucesso para o Google Drive!")
        print(f"ID do arquivo no Drive: {gfile['id']}")
        
    except Exception as e:
        print(f"Erro ao fazer upload para o Google Drive: {str(e)}")

def fazer_backup():
    """
    Função específica para fazer backup dos dados e enviar para o Google Drive
    """
    try:
        page_size = 2000
        offset = 0
        page_num = 1
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        found = False
        while True:
            result_page = (
                client_weaviate.query
                .get("NCM", ["codigo", "descricao"])
                .with_additional(["vector"])
                .with_limit(page_size)
                .with_offset(offset)
                .do()
            )
            records = result_page.get("data", {}).get("Get", {}).get("NCM", [])
            if not records:
                break
            found = True
            file_name = f"ncm_backup_{timestamp}_{page_num}.json"
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump({"data": {"Get": {"NCM": records}}}, f, ensure_ascii=False, indent=2)
            tamanho_mb = os.path.getsize(file_name) / (1024*1024)
            print(f"\nBackup salvo em: {file_name}")
            print(f"Tamanho do arquivo: {tamanho_mb:.2f} MB")
            upload_to_google_drive(file_name, file_name)
            page_num += 1
            offset += page_size
        if not found:
            print("Nenhum dado encontrado para backup!")
    except Exception as e:
        print(f"Erro ao fazer backup: {str(e)}")

def main():
    print("Iniciando processamento...")
    create_ncm_schema()
    process_excel()
    print("Processamento concluído!")
    
    # Exporta e faz upload do backup
    fazer_backup()
    
    # Exemplos de uso das outras funções...
    print("\nExemplo de busca por código NCM:")
    buscar_ncm_por_codigo("8471")
    
    print("\nExemplo de verificação de NCM:")
    verificar_ncm_nota("Notebook Dell Inspiron", "8471")
    print("\nExemplo de busca sem NCM informado:")
    verificar_ncm_nota("Notebook Dell Inspiron")

if __name__ == "__main__":
    main()
