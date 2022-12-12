# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    diff_days = fields.Integer(compute='_get_diff_dates')
    
    def _get_diff_dates(self):
        for slip in self:
            start_date = slip.contract_id.date_start
            end_date = slip.date_to
            slip.diff_days = (end_date - start_date).days

class HrPayslip(models.Model):
    _inherit = 'hr.contract'
    
    def _get_vacations(self, payslip, code_ac):
        _logger.info("."*300)
        payslip_ids = self.env["hr.payslip"].search([('vacation_paid', '=', True), ('employee_id', '=', payslip.employee_id)], limit=1)
        amount = 0
        lines = []
        
        _logger.info(payslip_ids)
        if len(payslip_ids) == 0:
            payslip_ids = self.env["hr.payslip"].search([('employee_id', '=', payslip.employee_id)])
            for slip in payslip_ids:
                for line in slip.line_ids.filtered(lambda line: line.category_id.code == code_ac):
                    lines.append(line.amount)
            amount = sum(lines)
        else:
            payslip_ids = self.env["hr.payslip"].search([('employee_id', '=', payslip.employee_id), ('id', '<=', payslip_ids.id)])
            for slip in payslip_ids:
                for line in slip.line_ids.filtered(lambda line: line.category_id.code == code_ac):
                    lines.append(line.amount)
            amount = sum(lines)

        return amount

    def _get_provisional(self, payslip, code, end=False):
        amount = 0        
        date_start = fields.Date.from_string(payslip.date_from)
        sd_s1 = date_start.replace(month=1, day=1)
        ed_s1 = date_start.replace(month=6, day=30)
        sd_s2 = date_start.replace(month=7, day=1)
        ed_s2 = date_start.replace(month=12, day=31)
        domain = []
        lines = []
        if date_start >= sd_s1 and  date_start <= ed_s1:
            _logger.info("REGLA 1: primer semestre")
            domain = [('date_from', '>=', sd_s1), ('date_from', '<=', ed_s1), ('employee_id', '=', payslip.employee_id)]
        if date_start >= sd_s2 and  date_start <= ed_s2:
            _logger.info("REGLA 2: segundo semestre")
            domain = [('date_from', '>=', sd_s2), ('date_from', '<=', ed_s2), ('employee_id', '=', payslip.employee_id)]
        payslip_ids = self.env['hr.payslip'].search(domain)
        for slip in payslip_ids:
            for line in slip.line_ids.filtered(lambda line: line.category_id.code == code):
                lines.append(line.amount)
        amount = end and (sum(lines)/len(lines)) or sum(lines)
        return amount


    def _get_last_month(self, payslip, codes):
        amount = 0
        date_start = fields.Date.from_string(payslip.date_from)
        start_date = date_start.replace(month=date_start.month and date_start.month-1 or 12, day=1)
        end_date = date_start.replace(month=date_start.month, day=1) - timedelta(days = 1)
        domain = [('date_from', '>=', start_date), ('date_from', '<=', end_date), ('employee_id', '=', payslip.employee_id)]
        payslip_ids = self.env['hr.payslip'].search(domain)
        for slip in payslip_ids:
            for line in slip.line_ids.filtered(lambda line: line.category_id.code in codes):
                amount += line.amount
        return amount
