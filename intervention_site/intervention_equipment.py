# -*- coding: utf-8 -*-

from openerp.osv import orm
from openerp.osv import fields
from openerp import tools
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import time
import datetime
from dateutil.relativedelta import relativedelta
import logging
logger = logging.getLogger('intervention_site')

EQUIP_STATUS = [
    ('owner', _('Owner')),
    ('tenant', _('Tenant')),
    ('depositary', _('Depositary')),
    ('loan', _('Loan')),
]


class InterventionEquipmentType(orm.Model):
    _name = 'intervention.equipment.type'
    _description = 'Type of equipment'

    _columns = {
        'name': fields.char(
            'Name', size=64, required=True,
            help='Name of equipment type'),
        'code': fields.char(
            'Code', size=32,
            help='Code of equipment type'),
        'active': fields.boolean(
            'Active', help='if check, this object is always available'),
        'company_id': fields.many2one(
            'res.company', 'Company'),
        'equipment_ids': fields.one2many(
            'intervention.equipment', 'type_id', 'Equipment',
            help='List of equipement link to this type'),
        'color': fields.integer(
            'Color', help='Color use in kanban view'),
    }

    _defaults = {
        'active': True,
        'company_id': lambda s, cr, uid,c:
            s.pool.get('res.company')._company_default_get(
                cr, uid, 'intervention.equipment.type', context=c),
        'color': 0,
    }


class InterventionEquipment(orm.Model):
    _name = 'intervention.equipment'
    _description = 'Equipment per site'

    _columns = {
        'name': fields.char(
            'Name', required=True, size=64, help='Name of the equipment'),
        'code': fields.char(
            'Equipement Code', size=32,
            help='Code for this equipment, keep / for automatic code'),
        'site_id': fields.many2one(
            'intervention.site', 'Site',
            help='Site where the equipment is visible'),
        'partner_id': fields.related(
            'site_id', 'partner_id', type='many2one', relation='res.partner',
            string='Address', store=True, readonly=True,
            help='Address fill on the site'),
        'active': fields.boolean(
            'Active', help='if check, this object is always available'),
        'buy_date': fields.date(
            'Buying date', help='Date when the equipment have been buy'),
        'starting_date': fields.date(
            'Commissioning', help='Date of the Commissioning'),
        'eow_date': fields.date(
            'End of warranty', help='End of the warranty'),
        'last_int_date': fields.date(
            'Last Intervention', help='Last intervention date'),
        'replace_date': fields.date(
            'Replacement', help='Date when this equipment must be replace'),
        'last_date': fields.date(
            'Last visit date',
            help='Indicate the last visite date'),
        'next_date': fields.date(
            'Next visit date',
            help='Indicate the next visite date'),
        'product_number': fields.char(
            'Product Number', size=64, help='Product Number of the equipment'),
        'serial_number': fields.char(
            'Serial Number', size=64, help='Serial number'),
        'supplier_id': fields.many2one(
            'res.partner', 'Supplier',
            help='Select supplier for this equipment'),
        'history_ids': fields.one2many(
            'intervention.equipment.history', 'equipment_id',
            'Histories', help='Histories for this equipment'),
        'type_id': fields.many2one(
            'intervention.equipment.type', 'Type',
            help='Select type of the equipment'),
        'user_id': fields.many2one(
            'res.users', 'Repairer',
            help='Choose dedicate repairer for this equipment'),
        'company_id': fields.many2one(
            'res.company', 'Company'),
        'contract_id': fields.many2one(
            'account.analytic.account', 'Contract',
            help='Contract relate to this equipment'),
        'out_of_contract': fields.boolean(
            'Out of contract', help='This equipment'),
        'notes': fields.text('Notes', help='Notes'),
        'status': fields.selection(
            EQUIP_STATUS, 'Status',
            help='Status for this equipment'),
        'free1': fields.char(
            'Free 1', size=64, help='Free field, use as you want'),
        'free2': fields.char(
            'Free 2', size=64, help='Free field, use as you want'),
        'free3': fields.char(
            'Free 3', size=64, help='Free field, use as you want'),
        'free4': fields.char(
            'Free 4', size=64, help='Free field, use as you want'),
        'free5': fields.char(
            'Free 5', size=64, help='Free field, use as you want'),
        'num1': fields.float(
            'Num 1', digits_compute=dp.get_precision('Product Unit of Measure'),
            help='Numeric field, use as you want'),
        'num2': fields.float(
            'Num 2', digits_compute=dp.get_precision('Product Unit of Measure'),
            help='Numeric field, use as you want'),
        'dat1': fields.date(
            'Date 1', help='Free date, use as you want'),
        'dat2': fields.date(
            'Date 2', help='Free date, use as you want'),
        'dat3': fields.date(
            'Date 2', help='Free date, use as you want'),

        # Field for reccurent invoicing
        'invoicing_enabled': fields.boolean(
            'Enable invoicing',
            help='Enable recurring invoicing'),
        'invoicing_contract_id': fields.many2one(
            'account.analytic.account', 'Invoicing contract',
            help='Specify contrat if different from the current contrat'),
        'invoicing_next_date': fields.date(
            'Next invoice date',
            help='Next date to invoice equipment'),
        'invoicing_period': fields.integer(
            'Period', help='Number of months between each invoice'),
        'invoicing_product_id': fields.many2one(
            'product.product', 'Product',
            help='Product to invoice'),
        'invoicing_quantity': fields.float(
            'Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
            help='Quantity of product to invoice'),
        'invoicing_journal_id': fields.many2one(
            'account.analytic.journal', 'Journal',
            help='Journal to group this element to invoice'),
    }

    _defaults = {
        'code': '/',
        'active': True,
        'company_id': lambda s, cr, uid,c:
            s.pool.get('res.company')._company_default_get(
                cr, uid, 'intervention.equipment', context=c),
        'status': '',
        'num1': 0.0,
        'num2': 0.0,
        'invoicing_enabled': False,
        'invoicing_period': 1,
        'invoicing_quantity': 1.0,
    }

    def name_get(self, cr, uid, ids, context=None):
        """
        For each equipment, add site and serial number
        """
        if context is None:
            context = {}
        if not len(ids):
            return []
        equips = self.browse(cr, uid, ids, context=context)
        res = []
        for equip in equips:
            name = equip.name
            e = equip.site_id
            if e:
                name += ' (%s)' % (e.name or '',)
            if equip.serial_number:
                name += ' [%s]' % (equip.serial_number or '',)
            elif equip.code:
                name += ' [%s]' % (equip.code or '',)
            res.append((equip.id, name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike',
                    context=None, limit=80):
        """
        We can search by code and/or name
        """
        if args is None:
            args=[]
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, uid, [('code', '=', name)] + args, limit=limit)
        if not ids:
            ids = self.search(cr, uid, [('code', 'ilike', name)] + args, limit=limit)
        if not ids:
            ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit)
        return self.name_get(cr, uid, ids, context=context)

    def copy(self, cr, uid, e_id, default=None, context=None):
        """
        Duplicate equipement
        """
        if context is None:
            context = {}

        equip = self.browse(cr, uid, e_id, context=context)

        default.update({
            'name': _('%s (Copy)') % equip.name,
            'code': '/',
            'active': True,
            'notes': _('Duplicate from [%s] %s') % (equip.code, equip.name),
            'invoicing_enabled': False,
        })
        return super(InterventionEquipment, self).copy(cr, uid, e_id, default, context=context)

    def cron_invoices(self, cr, uid, ids=None, context=None):
        """
        Cron must check only contract to compute
        """
        eq_ids = self.search(
            cr, uid, [('invoicing_enabled', '=', True)],
            context=context)
        logger.info('CRON::INVOICE equipment %s' % len(eq_ids))
        return self.trigger_invoice(cr, uid, eq_ids, context=context)

    def _compute_standard_price(self, cr, uid, product, context=None):
        """
        Override this function, id you want to provide another
        standard price
        """
        return product.standard_price

    def trigger_invoice(self, cr, uid, ids, context=None):
        """
        Button check if we can made recurring invoicing
        Compute reccuring invoices from equipment
        Line put on a contract, to be invoice next time
        """
        cur_date = time.strftime('%Y-%m-%d')
        al_obj = self.pool['account.analytic.line']
        contract_to_invoice = []
        lines_to_invoices = []
        for e in self.browse(cr, uid, ids, context=context):
            # Check if equipment have invoicing enabled
            if not e.invoicing_enabled:
                continue
            # We must check if date to invoice is past
            if e.invoicing_next_date <= cur_date:
                logger.info('Compute invoice "%s": next date %s' % (
                    e.name, e.invoicing_next_date))
                q = self._compute_standard_price(
                    cr, uid, e.invoicing_product_id, context=context)
                amount = q * e.invoicing_quantity
                unit_amount = e.invoicing_quantity
                unit = e.invoicing_product_id.uom_id.id
                vals = {
                    'ref': _('RI %s') % e.name,
                    'account_id': e.invoicing_contract_id.id,
                    'journal_id': e.invoicing_journal_id.id,
                    'user_id': uid,
                    'date': e.invoicing_next_date,
                    'name': e.name,
                    'to_invoice': e.invoicing_contract_id.to_invoice.id,
                    'product_id': e.invoicing_product_id.id,
                    'unit_amount': unit_amount,
                    'product_uom_id': unit,
                    'amount': amount,
                    'general_account_id': e.invoicing_product_id.property_account_income.id,  # noqa
                }
                line_id = al_obj.create(
                    cr, uid, vals,  context=context)
                # Add this contract to the list
                lines_to_invoices.append(line_id)
                contract_to_invoice.append(e.invoicing_contract_id.id)

                # Compute the next date to invoice and store it on the equipement
                val_month = e.invoicing_period or 1
                e.write({
                    'invoicing_next_date': datetime.datetime.strptime(
                        e.invoicing_next_date + ' 00:00:00',
                        tools.DEFAULT_SERVER_DATETIME_FORMAT) +
                    relativedelta(months=val_month),
                })
                body = _('Recurring invoicing: "%s" at %s') % (e.name, cur_date)
                e.invoicing_contract_id.message_post(
                    body=body, context=context)

        # For each contact, we invoice each line related
        inv_obj = self.pool['account.invoice']
        acc_obj = self.pool['account.analytic.account']
        for ctr_id in set(contract_to_invoice):
            ctr = acc_obj.browse(cr, uid, ctr_id, context=context)
            journal_ids = self.pool.get('account.journal').search(cr, uid,
                [('type', '=', 'sale'), ('company_id', '=', ctr.company_id.id)],
                limit=1)
            if not journal_ids:
                raise orm.except_orm(_('Error!'),
                    _('Please define sales journal for this company: "%s" (id:%d).') %
                                     (ctr.company_id.name, ctr.company_id.id))
            term_id = ctr.partner_id.property_payment_term and ctr.partner_id.property_payment_term.id or False
            if ctr.payment_term_id:
                term_id = ctr.payment_term_id.id

            inv_data = {
                'name': ctr.name or '',
                'origin': _('recurring invoicing: %s') % ctr.name,
                'type': 'out_invoice',
                'reference': ctr.name,
                'account_id': ctr.partner_id.property_account_receivable.id,
                'partner_id': ctr.partner_id.id,
                'journal_id': journal_ids[0],
                'invoice_line': [],
                'currency_id': ctr.pricelist_id.currency_id.id,
                'comment': ctr.description or False,
                'payment_term': term_id,
                'fiscal_position': ctr.partner_id.property_account_position and ctr.partner_id.property_account_position.id or False,
                'date_invoice': False,
                'company_id': ctr.company_id.id,
                'state': 'draft',
            }

            al_args = [
                ('account_id', '=', ctr_id),
                ('id', 'in', lines_to_invoices),
                ('invoice_id', '=', False),
            ]
            al_ids = al_obj.search(cr, uid, al_args, context=context)
            sequence = 1
            for line in al_obj.browse(cr, uid, al_ids, context=context):
                # We retrieve the first date on equipement line
                if not inv_data['date_invoice']:
                    inv_data['date_invoice'] = line.date
                # We compute the price from teh pricelist on contract
                # Because no priclist take in account from the invoice directly
                pricelist = ctr.pricelist_id.id
                product = line.product_id.id
                price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, line.unit_amount or 1.0, ctr.partner_id.id, {
                        'uom': line.product_uom_id.id,
                        'date': line.date,
                        })[pricelist]
                account = line.general_account_id.id or False
                if not account:
                    account = line.product_id.property_account_income.id or False
                if not account:
                    account = line.product_id.categ_id.property_account_income_categ.id
                line_data = {
                    'name': line.name,
                    'sequence': sequence,
                    'origin': line.ref,
                    'account_id': account,
                    'price_unit': price,
                    'quantity': line.unit_amount,
                    'discount': 0.0,
                    'uos_id': line.product_uom_id.id,
                    'product_id': product or False,
                    'invoice_line_tax_id': [(6, 0, [x.id for x in line.product_id.taxes_id])],
                    'account_analytic_id': line.account_id.id,
                }
                sequence += 1
                inv_data['invoice_line'].append((0, 0, line_data))

            inv_id = inv_obj.create(cr, uid, inv_data, context=context)
            inv_obj.button_reset_taxes(cr, uid, [inv_id], context=context)
            # We must update each line in contract with this invoice
            cr.execute("""
                UPDATE account_analytic_line
                   SET invoice_id=%s
                 WHERE id IN %s""", (inv_id, tuple(al_ids)))
        return True

    def create(self, cr, uid, values, context=None):
        """
        Generate site code
        """
        if context is None:
            context = {}

        if values.get('code', '') == '/':
            values['code'] = self.pool.get('ir.sequence').get(
                cr, uid, 'intervention.equip') or _('Sequence Not Defined on the company!!')

        return super(InterventionEquipment, self).create(cr, uid, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        """
        Block delete if equipment have histories
        """
        if context is None:
            context = {}

        for equip in self.browse(cr, uid, ids, context=context):
            if equip.history_ids:
                raise orm.except_orm(
                    _('Error'),
                    _('You cannot delete equipemnt with history!!, please inactivate it'))

        return super(InterventionEquipment, self).unlink(cr, uid, ids, context=context)


class InterventionEquipmentHistory(orm.Model):
    _name = 'intervention.equipment.history'
    _description = 'Equipment history'
    _order = 'hist_date desc'

    _columns = {
        'equipment_id': fields.many2one(
            'intervention.equipment', 'equipment',
            help='Equipement link to this history'),
        'hist_date': fields.date('Date', required=True, help='History date'),
        'user_id': fields.many2one('res.users', 'Users', required=True, help='Users that made this entry'),
        'summary': fields.text('Summary', help='Summary from this note'),
        'company_id': fields.related(
            'equipment_id', 'company_id', type='many2one', store=True,
            relation='intervention.equipment', string='Company'),
    }

    _defaults = {
        'hist_date': fields.date.context_today,
        'user_id': lambda self, cr, uid, ctx: uid,
        'summary': False,
    }
