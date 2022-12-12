# -*- coding: utf-8 -*-
{
    'name': "get_leaves",

    'summary': """
        Obtiene datos para el timbrado de horas extras y ausencias""",

    'description': """
        Obtiene datos para el timbrado de horas extras y ausencias
    """,

    'author': "Andrés Gaviria Taborda",
    'website': "http://www.intresco.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '14.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'hr',
                'bi_hr_payroll',
                'bi_hr_overtime_request_comm',
                ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
