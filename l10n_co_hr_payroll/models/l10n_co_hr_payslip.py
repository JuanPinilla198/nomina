# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    #Campos para Calcular Prima Manual
    is_prima = fields.Boolean(string="Incluir Prima de Servicios")
    no_prima_days = fields.Integer(string="Dias Trabajados")
    #Campos para Calcular liquidación Manual
    is_liquid = fields.Boolean(string="Calcular Liquidación")
    no_prima_liq = fields.Integer(string="Dias Trabajados (Prima)")
    no_cesan_liq = fields.Integer(string="Dias Trabajados (Cesantias)")
    no_vacac_liq = fields.Integer(string="Dias Trabajados (Vacaciones)")
    pagar_FSP = fields.Binary(string="Pagar FSP")
    pagar_fsp = fields.Boolean(string="Pagar FSP")
