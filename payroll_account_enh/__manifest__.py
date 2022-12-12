# -*- encoding: utf-8 -*-
{
    'name': 'Payroll Accounting Enhancement',
    'version': '14.0.0.1',
    'description': """Payroll Accounting Enhancement""",
    'depends': [
        'bi_hr_payroll_account',
        'dev_payslip_cancel',
    ],
    'data': [
        'views/view.xml',
    ],
    'installable': True,
    'application': True,
}
