# -*- coding: utf-8 -*-
{
    'name': 'Payslip send to DIAN',
    'version': '14.1.1.1',
    'category': 'Payroll',
    'summary': 'Payslip send to DIAN',
    'description': """
Payslip send to DIAN
============================================================
    """,
    'depends': [
        'base',
        'bi_hr_payroll',
        'mail',
        'eq_payslip_custom_pdf_report',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/ir_config_settings_view.xml',
        'views/hr_payslip_view.xml',
        'data/payslip_sequence.xml',
        'data/payslip_template.xml',
        'views/hr_contract_view.xml',
        'views/hr_employee_view.xml',
        'views/res_company_view.xml',
        'views/hr_salary_rule_view.xml',
        'report/payment_report_co.xml',
        'views/state_code_view.xml',
        'data/state_code_data.xml',
        'data/dian_documents_payslip.xml',
        'wizard/views/payroll_cancel_wiz_view.xml',
        'wizard/views/adjuste_method_view.xml',
        'views/payroll_window_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
