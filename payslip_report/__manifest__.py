# -*- coding: utf-8 -*-
{
    'name': 'Payslip Report',
    'version': '0.1',
    'category': 'Payroll',
    'summary': 'Payslip Report',
    'description': """
Payslip Report
============================================================
    """,
    'depends': [
        'base',
        'bi_hr_payroll',
        'bi_hr_payroll_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/views/hr_payslip_wizard_view.xml',
        'views/hr_payslip_view.xml',
        'views/hr_payroll_view.xml',
        'views/hr_payslip_view.xml',
        'views/hr_salary_rule_view.xml',
        'report/report_payslip_template.xml',
        'report/report.xml'
    ],
    'installable': True,
    'auto_install': False,
}
