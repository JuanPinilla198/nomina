# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    software_identification_code_payroll = fields.Char(string="Código de identificación del software nómina", required=True, default="")
    identificador_set_pruebas_payroll = fields.Char(string = 'Identificador del SET de pruebas nómina', required = True )
    software_pin_payroll = fields.Char(string="PIN del software nómina", required=True, default="")
    salario_minimo = fields.Float("Salario Minimo", default='1000000')
    salario_uvt = fields.Float("Salario UVT", default='38004')
    aux_transporte = fields.Float("Auxilio de transporte", default='117172')
    cantidad_salarios_maximo = fields.Integer("Cantidad de salarios máximo")
    max_salary_integral = fields.Char("Salario Integral", compute='_calculate_salary_integral')
    rule_id = fields.Many2one('hr.salary.rule', 'Regla')
    is_test = fields.Selection([('1', 'Producción'), ('2', 'Habilitación')])


    @api.depends('salario_minimo', 'cantidad_salarios_maximo')
    def _calculate_salary_integral(self):
    	for record in self:
    		record.max_salary_integral = record.salario_minimo * record.cantidad_salarios_maximo

class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    l10n_co_edi_code = fields.Char()