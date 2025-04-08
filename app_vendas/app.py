#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import datetime
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, jsonify, g
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# Configuração do banco de dados a partir das variáveis de ambiente
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'odoo18'),
    'user': os.getenv('DB_USER', 'odoo18'),
    'password': os.getenv('DB_PASSWORD', 'odoo18'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5435))
}

def get_db():
    """Conexão com o banco de dados PostgreSQL."""
    if 'db' not in g:
        g.db = psycopg2.connect(**DB_CONFIG)
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Fecha a conexão com o banco de dados ao finalizar a requisição."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def json_serial(obj):
    """Serializa objetos de data/hora para JSON."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

@app.route('/')
def index():
    """Página principal com o dashboard."""
    return render_template('index.html')

@app.route('/api/vendas/dashboard', methods=['GET'])
def api_vendas_dashboard():
    """API para obter dados do dashboard de vendas."""
    try:
        print("Iniciando API de dashboard")
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Parâmetros para filtro
        periodo = request.args.get('periodo', 'mes')
        print(f"Período solicitado: {periodo}")
        
        # Define o intervalo de datas com base no período
        hoje = datetime.datetime.now()
        
        if periodo == 'semana':
            data_inicio = hoje - datetime.timedelta(days=7)
        elif periodo == 'mes':
            data_inicio = hoje - datetime.timedelta(days=30)
        elif periodo == 'trimestre':
            data_inicio = hoje - datetime.timedelta(days=90)
        elif periodo == 'ano':
            data_inicio = hoje - datetime.timedelta(days=365)
        else:
            data_inicio = hoje - datetime.timedelta(days=30)  # Default: último mês
            
        print(f"Intervalo de datas: {data_inicio} até {hoje}")
        
        # Verificar se existem registros de saída
        cursor.execute("""
            SELECT COUNT(*) 
            FROM importar_nfe_nfe
            WHERE tipo_operacao = 'saida'
            AND data_emissao IS NOT NULL
        """)
        
        saida_count = cursor.fetchone()[0]
        print(f"Contagem de registros de saída: {saida_count}")
        tipo_operacao = 'saida' if saida_count > 0 else 'entrada'
        print(f"Tipo de operação selecionado: {tipo_operacao}")
        
        # Consulta para obter total de NFes e valores
        query_totais = """
            SELECT COUNT(*) as total_nfes, 
                   SUM(valor_total) as valor_total
            FROM importar_nfe_nfe
            WHERE tipo_operacao = %s
              AND data_emissao IS NOT NULL
              AND data_emissao >= %s
              AND data_emissao <= %s
        """
        print(f"Executando consulta de totais: {query_totais} com parâmetros ({tipo_operacao}, {data_inicio}, {hoje})")
        
        cursor.execute(query_totais, (tipo_operacao, data_inicio, hoje))
        result_totais = cursor.fetchone()
        print(f"Resultado da consulta de totais: {result_totais}")
        
        # Consulta para obter vendas por dia
        query_por_dia = """
            SELECT TO_CHAR(DATE(data_emissao AT TIME ZONE 'UTC'), 'DD/MM/YYYY') as data,
                   COUNT(*) as quantidade,
                   SUM(valor_total) as valor
            FROM importar_nfe_nfe
            WHERE tipo_operacao = %s
              AND data_emissao IS NOT NULL
              AND data_emissao >= %s
              AND data_emissao <= %s
            GROUP BY TO_CHAR(DATE(data_emissao AT TIME ZONE 'UTC'), 'DD/MM/YYYY')
            ORDER BY TO_CHAR(DATE(data_emissao AT TIME ZONE 'UTC'), 'DD/MM/YYYY')
        """
        print(f"Executando consulta de vendas por dia: {query_por_dia}")
        
        cursor.execute(query_por_dia, (tipo_operacao, data_inicio, hoje))
        vendas_resultado = cursor.fetchall()
        print(f"Número de registros retornados para vendas por dia: {len(vendas_resultado)}")
        
        vendas_por_dia = {}
        for row in vendas_resultado:
            vendas_por_dia[row['data']] = {
                'quantidade': row['quantidade'],
                'valor': float(row['valor']) if row['valor'] else 0
            }
        
        # Preparando o resultado
        resultado = {
            'periodo': periodo,
            'tipo_operacao': tipo_operacao,
            'total_nfes': result_totais['total_nfes'] if result_totais['total_nfes'] else 0,
            'valor_total': float(result_totais['valor_total']) if result_totais['valor_total'] else 0,
            'vendas_por_dia': vendas_por_dia
        }
        
        print(f"Retornando resultado: {json.dumps(resultado, default=json_serial)[:200]}...")
        return jsonify(resultado)
    except Exception as e:
        print(f"ERRO na API de dashboard: {str(e)}")
        app.logger.error(f"Erro na API de dashboard: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/produtos/mais-vendidos', methods=['GET'])
def api_produtos_mais_vendidos():
    """API para obter os produtos mais vendidos."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Parâmetros para filtro
        periodo = request.args.get('periodo', 'mes')
        limite = int(request.args.get('limite', 10))
        
        # Define o intervalo de datas com base no período
        hoje = datetime.datetime.now()
        
        if periodo == 'semana':
            data_inicio = hoje - datetime.timedelta(days=7)
        elif periodo == 'mes':
            data_inicio = hoje - datetime.timedelta(days=30)
        elif periodo == 'trimestre':
            data_inicio = hoje - datetime.timedelta(days=90)
        elif periodo == 'ano':
            data_inicio = hoje - datetime.timedelta(days=365)
        else:
            data_inicio = hoje - datetime.timedelta(days=30)  # Default: último mês
            
        # Verificar se existem registros de saída
        cursor.execute("""
            SELECT COUNT(*) 
            FROM importar_nfe_nfe
            WHERE tipo_operacao = 'saida'
            AND data_emissao IS NOT NULL
        """)
        
        saida_count = cursor.fetchone()[0]
        tipo_operacao = 'saida' if saida_count > 0 else 'entrada'
        
        # Consulta para obter produtos mais vendidos
        cursor.execute("""
            SELECT p.name as nome,
                   p.codigo as codigo,
                   SUM(i.quantidade) as quantidade,
                   SUM(i.valor_total) as valor_total
            FROM importar_nfe_item i
            JOIN importar_nfe_nfe n ON i.nfe_id = n.id
            JOIN importar_nfe_produto p ON i.produto_id = p.id
            WHERE n.tipo_operacao = %s
              AND n.data_emissao IS NOT NULL
              AND n.data_emissao >= %s
              AND n.data_emissao <= %s
            GROUP BY p.name, p.codigo
            ORDER BY quantidade DESC, valor_total DESC
            LIMIT %s
        """, (tipo_operacao, data_inicio, hoje, limite))
        
        produtos = []
        for row in cursor.fetchall():
            produtos.append({
                'nome': row['nome'],
                'codigo': row['codigo'],
                'quantidade': float(row['quantidade']) if row['quantidade'] else 0,
                'valor_total': float(row['valor_total']) if row['valor_total'] else 0
            })
        
        # Preparando o resultado
        resultado = {
            'periodo': periodo,
            'tipo_operacao': tipo_operacao,
            'produtos': produtos
        }
        
        return jsonify(resultado)
    except Exception as e:
        app.logger.error(f"Erro na API de produtos mais vendidos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/vendas/por-periodo', methods=['GET'])
def api_vendas_por_periodo():
    """API para obter vendas agrupadas por período (mês/ano)."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Parâmetros para filtro
        ano = request.args.get('ano', datetime.datetime.now().year)
        
        # Verificar se existem registros de saída
        cursor.execute("""
            SELECT COUNT(*) 
            FROM importar_nfe_nfe
            WHERE tipo_operacao = 'saida'
            AND data_emissao IS NOT NULL
        """)
        
        saida_count = cursor.fetchone()[0]
        tipo_operacao = 'saida' if saida_count > 0 else 'entrada'
        
        # Consulta para obter vendas por mês
        cursor.execute("""
            SELECT TO_CHAR(DATE_TRUNC('month', data_emissao), 'MM/YYYY') as mes,
                   COUNT(*) as quantidade,
                   SUM(valor_total) as valor_total
            FROM importar_nfe_nfe
            WHERE tipo_operacao = %s
              AND data_emissao IS NOT NULL
              AND EXTRACT(YEAR FROM data_emissao) = %s
            GROUP BY TO_CHAR(DATE_TRUNC('month', data_emissao), 'MM/YYYY')
            ORDER BY TO_CHAR(DATE_TRUNC('month', data_emissao), 'MM/YYYY')
        """, (tipo_operacao, ano))
        
        vendas_por_mes = []
        for row in cursor.fetchall():
            vendas_por_mes.append({
                'mes': row['mes'],
                'quantidade': row['quantidade'],
                'valor_total': float(row['valor_total']) if row['valor_total'] else 0
            })
        
        return jsonify({'tipo_operacao': tipo_operacao, 'vendas': vendas_por_mes})
    except Exception as e:
        app.logger.error(f"Erro na API de vendas por período: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/produtos/por-categoria', methods=['GET'])
def api_produtos_por_categoria():
    """API para obter produtos vendidos agrupados por NCM."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Parâmetros para filtro
        periodo = request.args.get('periodo', 'mes')
        
        # Define o intervalo de datas com base no período
        hoje = datetime.datetime.now()
        
        if periodo == 'semana':
            data_inicio = hoje - datetime.timedelta(days=7)
        elif periodo == 'mes':
            data_inicio = hoje - datetime.timedelta(days=30)
        elif periodo == 'trimestre':
            data_inicio = hoje - datetime.timedelta(days=90)
        elif periodo == 'ano':
            data_inicio = hoje - datetime.timedelta(days=365)
        else:
            data_inicio = hoje - datetime.timedelta(days=30)  # Default: último mês
            
        # Verificar se existem registros de saída
        cursor.execute("""
            SELECT COUNT(*) 
            FROM importar_nfe_nfe
            WHERE tipo_operacao = 'saida'
            AND data_emissao IS NOT NULL
        """)
        
        saida_count = cursor.fetchone()[0]
        tipo_operacao = 'saida' if saida_count > 0 else 'entrada'
        
        # Consulta para obter produtos por NCM
        cursor.execute("""
            SELECT 
                COALESCE(p.ncm, 'Sem NCM') as ncm,
                SUM(i.quantidade) as quantidade,
                SUM(i.valor_total) as valor_total
            FROM importar_nfe_item i
            JOIN importar_nfe_nfe n ON i.nfe_id = n.id
            JOIN importar_nfe_produto p ON i.produto_id = p.id
            WHERE n.tipo_operacao = %s
              AND n.data_emissao IS NOT NULL
              AND n.data_emissao >= %s
              AND n.data_emissao <= %s
            GROUP BY p.ncm
            ORDER BY valor_total DESC
        """, (tipo_operacao, data_inicio, hoje))
        
        produtos_por_ncm = []
        for row in cursor.fetchall():
            produtos_por_ncm.append({
                'ncm': row['ncm'],
                'quantidade': float(row['quantidade']) if row['quantidade'] else 0,
                'valor_total': float(row['valor_total']) if row['valor_total'] else 0
            })
        
        return jsonify({'tipo_operacao': tipo_operacao, 'produtos': produtos_por_ncm})
    except Exception as e:
        app.logger.error(f"Erro na API de produtos por categoria: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print(f"Iniciando aplicação com configuração de banco: {DB_CONFIG}")
    app.run(debug=True, host='0.0.0.0', port=8000) 