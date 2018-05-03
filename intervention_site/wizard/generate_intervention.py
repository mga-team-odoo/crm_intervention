# -*- coding: utf-8 -*-
from openerp.osv import orm
from openerp.osv import fields


class GenerateIntervention(orm.TransientModel):
    _name = 'generate.equipment.intervention'
    _description = 'Generate intervention from equipment'

    _columns = {
        'name': fields.char(
            'Prefix for the intervention', size=32, required=True),
        'begin_date': fields.datetime(
            'Start date', help='Date to begin intervention'),
        'section_id': fields.many2one(
            'crm.case.section', 'Section', help='Select section'),
        'user_id': fields.many2one(
            'res.users', 'Repairer', help='Select repairer'),
        'type_id': fields.many2one(
            'crm.intervention.type', 'Type',
            help='Type of intervention'),
    }

    def create_intervention(self, cr, uid, ids, context=None):
        """
        Generate intervention from the equipment
        """
        equip_ids = context.get('active_ids', [])
        this = self.browse(cr, uid, ids[0], context=context)
        inter_obj = self.pool['crm.intervention']
        int_ids = []
        for eq in self.pool['intervention.equipment'].browse(
                cr, uid, equip_ids, context=context):
            part_id = eq.partner_id and eq.partner_id.id or False
            if eq.site_id and eq.site_id.customer_id:
                part_id = eq.site_id.customer_id.id

            part_vals = inter_obj.onchange_partner_intervention_id(cr, uid, [], part_id)
            int_args = part_vals['value']
            int_args.update({
                'name': this.name + ' ' + eq.name,
                'section_id': this.section_id and this.section_id.id or False,
                'user_id': this.user_id and this.user_id.id or False,
                'date_planned_start': this.begin_date,
                'duration_planned': 1.0,
                'partner_id': part_id,
                'equipment_id': eq.id,
                'type_id': this.type_id and this.type_id.id or False,
            })
            if this.begin_date:
                int_args['date_planned_end'] = inter_obj.onchange_planned_duration(
                    cr, uid, [], 1.0, this.begin_date)['value']['date_planned_end']
            site = eq.site_id
            if site:
                int_args['site_id'] = site.id
                if not this.section_id and site.section_id:
                    int_args['section_id'] = site.section_id.id
                if site.partner_id:
                    int_args['partner_shipping_id'] = site.partner_id.id

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

            int_ids.append(inter_obj.create(cr, uid, int_args, context=context))

        return inter_obj.open_intervention(cr, uid, int_ids, context=context)
