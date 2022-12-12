# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

{
    'name': 'Cancel Employee Done Payslip',
    'version': '14.0.1.0',
    'sequence': 1,
    'category': 'Generic Modules/Human Resources',
    'description':
        """
        This Module add below functionality into odoo

        1.Cancel Done Payslip\n
odoo all allow Cancel employee Done Payslip, cancel employee payslip, hr cancel paylsip, payslip cancel, reject payslip, delete payslip entries, cancel payslip entries, employee cancel payslip, cancel process payslip, employee cancel payslip compute sheet

    """,
    'summary': 'cancel payslip odoo app allow cancel employee Done Payslip, cancel employee payslip, hr cancel paylsip, payslip cancel, reject payslip, delete payslip entries, cancel payslip entries, employee cancel payslip, cancel process payslip, employee cancel payslip compute sheet',
    'author': 'Devintelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',
    'depends': ['bi_hr_payroll', 'account', 'bi_hr_payroll_account'],
    'data': [
        'security/security.xml',
        'views/payslip_views.xml'
        ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    
    # author and support Details =============#
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',    
    'maintainer': 'DevIntelle Consulting Service Pvt.Ltd', 
    'support': 'devintelle@gmail.com',
    'price':15.0,
    'currency':'EUR',
    #'live_test_url':'https://youtu.be/A5kEBboAh_k',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
