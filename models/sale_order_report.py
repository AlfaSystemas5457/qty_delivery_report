from functools import partial
from odoo import models, fields, api
from odoo.tools.misc import formatLang
import os

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    price_subtotal_qty_delivered = fields.Monetary(
        'Subtotal Cantidad Entregada', compute='_compute_price_subtotal_qty_delivered', store=False)
    price_total_qty_delivered = fields.Monetary(
        'Total Cantidad Entregada', compute='_compute_price_total_qty_delivered', store=False)
    amount_tax_qty_delivered = fields.Monetary(
        'Impuesto Cantidad Entregada', compute='_compute_amount_tax_qty_delivered', store=False)
    
    qty_delivered_amount_by_group = fields.Binary(
        string="Importe Entregado por Grupo", 
        compute='_compute_qty_delivered_amount_by_group', 
        help="Tipo: [(nombre, importe entregado, base, importe entregado formateado, base formateada)]"
    )
    
    @api.onchange('price_total_qty_delivered', 'price_subtotal_qty_delivered')
    def _compute_amount_tax_qty_delivered(self):
        for order in self:
            order.amount_tax_qty_delivered = order.price_total_qty_delivered - order.price_subtotal_qty_delivered
    
    def _compute_qty_delivered_amount_by_group(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in order.order_line:
                price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
                taxes = line.tax_id.compute_all(
                    price_reduce,
                    quantity=line.qty_delivered,
                    product=line.product_id,
                    partner=order.partner_shipping_id
                )['taxes']
                for tax in line.tax_id:
                    group = tax.tax_group_id
                    res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                    for t in taxes:
                        if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                            res[group]['amount'] += t['amount']
                            res[group]['base'] += t['base']
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            order.qty_delivered_amount_by_group = [(
            l[0].name, l[1]['amount'], l[1]['base'],
            fmt(l[1]['amount']), fmt(l[1]['base']),
            len(res),
            ) for l in res]
            
    def _compute_price_subtotal_qty_delivered(self):
        for order in self:
            subtotal = 0.0
            for line in order.order_line:
                if line.qty_delivered and line.price_unit:
                    subtotal += line.qty_delivered * line.price_unit
            order.price_subtotal_qty_delivered = subtotal

    def _compute_price_total_qty_delivered(self):
        for order in self:
            total = 0.0
            for line in order.order_line:
                if line.qty_delivered > 0:
                    if line.tax_id:
                        price_with_discount = line.price_unit * (1.0 - line.discount / 100.0)
                        taxes = line.tax_id.compute_all(
                            price_with_discount,
                            quantity=line.qty_delivered,
                            product=line.product_id,
                            partner=order.partner_shipping_id
                        )
                        total_included = taxes['total_included']
                    else:
                        total_included = line.qty_delivered * line.price_unit

                    total += total_included
                    
            order.price_total_qty_delivered = total

class ExcelSaleOrder(models.AbstractModel):
    _name = 'report.qty_delivery_report.report_saleorder_excel'
    _inherit = 'report.report_xlsx.abstract'

    
    def generate_xlsx_report(self, workbook, data, partners):
        """
        Export the sale order report to Excel format.
        This method can be called from a button or action.
        """
        sheet = workbook.add_worksheet('Pedidos de Venta')

        title_header = workbook.add_format({'bold': True, 'font_size': 20, 'align': 'center', 'valign': 'vcenter'})
        title = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
        text = workbook.add_format({'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
        currency_format = workbook.add_format({'num_format': '[$$-80A]#,##0.00','font_size': 16, 'align': 'center', 'valign': 'vcenter'})
        
        sheet.set_column('A:B', 20)
        sheet.set_column('D:E', 50)
        sheet.set_column('F:G', 25)
        sheet.set_column('H:H', 30)
        sheet.set_column('I:I', 20)
        
        for order in partners:
            sheet.merge_range(0, 0, 0, 1, f"{order.name}", title_header)
            sheet.write(1, 0, "Fecha:", title)
            sheet.write(1, 1, order.date_order, date_format)
            
            sheet.write(2, 0, "Cliente:", title)
            sheet.write(2, 1, order.partner_id.name, text)
            
            sheet.write(3, 0, "Plazos de pago:", title)
            sheet.write(3, 1, order.payment_term_id.name if order.payment_term_id else "N/A", text)
            
            sheet.write(0, 3, "Producto", title)
            sheet.write(0, 4, "Descripción", title)
            sheet.write(0, 5, "Cantidad entregada", title)
            sheet.write(0, 6, "Precio unitario", title)
            sheet.write(0, 7, "Impuesto", title)
            sheet.write(0, 8, "Subtotal", title)
            
            row = 1
            for order_line in order.order_line:
                sheet.write(row, 3, f"{order_line.product_id.display_name}", text)
                sheet.write(row, 4, f"{order_line.name}", text)
                sheet.write(row, 5, order_line.qty_delivered if order_line.qty_delivered else 0, text)
                sheet.write(row, 6, order_line.price_unit, currency_format)
                sheet.write(row, 7, ", ".join([tax.name for tax in order_line.tax_id]), text)
                sheet.write(row, 8, (order_line.qty_delivered if order_line.qty_delivered else 0) * (order_line.price_unit), currency_format)
                
                row += 1
            
            sheet.merge_range(5, 0, 5, 1, "Entregado", title)
            
            sheet.write(6, 0, "Subtotal", title)
            sheet.write(6, 1, order.price_subtotal_qty_delivered, currency_format)
            
            sheet.write(7, 0, "Impuestos", title)
            sheet.write(7, 1, order.amount_tax_qty_delivered, currency_format)
            
            sheet.write(8, 0, "Total", title)
            sheet.write(8, 1, order.price_total_qty_delivered, currency_format)
            