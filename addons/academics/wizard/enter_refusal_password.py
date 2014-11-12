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

from openerp.osv import fields, osv
from openerp import SUPERUSER_ID

class enter_refusal_password(osv.osv_memory):
    _name = "enter.refusal.password"
    _description = "Enter Password"
    
    _columns = {
        'password': fields.char('Enter Password', size=16, required=True)
    }
      
    def refuse_applicant(self, cr, uid, ids, context=None):
        ap_obj = self.pool.get('acceptance.password')
        password = self.browse(cr, SUPERUSER_ID, ids)[0].password
        curr_password_ids = ap_obj.search(cr, SUPERUSER_ID, [])
        if not curr_password_ids:
            raise osv.except_osv(('No password set!'), ('Click on the change password link to create a password'))
        curr_password = ap_obj.browse(cr, SUPERUSER_ID, curr_password_ids)[0].new_password
        if password != curr_password:
            raise osv.except_osv(('Invalid!'), ('The password is incorrect'))
        
        return self.pool.get('aun.applicant').case_refuse(cr, uid, context['active_ids'], context)

enter_refusal_password()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
