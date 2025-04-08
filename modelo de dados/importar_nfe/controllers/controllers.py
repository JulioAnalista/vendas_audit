# -*- coding: utf-8 -*-
# from odoo import http


# class ImportarNfe(http.Controller):
#     @http.route('/importar_nfe/importar_nfe', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/importar_nfe/importar_nfe/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('importar_nfe.listing', {
#             'root': '/importar_nfe/importar_nfe',
#             'objects': http.request.env['importar_nfe.importar_nfe'].search([]),
#         })

#     @http.route('/importar_nfe/importar_nfe/objects/<model("importar_nfe.importar_nfe"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('importar_nfe.object', {
#             'object': obj
#         })

