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
from openerp.tools.translate import _
from lepl.apps.rfc3696 import Email
import time
import re
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from string import ascii_lowercase, ascii_uppercase
from openerp import pooler, tools
from openerp import SUPERUSER_ID

AVAILABLE_STATES = [
    ('draft', 'New'),
    ('submitted', 'Submitted'),
    ('accepted', 'Accepted'),
    ('done', 'Admitted'),
    ('refused', 'Refused'),
    ('pending', 'Pending')
]

FORM_STATES = [
    ('draft', 'New'),
    ('done', 'Done')
]

ACTIVITIES = [
    ('Academic Games','Academic Games'),
    ('Art','Art'),
    ('Art Visual','Art Visual'),
    ('Athletics','Athletics',),
    ('Basketball','Basketball'),
    ('Business Related','Business Related'),
    ('Campus or Comm. Service Orgs','Campus or Comm. Service Orgs'),
    ('Community Service','Community Service'),
    ('Coop or Internship Programs','Coop or Internship Programs'),
    ('Dance','Dance'),
    ('Envir or Ecology Activity','Envir or Ecology Activity'),
    ('Foreign Study - Study Abroad','Foreign Study - Study Abroad'),
    ('Fraternity or Sorority','Fraternity or Sorority'),
    ('Gifted Talented Activities','Gifted Talented Activities'),
    ('Health Related','Health Related'),
    ('Home Family Related','Home Family Related'),
    ('Honors or Indep. Study','Honors or Indep. Study'),
    ('Intramural Athletics','Intramural Athletics'),
    ('Music','Music'),
    ('Nature Related','Nature Related'),
    ('Piano','Piano'),
    ('Ping Pong','Ping Pong'),
    ('Political Organizations','Political Organizations'),
    ('R O T C','R O T C'),
    ('Racial or Ethnic Organizations','Racial or Ethnic Organizations'),
    ('Radio - TV','Radio - TV'),
    ('School Related','School Related'),
    ('Science Related','Science Related'),
    ('Soccer','Soccer'),
    ('Special Interest Groups','Special Interest Groups'),
    ('Student Government','Student Government'),
    ('Swimming','Swimming'),
    ('Theatre','Theatre'),
    ('Travel Inside Nigeria','Travel Inside Nigeria'),
    ('Travel Outside Nigeria','Travel Outside Nigeria'),
    ('Varsity Athletics','Varsity Athletics'),
    ('Voice','Voice'),
    ('Volleyball','Volleyball'),
    ('Writing Related','Writing Related'),
    ('Youth Related','Youth Related')
]


class admission_settings(osv.osv):
    _name = "admission.settings"
    _description = "Admission Settings"
    _inherit = ["mail.thread"]
    
    _columns = {
        'name': fields.char('Name'),
        'essay': fields.text('Essay Instruction', required=True, help='Application Essay Instruction', track_visibility="onchange"),
        'newsletter': fields.text('Newsletter Message', required=True, track_visibility="onchange"),
        'disclaimer': fields.text('Disclaimer Message', required=True, track_visibility="onchange"),
        'upload': fields.text('Upload Message', required=True, track_visibility="onchange"),
        'no_of_uploads': fields.integer('Number of uploads required', track_visibility="onchange")
    }
    
    def reset_password(self, cr, uid, ids, context=None):
        ap_obj = self.pool.get('acceptance.password')
        password_ids = ap_obj.search(cr, uid, [])
        ap_obj.unlink(cr, uid, password_ids)
        return True
    
    def check_max_uploads(self, cr, uid, ids, context=None):
        settings = self.browse(cr, uid, ids,context=context)[0]
        if settings.no_of_uploads > 3:
            raise osv.except_osv(_('Invalid!'), _('The number of uploads required cannot be greater than 3.'))
        return True
    
    _constraints =[
        (check_max_uploads, 'The number of uploads required cannot be greater than 3!',['Uploads Required'])
    ]
     
admission_settings()


class aun_applicant(osv.osv):
    _name = 'aun.applicant'
    _description = 'AUN Applicants'
    _inherit = ["mail.thread"]
 
#     def fields_get(self, cr, uid, fields=None, context=None):
#         term_obj = self.pool.get('aun.registrar.term')
#         term_ids = term_obj.search(cr, SUPERUSER_ID, [('admission_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('admission_end','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
#         if not term_ids:
#             raise osv.except_osv(_('Admission Closed!'), _('No term is currently open for admission!'))                   
#         return super(aun_applicant, self).fields_get(cr, SUPERUSER_ID, fields, context)
 
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_admis_applicant"):
            for record in reads:
                name = record.name
                res.append((record['id'], name))
        else:   
            for record in reads:
                if record.state == 'done':
                    name = record.name + ' / ' + record.term_admitted.name_get()[0][1] + ' / ' + record.type.name
                else:
                    name = record.name
                res.append((record['id'], name))
        return res
 
    def create(self, cr, uid, vals, context=None):
        app_obj = self.pool.get('aun.applicant')
        if 'partner_id' in vals and vals['partner_id']:
            self.pool.get('res.partner').write(cr, SUPERUSER_ID, [vals['partner_id']], {'applicant': True})
            term_ids = app_obj.search(cr,uid, [('partner_id','=',vals['partner_id']),('sem_id','=',vals['sem_id'])])
            if term_ids:
                raise osv.except_osv(_('Invalid!'),_("You cannot create multiple applications for the same term"))
        return super(aun_applicant, self).create(cr, uid, vals, context)
    
    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result
    
    def _set_image(self, cr, uid, ids, name, value, args, context=None):
        return self.write(cr, uid, [ids], {'image': tools.image_resize_image_big(value)}, context=context)

    def _has_image(self, cr, uid, ids, name, args, context=None):
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = obj.image != False
        return result
 
    def get_partner_id(self, cr, uid, context=None):
        res = False
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_admis_applicant"):
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            res = user.partner_id.id
        return res
    
    def get_message(self, cr, uid, context=None):
        settings_obj = self.pool.get('admission.settings')
        settings_id = settings_obj.search(cr, SUPERUSER_ID, [])
        if not settings_id:
            raise osv.except_osv(_('Contact the Administrator!'), _('Settings has not been created!'))
        essay_instruction = settings_obj.browse(cr, SUPERUSER_ID, settings_id[0]).essay
        return essay_instruction
    
    def get_news(self, cr, uid, context=None):
        settings_obj = self.pool.get('admission.settings')
        settings_id = settings_obj.search(cr, SUPERUSER_ID, [])
        if not settings_id:
            raise osv.except_osv(_('Contact the Administrator!'), _('Settings has not been created!'))
        newsletter_msg = settings_obj.browse(cr, SUPERUSER_ID, settings_id[0]).newsletter
        return newsletter_msg

    def get_disclaimer(self, cr, uid, context=None):
        settings_obj = self.pool.get('admission.settings')
        settings_id = settings_obj.search(cr, SUPERUSER_ID, [])
        if not settings_id:
            raise osv.except_osv(_('Contact the Administrator!'), _('Settings has not been created!'))
        disclaimer_msg = settings_obj.browse(cr, SUPERUSER_ID, settings_id[0]).disclaimer
        return disclaimer_msg

    def get_upload(self, cr, uid, context=None):
        settings_obj = self.pool.get('admission.settings')
        settings_id = settings_obj.search(cr, SUPERUSER_ID, [])
        if not settings_id:
            raise osv.except_osv(_('Contact the Administrator!'), _('Settings has not been created!'))
        upload_msg = settings_obj.browse(cr, SUPERUSER_ID, settings_id[0]).upload
        return upload_msg

    _columns = {
            'student_id': fields.char('Student ID', size=16, readonly=False, write=['academics.group_admis_director'], track_visibility="onchange"), 
            'create_date': fields.datetime('Creation Date', readonly=True, select=True),
            'date_submitted': fields.datetime('Date Submitted', readonly=True, select=True),
            'date_accepted': fields.datetime('Date Accepted', readonly=True),
            'date_refused': fields.datetime('Date Rejected', readonly=True),
            'date_admitted': fields.datetime('Date Admitted', readonly=True),
            'state': fields.selection(AVAILABLE_STATES, 'Status', readonly=True, track_visibility="onchange"),
            'name': fields.char('Applicant Name', size=64, readonly=True),
            'fname': fields.char('First Name', size=32, required=True, track_visibility="onchange"),
            'mname': fields.char('Middle Name', size=32, track_visibility="onchange"),
            'lname': fields.char('Last Name', size=32, required=True, track_visibility="onchange"),
            'partner_id': fields.many2one('res.partner', 'Partner', track_visibility="onchange"),
            'email': fields.char('Email', size=64, required=True, track_visibility="onchange"),
            'sex': fields.selection([('M','Male'),('F','Female')],'Gender', track_visibility="onchange"),
            'dob': fields.date('Date of Birth', track_visibility="onchange"),
            'city_of_birth': fields.char('City Of Birth', size=64, track_visibility="onchange"),
            'state_of_origin': fields.many2one('res.country.state', 'State of Origin', track_visibility="onchange"),
            'country_of_origin': fields.many2one('res.country', 'Country of Origin', track_visibility="onchange"),
            'state_of_residence': fields.many2one('res.country.state', 'State of Residence', track_visibility="onchange"),
            'street': fields.char('Street', size=32, track_visibility="onchange"),
            'street2': fields.char('Street2', size=32, track_visibility="onchange"),
            'city': fields.char('City1', size=32, track_visibility="onchange"),
            'state_id': fields.many2one('res.country.state', 'State', track_visibility="onchange"),
            'zip': fields.char('Zip', size=24, track_visibility="onchange"),
            'country_id': fields.many2one('res.country', 'Country', track_visibility="onchange"),
            'phone': fields.char('Mobile 1', size=64, required=True, track_visibility="onchange"),
            'mobile': fields.char('Mobile 2', size=64, track_visibility="onchange"),
            'perm_street': fields.char('Street', size=32, track_visibility="onchange"),
            'perm_street2': fields.char('Street2', size=32, track_visibility="onchange"),
            'perm_city': fields.char('City2', size=64, track_visibility="onchange"),
            'perm_state_id': fields.many2one('res.country.state', 'State', track_visibility="onchange"),
            'perm_zip': fields.char('Zip(Permanent)', size=24, track_visibility="onchange"),
            'perm_country_id': fields.many2one('res.country', 'Country', track_visibility="onchange"),
            'land_phone': fields.char('Home Phone', size=16, track_visibility="onchange"),
            'app_prev': fields.boolean('Have you applied to AUN in the past?', track_visibility="onchange"),
            'app_prev_acc': fields.boolean('If yes, were you accepted?', track_visibility="onchange"),
            'app_prev_enr': fields.boolean('If yes, did you enroll?', track_visibility="onchange"),
            'prev_student_id': fields.char('If yes, enter your student ID', track_visibility="onchange"),
            'app_prev_enr_term': fields.char('If yes, please specify year(s) and term(s) you have studied', size=64, track_visibility="onchange"),
            'no_of_siblings_uni': fields.selection([('0','None'),('1','1'),('2','2'),('3','3'),('3+','Above 3')], 'No of siblings in AUN', track_visibility="onchange"),
            'essay_instruction': fields.text('Essay Instruction'),
            'essay': fields.text('Essay'),
            'test_result_ids': fields.one2many('applicant.test', 'app_id', 'Results', track_visibility="onchange"),
            'essay_upload': fields.binary('Essay'),
            'image': fields.binary('Image'),
            'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized image", type="binary", multi="_get_image",
            store={
                'aun.applicant': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image of this contact. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
            'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized image", type="binary", multi="_get_image",
            store={
                'aun.applicant': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of this contact. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
            'has_image': fields.function(_has_image, type="boolean"),
            'sem_id': fields.many2one('aun.registrar.term', 'Application Term', domain=[('open_for_admission','=',True)], required=True, track_visibility="onchange"),
            'term_admitted': fields.many2one('aun.registrar.term', 'Admission Term', domain=[('open_for_admission','=',True)], track_visibility="onchange"),
            'major_id': fields.many2one('aun.registrar.major', 'Major', track_visibility="onchange"),
            'guardians': fields.one2many('aun.guardian','app_id','Guardians'),
            'activities': fields.one2many('aun.activity','app_id','Activities'),
            'high_school': fields.one2many('aun.high.school.app','app_id','High Schools' ),
            'recommendation1': fields.binary('Recommendation 1'),
            'recommendation2': fields.binary('Recommendation 2'),
            'type': fields.many2one('aun.application.type', 'Application Type', required=True, track_visibility="onchange"),
            'level_id': fields.many2one('aun.registrar.level', 'Admission Level'),
            'signature': fields.char('Full Name', size=256, track_visibility="onchange"),
            'sign_date': fields.date('Date', readonly=True, track_visibility="onchange"),
            'intl': fields.boolean('Non-Nigerian'),
            'editable': fields.boolean('Edit', help="Do not uncheck edit before saving the application. It will be unchecked automatically."),
            'provisional': fields.boolean('Provisional', track_visibility="onchange"),
            'prov_end_date': fields.date('End Date', track_visibility="onchange"),
            'newsletter': fields.boolean('Newsletter', track_visibility="onchange"),
            'newsletter_msg': fields.text('Newsletter Message'),
            'disclaimer_msg': fields.text('Disclaimer'),
            'upload_msg': fields.text('Uploads'),
            'upload1': fields.binary('Upload'),
            'upload2': fields.binary('Upload'),
            'upload3': fields.binary('Upload'),
            'deferred': fields.boolean('Deferred'),
            'deferred_term': fields.many2one('aun.registrar.term', 'Deferred Term', track_visibility="onchange"),
            'active': fields.boolean('Active')
            }
    _defaults={
            'active': True,
            'state': lambda *a: 'draft',
            'no_of_siblings_uni': '0',
            'partner_id': get_partner_id,
            'essay_instruction': get_message,
            'newsletter_msg': get_news,
            'disclaimer_msg': get_disclaimer,
            'upload_msg': get_upload,
    }

    def write(self, cr, uid, ids, vals, context=None):
        applicant = self.browse(cr, uid, ids, context=context)[0]
        
        if 'prov_end_date' in vals and vals['prov_end_date']:
            if vals['prov_end_date'] < str(date.today()):
                raise osv.except_osv(_('Invalid Date!'), _('Enter a provisional end date greater than or equal to today\'s date!'))
      
        if 'signature' in vals:
            if vals['signature']:
                vals['signature'] = vals['signature'].strip()
                if vals['signature']:
                    vals.update({'sign_date': time.strftime('%Y-%m-%d')})
                else:
                    vals.update({'sign_date': False})
            else:
                vals.update({'sign_date': False})
        name = ''
        try:
            first_name = vals['fname']
            if(first_name == False):
                first_name = ''
            name = first_name   
        except:
            name = applicant.fname
        
        try:
            middle_name = vals['mname']
            if(middle_name == False):
                middle_name = ''
            name += ' ' + middle_name
        except:
            if(applicant.mname != False):
                name += ' ' + applicant.mname
        try:
            last_name = vals['lname']
            if(last_name == False):
                last_name = ''            
            name += ' ' + last_name
        except:
            name += ' ' + applicant.lname
                    
        vals.update({'name': name, 'editable': False})
        return super(aun_applicant, self).write(cr, uid, ids, vals, context=context)

    def on_change_prov(self, cr, uid, ids, context=None):
        return {'value': {'prov_end_date': False}}
    
    def on_change_type(self, cr, uid, ids, type_id, major_id, context=None):
        res = {}
        if type_id:
            res['level_id'] = self.pool.get('aun.application.type').browse(cr, SUPERUSER_ID, type_id).level_id.id
            if major_id:
                mc = self.pool.get('aun.registrar.major.course').search(cr, SUPERUSER_ID, [('major_id','=',major_id),('level_id','=',res['level_id'])])
                if not mc:
                    res['major_id'] = False
        else:
            res['level_id'] = False     
        return {'value': res}

    def check_required_fields(self, cr, uid, ids, context=None):
        application = self.browse(cr, uid, ids)[0]
        empty_fields = []
        no_subjects = []
        if not application.major_id:
            empty_fields.append('Major')
        if not application.sex:
            empty_fields.append('Gender')
        if not application.dob:
            empty_fields.append('Date of Birth')
        if not application.state_of_origin and not application.intl:
            empty_fields.append('State of Origin')
        if not application.country_of_origin:
            empty_fields.append('Country of Origin')
        if not application.high_school:
            empty_fields.append('High School Information')
        if not (application.recommendation1 or application.recommendation2):
            empty_fields.append('Recommendation')
        if not application.type:
            empty_fields.append('Application Type')
        if not application.street:
            empty_fields.append('Street')
        if not application.city:
            empty_fields.append('City')
        if not application.state_id:
            empty_fields.append('State')
        if not application.country_id:
            empty_fields.append('Country')
        if not application.test_result_ids:
            empty_fields.append('Examination Results')
        if not (application.essay or application.essay_upload):
            empty_fields.append('Essay')
            
        settings_obj = self.pool.get('admission.settings')
        settings_id = settings_obj.search(cr, SUPERUSER_ID, [])
        if not settings_id:
            raise osv.except_osv(_('Contact the Administrator!'), _('Settings has not been created!'))
        no_of_uploads = settings_obj.browse(cr, SUPERUSER_ID, settings_id[0]).no_of_uploads

        uploads = 0
        if application.upload1:
            uploads+=1
        if application.upload2:
            uploads+=1
        if application.upload3:
            uploads+=1

        if uploads < no_of_uploads:
            raise osv.except_osv(_('Check uploads!'), _(str(no_of_uploads-uploads) + ' upload(s) missing under personal information (Step 1). Please upload the ' + str(no_of_uploads) + ' required document(s).'))

        for test in application.test_result_ids:
            if not test.awaiting_result:
                if not test.test_result_ids:
                    no_subjects.append(test.test_name_id.code)
                if not test.test:
                    empty_fields.append(test.test_name_id.code + ' Upload')
                
        for high_school in application.high_school:
            if not high_school.transcript_ids:
                no_subjects.append(high_school.name + ' Transcript Subjects')
            if not high_school.transcript_upload:
                empty_fields.append(high_school.name + ' Transcript Upload')
            
        if empty_fields or no_subjects:
            raise osv.except_osv(_('Application Incomplete!'), _('The following information is missing: \n' + ', '.join(empty_fields) + '.' + ['\nSubjects for: \n',''][not no_subjects] + ', '.join(no_subjects)))
    
        if not application.signature:
            raise osv.except_osv(_('Signature Required!'), _('Please enter your full name as digital signature on Step 8 of the application.'))
        
        return True
   
    def case_submit(self, cr, uid, ids, context=None):
        self.check_required_fields(cr, uid, ids)
        applicant = self.browse(cr, uid, ids)[0]
        if not applicant.date_submitted:
            self.write(cr, uid, ids, {'state': 'submitted', 'date_submitted': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
        partner_obj = self.pool.get('res.partner')
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_admis_applicant"):
            partner_obj.write(cr, SUPERUSER_ID, [applicant.partner_id.id], {
                                                     'name': applicant.name,
                                                     'dob': applicant.dob,
                                                     'email': applicant.email,
                                                     'sex': applicant.sex,
                                                     'state_of_origin': applicant.state_of_origin,
                                                     'sem_id': applicant.sem_id.id,
                                                     'street': applicant.street,
                                                     'street2': applicant.street2,
                                                     'state_id': applicant.state_id.id,
                                                     'country_id': applicant.country_id.id,
                                                     'city': applicant.city,
                                                     'phone': applicant.phone
                                                    })
        return True

    def case_refuse(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'refused', 'date_refused': date.today(), 'provisional': False}, context=context)
        self.email_applicant(cr, uid, ids, 'rejection_email')
        return True
    
    def case_pending(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'pending'}, context=context)
        return True

    def case_accept(self, cr, uid, ids, context=None):
        cr.execute("select id from aun_applicant WHERE student_id IS NOT NULL ORDER BY student_id DESC")
        res = cr.fetchone()
        if not res:
            stud_id = "A00000001"
        else:
            app = self.browse(cr,uid,res[0])
            stud_id = app.student_id
            a = int(stud_id[1:9])
            if a == 99999999:
                stud_id = chr(ord(stud_id[0])+1) + 00000001
            else:
                stud_id = stud_id[0] + str(a+1).zfill(8)
        applicant = self.browse(cr, uid, ids)[0]
        partner_obj = self.pool.get('res.partner')
        if applicant.prev_student_id:
            applicant_partner_id = partner_obj.search(cr, SUPERUSER_ID, [('name','=',applicant.prev_student_id),('student','=',True)])[0]
        else:
            if applicant.partner_id:
                applicant_partner_id = applicant.partner_id.id
                partner_obj.write(cr, SUPERUSER_ID, [applicant_partner_id], {'name': stud_id,'fname': applicant.fname,'mname': applicant.mname, 'lname': applicant.lname, 'applicant': True})
            else:
                applicant_partner_id = partner_obj.create(cr, SUPERUSER_ID, {'name': stud_id,'fname': applicant.fname,'mname': applicant.mname, 'lname': applicant.lname, 'applicant': True}, context=context)
        account_obj = self.pool.get('student.account')
        account_obj.create(cr, SUPERUSER_ID, {'student_id': applicant_partner_id,'applicant': True})
        if self.browse(cr, uid, ids)[0].provisional:
            self.email_applicant(cr, uid, ids, 'provisional_email')
        else:
            self.email_applicant(cr, uid, ids, 'acceptance_email')
        return self.write(cr, uid, ids, {'student_id': stud_id,'partner_id':applicant_partner_id, 'state': 'accepted', 'date_accepted': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
    
    def create_stud_account(self, cr, uid, ids, context=None):
        applicants= self.browse(cr, SUPERUSER_ID, self.search(cr, SUPERUSER_ID, [('sem_id','=',118),('state','=','accepted')]), context)
        partner_obj = self.pool.get('res.partner')
        for applicant in applicants:
            print applicant
            if applicant.prev_student_id:
                applicant_partner_id = partner_obj.search(cr, SUPERUSER_ID, [('name','=',applicant.prev_student_id),('student','=',True)])[0]
            else:
                if applicant.partner_id:
                    applicant_partner_id = applicant.partner_id.id
                    partner_obj.write(cr, SUPERUSER_ID, [applicant_partner_id], {'name': applicant.student_id,'fname': applicant.fname,'mname': applicant.mname, 'lname': applicant.lname})
                else:
                    applicant_partner_id = partner_obj.create(cr, SUPERUSER_ID, {'name': applicant.student_id,'fname': applicant.fname,'mname': applicant.mname, 'lname': applicant.lname}, context=context)
            account_obj = self.pool.get('student.account')
            account_id = account_obj.search(cr, SUPERUSER_ID, [('student_id','=',applicant_partner_id)])
            if not account_id:
                account_obj.create(cr, SUPERUSER_ID, {'student_id': applicant_partner_id,'applicant': True})
        return True
    
    def email_applicant(self, cr, uid, ids, template_id, context=None):
        template = self.pool.get('ir.model.data').get_object(cr, uid, 'academics', template_id)
        mail_obj = self.pool.get('mail.mail')
        assert template._name == 'email.template'
        for record in self.browse(cr, uid, ids, context):
            if not record.email:
                raise osv.except_osv(_("Cannot send email: user has no email address."), record.name)
            mail_id = self.pool.get('email.template').send_mail(cr, uid, template.id, record.id, True, context=context)
            mail_state = mail_obj.read(cr, uid, mail_id, ['state'], context=context)
            if mail_state and mail_state['state'] == 'exception':
                raise osv.except_osv(_("Check email"), ("Cannot send email: Please check the applicant\'s email address. \n Contact the system administrator if the email seems correct."))

    def case_admit(self, cr, uid, ids, context=None, *args):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's ids
        @param *args: Give Tuple Value
        """
        self.check_required_fields(cr, uid, ids)
        applicant = self.browse(cr, uid, ids)[0]
        if not applicant.term_admitted:
            raise osv.except_osv(_('No Admission Term!'), _('You must pick the term for which the student is being admitted!'))
        
        term_admitted = applicant.term_admitted
        level_id = applicant.type.level_id.id
        partner_obj = self.pool.get('res.partner')     
        
        if applicant.prev_student_id:
            applicant_partner_id = partner_obj.search(cr, SUPERUSER_ID, [('name','=',applicant.prev_student_id),('student','=',True)])[0]
        else:
            if applicant.partner_id:
                applicant_partner_id = applicant.partner_id.id
                #delete applicant's user id before creation of student user id
                user_ids = [user.id for user in applicant.partner_id.user_ids]
                self.pool.get('res.users').unlink(cr, SUPERUSER_ID, user_ids, context=context)
            else:
                applicant_partner_id = partner_obj.create(cr, SUPERUSER_ID, {'name': applicant.student_id}, context=context)
        
        default_standing_id = self.pool.get('aun.registrar.standing').search(cr, SUPERUSER_ID, [('default_standing','=',True)])
        if not default_standing_id:
            raise osv.except_osv(_('Contact the Registrar!'), _('There is no default standing set for students!'))

        default_state_id = self.pool.get('student.state').search(cr, SUPERUSER_ID, [('default_state','=',True)])
        if not default_state_id:
            raise osv.except_osv(_('Contact the Registrar!'), _('There is no default state set for students!'))
       
        #get student catalogue based on admission term
        term_term = term_admitted.name
        term_year = term_admitted.year
        catalogue_obj = self.pool.get('aun.registrar.catalogue')
        catalogue_id = catalogue_obj.search(cr, SUPERUSER_ID, [('start_year','<=', str(int(term_year) + int(term_term.year_adjustment))),('end_year','>',str(int(term_year) + int(term_term.year_adjustment)))])
        if not catalogue_id:
            raise osv.except_osv(_('Contact the Registrar!'), _('There is no matching catalogue for the applicant\'s admission year!'))
        catalogue_id = catalogue_id[0]
             
        #check if major is in admission catalogue
        if applicant.major_id and not applicant.major_id.no_school:
            mc_obj = self.pool.get('aun.registrar.major.course')
            major_ids = mc_obj.search(cr, SUPERUSER_ID, [('major_id','=',applicant.major_id.id),('level_id','=',level_id),('catalogue_id','=',catalogue_id)])
            if not major_ids:
                raise osv.except_osv(_('Major Unavailable!'), _(applicant.major_id.name + ' is not in the admission catalogue for this student! Please select another major!'))
        
        #create admissions hold if student is admitted provisionally
        if applicant.provisional:
            admis_hold = self.pool.get('ir.model.data').get_object(cr, uid, 'academics', 'Admissions Hold')
            hold_obj = self.pool.get('aun.registrar.hold.assignment')
            assert admis_hold._name == 'aun.registrar.hold'
            format_string = "%Y-%m-%d"
            end_date = date.today() + relativedelta(years=20)
            end_date_string = datetime.strftime(end_date, format_string)
            hold_obj.create(cr, uid, {
                                      'student_id': applicant_partner_id,
                                      'hold_id': admis_hold.id,
                                      'start_date': applicant.prov_end_date,
                                      'end_date': end_date_string,
                                      'note': 'Automatic hold from provisional admission'
                                      })
        if applicant.prev_student_id:
            partner_obj.write(cr, SUPERUSER_ID, [applicant_partner_id], {
                                                             'app_id': applicant.id,
                                                             'fname': applicant.fname,
                                                             'mname': applicant.mname,
                                                             'lname': applicant.lname,
                                                             'dob': applicant.dob,
                                                             'personal_email': applicant.email,
                                                             'city_of_birth': applicant.city_of_birth,
                                                             'state_of_origin': applicant.state_of_origin,
                                                             'sem_id': applicant.sem_id.id,
                                                             'street': applicant.street,
                                                             'street2': applicant.street2,
                                                             'state_id': applicant.state_id.id,
                                                             'country_id': applicant.country_id.id,
                                                             'city': applicant.city,
                                                             'admission_date': date.today(),
                                                             'term_admitted': term_admitted.id,
                                                             'catalogue_id': catalogue_id,
                                                             'phone': applicant.phone,
                                                             'mobile': applicant.mobile,
                                                             'student_state_id': default_state_id[0],
                                                             'level_id': applicant.level_id.id,
                                                             'major_ids': [(6, 0, [applicant.major_id.id])] if applicant.major_id else False,
                                                             'standing_id': default_standing_id[0],
                                                             'is_active': True,
                                                             'graduated': False,
                                                             'applicant': False,
                                                             'date_of_state': False,
    #                                                          'image': applicant.image
                                                            })
        else:   
            partner_obj.write(cr, SUPERUSER_ID, [applicant_partner_id], {
                                                             'app_id': applicant.id,
                                                             'name': applicant.student_id,
                                                             'fname': applicant.fname,
                                                             'mname': applicant.mname,
                                                             'lname': applicant.lname,
                                                             'dob': applicant.dob,
                                                             'personal_email': applicant.email,
                                                             'email': False,
                                                             'sex': applicant.sex,
                                                             'city_of_birth': applicant.city_of_birth,
                                                             'state_of_origin': applicant.state_of_origin,
                                                             'sem_id': applicant.sem_id.id,
                                                             'street': applicant.street,
                                                             'street2': applicant.street2,
                                                             'state_id': applicant.state_id.id,
                                                             'country_id': applicant.country_id.id,
                                                             'city': applicant.city,
                                                             'admission_date': date.today(),
                                                             'term_admitted': term_admitted.id,
                                                             'catalogue_id': catalogue_id,
                                                             'phone': applicant.phone,
                                                             'mobile': applicant.mobile,
                                                             'student': True,
                                                             'student_state_id': default_state_id[0],
                                                             'level_id': applicant.level_id.id,
                                                             'major_ids': [(6, 0, [applicant.major_id.id])] if applicant.major_id else False,
                                                             'standing_id': default_standing_id[0],
                                                             'is_active': True,
                                                             'applicant': False
#                                                              'image': applicant.image
                                                            })
            
            # no AUN email so user should not be created
#             partner_obj.create_user(cr, SUPERUSER_ID, [applicant_partner_id], context=None)
        account_obj = self.pool.get('student.account')
        account_id = account_obj.search(cr, SUPERUSER_ID, [('student_id','=',applicant_partner_id)])
        account_obj.write(cr, SUPERUSER_ID, account_id, {'applicant': False}, context=context)
        self.write(cr, uid, ids, {'state': 'done', 'date_admitted': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
        
        return True

#     def enroll_all(self, cr, uid, ids, context=None, *args):
#         student_obj = self.pool.get('res.partner')
#         cr.execute("select id from aun_applicant WHERE state ='draft'")
#         a = cr.fetchall()
#         app_ids = []
#         for app in a:
#             app_ids.append(app[0])
#         applicants = self.pool.get('aun.applicant').browse(cr, uid, app_ids)
#         for applicant in applicants:
#             enrolled_semester = applicant.sem_id.name
#             enrolled_year = applicant.sem_id.year
#             catalogue_obj = self.pool.get('aun.registrar.catalogue')
#             major = []
#             major.append(applicant.major_id.id)
#             if enrolled_semester == 'Fall':
#                 catalogue = catalogue_obj.search(cr,uid, [('start_year','=', str(enrolled_year))])
#             else:
#                 catalogue = catalogue_obj.search(cr,uid, [('start_year','=', str(int(enrolled_year) - 1))])
#             if applicant.mname:
#                 stud_name = applicant.fname + " " + applicant.mname + " " + applicant.lname
#             else: 
#                 stud_name = applicant.fname + " " + applicant.lname
#             print applicant.lname
#             self.pool.get('aun.applicant').write(cr, uid, applicant.id, {'state': 'done'}, context=context)
#             level = applicant.type.level.id
#             stud_id = student_obj.create(cr,uid,{
#                                                  'app_id': applicant.id,
#                                                  'name': applicant.student_id,
#                                                  'catalogue_id': catalogue[0],
#                                                  'major_id': [(6, 0, major)],
#                                                  'level': level,
#                                                      })
#             add = self.pool.get('res.partner.address')
#             add.create(cr,uid,{
#                                'street': applicant.mail_add,
#                                'partner_id': stud_id
#                                })
#         return True

    def on_change_state(self, cr, uid, ids, state_id, field_name, context=None):
        if state_id:
            country_id = self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id
            if field_name == 'state':
                return {'value': {'country_id': country_id}}
            elif field_name == 'perm_state':
                return {'value': {'perm_country_id': country_id}}
            elif field_name == 'state_of_origin':
                return {'value': {'country_of_origin': country_id}}
        return {}
    
    def on_change_country(self, cr, uid, ids, country_id, state_id, field_name, context=None):
        if country_id and state_id:
            if country_id != self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id:
                if field_name == 'country':
                    return {'value': {'state_id': False}}
                elif field_name == 'perm_country':
                    return {'value': {'perm_state_id': False}}
                elif field_name == 'country_of_origin':
                    return {'value': {'state_of_origin': False}}
        return {}
            
    def on_change_intl(self, cr, uid, ids, intl, context=None):
        if intl:
            return {'value': {'state_of_origin': False}}
        return {}
    
    def case_reset(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'submitted'}, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        applicants = self.read(cr, uid, ids, ['state'], context=context)
        app_test_obj = self.pool.get('applicant.test')
        unlink_ids = []
        inactive_ids = []
        for a in applicants:
            if a['state'] in ('draft'):
                unlink_ids.append(a['id'])
            elif a['state'] in ('submitted'):
                inactive_ids.append(a['id'])
                app_test_obj.unlink(cr, uid, app_test_obj.search(cr, uid, [('app_id','=',a['id'])]))
            else:
                raise osv.except_osv(_('Invalid action!'), _('You cannot delete this application.'))
        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        super(aun_applicant, self).write(cr, uid, inactive_ids, {'active': False}, context=context)
        return True
    
    def check_aun_email(self, cr, uid, ids, context=None):
        applicant = self.browse(cr, uid, ids,context=context)[0]
        aun_email = applicant.email
        if aun_email:
            aun_email = aun_email.strip()
            if aun_email[-11:] != "@aun.edu.ng":
                return False
            validator = Email()           
            return validator(aun_email)
       
        return True    
    
    def check_term(self, cr, uid, ids, context=None):
        application = self.browse(cr, uid, ids,context=context)[0]
        term = application.sem_id
        if not term.admission_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= term.admission_end:
            raise osv.except_osv(_('Term Restriction!'), _('This term is currently closed for admission.'))   
        return True
    
    def check_prev_student_id(self, cr, uid, ids, context=None):
        application = self.browse(cr, uid, ids,context=context)[0]
        if application.prev_student_id:
            partner_obj = self.pool.get('res.partner')
            if not partner_obj.search(cr, uid, [('name','=',application.prev_student_id),('student','=',True)]):
                raise osv.except_osv(_('Invalid Student ID!'), _('Ensure that you have entered a valid student ID!'))
        return True
    
    _constraints =[
        (check_prev_student_id, 'Please enter a valid student ID',['Student ID'])
        #(check_aun_email, 'Please enter a valid Email!',['Email']),
        #(check_term, 'This term is closed for admission!',['Term']),
    ]
    
    _sql_constraints = [
        ('student_id_uniq', 'unique(student_id)', 'Student ID cannot be duplicated!')
    ]

aun_applicant()


class aun_applicant_type(osv.osv):
    _name = "aun.applicant.type"
    _description = "Applicant Type"   
    _inherit = ["mail.thread"]
    _columns = {
        'name': fields.char('Type', size=32),
        'description': fields.text('Description'),
        }

aun_applicant_type()


class aun_application_type(osv.osv):
    _name = "aun.application.type"
    _description = "Application Type"
    _inherit = ["mail.thread"]

    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'done'
        return super(aun_application_type, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        app_type = self.browse(cr, uid, ids, context=context)[0]
        type_obj = self.pool.get('aun.applicant.type')
        level_obj = self.pool.get('aun.registrar.level') 
        if 'type_id' in vals:
            type_name = type_obj.browse(cr, uid, vals['type_id']).name
        else:
            type_name = app_type.type_id.name
        name = type_name
        
        if 'level_id' in vals:
            level_name = level_obj.browse(cr, uid, vals['level_id']).name
        else:
            level_name = app_type.level_id.name
        name += ' ' + level_name + ' Student'
                    
        vals.update({'name': name})
        return super(aun_application_type, self).write(cr, uid, ids, vals, context=context)

    _columns = {
        'name': fields.char('Name', readonly=True),
        'type_id': fields.many2one('aun.applicant.type', 'Applicant type', required=True, track_visibility="onchange"),
        'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility="onchange"),
        'description': fields.text('Description'),
        'state': fields.selection(FORM_STATES, 'Status', readonly=True),
        'active': fields.boolean('Active')
    }

    _defaults={
        'state': lambda *a: 'draft',
        'active': True
    }
    
    _sql_constraints = [
        ('app_type_uniq', 'unique(name)', 'This application type already exists!'),
    ]

aun_application_type()


class aun_guardian(osv.osv):
    _name = 'aun.guardian'
    _description = 'Guardians'
    _columns = {
            'name': fields.selection([('aunt','Aunt'),('brother','Brother'),('child','Child'),('father','Father'),('friend','Friend'),('grandparent','Grandparent'),('guardian','Guardian'),('husband','Husband'),('mother','Mother'),('other','Other'),('sister','Sister'),('uncle','Uncle'),('wife','Wife'),('other','Other')],'Relationship Type', required=True),
            'prefix': fields.selection([('mr','Mr.'),('mrs','Mrs.'),('dr','Dr.'),('chief','Chief'),('alhaji','Alhaji'),('hajiya','Hajiya'),('sir','Sir')],'Prefix'),
            'fname': fields.char('First Name', size=32, required=True),
            'mname': fields.char('Middle Name', size=32),
            'lname': fields.char('Last Name', size=32, required=True),
            'phone': fields.char('Phone Number', size=16, required=True),
            'email': fields.char('Email', size=64),
            'employer': fields.char('Employer', size=64),
            'street': fields.char('Street', size=32, required=True),
            'street2': fields.char('Street2', size=32),
            'city': fields.char('City', size=64, required=True),
            'state_id': fields.many2one('res.country.state', 'State', required=True),
            'country_id': fields.many2one('res.country', 'Country', required=True),
            'zip' : fields.char('ZIP', size=16),
            #'priority': fields.selection([('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9')], 'Priority'),
            'deceased': fields.boolean('Deceased'),
            'app_id': fields.many2one('aun.applicant', 'Applicant', required=True)
            }

    def on_change_state(self, cr, uid, ids, state_id, context=None):
        if state_id:
            country_id = self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id
            return {'value':{'country_id': country_id}}
        return {}

    def on_change_country(self, cr, uid, ids, country_id, state_id, context=None):
        if country_id and state_id:
            if country_id != self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id:
                return {'value': {'state_id': False}}
        return {}
                
#     _sql_constraints = [
#         ('priority_uniq', 'unique(app_id, priority)', 'Guardian priority must be unique!'),
#     ]   

aun_guardian()

class aun_activity(osv.osv):
    _name = 'aun.activity'
    _description = 'Applicants Activities'
    _columns = {
            'name': fields.selection(ACTIVITIES, 'Activity' ),
            'office_held': fields.text('Office Held/Honor Recieved'),
            'hours_per_week': fields.integer('Hours Per Week' ),
            'to_continue': fields.boolean('Would you continue this activity in AUN?'),
            'app_id': fields.many2one('aun.applicant', 'Activities'),
            }
    

class aun_high_school(osv.osv):
    _name = 'aun.high.school'
    _description = 'High Schools'
    _inherit = ["mail.thread"]
    _columns = {
            'name': fields.char('High School Name', required=True, size=128 ),
            'street': fields.char('Street', size=32, required=True, track_visibility="onchange"),
            'street2': fields.char('Street2', size=32, track_visibility="onchange"),
            'city': fields.char('City', required=True, size=64),
            'state_id': fields.many2one('res.country.state', 'State', required=True, track_visibility="onchange"),
            'country_id': fields.many2one('res.country', 'Country', required=True, track_visibility="onchange"),
            'zip': fields.char('Zip', required=True, track_visibility="onchange")
            }
    
    def on_change_state(self, cr, uid, ids, state_id, context=None):
        if state_id:
            country_id = self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id
            return {'value':{'country_id':country_id}}
        return {}
    
    def on_change_country(self, cr, uid, ids, country_id, state_id, context=None):
        if country_id and state_id:
            if country_id != self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id:
                return {'value': {'state_id': False}}
        return {}

aun_high_school()


class aun_high_school_app(osv.osv):
    _name = 'aun.high.school.app'
    _description = 'High School Information'
    _columns = {
            'name': fields.char('School Name', size=64, track_visibility="onchange"),
            'name_search': fields.many2one('aun.high.school', 'School', required=True, track_visibility="onchange"),
            'street': fields.related('name_search', 'street', type='char', string="Street", readonly=True, store=True),
            'street2': fields.related('name_search', 'street2', type='char', string="Street2", readonly=True, store=True),
            'city': fields.related('name_search', 'city', type='char', string="City", readonly=True, store=True),
            'state_id': fields.related('name_search', 'state_id', type='many2one', relation='res.country.state', string="State", readonly=True, store=True),
            'country_id': fields.related('name_search', 'country_id', type='many2one', relation='res.country', string="Country", readonly=True, store=True),
            'zip': fields.related('name_search', 'zip', type='char', string="ZIP", readonly=True, store=True),
            'counselor': fields.char('Counselor Name', size=64, required=False, track_visibility="onchange"),
            'counselor_email': fields.char('Counselor Email',size=64, required=False, track_visibility="onchange"),
            'counselor_no': fields.char('Counselor Phone',size=20, required=False, track_visibility="onchange"),
            'graduation_date': fields.date('Graduation Date', required=True, track_visibility="onchange"),
            'transcript_upload': fields.binary('Transcript Upload'),
            'transcript_ids': fields.one2many('transcript.course.app', 'high_school_app_id', 'Transcript Subjects', track_visibility="onchange"),
            'app_id': fields.many2one('aun.applicant', 'High Schools', required=True, track_visibility="onchange"),
            }
    
    def on_change_state(self, cr, uid, ids, state_id, context=None):
        if state_id:
            country_id = self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id
            return {'value':{'country_id':country_id}}
        return {}

    def on_change_country(self, cr, uid, ids, country_id, state_id, context=None):
        if country_id and state_id:
            if country_id != self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id:
                return {'value': {'state_id': False}}
        return {}   

    def on_change_name_search(self, cr, uid, ids, school_id, context=None):
        if not school_id:
            return {'value':{
                             'name': False,
                             'street': False,
                             'street2': False,
                             'city': False,
                             'state_id': False,
                             'country_id': False,
                             'zip': False
                             }}
        school = self.pool.get('aun.high.school').browse(cr, uid, school_id)
        return {'value':{
                         'name': school.name,
                         'street': school.street,
                         'street2': school.street2,
                         'city': school.city,
                         'state_id': school.state_id.id,
                         'country_id': school.country_id.id,
                         'zip': school.zip  
                         }}
        
    def on_change_name(self, cr, uid, ids, school, context=None):
        return {}

aun_high_school_app()


class test_name(osv.osv):
    _name = "test.name"
    _description = "Test Name"
    _inherit = ["mail.thread"]

    def create(self, cr, uid, vals, context=None):
        vals['name'] = vals['name'].strip()
        vals['code'] = vals['code'].strip()
        return super(test_name, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'name' in vals:
            vals['name'] = vals['name'].strip()
        if 'code' in vals:
            vals['code'] = vals['code'].strip()
        return super(test_name, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        super(test_name, self).write(cr, uid, ids, {'active': False}, context=context)
        return True
   
    _columns = {
        'name': fields.char('Test Name', size=64, required=True, track_visibility="onchange"),
        'code': fields.char('Test Code', size=16, required=True, track_visibility="onchange"),
        'active': fields.boolean('Active')
        }
    
    _defaults={
        'active': True
        }

    def _uniq_name(self, cr, uid, ids, context=None):
        test = self.browse(cr, uid, ids, context=context)[0]
        test_ids = self.search(cr, uid, [('id','not in',[test.id])])     
        for t in self.browse(cr, uid, test_ids):
            if t.name.lower() == test.name.lower():
                raise osv.except_osv(_('Check test name!'), _('There is another test called: ' + t.name + '. The name must be unique.'))
        return True
    
    _constraints=[
        (_uniq_name, 'There is another test with the same name.', ['Name'])
    ]
    
test_name()


class test_code(osv.osv):
    _name = "test.code"
    _description = "Test Code"
    _inherit = ["mail.thread"]

    _columns = {
        'name': fields.char('Name', track_visibility="onchange"),
        'test_id': fields.many2one('test.name', 'Test', required=True, track_visibility="onchange"),
        'subject': fields.char('Subject', size=32, required=True, track_visibility="onchange"),
        'positions': fields.integer('Positions', required=True, track_visibility="onchange"),
        'score_type': fields.selection([('N','Numeric'),('A','Alphanumeric ')], 'Data Type', required=True, track_visibility="onchange"),
        'low': fields.char('Min Score', size=32, required=True, help='Lowest Grade', track_visibility="onchange"),
        'high': fields.char('Max Score', size=32, required=True, help='Highest Grade', track_visibility="onchange"),
        'scores': fields.char('Scores Allowed(Optional)', size=256, help='If there are specific scores allowed in the range, enter them here separated by comma e.g. A1, A2, B2, F9...', track_visibility="onchange"),
        'active': fields.boolean('Active')
        }

    _defaults={
        'active': True
        }
    
    def unlink(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'active': False})
        return True

    def sort_key(self, s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

    def sort_scores(self, scores):
        scores = list(set(scores.replace(' ','').split(',')) - set(['']))
        return ', '.join(sorted(scores, key=self.sort_key))
    
    def create(self, cr, uid, vals, context=None):
        vals['subject'] = vals['subject'].strip()
        if vals['scores']:
            vals['scores'] = self.sort_scores(vals['scores'])
        return super(test_code, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'subject' in vals:
            vals['subject'] = vals['subject'].strip()
            
        test = self.browse(cr, uid, ids, context=context)[0]
        tn_obj = self.pool.get('test.name')
        name = '' 
        try:
            name = tn_obj.browse(cr, uid, vals['test_id']).code  
        except:
            name = test.test_id.code
        try:
            name += ' ' + vals['subject']
        except:
            name += ' ' + test.subject
            
        if name != test.name:        
            vals.update({'name': name})

        if 'scores' in vals and vals['scores']:
            vals['scores'] = self.sort_scores(vals['scores'])
        return super(test_code, self).write(cr, uid, ids, vals, context=context)
  
    def _uniq_test_subject(self, cr, uid, ids, context=None):
        test = self.browse(cr, uid, ids, context=context)[0]
        test_ids = self.search(cr, uid, [('id','not in',[test.id]),('test_id','=',test.test_id.id)])       
        for t in self.browse(cr, uid, test_ids):
            if t.subject.lower() == test.subject.lower():
                raise osv.except_osv(_('Check test subject!'), _(t.subject + ' already exists for this test. Test subjects must be unique.'))
        return True

    def _check_min_max(self, cr, uid, ids, context=None):
        test = self.browse(cr, uid, ids, context=context)[0]
        
        if test.score_type == 'N':
            try:
                float(test.low)
                float(test.high)
            except:
                raise osv.except_osv(_('Check min/max!'), _('The min and max values must be numeric.'))
            if len(test.low) > test.positions: 
                raise osv.except_osv(_('Check min/max!'), _('The length of the min value must be less than or equal to the positions.'))
            if len(test.high) != test.positions:
                raise osv.except_osv(_('Check min/max!'), _('The length of the max value must be equal to the positions.'))

            if float(test.high) <= float(test.low):
                raise osv.except_osv(_('Check min/max!'), _('The max value must be greater than the min value.'))
            
        if test.score_type == 'A':
            low_not_num = high_not_num = False
            try:
                float(test.low)
            except:
                low_not_num = True
            try:
                float(test.high)
            except:
                high_not_num = True            
            
            if not(low_not_num and high_not_num and test.low.isalnum() and test.high.isalnum()):
                raise osv.except_osv(_('Check min/max!'), _('The min and max values must be alphanumeric.'))
            if len(test.low) != test.positions or len(test.high) != test.positions:
                raise osv.except_osv(_('Check min/max!'), _('The length of the min and max values must be equal to the positions.'))
            
            low=[]
            high=[]
            for i in xrange(len(test.low)):
                #check if both characters are alphabets and same case
                if ((test.low[i] in ascii_uppercase and test.high[i] in ascii_lowercase) or
                    (test.low[i] in ascii_lowercase and test.high[i] in ascii_uppercase)):
                    raise osv.except_osv(_('Check min/max!'), _('Ensure that both min and max have the same case (Uppercase or lowercase).'))
                
                #check if both characters are digits
                if (test.low[i].isdigit() and not test.high[i].isdigit()) or (test.high[i].isdigit() and not test.high[i].isdigit()):
                    raise osv.except_osv(_('Check min/max!'), _('Ensure that both min and max have digits in the same positions.'))
                
                #check if max is alphanumerically greater than min
                if test.low[i].isdigit():
                    low.append(int(test.low[i]))
                    high.append(int(test.high[i]))                    
                else:
                    low.append((ascii_lowercase.index(test.low[i].lower()) + 1) * 10)
                    high.append((ascii_lowercase.index(test.high[i].lower()) + 1) * 10)

            if sum(high) <= sum(low):
                raise osv.except_osv(_('Check min/max!'), _('The max value must be greater than the min value.'))
        
        #check optional scores
        if test.scores:
            scores = test.scores.replace(' ','').split(',')
            for score in scores:
                self.validate_score(test.test_id.code + ' ' + test.subject, score, test.low, test.high, test.score_type)
                
        return True

    def validate_score(self, test_name, score, min_score, max_score, score_type):
        if score_type == 'N':
            try:
                float(score)
            except:
                raise osv.except_osv(_('Invalid Score!'), _(score + ' is not numeric and ' + test_name + ' is a numerically scored test.'))
            if len(score) > len(max_score):
                raise osv.except_osv(_('Check Score!'), _(score + ' is not valid for ' + test_name + '. Check number of digits.'))
            if not(float(max_score) >= float(score) >= float(min_score)):
                raise osv.except_osv(_('Invalid Score!'), _(score + ' is not in the range specified for ' + test_name + '.'))
        
        if score_type == 'A':
            if len(score) != len(min_score):
                raise osv.except_osv(_('Invalid Score!'), _(score + ' is not valid for ' + test_name + '. Check score length'))

            low = []
            high = []
            val = []
            for i in xrange(len(min_score)):
                if min_score[i].isdigit():
                    if not score[i].isdigit():
                        raise osv.except_osv(_('Invalid Score!'), _(score + ' is not an acceptable score for ' + test_name))                    
                    low.append(int(min_score[i]))
                    high.append(int(max_score[i]))
                    val.append(int(score[i]))
                else:
                    if ((min_score[i] in ascii_uppercase and score[i] in ascii_lowercase) or
                        (min_score[i] in ascii_lowercase and score[i] in ascii_uppercase) or
                        score[i] not in ascii_lowercase + ascii_uppercase):
                        raise osv.except_osv(_('Check Score!'), _(score + ' is not a valid score for ' + test_name))
                    low.append((ascii_lowercase.index(min_score[i].lower()) + 1) * 10)
                    high.append((ascii_lowercase.index(max_score[i].lower()) + 1) * 10)
                    val.append((ascii_lowercase.index(score[i].lower()) + 1) * 10)
                    
            if sum(val) not in xrange(sum(low), sum(high) + 1):
                raise osv.except_osv(_('Invalid Score!'), _(score + ' is not in the range for ' + test_name))
                    
        return True
    
    _constraints=[
        (_uniq_test_subject, 'The subject already exists for this test.', ['Subject']),
        (_check_min_max, 'Check the min and max values.', ['Min/Max'])
    ]
    
test_code()



class applicant_test(osv.osv):
    _name = "applicant.test"
    _description = "Results"
    _inherit = ["mail.thread"]

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.app_id.name
            res.append((record['id'], name))
        return res

    def on_change_test(self, cr, uid, ids, test_name_id, context=None):
        if test_name_id:
            return {'value': {'test_result_ids': False}}
        return {} 

    def write(self, cr, uid, ids, vals, context=None):
        res = super(applicant_test, self).write(cr, uid, ids, vals, context=context)
        app_test = self.browse(cr, uid, ids, context=context)[0]
        wrong_tests = []
        duplicate_tests = []
        for tr in app_test.test_result_ids:
            other_res_ids = self.pool.get('test.result').search(cr, uid, [('app_test_id','=',tr.app_test_id.id),('test_id','=',tr.test_id.id)])
            if len(other_res_ids) > 1:
                duplicate_tests.append(tr.test_id.name)
            if tr.test_id.test_id.id != app_test.test_name_id.id:
                wrong_tests.append(tr.test_id.name)
        if wrong_tests:
            raise osv.except_osv(_('Invalid Test!'), _('The following tests are not ' + app_test.test_name_id.code + ' tests: ' + ', '.join(wrong_tests)))
        if duplicate_tests:
            raise osv.except_osv(_('Duplicate Test!'), _('The following tests are duplicated: ' + ', '.join(set(duplicate_tests))))
        return res

    def unlink(self, cr, uid, ids, context=None):
        super(applicant_test, self).write(cr, uid, ids, {'active': False}, context=context)
        return True

    _columns = {
        'app_id': fields.many2one('aun.applicant', 'Student', required=True, track_visibility="onchange"),
        'test_name_id': fields.many2one('test.name', 'Examination', required=True, track_visibility="onchange"),
        'test': fields.binary('Upload'),
        'exam_no': fields.char('Examination Number', size=64, required=True),
        'awaiting_result': fields.boolean('Awaiting Result'),
        'test_result_ids': fields.one2many('test.result', 'app_test_id', 'Results', track_visibility="onchange"),
        'active': fields.boolean('Active')
        }
    
    _defaults={
        'active': True
        }

    _sql_constraints = [
        ('app_test_id_uniq', 'unique(app_id, test_name_id)', 'One of your test results is duplicated!')
    ]
    
applicant_test()


class test_result(osv.osv):
    _name = "test.result"
    _description = "Test Result"
    _inherit = ["mail.thread"]
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.app_test_id.app_id.name + '/' + record.test_id.name
            res.append((record['id'], name))
        return res

    def create(self, cr, uid, vals, context=None):
        vals['score'] = vals['score'].strip()
        return super(test_result, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'score' in vals:
            vals['score'] = vals['score'].strip()
        return super(test_result, self).write(cr, uid, ids, vals, context=context)
        
    _columns = {
        'test_id': fields.many2one('test.code', 'Subject', required=True, track_visibility="onchange"),
        'score': fields.char('Score', size=32, required=True, track_visibility="onchange"),
        'app_test_id': fields.many2one('applicant.test', 'Applicant', required=True),
        'app_id': fields.related('app_test_id', 'app_id', type='many2one', relation='aun.applicant', string='Applicant', readonly=True, store=True),
        }

    def on_change_test(self, cr, uid, ids, test_id, context=None):
        if test_id:
            return {'value': {'score': False}}
        return {}

    def _check_score(self, cr, uid, ids, context=None):
        result = self.browse(cr, uid, ids, context=context)[0]
        test = result.test_id
        if test.scores:
            if result.score not in test.scores.replace(' ','').split(','):
                raise osv.except_osv(_('Invalid Score!'), _(result.score + ' is not an acceptable score for ' + test.name + '.'))
        else:
            self.pool.get('test.code').validate_score(test.name, result.score, test.low, test.high, test.score_type)
        return True
    
    _constraints=[
        (_check_score, 'Invalid Score.', ['Score'])
    ]
    
test_result()



class transcript_course(osv.osv):
    _name = "transcript.course"
    _description = "Transcript Course"
    _inherit = ["mail.thread"]

    _columns = {
        'name': fields.char('Subject', required=True, track_visibility="onchange"),
        'max': fields.integer('Max Score', required=True, track_visibility="onchange"),
        'active': fields.boolean('Active')
        }

    _defaults={
        'active': True
        }
    
    def unlink(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'active': False})
        return True
    
    def create(self, cr, uid, vals, context=None):
        vals['name'] = vals['name'].strip()
        return super(transcript_course, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'name' in vals:
            vals['name'] = vals['name'].strip()
        return super(transcript_course, self).write(cr, uid, ids, vals, context=context)
  
    def _uniq_test_subject(self, cr, uid, ids, context=None):
        course = self.browse(cr, uid, ids, context=context)[0]
        course_ids = self.search(cr, uid, [('id','not in',[course.id])])
        for c in self.browse(cr, uid, course_ids):
            if c.name.lower() == course.name.lower():
                raise osv.except_osv(_('Check subject!'), _(c.name + ' already exists. Please check the name.'))
        return True

    def _check_max(self, cr, uid, ids, context=None):
        course = self.browse(cr, uid, ids, context=context)[0]
        if course.max <= 0:
            raise osv.except_osv(_('Check max!'), _('The max value must be greater than 0.'))
        return True
    
    _constraints=[
        (_uniq_test_subject, 'The subject already exists.', ['Subject']),
        (_check_max, 'Check the max score.', ['Max Score'])
    ]
    
transcript_course()


class transcript_course_app(osv.osv):
    _name = "transcript.course.app"
    _description = "Applicant Transcript Course"

    _columns = {
        'name': fields.many2one('transcript.course', 'Subject', required=True),
        'score': fields.integer('Score', required=True),
        'high_school_app_id': fields.many2one('aun.high.school.app', 'Applicant High School', required=True),
        'app_id': fields.related('high_school_app_id', 'app_id', type='many2one', relation='aun.applicant', string='Applicant', readonly=True, store=True),
        }

    def _check_score(self, cr, uid, ids, context=None):
        result = self.browse(cr, uid, ids, context=context)[0]
        subject = result.name
        if result.score < 0:
            raise osv.except_osv(_('Invalid Transcript Score!'), _('The score for ' + subject.name + ' cannot be less than 0.'))
        if result.score > subject.max:
            raise osv.except_osv(_('Invalid Transcript Score!'), _('The score for ' + subject.name + ' cannot be greater than ' + str(subject.max) + '.'))                    
        return True

    _constraints=[
        (_check_score, 'Invalid Score.', ['Score'])
    ]

    _sql_constraints = [
        ('course_student_uniq', 'unique(name, app_id)', 'One or more subjects are duplicated in your transcript!')
    ]
    
transcript_course_app()



class acceptance_password(osv.osv):
    _name = "acceptance.password"
    _description = "Change Password"
    
    _columns = {
        'name': fields.char('Name'),
        'orig_password': fields.char('Original Password', size=16, required=True),
        'new_password': fields.char('New Password', size=16, required=True),
        'confirm_password': fields.char('Confirm Password', size=16, required=True),
    }
    _defaults={
        'name': 'draft'
    }
    
    def create(self, cr, uid, vals, context=None):
        if vals['new_password'] != vals['confirm_password']:
            raise osv.except_osv(_('Check Password'), _('The new password and its confirmation must be identical.'))
        orig_ap_id = self.search(cr, SUPERUSER_ID, [])
        if orig_ap_id:
            if self.browse(cr, uid, orig_ap_id)[0].new_password != vals['orig_password']:
                raise osv.except_osv(_('Incorrect Password'), _('The old password you provided is incorrect, your password was not changed.'))
            self.unlink(cr, SUPERUSER_ID, orig_ap_id)
        vals['name'] = 'Password Changed'
        return super(acceptance_password, self).create(cr, SUPERUSER_ID, vals, context)

acceptance_password()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
