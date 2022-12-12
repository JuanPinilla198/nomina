# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.
{
	'name': 'Payroll for Construction & Contracting Industry in Odoo',
	'summary': 'Payroll for Construction payroll Contracting payroll Construction payroll for job costing payroll Construction contractor payroll project job costing payroll project costing payroll project job costing payroll for construction payslip costing payslip',
	'description': '''Payroll system for construction and Contracting Industry.

hr payroll
payroll in construction

	''',
	'author': 'BrowseInfo',
	'website': 'https://www.browseinfo.in',
	'category': 'Human Resources',
    "price": 15.0,
    "currency": 'EUR',
	'version': '14.0.0.0',
	'depends': ['base',
				'project',
				'hr_timesheet',
				'bi_website_mobile_timesheet',
				'bi_hr_timesheet_sheet',
				'bi_hr_payroll',
				'analytic',
				],
	'data': [
		'security/ir.model.access.csv',
		'views/timecard_view.xml',
		'views/timesheet_card.xml',
		'views/view_main.xml',
		'views/payroll_timacard_template_view.xml',
		'views/payroll_payslip_template.xml',
		'views/employee_payslip_template_view.xml',
		'views/employee_payslip_report.xml',
		],
	'installable': True,
	'application': True,
    "auto_install": False,
	'qweb': [],
	'live_test_url' : 'https://youtu.be/mC4qfNGeFQM',
	'images':['static/description/Banner.png'],
}
