# -*- coding: utf-8 -*-

{
    'name': "Quorion Electronic Cash Register",
    'version': '14.0.1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Quorion cash registers support module',
    'description': """
        This module enhance the Point of Sale module by adding support to many models of cash registers from Quorion maufacturer. 
        In the Point of Sale module configuration you can link a pos to a cash register. Then, a list of product prices can be sent 
        to the register and reports can be requested after sale. With data from these reports, a session and an order are created as 
        in Point of Sale module workflow.
    """,
    'depends': ['ecr'],
    'data': [
        'security/ir.model.access.csv',
        'data/ecr_model.xml',
        'views/ecr_register_quorion.xml',
    ],
    'installable': True,
    'author': "Alexander Falcon",
    # 'website': "http://www.yourcompany.com",
    'license': 'LGPL-3',
}
