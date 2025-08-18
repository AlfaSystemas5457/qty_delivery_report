from functools import partial
from odoo import models, fields, api
from odoo.tools.misc import formatLang
import os

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

        log_lines = []
        for order in self:
            total = 0.0
            for line in order.order_line:
                if line.qty_delivered > 0:
                    # Calcular el subtotal basado en lo entregado (sin descuentos)
                    subtotal = line.qty_delivered * line.price_unit
                    log_lines.append(f"Subtotal sin descuento (line {line.id}): {subtotal}")

                    # Aplicar descuento sobre el subtotal
                    subtotal_after_discount = subtotal * (1 - (line.discount or 0.0) / 100.0)
                    log_lines.append(f"Subtotal después del descuento (line {line.id}): {subtotal_after_discount}")

                    # Verificar impuestos
                    if line.tax_id:
                        # Calcular impuestos sobre el subtotal después del descuento
                        tax_details = line.tax_id.compute_all(
                            subtotal_after_discount,
                            order.currency_id,
                            line.qty_delivered,
                            product=line.product_id,
                            partner=order.partner_id
                        )
                        total_included = tax_details['total_included']  # Total con impuestos
                        log_lines.append(f"Impuestos calculados (line {line.id}): {total_included}")
                    else:
                        # Si no hay impuestos, el total es solo el subtotal después del descuento
                        total_included = subtotal_after_discount
                        log_lines.append(f"Sin impuestos, total incluido es el subtotal (line {line.id}): {total_included}")

                    # Acumulamos el total después de impuestos
                    total += total_included
                    log_lines.append(f"Total acumulado después de esta línea (line {line.id}): {total}")

            # Asignamos el total calculado a price_total_qty_delivered
            order.price_total_qty_delivered = total
            log_lines.append(f"Total final (order {order.id}): {order.price_total_qty_delivered}")

        # Guardar los logs en un archivo txt
        log_path = os.path.join(os.path.expanduser("~"), "qty_delivery_report_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            for line in log_lines:
                f.write(line + "\n")



