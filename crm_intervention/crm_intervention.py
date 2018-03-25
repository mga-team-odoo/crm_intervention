# -*- coding: utf-8 -*-
##############################################################################
#
#    crm_intervention module for OpenERP, Managing intervention in CRM
#    Copyright (C) 2011 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Sebastien LANGE <sebastien.lange@syleam.fr>
#    Copyright (C) 2014-2017 Christophe CHAUVET.
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

from openerp.addons.base_status.base_state import base_state
from openerp.addons.base_status.base_stage import base_stage
from openerp.addons.crm import crm
from openerp.osv import orm
from openerp.osv import fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import time
import pytz
import datetime
import openerp.tools as tools

CRM_INTERVENTION_STATES = (
    crm.AVAILABLE_STATES[2][0],  # Cancelled
    crm.AVAILABLE_STATES[3][0],  # Done
    crm.AVAILABLE_STATES[4][0],  # Pending
)

html_invitation = _("""
<html>
<head>
<meta http-equiv="Content-type" content="text/html; charset=utf-8" />
<title>%(name)s</title>
</head>
<body>
<table border="0" cellspacing="10" cellpadding="0" width="100%%"
    style="font-family: Arial, Sans-serif; font-size: 14">
    <tr>
        <td width="100%%">Hello,</td>
    </tr>
    <tr>
        <td width="100%%">You are invited by <i>%(user)s</i></td>
    </tr>
    <tr>
        <td width="100%%">Below are the details of event. Hours and dates expressed in %(timezone)s time.</td>
    </tr>
</table>

<table cellspacing="0" cellpadding="5" border="0" summary=""
    style="width: 90%%; font-family: Arial, Sans-serif; border: 1px Solid #ccc; background-color: #f6f6f6">
    <tr valign="center" align="center">
        <td bgcolor="DFDFDF">
        <h3>%(name)s</h3>
        </td>
    </tr>
    <tr>
        <td>
        <table cellpadding="8" cellspacing="0" border="0"
            style="font-size: 14" summary="Eventdetails" bgcolor="f6f6f6"
            width="90%%">
            <tr>
                <td width="21%%">
                <div><b>Start Date</b></div>
                </td>
                <td><b>:</b></td>
                <td>%(start_date)s</td>
                <td width="15%%">
                <div><b>End Date</b></div>
                </td>
                <td><b>:</b></td>
                <td width="25%%">%(end_date)s</td>
            </tr>
            <tr valign="top">
                <td><b>Description</b></td>
                <td><b>:</b></td>
                <td colspan="3">%(description)s</td>
            </tr>
            <tr valign="top">
                <td>
                <div><b>Location</b></div>
                </td>
                <td><b>:</b></td>
                <td colspan="3">%(location)s</td>
            </tr>
        </table>
        </td>
    </tr>
</table>
</body>
</html>
""")


class res_partner(orm.Model):
    """
    Add dedicate user for the intervention on this partner
    """
    _inherit = 'res.partner'

    _columns = {
        'intervention_user_id': fields.many2one(
            'res.users', 'Repairer',
            help='Select the dedicate repairer'),
    }


class crm_case_section(orm.Model):
    _inherit = 'crm.case.section'

    _columns = {
        'unit_hour_id': fields.many2one('product.uom', 'Hour unit',
                                        help='Select unit represent hour'),
        'unit_day_id': fields.many2one('product.uom', 'Day unit',
                                       help='Select unit represent days'),
        'use_inter': fields.boolean(
            'In intervention', help='If check, we can use in intervention'),
    }

    _defaults = {
        'use_inter': False,
    }


class intervention_type(orm.Model):
    _name = 'crm.intervention.type'
    _description = 'Intervention type'

    _columns = {
        'name': fields.char(
            'Name', size=64, required=True,
            help='Name of the intervention type'),
        'code': fields.char(
            'Code', size=16,
            help='Code for this intervention type'),
        'company_id': fields.many2one(
            'res.company', 'Company'),
        'color': fields.integer(
            'Color', help='Color for Kanban view'),
        'product_id': fields.many2one(
            'product.product', 'product',
            help='Product service to invoice'),
        'notes': fields.text(
            'Notes', help='Notes'),
        'active': fields.boolean(
            'Active', help='if check, this object is always available'),
    }

    _defaults = {
        'color': 0,
        'company_id': lambda s, cr, uid, c: s.pool.get(
            'res.company')._company_default_get(
                cr, uid, 'crm.intervention.type', context=c),
        'active': True,
    }


class crm_intervention(base_state, base_stage, orm.Model):
    _name = 'crm.intervention'
    _description = 'Intervention'
    _order = "date_planned_start desc"
    _inherit = ['mail.thread']

    def _get_default_section_intervention(self, cr, uid, context=None):
        """Gives default section for intervention section
        :param self: The object pointer
        :param cr: the current row, from the database cursor,
        :param uid: the current user’s ID for security checks,
        :param context: A standard dictionary for contextual values
        """
        mod, res_id = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'crm_intervention', 'section_interventions_department')
        if res_id:
            return res_id
        return False

    def _get_default_email_cc(self, cr, uid, context=None):
        """Gives default email address for intervention section
        :param self: The object pointer
        :param cr: the current row, from the database cursor,
        :param uid: the current user’s ID for security checks,
        :param context: A standard dictionary for contextual values
        """
        mod, res_id = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'crm_intervention', 'section_interventions_department')
        if res_id:
            return self.pool['crm.case.section'].browse(
                cr, uid, res_id, context=context).reply_to
        return False

    _columns = {
        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Name', size=128, required=True),
        'active': fields.boolean('Active', required=False),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'description': fields.text('Description'),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'write_date': fields.datetime('Update Date', readonly=True),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'section_id': fields.many2one(
            'crm.case.section', 'Interventions Team',
            domain=[('use_inter', '=', True)],
            help='Interventions team to which Case belongs to.'
            'Define Responsible user and Email account for mail gateway.'),
        'company_id': fields.many2one('res.company', 'Company'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'email_cc': fields.text(
            'Watchers Emails', size=252,
            help="These email addresses will be added to the CC field of all "
            "inbound and outbound emails for this record before being sent. "
            "Separate multiple email addresses with a comma"),
        'email_from': fields.char(
            'Email', size=128, help="These people will receive email."),
        'ref': fields.reference(
            'Reference', selection=crm._links_get, size=128),
        'ref2': fields.reference(
            'Reference 2', selection=crm._links_get, size=128),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'categ_id': fields.many2one(
            'crm.case.categ', 'Category',
            domain="[('section_id','=',section_id), "
            "('object_id.model', '=', 'crm.intervention')]"),
        'number_request': fields.char('Number Request', size=64),
        'customer_information': fields.text('Customer_information', ),
        'intervention_todo': fields.text(
            'Intervention to do',
            help="Indicate the description of this intervention to do", ),
        'date_planned_start': fields.datetime(
            'Planned Start Date',
            help="Indicate the date of begin intervention planned", ),
        'date_planned_end': fields.datetime(
            'Planned End Date',
            help="Indicate the date of end intervention planned", ),
        'date_effective_start': fields.datetime(
            'Effective start date',
            help="Indicate the date of begin intervention",),
        'date_effective_end': fields.datetime(
            'Effective end date',
            help="Indicate the date of end intervention",),
        'duration_planned': fields.float(
            'Planned duration',
            help='Indicate estimated to do the intervention.'),
        'duration_effective': fields.float(
            'Effective duration',
            help='Indicate real time to do the intervention (w/o pause).'),
        'pause_effective': fields.float(
            'Pause duration',
            help='Indicate real time pause in the intervention.'),
        'alldays_planned': fields.boolean(
            'All day planned', help='All-day intervention planned'),
        'alldays_effective': fields.boolean(
            'All day effective', help='All-day intervention effective'),
        'partner_id': fields.many2one(
            'res.partner', 'Customer',
            change_default=True, select=True),
        'partner_invoice_id': fields.many2one(
            'res.partner', 'Invoice Address',
            help="The name and address for the invoice",),
        'partner_order_id': fields.many2one(
            'res.partner', 'Intervention Contact',
            help="The name and address of the contact that "
            "requested the intervention."),
        'partner_shipping_id': fields.many2one(
            'res.partner', 'Intervention Address'),
        'partner_address_phone': fields.char('Phone', size=64),
        'partner_address_mobile': fields.char('Mobile', size=64),
        'state': fields.selection(
            crm.AVAILABLE_STATES, 'State', size=16, readonly=True,
            help="The state is set to 'Draft', when a case is created."
            "\nIf the case is in progress the state is set to 'Open'."
            "\nWhen the case is over, the state is set to \'Done\'."
            "\nIf the case needs to be reviewed then the state is set to"
            "'Pending'."),
        'contract_id': fields.many2one(
            'account.analytic.account', 'Contract',
            help='Select analytic account to generate line on this contract\n'
                 'if no contrat, invoicing button generate an invoice'),
        'analytic_line_id': fields.many2one(
            'account.analytic.line', 'Analytic line',
            help='Analytic line'),
        'invoice_contract_id': fields.related(
            'analytic_line_id', 'invoice_id', type='many2one', relation='account.invoice',
            string='Invoice contract', store=True, help='Invoice relate in this contract'),
        'invoice_id': fields.many2one(
            'account.invoice', 'Invoice',
            help='Invoice link to this intervention'),
        'invoice_qty': fields.float(
            'Invoice Qty', digits_compute=dp.get_precision('Account'),
            help='Quantity to invoice'),
        'invoice_uom_id': fields.many2one('product.uom', 'Invoice Unit', help='Invoice unit'),
        'product_id': fields.many2one(
            'product.product', 'Prestation',
            domain=[('type', '=', 'service')],
            help='Product service relate with this intervention'),
        'out_of_contract': fields.boolean(
            'Out of contract',
            help='If check, this product is invoiced directly'),
        'message_ids': fields.one2many(
            'mail.message', 'res_id', 'Messages',
            domain=[('model', '=', _name)]),
        'meeting_id': fields.many2one(
            'crm.meeting', 'Meeting',
            help='Intervention store in calendar'),
        'type_id': fields.many2one(
            'crm.intervention.type', 'Type',
            help='Type of the intervention'),
    }

    _defaults = {
        'partner_invoice_id': lambda self, cr, uid,
        context: context.get('partner_id', False) and
        self.pool.get('res.partner').address_get(
            cr, uid, [context['partner_id']], ['invoice'])['invoice'],
        'partner_order_id': lambda self, cr, uid,
        context: context.get('partner_id', False) and
        self.pool.get('res.partner').address_get(
            cr, uid, [context['partner_id']], ['contact'])['contact'],
        'partner_shipping_id': lambda self, cr, uid,
        context: context.get('partner_id', False) and
        self.pool.get('res.partner').address_get(
            cr, uid, [context['partner_id']], ['delivery'])['delivery'],
        'number_request': lambda obj, cr, uid,
        context: obj.pool.get('ir.sequence').get(cr, uid, 'intervention'),
        'active': 1,
        'user_id': lambda s, cr, uid, c: s._get_default_user(cr, uid, c),
        'email_cc': _get_default_email_cc,
        'state': 'draft',
        'section_id': _get_default_section_intervention,
        'company_id': lambda s, cr, uid,
        c: s.pool.get('res.company')._company_default_get(
            cr, uid, 'crm.helpdesk', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
        'alldays_planned': False,
        'alldays_effective': False,
        'pause_effective': 0.0,
        'out_of_contract': False,
    }

    def _create_calendar_event(self, cr, uid, inter, context=None):
        """
        Create an event in calendar meeting
        """
        ctx = context.copy()
        ctx['inter_event'] = True  # Prevent recursive loop
        meeting_obj = self.pool.get('crm.meeting')
        cal_type = self.pool['ir.model.data'].get_object_reference(
            cr, uid, 'crm_intervention', 'metting_type_intervention')[1]
        meeting_vals = {
            'name': inter.name or _('Intervention'),
            'categ_ids': [(6, 0, [cal_type])],
            'duration': inter.duration_planned,
            'description': inter.intervention_todo or inter.customer_information or '',
            'user_id': inter.user_id.id,
            'date': inter.date_planned_start,
            'end_date': inter.date_planned_end,
            'date_deadline': inter.date_planned_end,
            'allday': inter.alldays_planned,
            'state': 'open',
            'class': 'confidential',
        }
        meeting_id = meeting_obj.create(cr, uid, meeting_vals)
        inter.write({'meeting_id': meeting_id}, context=ctx)
        return meeting_id

    def _delete_calendar_event(self, cr, uid, meeting_id, context=None):
        """
        delete the event in calendar when intervention is cancel or draft
        """
        return self.pool['crm.meeting'].unlink(cr, uid, [meeting_id], context=context)

    def write(self, cr, uid, ids, values, context=None):
        """
        Before changing state, check if date is filled
        """
        if context is None:
            context = {}

        res = super(crm_intervention, self).write(cr, uid, ids, values,
                                                  context=context)

        for inter in self.browse(cr, uid, ids, context=context):
            if inter.state == 'open':
                if not inter.date_planned_start:
                    raise orm.except_orm(
                        _('Error'),
                        _('Date planned start is required before open the intervention')  # noqa
                    )
                if not inter.date_planned_end:
                    raise orm.except_orm(
                        _('Error'),
                        _('Date planned end is required before open the intervention')  # noqa
                    )
                if not context.get('inter_event'):
                    self._create_calendar_event(cr, uid, inter, context=context)
            elif inter.state == 'pending':
                if not inter.date_effective_start:
                    raise orm.except_orm(
                        _('Error'),
                        _('Date effective start is required before to pending the intervention')  # noqa
                    )
                if not (inter.date_effective_end or inter.alldays_effective):
                    raise orm.except_orm(
                        _('Error'),
                        _('Date effective end or all days is required before to pending the intervention')  # noqa
                    )
            elif inter.state == 'cancel':
                if inter.meeting_id:
                    self._delete_calendar_event(cr, uid, inter.meeting_id.id, context=context)
            elif inter.state == 'draft':
                if inter.meeting_id:
                    self._delete_calendar_event(cr, uid, inter.meeting_id.id, context=context)
        return res

    def case_pending(self, cr,uid, ids, context=None):
        """
        Check if product defined on type_id
        """
        for inter in self.browse(cr, uid, ids, context=context):
            if not inter.product_id and inter.type_id and inter.type_id.product_id:
                inter.write({'product_id': inter.type_id.product_id.id})
        return super(crm_intervention, self).case_pending(
            cr, uid, ids, context=context)

    @staticmethod
    def _eval_timestamp(curdate):
        _date = datetime.datetime.fromtimestamp(time.mktime(
            time.strptime(curdate, "%Y-%m-%d %H:%M:%S")))
        return _date

    def onchange_product_id(self, cr, uid, ids, product_id, alldays, duration, pause, begin_dt,
                            end_dt, context=None):
        vals = {
            'invoice_qty': 0.0,
            'invoice_uom_id': False,
        }
        if not product_id:
            return {'value': vals}

        product = self.pool['product.product'].browse(cr, uid, product_id, context=context)
        vals['invoice_uom_id'] = product.uom_id.id
        if alldays:
            _b = self._eval_timestamp(begin_dt)
            try:
                _e = self._eval_timestamp(end_dt)
                vals['invoice_qty'] = (_e - _b).days + 1.0
            except Exception, e:
                vals['invoice_qty'] = 1.0
        else:
            vals['invoice_qty'] = duration

        return {'value': vals}

    def onchange_partner_intervention_id(self, cr, uid, ids, part):
        if not part:
            return {
                'value': {
                    'partner_invoice_id': False,
                    'partner_shipping_id': False,
                    'partner_order_id': False,
                    'email_from': False,
                    'partner_address_phone': False,
                    'partner_address_mobile': False,
                    'contract_id': False,
                }
            }
        part_obj = self.pool['res.partner']
        addr = part_obj.address_get(
            cr, uid, [part], ['default', 'delivery', 'invoice', 'contact'])
        part = part_obj.browse(cr, uid, part)
        val = {
            'partner_invoice_id': addr['invoice'],
            'partner_order_id': addr['contact'],
            'partner_shipping_id': addr['delivery'],
        }
        part_deliv = self.pool.get('res.partner').browse(
            cr, uid, addr['delivery'])
        val.update({
            'email_from': part_deliv.email,
            'partner_address_phone': part_deliv.phone,
            'partner_address_mobile': part_deliv.mobile,
        })

        # retrieve contract if only one
        ctr_ids = self.pool['account.analytic.account'].search(cr, uid, [
            ('partner_id', '=', part.id),
            ('type', '=', 'contract'),
            ('use_inter', '=', True),
        ])
        if len(ctr_ids) == 1:
            val['contract_id'] = ctr_ids[0]
        if part.intervention_user_id:
            val['user_id'] = part.intervention_user_id.id

        return {'value': val}

    def onchange_planned_duration(self, cr, uid, ids, planned_duration,
                                  planned_start_date):
        if not planned_duration:
            return {'value': {'date_planned_end': False}}
        start_date = datetime.datetime.fromtimestamp(
            time.mktime(time.strptime(
                planned_start_date, "%Y-%m-%d %H:%M:%S")))
        return {'value': {
            'date_planned_end': (start_date + datetime.timedelta(
                hours=planned_duration)).strftime('%Y-%m-%d %H:%M:%S')}}

    def onchange_planned_end_date(self, cr, uid, ids, planned_end_date,
                                  planned_start_date):
        start_date = datetime.datetime.fromtimestamp(time.mktime(
            time.strptime(planned_start_date, "%Y-%m-%d %H:%M:%S")))
        end_date = datetime.datetime.fromtimestamp(time.mktime(
            time.strptime(planned_end_date, "%Y-%m-%d %H:%M:%S")))
        difference = end_date - start_date
        minutes, secondes = divmod(difference.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return {'value': {
            'duration_planned': (float(difference.days * 24) +
                                 float(hours) + float(minutes) / float(60))}}

    def onchange_effective_values(self, cr, uid, ids, eff_str_date,
            duration_eff, pause_eff, eff_end_date, fld=''):
        """
        Compute effective date
        """
        vals = {}
        warn = {}
        if not eff_str_date and ids:
            warn = {
                'title': _('Warning'),
                'message': _('Please fill be start date!!')
            }

        if eff_str_date:
            start_date = datetime.datetime.fromtimestamp(time.mktime(
                time.strptime(eff_str_date, "%Y-%m-%d %H:%M:%S")))

        if fld == 'end' and eff_str_date and eff_end_date:
            end_date = datetime.datetime.fromtimestamp(time.mktime(
                time.strptime(eff_end_date, "%Y-%m-%d %H:%M:%S")))
            difference = end_date - start_date
            minutes, secondes = divmod(difference.seconds, 60)
            hours, minutes = divmod(minutes, 60)
            vals = {
                'duration_effective': (
                    float(difference.days * 24) +
                    float(hours) + float(minutes) / float(60)) - pause_eff
            }
        if fld in ('duration', 'pause') and eff_str_date:
            total_duration =  (duration_eff or 0.0) + (pause_eff or 0.0)
            vals = {
                'date_effective_end': (start_date + datetime.timedelta(
                    hours=total_duration)).strftime('%Y-%m-%d %H:%M:00')
            }
        return {'warning': warn, 'value': vals}

    def send_event_repairer(self, cr, uid, ids, context=None):
        """Send an email to the repairer"""
        if context is None:
            context = {}
        if len(ids) > 1:
            raise orm.except_orm(
                _('Error'),
                _('Send one mail per intervention'))

        inter = self.browse(cr, uid, ids[0], context=context)

        def ics_datetime(idate, short=False):
            if idate:
                #returns the datetime as UTC, because it is stored as it in the database
                return datetime.datetime.strptime(idate, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.timezone('UTC'))
            return False
        try:
            import vobject
        except ImportError:
            raise orm.except_orm(
                _('Error'),
                _('missing vobject library'))

        usr = self.pool['res.users'].browse(cr, uid, uid, context=context)
        cal = vobject.iCalendar()
        event = cal.add('vevent')
        event.add('created').value = ics_datetime(time.strftime('%Y-%m-%d %H:%M:%S'))
        event.add('dtstart').value = ics_datetime(inter.date_planned_start)
        event.add('dtend').value = ics_datetime(inter.date_planned_end)
        event.add('summary').value = inter.name
        if  inter.customer_information:
            event.add('description').value = inter.customer_information
        if inter.partner_shipping_id:
            addr = self.pool['res.partner']._display_address(
                cr, uid, inter.partner_shipping_id, context=context)
            event.add('location').value = addr
        ics_file = cal.serialize()

        desc = inter.customer_information
        if inter.intervention_todo and desc:
            desc += '<br/><hr/><br/>' + inter.intervention_todo
        else:
            desc = inter.intervention_todo

        body_vals = {
            'name': inter.name,
            'start_date': inter.date_planned_start,
            'end_date': inter.date_planned_end,
            'timezone': context.get('tz', pytz.timezone('UTC')),
            'description': desc or '-',
            'location': addr or '-',
            'user': usr.name,
        }
        body = html_invitation % body_vals
        if usr.alias_id:
            sender = "%s <%s@%s>" % (usr.name, usr.alias_id.alias_name,
                                     usr.alias_id.alias_domain)
        else:
            sender = "%s <%s>" % (usr.name, usr.email)

        vals = {
            'email_from': sender,
            'email_to': inter.user_id.email,
            'state': 'outgoing',
            'subject': _('[INTERVENTION] %s') % inter.name,
            'body_html': body,
            'auto_delete': True
        }
        if ics_file:
            vals['attachment_ids'] = [(0,0,{
                'name': 'intervention.ics',
                'datas_fname': 'intervention.ics',
                'datas': str(ics_file).encode('base64')})]
        self.pool.get('mail.mail').create(cr, uid, vals, context=context)
        log_body = _('Event send to %s by email') % usr.name
        inter.message_post(body=log_body, type='comment')
        return True

    def action_email_send(self, cr, uid, ids, context=None):
        """
        Send email from the form
        """
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'  # noqa
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(
                cr, uid, 'crm_intervention', 'email_template_intervention')[1]
        except ValueError:
            template_id = False

        try:
            compose_form_id = ir_model_data.get_object_reference(
                cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        ctx = dict(context)
        ctx.update({
            'default_model': 'crm.intervention',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': False
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Override to updates the document according to the email. """
        if custom_values is None:
            custom_values = {}

        vals = {
            'name': msg.get('subject'),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'description': msg.get('body'),
            'user_id': False,
        }
        if msg.get('priority', False):
            vals['priority'] = msg.get('priority')

        vals.update(custom_values)
        return super(crm_intervention, self).message_new(
            cr, uid, msg, custom_values=vals, context=context)

    def message_update(self, cr, uid, ids, msg, vals={},
                       default_act='pending', context=None):
        """
        :param self: The object pointer
        :param cr: the current row, from the database cursor,
        :param uid: the current user’s ID for security checks,
        :param ids: List of update mail’s IDs
        """
        if isinstance(ids, (str, int, long)):
            ids = [ids]

        maps = {
            'cost': 'planned_cost',
            'revenue': 'planned_revenue',
            'probability': 'probability'
        }
        vls = {}
        for line in msg['body'].split('\n'):
            line = line.strip()
            res = tools.command_re.match(line)
            if res and maps.get(res.group(1).lower()):
                key = maps.get(res.group(1).lower())
                vls[key] = res.group(2).lower()
        vals.update(vls)

        # Unfortunately the API is based on lists
        # but we want to update the state based on the
        # previous state, so we have to loop:
        for case in self.browse(cr, uid, ids, context=context):
            values = dict(vals)
            if case.state in CRM_INTERVENTION_STATES:
                values.update(state=crm.AVAILABLE_STATES[1][0])  # re-open
            res = self.write(cr, uid, [case.id], values, context=context)
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        """
        """
        if context is None:
            context = {}

        if default is None:
            default = {}

        default.update({
            'number_request': self.pool['ir.sequence'].get(
                cr, uid, 'intervention'),
            'date_effective_start': False,
            'date_effective_end': False,
            'duration_effective': 0.0,
            'pause_effective': 0.0,
            'alldays_effective': False,
            'categ_id': False,
            'description': False,
            'timesheet_ids': False,
            'analytic_line_id': False,
            'invoice_id': False,
            'invoice_contract_id': False,
        })

        return super(crm_intervention, self).copy(
            cr, uid, id, default, context=context)

    def _required_field(self, inter, fields):
        """Check if fields given is fill"""
        for f in fields:
            if not getattr(inter, f):
                raise orm.except_orm(
                    _('Error'),
                    _('%s is necessary to make invoice') % f
                )

    def prepare_invoice(self, cr, uid, ids, context=None):

        for inter in self.browse(cr, uid, ids, context=context):
            self._required_field(inter=inter, fields=[
                'product_id','invoice_qty', 'invoice_uom_id'])

            self.generate_analytic_line(
                cr, uid, [inter.id], context=context)
            self.generate_invoice(
                cr, uid, [inter.id], context=context)
        return True

    def _prepare_invoice_line(self, cr, uid, inter, lines, inv, context=None):
        """
        Hook to add more than one line in the invoice
        """
        line_obj = self.pool['account.invoice.line']
        line = {
            'origin': inter.number_request,
            'product_id': inter.product_id.id,
            'quantity': inter.invoice_qty,
        }
        line.update(line_obj.product_id_change(
            cr, uid, [], inter.product_id.id, inter.product_id.uom_id.id,
            qty=line['quantity'], partner_id=inter.partner_invoice_id.id,
            fposition_id=inv['fiscal_position'], context=context,
            company_id=inter.company_id and inter.company_id.id or
            False)['value']
        )
        line['uos_id'] = inter.invoice_uom_id.id,
        line['invoice_line_tax_id'] = [
            (6, 0, line['invoice_line_tax_id'])
        ]
        line['name'] = inter.name + '\n' + inter.user_id.name + '\n' \
            + inter.number_request + '\n' + line['name']
        lines.append(line)
        return lines

    def generate_invoice(self, cr, uid, ids, context=None):
        """
        Generate a direct invoice
        """
        inv_obj = self.pool['account.invoice']
        line_obj = self.pool['account.invoice.line']
        for inter in self.browse(cr, uid, ids, context=context):
            if not inter.out_of_contract and inter.contract_id:
                continue

            if inter.invoice_id:
                raise orm.except_orm(_('Error'),
                                     _('This intervention already invoiced'))
            if not inter.product_id:
                raise orm.except_orm(_('Error'),
                                     _('Product to invoice is necessary'))

            vals = {
                'partner_id': inter.partner_invoice_id.id,
                'date_invoice': inter.date_effective_start[:10],
                'type': 'out_invoice',
                'origin': _('GI %s') % inter.number_request,
                'user_id': inter.user_id.id,
                'section_id': inter.section_id.id,
            }
            vals.update(inv_obj.default_get(cr, uid, [
                'journal_id', 'currency_id', 'state', 'company_id',
                'internal_number', 'sent', 'user_id', 'reference_type'
            ], context=context))
            result = inv_obj.onchange_partner_id(
                cr, uid, [], 'out_invoice', vals['partner_id'],
                vals['date_invoice'], False, False,
                inter.company_id and inter.company_id.id or False)
            vals.update(result['value'])

            lines = self._prepare_invoice_line(cr, uid, inter, [], vals, context=context)
            vals['invoice_line'] = [(0, 0, l) for l in lines]

            inv_id = inv_obj.create(cr, uid, vals, context=context)
            inv_obj.button_reset_taxes(cr, uid, [inv_id], context=context)
            inter.write({'invoice_id': inv_id, 'state': 'done'})

        return True

    def generate_analytic_line(self, cr, uid, ids, context=None):
        """
        Generate an analytic line in the contract specified, base on product
        """
        for inter in self.browse(cr, uid, ids, context=context):
            if inter.out_of_contract or not inter.contract_id:
                continue
            if inter.analytic_line_id:
                raise orm.except_orm(_('Error'), _('This intervention already pre-invoiced'))  # noqa
            if not inter.product_id:
                raise orm.except_orm(_('Error'), _('Product to invoice is necessary'))  # noqa
            if not inter.contract_id:
                raise orm.except_orm(_('Error'), _('Contract is necessary'))

            emp = self._get_employee(cr, uid, inter, context=context)
            if not inter.section_id:
                raise orm.except_orm(
                    _('Error'),
                    _('No section defined on this intervention!'))

            sprice = inter.product_id.standard_price or 1.0
            if inter.alldays_effective:
                q = self.pool['product.uom']._compute_price(
                    cr, uid, inter.product_id.uom_id.id,
                    sprice, inter.section_id.unit_day_id.id)
                amount = q * -1
                unit_amount = 1.0
                unit = inter.section_id.unit_day_id.id
            else:
                q = self.pool['product.uom']._compute_price(
                    cr, uid, inter.product_id.uom_id.id,
                    sprice, inter.section_id.unit_hour_id.id)
                amount = (q * inter.duration_effective) * -1
                unit_amount = inter.duration_effective
                unit = inter.section_id.unit_hour_id.id

            if not emp.journal_id:
                raise orm.except_orm(
                    _('Error'),
                    _('Not journal defined on teh employee!!'))

            vals = {
                'name': _('BI Num %s') % inter.number_request,
                'account_id': inter.contract_id.id,
                'journal_id': emp.journal_id.id,
                'user_id': inter.user_id.id,
                'date': inter.date_effective_start[:10],
                'ref': inter.name[:64],
                'to_invoice': inter.contract_id.to_invoice.id,
                'product_id': inter.product_id.id,
                'unit_amount': unit_amount,
                'product_uom_id': unit,
                'amount': amount,
                'general_account_id': inter.product_id.property_account_income.id,  # noqa
            }

            line_id = self.pool['account.analytic.line'].create(
                cr, uid, vals,  context=context)
            inter.write({'analytic_line_id': line_id, 'state': 'done'},
                        context=context)

        return True

    def _get_employee(self, cr, uid, inter, context=None):
        """
        To create an analytical line, we have to retrieve
        the employee associated with the user
        if no user defined on inetrvention, we use the current user

        :return: Return a browse object to the employee
        """
        user_id = inter.user_id and inter.user_id.id or uid
        emp_obj = self.pool['hr.employee']
        emp_ids = emp_obj.search(cr, uid, [
            ('user_id', '=', user_id)
        ], context=context)
        if not emp_ids:
            raise orm.except_orm(
                _('Error'),
                _('Employee not found (uid: %s)' % uid)
            )
        return emp_obj.browse(cr, uid, emp_ids[0], context=context)

    def open_intervention(self, cr, uid, int_ids, context=None):
        """Open the tree or form view of intervention"""
        mod_obj = self.pool['ir.model.data']
        act_obj = self.pool['ir.actions.act_window']

        result = mod_obj.get_object_reference(cr, uid, 'crm_intervention', 'crm_case_intervention_act111')
        r_id = result and result[1] or False
        result = act_obj.read(cr, uid, [r_id], context=context)[0]
        result['domain'] = "[('id','in', [" + ','.join(map(str, int_ids)) + "])]"
        del result['context']
        result['context'] = context or {}

        return result


class account_analytic_account(orm.Model):
    _inherit = 'account.analytic.account'

    _columns = {
        'use_inter': fields.boolean(
            'Use in intervention',
            help='Check this if this contract can be in intervention'),
    }

    _defaults = {
        'use_inter': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
