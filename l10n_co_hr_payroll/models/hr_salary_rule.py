# -*- coding: utf-8 -*-

from odoo import fields, models, _


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    rule_type = fields.Selection([('devengos', 'Devengos'), ('deducciones', 'Deducciones'),('none', 'No aplica')], string="Tipo de afectación")
