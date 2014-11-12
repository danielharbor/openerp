# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name" : "Academics Management",
    "version" : "1.0",
    "author" : "Daniel Harbor",
    "category": 'Academics',
    "description": """
    AUN Academic Module including admission, registrar, student and dean Module
    """,
    'website': 'http://www.aun.com',
    'init_xml': [],
    "depends" : ['hr', 'account', 'purchase_requisition', 'sale'],
    'update_xml': [
        "security/academics_security.xml",
        "wizard/enter_acceptance_password_view.xml",
        "wizard/enter_refusal_password_view.xml",
        "wizard/hold_run_batch_view.xml",
        "academics_registrar_view.xml",
        "academics_admission_view.xml",
        "academics_registrar_data.xml",
        "transcript_view.xml",
        "registrar_forms_view.xml",
        "wizard/duplicate_catalogue_view.xml",
        "wizard/duplicate_term_view.xml",
        "wizard/what_if_analysis.xml",
        "housing_view.xml",
        "academics_bursar_view.xml",
        "wizard/clearance_view.xml",
        "academics_report.xml",
        'security/ir.model.access.csv'
    ],
    'demo_xml': [
    ],
    'test': [

            ],
    'installable': True,
    'application': True,
    'active': False,
    'certificate': '',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
