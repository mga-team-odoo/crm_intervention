# -*- coding: utf-8 -*-

from openerp.osv import orm
from openerp.osv import fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import time


class InterventionSite(orm.Model):
    _name = 'intervention.site'
    _description = 'Site of the intervention'

    _columns = {
        'name': fields.char(
            'Site Name', size=64, required=True, help='Name of the site'),
        'code': fields.char(
            'Site Code', size=32,
            help='Code for this site, keep / for automatic code'),
        'partner_id': fields.many2one(
            'res.partner', 'Address', help='Select address for this site'),
        'customer_id': fields.many2one(
            'res.partner', 'Customer', help='Select customer for this site'),
        'active': fields.boolean(
            'Active', help='if check, this object is always available'),
        'contract_id': fields.many2one(
            'account.analytic.account', 'Contract',
            help='Contract relate to this site'),
        'equipment_ids': fields.one2many(
            'intervention.equipment', 'site_id', 'Equipments',
            help='Equipment in this site'),
        'inter_ids': fields.one2many(
            'crm.intervention', 'site_id', 'Interventions',
            help='List of intervention for this site'),
        'company_id': fields.many2one(
            'res.company', 'Company'),
        'notes': fields.text('Notes', help='Notes'),
        'last_date': fields.date(
            'Last Inspection', help='Date to the last inspection'),
        'next_date': fields.date(
            'Next Inspection', help='Date to the next inspection'),
        'inspection_month': fields.integer(
            'Month', help='Number of month beetween two inspection visit'),
        'section_id': fields.many2one(
            'crm.case.section', 'Section',
            help='Section assigned to this site'),
        'user_id': fields.many2one(
            'res.users', 'Repairer',
            help='Choose dedicate repairer for this site'),
        'zip': fields.related(
            'partner_id', 'zip', type='char',
            relation='res.partner', string='Zip site',
            help='Zip code for the physical address of the site'),
        'city': fields.related(
            'partner_id', 'city', type='char',
            relation='res.partner', string='City',
            help='City for the physical address of the site'),
        'distance_product_id': fields.many2one(
            'product.product', 'Distance product',
            help='Product to invoice distance'),
        'distance_quantity': fields.float(
            'Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
            help='Quantity of distance to invoice'),
        'distance_uom_id': fields.related(
            'distance_product_id', 'uom_id', type='many2one', relation='product.uom',
            string='Distance UOM',
            help='Unit associate to the distance, cannot be changed'),
        'distance_name': fields.char(
            'Description', size=64, help='Description to invoice'),
    }

    _defaults = {
        'code': '/',
        'active': True,
        'company_id': lambda s, cr, uid,c:
            s.pool.get('res.company')._company_default_get(
                cr, uid, 'intervention.site', context=c),
        'inspection_month': 12,
        'distance_quantity': 1.0,
    }

    def name_get(self, cr, uid, ids, context=None):
        """
        For each site, add zip and city
        """
        if context is None:
            context = {}
        if not len(ids):
            return []

        res = []
        for site in self.browse(cr, uid, ids, context=context):
            name = site.name
            if site.code and site.code != '/':
                name = '[' + site.code + '] ' + name
            p = site.partner_id
            if p:
                name += ' (%s %s)' % (p.zip or '',p.city or '')
            res.append((site.id, name))
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

    def copy(self, cr, uid, s_id, default=None, context=None):
        """
        Prevent duplicate equipement
        """
        if context is None:
            context = {}

        default.update({
            'code': '/',
            'equipment_ids': [],
            'last_date': False,
            'next_date': False,
            'notes': False,
            'active': True,
        })

        return super(InterventionSite, self).copy(cr, uid, s_id, default, context=context)

    def create(self, cr, uid, values, context=None):
        """
        Generate site code
        """
        if context is None:
            context = {}

        if values.get('code', '') == '/':
            values['code'] = self.pool.get('ir.sequence').get(
                cr, uid, 'intervention.site') or _('Sequence not defined on company')

        return super(InterventionSite, self).create(cr, uid, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        """
        Block delete site, if equipment is present
        """
        if context is None:
            context = {}

        for site in self.browse(cr, uid, ids, context=context):
            if site.equipment_ids:
                raise orm.except_orm(
                    _('Error'),
                    _('You cannot delete site with equipments!! Please inactivate it'))

        return super(InterventionSite, self).unlink(cr, uid, ids, context=context)

    def create_intervention(self, cr, uid, ids, context=None):
        """Create an inetrvention from the site"""
        inter_obj = self.pool['crm.intervention']
        int_ids = []
        for site in self.browse(cr, uid, ids, context=context):
            part_id = site.customer_id and site.customer_id.id or False
            part_vals = inter_obj.onchange_partner_intervention_id(cr, uid, [], part_id)
            int_args = part_vals['value']
            int_args.update({
                'name': site.name,
                'section_id': site.section_id and site.section_id.id or False,
                'user_id': site.user_id and site.user_id.id or uid,
                'date_planned_start': time.strftime('%Y-%m-%d %H:%M:00'),
                'duration_planned': 1.0,
                'partner_id': part_id,
                'site_id': site.id,
                'equipment_id': False,
                'partner_shipping_id': site.partner_id and site.partner_id.id or part_id,
                'intervention_todo': site.notes or False,
            })
            if site.contract_id:
                int_args.update({
                    'contract_id': site.contract_id.id,
                    'partner_invoice_id': site.partner_id and site.partner_id.id or part_id,
                })
            else:
                int_args.update({
                    'contract_id': False,
                    'partner_invoice_id': part_id,
                })
            if site.user_id and site.user_id.inter_location_id:
                int_args.update({
                    'src_location_id': site.user_id.inter_location_id.id,
                })

            int_args['date_planned_end'] = inter_obj.onchange_planned_duration(
                cr, uid, [], 1.0, int_args['date_planned_start']
            )['value']['date_planned_end']
            int_ids.append(inter_obj.create(cr, uid, int_args, context=context))
        return inter_obj.open_intervention(cr, uid, int_ids, context=context)

    def _compute_extra_product(self, cr, uid, site_id, extras=None, context=None):
        """
        Hook to compute extra product like distance
        """
        if extras is None:
            extras = []

        this = self.browse(cr, uid, site_id, context=context)
        if this.distance_product_id:
            extras.append({
                'product_id': this.distance_product_id.id,
                'product_qty': this.distance_quantity,
                'product_uom_id': this.distance_uom_id.id,
                'name': this.distance_name,
                'to_invoice': True
            })
        return extras
