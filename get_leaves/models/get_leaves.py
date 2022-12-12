# -*- coding: utf-8 -*-
from ast import Num
from re import search
from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):

    _inherit = 'hr.payslip'

    leaves_ids = fields.One2many('hr.leave', 'payslip_id')
    overtime_ids = fields.One2many('overtime.request', 'payslip_id')
    total_payslip = fields.Float('Total')

    def _get_inputs(self, line, date_from_payslip, date_to_payslip):

        for tupla in line:
            for value in tupla[2].values():
                if value == "1001" or value == "1002" or value == "1003" or value == "1004" or value == "1005" or value == "1006" or value == "1010": 
                    leave_obj = self.env['hr.leave'].search([('employee_id', '=', tupla[2]["employee_id"]),
                                                 ('state', '=', 'validate'),
                                                 '&','|',('request_date_from', '>=', date_from_payslip),
                                                         ('request_date_to', '>=', date_from_payslip),
                                                         '|',('request_date_from', '<=', date_to_payslip),
                                                             ('request_date_to', '<=', date_to_payslip),
                                                 ])
                    lista = []
                    for data_leave in leave_obj:
                        lista.append(data_leave.id)
                    lines = [(4, line)
                        for line in lista]
                    return lines

    def _calculate_leaves(self,num_of_days, codes):
        if num_of_days > 2:
            pro_sal_mes_ant = self._get_last_month_leave(codes)
            if pro_sal_mes_ant != 0:
                if ((pro_sal_mes_ant/30))*(2/3) < ((self.employee_id.company.salario_minimo/30))*(2/3):
                    pago = (self.employee_id.company.salario_minimo / 30)*num_of_days
                    return pago
                else:
                    pago = ((pro_sal_mes_ant/30)*num_of_days)*(2/3)
                    return pago
            elif pro_sal_mes_ant == 0:
                pago = ((self.contract_id.wage/30)*num_of_days)*(2/3)
                if pago/num_of_days < (self.employee_id.company.salario_minimo / 30)*(2/3) :
                    return (self.employee_id.company.salario_minimo / 30)*num_of_days
                else:
                    return pago
        elif num_of_days >= 1 and num_of_days <=2:
            for line_values in self.line_ids.filtered(lambda l: l.salary_rule_id.rule_type == 'devengos'):
                if line_values.code == "1005":
                    return line_values.total

    def calculate_overtime(self, num_of_hours, percent=0):

        salario = self.contract_id.wage
        num_horas = num_of_hours
        porcentaje = percent
        _pago = round((salario/30/8)*num_horas*porcentaje, 0)

        return _pago
    
    def _get_last_month_leave(self, codes):
        amount = 0
        date_start = fields.Date.from_string(self.date_from)
        start_date = date_start.replace(month=date_start.month and date_start.month-1 or 12, day=1)
        end_date = date_start.replace(month=date_start.month, day=1) - timedelta(days = 1)
        domain = [('date_from', '>=', start_date), ('date_from', '<=', end_date), ('employee_id', '=', self.employee_id.id)]
        payslip_ids = self.search(domain)
        for slip in payslip_ids:
            for line in slip.line_ids.filtered(lambda line: line.category_id.code in codes):
                amount += line.amount
        return amount

    #@api.multi
    def compute_sheet(self):        
        for payslip in self:
            date_f = payslip.date_from
            date_t = payslip.date_to
            date_from_payslip = payslip.date_from
            date_to_payslip = payslip.date_to
            # number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            # set the list of contract for which the rules have to be applied
            # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
            contract_ids = payslip.contract_id.ids or \
                self.get_contract(payslip.employee_id,
                                  payslip.date_from, payslip.date_to)
            lines = [(0, 0, line)
                     for line in self._get_payslip_lines(contract_ids, payslip.id)]
            overtime = self.get_overtime(lines, date_f, date_t)
            leaves = self._get_inputs(lines, date_from_payslip, date_to_payslip)
            payslip.write({'line_ids': lines,'overtime_ids' : overtime})
        
        for lines in self.line_ids.filtered(lambda l: l.salary_rule_id.code == '1405'):
            self.total_payslip = lines.total

        # self._get_inputs()
        #res = super(HrPayslip, self).compute_sheet()
        return True

    @api.onchange('employee_id', 'date_from', 'date_to')
    def get_leaves(self):
        leave_obj = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id),
                                                 ('state', '=', 'validate'),
                                                 '&','|',('request_date_from', '>=', self.date_from),
                                                         ('request_date_to', '>=', self.date_from),
                                                         '|',('request_date_from', '<=', self.date_to),
                                                             ('request_date_to', '<=', self.date_to),
                                                 ])
        lista = []
        print(leave_obj, "este es el leave obje-----------------------------------------------------------")
        for data_leave in leave_obj:
            lista.append(data_leave.id)
        lines = [(4, line)
            for line in lista]
        self.write({'leaves_ids' : lines})

    def get_overtime(self, line, date_f, date_t):
        for tupla in line:
            for key, value in tupla[2].items():
                if value == "1107-1" or value == "1107-2" or value == "1107-3" or value == "1107-4" or value == "1107-5" or value == "1107-6" or value == "1107-7" or value == "1207-1" or value == "1207-2" or value == "1207-3" or value == "1207-4" or value == "1207-5" or value == "1207-6" or value == "1207-7" or value == "1307-1" or value == "1307-2" or value == "1307-3" or value == "1307-4" or value == "1307-5" or value == "1307-6" or value == "1307-7":
                    overtime_obj = self.env['overtime.request'].search(
                        [('state', '=', 'done'), 
                         ('employee_id', '=', tupla[2]["employee_id"]),
                         ('start_date', '>=', date_f),
                         ('end_date', '<=', date_t)])
                    lista = []
                    for data_overtime in overtime_obj:
                        lista.append(data_overtime.id)
                    lines = [(4, line)
                        for line in lista]
                    return lines
    
class PayslipLeave(models.Model):

    _inherit = 'hr.leave'

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='payslip'
    )
    computed = fields.Boolean(string="Calculada")

    type_leave_disease_dian = fields.Selection(selection=[('1', 'Común'),
                                                          ('2', 'Profesional'),
                                                          ('3', 'Laboral')],
                                               string="Tipo de Incapacidad")
    pago = fields.Float(string="Pago")
    include_sunday = fields.Boolean(string="Incluir domingo")
    eps_100 = fields.Boolean(string="EPS 100%")
    check_eps = fields.Boolean(string="EPS 100%")
    check_no_remunerado = fields.Boolean(string="Incluir domingo")
    field_bol = fields.Boolean()
    @api.onchange('holiday_status_id')
    def check_sunday(self):
        if self.holiday_status_id.name == 'AUSENCIA_NO_REMUNERADO':
            self.check_no_remunerado = True
        else:
            self.check_no_remunerado = False

    @api.onchange('holiday_status_id')
    def check_eps100(self):
        if self.holiday_status_id.name == 'EPS':
            self.check_eps = True
        else:
            self.check_eps = False
class PayslipOvertime(models.Model):
    _inherit = 'overtime.request'

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='payslip',
    )

    pago = fields.Float(string="Pago")

class HrContract(models.Model):

    _inherit = 'hr.contract'

    # Esta función Valida si se Paga Incapcidad EPS o si Se paga Incapacidad Empleador o Ambas, 
    # Y tambien entrega los montos del pago de cada una.
    def execute_rules_leave_EPS(self, payslip):
        number = count = 0
        date_from_payslip = payslip.date_from
        date_to_payslip = payslip.date_to
        leave_obj = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id),
                                                 ('state', '=', 'validate'),
                                                 ('holiday_status_id', '=', "EPS"),
                                                 '&','|',('request_date_from', '>=', date_from_payslip),
                                                         ('request_date_to', '>=', date_from_payslip),
                                                         '|',('request_date_from', '<=', date_to_payslip),
                                                             ('request_date_to', '<=', date_to_payslip),
                                                 ])              
        for data_leave in leave_obj:
            print("Entra for")
            count += 1
        print(count)
        if count > 1:
            print("Entra if1")
            in_1 = in_2 = False
            value_1 = value_2 = 0
            for data_leave in leave_obj:
                print(data_leave, "Entra for1")
                get_date_from = data_leave.request_date_from
                get_date_to = data_leave.request_date_to
                num_of_days = data_leave.number_of_days_display
                if get_date_from  < date_from_payslip:
                    print("Entra if <")
                    diff =  abs((date_from_payslip - get_date_from).days)
                    if diff >= 2:  
                        in_2 = True
                        number = num_of_days - diff 
                        value_2 += number
                    elif diff == 1:
                        in_1 = in_2 = True
                        number = num_of_days - diff 
                        value_2 += number
                        value_1 += 1
                if get_date_from  >= date_from_payslip and data_leave.holiday_status_id.name == "EPS":
                    print("Entra if =>")
                    print(date_to_payslip, get_date_to)
                    if date_to_payslip >= get_date_to:
                        print("Entra if =>2", in_1)
                        number = num_of_days
                        if in_1 == False: 
                            print("estas enrando???", number)
                            if number <= 2.0:
                                in_1 = True
                                value_1 += number
                            elif number > 2.0:
                                print("dberias estar entrando")
                                in_1 = in_2 = True
                                value_1 += 2
                                number = number - 2
                                value_2 += number
                        else:
                            print("estas entrando al else")
                            print(number)
                            if number <= 2:
                                value_1 += number
                            elif number > 2:

                                in_1 = in_2 = True
                                value_1 += 2
                                value_2 += number - 2
                        print(in_1, value_1, in_2, value_2, "$$$$$$$$$$$$2")
                if get_date_from  >= date_from_payslip:
                    print("Entra if >=")
                    if date_to_payslip < get_date_to:
                        diff =  date_to_payslip - get_date_from
                        diff = diff.days + 1
                        if diff <= 2:
                            in_1 = True
                            value_1 += diff
                        elif diff > 2:
                            in_1 = in_2 = True
                            value_1 += 2
                            value_2 += diff - 2
            if in_1:
                print(in_1, value_1, in_2, value_2, "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$4")
                return (in_1, value_1, in_2, value_2)
        for data_leave in leave_obj:
            print("entras en el for 2")
            print(data_leave.request_date_from, data_leave.request_date_to, data_leave.number_of_days_display)
            get_date_from = data_leave.request_date_from
            get_date_to = data_leave.request_date_to
            num_of_days = data_leave.number_of_days_display
            

            if get_date_from >= date_from_payslip:
                if get_date_to <= date_to_payslip:
                    print("entra en el for del 1---------------------")
                    diff = num_of_days
                    if diff > 2:
                        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$5")
                        return (True, 2, True, diff - 2)
                    elif diff <= 2:
                        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$6")
                        return (True, diff, False, 0)
            if get_date_from  >= date_from_payslip:
                if date_to_payslip < get_date_to:
                    diff =  date_to_payslip - get_date_from
                    diff = diff.days + 1
                    if diff <= 2:
                        return (True, diff, False, 0)
                    if diff > 2:
                        print(in_1, value_1, in_2, value_2, "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$7")
                        return (True, 2, True, diff - 2)
            if get_date_from  < date_from_payslip:
                diff =  abs((date_from_payslip - get_date_from).days)
                if diff > 2:  
                    number = num_of_days  - diff  
                    print(in_1, value_1, in_2, value_2, "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$8")
                    return (False, 0, True, number)
        return (False, 0, False, 0)

    def worked_days_last_month(self, payslip):
        date_start = fields.Date.from_string(payslip.date_from)
        start_date = date_start.replace(month=date_start.month and date_start.month-1 or 12, day=1)
        end_date = date_start.replace(month=date_start.month, day=1) - timedelta(days = 1)
        domain = [('date_from', '>=', start_date), ('date_from', '<=', end_date), ('employee_id', '=', payslip.employee_id)]
        payslip_ids = self.env['hr.payslip'].search(domain)
        days = 0
        for payslip in payslip_ids:
            for worked_days in payslip.worked_days_line_ids:
                if worked_days.code == "WORK100":
                    days += worked_days.number_of_days
        return days
        #_logger.info("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        #_logger.info(payslip_ids)