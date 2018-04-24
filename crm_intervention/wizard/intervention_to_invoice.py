# -*- coding: utf-8 -*-
from openerp.osv import orm
from openerp.osv import fields
from openerp.tools.translate import _
import logging
logger = logging.getLogger('crm_intervention')


class InterventionToInvoice(orm.TransientModel):
    _name = 'generate.intervention.invoice'
    _description = 'Generate intervention from equipment'

    _columns = {
        'date': fields.date(
            'Invoice date', required=True,
            help='Date for the invoice generate'),
    }

    _defaults = {
        'date': fields.date.context_today,
    }

    def create_invoice(self, cr, uid, ids, context):
        """
        Creat invoices and display it
        """
        if context.get('active_model', '') != 'report.contract.invoice':
            raise orm.except_orm(
                _('Error'),
                _('Must be launch on contract to invoice only'))
        this = self.browse(cr, uid, ids[0], context=context)
        line_ids = context.get('active_ids', [])
        ctr_inv_obj = self.pool['report.contract.invoice']
        inter_obj = self.pool['crm.intervention']

        logger.info('Compute %s lines' % len(line_ids))
        ctx = context.copy()
        ctx['date_invoice'] = this.date

        ctr_val = ctr_inv_obj.group_per_contract(cr, uid, line_ids, context=ctx)
        inv_ids = ctr_inv_obj._invoiced_contract(cr, uid, ctr_val, context=ctx)
        return inter_obj.open_invoices(cr, uid, inv_ids, context=ctx)
