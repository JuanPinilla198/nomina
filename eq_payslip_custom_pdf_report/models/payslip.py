# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

from odoo import fields, models, api, _
from datetime import datetime

class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    #@api.multi
    def get_payslip_data(self, flag=None):
        result = {'income': [], 'income_total': 0.0,
                  'expense': [], 'expense_total': 0.0,
                  'net_total': 0.0,}
        for line in self.line_ids:
            code = line.salary_rule_id.rule_type
            if code in ['devengos']:
                result['income'].append(line)
                result['income_total'] += line.total
            if code in ['deducciones']:
                result['expense'].append(line)
                result['expense_total'] += line.total
            #if code in ['devengos','deducciones']:
                #result['net_total'] = line.total
        income = expense = 0
        for i, y in result.items():
            if i == 'income_total':
                income = y
            if i == 'expense_total':
                expenses = y
        result['net_total'] = income-expenses
        
        if flag:
            return result
        total_inc_line = len(result['income'])
        total_exp_line = len(result['expense'])
        total_line = max([total_inc_line, total_exp_line])
        
        final = []
        line_obj = self.env['hr.payslip.line']
        for i in range(total_line):
            tmp = {'income': line_obj,
                   'expense': line_obj}
            if total_inc_line > i:
                tmp['income'] = result['income'][i]
            if total_exp_line > i:
                tmp['expense'] = result['expense'][i]
            final.append(tmp)
        return final
    
    #Gavi
    #@api.multi
    def get_payslip_data_1(self, flag=None):
        result = {'income1': [], 'income1_total': 0.0,}
        for line in self.line_ids:
            code = line.salary_rule_id.category_id.code
            if code in ['base1','base_aux',]:
                result['income1'].append(line)
                result['income1_total'] += line.total
        if flag:
            return result
        total_inc_line_1 = len(result['income1'])
        total_line_1 = max([total_inc_line_1])
        
        final_1 = []
        line_obj = self.env['hr.payslip.line']
        for i in range(total_line_1):
            tmp = {'income1': line_obj}
            if total_inc_line_1 > i:
                tmp['income1'] = result['income1'][i]
            final_1.append(tmp)
        return final_1
    
    #gavii2
    #@api.multi
    def get_payslip_data_2(self, flag=None):
        result = {'income2': [], 'income2_total': 0.0,}
        for line in self.line_ids:
            code = line.salary_rule_id.category_id.code
            if code in ['base2',]:
                result['income2'].append(line)
                result['income2_total'] += line.total
        if flag:
            return result
        total_inc_line_2 = len(result['income2'])
        total_line_2 = max([total_inc_line_2])
        
        final_2 = []
        line_obj = self.env['hr.payslip.line']
        for i in range(total_line_2):
            tmp = {'income2': line_obj}
            if total_inc_line_2 > i:
                tmp['income2'] = result['income2'][i]
            final_2.append(tmp)
        return final_2

    #Liquidacion Nomina
    def get_payslip_data_3(self, flag=None):
        result = {'income3': [], 'income3_total': 0.0,}
        for line in self.line_ids:
            code = line.salary_rule_id.category_id.code
            if code in ['pri_liq','cesan','intcesan','vac']:
                result['income3'].append(line)
                result['income3_total'] += line.total
            if code in ['total_liq']:
                result['net_total3'] = line.total
        if flag:
            return result
        total_inc_line_3 = len(result['income3'])
        total_line_3 = max([total_inc_line_3])
        
        final_3 = []
        line_obj = self.env['hr.payslip.line']
        for i in range(total_line_3):
            tmp = {'income3': line_obj}
            if total_inc_line_3 > i:
                tmp['income3'] = result['income3'][i]
            final_3.append(tmp)
        return final_3
        

    #@api.multi
    def get_input_related_line(self, lineid):
        input_amount = ""
        if lineid:
            line_calc_str = lineid.amount_python_compute or ''
            inputs_i = line_calc_str.find('inputs')
            amount_i = line_calc_str.find('amount')
            if inputs_i and amount_i:
                split_lst = line_calc_str[inputs_i:amount_i].split('.')
                if split_lst and len(split_lst) > 1:
                    code = split_lst[1]
                    input_line_ids = self.input_line_ids.filtered(lambda l: l.code == code)
                    if input_line_ids:
                        input_amount = input_line_ids[-1].amount
        return input_amount


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
