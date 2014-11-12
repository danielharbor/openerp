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

from report import report_sxw
from openerp import SUPERUSER_ID
from openerp.osv import osv

SUBJECT_MAX_SIZE=4
REP_COURSE_LEVEL='X'

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, SUPERUSER_ID, name, context)
        partner_ids = context['active_ids']
        partners = []
        partner_catalogs = []
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student") and 'check' not in context:
            raise osv.except_osv(('Catalog Issue!'), ('You cannot perform degree audit on your record.'))
        for partner_id in partner_ids:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if not partner.catalogue_id and 'check' not in context:
                partner_catalogs.append(self._get_current_name(partner))
            holds = self.pool.get('res.partner').get_holds(cr, uid, partner_id)
            if holds['transcript'] or holds['grades']:
                partners.append(self._get_current_name(partner))
        if partner_catalogs:
            if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
                raise osv.except_osv(('Catalog Issue!'), ('Your degree audit is not available due you do not have a catalog.'))
            else:
                raise osv.except_osv(('Catalog Issue!'), ('The following student(s) have a catalog issue: '+ ', '.join(partners)))
        if partners:
            if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
                raise osv.except_osv(('Holds!'), ('Your degree audit is not available due to holds on your record.'))
            else: 
                raise osv.except_osv(('Holds!'), ('The following student(s) have a hold restriction: '+ ', '.join(partners)))
        self.localcontext.update({
            'get_categories':self._get_categories,
            'get_majors':self._get_majors,
            'get_concentrations':self._get_concentrations,
            'get_current_name':self._get_current_name,
            'get_school':self._get_school,
            'get_current_programs': self._get_current_programs,
            'get_programs': self._get_programs,
            'courses_to_display': self._courses_to_display,
            'check_bool':self._check_bool,
            'other_enrollments':self._other_enrollments,
            'get_catalogue': self._get_catalogue,
            'get_major_ids':self._get_major_ids,
            'get_concentration_ids': self._get_concentration_ids,
            'get_student':self._get_student,
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
        })
        self.COURSES=[]
    
    def _get_student(self, student_id):
            return self.pool.get('res.partner').browse(self.cr, self.uid, [student_id])[0]

    def _get_catalogue(self, partner):
        return partner.catalogue_id.start_year + '-' + partner.catalogue_id.end_year
    
    def _format_credit(self, credit):
        return '{0:.2f}'.format(float(credit)) 
    
    def _get_major_req(self, partner, major, catalogue_id, level_id):
        courses = []
        ids = self.pool.get('aun.registrar.major.course').search(self.cr, self.uid, [('major_id', '=', major.id), ('level_id','=',level_id), ('catalogue_id', '=', catalogue_id)])
        if ids:
            major_courses = self.pool.get('aun.registrar.major.course').browse(self.cr, self.uid, ids)
            for major_course in major_courses:
                for course in major_course.course_ids:
                    courses.append(course)
        return courses
    
    def _get_minor_req(self, partner, minor, catalogue_id, level_id):
        courses = []
        ids = self.pool.get('aun.registrar.major.course').search(self.cr, self.uid, [('major_id', '=', minor.id), ('level_id','=',level_id), ('catalogue_id', '=', catalogue_id)])
        if ids:
            major_courses = self.pool.get('aun.registrar.major.course').browse(self.cr, self.uid, ids)
            for major_course in major_courses:
                for course in major_course.minor_course_ids:
                    courses.append(course)
        return courses
    
    def _get_concentration_req(self, partner, concentration):
        courses = []
        ids = self.pool.get('registrar.concentration').search(self.cr, self.uid, [('id', '=', concentration.id)])
        if ids:
            concentration_courses = self.pool.get('registrar.concentration').browse(self.cr, self.uid, ids)
            for concentration_course in concentration_courses:
                for course in concentration_course.course_ids:
                    courses.append(course)
        return courses
    
    def _get_general_req(self, category, major_ids, catalogue_id, level_id):
        courses = categories = []
        has_major_category=False
        has_concentration_category = False
        if major_ids and major_ids[0]:
            if major_ids[0]._table_name == 'registrar.concentration':
                for concentration in major_ids:
                    for cat in concentration.category_ids:
                        if cat.name.id == category.name.id:
                            for category_course in cat.course_ids:
                                courses.append(category_course)
                            has_concentration_category = True
                            
        if not has_concentration_category:
            if major_ids:
                major_ids = [major.id for major in major_ids]
                ids = self.pool.get('aun.registrar.major.course').search(self.cr, self.uid, [('category_ids', '!=', False), ('major_id','in', major_ids), ('level_id', '=', level_id), ('catalogue_id', '=', catalogue_id)])
                if ids:
                    major_courses = self.pool.get('aun.registrar.major.course').browse(self.cr, self.uid, ids)
                    for major_course in major_courses:
                        for cat in major_course.category_ids:
                            if cat.name.id == category.name.id:
                                for category_course in cat.course_ids:
                                    courses.append(category_course) 
                                has_major_category = True

        if not has_major_category and not has_concentration_category:
            ids = self.pool.get('registrar.cat.category').search(self.cr, self.uid, [('id', '=', category.id), ('level_id', '=', level_id), ('catalogue_id', '=', catalogue_id)])
            if ids:
                categories = self.pool.get('registrar.cat.category').browse(self.cr, self.uid, ids)
                for category in categories:
                    for category_course in category.course_ids:
                        courses.append(category_course)  
        return courses
    
    def _get_course(self, course_id):
        if course_id:
            return self.pool.get('aun.registrar.course').browse(self.cr, SUPERUSER_ID,[int(course_id)])
        return False
    
    def _get_course_by_subject(self,subject, credit, level_from=False, level_to=False):
        courses = []
        if level_from and level_to:
            course_ids =self.pool.get('aun.registrar.course').search(self.cr, self.uid, [('subject_id','=',subject.id), ('credit_low','>=',credit), ('code','>=',level_from), ('code','<=',level_to)])
        elif level_from:
            course_ids =self.pool.get('aun.registrar.course').search(self.cr, self.uid, [('subject_id','=',subject.id), ('credit_low','>=',credit), ('code','>=',level_from)])
        elif level_to:
            course_ids =self.pool.get('aun.registrar.course').search(self.cr, self.uid, [('subject_id','=',subject.id), ('credit_low','>=',credit), ('code','<=',level_to)])
        else:
            course_ids =self.pool.get('aun.registrar.course').search(self.cr, self.uid, [('subject_id','=',subject.id), ('credit_low','>=',credit)])
        if course_ids:     
            courses = self.pool.get('aun.registrar.course').browse(self.cr, self.uid,course_ids)
            for course in courses:
                if course.equivalents:
                    for equivalent in course.equivalents:
                        courses.append(equivalent)
        return courses
        
    def _check_bool(self, variable):
        if variable in ("True", "False", False, True):
            return True
        return False
    
    def _get_subject_or_level_from_to(self, major_course):
        if major_course.level_from:
            level_from = major_course.level_from[0]+REP_COURSE_LEVEL+REP_COURSE_LEVEL
            level_to=''
            if major_course.level_to:
                level_to = '/'+major_course.level_to[0]+REP_COURSE_LEVEL+REP_COURSE_LEVEL
            return major_course.subject_id.name+' '+level_from+level_to
        return major_course.subject_id.name
    
    def _courses_to_display(self, partner, major, major_ids, catalogue_id, level_id, is_minor=False,is_concentration=False, is_category=False):
        if is_concentration:
            major_courses = self._get_concentration_req(partner, major) 
        elif is_minor:
            major_courses = self._get_minor_req(partner, major, catalogue_id, level_id)
        elif is_category:
            major_courses = self._get_general_req(major, major_ids, catalogue_id, level_id) 
        else:
            major_courses = self._get_major_req(partner, major, catalogue_id, level_id)
        courses=[True, []]
        i=0
        while i < len(major_courses):
            course = {'name':'', 'grade':'','course':'','credit':'','semester':'','status':0}
            course['name']=major_courses[i].course_id.name or self._get_subject_or_level_from_to(major_courses[i])
            course['grade_requirement']=major_courses[i].grade_requirement or major_courses[i].major_course_id.grade_requirement or major_courses[i].cat_id.grade_requirement

            j = i+1
            if j < len(major_courses):
                while(j<len(major_courses) and major_courses[j].andor not in ['&', False, '']):
                    if major_courses[j].course_id:
                        course['name'] +=', ' +major_courses[j].course_id.name
                    elif major_courses[j].level_from:
                        course['name'] += ', ' +self._get_subject_or_level_from_to(major_courses[j])
                    elif major_courses[j].subject_id:
                        course['name'] +=', ' +major_courses[j].subject_id.name
                    j+=1            
            course_names = course['name'].split(', ')
            for course_name in course_names:
                course_name = course_name.strip(" ")
                if(len(course_name)>SUBJECT_MAX_SIZE and REP_COURSE_LEVEL not in course_name):
                    if str(course_name) not in self.COURSES:
                        crses = self._get_courses_by_name(course_name)
                        for crse in crses:
                            enrollment = self._get_enrollment(partner, crse)
                            transfer_enrollment = self._get_transfer_enrollment(partner, crse)
                            course['course'] = crse.name
                            course['credit'] = self._format_credit(crse.credit_low)
                            if enrollment:
                                course['semester'] = enrollment.section_id.term_id.name.name +' '+enrollment.section_id.term_id.year
                                if enrollment.grade:
                                    course['grade'] = enrollment.grade.name
                                    if(self._check_grade_requirement(partner, crse, course['grade_requirement'])):
                                        course['status'] = 2
                                        self.COURSES.append(str(course_name))
                                        break
                                else:
                                    course['status'] = 1
                                    self.COURSES.append(str(crse.name))
                                    break
                            elif transfer_enrollment:
                                course['semester'] = transfer_enrollment.term_id.name.name + ' ' + transfer_enrollment.term_id.year
                                course['grade'] = transfer_enrollment.grade_id.name
                                if(self._check_grade_requirement(partner, crse, course['grade_requirement'])):
                                    course['status'] = 2
                                    self.COURSES.append(str(course_name))
                                    break
                else:
                    subj = self._get_subject_by_name(course_name[:SUBJECT_MAX_SIZE].strip(" "))
                    level_from = level_to = False
                    if course_name[SUBJECT_MAX_SIZE:]:
                        c_code = course_name[SUBJECT_MAX_SIZE:].split("/")
                        if len(c_code) == 2:
                            level_from = c_code[0].replace(REP_COURSE_LEVEL, '0')
                            level_to = c_code[1].replace(REP_COURSE_LEVEL, '9')
                        else:
                            level_from = c_code[0].replace(REP_COURSE_LEVEL, '0')
                    subject_courses = self._get_course_by_subject(subj, major_courses[j-1].credit, level_from, level_to)
                    for crse in subject_courses:
                        if str(crse.name) not in self.COURSES:
                            enrollment = self._get_enrollment(partner, crse)
                            transfer_enrollment = self._get_transfer_enrollment(partner, crse)
                            course['credit'] = self._format_credit(crse.credit_low)
                            if enrollment:
                                course['course'] = crse.name
                                course['credit'] = self._format_credit(crse.credit_low)
                                course['semester'] = enrollment.section_id.term_id.name.name +' '+enrollment.section_id.term_id.year
                                if enrollment.grade:
                                    course['grade'] = enrollment.grade.name
                                    if(self._check_grade_requirement(partner, crse, course['grade_requirement'])):
                                        course['status'] = 2
                                        self.COURSES.append(str(crse.name))
                                        break
                                else:
                                    course['status'] = 1
                                    self.COURSES.append(str(crse.name))
                                    break
                            elif transfer_enrollment:
                                course['semester'] = transfer_enrollment.term_id.name.name + ' ' + transfer_enrollment.term_id.year
                                course['grade'] = transfer_enrollment.grade_id.name
                                if(self._check_grade_requirement(partner, crse, course['grade_requirement'])):
                                    course['status'] = 2
                                    self.COURSES.append(str(course_name))
                                    break
                    if course['status'] in [1,2]:
                        break
            courses[1].append(course)
            i=j
        for course in courses[1]:
            if course['status'] is not 2:
                courses[0]=0  
        return courses
    
    def _other_enrollments(self, partner):
        courses=[True, []]
        ids = self.pool.get('aun.registrar.enrollment').search(self.cr, self.uid, [('student_id', '=', partner.id),('repeat','not in',['E']), ('state','=','registered'),('lab','=',False)])
        if ids:
            enrollments = self.pool.get('aun.registrar.enrollment').browse(self.cr, self.uid, ids)
            for enrollment in enrollments:
                course = {'name':'', 'grade':'','credit':'','semester':'', 'status':2, 'course':''}
                if str(enrollment.section_id.course_id.name.strip(" ")) not in self.COURSES:
                    course['name']=enrollment.section_id.course_id.name
                    course['course']=enrollment.section_id.course_id.name
                    course['credit'] = self._format_credit(enrollment.section_id.course_id.credit_low)
                    course['semester'] = enrollment.section_id.term_id.name.name +' '+enrollment.section_id.term_id.year
                    if enrollment.grade:
                        course['grade'] = enrollment.grade.name
                    else:
                        course['status'] = 1
                    courses[1].append(course)
        return courses
        
    def _get_courses_by_name(self, course_name):
        courses = []
        id = self.pool.get('aun.registrar.course').search(self.cr,self.uid,[('name','=',course_name)])
        if id:
            courses = self.pool.get('aun.registrar.course').browse(self.cr, self.uid,id)
            for course in courses:
                if course.equivalents:
                    for equivalent in course.equivalents:
                        courses.append(equivalent) 
        return courses
    
    def _get_subject_by_name(self, subject_name):
        id = self.pool.get('course.subject').search(self.cr,self.uid,[('name','=',subject_name)])
        if id:
            return self.pool.get('course.subject').browse(self.cr, self.uid,id)[0]
        return False
    
    def _check_grade_requirement(self, partner, course, default_grade):
        grade=0
        check_grade=True
        if default_grade:
            grade=default_grade.numeric_value
        if course:
            course_grade = self._get_grade(partner, course)
            if not course_grade or (course_grade and grade > course_grade.numeric_value):   
                check_grade=False 
        return check_grade
            
    def _get_categories(self, partner, catalogue_id, level_id):
        categories=[]
        ids = self.pool.get('registrar.cat.category').search(self.cr,self.uid,[('level_id','=',level_id),('catalogue_id','=',catalogue_id)])
        if ids:
            c = self.pool.get('registrar.cat.category').browse(self.cr, self.uid, ids)
            for category in c:
                categories.append(category)
        return categories

    def _get_semester(self, partner, course):
        id = self.pool.get('aun.registrar.enrollment').search(self.cr, self.uid, [('student_id', '=', partner.id),('course_id', '=', course.id), ('state','=','registered'),('lab','=',False)])
        if id:
            enrollment = self.pool.get('aun.registrar.enrollment').browse(self.cr, self.uid, id)[0]
            term_id = enrollment.section_id.term_id
            return term_id.name.name + ' ' + term_id.year
        return False

    def _get_grade(self, partner, course):
        id = self.pool.get('aun.registrar.enrollment').search(self.cr, self.uid, [('student_id', '=', partner.id),('course_id', '=', course.id),('repeat','not in',['E']), ('state','=','registered'),('lab','=',False)])
        if id:
            enrollment = self.pool.get('aun.registrar.enrollment').browse(self.cr, self.uid, id)[0]
            return enrollment.grade
        else:
            id = self.pool.get('transfer.course.equivalent').search(self.cr, self.uid, [('student_id', '=', partner.id),('course_id', '=', course.id),('repeat','not in',['E'])])
            if id:
                transfer = self.pool.get('transfer.course.equivalent').browse(self.cr, self.uid, id)[0]
                return transfer.grade_id 
        return False
    
    def _get_enrollment(self, partner, course):
        id = self.pool.get('aun.registrar.enrollment').search(self.cr, self.uid, [('student_id', '=', partner.id),('course_id', '=', course.id),('repeat','not in',['E']), ('state','=','registered'),('lab','=',False)])
        if id:
            enrollment = self.pool.get('aun.registrar.enrollment').browse(self.cr, self.uid, id)[0]
            return enrollment
        return False
    
    def _get_transfer_enrollment(self, partner, course):
        id = self.pool.get('transfer.course.equivalent').search(self.cr, self.uid, [('student_id', '=', partner.id),('course_id', '=', course.id),('repeat','not in',['E'])])
        if id:
            transfer = self.pool.get('transfer.course.equivalent').browse(self.cr, self.uid, id)[0]
            return transfer
        return []

    def _get_majors(self, majors):
        return ', '.join([major.name for major in majors])

    def _get_major_ids(self, major_ids):
        return self.pool.get('aun.registrar.major').browse(self.cr, self.uid, major_ids)
    
    def _get_concentration_ids(self, concentration_ids):
        return self.pool.get('registrar.concentration').browse(self.cr, self.uid, concentration_ids)
    
    def _get_concentrations(self, concentrations):
        return ', '.join([concentration.name for concentration in concentrations])
    
    def _get_current_name(self, partner):
        return (partner.fname or "") + " " + (partner.mname or " ")+ " " + (partner.lname or "") 

    def _get_current_programs(self, partner):
        programs = []
        program_ids = self.pool.get('res.partner').browse(self.cr, self.uid, partner.id)._get_schools_and_programs(self.cr, self.uid)[partner.id]['program_ids'][0][2]
        if program_ids:
            programs = self.pool.get('registrar.program').browse(self.cr, self.uid, program_ids)          
        return ', '.join([program.title+'('+program.name+')' for program in programs])
    
    def _get_programs(self, partner):
        catalogue_id = partner.catalogue_id.id
        level_id = partner.level_id.id
        mc_obj = self.pool.get('aun.registrar.major.course')
        major_ids = [major.id for major in partner.major_ids]
        major_course_ids = mc_obj.search(self.cr, self.uid, [('catalogue_id','=',catalogue_id),('major_id','in',major_ids),('level_id','=',level_id)], context=None)
        major_courses = mc_obj.browse(self.cr, self.uid, major_course_ids, context=None)
        return ', '.join(list(set([mc.program_id.name+' in '+mc.major_id.name for mc in major_courses])))
      
    def _get_school(self, partner):    
        schools = []
        school_ids = self.pool.get('res.partner').browse(self.cr, self.uid, partner.id)._get_schools_and_programs(self.cr, self.uid)[partner.id]['school_ids'][0][2]
        if school_ids:
            schools = self.pool.get('aun.registrar.school').browse(self.cr, self.uid, school_ids)          
        return ', '.join([school.name.name for school in schools])  
    
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
    
    def _get_total_gpa(self, points, gpa_hrs):
        if(gpa_hrs == '0.00'):
            return gpa_hrs
        value = float(points)/float(gpa_hrs)
        if(value == 0):
            return '0.00'
        return '{0:.2f}'.format(value)  

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
