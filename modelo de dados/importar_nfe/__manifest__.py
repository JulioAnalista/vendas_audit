# -*- coding: utf-8 -*-
{
    'name': "Importar NFe",

    'summary': "Módulo para importação de Notas Fiscais Eletrônicas (NFe)",

    'description': """
Módulo para Importação de Notas Fiscais Eletrônicas (NFe)
==========================================================

Este módulo permite a importação de arquivos XML de Notas Fiscais Eletrônicas (NFe)
para o sistema Odoo, facilitando a integração com o sistema fiscal brasileiro.

Funcionalidades:
- Importação de arquivos XML de NFe
- Visualização e gerenciamento das notas importadas
- Integração com outros módulos do sistema
    """,

    'author': "Bumerangue Sistemas",
    'website': "https://www.bumeranguesistemas.com.br",

    'category': 'Accounting',
    'version': '1.0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'web', 'mail'],

    # always loaded
    'data': [
        'security/importar_nfe_groups.xml',
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/views.xml',
        'views/server_actions.xml',
        'views/menu_items.xml',
        'data/sequence.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    
    # Assets
    'assets': {
        'web.assets_backend': [
            'importar_nfe/static/src/css/pasta_widget.css',
            'importar_nfe/static/src/xml/pasta_widget.xml',
            'importar_nfe/static/src/js/pasta_widget.js',
        ],
    },
    
    'installable': True,
    'application': True,
    'auto_install': False,
}
