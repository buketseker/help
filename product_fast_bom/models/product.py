# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class product_template(models.Model):
    _inherit = 'product.template'

    bom_line_ids = fields.One2many('mrp.bom.line','product_tmpl_id',string='BoM Line')
    bom_type = fields.Selection([
        ('normal', 'Manufacture this product'),
        ('phantom', 'Ship this product as a set of components (kit)')], 'BoM Type',
        default='normal', 
        help="Kit (Phantom): When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product.")
    code =fields.Char("Reference")
    product_qty = fields.Float("Quantity",default=1.0)

    @api.model
    def _extract_bom_line(self, vals):
        return vals.pop('bom_line_ids', {})

    @api.multi
    def _prepare_bom_vals(self, vals):
        self.ensure_one()
        return {
            'type':self.bom_type,
            'product_tmpl_id': self.id,
            'bom_line_ids': vals,
            'code':self.code,
            'product_qty':self.product_qty,
        }

    @api.multi
    def _process_bom_vals(self, vals):
        for record in self:
            if record.bom_ids:
                record.bom_ids[0].write({'bom_line_ids': vals})
            else:
                record.env['mrp.bom'].create(self._prepare_bom_vals(vals))

    @api.model
    def create(self, vals):
        bom_vals = vals.pop('bom_line_ids', {})
        record = super(product_template, self).create(vals)
        if bom_vals:
            record._process_bom_vals(bom_vals)
        return record

    @api.multi
    def write(self, vals):
        bom_vals = vals.pop('bom_line_ids', {})
        res = super(product_template, self).write(vals)
        for record in self:
            if record.bom_ids:
                record.bom_ids[0].type = record.bom_type
                record.bom_ids[0].code = record.code
                record.bom_ids[0].product_qty = record.product_qty
        if bom_vals:
            ctx = self._context.copy()
            ctx.pop('default_type', None)
            self.with_context(ctx)._process_bom_vals(bom_vals)
        return res

    @api.multi
    def unlink(self):
        for record in self:
            if record.bom_ids:
                record.bom_ids.unlink()
        return super(product_template, self).unlink()

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    _sql_constraint = (
        'uniq_product_template',
        'uniq(product_tmpl_id)',
        _('You can only have one Bom per product template'),
        )


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    product_tmpl_id = fields.Many2one('product.template',related='bom_id.product_tmpl_id',store=True,readonly=True)
