from functools import partial
from odoo import models, fields, api
from odoo.tools.misc import formatLang

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    price_subtotal_qty_delivered = fields.Float(
        'Subtotal Qty Delivered', compute='_compute_price_subtotal_qty_delivered', store=False)
    price_total_qty_delivered = fields.Float(
        'Total Qty Delivered', compute='_compute_price_total_qty_delivered', store=False)
    
    qty_delivered_amount_by_group = fields.Binary(
        string="Delivered Amount by Group", 
        compute='_compute_qty_delivered_amount_by_group', 
        help="Type: [(name, delivered amount, base, formatted delivered amount, formatted base)]"
    )
    
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
                    subtotal = line.qty_delivered * line.price_unit
                    subtotal_after_discount = subtotal * (1 - (line.discount or 0.0) / 100.0)
                    
                    taxes = line.tax_id.compute_all(
                        subtotal_after_discount,
                        order.currency_id,
                        line.qty_delivered,
                        product=line.product_id,
                        partner=order.partner_id
                    ) if line.tax_id else {'total_included': subtotal_after_discount}

                    total += taxes['total_included']

            order.price_total_qty_delivered = total
