# -*- coding: utf-8 -*-
##############################################################################
#
#    crm_intervention module for OpenERP, Managing intervention in CRM
#    Copyright (C) 2014-2018 Christophe CHAUVET.
#
#    This file is a part of crm_intervention
#
#    crm_intervention is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    crm_intervention is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import orm
from openerp.osv import fields
from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


class report_contract_invoice(orm.Model):
    _name = 'report.contract.invoice'
    _description = 'Contract to invoice'
    _auto = False
    _order = 'contract_id'
    _rec_name = 'description'

    _columns = {
        'contract_id': fields.many2one(
            'account.analytic.account', 'Contract', readonly=True,
            help='Contract relate to this lines'),
        'partner_id': fields.many2one(
            'res.partner', 'Invoiced partner', readonly=True,
            help='Partner related to the contract'),
        'pricelist_id': fields.many2one(
            'product.pricelist', 'Pricelist', readonly=True,
            help=''),
        'manager_id': fields.many2one(
            'res.users', 'Responsible', readonly=True,
            help=''),
        'real_date': fields.date('Line date', readonly=True),
        'product_id': fields.many2one(
            'product.product', 'product',  readonly=True),
        'quantity': fields.float(
            'Quantity', digits_compute=dp.get_precision('Product Price'),
            readonly=True),
        'uom_id': fields.many2one('product.uom', 'Uom', readonly=True),
        'user_id': fields.many2one('res.users', 'Repairer', readonly=True),
        'reference': fields.char(
            'Reference', size=64, readonly=True,
            help='Intervention'),
        'description': fields.char('Description', size=256, readonly=True),
        'company_id': fields.many2one(
            'res.company', 'Company', readonly=True,
            help='Company relate to this line'),
        'invoice_id': fields.many2one(
            'account.invoice', 'Invoices', readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_contract_invoice')
        cr.execute("""
                  CREATE OR REPLACE VIEW report_contract_invoice AS
                  SELECT acc_line.id as id,
                         acc.id as contract_id,
                         acc.partner_id as partner_id,
                         acc.pricelist_id as pricelist_id,
                         acc.manager_id as manager_id,
                         acc_line.date as real_date,
                         acc_line.name as description,
                         acc_line.product_id as product_id,
                         acc_line.unit_amount as quantity,
                         acc_line.product_uom_id as uom_id,
                         acc_line.user_id as user_id,
                         acc_line.to_invoice as to_invoice_id,
                         acc_line.ref as reference,
                         acc.company_id as company_id,
                         acc_line.invoice_id as invoice_id
                    FROM account_analytic_account acc
                    JOIN account_analytic_line acc_line on acc_line.account_id = acc.id
                  WHERE use_inter = true
                    AND acc_line.invoice_id IS NULL""")

    def group_per_contract(self, cr, uid, ids, context=None):
        """
        Group each line ids, per contract
        Return dict with 1 key per contract, and the list of line
        related to this contract
        """
        res = {}
        warn = []
        for l in self.browse(cr, uid, ids, context=context):
            if l.contract_id.id not in res:
                res[l.contract_id.id] = [l.id]
                if not l.contract_id.pricelist_id:
                    warn.append(_('\nNo pricelist on contract %s/%s') % (
                        l.contract_id.code, l.contract_id.name))
            else:
                res[l.contract_id.id].append(l.id)

        if warn:
            raise orm.except_orm(
                _('Error'),
                _('Please check: %s') % ''.join(warn))
        return res

    def _invoice_header(self, cr, uid, ctr, context=None):
        """
        Compose the invoice header
        """
        inv_obj = self.pool['account.invoice']
        vals = {
            'partner_id': ctr.partner_id.id,
            'date_invoice': context.get('date_invoice') or False,
            'type': 'out_invoice',
            'origin': _('Contract %s/%s') % (ctr.code, ctr.name),
            'user_id': ctr.manager_id and ctr.manager_id.id or False,
            'section_id': False,
        }
        vals.update(inv_obj.default_get(cr, uid, [
            'journal_id', 'currency_id', 'state', 'company_id',
            'internal_number', 'sent', 'user_id', 'reference_type'
        ], context=context))
        result = inv_obj.onchange_partner_id(
            cr, uid, [], 'out_invoice', vals['partner_id'],
            vals['date_invoice'], False, False,
            ctr.company_id and ctr.company_id.id or False)
        vals.update(result['value'])

        return vals

    def _hook_compose_origin(self, cr, uid, line, context=None):
        """
        Compose an origin for this line
        """
        return line.reference

    def _hook_compose_notes(self, cr, uid, line, context=None):
        """
        Compose an note for this line
        """
        return line.reference

    def _hook_line_extra(self, cr, uid, line, context=None):
        """
        This Hook can permit to add additionnal field for the line
        return a dict with key for account.invoice.line
        """
        return {}

    def _hook_header_extra(self, cr, uid, ctr, context=None):
        """
        This Hook can permit to add additionnal field for the invoice
        return a dict with key for account.invoice
        """
        return {}

    def _invoice_lines(self, cr, uid, lines, context=None):
        """
        Compose a dict for each lines
        """
        res = []
        cpt = 1
        inter_obj = self.pool['crm.intervention']
        for l in lines:
            pline = {
                'name': l.description,
                'product_id': l.product_id.id,
                'quantity': l.quantity,
                'uos_id': l.uom_id.id,
                'sequence': cpt,
                'price_unit': 0.0,
                'discount': 0.0,
                'invoice_line_tax_id': [(6, 0, [x.id for x in l.product_id.taxes_id])],
                'account_analytic_id': l.contract_id.id,
            }
            cpt += 1
            partner = l.partner_id
            pline.update(inter_obj._compute_pricelist(
                cr, uid, partner, l.product_id, l.quantity,
                context=context))  # add price_unit and discount
            pline['origin'] = self._hook_compose_origin(cr, uid, l, context=context)
            pline['notes'] = self._hook_compose_notes(cr, uid, l, context=context)
            # Call hook to add additionnal field
            pline.update(self._hook_line_extra(cr, uid, l, context=context))

            res.append(pline)
        return res

    def _invoiced_contract(self, cr, uid, values, context=None):
        """
        For each key in values (1 per contract),
        """
        inv_obj = self.pool['account.invoice']
        ctr_obj = self.pool['account.analytic.account']
        inv_ids = []
        for ctr_id in values.keys():
            line_ids = values[ctr_id]
            ctr = ctr_obj.browse(cr, uid, ctr_id, context=context)
            accline = self.browse(cr, uid, line_ids, context=context)
            vals = self._invoice_header(cr, uid, ctr, context=context)
            lines = self._invoice_lines(cr, uid, accline, context=context)
            vals.update(self._hook_header_extra(cr, uid, ctr, context=context))
            vals['invoice_line'] = [(0, 0, l) for l in lines]
            inv_id = inv_obj.create(cr, uid, vals, context=context)
            inv_obj.button_reset_taxes(cr, uid, [inv_id], context=context)
            inv_ids.append(inv_id)

            # We must update each line in contract with this invoice
            cr.execute("""
                UPDATE account_analytic_line
                   SET invoice_id=%s
                 WHERE id IN %s""", (inv_id, tuple(line_ids)))

        return inv_ids

    def list_invoices(self, cr, uid, ids, context=None):
        """
        Return the list of invoices
        """
        res = set()  # We  use set to remove duplicate invoice
        for l in self.browse(cr, uid, ids, context=context):
            if l.invoice_id:
                res.add(l.invoice_id.id)

        return list(res)
