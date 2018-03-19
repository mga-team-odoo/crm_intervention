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
            int_args = {
                'name': this.name + ' ' + eq.name,
                'section_id': this.section_id and this.section_id.id or False,
                'user_id': this.user_id and this.user_id.id or False,
                'date_planned_start': this.begin_date,
                'duration_planned': 1.0,
                'partner_id': part_id,
                'equipment_id': eq.id,
                'type_id': this.type_id and this.type_id.id or False,
            }
            if this.begin_date:
                int_args['date_planned_end'] = inter_obj.onchange_planned_duration(
                    cr, uid, [], 1.0, this.begin_date)['value']['date_planned_end']
            int_args.update(part_vals['value'])
            if eq.site_id:
                int_args['site_id'] = eq.site_id.id
                if not this.section_id and eq.site_id.section_id:
                    int_args['section_id'] = eq.site_id.section_id.id
                if eq.site_id.partner_id:
                    int_args['partner_shipping_id'] = eq.site_id.partner_id.id
            int_ids.append(inter_obj.create(cr, uid, int_args, context=context))

        return inter_obj.open_intervention(cr, uid, int_ids, context=context)
