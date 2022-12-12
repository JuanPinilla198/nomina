# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
import datetime
from odoo.exceptions import UserError

class Hr_employee_inherit_(models.Model):
    _inherit = "hr.employee"

    def get_overtime(self,id,start_date,end_date, hour_type=''):
        
        over_time_rec = self.env['overtime.request'].search([('employee_id','=',self.id),('start_date','>=',start_date),
                                                                    ('end_date','<=',end_date),('state','=','done')])
        total = 0.0
        for line in over_time_rec : 
            if line.include_in_payroll == True :
                #total = total + line.num_of_hours 
                if line.tipo_de_hora_extra == hour_type:
                    total = total + line.num_of_hours

        multi_over_time_rec = self.env['multiple.overtime.request'].search([('start_date','>=',start_date),
                                                                    ('end_date','<=',end_date),('state','=','done')])
        
        for res in multi_over_time_rec : 
            if res.include_in_payroll == True :
                if id in res.employee_ids.ids :
                    #total = total + res.num_of_hours 
                    if line.tipo_de_hora_extra == hour_type:
                        total = total + res.num_of_hours
        return total
