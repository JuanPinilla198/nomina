# -*- coding: utf-8 -*-

from odoo import fields, models, api, SUPERUSER_ID, _
import json
import logging
import http.client
from datetime import datetime, date, time, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse


_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    wispro_sincronize = fields.Boolean("Sincronize Wispro", default=False, related="company_id.wispro_sincronize", readonly=False)
    api_token_wispro = fields.Char("API token Wispro", related="company_id.api_token_wispro", readonly=False)

    def launch_wizard(self):
        search_wizard_view = self.env.ref('payslip_report.ir_ui_wispro_api_consume_wizard_view')
        # print(self._context)
        token = self.api_token_wispro
        # wispro_response = self.wispro_response(token)

        wispro_response = self.wispro_invoice_list(token)

        return {
            'name': _('Wispro API Consume: Lists Ivoices'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wispro.api.consume',
            'views': [(search_wizard_view.id, 'form')],
            'view_id': search_wizard_view.id,
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_wispro_response': wispro_response,
            },
        }
    
    def wispro_invoice_list(self,token):
        conn = http.client.HTTPSConnection("www.cloud.wispro.co")
        payload = ''
        headers = {
          'Authorization': token
        }
        conn.request("GET", "/api/v1/invoicing/invoices", payload, headers)
        res = conn.getresponse()
        data = res.read()
        # print(data.decode("utf-8"))
        response = data.decode("utf-8")
        return response



class ResCompany(models.Model):
    _inherit = 'res.company'


    wispro_sincronize = fields.Boolean("Sincronize Wispro")
    api_token_wispro = fields.Char("API token Wispro", )


    def _process_data(self, data_dict, model, company):
        if model == 'res.partner':
            for record in data_dict:
                res_partner = self.env['res.partner']
                if res_partner.search_count(['|',('wispro_partner_id', '=', record.get('id')), ('name', '=', record.get('name'))]) == 0:
                    vals = {
                            'wispro_partner_id': record.get('id'),
                            'name': record.get('name'),
                            'street': record.get('address'),
                            'city': record.get('city'),
                            # 'service_provider': 'wispro',
                            #'state': record.get('state'),
                            'phone': record.get('phone'),
                            'mobile': record.get('phone_mobile'),
                            'email': record.get('email'),
                            'function': record.get('national_identification_number'),

                            }
                    self.env[model].create(vals)

        if model == 'product.template':
            for record in data_dict:
                if self.env['product.template'].search_count([('wispro_subscription_template_id', '=', record.get('id'))]) == 0:
                    subscription_tmpl = self.env['sale.subscription.template'].search([('recurring_interval', '=', record.get('frequency_in_months')), ('recurring_rule_type', '=', 'monthly')])
                    vals = {
                        'wispro_subscription_template_id': record.get('id'),
                        'name': record.get('name'),
                        'type': 'service',
                        'company_id': company.id,
                        'list_price': record.get('price'),
                        'recurring_invoice': True,
                        'subscription_template_id': subscription_tmpl.id,
                        'description': '\n'.join(x + ':' + str(y) for x, y in record.items()),
                    }
                    if len(subscription_tmpl) > 0:
                        self.env[model].create(vals)

        if model == 'sale.subscription':
            # print(data_dict)
            for record in data_dict:
                if self.env['sale.subscription'].search_count([('wispro_subscription_id', '=', record.get('id'))]) == 0:
                    product_id = self.env['product.product'].search([('wispro_subscription_template_id', '=', record.get('plan_id'))])
                    print(product_id)
                    partner_id = self.env['res.partner'].search([('wispro_partner_id', '=', record.get('client_id'))])
                    print(partner_id)
                    vals = {
                        'company_id':company.id,
                        'wispro_subscription_id': record.get('id'),
                        # 'service_provider': 'wispro',
                        'recurring_invoice_line_ids': [(0, 0,  { 'product_id': product_id.id, 'uom_id': product_id.uom_id.id, 'price_unit': product_id.list_price, })],
                        'template_id': product_id.subscription_template_id.id,
                        'partner_id': partner_id.id,
                        'stage_id':  2 if record.get('state') == 'enabled' else 4,
                        'date_start': record.get('start_date'),
                    }
                    if len(product_id) > 0 and len(partner_id):
                        self.env[model].create(vals)

    def _process_invoices(self, data_dict, model):
        for record in data_dict:
            date_from = datetime.strptime(record.get('from'), "%Y-%m-%d").date()
            date_to = datetime.strptime(record.get('to'), "%Y-%m-%d").date()
            invoice_id = self.env['account.move'].search([('start_period', '=', date_from), ('end_period', '=', date_to), ("partner_id.name", '=', record.get('client_name'))])
            sale_subscription = self.env['sale.subscription'].search([('partner_id', '=', invoice_id.partner_id.id),("wispro_subscription_id", '=', record.get('contract_id'))]) 
            if sale_subscription:
                invoice_id.write({'wispro_invoice_id': record.get('id')})


    def _get_wispro_request(self, url, method='GET', model=''):
        conn = http.client.HTTPSConnection("www.cloud.wispro.co")
        for company in self.search([('api_token_wispro', '!=', False)]):
            token = company.api_token_wispro
            _logger.info(company.api_token_wispro)
            headers = {
            'Authorization': token
            }

            start_date = datetime.today().replace(day=1)
            end_date = datetime.today().replace(month=datetime.today().month+1, day=1)
            end_date = end_date - timedelta(days=1)

            if model == 'account.move':
                url = url + '?created_at_after=' + start_date.strftime('%Y-%m-%dT%H:%M:%S') + '&created_at_before=' + end_date.strftime('%Y-%m-%dT%H:%M:%S')

            conn.request(method, url, {} , headers)
            res = conn.getresponse()

            data = res.read()
            response = data.decode("utf-8")
            meta = json.loads(response).get("meta")

            pagination = meta.get('pagination').get('total_pages')

            _logger.info("/"*90)
            data_dict = json.loads(response).get("data") #lista de diccionarios

            if model == 'account.move':
                self._process_invoices(data_dict, model)
            else:           
                self._process_data(data_dict, model, company)

            if pagination >2:
                for page in range(2,pagination+1):
                    if model == 'account.move':
                        url_tmp = url + "&page=" + str(page)
                    else:
                        url_tmp = url + "?page=" + str(page)

                    conn.request(method, url_tmp, {} , headers)
                    res = conn.getresponse()

                    data = res.read()
                    response = data.decode("utf-8")

                    _logger.info("*"*90)
                    data_dict = json.loads(response).get("data") #lista de diccionarios
                
                    if model == 'account.move':
                        self._process_invoices(data_dict, model)
                    else:           
                        self._process_data(data_dict, model, company)
