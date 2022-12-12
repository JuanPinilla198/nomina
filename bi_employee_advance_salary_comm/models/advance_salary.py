    # -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api,_
from odoo.exceptions import UserError


class ChartfAccount(models.Model):
    _name = 'advance.salary'
    _rec_name = 'employee_id'


    name = fields.Char(string="Name")
    employee_id = fields.Many2one('hr.employee',string="Employee")
    req_date = fields.Datetime(string="Request Date",default=fields.datetime.now(),readonly=True)
    req_amount = fields.Monetary(strring="Request Amount")
    currency_id = fields.Many2one('res.currency',string="Currency",default = lambda self : self.env.user.company_id.currency_id.id,readonly=True)

    department_id = fields.Many2one('hr.department',string="Department")
    job_id = fields.Many2one('hr.job',string="Job Position",required=True)
    department_manager_id = fields.Many2one('hr.employee',string="Manager")
    req_user_id = fields.Many2one('res.users',string="Request User")


    confirm_date = fields.Datetime(string="Confirm Date")
    approve_date_department = fields.Datetime(string="Approve Date(Department)")
    approve_date_hr = fields.Datetime(string="Approve Date(HR)")
    approve_date_director = fields.Datetime(string="Approve Date(Director)")
    paid_date = fields.Datetime(string="Paid Date")

    confirm_by_id = fields.Many2one('res.users',string="Confirm By")
    depet_manager_approve_by_id = fields.Many2one('res.users',string="Department Approve By")
    hr_manager_id = fields.Many2one('res.users',string="HR Manager")
    director_id = fields.Many2one('res.users',string="Director")
    paid_by_id = fields.Many2one('res.users',string="Paid By")
    company_id = fields.Many2one('res.company',string="Company")

    partner_id = fields.Many2one('res.partner',string = "Employee Partner")
    payment_method_id = fields.Many2one('account.journal',string="Payment Method",domain=[('type','in',['bank','cash'])])
    payment_id = fields.Many2one('account.payment',string="Payment",readonly=True)
    paid_amount = fields.Monetary(string="Paid Amount",readonly=True)

    state = fields.Selection([('draft','Draft'),('confirmed','Confirmed'),('approve_dept','Department Approve'),
                            ('approve_hr','HR Approve'),('approve_director','Director Approve'),('paid','Paid'),('done','Done')]
                            ,default='draft')


    @api.onchange('employee_id')
    def onchange_employee(self):
        self.department_id = self.employee_id.department_id.id
        self.job_id = self.employee_id.job_id
        self.department_manager_id = self.employee_id.department_id.manager_id.id

        return

    def unlink(self):
        for order in self:
            if order.state not in ('draft'):
                raise UserError(_('You can not delete a  confirmed Request .'))
        return super(ChartfAccount, self).unlink()


    def action_pay(self):
        payment_obj = self.env['account.payment']
        payment_method_type_id = self.env['account.payment.method'].search([('payment_type','=','outbound')],limit=1)
        payment = payment_obj.create({'payment_type' : 'outbound',
                            'partner_id' : self.partner_id.id,
                            'partner_type' : 'supplier',
                            'amount' : self.req_amount,
                            'journal_id' : self.payment_method_id.id,
                            'date' : fields.datetime.now(),
                            'payment_method_id' : payment_method_type_id.id,
                            'name' : 'Draft Payment'
                            })
        
        self.payment_id = payment.id
        self.paid_amount = payment.amount

        self.write({'state':'paid','paid_by_id': self.env.user.id,'paid_date':fields.datetime.now()})

    def action_confirm(self):
        if self.req_amount > self.employee_id.job_id.salary_limit : 
            raise   UserError(_('Your request amount is more than your salary limit.'))
        self.write({'state':'confirmed','confirm_by_id':self.env.user.id,'confirm_date' : fields.datetime.now()})

    def action_approve_dept(self):
        self.write({'state':'approve_dept','depet_manager_approve_by_id':self.env.user.id,'approve_date_department' : fields.datetime.now()})

    def action_approve_hr(self):
        self.write({'state':'approve_hr','hr_manager_id':self.env.user.id,'approve_date_hr' : fields.datetime.now()})


    def action_approve_director(self):
        self.write({'state':'approve_director','director_id':self.env.user.id,'approve_date_director' : fields.datetime.now()})

    def action_done(self):
        employee_id = self.env['hr.employee'].search([('id','=',self.employee_id.id)])
        for employee in employee_id:
            if employee_id.payslip_count != 0:
                self.write({'state':'done'})
            else:
                raise UserError(_('Payslip is not created for this month.'))
        return

class Hr_job(models.Model) :
    _inherit = 'hr.job'

    salary_limit = fields.Float(string="Salary Limit",default = 0.0)


class Hr_employee_inherit_(models.Model):
    _inherit = "hr.employee"

    def get_advancesalary(self,id,start_date,end_date):
        
        over_time_rec = self.env['advance.salary'].search([('employee_id','=',id),('paid_date','>=',start_date),
                                                                    ('paid_date','<=',end_date),('state','=','done')])

        
        total = 0.0
        for line in over_time_rec : 
            total = total + line.paid_amount 

        return total
