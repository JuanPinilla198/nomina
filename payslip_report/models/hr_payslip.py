# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    vacation_paid = fields.Boolean("Vacaciones")
    analytic_account_id = fields.Many2one('account.analytic.account', related='contract_id.analytic_account_id', store=True)

    parent_analytic_id = fields.Many2one('account.analytic.account', store=True)

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'
    _order = 'salary_rule_id'
