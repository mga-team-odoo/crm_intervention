# -*- coding: utf-8 -*-
##############################################################################
#
#    crm_intervention module for OpenERP, Managing intervention in CRM
#    Copyright (C) 2011 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Sebastien LANGE <sebastien.lange@syleam.fr>
#              Christophe CHAUVET <christophe.chauvet@gmail.com>
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

{
    'name': 'CRM Intervention',
    'version': '0.4',
    'category': 'Generic Modules/CRM & SRM',
    'description': """Intervention Management""",
    'author': 'SYLEAM, Mirounga',
    'website': 'http://www.mirounga.fr/',
    'depends': [
        'crm',
        'account',
        'base_calendar',
        'hr_timesheet_invoice',
    ],
    'data': [
        'security/crm_security.xml',
        'security/ir.model.access.csv',
        'views/crm_intervention_view.xml',
        'data/crm_intervention_data.xml',
        'wizard/intervention_to_invoice_view.xml',
        'report/crm_intervention_view.xml',
        'report/contract_to_invoice_view.xml',
        'edi/mail_template.xml',
    ],
    'demo': [
        'demo/intervention.xml',
    ],
    'test': [
        'test/intervention.yml',
        'test/intervention_alldays.yml',
        'test/intervention_contract.yml',
        'test/intervention_out_of_contract.yml',
    ],
    'installable': True,
    'active': False,
    'license': 'AGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
