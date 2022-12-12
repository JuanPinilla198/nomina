# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Employee Timesheet Sheet in Odoo',
    'version': '14.0.0.1',
    'category': 'Human Resources',
    'sequence': 80,
    'price': 39,
    'currency': "EUR",
    'summary': 'Apps for Employee Timesheet Activities Employee Timesheets sheet for employee project timesheet sheet for employee timesheet log entry timesheet log for employee time-sheet log timesheet validation process Timesheet Activities for employee timesheet entry',
    'description': """

    employee timesheet , employee playslip , hourly bill ,bill timesheet , logged hours reports , track timesheet activities , 
        Hourly payslip on Payroll, HR hourly payroll, payslip based on hourly timesheet, payslip intergrated with timesheet. hourly salary calculation for employee, payslip calculation based on timesheet activity, HR timesheet payrol.Hourly payslip for employee,Generate Employee payslip based on timesheet. 
job contract, job contracting, Construction job , contracting job , contract estimation cost estimation project estimation , hourly timesheet
        This modules helps to manage contracting,Job Costing and Job Cost Sheet inculding dynamic material request
Record and validate timesheets and attendances easily
=====================================================

This application supplies a new screen enabling you to manage your work encoding (timesheet) by period. Timesheet entries are made by employees each day. At the end of the defined period, employees validate their sheet and the manager must then approve his team's entries. Periods are defined in the company forms and you can set them to run monthly or weekly.

The complete timesheet validation process is:
---------------------------------------------
* Draft sheet
* Confirmation at the end of the period by the employee
* Validation by the project manager

The validation can be configured in the company:
------------------------------------------------
* Period size (Day, Week, Month)
* Maximal difference between timesheet and attendances
This apps helps to recored Timeshees Activities of Employee as Sheet, this module has been deprecated after Odoov10.0
    employee timesheet sheet
    Odoo timesheet sheet of employee timesheet sheet of employee
    odoo timesheets sheet for employee timesheet sheet of employee
    Odoo timesheet for employee timesheet sheet for employee
    Odoo record timesheet sheet
    odoo employee timsheet log entry
    odoo timesheet log for employee time-sheet log
    """,
    'website': 'https://www.browseinfo.in',
    'author': 'BrowseInfo',
    'depends': ['hr_timesheet','web'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_timesheet_sheet_security.xml',
        'data/hr_timesheet_sheet_data.xml',
        'views/hr_timesheet_sheet_templates.xml',
        'views/hr_timesheet_sheet_views.xml',
        'views/hr_department_views.xml',
        'views/hr_timesheet_sheet_config_settings_views.xml',
	    'report/employee_timesheet_report.xml',
	    'report/employee_timesheet_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://youtu.be/vBs0omX_xu0',
    'qweb': ['static/src/xml/timesheet.xml', ],
    "images":['static/description/Banner.png'],
}
