# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from datetime import datetime, date, timedelta
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.portal.controllers.portal import CustomerPortal
from dateutil.relativedelta import relativedelta
import time
from odoo.tools import groupby as groupbyelem
from operator import itemgetter

class CustomerTimesheet(CustomerPortal):

    @http.route(['/timesheet'], type='http', auth="public", website=True)
    def search_timesheet(self, page=1, **kwargs):
        partner = request.env.user.partner_id
        return request.render("bi_website_mobile_timesheet.timesheet_search_page")

    def _get_search_timesheet_domain(self, search):
        domain = []
        if search:
            for srch in search.split(" "):
                domain = ['|','|',('name', 'ilike', srch),('project_id.name', 'ilike', srch),('task_id.name', 'ilike', srch)]
        return domain


    def _get_search_timesheet(self, post):
        # OrderBy will be parsed in orm and so no direct sql injection
        # id is added to be sure that order is a unique sort key
        return '%s ,id desc' % post.get('timesheet_ftr','write_date desc')


    @http.route(['/my/timesheet'], type='http', auth="public", website=True)
    def partner_timesheet(self, search="" ,**post):
        partner = request.env.user.partner_id
        user_name = request.env.user.name
        sheet_date = False
        domain = self._get_search_timesheet_domain(search)
        keep = QueryURL('/my/timesheet' , search=search, order=post.get('order'))
        if 'date' in post :
            sheet_date = post['date']
            username = partner.name
            if sheet_date:
                domain += [('date','=', sheet_date),('user_id','=', request.env.user.name)]
            else:
                domain += [('date','=', '1000-07-06'),('user_id','=', request.env.user.name)]
        else:
            username = partner.name
            domain += [('user_id.name','=', request.env.user.name)]
        domain += [('project_id.allow_timesheets','=',True),('project_id.hide_project','=',False)]
        format_str = '%d%m%Y' 
            
        if post.get('time_ftr') == "current date":
            current_date = datetime.now()
            domain += [('date','=',current_date)]

        if post.get('time_ftr') == "last month":
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month-1)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append(str(month))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('date','>=',from_date),('date','<=',to_date)]
            
        if post.get('time_ftr') == "last week":
            domain+=[('date','>=', ((date.today()  + relativedelta(days=0, weeks=-1)).strftime('%Y-%m-%d'))),
            ('date','<=', ((date.today()  + relativedelta(days=6, weeks=-1)).strftime('%Y-%m-%d')))]
            
        if post.get('time_ftr') == "last year":
            from_month = []
            to_month = []
            from_month.append('01')
            from_month.append('01')
            from_month.append(str(date.today().year-1))
            to_month.append('30')
            to_month.append('12')
            to_month.append(str(date.today().year-1))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('date','>=',from_date),('date','<=',to_date)]
        
        if post.get('time_ftr') == "current month":
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append(str(month))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('date','>=',from_date),('date','<=',to_date)]

        if post.get('time_ftr') == "current week":
            domain+=[('date','<=', ((date.today() - relativedelta(days=1, weeks=-1)).strftime('%Y-%m-%d'))),
            ('date','>=', ((date.today() - relativedelta(days=7, weeks=-1)).strftime('%Y-%m-%d')))]

        if post.get('time_ftr') == "current year":
            from_month = []
            to_month = []
            from_month.append('01')
            from_month.append('01')
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append('12')
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('date','>=',from_date),('date','<=',to_date)]

        if post.get('time_ftr') == "current quarter":
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month)
            month_sec = '{:02d}'.format(date.today().month+2)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append(str(month_sec))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('date','>=',from_date),('date','<=',to_date)]
        
        tasks = request.env['account.analytic.line'].sudo().search(domain, order=self._get_search_timesheet(post))
        request.session['my_tasks_history'] = tasks.ids[:100]
        
        if post.get('timesheet_group') == "project":
            grouped_tasks = [request.env['account.analytic.line'].concat(*g) for k, g in groupbyelem(tasks, itemgetter('project_id'))]
        if post.get('timesheet_group') == "task":
            grouped_tasks = [request.env['account.analytic.line'].concat(*g) for k, g in groupbyelem(tasks, itemgetter('task_id'))]
        if post.get('timesheet_group') == "employee":
            grouped_tasks = [request.env['account.analytic.line'].concat(*g) for k, g in groupbyelem(tasks, itemgetter('employee'))]

        else:
            grouped_tasks = [tasks]
          
        timesheet_ids = request.env['account.analytic.line'].sudo().search(domain, order=self._get_search_timesheet(post))
        if timesheet_ids:
            return request.render("bi_website_mobile_timesheet.bi_portal_my_timesheet",{"username" : username , 'timesheet_ids' : timesheet_ids, 'keep' : keep , 'search' : search, 'grouped_tasks': grouped_tasks,'groupby': post.get('timesheet_group')})
        else:
            return request.render("bi_website_mobile_timesheet.bi_portal_my_timesheet",{"khush":'khush',"username" : username , 'timesheet_ids' : timesheet_ids, 'keep' : keep , 'search' : search, 'grouped_tasks': grouped_tasks,'groupby': post.get('timesheet_group')})

class AddTimesheet(http.Controller):

    @http.route(['/my/add_new_timesheet'], type='http', auth="public", website=True)
    def add_new_timesheet(self, page=1, **kwargs):
        
        partner = request.env.user.partner_id
        return request.render("bi_website_mobile_timesheet.bi_new_timesheet_form")

    @http.route(['/my/new_timesheet_submit'], type='http', auth="public", website=True)
    def submit_new_timesheet(self, **post):
        
        if post:
            project = post['project']
            task = post['task']
            date = post['date']
            duration = post['duration']
            st_time = post['st_time']
            ed_time = post['ed_time']
            work_type = post['work_types']
            disc = post['disc']
            is_billable = post.get('is_billable') or False
            is_paid = post.get('is_paid') or False
            lang = request.env['res.lang'].sudo().search([('code','=',request.env.user.lang)]) 


            analytic_obj = request.env['account.analytic.line']
            project_obj = request.env['project.project'].sudo().browse(int(project))
            task_obj = request.env['project.task'].sudo().browse(int(task))
            timesheet_user_entry = request.env['timesheet.user.details']

            if is_billable == 'on':
                is_billable = True
            else:
                is_billable = False

            if is_paid == 'on':
                is_paid = True
            else:
                is_paid = False

            work_type = request.env['timesheet.work.type'].sudo().search([('work_type','ilike',work_type)])
            duration_replace = duration.replace(':', '.')
            analytic_obj = analytic_obj.sudo().create({
                'date':date,
                'user_id': request.env.user.id,
                'name': disc,
                'project_id': project_obj.id,
                'account_id' : project_obj.analytic_account_id.id,
                'task_id': task_obj.id,
                'work_type': work_type.id,
                'st_time': st_time,
                'ed_time': ed_time,
                'is_billable': is_billable,
                'is_paid': is_paid,
                'unit_amount': float(duration_replace),  
            })

            timesheet_user_entry = timesheet_user_entry.sudo().create({
                'name': request.env.user.name,
                'login': request.env.user.email,
                'lang' : lang.id,
                'last_update': datetime.now(),
                'project_project': project_obj.id,
                'project_task': task_obj.id,
            })

            return request.redirect("/my/timesheet")
        else:
            request.render("bi_website_mobile_timesheet.timesheet_failed")

class EditTimesheet(http.Controller):

    @http.route(['/edit_timesheet/<model("account.analytic.line"):timesheet>'], type='http', auth="public", website=True)
    def edit_timesheet(self, timesheet, category='', search='', **kwargs):
        return request.render("bi_website_mobile_timesheet.bi_portal_edit_timesheet",{'timesheet':timesheet})


    # DELETE TIMESHEET
    @http.route('/my/delete_timesheet/', type='json', auth="public", methods=['POST'], website=True)
    def delete_timesheet(self, ts_id, **post):
        timesheet_ids = request.env['account.analytic.line'].sudo().search([('id','=',ts_id)])
        timesheet_ids.unlink()
        return request.redirect('/my/timesheet')    

    # SAVE EDITED TIMESHEET
    @http.route(['/my/save_edit_timesheet'], type='http', auth="public", website=True)
    def edit_timesheet_save(self,context=None,**post):
        if post:
            project = post['project']
            task = post['task']
            date = post['date']
            duration = post['duration']
            st_time = post['st_time']
            ed_time = post['ed_time']
            work_type = post['work_types']
            disc = post['disc']
            is_billable = post.get('is_billable') or False
            is_paid = post.get('is_paid') or False

        if is_billable == 'on':
            is_billable = True
        else:
            is_billable = False

        if is_paid == 'on':
            is_paid = True
        else:
            is_paid = False

        timesheet_id = str(post['timesheet_id'])

        project_obj = request.env['project.project'].sudo().search([('id','=',project)])
        task_obj = request.env['project.task'].sudo().search([('id','=',task)])
        analytic_obj = request.env['account.analytic.line'].sudo().search([('id','=',timesheet_id)])
        work_type = request.env['timesheet.work.type'].sudo().search([('work_type','ilike',work_type)])
        duration_replace = duration.replace(':', '.')
        analytic_obj.update({
            'date':date,
            'user_id': request.env.user.id,
            'name': disc,
            'project_id': project_obj.id,
            'task_id': task_obj.id,
            'work_type': work_type.id,
            'st_time': st_time,
            'ed_time': ed_time,
            'is_billable': is_billable,
            'is_paid': is_paid,
            'unit_amount': float(duration_replace), 
        })
        return request.redirect("/my/timesheet")
        