#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2
import psycopg2.extras

# Configuração do banco de dados
DB_CONFIG = {
    'dbname': 'odoo18',
    'user': 'odoo18',
    'password': 'odoo18',
    'host': 'localhost',
    'port': 5435
}

def test_connection():
    """Testa a conexão com o banco de dados."""
    try:
        print("Tentando conectar ao banco de dados PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        print(f"Conexão bem sucedida! Versão do PostgreSQL: {db_version[0]}")
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def list_tables(conn):
    """Lista as tabelas disponíveis no banco de dados."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        print(f"\nTabelas disponíveis no banco de dados ({len(tables)}):")
        for i, table in enumerate(tables, 1):
            print(f"{i}. {table[0]}")
            
        return [table[0] for table in tables]
    except Exception as e:
        print(f"Erro ao listar tabelas: {e}")
        return []

def check_nfe_table(conn):
    """Verifica se a tabela importar_nfe_nfe existe e mostra suas informações."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Verificar se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'importar_nfe_nfe'
            );
        """)
        
        if not cursor.fetchone()[0]:
            print("\nA tabela 'importar_nfe_nfe' não foi encontrada no banco de dados.")
            return False
            
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM importar_nfe_nfe;")
        count = cursor.fetchone()[0]
        print(f"\nA tabela 'importar_nfe_nfe' contém {count} registros.")
        
        if count > 0:
            # Mostrar alguns registros
            cursor.execute("""
                SELECT id, name, chave_acesso, data_emissao, tipo_operacao, 
                       valor_total, state 
                FROM importar_nfe_nfe 
                LIMIT 5;
            """)
            
            records = cursor.fetchall()
            print("\nPrimeiros registros da tabela 'importar_nfe_nfe':")
            for record in records:
                print(f"ID: {record['id']}, Número: {record['name']}, "
                      f"Data: {record['data_emissao']}, "
                      f"Valor: {record['valor_total']}, Estado: {record['state']}")
            
            # Verificar registros de saída processados
            cursor.execute("""
                SELECT COUNT(*) 
                FROM importar_nfe_nfe 
                WHERE tipo_operacao = 'saida' AND state = 'processed';
            """)
            
            saida_count = cursor.fetchone()[0]
            print(f"\nExistem {saida_count} notas fiscais de saída processadas.")
            
            return True
        else:
            print("A tabela está vazia.")
            return False
            
    except Exception as e:
        print(f"Erro ao verificar tabela de NFe: {e}")
        return False

def check_item_table(conn):
    """Verifica se a tabela importar_nfe_item existe e mostra suas informações."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Verificar se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'importar_nfe_item'
            );
        """)
        
        if not cursor.fetchone()[0]:
            print("\nA tabela 'importar_nfe_item' não foi encontrada no banco de dados.")
            return False
            
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM importar_nfe_item;")
        count = cursor.fetchone()[0]
        print(f"\nA tabela 'importar_nfe_item' contém {count} registros.")
        
        if count > 0:
            # Mostrar alguns registros
            cursor.execute("""
                SELECT i.id, i.nfe_id, i.produto_id, i.quantidade, i.valor_total,
                       p.name as produto_nome, p.codigo as produto_codigo
                FROM importar_nfe_item i
                JOIN importar_nfe_produto p ON i.produto_id = p.id
                LIMIT 5;
            """)
            
            records = cursor.fetchall()
            print("\nPrimeiros registros da tabela 'importar_nfe_item':")
            for record in records:
                print(f"ID: {record['id']}, NFe ID: {record['nfe_id']}, "
                      f"Produto: {record['produto_nome']} ({record['produto_codigo']}), "
                      f"Quantidade: {record['quantidade']}, Valor: {record['valor_total']}")
            
            return True
        else:
            print("A tabela está vazia.")
            return False
            
    except Exception as e:
        print(f"Erro ao verificar tabela de itens: {e}")
        return False

def test_api_queries(conn):
    """Testa as consultas usadas pelas APIs do dashboard."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        print("\n=== Testando consultas da API ===")
        
        # Teste da consulta do dashboard principal
        print("\nConsulta de totais (dashboard):")
        cursor.execute("""
            SELECT COUNT(*) as total_nfes, 
                   SUM(valor_total) as valor_total
            FROM importar_nfe_nfe
            WHERE tipo_operacao = 'saida'
              AND state = 'processed'
        """)
        
        result = cursor.fetchone()
        print(f"Total de NFes: {result['total_nfes']}, Valor Total: {result['valor_total']}")
        
        # Teste da consulta de produtos mais vendidos
        print("\nConsulta de produtos mais vendidos:")
        cursor.execute("""
            SELECT p.name as nome,
                   p.codigo as codigo,
                   SUM(i.quantidade) as quantidade,
                   SUM(i.valor_total) as valor_total
            FROM importar_nfe_item i
            JOIN importar_nfe_nfe n ON i.nfe_id = n.id
            JOIN importar_nfe_produto p ON i.produto_id = p.id
            WHERE n.tipo_operacao = 'saida'
              AND n.state = 'processed'
            GROUP BY p.name, p.codigo
            ORDER BY SUM(i.quantidade) DESC, SUM(i.valor_total) DESC
            LIMIT 5
        """)
        
        produtos = cursor.fetchall()
        if produtos:
            print(f"Encontrados {len(produtos)} produtos:")
            for produto in produtos:
                print(f"  - {produto['nome']} ({produto['codigo']}): "
                      f"Quantidade: {produto['quantidade']}, Valor: {produto['valor_total']}")
        else:
            print("Nenhum produto encontrado com a consulta.")
        
        return True
        
    except Exception as e:
        print(f"Erro ao testar consultas da API: {e}")
        return False

def main():
    """Função principal"""
    print("=== Teste de Conexão com Banco de Dados ===")
    print(f"Configuração: {DB_CONFIG}")
    
    # Testar conexão
    conn = test_connection()
    if not conn:
        print("Falha na conexão. Verifique as configurações e tente novamente.")
        sys.exit(1)
    
    try:
        # Listar tabelas
        tables = list_tables(conn)
        
        # Verificar tabelas específicas
        nfe_ok = check_nfe_table(conn)
        item_ok = check_item_table(conn)
        
        # Testar consultas da API
        if nfe_ok and item_ok:
            api_test_ok = test_api_queries(conn)
        
        # Resumo
        print("\n=== Resumo do Teste ===")
        print(f"Conexão com o banco: {'OK' if conn else 'FALHA'}")
        print(f"Tabelas encontradas: {len(tables)}")
        print(f"Tabela NFe: {'OK' if nfe_ok else 'FALHA'}")
        print(f"Tabela Item: {'OK' if item_ok else 'FALHA'}")
        
        if nfe_ok and item_ok:
            print(f"Consultas da API: {'OK' if api_test_ok else 'FALHA'}")
            
            if api_test_ok:
                print("\nTodos os testes foram bem-sucedidos! A aplicação deve funcionar corretamente.")
            else:
                print("\nAs tabelas existem, mas há problemas com as consultas da API.")
        else:
            print("\nAlgumas tabelas necessárias não foram encontradas ou estão vazias.")
            
    except Exception as e:
        print(f"Erro durante os testes: {e}")
    finally:
        if conn:
            conn.close()
            print("\nConexão fechada.")

if __name__ == "__main__":
    main() 