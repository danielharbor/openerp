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

import time
from datetime import datetime
from dateutil import relativedelta

from openerp.osv import fields, osv
from openerp.tools.translate import _

class hold_run_students(osv.osv_memory):

    _name ='hold.run.students'
    _description = 'Generate holds for all selected students'
    _columns = {
        'student_ids': fields.many2many('res.partner', 'hold_run_student_rel', 'hold_run_id', 'student_id', 'Students', domain=[('student','=',True)]),
    }
    
    def generate_holds(self, cr, uid, ids, context=None):
        student_obj = self.pool.get('res.partner')
        hold_obj = self.pool.get('aun.registrar.hold.assignment')
        run_obj = self.pool.get('hold.run')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        run_data = {}
        if context and context.get('active_id', False):
            run_data = run_obj.read(cr, uid, context['active_id'], ['start_date', 'end_date', 'hold_id', 'note'])
        from_date =  run_data.get('start_date', False)
        to_date = run_data.get('end_date', False)
        hold_id = run_data.get('hold_id', False)
        note = run_data.get('note', False)
        
        hold = self.pool.get('aun.registrar.hold').browse(cr, uid, hold_id[0])
        user = self.pool.get('res.users').browse(cr, uid, uid)
        if not(set(user.groups_id) & set(hold.group_ids)):
            groups = [g.name for g in hold.group_ids]
            if groups:
                raise osv.except_osv(_('Hold Restriction!'), _('Only ' + ['this group','these groups'][len(groups) > 1] + ' can generate the ' + hold.name + ': ' + ', '.join(groups)))
            else:
                raise osv.except_osv(_('Hold Restriction!'), _('Only the system administrator can generate the ' + hold.name))
        
        if not data['student_ids']:
            raise osv.except_osv(_("Warning!"), _("You must select at least one student to generate hold(s)."))
        for student in student_obj.browse(cr, uid, data['student_ids'], context=context):
            res = {
                'student_id': student.id,
                'hold_id': hold_id[0],
                'hold_run_id': context.get('active_id', False),
                'start_date': from_date,
                'end_date': to_date,
                'note': note,
                'state': 'active'
            }
            hold_obj.create(cr, uid, res, context=context)
        return {'type': 'ir.actions.act_window_close'}

hold_run_students()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
