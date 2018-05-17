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


class report_contract_invoice(orm.Model):
    _inherit = 'report.contract.invoice'

    _columns = {
        'site_id': fields.many2one(
            'intervention.site', 'Site', readonly=True,
            help='Site relate'),
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
                         acc_line.invoice_id as invoice_id,
                         int_site.id as site_id
                    FROM account_analytic_account acc
                    JOIN account_analytic_line acc_line ON (acc_line.account_id = acc.id)
                    LEFT JOIN crm_intervention inter ON (inter.analytic_line_id = acc_line.id)
                    LEFT JOIN intervention_line int_line ON (int_line.analytic_line_id = acc_line.id)
                    LEFT JOIN crm_intervention inter2 ON (inter2.id = int_line.inter_id)
                    LEFT JOIN intervention_site int_site ON (int_site.id = coalesce(inter.site_id, inter2.site_id))
                  WHERE use_inter = true
                    AND acc_line.invoice_id IS NULL""")
