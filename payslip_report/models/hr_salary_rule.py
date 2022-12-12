# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _order = 'sequence'

    dont_show_in_report = fields.Boolean(string='No mostrar en informe')
