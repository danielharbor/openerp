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
from datetime import date

class duplicate_term(osv.osv_memory):
    _name = "duplicate.term"
    _description = "Duplicate Term"
        
    def _populate_year(self, cr, uid, context=None):
        current_year = date.today().year
        return [(str(i), str(i)) for i in range(current_year-3, current_year+10)]
    
    _columns = {
        'orig_term': fields.many2one('aun.registrar.term', 'Original Term', help='Term to be duplicated', required=True),
        'copy_term': fields.many2one('aun.registrar.term', 'Duplicate Term', help='Term to which information is copied', required=True),
        'sections': fields.many2many('aun.registrar.section', 'rel_duplicate_section', 'dup_id', 'section_id', 'Section(s)'),
        'capacity': fields.char('Default Capacity', size=8),
        'faculty': fields.boolean('Faculty'),
        'duration': fields.boolean('Duration'),
        'location': fields.boolean('Location'),
        'labs': fields.boolean('Labs')
    }

    def on_change_orig_term(self, cr, uid, ids, orig_term_id, context=None):
        copy_term_ids = []
        if orig_term_id:
            term_obj = self.pool.get('aun.registrar.term')
            orig_term_code = term_obj.browse(cr, uid, orig_term_id).code
            for term_id in term_obj.search(cr, uid, []):
                if int(term_obj.browse(cr, uid, term_id).code) > int(orig_term_code):
                    copy_term_ids.append(term_id)
        return {'domain': {'copy_term': [('id','in',copy_term_ids)]}, 'value': {'copy_term': False, 'sections': False}}
    
    def duplicate_term_open_window(self, cr, uid, ids, context=None):
        dt = self.browse(cr, uid, ids, context = context)[0]
        if dt.capacity:
            try:
                int(dt.capacity)
            except:
                raise osv.except_osv(('Invalid Capacity!'), ('Enter a number'))
        
        section_obj = self.pool.get('aun.registrar.section')
        if dt.sections:
            section_ids = [s.id for s in dt.sections]
        else:
            section_ids = section_obj.search(cr, uid, [('term_id','=',dt.orig_term.id)])
                  
        for section_id in section_ids:
            defaults = {'term_id': dt.copy_term.id}
            if dt.capacity:                
                defaults['max_size'] = int(dt.capacity)
            if not dt.faculty:
                defaults['faculty'] = False
            if not dt.duration:
                defaults['duration_id'] = False
            if not dt.location:
                defaults['location_id'] = False
            if not dt.labs:
                defaults['no_of_labs'] = 0
                defaults['labs'] = False
               
            ctx = dict(context, duplicate = True)
            section_obj.copy(cr, uid, section_id, defaults, context=ctx)
           
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'academics', 'registrar_section_action')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        return result

duplicate_term()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
