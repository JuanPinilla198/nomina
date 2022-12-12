# -*- coding: utf-8 -*-
from odoo import http

# class ProvAcumulate(http.Controller):
#     @http.route('/prov_acumulate/prov_acumulate/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/prov_acumulate/prov_acumulate/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('prov_acumulate.listing', {
#             'root': '/prov_acumulate/prov_acumulate',
#             'objects': http.request.env['prov_acumulate.prov_acumulate'].search([]),
#         })

#     @http.route('/prov_acumulate/prov_acumulate/objects/<model("prov_acumulate.prov_acumulate"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('prov_acumulate.object', {
#             'object': obj
#         })