# -*- coding: utf-8 -*-

{
    'name': 'OPay Integration',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: OPay Integration',
    'version': '1.0',
    "author": "Sally Ahmed",
    'description': """OPay Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/inherit_account_invoice.xml',
        'views/payment_opay_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_opay_integration/static/src/js/payment_form.js',
            'https://sandboxapi.opaycheckout.com/api/v1/international/cashier/create',
        ],
    },
    'license': 'LGPL-3',
}
