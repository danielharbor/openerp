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

class duplicate_catalogue(osv.osv_memory):
    _name = "duplicate.catalogue"
    _description = "Duplicate Catalogue"
        
    def _populate_year(self, cr, uid, context=None):
        current_year = date.today().year
        return [(str(i), str(i)) for i in range(current_year-2, current_year+10)]
    
    _columns = {
        'catalogue': fields.many2one('aun.registrar.catalogue', 'Original Catalogue', help='Catalogue to be duplicated', required=True),
        'start_year': fields.selection(_populate_year, 'Start Year', required=True),
        'end_year': fields.selection(_populate_year, 'End Year', required=True)
    }

    def duplicate_catalogue_open_window(self, cr, uid, ids, context=None):
        dc = self.browse(cr, uid, ids, context = context)[0]
        catalogue_obj = self.pool.get('aun.registrar.catalogue')
        ctx = dict(context, duplicate = True)
        catalogue_obj.copy(cr, uid, dc.catalogue.id, {'start_year': dc.start_year, 'end_year': dc.end_year}, context=ctx)
        catalogue_id = catalogue_obj.search(cr, uid, [('start_year','=',dc.start_year), ('end_year','=',dc.end_year)])[0]
        
        repeat_obj = self.pool.get('aun.registrar.repeat')
        repeat_ids = repeat_obj.search(cr, uid, [('catalogue_id','=',dc.catalogue.id)])
        for repeat_id in repeat_ids:
            repeat_obj.copy(cr, uid, repeat_id, {'catalogue_id': catalogue_id})       
        
        prereq_obj = self.pool.get('aun.registrar.cat.prerequisite')
        prereq_ids = prereq_obj.search(cr, uid, [('catalogue_id','=',dc.catalogue.id)])
        for prereq_id in prereq_ids:
            prereq_obj.copy(cr, uid, prereq_id, {'catalogue_id': catalogue_id})
            
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'academics', 'registrar_catalogue_action')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        return result

duplicate_catalogue()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
