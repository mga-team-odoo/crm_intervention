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
