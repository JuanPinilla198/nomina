# -*- coding: utf-8 -*-

from odoo import fields, models

class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    tipo_nomina = fields.Selection(
        selection=[
            ('102', 'Nómina Individual'),
            ('103', 'Nómina Individual de Ajuste'),
        ], string='Tipo de Nómina', default='102', required=True)