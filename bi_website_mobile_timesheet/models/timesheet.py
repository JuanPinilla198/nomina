# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class Website(models.Model):
    _inherit = 'website'


    def get_country_list(self):            
        country_ids=self.env['res.country'].sudo().search([])
        return country_ids
        
    def get_state_list(self):            
        state_ids=self.env['res.country.state'].sudo().search([])
        return state_ids

    def get_all_timesheets(self):            
        user_name = self.env.user.name
        timesheet_ids = self.env['account.analytic.line'].sudo().search([('user_id','=', self.env.user.name),("project_id.hide_project",'=',False),("project_id.allow_timesheets",'=',True)])
        return timesheet_ids

    def get_timesheets(self,date):            
        user_name = self.env.user.name
        timesheet_ids = self.env['account.analytic.line'].sudo().search([('date','=', date),('user_id','=', self.env.user.name),("project_id.hide_project",'=',False),("project_id.allow_timesheets",'=',True)])
        return timesheet_ids

    def get_project_details(self):

        project_details = self.env['project.project'].sudo().search([])
        project_ids = self.env['project.project'].sudo().search([("hide_project",'=',False),("allow_timesheets",'=',True)])
        partner = self.env['res.partner'].browse(self.env['res.users'].browse(self.env['res.users']._context['uid']).partner_id.id)
        projects = []
        for i in project_ids :
            # if partner in i.message_partner_ids :
            projects.append(i)
        return projects

    def get_task_details(self):
        a = self.get_project_details()
        projects = self.env['project.project'].sudo().search([("hide_project",'=',False),("allow_timesheets",'=',True)])
        partner = self.env['res.partner'].browse(self.env['res.users'].browse(self.env['res.users']._context['uid']).partner_id.id)
        tasks = []

        for p in a:
            for t in p.task_ids:
                tasks.append(t)
        return tasks

    def get_work_types(self):

        work_type = self.env['timesheet.work.type'].sudo().search([])
        return work_type

    def edit_timesheet(self,timesheet):

        work_type = self.env['timesheet.work.type'].sudo().search([])
        return work_type

class AnalyticTimesheetDetails(models.Model):
    _inherit = 'account.analytic.line'

    work_type = fields.Many2one('timesheet.work.type','Work Type')
    st_time = fields.Char('Start Time')
    ed_time = fields.Char('End Time')
    is_billable = fields.Boolean('Is Billable')
    is_paid = fields.Boolean('Is Paid')
    employee = fields.Many2one("res.users")

class TimesheetWorkTypes(models.Model):
    _name = 'timesheet.work.type'
    _description = "timesheet work type model"
    _rec_name = "work_type"

    work_code = fields.Char("Code")
    work_type = fields.Char("Name")

class TimesheetUserDetails(models.Model):
    _name = 'timesheet.user.details'
    _description = "timesheet user details model"

    name = fields.Char('Name')
    login = fields.Char('Login')
    lang = fields.Many2one('res.lang')
    last_update = fields.Datetime('Last Connection')

    project_project = fields.Many2one('project.project')
    project_task = fields.Many2one('project.task')

class ProjectUpdate(models.Model):
    _inherit = 'project.project'

    timesheet_user = fields.One2many('timesheet.user.details','project_project')
    hide_project = fields.Boolean("Hide Project in web")

class ProjectUpdateTask(models.Model):
    _inherit = 'project.task'

    timesheet_user = fields.One2many('timesheet.user.details','project_task')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

