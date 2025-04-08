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
        print(f"Conexão bem sucedida ao banco {DB_CONFIG['dbname']} no host {DB_CONFIG['host']}!")
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def check_tables(conn):
    """Verifica as tabelas relevantes no banco de dados."""
    try:
        cursor = conn.cursor()
        
        # Verificar tabelas principais
        tables_to_check = [
            'importar_nfe_nfe',
            'importar_nfe_item',
            'importar_nfe_produto',
            'importar_nfe_emitente',
            'importar_nfe_destinatario'
        ]
        
        print("\nVerificando tabelas principais:")
        for table in tables_to_check:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                );
            """)
            exists = cursor.fetchone()[0]
            
            if exists:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✓ Tabela '{table}' encontrada com {count} registros")
            else:
                print(f"  ✗ Tabela '{table}' não encontrada")
                
        return True
    except Exception as e:
        print(f"Erro ao verificar tabelas: {e}")
        return False

def query_products(conn, limit=20):
    """Consulta produtos reais no banco de dados."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
            SELECT id, name, codigo, ncm, unidade 
            FROM importar_nfe_produto
            ORDER BY id
            LIMIT %s
        """, (limit,))
        
        products = cursor.fetchall()
        
        print(f"\nEncontrados {len(products)} produtos:")
        for product in products:
            print(f"  - {product['id']}: {product['name']} (Código: {product['codigo']}, NCM: {product['ncm']})")
            
        return products
    except Exception as e:
        print(f"Erro ao consultar produtos: {e}")
        return []

def query_sales(conn, limit=20):
    """Consulta vendas reais no banco de dados."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Verificar se existem registros de saída
        cursor.execute("""
            SELECT COUNT(*) 
            FROM importar_nfe_nfe
            WHERE tipo_operacao = 'saida'
        """)
        
        saida_count = cursor.fetchone()[0]
        tipo_operacao = 'saida' if saida_count > 0 else 'entrada'
        
        print(f"\nExistem {saida_count} notas fiscais de saída.")
        if saida_count == 0:
            print("Usando notas fiscais de entrada para a análise já que não há saídas.")
        
        # Consultar as notas fiscais
        cursor.execute("""
            SELECT id, name, chave_acesso, data_emissao, valor_total, state
            FROM importar_nfe_nfe
            WHERE tipo_operacao = %s
            AND data_emissao IS NOT NULL
            ORDER BY data_emissao DESC
            LIMIT %s
        """, (tipo_operacao, limit))
        
        sales = cursor.fetchall()
        
        print(f"\nEncontradas {len(sales)} notas fiscais de {tipo_operacao}:")
        for sale in sales:
            date_str = sale['data_emissao'].strftime('%d/%m/%Y') if sale['data_emissao'] else 'N/A'
            print(f"  - {sale['id']}: {sale['name']} (Data: {date_str}, Valor: {sale['valor_total']})")
            
        return sales
    except Exception as e:
        print(f"Erro ao consultar vendas: {e}")
        return []

def query_sale_items(conn, nfe_id):
    """Consulta itens de uma nota fiscal específica."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
            SELECT i.id, i.produto_id, i.quantidade, i.valor_unitario, i.valor_total,
                   p.name as produto_nome, p.codigo as produto_codigo, p.ncm
            FROM importar_nfe_item i
            JOIN importar_nfe_produto p ON i.produto_id = p.id
            WHERE i.nfe_id = %s
            ORDER BY i.numero_item
        """, (nfe_id,))
        
        items = cursor.fetchall()
        
        if items:
            print(f"\nItens da Nota Fiscal {nfe_id}:")
            for item in items:
                print(f"  - {item['produto_nome']} (Código: {item['produto_codigo']})")
                print(f"    Quantidade: {item['quantidade']}, Valor Unitário: {item['valor_unitario']}, Total: {item['valor_total']}")
        
        return items
    except Exception as e:
        print(f"Erro ao consultar itens da nota fiscal: {e}")
        return []

def query_products_by_period(conn):
    """Consulta produtos vendidos por período."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Verificar se existem registros de saída
        cursor.execute("""
            SELECT COUNT(*) 
            FROM importar_nfe_nfe
            WHERE tipo_operacao = 'saida'
            AND data_emissao IS NOT NULL
        """)
        
        saida_count = cursor.fetchone()[0]
        tipo_operacao = 'saida' if saida_count > 0 else 'entrada'
        
        # Definir período para últimos 12 meses
        hoje = datetime.now()
        data_inicio = hoje - timedelta(days=365)
        
        cursor.execute("""
            SELECT p.id, p.name, p.codigo, p.ncm,
                   SUM(i.quantidade) as total_quantidade,
                   SUM(i.valor_total) as total_valor
            FROM importar_nfe_item i
            JOIN importar_nfe_nfe n ON i.nfe_id = n.id
            JOIN importar_nfe_produto p ON i.produto_id = p.id
            WHERE n.tipo_operacao = %s
              AND n.data_emissao IS NOT NULL
              AND n.data_emissao >= %s
              AND n.data_emissao <= %s
            GROUP BY p.id, p.name, p.codigo, p.ncm
            ORDER BY total_quantidade DESC
            LIMIT 20
        """, (tipo_operacao, data_inicio, hoje))
        
        products = cursor.fetchall()
        
        print(f"\nTop 20 produtos mais {tipo_operacao} no último ano:")
        for i, product in enumerate(products, 1):
            print(f"{i}. {product['name']} (Código: {product['codigo']})")
            print(f"   Quantidade: {product['total_quantidade']}, Valor Total: {product['total_valor']}")
            
        return products
    except Exception as e:
        print(f"Erro ao consultar produtos por período: {e}")
        return []

def query_sales_by_month(conn):
    """Consulta vendas agrupadas por mês."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Verificar se existem registros de saída
        cursor.execute("""
            SELECT COUNT(*) 
            FROM importar_nfe_nfe
            WHERE tipo_operacao = 'saida'
            AND data_emissao IS NOT NULL
        """)
        
        saida_count = cursor.fetchone()[0]
        tipo_operacao = 'saida' if saida_count > 0 else 'entrada'
        
        # Definir período para últimos 12 meses
        hoje = datetime.now()
        data_inicio = hoje - timedelta(days=365)
        
        cursor.execute("""
            SELECT TO_CHAR(DATE_TRUNC('month', data_emissao), 'MM/YYYY') as mes,
                   COUNT(*) as quantidade,
                   SUM(valor_total) as valor_total
            FROM importar_nfe_nfe
            WHERE tipo_operacao = %s
              AND data_emissao IS NOT NULL
              AND data_emissao >= %s
              AND data_emissao <= %s
            GROUP BY mes
            ORDER BY mes
        """, (tipo_operacao, data_inicio, hoje))
        
        sales_by_month = cursor.fetchall()
        
        print(f"\nVendas por mês (último ano, tipo: {tipo_operacao}):")
        for sale in sales_by_month:
            print(f"  - {sale['mes']}: {sale['quantidade']} notas, Valor Total: {sale['valor_total']}")
            
        return sales_by_month
    except Exception as e:
        print(f"Erro ao consultar vendas por mês: {e}")
        return []

def main():
    """Função principal"""
    print("=== Consulta de Dados Reais do Banco PostgreSQL ===")
    print(f"Configuração: {DB_CONFIG}")
    
    # Conectar ao banco de dados
    conn = connect_db()
    if not conn:
        print("Falha na conexão. Verifique as configurações e tente novamente.")
        sys.exit(1)
    
    try:
        # Verificar tabelas
        check_tables(conn)
        
        # Consultar produtos
        products = query_products(conn)
        
        # Consultar vendas
        sales = query_sales(conn)
        
        # Se encontrou vendas, consultar itens da primeira venda
        if sales:
            items = query_sale_items(conn, sales[0]['id'])
        
        # Consultar produtos por período
        period_products = query_products_by_period(conn)
        
        # Consultar vendas por mês
        sales_by_month = query_sales_by_month(conn)
        
        print("\n=== Resumo das Consultas ===")
        print(f"Produtos encontrados: {len(products)}")
        print(f"Vendas encontradas: {len(sales)}")
        print(f"Produtos por período: {len(period_products)}")
        print(f"Meses com vendas: {len(sales_by_month)}")
        
    except Exception as e:
        print(f"Erro durante a execução: {e}")
    finally:
        if conn:
            conn.close()
            print("\nConexão fechada.")

if __name__ == "__main__":
    main() 