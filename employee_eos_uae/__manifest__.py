# -*- coding: utf-8 -*-
{
    'name': 'Employee End of Service - UAE',
    'summary': 'Compute UAE-compliant End of Service (EOS) settlements with free zone rules and unused leave payout',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Employees',
    'author': 'Your Company',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': ['hr', 'hr_contract', 'hr_holidays'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/hr_eos_views.xml',
        'views/menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
}


