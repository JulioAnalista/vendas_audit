#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração do banco de dados a partir das variáveis de ambiente
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'odoo18'),
    'user': os.getenv('DB_USER', 'odoo18'),
    'password': os.getenv('DB_PASSWORD', 'odoo18'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5435))
}

def connect_db():
    """Conecta ao banco de dados."""
    try:
        print("Conectando ao banco de dados PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("Conexão bem sucedida!")
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def check_data_status(conn):
    """Verifica o status dos dados no banco."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Verificar registros com data nula
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM importar_nfe_nfe
            WHERE data_emissao IS NULL
        """)
        
        total_null_dates = cursor.fetchone()['total']
        
        # Verificar registros por tipo de operação
        cursor.execute("""
            SELECT tipo_operacao, COUNT(*) as total
            FROM importar_nfe_nfe
            GROUP BY tipo_operacao
        """)
        
        tipos = {}
        for row in cursor.fetchall():
            tipos[row['tipo_operacao'] or 'NULL'] = row['total']
        
        # Verificar notas de saída com data
        cursor.execute("""
            SELECT COUNT(*) FROM importar_nfe_nfe
            WHERE tipo_operacao = 'saida' 
            AND data_emissao IS NOT NULL
        """)
        
        saidas_com_data = cursor.fetchone()[0]
        
        return {
            'total_null_dates': total_null_dates,
            'tipos_operacao': tipos,
            'saidas_com_data': saidas_com_data
        }
    except Exception as e:
        print(f"Erro ao verificar status dos dados: {e}")
        return None

def update_null_dates(conn, limit=1000):
    """Atualiza registros com data_emissao nulo."""
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE importar_nfe_nfe
            SET data_emissao = TIMESTAMP '2023-01-01' + 
                              (random() * (TIMESTAMP '2024-01-01' - TIMESTAMP '2023-01-01'))
            WHERE data_emissao IS NULL
            AND id IN (
                SELECT id FROM importar_nfe_nfe
                WHERE data_emissao IS NULL
                LIMIT %s
            )
        """, (limit,))
        
        updated = cursor.rowcount
        conn.commit()
        
        print(f"Foram atualizados {updated} registros com datas aleatórias.")
        return updated
    except Exception as e:
        conn.rollback()
        print(f"Erro ao atualizar datas: {e}")
        return 0

def create_saida_records(conn, limit=1000):
    """Cria registros de saída convertendo entradas existentes."""
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE importar_nfe_nfe
            SET tipo_operacao = 'saida'
            WHERE tipo_operacao = 'entrada'
            AND data_emissao IS NOT NULL
            AND id IN (
                SELECT id FROM importar_nfe_nfe
                WHERE tipo_operacao = 'entrada'
                AND data_emissao IS NOT NULL
                ORDER BY id
                LIMIT %s
            )
        """, (limit,))
        
        updated = cursor.rowcount
        conn.commit()
        
        print(f"Foram convertidos {updated} registros para tipo_operacao = 'saida'.")
        return updated
    except Exception as e:
        conn.rollback()
        print(f"Erro ao converter registros: {e}")
        return 0

def add_sample_data(conn, num_samples=50):
    """Adiciona dados de amostra para vendas."""
    try:
        cursor = conn.cursor()
        
        # Obter produtos existentes para usar
        cursor.execute("""
            SELECT id FROM importar_nfe_produto
            LIMIT 10
        """)
        
        produtos = cursor.fetchall()
        if not produtos:
            print("Não foram encontrados produtos para usar nos dados de amostra.")
            return 0
            
        # Obter emitentes e destinatários existentes
        cursor.execute("SELECT id FROM importar_nfe_emitente LIMIT 1")
        emitente_id = cursor.fetchone()
        
        cursor.execute("SELECT id FROM importar_nfe_destinatario LIMIT 1")
        destinatario_id = cursor.fetchone()
        
        if not emitente_id or not destinatario_id:
            print("Emitente ou destinatário não encontrado.")
            return 0
            
        # Criar notas fiscais de amostra
        inserted = 0
        for i in range(num_samples):
            # Data de emissão nos últimos 12 meses
            data_emissao = datetime.now() - timedelta(days=i*7)  # A cada 7 dias
            
            # Inserir nota fiscal
            cursor.execute("""
                INSERT INTO importar_nfe_nfe (
                    name, chave_acesso, numero, serie, modelo, tipo_operacao,
                    data_emissao, valor_produtos, valor_total,
                    emitente_id, destinatario_id, state, active
                )
                VALUES (
                    %s, %s, %s, %s, %s, 'saida',
                    %s, %s, %s,
                    %s, %s, 'processed', true
                )
                RETURNING id
            """, (
                f"NFE-{10000+i}", f"CHAVE{i:05d}", f"{10000+i}", "1", "55",
                data_emissao, 100.0 * (i+1), 100.0 * (i+1) * 1.1,
                emitente_id[0], destinatario_id[0]
            ))
            
            nfe_id = cursor.fetchone()[0]
            
            # Adicionar alguns itens à nota fiscal
            for j in range(1, 4):  # 3 itens por nota
                produto_id = produtos[(i+j) % len(produtos)][0]
                quantidade = j * 2.0
                valor_unitario = 50.0 * j
                valor_total = quantidade * valor_unitario
                
                cursor.execute("""
                    INSERT INTO importar_nfe_item (
                        nfe_id, produto_id, numero_item, quantidade,
                        valor_unitario, valor_total
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    nfe_id, produto_id, j, quantidade,
                    valor_unitario, valor_total
                ))
            
            inserted += 1
        
        conn.commit()
        print(f"Foram inseridas {inserted} notas fiscais de amostra com seus itens.")
        return inserted
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao adicionar dados de amostra: {e}")
        return 0

def main():
    """Função principal"""
    print("=== Gerador de Dados de Amostra ===")
    print(f"Configuração: {DB_CONFIG}")
    
    # Conectar ao banco de dados
    conn = connect_db()
    if not conn:
        print("Falha na conexão. Verifique as configurações e tente novamente.")
        sys.exit(1)
    
    try:
        # Verificar estado atual dos dados
        print("\nVerificando o estado atual dos dados...")
        status = check_data_status(conn)
        
        if status:
            print(f"- Registros com data nula: {status['total_null_dates']}")
            print("- Tipos de operação:")
            for tipo, total in status['tipos_operacao'].items():
                print(f"  * {tipo}: {total} registros")
            print(f"- Notas de saída com data: {status['saidas_com_data']}")
        
        # Atualizar datas nulas
        if status and status['total_null_dates'] > 0:
            print("\nAtualizando registros com data nula...")
            update_null_dates(conn, min(status['total_null_dates'], 1000))
        
        # Verificar se existem notas de saída suficientes
        if status and status.get('saidas_com_data', 0) < 50:
            if 'entrada' in status['tipos_operacao'] and status['tipos_operacao']['entrada'] > 0:
                print("\nConvertendo algumas notas de entrada para saída...")
                create_saida_records(conn, 100)
            
            # Adicionar dados de amostra
            print("\nAdicionando dados de amostra...")
            add_sample_data(conn, 50)
        
        # Verificar estado final
        print("\nEstado final dos dados:")
        final_status = check_data_status(conn)
        
        if final_status:
            print(f"- Registros com data nula: {final_status['total_null_dates']}")
            print("- Tipos de operação:")
            for tipo, total in final_status['tipos_operacao'].items():
                print(f"  * {tipo}: {total} registros")
            print(f"- Notas de saída com data: {final_status['saidas_com_data']}")
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")
    finally:
        if conn:
            conn.close()
            print("\nConexão fechada.")

if __name__ == "__main__":
    main() 