# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo import models, fields, api, _


class InheritHrContract(models.Model):
    _inherit = "hr.contract"

    work_rate_many_ids = fields.One2many("timesheet.work.line","work_id")


class InheritTimesheet(models.Model):
    _inherit = "account.analytic.line"

    task = fields.Many2one("project.task",string="Task")
    work_type_id = fields.Many2one("timesheet.work.type",string="Work Type")
    start_time = fields.Float("Start Time")
    end_time = fields.Float("End Time")
    quantity = fields.Float("Quantity")
    is_billable = fields.Boolean("Is Billable")
    is_paid = fields.Boolean("Is Paid")
    is_payroll_paid = fields.Boolean("Is Payroll Paid")

    line_payslip = fields.Many2one("hr.payslip")

class inheritTimesheet(models.Model):
    _inherit = "hr_timesheet_sheet.sheet"

    payslip_count = fields.Integer(compute='_payslip_count',string="Sheet")

    def _payslip_count(self):
        for s_id in self:   
            support_ids = self.env['hr.payslip'].search([("employee_id",'=',self.employee_id.id)])
            s_id.payslip_count = len(support_ids)
        return
        
    def butoon_count_payslip(self):
        
        self.ensure_one()
        return {
            'name': 'Sheet Count',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'hr.payslip',
            'domain': [("employee_id",'=',self.employee_id.id)],
        }

class inheritPayslip(models.Model):
    _inherit = "hr.payslip"

    timesheet_count = fields.Integer(compute='_timesheet_count',string="Sheet")
    work_type_ids = fields.One2many("timesheet.work.line","payslip_many_id",readonly=True,store=True)
    check_compute_sheet = fields.Boolean("Check boolean",default=False)
    link_analytic = fields.One2many("account.analytic.line","line_payslip",string="Link")
    change_value = fields.Boolean("Change state",default=False)


    def _timesheet_count(self):
        if self.check_compute_sheet == True:
            for s_id in self:   
                support_ids = self.env['hr_timesheet_sheet.sheet'].search([("employee_id",'=',self.employee_id.id),('date_from','>=',self.date_from),('date_to','<=',self.date_to)])
                s_id.timesheet_count = len(support_ids)
            return
        else:
            self.timesheet_count = False


        
    def butoon_timesheet(self):
        if self.check_compute_sheet == True:
            self.ensure_one()
            return {
                'name': 'Sheet Count',
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'hr_timesheet_sheet.sheet',
                'domain': [("employee_id",'=',self.employee_id.id),('date_from','>=',self.date_from),('date_to','<=',self.date_to)],
            }   

    count_timesheet_line = fields.Integer(compute='_count_timesheet_lines',string="Timesheet lines")
    
    def _count_timesheet_lines(self):
        if self.check_compute_sheet == True:
            for s_id in self:   
                support_ids = self.env['account.analytic.line'].search([("id","in",self.link_analytic.ids)])
                s_id.count_timesheet_line = len(support_ids)
            return
        else:
            self.count_timesheet_line = False

    def butoon_lines(self):
        if self.check_compute_sheet == True:
            self.ensure_one()
            
            return {
                'name': 'Timesheet Count',
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'account.analytic.line',
                'domain': [("id","in",self.link_analytic.ids)],
            }

    def action_payslip_done(self):
        res = super(inheritPayslip,self).action_payslip_done()
        self.change_value=True
        self.state_check()
        return res

    def state_check(self):
        for i in self.link_analytic:
            i.is_payroll_paid = True


    def compute_sheet(self):
        for payslip in self:
            if payslip.check_compute_sheet == False :
                list_work = []
                dict_work = {}
                support_ids = self.env['hr_timesheet_sheet.sheet'].search([('employee_id','=',payslip.employee_id.id)])
                start = datetime.strptime(str(payslip.date_from), "%Y-%m-%d")
                end = datetime.strptime(str(payslip.date_to), "%Y-%m-%d")
                date_array = (start + timedelta(days=x) for x in range(0, (end-start).days + 1))
                
                date_list = []
                for date_object in date_array:
                    date_list.append(date_object.strftime("%Y-%m-%d"))

                for support in support_ids:
                    if str(support.date_from) in date_list and str(support.date_to) in date_list:
                        payslip.update({'link_analytic' : [(6,0,support.timesheet_ids.ids)],})

                for i in payslip.link_analytic:
                    if i.work_type_id not in dict_work :
                        dict_work[i.work_type_id] = i.unit_amount
                    else:
                        dict_work[i.work_type_id] = dict_work[i.work_type_id] + i.unit_amount       
                    if i.work_type_id not in list_work:
                        list_work.append(i.work_type_id)
                
                for k in dict_work:
                    payslip.work_type_ids = [(0,0,{'work_type_id':k.id,'hours':dict_work.get(k),})]

                payslip.check_compute_sheet = True
        return super(inheritPayslip,self).compute_sheet()


class TimesheetWorkLine(models.Model):
    _name="timesheet.work.line"
    _description = "Timesheet Work Line"

    work_type_id = fields.Many2one('timesheet.work.type','Work Type')
    rate = fields.Float("Rate")
    hours = fields.Float("Hours")
    work_id = fields.Many2one('hr.contract','Work')
    payslip_many_id = fields.Many2one("hr.payslip")


class Hr_employee_inherit_regular(models.Model):
    _inherit = "hr.employee"

    def get_work_salary(self,str,payslip):
        result = 0.0
        payslip_hours = self.env['hr.payslip'].search([('id','=',payslip)])
        work_rule = self.env['hr.salary.rule'].search([('code','=',str)])
       
        for i in payslip_hours:
            for k in i.work_type_ids:
                for a in i.contract_id.work_rate_many_ids:
                    if str == k.work_type_id.work_code:
                        if str == work_rule.code:
                            if a.work_type_id == k.work_type_id:
                                result = a.rate * k.hours
                                
        return result