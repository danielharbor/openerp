# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    $Id: account.py 1005 2005-07-25 08:41:42Z nicoe $
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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

class what_if_analysis(osv.osv_memory):
    _name = 'what.if.analysis'
    _description = 'What If Analysis'
    
    def _get_schools_and_programs(self, cr, uid, ids, name, arg, context=None):
        res = {}
        mc_obj = self.pool.get('aun.registrar.major.course')
        for student in self.browse(cr, SUPERUSER_ID, ids, context=None):
            res[student.id] = {}
            major_ids = [major.id for major in student.major_ids]
            major_course_ids = mc_obj.search(cr, uid, [('catalogue_id','=',student.catalogue_id.id),('major_id','in',major_ids),('level_id','=',student.level_id.id)], context=None)
            major_courses = mc_obj.browse(cr, uid, major_course_ids, context=None)
            school_ids = list(set([mc.school_id.id for mc in major_courses]))
            program_ids = list(set([mc.program_id.id for mc in major_courses]))
            res[student.id]['school_ids'] = [(6, 0, school_ids)]
            res[student.id]['program_ids'] = [(6, 0, program_ids)]
        return res
    
    def get_student_id(self, cr, uid, context=None):
        res = ""
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            res = user.partner_id.id
        return res
    
#     def get_catalogue_id(self, cr, uid, context=None):
#         res = ""
#         if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
#             student = self.pool.get('res.partner').browse(cr, uid, uid, context)
#             res = student.catalogue_id.id
#         return res
#     
#     def get_major_ids(self, cr, uid, context=None):
#         res = ""
#         if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
#             student = self.pool.get('res.partner').browse(cr, uid, uid, context)
#             res = [major.id for major in student.major_ids]
#         return res
#     
#     def get_minor_ids(self, cr, uid, context=None):
#         res = ""
#         if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
#             student = self.pool.get('res.partner').browse(cr, uid, uid, context)
#             res = [minor.id for minor in student.minor_ids]
#         return res
#     
#     def get_minor_ids(self, cr, uid, context=None):
#         res = ""
#         if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
#             student = self.pool.get('res.partner').browse(cr, uid, uid, context)
#             res = [minor.id for minor in student.minor_ids]
#         return res
    
    def on_change_student_id(self, cr, uid, ids, student_id, context=None):
        catalogue_id = major_ids = minor_ids = concentration_ids = level_id = fname = mname = lname = False
        if student_id:
            student = self.pool.get('res.partner').browse(cr, uid, student_id, context)
            fname = student.fname
            mname = student.mname
            lname = student.lname
            level_id = student.level_id.id
            catalogue_id = student.catalogue_id.id
            major_ids = [major.id for major in student.major_ids]
            minor_ids = [minor.id for minor in student.minor_ids]
            concentration_ids = [concentration.id for concentration in student.concentration_ids]
        return {'value': {'fname':fname, 'mname':mname, 'lname':lname,'catalogue_id': catalogue_id, 'major_ids':major_ids, 'minor_ids':minor_ids,
                          'level_id':level_id}}
        
    def on_change_majors(self, cr, uid, ids, student_id, catalogue_id, majors, minors, concentrations, context=None):
        if student_id:
            student = self.pool.get('res.partner').browse(cr, uid, student_id, context)
            major_ids = majors[0][2]
            minor_ids = minors[0][2]
            conc_obj = self.pool.get('registrar.concentration')
            mc_obj = self.pool.get('aun.registrar.major.course')
            catalogue = self.pool.get('aun.registrar.catalogue').browse(cr, uid, catalogue_id)
            cat_major_courses = catalogue.major_course_ids
            cat_major_ids = []
            for mc in cat_major_courses:
                cat_major_ids.append(mc.major_id.id)
            major_ids = [m for m in major_ids if m in cat_major_ids]
            minor_ids = [m for m in minor_ids if m in cat_major_ids]     
            concs = conc_obj.browse(cr, uid, concentrations[0][2])
            conc_ids = []
#             for conc in concs:
#                 for concentration in conc.conc_ids:
#                     if concentration.major_course_id.major_id.id in major_ids and conc.id not in conc_ids:
#                         conc_ids.append(conc.id)
            minor_ids = [m for m in minor_ids if m not in major_ids]
            maj_courses = []            
            major_course_ids = mc_obj.search(cr, uid, [('catalogue_id','=',catalogue_id),('major_id','in',major_ids),('level_id','=',student.level_id.id)], context=None)
            major_courses = mc_obj.browse(cr, uid, major_course_ids, context=None)
            maj_courses += major_courses
            school_ids = list(set([mc.school_id.id for mc in maj_courses]))
            program_ids = list(set([mc.program_id.id for mc in maj_courses]))
            return {'value': {'major_ids': [(6, 0, major_ids)],'minor_ids': [(6, 0, minor_ids)], 'concentration_ids': [(6, 0, conc_ids)], 'program_ids': [(6, 0, program_ids)], 'school_ids': [(6, 0, school_ids)]}}
        return {'value': {}}
    
    _columns = {
        'student_id': fields.many2one('res.partner', 'Student ID', ondelete="cascade", select=False, required=True, track_visibility="onchange", domain=[('student','=',True)]),
        'fname': fields.related('student_id', 'fname', type='char', relation='res.partner', string='First Name', readonly=True, store=False),
        'mname': fields.related('student_id', 'mname', type='char', relation='res.partner', string='Middle Name', readonly=True, store=False),
        'lname': fields.related('student_id', 'lname', type='char', relation='res.partner', string='Last Name', readonly=True, store=False),
        'level_id': fields.related('student_id', 'level_id', type="many2one", relation="aun.registrar.level", required=True, string='Level', readonly=True),
        'catalogue_id': fields.many2one('aun.registrar.catalogue', 'Catalogue', required=True),       
        'major_ids': fields.many2many('aun.registrar.major', 'rel_major_student_audit', 'student_id', 'major_id', 'Major(s)', required=True, domain="[('major_course_ids.catalogue_id','in',[catalogue_id]),('major_course_ids.program_id.level_id','in',[level_id])]"),
        'minor_ids': fields.many2many('aun.registrar.major', 'rel_minor_student_audit', 'student_id', 'major_id', 'Minor(s)'),
        'concentration_ids': fields.many2many('registrar.concentration', 'rel_concentration_student_audit', 'student_id', 'concentration_id', 'Concentration(s)', domain="[('major_course_id.major_id','in',major_ids[0][2]),('major_course_id.catalogue_id','in',[catalogue_id]),('major_course_id.program_id.level_id','in',[level_id])]"),    
        'school_ids':fields.function(_get_schools_and_programs, string='School(s)', type='many2many', method=True, multi='program_info', relation='aun.registrar.school', store=False),
        'program_ids': fields.function(_get_schools_and_programs, string='Program(s)', type='many2many', method=True, multi='program_info', relation='registrar.program', store=False),
    }
    
    _defaults={
       'student_id': get_student_id,
#        'catalogue_id': get_catalogue_id,
#        'major_ids': get_major_ids,
#        'minor_ids': get_minor_ids
    }
    
    def print_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        if not data['student_id'] or not data['major_ids']:
            raise osv.except_osv(_('Error!'), _('You must select a student and a major'))
        
        if context is None:
            context = {}
        active_ids = context.get('active_ids', [])
        if len(active_ids) > 0:
            datas = {'ids': active_ids}
        else:
            datas = {'ids': [data['student_id'][0]]}
            context['active_id'] = data['student_id'][0]
            context['active_ids'] = [data['student_id'][0]]
            context['check'] = False

        datas['model'] = 'res.partner'
        info = self.read(cr, uid, ids)[0]
        datas['form'] = info
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'what_if_analysis',
            'datas': datas,
            'context': context,
            }
    
what_if_analysis()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
