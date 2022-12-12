# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.contract'

    contract_type = fields.Selection(
        selection=[
            ('1', 'Termino fijo'),
            ('2', 'Termino indefinido'),
            ('3', 'Obra o Labor'),
            ('4', 'Aprendizaje'),
            ('5', 'Practicas o Pasantias'),
        ], string="Tipo de Contrato",
        required=True
        )
    
    phase = fields.Selection(
        selection=[
            ('teaching_phase', 'Fase lectiva (50% SMMLV)'),
            ('practical_phase', 'Fase practica (75% SMMLV)'),
            ('practical_phase_100', 'Fase practica (100% SMMLV)'),
        ], string="Fase de aprendizaje",
        )
    
    payroll_period = fields.Selection(
        selection=[
            ('1', 'Semanal'),
            ('2', 'Decenal'),
            ('3', 'Catorcenal'),
            ('4', 'Quincenal'),
            ('5', 'Mensual'),
            ('6', 'Otro'),
        ], string='Periodo Nómina', required=True
    )