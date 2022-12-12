# -*- coding: utf-8 -*-

from odoo import models, api


class HRPayslip(models.Model):
    _inherit = 'hr.payslip'

    def confirm_multi_payslips(self):
        for record in self:
            if record.state == 'draft':
                record.action_payslip_done()

    def cancel_multi_payslips(self):
        for record in self:
            if record.state == 'done':
                record.action_payslip_cancel()
                record.action_payslip_draft()
