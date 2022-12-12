# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

{
    'name': "Payslip Report",
    'category': 'Payroll',
    'version': '12.0.1.0',
    'author': 'Equick ERP',
    'description': """
        This module allows user to print payslip report in PDF format.
    """,
    'summary': """
        This module allows user to print payslip report in PDF format.
        | payslip report | payroll report | payroll template
        | payslip template | employee payslip report | employee payroll report.
    """,
    'depends': ['base', 'bi_hr_payroll'],
    'price': 12,
    'currency': 'EUR',
    'license': 'OPL-1',
    'website': "",
    'data': [
        'views/report.xml',
        'views/report_custom_payslip_temp.xml',
        'views/liquidacion_report_co.xml'
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: