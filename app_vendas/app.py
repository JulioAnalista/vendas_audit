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

@app.route('/relatorios')
def relatorios():
    """Página de relatórios detalhados."""
    # Preparar dados para a página de relatórios
    conn = get_db()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Obter informações para indicadores
        cursor.execute("""
            SELECT 
                SUM(valor_total) as total_ano,
                AVG(valor_total) as ticket_medio,
                TO_CHAR(DATE_TRUNC('month', data_emissao), 'MM/YYYY') as mes,
                SUM(valor_total) as valor_mes
            FROM importar_nfe_nfe
            WHERE tipo_operacao = 'saida'
              AND data_emissao >= NOW() - INTERVAL '1 year'
            GROUP BY mes
            ORDER BY valor_mes DESC
            LIMIT 1
        """)
        
        melhor_mes_info = cursor.fetchone()
        info = {
            'total_ano': f"R$ {melhor_mes_info['total_ano']:.2f}" if melhor_mes_info and melhor_mes_info['total_ano'] else 'R$ 0,00',
            'ticket_medio': f"R$ {melhor_mes_info['ticket_medio']:.2f}" if melhor_mes_info and melhor_mes_info['ticket_medio'] else 'R$ 0,00',
            'melhor_mes': melhor_mes_info['mes'] if melhor_mes_info else 'N/A'
        }
        
        # Obter top NCMs
        cursor.execute("""
            SELECT 
                COALESCE(p.ncm, 'Sem NCM') as codigo,
                COALESCE(p.ncm, 'Sem NCM') as descricao,
                SUM(i.valor_total) as valor
            FROM importar_nfe_produto p
            JOIN importar_nfe_item i ON p.id = i.produto_id
            JOIN importar_nfe_nfe n ON i.nfe_id = n.id
            WHERE n.tipo_operacao = 'saida'
              AND n.data_emissao >= NOW() - INTERVAL '1 year'
            GROUP BY p.ncm
            ORDER BY valor DESC
            LIMIT 10
        """)
        
        ncms = []
        for row in cursor.fetchall():
            ncms.append({
                'codigo': row['codigo'],
                'descricao': row['descricao'],
                'valor': f"R$ {row['valor']:.2f}" if row['valor'] else 'R$ 0,00'
            })
        
        # Obter top produtos
        cursor.execute("""
            SELECT 
                p.name as nome,
                p.codigo,
                p.ean,
                COALESCE(p.ncm, 'Sem NCM') as ncm,
                SUM(i.quantidade) as quantidade,
                SUM(i.valor_total) as valor_total,
                AVG(i.valor_unitario) as preco_medio
            FROM importar_nfe_produto p
            JOIN importar_nfe_item i ON p.id = i.produto_id
            JOIN importar_nfe_nfe n ON i.nfe_id = n.id
            WHERE n.tipo_operacao = 'saida'
              AND n.data_emissao >= NOW() - INTERVAL '1 year'
            GROUP BY p.name, p.codigo, p.ean, p.ncm
            ORDER BY valor_total DESC
            LIMIT 10
        """)
        
        produtos = []
        for row in cursor.fetchall():
            produtos.append({
                'nome': row['nome'],
                'codigo': row['codigo'],
                'ean': row['ean'] if row['ean'] else '',
                'ncm': row['ncm'],
                'quantidade': f"{row['quantidade']:.0f}" if row['quantidade'] else '0',
                'valor_total': f"R$ {row['valor_total']:.2f}" if row['valor_total'] else 'R$ 0,00',
                'preco_medio': f"R$ {row['preco_medio']:.2f}" if row['preco_medio'] else 'R$ 0,00'
            })
        
        return render_template('relatorios.html', info=info, ncms=ncms, produtos=produtos)
    except Exception as e:
        app.logger.error(f"Erro ao carregar página de relatórios: {str(e)}")
        return render_template('relatorios.html', erro=str(e))
    finally:
        if conn:
            conn.close()

@app.route('/api/gerar-relatorios', methods=['GET'])
def api_gerar_relatorios():
    """API para gerar relatórios."""
    try:
        # Chamada ao script de análise de produtos
        import subprocess
        result = subprocess.run(['python', 'analisar_produtos.py'], capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({'success': True, 'message': 'Relatórios gerados com sucesso.'})
        else:
            return jsonify({
                'success': False, 
                'error': f"Erro ao gerar relatórios: {result.stderr}"
            }), 500
    except Exception as e:
        app.logger.error(f"Erro na API de geração de relatórios: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/vendas/dashboard', methods=['GET'])
def api_vendas_dashboard():
    """API para obter dados do dashboard de vendas."""
    try:
        print("Iniciando API de dashboard")
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Coleta dos parâmetros de filtro
        tipo_filtro = request.args.get('tipo_filtro', 'ultimos_dias')
        print(f"Tipo de filtro: {tipo_filtro}")
        
        # Define o intervalo de datas com base no tipo de filtro e parâmetros
        hoje = datetime.datetime.now()
        
        if tipo_filtro == 'ultimos_dias':
            dias = int(request.args.get('dias', 30))
            data_inicio = hoje - datetime.timedelta(days=dias)
            periodo_desc = f"Últimos {dias} dias"
        
        elif tipo_filtro == 'ano':
            ano = int(request.args.get('ano', hoje.year))
            data_inicio = datetime.datetime(ano, 1, 1)
            data_fim = datetime.datetime(ano, 12, 31, 23, 59, 59)
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar o ano inteiro
            periodo_desc = f"Ano {ano}"
            
        elif tipo_filtro == 'trimestre':
            ano = int(request.args.get('ano', hoje.year))
            trimestre = int(request.args.get('trimestre', ((hoje.month-1)//3)+1))
            mes_inicio = (trimestre - 1) * 3 + 1
            mes_fim = mes_inicio + 2
            
            data_inicio = datetime.datetime(ano, mes_inicio, 1)
            if mes_fim == 12:
                data_fim = datetime.datetime(ano, mes_fim, 31, 23, 59, 59)
            else:
                data_fim = datetime.datetime(ano, mes_fim + 1, 1) - datetime.timedelta(seconds=1)
            
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar o trimestre inteiro
            periodo_desc = f"{trimestre}º Trimestre de {ano}"
            
        elif tipo_filtro == 'mes':
            ano = int(request.args.get('ano', hoje.year))
            mes = int(request.args.get('mes', hoje.month))
            
            data_inicio = datetime.datetime(ano, mes, 1)
            if mes == 12:
                data_fim = datetime.datetime(ano, 12, 31, 23, 59, 59)
            else:
                data_fim = datetime.datetime(ano, mes + 1, 1) - datetime.timedelta(seconds=1)
            
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar o mês inteiro
            nomes_meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                           'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
            periodo_desc = f"{nomes_meses[mes-1]} de {ano}"
            
        elif tipo_filtro == 'semana':
            data_str = request.args.get('data', hoje.strftime('%Y-%m-%d'))
            data_ref = datetime.datetime.strptime(data_str, '%Y-%m-%d')
            
            # Calcular o início da semana (segunda-feira)
            dia_semana = data_ref.weekday()  # 0 = segunda, 6 = domingo
            data_inicio = data_ref - datetime.timedelta(days=dia_semana)
            data_fim = data_inicio + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar a semana inteira
            periodo_desc = f"Semana de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
            
        else:  # Default: últimos 30 dias
            data_inicio = hoje - datetime.timedelta(days=30)
            periodo_desc = "Últimos 30 dias"
            
        print(f"Período: {periodo_desc}")
        print(f"Intervalo de datas: de {data_inicio} até {hoje}")
        
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
            'periodo': periodo_desc,
            'tipo_operacao': tipo_operacao,
            'data_inicio': data_inicio.strftime('%Y-%m-%d'),
            'data_fim': hoje.strftime('%Y-%m-%d'),
            'tipo_filtro': tipo_filtro,
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
        
        # Coleta dos parâmetros de filtro
        tipo_filtro = request.args.get('tipo_filtro', 'ultimos_dias')
        limite = int(request.args.get('limite', 10))
        
        # Define o intervalo de datas com base no tipo de filtro e parâmetros
        hoje = datetime.datetime.now()
        
        if tipo_filtro == 'ultimos_dias':
            dias = int(request.args.get('dias', 30))
            data_inicio = hoje - datetime.timedelta(days=dias)
            periodo_desc = f"Últimos {dias} dias"
        
        elif tipo_filtro == 'ano':
            ano = int(request.args.get('ano', hoje.year))
            data_inicio = datetime.datetime(ano, 1, 1)
            data_fim = datetime.datetime(ano, 12, 31, 23, 59, 59)
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar o ano inteiro
            periodo_desc = f"Ano {ano}"
            
        elif tipo_filtro == 'trimestre':
            ano = int(request.args.get('ano', hoje.year))
            trimestre = int(request.args.get('trimestre', ((hoje.month-1)//3)+1))
            mes_inicio = (trimestre - 1) * 3 + 1
            mes_fim = mes_inicio + 2
            
            data_inicio = datetime.datetime(ano, mes_inicio, 1)
            if mes_fim == 12:
                data_fim = datetime.datetime(ano, mes_fim, 31, 23, 59, 59)
            else:
                data_fim = datetime.datetime(ano, mes_fim + 1, 1) - datetime.timedelta(seconds=1)
            
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar o trimestre inteiro
            periodo_desc = f"{trimestre}º Trimestre de {ano}"
            
        elif tipo_filtro == 'mes':
            ano = int(request.args.get('ano', hoje.year))
            mes = int(request.args.get('mes', hoje.month))
            
            data_inicio = datetime.datetime(ano, mes, 1)
            if mes == 12:
                data_fim = datetime.datetime(ano, 12, 31, 23, 59, 59)
            else:
                data_fim = datetime.datetime(ano, mes + 1, 1) - datetime.timedelta(seconds=1)
            
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar o mês inteiro
            nomes_meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                           'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
            periodo_desc = f"{nomes_meses[mes-1]} de {ano}"
            
        elif tipo_filtro == 'semana':
            data_str = request.args.get('data', hoje.strftime('%Y-%m-%d'))
            data_ref = datetime.datetime.strptime(data_str, '%Y-%m-%d')
            
            # Calcular o início da semana (segunda-feira)
            dia_semana = data_ref.weekday()  # 0 = segunda, 6 = domingo
            data_inicio = data_ref - datetime.timedelta(days=dia_semana)
            data_fim = data_inicio + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar a semana inteira
            periodo_desc = f"Semana de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
            
        else:  # Default: últimos 30 dias
            data_inicio = hoje - datetime.timedelta(days=30)
            periodo_desc = "Últimos 30 dias"
            
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
                   p.ean as ean,
                   SUM(i.quantidade) as quantidade,
                   SUM(i.valor_total) as valor_total
            FROM importar_nfe_item i
            JOIN importar_nfe_nfe n ON i.nfe_id = n.id
            JOIN importar_nfe_produto p ON i.produto_id = p.id
            WHERE n.tipo_operacao = %s
              AND n.data_emissao IS NOT NULL
              AND n.data_emissao >= %s
              AND n.data_emissao <= %s
            GROUP BY p.name, p.codigo, p.ean
            ORDER BY quantidade DESC, valor_total DESC
            LIMIT %s
        """, (tipo_operacao, data_inicio, hoje, limite))
        
        produtos = []
        for row in cursor.fetchall():
            produtos.append({
                'nome': row['nome'],
                'codigo': row['codigo'],
                'ean': row['ean'] if row['ean'] else '',
                'quantidade': float(row['quantidade']) if row['quantidade'] else 0,
                'valor_total': float(row['valor_total']) if row['valor_total'] else 0
            })
        
        # Preparando o resultado
        resultado = {
            'periodo': periodo_desc,
            'tipo_operacao': tipo_operacao,
            'data_inicio': data_inicio.strftime('%Y-%m-%d'),
            'data_fim': hoje.strftime('%Y-%m-%d'),
            'tipo_filtro': tipo_filtro,
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
        
        # Coleta dos parâmetros de filtro
        tipo_filtro = request.args.get('tipo_filtro', 'ultimos_dias')
        
        # Define o intervalo de datas com base no tipo de filtro e parâmetros
        hoje = datetime.datetime.now()
        
        if tipo_filtro == 'ultimos_dias':
            dias = int(request.args.get('dias', 30))
            data_inicio = hoje - datetime.timedelta(days=dias)
            periodo_desc = f"Últimos {dias} dias"
        
        elif tipo_filtro == 'ano':
            ano = int(request.args.get('ano', hoje.year))
            data_inicio = datetime.datetime(ano, 1, 1)
            data_fim = datetime.datetime(ano, 12, 31, 23, 59, 59)
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar o ano inteiro
            periodo_desc = f"Ano {ano}"
            
        elif tipo_filtro == 'trimestre':
            ano = int(request.args.get('ano', hoje.year))
            trimestre = int(request.args.get('trimestre', ((hoje.month-1)//3)+1))
            mes_inicio = (trimestre - 1) * 3 + 1
            mes_fim = mes_inicio + 2
            
            data_inicio = datetime.datetime(ano, mes_inicio, 1)
            if mes_fim == 12:
                data_fim = datetime.datetime(ano, mes_fim, 31, 23, 59, 59)
            else:
                data_fim = datetime.datetime(ano, mes_fim + 1, 1) - datetime.timedelta(seconds=1)
            
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar o trimestre inteiro
            periodo_desc = f"{trimestre}º Trimestre de {ano}"
            
        elif tipo_filtro == 'mes':
            ano = int(request.args.get('ano', hoje.year))
            mes = int(request.args.get('mes', hoje.month))
            
            data_inicio = datetime.datetime(ano, mes, 1)
            if mes == 12:
                data_fim = datetime.datetime(ano, 12, 31, 23, 59, 59)
            else:
                data_fim = datetime.datetime(ano, mes + 1, 1) - datetime.timedelta(seconds=1)
            
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar o mês inteiro
            nomes_meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                           'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
            periodo_desc = f"{nomes_meses[mes-1]} de {ano}"
            
        elif tipo_filtro == 'semana':
            data_str = request.args.get('data', hoje.strftime('%Y-%m-%d'))
            data_ref = datetime.datetime.strptime(data_str, '%Y-%m-%d')
            
            # Calcular o início da semana (segunda-feira)
            dia_semana = data_ref.weekday()  # 0 = segunda, 6 = domingo
            data_inicio = data_ref - datetime.timedelta(days=dia_semana)
            data_fim = data_inicio + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            hoje = data_fim  # Usando data_fim em vez de hoje para mostrar a semana inteira
            periodo_desc = f"Semana de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
            
        else:  # Default: últimos 30 dias
            data_inicio = hoje - datetime.timedelta(days=30)
            periodo_desc = "Últimos 30 dias"
            
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
        
        # Preparando o resultado
        resultado = {
            'periodo': periodo_desc,
            'tipo_operacao': tipo_operacao,
            'data_inicio': data_inicio.strftime('%Y-%m-%d'),
            'data_fim': hoje.strftime('%Y-%m-%d'),
            'tipo_filtro': tipo_filtro,
            'produtos': produtos_por_ncm
        }
        
        return jsonify(resultado)
    except Exception as e:
        app.logger.error(f"Erro na API de produtos por categoria: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/produtos')
def produtos():
    """Página de listagem de produtos."""
    conn = get_db()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Obter todos os NCMs distintos
        cursor.execute("""
            SELECT DISTINCT COALESCE(ncm, 'Sem NCM') as ncm
            FROM importar_nfe_produto
            ORDER BY ncm
        """)
        
        ncms = [row['ncm'] for row in cursor.fetchall()]
        
        # Obter produtos com dados de vendas
        cursor.execute("""
            SELECT 
                p.id,
                p.name as nome,
                p.codigo,
                p.ean,
                COALESCE(p.ncm, 'Sem NCM') as ncm,
                COALESCE(SUM(i.quantidade), 0) as quantidade,
                COALESCE(SUM(i.valor_total), 0) as valor_total,
                CASE WHEN SUM(i.quantidade) > 0 
                     THEN SUM(i.valor_total) / SUM(i.quantidade) 
                     ELSE 0 
                END as preco_medio
            FROM importar_nfe_produto p
            LEFT JOIN importar_nfe_item i ON p.id = i.produto_id
            LEFT JOIN importar_nfe_nfe n ON i.nfe_id = n.id AND n.tipo_operacao = 'saida'
            GROUP BY p.id, p.name, p.codigo, p.ean, p.ncm
            ORDER BY p.name
            LIMIT 1000
        """)
        
        produtos = []
        for row in cursor.fetchall():
            produtos.append({
                'id': row['id'],
                'nome': row['nome'],
                'codigo': row['codigo'],
                'ean': row['ean'] if row['ean'] else '',
                'ncm': row['ncm'],
                'quantidade': f"{row['quantidade']:.0f}" if row['quantidade'] else '0',
                'valor_total': f"R$ {row['valor_total']:.2f}" if row['valor_total'] else 'R$ 0,00',
                'preco_medio': f"R$ {row['preco_medio']:.2f}" if row['preco_medio'] else 'R$ 0,00'
            })
        
        return render_template('produtos.html', produtos=produtos, ncms=ncms)
    except Exception as e:
        app.logger.error(f"Erro ao carregar página de produtos: {str(e)}")
        return render_template('produtos.html', erro=str(e))
    finally:
        if conn:
            conn.close()

@app.route('/api/produtos/<int:produto_id>', methods=['GET'])
def api_produto_detalhes(produto_id):
    """API para obter detalhes de um produto específico."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Obter informações do produto
        cursor.execute("""
            SELECT 
                p.id,
                p.name as nome,
                p.codigo,
                p.ean,
                COALESCE(p.ncm, 'Sem NCM') as ncm,
                COUNT(DISTINCT n.id) as qtd_nfes,
                COALESCE(SUM(i.quantidade), 0) as quantidade,
                COALESCE(SUM(i.valor_total), 0) as valor_total,
                CASE WHEN SUM(i.quantidade) > 0 
                     THEN SUM(i.valor_total) / SUM(i.quantidade) 
                     ELSE 0 
                END as preco_medio
            FROM importar_nfe_produto p
            LEFT JOIN importar_nfe_item i ON p.id = i.produto_id
            LEFT JOIN importar_nfe_nfe n ON i.nfe_id = n.id AND n.tipo_operacao = 'saida'
            WHERE p.id = %s
            GROUP BY p.id, p.name, p.codigo, p.ean, p.ncm
        """, (produto_id,))
        
        produto = cursor.fetchone()
        if not produto:
            return jsonify({"error": "Produto não encontrado"}), 404
        
        # Obter histórico de vendas do produto
        cursor.execute("""
            SELECT 
                TO_CHAR(n.data_emissao, 'DD/MM/YYYY') as data,
                n.numero as nfe,
                i.quantidade,
                i.valor_unitario,
                i.valor_total
            FROM importar_nfe_item i
            JOIN importar_nfe_nfe n ON i.nfe_id = n.id
            WHERE i.produto_id = %s
              AND n.tipo_operacao = 'saida'
            ORDER BY n.data_emissao DESC
            LIMIT 50
        """, (produto_id,))
        
        historico = []
        for row in cursor.fetchall():
            historico.append({
                'data': row['data'],
                'nfe': row['nfe'],
                'quantidade': f"{row['quantidade']:.0f}" if row['quantidade'] else '0',
                'valor_unitario': f"R$ {row['valor_unitario']:.2f}" if row['valor_unitario'] else 'R$ 0,00',
                'valor_total': f"R$ {row['valor_total']:.2f}" if row['valor_total'] else 'R$ 0,00'
            })
        
        # Preparando o resultado
        resultado = {
            'id': produto['id'],
            'nome': produto['nome'],
            'codigo': produto['codigo'],
            'ean': produto['ean'] if produto['ean'] else '',
            'ncm': produto['ncm'],
            'quantidade': f"{produto['quantidade']:.0f}" if produto['quantidade'] else '0',
            'valor_total': f"R$ {produto['valor_total']:.2f}" if produto['valor_total'] else 'R$ 0,00',
            'preco_medio': f"R$ {produto['preco_medio']:.2f}" if produto['preco_medio'] else 'R$ 0,00',
            'historico': historico
        }
        
        return jsonify(resultado)
    except Exception as e:
        app.logger.error(f"Erro na API de detalhes do produto: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/produtos/busca-ean', methods=['GET'])
def api_busca_produto_por_ean():
    """API para buscar produto por código EAN."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        ean = request.args.get('ean', '')
        
        if not ean:
            return jsonify({"error": "Parâmetro EAN é obrigatório"}), 400
        
        # Fazer a busca pelo EAN
        cursor.execute("""
            SELECT id, name, codigo, ean, ncm, unidade
            FROM importar_nfe_produto
            WHERE ean = %s
            LIMIT 1
        """, (ean,))
        
        produto = cursor.fetchone()
        
        if not produto:
            return jsonify({"error": "Produto não encontrado"}), 404
        
        # Buscar informações de preço
        cursor.execute("""
            SELECT AVG(valor_unitario) as preco_medio
            FROM importar_nfe_item
            WHERE produto_id = %s
        """, (produto['id'],))
        
        info_preco = cursor.fetchone()
        preco_medio = info_preco['preco_medio'] if info_preco and info_preco['preco_medio'] else 0
        
        resultado = {
            'id': produto['id'],
            'nome': produto['name'],
            'codigo': produto['codigo'],
            'ean': produto['ean'],
            'ncm': produto['ncm'],
            'unidade': produto['unidade'],
            'preco_medio': float(preco_medio)
        }
        
        return jsonify(resultado)
    except Exception as e:
        app.logger.error(f"Erro na API de busca por EAN: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/produtos/listar', methods=['GET'])
def api_listar_produtos():
    """API para listar produtos com paginação e filtro."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Parâmetros de paginação e filtro
        pagina = int(request.args.get('pagina', 1))
        limite = int(request.args.get('limite', 10))
        filtro = request.args.get('filtro', '')
        
        offset = (pagina - 1) * limite
        
        # Construir a consulta base
        query_base = """
            FROM importar_nfe_produto p
            WHERE 1=1
        """
        
        params = []
        
        # Adicionar condições de filtro se necessário
        if filtro:
            query_base += """
                AND (
                    p.name ILIKE %s 
                    OR p.codigo ILIKE %s 
                    OR p.ean ILIKE %s
                    OR p.ncm ILIKE %s
                )
            """
            filtro_param = f"%{filtro}%"
            params.extend([filtro_param, filtro_param, filtro_param, filtro_param])
        
        # Consulta para contar o total de registros
        cursor.execute(f"SELECT COUNT(*) as total {query_base}", params)
        total = cursor.fetchone()['total']
        
        # Consulta para buscar os produtos com paginação
        query_produtos = f"""
            SELECT 
                p.id,
                p.name as nome,
                p.codigo,
                p.ean,
                p.ncm,
                p.unidade,
                p.descricao
            {query_base}
            ORDER BY p.name
            LIMIT %s OFFSET %s
        """
        
        params.extend([limite, offset])
        cursor.execute(query_produtos, params)
        
        produtos = []
        produtos_ids = []
        
        for row in cursor.fetchall():
            produto = {
                'id': row['id'],
                'nome': row['nome'],
                'codigo': row['codigo'],
                'ean': row['ean'],
                'ncm': row['ncm'],
                'unidade': row['unidade'],
                'descricao': row['descricao'],
                'preco_medio': 0
            }
            produtos.append(produto)
            produtos_ids.append(row['id'])
        
        # Buscar preços médios para os produtos encontrados
        if produtos_ids:
            placeholders = ', '.join(['%s'] * len(produtos_ids))
            query_precos = f"""
                SELECT 
                    i.produto_id,
                    AVG(i.valor_unitario) as preco_medio
                FROM importar_nfe_item i
                WHERE i.produto_id IN ({placeholders})
                GROUP BY i.produto_id
            """
            
            cursor.execute(query_precos, produtos_ids)
            
            precos = {}
            for row in cursor.fetchall():
                precos[row['produto_id']] = float(row['preco_medio']) if row['preco_medio'] else 0
            
            # Adicionar preços aos produtos
            for produto in produtos:
                produto['preco_medio'] = precos.get(produto['id'], 0)
        
        # Buscar histórico de preços para os produtos encontrados
        for produto in produtos:
            cursor.execute("""
                SELECT 
                    TO_CHAR(n.data_emissao, 'DD/MM/YYYY') as data,
                    i.valor_unitario as preco
                FROM importar_nfe_item i
                JOIN importar_nfe_nfe n ON i.nfe_id = n.id
                WHERE i.produto_id = %s
                ORDER BY n.data_emissao DESC
                LIMIT 5
            """, (produto['id'],))
            
            historico = []
            for row in cursor.fetchall():
                historico.append({
                    'data': row['data'],
                    'preco': float(row['preco']) if row['preco'] else 0
                })
            
            produto['historico_precos'] = historico
        
        resultado = {
            'total': total,
            'pagina': pagina,
            'limite': limite,
            'paginas': (total + limite - 1) // limite,  # Cálculo do total de páginas
            'produtos': produtos
        }
        
        return jsonify(resultado)
    except Exception as e:
        app.logger.error(f"Erro na API de listagem de produtos: {str(e)}")
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