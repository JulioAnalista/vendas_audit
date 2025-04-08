# -*- coding: utf-8 -*-
{
    'name': 'Visualização de Vendas e Produtos',
    'version': '1.0',
    'summary': 'Visualizar vendas e produtos por período',
    'description': """
        Módulo para visualização das vendas e produtos vendidos por período.
        Permite análise de volume de vendas, produtos mais vendidos e outras métricas relacionadas.
    """,
    'category': 'Sales',
    'author': 'NCM Audit',
    'website': '',
    'depends': [
        'base',
        'web',
        'importar_nfe',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/visualizacao_vendas_views.xml',
        'views/vendas_dashboard_views.xml',
        'views/menu_views.xml',
        'reports/vendas_report.xml',
    ],
    'qweb': [
        'static/src/xml/dashboard_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'visualizacao_vendas/static/src/js/dashboard.js',
            'visualizacao_vendas/static/src/css/dashboard.css',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
} 