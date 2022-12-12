# -*- coding: utf-8 -*-
from odoo import http

# class AccountExtra(http.Controller):
#     @http.route('/account_extra/account_extra/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/account_extra/account_extra/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('account_extra.listing', {
#             'root': '/account_extra/account_extra',
#             'objects': http.request.env['account_extra.account_extra'].search([]),
#         })

#     @http.route('/account_extra/account_extra/objects/<model("account_extra.account_extra"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('account_extra.object', {
#             'object': obj
#         })