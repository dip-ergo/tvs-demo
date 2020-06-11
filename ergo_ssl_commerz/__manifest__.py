# -*- coding: utf-8 -*-
{
    'name': "SSLCommerz Payment Acquirer",

    'summary': """
        SSLCommerz Payment Acquirer""",

    'description': """
        This module integrates sslcommerz payment gateway V4.0 with Odoo
    """,

    'author': "Ergo Ventures Ltd",
    'website': "http://www.ergo-ventures.com",
    'category': 'Accounting/Payment',
    'version': '2.0',

    # any module necessary for this one to work correctly
    'depends' : ['payment'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/ssl_commerz_views.xml',
        'views/ssl_commerz_payment_template.xml',
        'data/payment_acquirer_data.xml',
        # 'views/add_contact_wizard.xml'
    ],

    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
