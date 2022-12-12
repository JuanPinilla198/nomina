# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Nómina Colombiana',
    'category': 'Human Resources',

    'depends': ['base',
                'hr',
                'l10n_co',
                'bi_hr_payroll_account',
                'account_extra',           
                'payslip_rules_methods',
                'bi_hr_employee_loan_comm',
                'get_leaves',
                'bi_hr_overtime_request_comm',
                'bi_employee_advance_salary_comm',
                 ],
    'description': """
Nomina Colombiana
======================

* Nómina Básica Colombiana
    """,

    'data': [
        'views/l10n_co_hr_payroll_view.xml',
        'data/l10n_co_hr_payroll_data.xml',
        'views/res_company_view.xml',
        'data/leaves_types.xml',
        'data/calendar.xml',
    ],
}
