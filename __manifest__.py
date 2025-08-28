# -*- coding: utf-8 -*-
{
    'name': 'Qty Delivery Report',
    'version': '1.0',
    'description': 'Agrega un reporte de por cantidad entregada en los pedidos de venta',
    'summary': 'Agrega un reporte de por cantidad entregada en los pedidos de venta',
    'author': 'DGV',
    'website': 'https://github.com/AlfaSystemas5457/qty_delivery_report',
    'license': 'LGPL-3',
    'category': 'sale',
    'depends': [
        'sale',
        'report_xlsx',
    ],
    'data': [
        'report/sales_report.xml',
        'report/excel_sale_report.xml',
        'views/add_qty_delivered.xml',
    ],
}
