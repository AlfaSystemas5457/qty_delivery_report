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
                    price_with_discount = line.price_unit * (1.0 - line.discount / 100.0)
                    subtotal = line.qty_delivered * price_with_discount
                    
                    total_tax = 0.0

                    if line.tax_id:
                        for tax in line.tax_id:
                            tax_rate = tax.amount / 100.0
                            tax_amount = subtotal * tax_rate
                            total_tax += tax_amount 

                        total_included = subtotal + total_tax
                    else:
                        total_included = subtotal

                    total += total_included
                    
            order.price_total_qty_delivered = total
            
