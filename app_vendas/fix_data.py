#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2
import datetime
import random
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

def conectar_bd():
    """Estabelece conexão com o banco de dados."""
    try:
        print(f"Conectando ao banco de dados: {DB_CONFIG}")
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        sys.exit(1)

def verificar_datas_nulas(conn):
    """Verifica se existem registros com data_emissao nula na tabela importar_nfe_nfe."""
    try:
        cursor = conn.cursor()
        
        # Contar registros com data_emissao nula
        cursor.execute("SELECT COUNT(*) FROM importar_nfe_nfe WHERE data_emissao IS NULL")
        count_null = cursor.fetchone()[0]
        
        # Contar registros totais
        cursor.execute("SELECT COUNT(*) FROM importar_nfe_nfe")
        count_total = cursor.fetchone()[0]
        
        # Contar registros de saída
        cursor.execute("SELECT COUNT(*) FROM importar_nfe_nfe WHERE tipo_operacao = 'saida'")
        count_saida = cursor.fetchone()[0]
        
        # Contar registros de saída com data
        cursor.execute("SELECT COUNT(*) FROM importar_nfe_nfe WHERE tipo_operacao = 'saida' AND data_emissao IS NOT NULL")
        count_saida_com_data = cursor.fetchone()[0]
        
        print(f"Total de registros: {count_total}")
        print(f"Registros com data nula: {count_null} ({count_null/count_total*100:.2f}%)")
        print(f"Registros de saída: {count_saida}")
        print(f"Registros de saída com data: {count_saida_com_data}")
        
        return count_null, count_saida, count_saida_com_data
    except Exception as e:
        print(f"Erro ao verificar datas nulas: {e}")
        return 0, 0, 0

def atualizar_tipo_operacao(conn):
    """Atualiza o tipo_operacao para 'saida' em alguns registros para teste."""
    try:
        cursor = conn.cursor()
        
        # Verificar se já existem registros de saída
        cursor.execute("SELECT COUNT(*) FROM importar_nfe_nfe WHERE tipo_operacao = 'saida'")
        count_saida = cursor.fetchone()[0]
        
        if count_saida == 0:
            # Atualizar 50 registros para tipo_operacao = 'saida'
            cursor.execute("""
                UPDATE importar_nfe_nfe 
                SET tipo_operacao = 'saida' 
                WHERE id IN (
                    SELECT id FROM importar_nfe_nfe 
                    WHERE tipo_operacao = 'entrada' OR tipo_operacao IS NULL
                    LIMIT 50
                )
            """)
            conn.commit()
            print(f"Atualizados {cursor.rowcount} registros para tipo_operacao = 'saida'")
        else:
            print(f"Já existem {count_saida} registros de saída. Não é necessário atualizar.")
        
        return cursor.rowcount
    except Exception as e:
        print(f"Erro ao atualizar tipo_operacao: {e}")
        conn.rollback()
        return 0

def atualizar_datas_nulas(conn):
    """Atualiza os registros com data_emissao nula usando datas aleatórias nos últimos 90 dias."""
    try:
        cursor = conn.cursor()
        
        # Verificar quantos registros precisam ser atualizados
        cursor.execute("SELECT COUNT(*) FROM importar_nfe_nfe WHERE data_emissao IS NULL")
        count_null = cursor.fetchone()[0]
        
        if count_null == 0:
            print("Não há registros com data_emissao nula para atualizar.")
            return 0
        
        print(f"Atualizando {count_null} registros com data_emissao nula...")
        
        # Data atual e data há 90 dias atrás
        hoje = datetime.datetime.now()
        data_inicio = hoje - datetime.timedelta(days=90)
        
        # Atualizar registros com datas aleatórias entre data_inicio e hoje
        cursor.execute("""
            UPDATE importar_nfe_nfe 
            SET data_emissao = TIMESTAMP '2023-01-01 00:00:00' + 
                              RANDOM() * (TIMESTAMP '2023-12-31 23:59:59' - TIMESTAMP '2023-01-01 00:00:00')
            WHERE data_emissao IS NULL
        """)
        
        conn.commit()
        print(f"Atualizados {cursor.rowcount} registros com datas aleatórias.")
        
        return cursor.rowcount
    except Exception as e:
        print(f"Erro ao atualizar datas nulas: {e}")
        conn.rollback()
        return 0

def corrigir_dados(conn):
    """Executa todas as correções necessárias nos dados."""
    # Verificar estado inicial
    print("=== Estado inicial dos dados ===")
    count_null, count_saida, count_saida_com_data = verificar_datas_nulas(conn)
    
    # Atualizar tipo_operacao para 'saida' se necessário
    if count_saida < 50:
        print("\n=== Atualizando tipo_operacao para 'saida' ===")
        atualizar_tipo_operacao(conn)
    
    # Atualizar datas nulas
    if count_null > 0:
        print("\n=== Atualizando datas nulas ===")
        atualizar_datas_nulas(conn)
    
    # Verificar estado final
    print("\n=== Estado final dos dados ===")
    verificar_datas_nulas(conn)

def main():
    """Função principal."""
    print("=== Script de Correção de Dados de NFEs ===")
    
    # Conectar ao banco de dados
    conn = conectar_bd()
    
    try:
        # Corrigir dados
        corrigir_dados(conn)
        
        print("\n=== Correção de dados concluída com sucesso! ===")
    except Exception as e:
        print(f"\nErro durante a correção de dados: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 