# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class payroll_payslip_temp_id(models.AbstractModel):
    _name = 'report.bi_payroll_construction_contracting.id_payroll_payslip'
    _description = "Report Payroll Payslips"

    def get_lines_by_contribution_register(self, payslip_lines):
        result = {}
        res = {}
        for line in payslip_lines:
            result.setdefault(line.slip_id.id, {})
        for payslip_id, lines_dict in result.items():
            res.setdefault(payslip_id, [])
            for register, lines in lines_dict.items():
                res[payslip_id].append({
                    'register_name': register.name,
                    'total': sum(lines.mapped('total')),
                })
                for line in lines:
                    res[payslip_id].append({
                        'name': line.name,
                        'code': line.code,
                        'quantity': line.quantity,
                        'total': line.total,
                    })

        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        payslips = self.env['hr.payslip'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,
            'get_lines_by_contribution_register': self.get_lines_by_contribution_register(payslips.mapped('line_ids').filtered(lambda r: r.appears_on_payslip)),
        }
