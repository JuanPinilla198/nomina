# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import datetime
import pytz
from odoo.exceptions import UserError,ValidationError
import logging
_logger=logging.getLogger(__name__)




class my_equipment_request(models.Model):
    _name = "overtime.request"
    _rec_name = "employee_id"
    _description = "Overtime Request"



    def _compute_num_of_hours(self):
        self.num_of_hours = 0.0
        for line in self :          
            if line.start_date and line.end_date :
                diff  = line.end_date - line.start_date
                days, seconds = diff.days, diff.seconds
                hours = days * 24 + seconds // 3600
                line.num_of_hours = hours
        return
        

    employee_id = fields.Many2one('hr.employee',string="Employee" ,required=True)
    start_date = fields.Datetime(string="Start Date",required=True,default=fields.datetime.now())
    end_date = fields.Datetime(string="End Date",required=True)
    department_id = fields.Many2one('hr.department',string="Department")
    department_manager_id = fields.Many2one('hr.employee',string="Manager")
    include_in_payroll = fields.Boolean(string = "Include In Payroll",default=True)
    
    approve_date = fields.Datetime(string="Approve Date",readonly=True)
    approve_by_id = fields.Many2one('res.users',string="Approve By",readonly=True)

    dept_approve_date = fields.Datetime(string="Department Approve Date",readonly=True)
    dept_manager_id = fields.Many2one('res.users',string="Department Manager",readonly=True)

    num_of_hours = fields.Float(string="Number Of Hours",compute="_compute_num_of_hours")

    notes = fields.Text(string="Notes")

    state = fields.Selection([('new','New'),('first_approve','Waiting For First Approve'),('dept_approve','Waiting For Department Approve'),
                                ('done','Done'),('refuse','Refuse')],string="State",default='new')
    
    tipo_de_hora_extra = fields.Selection([
		('hora_extra_diurna_normal','Hora extra diurno normal 25%'),
		('hora_extra_nocturno','Hora extra nocturna 75%'),
		('recargo_nocturno','Recargo nocturno 35%'),
		('hora_extra_diurna_festiva','Hora extra diurna domingos y festivo 100%'),
		('h_diurna_festiva','Hora recargo diurna festiva 75%'),
		('trabajo_extra_nocturno_domingos_festivos','Hora extra nocturno en domingos y festivos 150%'),
		('recargo_nocturna_f_d','Hora recargo nocturno dominical y festivo 110%'),
		#('recargo_nocturno_festivo','Recargo nocturno festivo 1,1'),
		#('trabajo_extra_nocturno_domingos_festivos','Hora extra nocturno en domingos y festivos 2,5'),
		#('trabajo_dominical_festivo','Hora extra diurna domingos y festivo 2'),
		
		],
		string="Tipo de hora extra",default='hora_extra_diurna_normal')

    analytic_account = fields.Many2one('account.analytic.account',string="Cuenta Analitica")

    @api.constrains('end_date','start_date')
    def check_end_date(self):
        if self.end_date < self.start_date :
            raise ValidationError(_('End Date must be after the Start Date!!'))

    @api.onchange('start_date')
    def onchange_end_date(self):
        if self.start_date:
            self.end_date = self.start_date + datetime.timedelta(hours=1)

    @api.onchange('employee_id')
    def onchange_employee(self):

        self.department_id = self.employee_id.department_id.id
        self.department_manager_id = self.employee_id.department_id.manager_id.id
        
        
    def confirm_action(self):

        self.write({'state' : 'first_approve'})
        return

    def first_approve_action(self):
        self.write({'state' : 'dept_approve',
                    'approve_by_id' : self.env.user.id,
                    'approve_date' : fields.datetime.now()})        
        return

    def dept_approve_action(self):
        self.write({'state' : 'done',
                    'dept_manager_id' : self.env.user.id,
                    'dept_approve_date' : fields.datetime.now()})       
        return


    def refuse_action(self):
        self.write({'state' : 'refuse'})
        return




