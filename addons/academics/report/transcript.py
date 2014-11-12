#!/usr/bin/env python
#-*- coding:utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from openerp.osv import osv
from openerp import SUPERUSER_ID


from report import report_sxw
class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, SUPERUSER_ID, name, context)
        partner_ids = context['active_ids']
        partners = []
        for partner_id in partner_ids:
            holds = self.pool.get('res.partner').get_holds(cr, uid, partner_id)
            if holds['transcript'] or holds['grades']:
                partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
                partners.append(self._get_current_name(partner))
        if partners:
            if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
                raise osv.except_osv(('Holds!'), ('Your transcript is not available due to holds on your record.'))
            else: 
                raise osv.except_osv(('Holds!'), ('The following students have a hold restriction: '+ ', '.join(partners)))
        
        self.localcontext.update({
            'get_point': self._get_point,
            'get_transfer_point': self._get_transfer_point,
            'get_credit':self._get_credit,
            'get_transfer_credit':self._get_transfer_credit,
            'get_total_gpa_hrs':self._get_total_gpa_hrs,
            'get_total_earned_hrs':self._get_total_earned_hrs,
            'get_total_points':self._get_total_points,
            'get_total_gpa':self._get_total_gpa,
            'get_institution_gpa_hrs':self._get_institution_gpa_hrs,
            'get_institution_earned_hrs':self._get_institution_earned_hrs,
            'get_institution_points':self._get_institution_points,
            'get_transfer_gpa_hrs':self._get_transfer_gpa_hrs,
            'get_transfer_earned_hrs':self._get_transfer_earned_hrs,
            'get_transfer_points':self._get_transfer_points,
            'get_terms': self._get_terms,
            'get_transfer_terms': self._get_transfer_terms,
            'get_enrollment':self._get_enrollment,
            'get_total_earned_hrs_by_term':self._get_total_earned_hrs_by_term,
            'get_total_gpa_hrs_by_term':self._get_total_gpa_hrs_by_term,
            'get_total_points_by_term':self._get_total_points_by_term,
            'get_total_transfer_earned_hrs_by_term':self._get_total_transfer_earned_hrs_by_term,
            'get_total_transfer_gpa_hrs_by_term':self._get_total_transfer_gpa_hrs_by_term,
            'get_total_transfer_points_by_term':self._get_total_transfer_points_by_term,
            'get_majors':self._get_majors,
            'get_school':self._get_school,
            'get_current_name':self._get_current_name,
            'get_concentrations':self._get_concentrations,
            'get_current_programs': self._get_current_programs,
            'get_programs': self._get_programs,
            'get_term_majors': self._get_term_majors,
            'get_term_schools': self._get_term_schools,
            'get_term_honors': self._get_term_honors,
            'get_term_standing': self._get_term_standing,
            'get_transfer_institutions': self._get_transfer_institutions,
            'get_transfer_enrollment': self._get_transfer_enrollment,
            'get_levels': self._get_levels,
            'get_partners': self._get_partners,
            'get_levels_by_ids': self._get_levels_by_ids,
            'get_terms_by_ids':self._get_terms_by_ids,
            'get_transfer_terms_by_ids':self._get_transfer_terms_by_ids
        })


    def _get_partners(self, partner_id):
        if partner_id:
            return self.pool.get('res.partner').browse(self.cr, self.uid, [partner_id])
        return []
    
    def _get_levels(self, partner_id):
        levels = []
        ids = self.pool.get('level.gpa').search(self.cr, self.uid, [('student_id', '=', partner_id)])
        if ids:
            level_gpas = self.pool.get('level.gpa').browse(self.cr, self.uid, ids)
            for level_gpa in level_gpas:
                if level_gpa.level_id not in levels:
                    levels.append(level_gpa.level_id)
        return levels
    
    def _get_levels_by_ids(self, level_ids):
        if level_ids:
            return self.pool.get('aun.registrar.level').browse(self.cr, self.uid, level_ids)
        return []
    
    def _get_terms(self, partner_id, level_id):
        term_ids = []
        ids = self.pool.get('aun.registrar.enrollment').search(self.cr, self.uid, [('student_id', '=', partner_id),('section_id.level_id', '=', level_id), ('state','=','registered'),('lab','=',False)])
        enrollments = self.pool.get('aun.registrar.enrollment').browse(self.cr, self.uid, ids)
        for term in enrollments:
            if term.section_id.term_id not in term_ids:
                term_ids.append(term.section_id.term_id)
        return term_ids
    
    def _get_terms_by_ids(self, partner_id, level_id, trm_ids):
        term_ids = []
        if trm_ids:
            ids = self.pool.get('aun.registrar.enrollment').search(self.cr, self.uid, [('student_id', '=', partner_id),('section_id.term_id', 'in', trm_ids),('section_id.level_id', '=', level_id), ('state','=','registered'),('lab','=',False)])
            enrollments = self.pool.get('aun.registrar.enrollment').browse(self.cr, self.uid, ids)
            for term in enrollments:
                if term.section_id.term_id not in term_ids:
                    term_ids.append(term.section_id.term_id)
            return term_ids
        else:
            return self._get_terms(partner_id, level_id)
    
    def _get_transfer_terms(self, partner_id, level_id):
        term_ids = []
        ids = self.pool.get('transfer.course.equivalent').search(self.cr, self.uid, [('student_id', '=', partner_id),('level_id', '=', level_id)])
        transfers = self.pool.get('transfer.course.equivalent').browse(self.cr, self.uid, ids)
        for transfer in transfers:
            if transfer.term_id not in term_ids:
                term_ids.append(transfer.term_id)
        return term_ids
    
    def _get_transfer_terms_by_ids(self, partner_id, level_id, trm_ids):
        term_ids = []
        if trm_ids:
            ids = self.pool.get('transfer.course.equivalent').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', 'in', trm_ids),('level_id', '=', level_id)])
            transfers = self.pool.get('transfer.course.equivalent').browse(self.cr, self.uid, ids)
            for transfer in transfers:
                if transfer.term_id not in term_ids:
                    term_ids.append(transfer.term_id)
            return term_ids
        else:
            return self._get_transfer_terms(partner_id, level_id)

    def _get_enrollment(self, partner_id, term_id, level_id):
        ids = self.pool.get('aun.registrar.enrollment').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('section_id.level_id', '=', level_id), ('state','=','registered'),('lab','=',False)])
        enrollments = self.pool.get('aun.registrar.enrollment').browse(self.cr, self.uid, ids)
        return enrollments
    
    def _get_transfer_enrollment(self, partner_id, term_id, level_id):
        ids = self.pool.get('transfer.course.equivalent').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)])
        transfers = self.pool.get('transfer.course.equivalent').browse(self.cr, self.uid, ids)
        return transfers

    def _get_total_earned_hrs(self, partner_id, level_id):
        earned_hrs = 0
        ids = self.pool.get('level.gpa').search(self.cr, self.uid, [('student_id','=',partner_id),('level_id','=',level_id)])
        if ids:
            gpa = self.pool.get('level.gpa').browse(self.cr, self.uid, ids)[0]
            earned_hrs = gpa.o_earned_hours
        return '{0:.2f}'.format(earned_hrs)
    
    def _get_institution_earned_hrs(self, partner_id, level_id):
        earned_hrs = 0
        ids = self.pool.get('level.gpa').search(self.cr, self.uid, [('student_id','=',partner_id),('level_id','=',level_id)])
        if ids:
            gpa = self.pool.get('level.gpa').browse(self.cr, self.uid, ids)[0]
            earned_hrs = gpa.earned_hours
        return '{0:.2f}'.format(earned_hrs)
    
    def _get_transfer_earned_hrs(self, partner_id, level_id):
        earned_hrs = 0
        ids = self.pool.get('level.gpa').search(self.cr, self.uid, [('student_id','=',partner_id),('level_id','=',level_id)])
        if ids:
            gpa = self.pool.get('level.gpa').browse(self.cr, self.uid, ids)[0]
            earned_hrs = gpa.t_earned_hours
        return '{0:.2f}'.format(earned_hrs)

    def _get_total_earned_hrs_by_term(self, partner_id, term_id, level_id):
        earned_hrs = 0
        ids = self.pool.get('gpa.info').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)]) 
        if ids:
            gpa = self.pool.get('gpa.info').browse(self.cr, self.uid, ids)[0]
            earned_hrs = gpa.earned_hours
        return '{0:.2f}'.format(earned_hrs)
    
    def _get_total_transfer_earned_hrs_by_term(self, partner_id, term_id, level_id):
        earned_hrs = 0
        ids = self.pool.get('gpa.info').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)]) 
        if ids:
            gpa = self.pool.get('gpa.info').browse(self.cr, self.uid, ids)[0]
            earned_hrs = gpa.t_earned_hours
        return '{0:.2f}'.format(earned_hrs)

    
    def _get_total_gpa_hrs(self, partner_id, level_id):
        gpa_hrs = 0
        ids = self.pool.get('level.gpa').search(self.cr, self.uid, [('student_id','=',partner_id),('level_id','=',level_id)])
        if ids:
            partner = self.pool.get('level.gpa').browse(self.cr, self.uid, ids)[0]
            gpa_hrs = partner.o_gpa_hours
        return '{0:.2f}'.format(gpa_hrs)
    
    def _get_institution_gpa_hrs(self, partner_id, level_id):
        gpa_hrs = 0
        ids = self.pool.get('level.gpa').search(self.cr, self.uid, [('student_id','=',partner_id),('level_id','=',level_id)])
        if ids:
            partner = self.pool.get('level.gpa').browse(self.cr, self.uid, ids)[0]
            gpa_hrs = partner.gpa_hours
        return '{0:.2f}'.format(gpa_hrs)
    
    def _get_transfer_gpa_hrs(self, partner_id, level_id):
        gpa_hrs = 0
        ids = self.pool.get('level.gpa').search(self.cr, self.uid, [('student_id','=',partner_id),('level_id','=',level_id)])
        if ids:
            partner = self.pool.get('level.gpa').browse(self.cr, self.uid, ids)[0]
            gpa_hrs = partner.t_gpa_hours
        return '{0:.2f}'.format(gpa_hrs)

    def _get_total_gpa_hrs_by_term(self, partner_id, term_id, level_id):
        gpa_hrs = 0
        ids = self.pool.get('gpa.info').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)]) 
        if ids:
            gpa = self.pool.get('gpa.info').browse(self.cr, self.uid, ids)[0]
            gpa_hrs = gpa.gpa_hours
        return '{0:.2f}'.format(gpa_hrs)
    
    def _get_total_transfer_gpa_hrs_by_term(self, partner_id, term_id, level_id):
        gpa_hrs = 0
        ids = self.pool.get('gpa.info').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)]) 
        if ids:
            gpa = self.pool.get('gpa.info').browse(self.cr, self.uid, ids)[0]
            gpa_hrs = gpa.t_gpa_hours
        return '{0:.2f}'.format(gpa_hrs)

    def _get_total_points(self, partner_id, level_id):
        points = 0
        ids = self.pool.get('level.gpa').search(self.cr, self.uid, [('student_id','=',partner_id),('level_id','=',level_id)])
        if ids:
            gpa = self.pool.get('level.gpa').browse(self.cr, self.uid, ids)[0]
            points = gpa.o_quality_points
        return '{0:.2f}'.format(points)
    
    def _get_institution_points(self, partner_id, level_id):
        points = 0
        ids = self.pool.get('level.gpa').search(self.cr, self.uid, [('student_id','=',partner_id),('level_id','=',level_id)])
        if ids:
            gpa = self.pool.get('level.gpa').browse(self.cr, self.uid, ids)[0]
            points = gpa.quality_points
        return '{0:.2f}'.format(points)
    
    def _get_transfer_points(self, partner_id, level_id):
        points = 0
        ids = self.pool.get('level.gpa').search(self.cr, self.uid, [('student_id','=',partner_id),('level_id','=',level_id)])
        if ids:
            gpa = self.pool.get('level.gpa').browse(self.cr, self.uid, ids)[0]
            points = gpa.t_quality_points
        return '{0:.2f}'.format(points)

    def _get_total_points_by_term(self, partner_id, term_id, level_id):
        quality_points = 0
        ids = self.pool.get('gpa.info').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)]) 
        if ids:
            gpa = self.pool.get('gpa.info').browse(self.cr, self.uid, ids)[0]
            quality_points = gpa.quality_points
        return '{0:.2f}'.format(quality_points)
    
    def _get_total_transfer_points_by_term(self, partner_id, term_id, level_id):
        quality_points = 0
        ids = self.pool.get('gpa.info').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)]) 
        if ids:
            gpa = self.pool.get('gpa.info').browse(self.cr, self.uid, ids)[0]
            quality_points = gpa.t_quality_points
        return '{0:.2f}'.format(quality_points)

    def _get_total_gpa(self, points, gpa_hrs):
        if(gpa_hrs == '0.00'):
            return gpa_hrs
        value = float(points)/float(gpa_hrs)
        if(value == 0):
            return '0.00'
        return '{0:.2f}'.format(value)   

    def _get_point(self, enrollment_id):
        if not enrollment_id.grade:
            return '{0:.2f}'.format(0)
        points= [0, enrollment_id.grade.quality_points * enrollment_id.credit][enrollment_id.repeat != 'E']
        return '{0:.2f}'.format(points)
    
    def _get_transfer_point(self, transfer_id):
        if not transfer_id.grade_id:
            return '{0:.2f}'.format(0)
        points= [0, transfer_id.grade_id.quality_points * transfer_id.credit][transfer_id.repeat != 'E']
        return '{0:.2f}'.format(points)
     
    def _get_credit(self, enrollment_id):
        if not enrollment_id.grade:
            return '{0:.2f}'.format(enrollment_id.credit)
        credit = [0, enrollment_id.credit][enrollment_id.grade.earned and enrollment_id.repeat != 'E']
        return '{0:.2f}'.format(float(credit))

    def _get_transfer_credit(self, transfer_id):
        if not transfer_id.grade_id:
            return '{0:.2f}'.format(transfer_id.credit)
        credit = [0, transfer_id.credit][transfer_id.grade_id.earned and transfer_id.repeat != 'E']
        return '{0:.2f}'.format(float(credit))
    
    def _get_majors(self, majors):
        return ', '.join([major.name for major in majors])
    
    def _get_schools(self, schools):
        return ', '.join([school.name.name for school in schools])

    def _get_school(self, partner):    
        schools = []
        school_ids = self.pool.get('res.partner').browse(self.cr, self.uid, partner.id)._get_schools_and_programs(self.cr, self.uid)[partner.id]['school_ids'][0][2]
        if school_ids:
            schools = self.pool.get('aun.registrar.school').browse(self.cr, self.uid, school_ids)          
        return ', '.join([school.name.name for school in schools])       
    
    def _get_current_name(self, partner):
        return (partner.fname or "") + " " + (partner.mname or " ")+ " " + (partner.lname or "") 

    def _get_concentrations(self, concentrations):
        return ', '.join([concentration.name for concentration in concentrations])
    
    def _get_current_programs(self, partner):
        programs = []
        program_ids = self.pool.get('res.partner').browse(self.cr, self.uid, partner.id)._get_schools_and_programs(self.cr, self.uid)[partner.id]['program_ids'][0][2]
        if program_ids:
            programs = self.pool.get('registrar.program').browse(self.cr, self.uid, program_ids)          
        return ', '.join([program.title+'('+program.name+')' for program in programs])
    
    def _get_programs(self, partner):
        mc_obj = self.pool.get('aun.registrar.major.course')
        major_ids = [major.id for major in partner.major_ids]
        major_course_ids = mc_obj.search(self.cr, self.uid, [('catalogue_id','=',partner.catalogue_id.id),('major_id','in',major_ids),('level_id','=',partner.level_id.id)], context=None)
        major_courses = mc_obj.browse(self.cr, self.uid, major_course_ids, context=None)
        return ', '.join(list(set([mc.program_id.name+' in '+mc.major_id.name for mc in major_courses])))
  
    def _get_term_majors(self, partner_id, term_id, level_id):
        ids = self.pool.get('gpa.info').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)]) 
        if ids:
            gpa = self.pool.get('gpa.info').browse(self.cr, self.uid, ids)[0]
            if gpa.major_ids:
                return self._get_majors(gpa.major_ids)
        return "Major Undeclared"
    
    def _get_term_schools(self, partner_id, term_id, level_id):
        ids = self.pool.get('gpa.info').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)]) 
        if ids:
            gpa = self.pool.get('gpa.info').browse(self.cr, self.uid, ids)[0]
            if gpa.school_ids:
                return self._get_schools(gpa.school_ids)
        return ""
    
    def _get_term_honors(self, partner_id, term_id, level_id):
        ids = self.pool.get('gpa.info').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)]) 
        if ids:
            gpa = self.pool.get('gpa.info').browse(self.cr, self.uid, ids)[0]
            if gpa.honors_id:
                return gpa.honors_id.name
        return ""
    
    def _get_term_standing(self, partner_id, term_id, level_id):
        ids = self.pool.get('gpa.info').search(self.cr, self.uid, [('student_id', '=', partner_id),('term_id', '=', term_id),('level_id', '=', level_id)]) 
        if ids:
            gpa = self.pool.get('gpa.info').browse(self.cr, self.uid, ids)[0]
            if gpa.standing_id:
                return gpa.standing_id.name
        return "No Standing"
    
    def _get_transfer_institutions(self, partner_id, level_id):
        ids = self.pool.get('transfer.info').search(self.cr, self.uid, [('student_id', '=', partner_id), ('level_id','=',level_id)]) 
        if ids:
            return self.pool.get('transfer.info').browse(self.cr, self.uid, ids)
        return False
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
