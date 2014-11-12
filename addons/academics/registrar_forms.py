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
from openerp import SUPERUSER_ID

FORM_STATES = [
    ('draft', 'Draft'),
    ('pending', 'Awaiting Approval'),
    ('denied', 'Denied'),
    ('approved_waiting', 'Awaiting Registrar'),
    ('approved', 'Approved'),
    ('cancelled', 'Cancelled'),
]

class add_drop_application(osv.osv):
    _name = "add.drop.application"
    _description = "Add/Drop Form"
    _inherit=['mail.thread','ir.needaction_mixin']

    def _needaction_domain_get(self, cr, uid, context=None):
        approval_ids = self.pool.get('add.drop.approval').search(cr, uid, ['|',('write_uid','=',uid),('state','not in',['in_progress'])])
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_dean"):
            return [('state','=','pending')]
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_faculty"):
            return [('state','=','pending'),('approval_ids.id','not in',approval_ids),('section_id.faculty.faculty_id.user_id.id','in',[uid])]
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_ass_registrar"):
            return [('state','=','approved_waiting')]
        return False

    def _get_enrollment(self, cr, uid, ids, name, arg, context=None):
        res = {}
        enr_obj = self.pool.get('aun.registrar.enrollment')
        for add_drop_app in self.browse(cr, SUPERUSER_ID, ids):
            enrollment_id = enr_obj.search(cr, SUPERUSER_ID, [('student_id','=',add_drop_app.student_id.id),('section_id','=',add_drop_app.section_id.id),('lab','=',False),('state','=','registered')])
            res[add_drop_app.id] = enrollment_id[0] if enrollment_id else False
        return res
    
    def _get_name(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for add_drop_app in self.browse(cr, SUPERUSER_ID, ids):
            res[add_drop_app.id] = add_drop_app.fname + ' ' + add_drop_app.lname
        return res
    
    _columns = {
        'student_id': fields.related('add_drop_id', 'student_id', type='many2one', relation='res.partner', string='Student ID', required=True, readonly=True, store=True),
        'fname': fields.related('student_id', 'fname', type='char', string='First Name', readonly=True, store=True),
        'lname': fields.related('student_id', 'lname', type='char', string='Last Name', readonly=True, store=True),
        'student_name': fields.function(_get_name, string="Name", type='char', method=True, store=False),
        'image_medium': fields.related('student_id', 'image_medium', type='binary', readonly=True, string='Image', store=False),
        'phone': fields.related('student_id', 'phone', type='char', string='Mobile Number', readonly=True, store=False),
        'email': fields.related('student_id', 'email', type='char', string='Email', readonly=True, store=False),
        'major_ids': fields.related('student_id', 'major_ids', type='many2many', relation="aun.registrar.major", string='Major(s)', readonly=True, store=False),
        'minor_ids': fields.related('student_id', 'minor_ids', type='many2many', relation="aun.registrar.major", string='Minor(s)', readonly=True, store=False),
        'concentration_ids': fields.related('student_id', 'concentration_ids', type='many2many', relation="aun.registrar.major", string='Concentration(s)', readonly=True, store=False),
        'fname_approved': fields.char('First Name', readonly=True),
        'lname_approved': fields.char('Last Name', readonly=True),
        'phone_approved': fields.char('Mobile Number', readonly=True),
        'email_approved': fields.char('Email', readonly=True),
        'majors_approved': fields.char('Major(s)', readonly=True),
        'minors_approved': fields.char('Minor(s)', readonly=True),
        'concs_approved': fields.char('Concentration(s)', readonly=True),        
        'term_id': fields.many2one('aun.registrar.term', 'Term', required=True, track_visibility="onchange"),
        'action': fields.selection([('add','Add'),('drop','Drop')], 'Action', required=True),
        'section_id': fields.many2one('aun.registrar.section', 'Class', required=True, track_visibility="onchange"),
        'course_id': fields.related('section_id', 'course_id', type='many2one', relation='aun.registrar.course', string='Course', store=True),
        'sections': fields.many2many('aun.registrar.section', 'rel_add_drop_app_section','application_id','section_id','Section(s)'),
        'lab_ids': fields.many2many('section.lab', 'rel_add_drop_app_lab','add_drop_id','application_id', 'Lab(s)', track_visibility="onchange"),
        'grade_id': fields.many2one('aun.registrar.grade', 'Grade', domain=[('refund','=',True)], track_visibility="onchange", write=['academics.group_registrar_faculty','academics.group_registrar_dean','academics.group_registrar_ass_registrar']),
        'enrollment_id': fields.function(_get_enrollment, string='Enrollment', type='many2one', relation='aun.registrar.enrollment', method=True, store=False),
        'add_drop_id': fields.many2one('aun.add.drop', 'Add Drop', required=True),
        'approval_ids': fields.one2many('add.drop.approval', 'application_id', 'Add Drop Authorization', readonly=True),
        'state': fields.selection(FORM_STATES, 'State', readonly=True, track_visibility="onchange"),
        'active': fields.boolean('Active')
        }
    
    _defaults={
        'state': 'draft',
        'active': True
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):     
            for record in reads:
                name = record.section_id.name
                res.append((record['id'], name))
        else:
            for record in reads:
                name = record.student_id.name + '-' + record.section_id.name
                res.append((record['id'], name))
        return res

    def copy(self, cr, uid, ids, default=None, context=None):
        raise osv.except_osv(_('Invalid!'), _('You cannot duplicate an add/drop application. Please create a new one.'))
    
    def confirm(self, cr, uid, ids, context=None):
        add_drop_app = self.browse(cr, uid, ids, context=context)[0]
        student_id = add_drop_app.student_id.id
        section_id = add_drop_app.section_id.id
        lab_ids = [l.id for l in add_drop_app.lab_ids]
        add_drop_id = add_drop_app.add_drop_id.id
        action = add_drop_app.action
        if action == 'add':
            ctx = dict(add = True)
            number = 4
        else:
            ctx = dict(drop = True)
            number = 3
            enr_obj = self.pool.get('aun.registrar.enrollment')
            enrollment_id = enr_obj.search(cr, uid, [('student_id','=',student_id),('section_id','=',section_id),('lab','=',False),('state','=','registered')])
            if add_drop_app.grade_id:
                enr_obj.write(cr, uid, enrollment_id, {'grade': add_drop_app.grade_id.id}, context=context)
            else:
                enr_obj.unlink(cr, uid, enrollment_id, context=ctx)
            
            #delete any approved add applications for the section
            self.unlink(cr, uid, self.search(cr, uid, [('student_id','=',student_id),('section_id','=',section_id),('action','=','add'),('state','=','approved')]), context=dict(delete_approved = True))

        add_drop_obj = self.pool.get('aun.add.drop')
        for lab_id in lab_ids:
            add_drop_obj.write(cr, uid, [add_drop_id], {'sections': [(number, section_id)], 'labs': [(number, lab_id)]}, context=ctx)
        if not lab_ids:
            add_drop_obj.write(cr, uid, [add_drop_id], {'sections': [(number, section_id)]}, context=ctx)
        return self.write(cr, uid, ids, {'state': 'approved'}, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        add_drop_apps = self.browse(cr, uid, ids, context=context)
        approved = [ad for ad in add_drop_apps if ad.state == 'approved']
        if approved and not context.get('delete_approved'):
            raise osv.except_osv(_('Invalid!'), _('An approved add/drop application cannot be deleted.'))
        unlink_ids = [ad.id for ad in add_drop_apps if ad.state != 'cancelled']
        super(add_drop_application, self).write(cr, uid, unlink_ids, {'state': 'cancelled', 'active': False}, context=context)
        return True

    def _check_sections(self, cr, uid, ids, context=None):
        add_drop_app = self.browse(cr, uid, ids, context=context)[0]
        course = add_drop_app.section_id.course_id
        repeat_course_ids = self.search(cr, uid, [('student_id','=',add_drop_app.student_id.id),('add_drop_id','=',add_drop_app.add_drop_id.id),('course_id','=',course.id),('action','=',add_drop_app.action),('state','not in',['denied'])])
        if len(repeat_course_ids) > 1:
            raise osv.except_osv(_('Invalid!'), _(course.name + ' is duplicated in your add/drop'))
        return True
        
    def _check_labs(self, cr, uid, ids, context=None):
        add_drop_app = self.browse(cr, uid, ids, context=context)[0]
        section = add_drop_app.section_id
        lab_ids = [lab.id for lab in add_drop_app.lab_ids]
        if section.labs and add_drop_app.state not in ['denied', 'approved']:
            section_lab_ids = [l.id for l in section.labs]
            mandatory_labs = []
            for lab in section.labs:
                if lab.mandatory and lab.id not in lab_ids:
                    mandatory_labs.append(lab.course_id.name + ' ' + lab.name)
            if mandatory_labs:
                raise osv.except_osv(_('Lab Restriction!'), _(', '.join(mandatory_labs) + [' is a mandatory lab', ' are mandatory labs'][len(mandatory_labs) > 1] + ' for ' + section.course_id.name + ' (' + section.name + ')'))
            if len(list(set(section_lab_ids) & set(lab_ids))) != section.no_of_labs:
                raise osv.except_osv(_('Lab Restriction!'), _('You must pick ' + str(section.no_of_labs) + [' lab', ' labs'][section.no_of_labs > 1] + ' for ' + section.course_id.name + ' (' + section.name + ')'))
        return True
    
    _constraints = [
        (_check_sections, 'Check sections!',['Sections']),
        (_check_labs, 'Check labs!',['Lab(s)'])
    ]

    def on_change_action(self, cr, uid, ids, action, term_id, sections, context=None):
        res = {}
        res['value'] = {'lab_ids': False, 'section_id': False}
        if action == 'add':
            res['domain'] = {'section_id': [('id','not in',sections[0][2]),('term_id','=',term_id),('state','=','active')]}
        elif action == 'drop':
            res['domain'] = {'section_id': [('id','in',sections[0][2]),('term_id','=',term_id),('state','=','active')]}
        return res

    def on_change_section(self, cr, uid, ids, action, student_id, term_id, section_id, sections, context=None):
        res = {}
        if section_id:
            allowed = True
            if action == 'add' and section_id in sections[0][2]:
                res.update({'value': {'section_id': False, 'course_id': False, 'lab_ids': False}, 'domain': {'section_id': [('id','not in',sections[0][2]),('term_id','=',term_id),('state','=','active')]}, 'warning': {'title': 'Invalid', 'message': 'You are already registered in the class you selected.'}})
                allowed = False
            elif action == 'drop' and section_id not in sections[0][2]:
                res.update({'value': {'section_id': False, 'course_id': False, 'lab_ids': False}, 'domain': {'section_id': [('id','in',sections[0][2]),('term_id','=',term_id),('state','=','active')]}, 'warning': {'title': 'Invalid', 'message': 'You cannot drop a class in which you are not registered.'}})
                allowed = False
            if allowed:
                section = self.pool.get('aun.registrar.section').browse(cr, uid, section_id)     
                if action == 'add':
                    lab_ids = [lab.id for lab in section.labs if lab.mandatory]
                else:
                    enr_obj = self.pool.get('aun.registrar.enrollment')
                    lab_enr_ids = enr_obj.search(cr, uid, [('student_id','=',student_id),('section_id','=',section_id),('lab','=',True),('state','=','registered')])
                    lab_ids = [enr.lab_id.id for enr in enr_obj.browse(cr, uid, lab_enr_ids)]
                
                res.update({'value': {'course_id': section.course_id.id, 'lab_ids': [(6, 0, lab_ids)]}})
        else:
            res.update({'value': {'course_id': False, 'lab_ids': False}})
        return res
    
    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'pending'
        add_drop = self.pool.get('aun.add.drop').browse(cr, uid, vals['add_drop_id'])
        vals['student_id'] = add_drop.student_id.id
        if vals['action'] == 'drop':
            enr_obj = self.pool.get('aun.registrar.enrollment')
            lab_enr_ids = enr_obj.search(cr, uid, [('student_id','=',vals['student_id']),('section_id','=',vals['section_id']),('lab','=',True),('state','=','registered')])
            lab_ids = [enr.lab_id.id for enr in enr_obj.browse(cr, uid, lab_enr_ids)]
            vals['lab_ids'] = [(6, 0, lab_ids)]
        res = super(add_drop_application, self).create(cr, uid, vals)
        student = self.pool.get('res.partner').browse(cr, uid, vals['student_id'])
        if not student.user_ids:
            raise osv.except_osv(_("This student does not have a user account, Contact Administrator"), student.name)
        self.message_subscribe_users(cr, SUPERUSER_ID, [res], [student.user_ids[0].id], context=context)
        self.create_add_drop_approvals(cr, SUPERUSER_ID, [res])
        return res
    
    def create_add_drop_approvals(self, cr, uid, ids, context=None):
        add_drop = self.browse(cr, uid, ids, context=context)[0]
        manager_ids = self.pool.get('add.drop.manager').search(cr, uid, [])
        if not manager_ids:
            raise osv.except_osv(_('Contact Registrar!'), _('No approval structure set!'))
        managers= self.pool.get('add.drop.manager').browse(cr, uid, manager_ids)
        approval_obj = self.pool.get('add.drop.approval')
        counter = 0
        for manager in managers:
            approval_obj.create(cr, uid, {
                                            'state':'in_progress',
                                            'manager_id':manager.id,
                                            'application_id': add_drop.id,
                                            'can_approve': [False, True][counter==0]
                                        },context=context)
            counter=1;
        return True 

add_drop_application()


class add_drop_manager(osv.osv):
    _name='add.drop.manager'
    _description='Add Drop Manager'
    _inherit=['mail.thread']
    _order='sequence ASC'
    
    def _get_sequence(self, cr, uid, context=None):
        ids = self.search(cr, uid, [])
        if not ids:
            return 0
        manager = self.browse(cr, uid, [ids[-1]])[0]
        return manager.sequence + 1;
    
    def unlink(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'active': False}, context=context)    
    
    def onchange_type(self, cr, uid, ids):
        return {'value': {'employee_id': False,'employee_ids': False, 'role': False}}
        
    _columns={
              'employee_id': fields.many2one('hr.employee', 'Employee', track_visibility='onchange'),
              'employee_ids': fields.many2many('hr.employee', 'rel_add_drop_employee', 'manager_id', 'employee_id', 'Employees', track_visibility='onchange'),
              'name': fields.char('Name', size=32,required=True, track_visibility='onchange'),
              'type': fields.selection([('department', 'By School')], 'Approval Type', track_visibility='onchange'),
              'role': fields.selection([('instructor', 'Instructor'), ('dean', 'Dean')], 'Role', track_visibility='onchange'),
              'sequence': fields.integer('Sequence', required=True, track_visibility='onchange'),
              'active': fields.boolean('True')
            }
    
    _defaults={
            'active': True,
            'sequence': _get_sequence
            }
          
add_drop_manager()


class add_drop_approval(osv.osv):
    _name='add.drop.approval'
    _description='Add Drop Approval'
    _columns={
              'application_id': fields.many2one('add.drop.application', 'Add Drop', ondelete='cascade'),
              'manager_id': fields.many2one('add.drop.manager', 'Approval'),              
              'state': fields.selection([('in_progress', 'Awaiting Approval'),('approved','Approved'),('denied','Denied')],'Approval State'),
              'create_date': fields.datetime('Created Date'),
              'write_date': fields.datetime('Processed Date'),
              'write_uid': fields.many2one('res.users', 'Processed By'),
              'can_approve': fields.boolean('Can Approve')
            }
    _defaults={
               'state': 'in_progress'
            }
    
    def _process_approvals(self, cr, uid, ids, approval, context=None):
        if approval.can_approve:
            self.write(cr, uid, ids, {'state':'approved'})
            if self.search(cr, uid, [('id', 'in', [approval.id+1])]):
                self.write(cr, uid, [approval.id+1], {'can_approve':True})
            new_approval = self.browse(cr, uid, ids, context=context)[0]
            approvals = new_approval.application_id.approval_ids
            overall_approval = True
            for approval in approvals:
                if approval.state != 'approved':
                    overall_approval = False
            if overall_approval:
                add_drop = approval.application_id
                self.pool.get('add.drop.application').write(cr, uid, [approval.application_id.id], {'state': 'approved_waiting',
                                                                                                   'fname_approved': add_drop.fname,
                                                                                                   'lname_approved': add_drop.lname,
                                                                                                   'phone_approved': add_drop.phone,
                                                                                                   'email_approved': add_drop.email,
                                                                                                   'majors_approved': ', '.join([m.name for m in add_drop.major_ids]),
                                                                                                   'minors_approved': ', '.join([m.name for m in add_drop.minor_ids]),
                                                                                                   'concs_approved': ', '.join([c.name for c in add_drop.concentration_ids])
                                                                                                   }, context=context)
            else:
                self.pool.get('add.drop.application').write(cr, uid, [approval.application_id.id], {'state': 'pending'}, context=context)
                
        else:
            approval = self.browse(cr, uid, [approval.id-1], context=context)[0]
            raise osv.except_osv(('Warning!'),('%s\'s approval is needed!' %(approval.manager_id.name)))    
        return True
    
    def _process_denials(self, cr, uid, ids, deny, context=None):
        if deny.can_approve:
            self.write(cr, uid, ids, {'state':'denied'})
            self.pool.get('add.drop.application').write(cr, uid, [deny.application_id.id], {'state':'denied'}, context=context)
        else:
            approval = self.browse(cr, uid, [deny.id-1], context=context)[0]
            raise osv.except_osv(('Warning!'),('%s\'s approval is needed!' %(approval.manager_id.name)))    
        return True
    
    def _approve_or_deny(self, cr, uid, ids, value, context=None):
        approval = self.browse(cr, uid, ids, context=context)[0]
        add_drop_app = approval.application_id
        if approval.application_id.state == 'cancelled':
            raise osv.except_osv(('Invalid!'),('You cannot approve or deny a cancelled application'))
        #registrar says not needed
#         if add_drop_app.action == 'drop' and value == 'approve' and not add_drop_app.grade_id:
#             raise osv.except_osv(('Invalid!'),('You need to assign a grade before approving the application'))
        if approval.manager_id.role =='instructor':
            instructor_user_id = dean_user_id = False
            dean_user_ids= []
            if add_drop_app.section_id.primary_faculty_user_id:
                instructor_user_id = add_drop_app.section_id.primary_faculty_user_id.id
            if add_drop_app.section_id.course_id.subject_id.school_id.name.manager_id:
                dean_user_id = add_drop_app.section_id.course_id.subject_id.school_id.name.manager_id.user_id.id
            if approval.application_id.section_id.course_id.subject_id.school_id.name.manager_ids:
                dean_user_ids = [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, [x.id for x in add_drop_app.section_id.course_id.subject_id.school_id.name.manager_ids])]
            if (instructor_user_id == uid or dean_user_id == uid or uid in dean_user_ids):
                if value=='approve':
                    self._process_approvals(cr, uid, ids, approval)
                elif value=='deny':
                    self._process_denials(cr, uid, ids, approval)
            else:
                if value=='approve':
                    raise osv.except_osv(('Warning!'),('You cannot approve this add drop.'))
                elif value=='deny':
                    raise osv.except_osv(('Warning!'),('You cannot deny this add drop.'))
        elif approval.manager_id.role =='dean':
            if add_drop_app.section_id.course_id.subject_id.school_id.name.manager_id:
                dean_user_id = add_drop_app.section_id.course_id.subject_id.school_id.name.manager_id.user_id.id
                dean_user_ids = []
                if add_drop_app.section_id.course_id.subject_id.school_id.name.manager_ids:
                    dean_user_ids = [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, [x.id for x in approval.application_id.section_id.course_id.subject_id.school_id.name.manager_ids])]
                if (dean_user_id == uid or uid in dean_user_ids):
                    if value=='approve':
                        self._process_approvals(cr, uid, ids, approval)
                    elif value=='deny':
                        self._process_denials(cr, uid, ids, approval)  
                else:
                    if value=='approve':
                        raise osv.except_osv(('Warning!'),('You cannot approve this add drop.'))
                    elif value=='deny':
                        raise osv.except_osv(('Warning!'),('You cannot deny this add drop.'))
        else:
            employee_user_ids = [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, [x.id for x in approval.manager_id.employee_ids])]
            if(approval.manager_id.employee_id.user_id.id == uid or uid in employee_user_ids):
                    if value=='approve':
                        self._process_approvals(cr, uid, ids, approval)
                    elif value=='deny':
                        self._process_denials(cr, uid, ids, approval)
            else:
                if value=='approve':
                    raise osv.except_osv(('Warning!'),('You cannot approve this add drop.'))
                elif value=='deny':
                    raise osv.except_osv(('Warning!'),('You cannot deny this add drop.'))
        return True

    def approve(self, cr, uid, ids, context=None):
        self._approve_or_deny(cr, uid, ids, 'approve', context)
        return True
    
    def deny(self, cr, uid, ids, context=None):
        self._approve_or_deny(cr, uid, ids, 'deny', context)
        return True

add_drop_approval()


class aun_registrar_override(osv.osv):
    _name = "aun.registrar.override"
    _description = "Course Override"
    _inherit=['mail.thread','ir.needaction_mixin']

    def _needaction_domain_get(self, cr, uid, context=None):
        approval_ids = self.pool.get('override.approval').search(cr, uid, [('write_uid','=',uid)])
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_dean"):
            return [('state','=','pending')]
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_faculty"):
            return [('state','=','pending'),('faculty_approved','=',False),('approval_ids.id','not in',approval_ids),('section_id.faculty.faculty_id.user_id.id','in',[uid])]
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_ass_registrar"):
            return [('state','=','approved_waiting')]
        return False

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):       
            for record in reads:
                name = 'Override ' + record.section_id.name
                res.append((record['id'], name))
        else:
            for record in reads:
                name = 'Override ' + record.student_id.name + '-' + record.section_id.name
                res.append((record['id'], name))
        return res
    
    _columns = {
        'student_id': fields.many2one('res.partner', 'Student', required=True, domain=[('student','=',True)], track_visibility="onchange"),
        'fname': fields.related('student_id', 'fname', type='char', string='First Name', readonly=True, store=False),
        'lname': fields.related('student_id', 'lname', type='char', string='Last Name', readonly=True, store=False),
        'phone': fields.related('student_id', 'phone', type='char', string='Mobile Number', readonly=True, store=False),
        'email': fields.related('student_id', 'email', type='char', string='Email', readonly=True, store=False),
        'section_id': fields.many2one('aun.registrar.section', 'Section', required=True, track_visibility="onchange"),
        'course_id': fields.related('section_id', 'course_id', type='many2one', relation='aun.registrar.course', string='Course', readonly=True, store=True),
        'term_id': fields.many2one('aun.registrar.term', 'Term', required=True, domain=['|',('is_active','=',True),('open_for_registration','=',True)], track_visibility="onchange"),
        'major_ids': fields.related('student_id', 'major_ids', type='many2many', relation="aun.registrar.major", string='Major(s)', readonly=True, store=False),
        'minor_ids': fields.related('student_id', 'minor_ids', type='many2many', relation="aun.registrar.major", string='Minor(s)', readonly=True, store=False),
        'concentration_ids': fields.related('student_id', 'concentration_ids', type='many2many', relation="aun.registrar.major", string='Concentration(s)', readonly=True, store=False),
        'override_prerequisite': fields.boolean('Override Prerequisite(s)', track_visibility="onchange"),
        'override_corequisite': fields.boolean('Override Corequisite(s)', track_visibility="onchange"),
        'override_repeat_limit': fields.boolean('Override Repeat Limit', track_visibility="onchange"),
        'override_time_conflict': fields.boolean('Override Time Conflict', track_visibility="onchange"),
        'override_class_size': fields.boolean('Override Class Size', track_visibility="onchange"),
        'override_status': fields.boolean('Override Academic Status', track_visibility="onchange"),
        'override_level': fields.boolean('Override Level', track_visibility="onchange"),
#         'override_major': fields.boolean('Override Major', track_visibility="onchange"),
        'student_approved': fields.related('student_id', type='many2one', relation='res.partner', string='Student ID', readonly=True, store=False),
        'fname_approved': fields.char('First Name', readonly=True),
        'lname_approved': fields.char('Last Name', readonly=True),
        'section_approved': fields.related('section_id', type='many2one', relation='aun.registrar.section', string='Section', readonly=True, store=False),
        'course_approved': fields.related('course_id', type='many2one', relation='aun.registrar.course', string='Course', readonly=True, store=False),
        'term_approved': fields.related('term_id', type='many2one', relation='aun.registrar.term', string='Term', readonly=True, store=False),
        'phone_approved': fields.char('Mobile Number', readonly=True),
        'email_approved': fields.char('Email', readonly=True),
        'majors_approved': fields.char('Major(s)', readonly=True),
        'minors_approved': fields.char('Minor(s)', readonly=True),
        'concs_approved': fields.char('Concentration(s)', readonly=True),
        'schools_approved': fields.char('School(s)', readonly=True),
        'approval_ids': fields.one2many('override.approval', 'application_id', 'Override Authorization', readonly=True),
        'note': fields.text('Note', required=True),
        'note_approved': fields.related('note', type='text', string='Note', readonly=True, store=False),
        'faculty_approved': fields.boolean('Faculty Approved'),
        'state': fields.selection(FORM_STATES, 'State', readonly=True, track_visibility="onchange"),
        'image_medium': fields.related('student_id', 'image_medium', type='binary', readonly=True, string='Image', store=False),
        'active': fields.boolean('Active')
        }
    
    _defaults={
        'student_id': lambda self,cr,uid,c: self.pool.get('aun.add.drop').get_student_id(cr, uid),
        'state': 'draft',
        'active': True
    }
   
    def copy(self, cr, uid, ids, default=None, context=None):
        raise osv.except_osv(_('Invalid!'), _('You cannot duplicate an override application. Please create a new one.'))
    
    def confirm(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'approved'}, context=context)
     
    def check_overrides(self, cr, uid, ids, context=None):
        multiples = []
        override = self.browse(cr, uid, ids,context=context)[0]
        multiple_po = self.search(cr, uid, [('student_id','=',override.student_id.id),('section_id','=',override.section_id.id),('override_prerequisite','=',True),('state','not in',['denied','cancelled'])])
        multiple_co = self.search(cr, uid, [('student_id','=',override.student_id.id),('section_id','=',override.section_id.id),('override_corequisite','=',True),('state','not in',['denied','cancelled'])])
        multiple_cs = self.search(cr, uid, [('student_id','=',override.student_id.id),('section_id','=',override.section_id.id),('override_class_size','=',True),('state','not in',['denied','cancelled'])])
        multiple_tc = self.search(cr, uid, [('student_id','=',override.student_id.id),('section_id','=',override.section_id.id),('override_time_conflict','=',True),('state','not in',['denied','cancelled'])])
        multiple_rl = self.search(cr, uid, [('student_id','=',override.student_id.id),('section_id','=',override.section_id.id),('override_repeat_limit','=',True),('state','not in',['denied','cancelled'])])
        multiple_so = self.search(cr, uid, [('student_id','=',override.student_id.id),('section_id','=',override.section_id.id),('override_status','=',True),('state','not in',['denied','cancelled'])])
        multiple_lo = self.search(cr, uid, [('student_id','=',override.student_id.id),('section_id','=',override.section_id.id),('override_level','=',True),('state','not in',['denied','cancelled'])])
        if len(multiple_po) > 1:
            multiples.append('Prerequisite override')
        if len(multiple_co) > 1:
            multiples.append('Corequisite override')
        if len(multiple_cs) > 1:
            multiples.append('Class size override')
        if len(multiple_rl) > 1:
            multiples.append('Repeat limit override')
        if len(multiple_tc) > 1:
            multiples.append('Time conflict override')
        if len(multiple_so) > 1:
            multiples.append('Status override')
        if len(multiple_lo) > 1:
            multiples.append('Level override')
        if multiples:
            raise osv.except_osv(_('Invalid!'), _('You have already applied for the following overrides for this class: \n' + ', '.join(multiples)))
        if not (override.override_prerequisite or override.override_corequisite or override.override_repeat_limit or override.override_class_size or override.override_time_conflict or override.override_status or override.override_level):
            raise osv.except_osv(_('No override selected!'), _('You must check at least one override.'))
        return True
        
    _constraints=[
        (check_overrides, 'Check override.',['Override'])
    ]

    def on_change_section(self, cr, uid, ids, section_id, context=None):
        res = {}
        res.update({'value': {'course_id': False}})
        if section_id:
            section = self.pool.get('aun.registrar.section').browse(cr, uid, section_id)
            res.update({'value': {'course_id': section.course_id.id}})
        return res

    def on_change_term(self, cr, uid, ids, term_id, section_id, context=None):
        res = {}
        if term_id and section_id:
            section = self.pool.get('aun.registrar.section').browse(cr, uid, section_id)
            if section.term_id.id != term_id:
                res.update({'value': {'section_id': False}})
        return res
    
    def on_change_student(self, cr, uid, ids, student_id, context=None):
        res = {}
        res['value'] = {}
        if student_id:
            student = self.pool.get('res.partner').browse(cr, uid, student_id)
            res['value'] = {'fname': student.fname, 'lname': student.lname, 'image_medium': student.image_medium} 
        else:
            res['value'] = {'fname': False, 'lname': False, 'image_medium': False}
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        overrides = self.browse(cr, uid, ids, context=context)
        approved = [ad for ad in overrides if ad.state == 'approved']
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_registrar"):
            pass
        elif approved:
            raise osv.except_osv(_('Invalid!'), _('You cannot delete an approved override application.'))
        unlink_ids = [ad.id for ad in overrides if ad.state != 'cancelled']
        return super(aun_registrar_override, self).write(cr, uid, unlink_ids, {'state': 'cancelled', 'active': False}, context=context)
    
    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'pending'
        res = super(aun_registrar_override, self).create(cr, uid, vals)
        student = self.pool.get('res.partner').browse(cr, uid, vals['student_id'])
        if not student.user_ids:
            raise osv.except_osv(_("This student does not have a user account, Contact Administrator"), student.name)
        self.message_subscribe_users(cr, SUPERUSER_ID, [res], [student.user_ids[0].id], context=context)
        self.create_override_approvals(cr, SUPERUSER_ID, [res])
        return res
    
    def create_override_approvals(self, cr, uid, ids, context=None):
        override = self.browse(cr, uid, ids, context=context)[0]
        manager_ids = self.pool.get('override.manager').search(cr, uid, [])
        if not manager_ids:
            raise osv.except_osv(_('Contact Registrar!'), _('No approval structure set!'))
        managers = self.pool.get('override.manager').browse(cr, uid, manager_ids)
        approval_obj = self.pool.get('override.approval')
        counter = 0
        for manager in managers:
            approval_obj.create(cr, uid, {
                                            'state': 'in_progress',
                                            'manager_id': manager.id,
                                            'application_id': override.id,
                                            'can_approve': [False, True][counter==0]
                                        }, context=context)
            counter=1;
        return True
    
aun_registrar_override()


class override_manager(osv.osv):
    _name='override.manager'
    _description='Override Manager'
    _inherit=['mail.thread']
    _order='sequence ASC'
    
    def _get_sequence(self, cr, uid, context=None):
        ids = self.search(cr, uid, [])
        if not ids:
            return 0
        manager = self.browse(cr, uid, [ids[-1]])[0]
        return manager.sequence + 1;
    
    def unlink(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'active': False}, context=context)
    
    def onchange_type(self, cr, uid, ids):
        return {'value': {'employee_id': False,'employee_ids': False, 'role': False}}
        
    _columns={
              'employee_id': fields.many2one('hr.employee', 'Employee', track_visibility='onchange'),
              'employee_ids': fields.many2many('hr.employee', 'rel_override_employee', 'manager_id', 'employee_id', 'Employees', track_visibility='onchange'),
              'name': fields.char('Name', size=32,required=True, track_visibility='onchange'),
              'type': fields.selection([('department', 'By School')], 'Approval Type', track_visibility='onchange'),
              'role': fields.selection([('instructor', 'Instructor'), ('dean', 'Dean')], 'Role', track_visibility='onchange'),
              'sequence': fields.integer('Sequence', required=True, track_visibility='onchange'),
              'active': fields.boolean('Active')
            }
    
    _defaults={
            'active': True,
            'sequence': _get_sequence
            }
          
override_manager()


class override_approval(osv.osv):
    _name='override.approval'
    _description='Override Approval'
    _columns={
              'application_id': fields.many2one('aun.registrar.override', 'Override', ondelete='cascade'),
              'manager_id': fields.many2one('override.manager', 'Approval'),
              'state': fields.selection([('in_progress', 'Awaiting Approval'),('approved','Approved'),('denied','Denied')],'Approval State'),
              'create_date': fields.datetime('Created Date'),
              'write_date': fields.datetime('Processed Date'),
              'write_uid': fields.many2one('res.users', 'Processed By'),
              'can_approve': fields.boolean('Can Approve')
            }
    _defaults={
               'state': 'in_progress'
            }
    
    def _process_approvals(self, cr, uid, ids, approval, context=None):
        if approval.can_approve:
            override_obj = self.pool.get('aun.registrar.override')
            override = approval.application_id
            self.write(cr, uid, ids, {'state':'approved'})
            if approval.manager_id.role == 'instructor':
                override_obj.write(cr, uid, [override.id], {'faculty_approved': True})
            if self.search(cr, uid, [('id', 'in', [approval.id+1])]):
                self.write(cr, uid, [approval.id+1], {'can_approve':True})
            new_approval = self.browse(cr, uid, ids, context=context)[0]
            approvals = new_approval.application_id.approval_ids
            overall_approval = True
            for approval in approvals:
                if approval.state != 'approved':
                    overall_approval = False
            if overall_approval:
                override_obj.write(cr, uid, [override.id], {'state': 'approved_waiting',
                                                           'fname_approved': override.fname,
                                                           'lname_approved': override.lname,
                                                           'phone_approved': override.phone,
                                                           'email_approved': override.email,
                                                           'majors_approved': ', '.join([m.name for m in override.major_ids]),
                                                           'minors_approved': ', '.join([m.name for m in override.minor_ids]),
                                                           'concs_approved': ', '.join([c.name for c in override.concentration_ids])
                                                          }, context=context)
        else:
            approval = self.browse(cr, uid, [approval.id-1], context=context)[0]
            raise osv.except_osv(('Warning!'),('%s\'s approval is needed!' %(approval.manager_id.name)))    
        return True
    
    def _process_denials(self, cr, uid, ids, deny, context=None):
        if deny.can_approve:
            self.write(cr, uid, ids, {'state':'denied'})
            self.pool.get('aun.registrar.override').write(cr, uid, [deny.application_id.id], {'state':'denied'}, context=context)
        else:
            approval = self.browse(cr, uid, [deny.id-1], context=context)[0]
            raise osv.except_osv(('Warning!'),('%s\'s approval is needed!' %(approval.manager_id.name)))
        return True
    
    def _approve_or_deny(self, cr, uid, ids, value, context=None):
        approval = self.browse(cr, uid, ids, context=context)[0]
        if approval.application_id.state == 'cancelled':
            raise osv.except_osv(('Invalid!'),('You cannot approve or deny a cancelled application'))
        if approval.manager_id.role == 'instructor':
            instructor_user_id = dean_user_id = False
            dean_user_ids= []
            if approval.application_id.section_id.primary_faculty_user_id:
                instructor_user_id = approval.application_id.section_id.primary_faculty_user_id.id
            if approval.application_id.section_id.course_id.subject_id.school_id.name.manager_id:
                dean_user_id = approval.application_id.section_id.course_id.subject_id.school_id.name.manager_id.user_id.id
            if approval.application_id.section_id.course_id.subject_id.school_id.name.manager_ids:
                dean_user_ids = [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, [x.id for x in approval.application_id.section_id.course_id.subject_id.school_id.name.manager_ids])]
            if (instructor_user_id == uid or dean_user_id == uid or uid in dean_user_ids):
                if value=='approve':
                    self._process_approvals(cr, uid, ids, approval)
                elif value=='deny':
                    self._process_denials(cr, uid, ids, approval)
            else:
                if value=='approve':
                    raise osv.except_osv(('Warning!'),('You cannot approve this override.'))
                elif value=='deny':
                    raise osv.except_osv(('Warning!'),('You cannot deny this override.'))
        elif approval.manager_id.role =='dean':
            if approval.application_id.section_id.course_id.subject_id.school_id.name.manager_id:
                dean_user_id = approval.application_id.section_id.course_id.subject_id.school_id.name.manager_id.user_id.id
                dean_user_ids = []
                if approval.application_id.section_id.course_id.subject_id.school_id.name.manager_ids:
                    dean_user_ids = [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, [x.id for x in approval.application_id.section_id.course_id.subject_id.school_id.name.manager_ids])]
                if (dean_user_id == uid or uid in dean_user_ids):
                    if value=='approve':
                        self._process_approvals(cr, uid, ids, approval)
                    elif value=='deny':
                        self._process_denials(cr, uid, ids, approval)  
                else:
                    if value=='approve':
                        raise osv.except_osv(('Warning!'),('You cannot approve this override.'))
                    elif value=='deny':
                        raise osv.except_osv(('Warning!'),('You cannot deny this override.'))
        else:
            employee_user_ids = [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, [x.id for x in approval.manager_id.employee_ids])]
            if(approval.manager_id.employee_id.user_id.id == uid or uid in employee_user_ids):
                if value=='approve':
                    self._process_approvals(cr, uid, ids, approval)
                elif value=='deny':
                    self._process_denials(cr, uid, ids, approval)
            else:
                if value=='approve':
                    raise osv.except_osv(('Warning!'),('You cannot approve this override.'))
                elif value=='deny':
                    raise osv.except_osv(('Warning!'),('You cannot deny this override.'))
        return True
    
    def approve(self, cr, uid, ids, context=None):
        self._approve_or_deny(cr, uid, ids, 'approve', context)
        return True
    
    def deny(self, cr, uid, ids, context=None):
        self._approve_or_deny(cr, uid, ids, 'deny', context)
        return True
        
override_approval()


class course_overload(osv.osv):
    _name = "course.overload"
    _description = "Course Overload"
    _inherit=['mail.thread','ir.needaction_mixin']

    def _needaction_domain_get(self, cr, uid, context=None):
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_dean"):
            return [('state','=','pending')]
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_ass_registrar"):
            return [('state','=','approved_waiting')]
        return False

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):       
            for record in reads:
                name = 'Overload ' + record.term_id.name_get()[0][1]
                res.append((record['id'], name))
        else:
            for record in reads:
                name = 'Overload ' + record.student_id.name + '-' + record.term_id.name_get()[0][1]
                res.append((record['id'], name))
        return res

    def _get_level_gpa_info(self, cr, uid, ids, name, arg, context=None):
        res = {}
        lg_obj = self.pool.get('level.gpa')
        term_obj = self.pool.get('aun.registrar.term')
        enr_obj = self.pool.get('aun.registrar.enrollment')
        for overload in self.browse(cr, SUPERUSER_ID, ids):
            student = overload.student_id
            res[overload.id] = {}
            res[overload.id]['cgpa'] = 0
            res[overload.id]['total_credits'] = 0
            res[overload.id]['active_credits'] = 0
            active_term_ids = term_obj.search(cr, SUPERUSER_ID, [('is_active','=',True)])
            active_enr_ids = enr_obj.search(cr, SUPERUSER_ID, [('student_id','=',student.id),('term_id','in',active_term_ids),('state','=','registered')])
            school_ids = student._get_schools_and_programs(cr, SUPERUSER_ID)[student.id]['school_ids'][0][2]
            current_level_gpa_id = lg_obj.search(cr, SUPERUSER_ID, [('student_id','=',student.id),('current','=',True)])
            res[overload.id]['active_credits'] = sum([e.credit for e in enr_obj.browse(cr, SUPERUSER_ID, active_enr_ids)])
            res[overload.id]['school_ids'] = [(6, 0, school_ids)]

            #write to dean users field
            schools = self.pool.get('aun.registrar.school').browse(cr, uid, school_ids)
            dean_user_ids = [s.name.manager_id.user_id.id for s in schools if s.name.manager_id]
            other_manager_user_ids = []
            if not dean_user_ids:
                default_school_id = self.pool.get('aun.registrar.school').search(cr, SUPERUSER_ID, [('default_school','=',True)])
                schools = self.pool.get('aun.registrar.school').browse(cr, uid, default_school_id)
                dean_user_ids = [s.name.manager_id.user_id.id for s in schools if s.name.manager_id]
            if dean_user_ids:
                for school in schools:
                    if school.name.manager_ids:
                        other_manager_user_ids += [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, [x.id for x in school.name.manager_ids])]
            user_ids = list(set(dean_user_ids + other_manager_user_ids))
            res[overload.id]['fnct_dean_user_ids'] = [(6, 0, user_ids)]
            overload_user_ids = [u.id for u in overload.dean_user_ids]
            if list(set(user_ids) - set(overload_user_ids)) or list(set(overload_user_ids) - set(user_ids)):
                self.write(cr, uid, ids, {'dean_user_ids': [(6, 0, user_ids)]}, context=context)
                
            if current_level_gpa_id:
                level_gpa = lg_obj.browse(cr, SUPERUSER_ID, current_level_gpa_id[0])
                res[overload.id]['cgpa'] = level_gpa.cgpa
                res[overload.id]['total_credits'] = level_gpa.total_credits
        return res
 
    _columns = {
        'student_id': fields.many2one('res.partner', 'Student', required=True, domain=[('student','=',True)], track_visibility="onchange"),
        'fname': fields.related('student_id', 'fname', type='char', string='First Name', readonly=True, store=False),
        'lname': fields.related('student_id', 'lname', type='char', string='Last Name', readonly=True, store=False),
        'phone': fields.related('student_id', 'phone', type='char', string='Mobile Number', readonly=True, store=False),
        'email': fields.related('student_id', 'email', type='char', string='Email', readonly=True, store=False),
        'major_ids': fields.related('student_id', 'major_ids', type='many2many', relation="aun.registrar.major", string='Major(s)', readonly=True, store=False),
        'minor_ids': fields.related('student_id', 'minor_ids', type='many2many', relation="aun.registrar.major", string='Minor(s)', readonly=True, store=False),
        'concentration_ids': fields.related('student_id', 'concentration_ids', type='many2many', relation="aun.registrar.major", string='Concentration(s)', readonly=True, store=False),
        'school_ids': fields.function(_get_level_gpa_info, string='School(s)', type='many2many', relation="aun.registrar.school", method=True, multi='level_gpa_info', store=False),
        'cgpa': fields.function(_get_level_gpa_info, string='CGPA', type='float', method=True, multi='level_gpa_info', store=False),
        'total_credits': fields.function(_get_level_gpa_info, string='Total Credits Earned', type='float', method=True, multi='level_gpa_info', store=False),
        'active_credits': fields.function(_get_level_gpa_info, string='Currently Enrolled Credits (Excluding Overload)', type='float', method=True, multi='level_gpa_info', store=False),
        'dean_user_ids': fields.many2many('res.users', 'rel_overload_user', 'overload_id', 'user_id', 'Deans'),
        'fnct_dean_user_ids': fields.function(_get_level_gpa_info, string='Deans', type='many2many', relation='res.users', method=True, multi='level_gpa_info', store=False),
        'fname_approved': fields.char('First Name', readonly=True),
        'lname_approved': fields.char('Last Name', readonly=True),
        'phone_approved': fields.char('Mobile Number', readonly=True),
        'email_approved': fields.char('Email', readonly=True),
        'majors_approved': fields.char('Major(s)', readonly=True),
        'minors_approved': fields.char('Minor(s)', readonly=True),
        'concs_approved': fields.char('Concentration(s)', readonly=True),
        'schools_approved': fields.char('School(s)', readonly=True),
        'cgpa_approved': fields.float('CGPA', readonly=True),
        'credits_approved': fields.float('Requested Credits', readonly=True),
        'total_approved': fields.float('Total Credits Earned', readonly=True),
        'active_approved': fields.float('Currently Enrolled Credits (Excluding Overload)', readonly=True),
        'image_medium': fields.related('student_id', 'image_medium', type='binary', readonly=True, string='Image', store=False),
        'term_id': fields.many2one('aun.registrar.term', 'Term', required=True, domain=['|',('is_active','=',True),('open_for_registration','=',True)], track_visibility="onchange"),
        'credits_allowed': fields.float('Requested Credits', digits=(3,2), track_visibility="onchange"),
        'approval_ids': fields.one2many('overload.approval', 'application_id', 'Override Authorization', readonly=True),
        'state': fields.selection(FORM_STATES, 'State', readonly=True, track_visibility="onchange"),
        'active': fields.boolean('Active')
        }
    
    _defaults={
        'student_id': lambda self,cr,uid,c: self.pool.get('aun.add.drop').get_student_id(cr, uid),
        'state': 'draft',
        'active': True
    }
    
    def confirm(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'approved'}, context=context)
    
    def copy(self, cr, uid, ids, default=None, context=None):
        raise osv.except_osv(_('Invalid!'), _('You cannot duplicate an overload application. Please create a new one.'))
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        overloads = self.browse(cr, uid, ids, context=context)
        approved = [ad for ad in overloads if ad.state == 'approved']
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_registrar"):
            pass
        elif approved:
            raise osv.except_osv(_('Invalid!'), _('You cannot delete an approved overload application.'))
        unlink_ids = [ad.id for ad in overloads if ad.state != 'cancelled']
        super(course_overload, self).write(cr, uid, unlink_ids, {'state': 'cancelled', 'active': False}, context=context)
        return True
    
    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'pending'
        res = super(course_overload, self).create(cr, uid, vals)
        student = self.pool.get('res.partner').browse(cr, uid, vals['student_id'])
        if not student.user_ids:
            raise osv.except_osv(_("This student does not have a user account, Contact Administrator"), student.name)
        self.message_subscribe_users(cr, SUPERUSER_ID, [res], [student.user_ids[0].id], context=context)
        self.create_overload_approvals(cr, SUPERUSER_ID, [res])
        return res
    
    def create_overload_approvals(self, cr, uid, ids, context=None):
        overload = self.browse(cr, uid, ids, context=context)[0]
        manager_ids = self.pool.get('overload.manager').search(cr, uid, [])
        if not manager_ids:
            raise osv.except_osv(_('Contact Registrar!'), _('No approval structure set!'))
        managers = self.pool.get('overload.manager').browse(cr, uid, manager_ids)
        approval_obj = self.pool.get('overload.approval')
        counter = 0
        for manager in managers:
            approval_obj.create(cr, uid, {
                                            'state': 'in_progress',
                                            'manager_id': manager.id,
                                            'application_id': overload.id,
                                            'can_approve': [False, True][counter==0]
                                        }, context=context)
            counter=1;
        return True

    def on_change_student_term(self, cr, uid, ids, student_id, term_id, field, context=None):
        res = {}
        res['value'] = {}
        if field == 'student_id':
            if student_id:
                student = self.pool.get('res.partner').browse(cr, uid, student_id)
                res['value'] = {'fname': student.fname, 'lname': student.lname, 'image_medium': student.image_medium}
            else:
                res['value'] = {'fname': False, 'lname': False, 'image_medium': False}

        res['value'].update({'credits_allowed': self.get_limits(cr, uid, student_id, term_id)['maximum_hours'][0]})
        return res
    
    def check_overloads(self, cr, uid, ids, context=None):
        overload = self.browse(cr, uid, ids,context=context)[0]
        student_id = overload.student_id.id
        term_id = overload.term_id.id
        limits = self.get_limits(cr, uid, student_id, term_id)
        limit_max = limits['maximum_hours'][0]
        if overload.credits_allowed <= limit_max:
            raise osv.except_osv(_('Credit Hour Limit!'), _('The overload amount should be greater than your current maximum credit hour limit: ' + '{0:.2f}'.format(limit_max) + ' credit hours'))
        pending_overloads = self.search(cr, uid, [('student_id','=',student_id),('term_id','=',term_id),('state','not in',['denied','cancelled'])])
        if len(pending_overloads) > 1:
            raise osv.except_osv(_('Invalid!'), _('You already have an overload application in this term. Please cancel it to create a new one.'))
        return True
  
    def get_limits(self, cr, uid, student_id, term_id, context=None):
        limits = {}
        if not student_id or not term_id:
            limits['minimum_hours'] = [0.00, '']
            limits['maximum_hours'] = [0.00, '']
        else:
            student = self.pool.get('res.partner').browse(cr, uid, student_id)
            if not student.level_id:
                raise osv.except_osv(_('Contact the Registrar!'), _('You do not have a level.'))
            if not student.standing_id:
                standing_obj = self.pool.get('aun.registrar.standing')
                default_standing_id = standing_obj.search(cr, uid, [('default_standing','=',True)])
                if not default_standing_id:
                    raise osv.except_osv(_('Contact the Registrar!'), _('There is no default standing set for students!'))
                standing = standing_obj.browse(cr, uid, default_standing_id)[0]
            else:
                standing = student.standing_id
            source_term = 'the term'
            source_standing = 'your standing'
            term = self.pool.get('aun.registrar.term').browse(cr, uid, term_id)
            ltd_obj = self.pool.get('aun.level.term.defaults')
            ltd_id = ltd_obj.search(cr, SUPERUSER_ID, [('term_term_id','=',term.name.id), ('level_id','=',student.level_id.id)])
            if not ltd_id:
                raise osv.except_osv(_('Check Term Defaults!'), _('There is no default credit hour limit in this term for the student\'s level!'))
            ltd = ltd_obj.browse(cr, SUPERUSER_ID, ltd_id)[0]
            
            if standing.minimum_hours == 0 or standing.minimum_hours < ltd.minimum_hours:
                limits['minimum_hours'] = [ltd.minimum_hours, source_term]
            else:
                limits['minimum_hours'] = [standing.minimum_hours, source_standing]
            
            if standing.maximum_hours == 0 or standing.maximum_hours > ltd.maximum_hours:
                limits['maximum_hours'] = [ltd.maximum_hours, source_term]
            else: 
                limits['maximum_hours'] = [standing.maximum_hours, source_standing]
        
        return limits
    
    _constraints = [
        (check_overloads, 'Check Overload.',['student_id'])
    ]
    
course_overload()


class overload_manager(osv.osv):
    _name='overload.manager'
    _description='Overload Manager'
    _inherit=['mail.thread']
    _order='sequence ASC'
    
    def _get_sequence(self, cr, uid, context=None):
        ids = self.search(cr, uid, [])
        if not ids:
            return 0
        manager = self.browse(cr, uid, [ids[-1]])[0]
        return manager.sequence + 1;
    
    def unlink(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'active': False}, context=context)
    
    def onchange_type(self, cr, uid, ids):
        return {'value': {'employee_id': False,'employee_ids': False, 'role': False}}
        
    _columns={
              'employee_id': fields.many2one('hr.employee', 'Employee', track_visibility='onchange'),
              'employee_ids': fields.many2many('hr.employee', 'rel_overload_employee', 'manager_id', 'employee_id', 'Employees', track_visibility='onchange'),
              'name': fields.char('Name', size=32,required=True, track_visibility='onchange'),
              'type': fields.selection([('department', 'By School')], 'Approval Type', track_visibility='onchange'),
              'role': fields.selection([('dean', 'Dean')], 'Role', track_visibility='onchange'),
              'sequence': fields.integer('Sequence', required=True, track_visibility='onchange'),
              'active': fields.boolean('Active')
            }

    _defaults={
            'active': True,
            'sequence': _get_sequence
            }

overload_manager()


class overload_approval(osv.osv):
    _name='overload.approval'
    _description='Overload Approval'
    _columns={
              'application_id': fields.many2one('course.overload', 'Override', ondelete='cascade'),
              'manager_id': fields.many2one('overload.manager', 'Approval'),              
              'state': fields.selection([('in_progress', 'Awaiting Approval'),('approved','Approved'),('denied','Denied')],'Approval State'),
              'create_date': fields.datetime('Created Date'),
              'write_date': fields.datetime('Processed Date'),
              'write_uid': fields.many2one('res.users', 'Processed By'),
              'can_approve': fields.boolean('Can Approve')
            }
    _defaults={
               'state': 'in_progress'
            }
    
    def _process_approvals(self, cr, uid, ids, approval, context=None):
        if approval.can_approve:
            self.write(cr, uid, ids, {'state': 'approved'})
            if self.search(cr, uid, [('id', 'in', [approval.id+1])]):
                self.write(cr, uid, [approval.id+1], {'can_approve':True})
            new_approval = self.browse(cr, uid, ids, context=context)[0]
            approvals = new_approval.application_id.approval_ids
            overall_approval = True
            for approval in approvals:
                if approval.state != 'approved':
                    overall_approval = False

            if overall_approval:
                student = approval.application_id.student_id
                school_ids = student._get_schools_and_programs(cr, SUPERUSER_ID)[student.id]['school_ids'][0][2]
                schl_obj = self.pool.get('aun.registrar.school')
                overload = approval.application_id
                self.pool.get('course.overload').write(cr, uid, [overload.id], {'state': 'approved_waiting',
                                                                               'fname_approved': overload.fname,
                                                                               'lname_approved': overload.lname,
                                                                               'phone_approved': overload.phone,
                                                                               'email_approved': overload.email,
                                                                               'total_approved': overload.total_credits,
                                                                               'active_approved': overload.active_credits,
                                                                               'credits_approved': overload.credits_allowed,
                                                                               'cgpa_approved': overload.cgpa,
                                                                               'majors_approved': ', '.join([m.name for m in overload.major_ids]),
                                                                               'minors_approved': ', '.join([m.name for m in overload.minor_ids]),
                                                                               'concs_approved': ', '.join([c.name for c in overload.concentration_ids]),
                                                                               'schools_approved': ', '.join([s.name.name for s in schl_obj.browse(cr, uid, school_ids)])
                                                                               }, context=context)
        else:
            approval = self.browse(cr, uid, [approval.id-1], context=context)[0]
            raise osv.except_osv(('Warning!'),('%s\'s approval is needed!' %(approval.manager_id.name)))
        return True
    
    def _process_denials(self, cr, uid, ids, deny, context=None):
        if deny.can_approve:
            self.write(cr, uid, ids, {'state':'denied'})
            self.pool.get('course.overload').write(cr, uid, [deny.application_id.id], {'state':'denied'}, context=context)
        else:
            approval = self.browse(cr, uid, [deny.id-1], context=context)[0]
            raise osv.except_osv(('Warning!'),('%s\'s approval is needed!' %(approval.manager_id.name)))    
        return True
    
    def _approve_or_deny(self, cr, uid, ids, value, context=None):
        approval = self.browse(cr, uid, ids, context=context)[0]
        student = approval.application_id.student_id
        if approval.application_id.state == 'cancelled':
            raise osv.except_osv(('Invalid!'),('You cannot approve or deny a cancelled application'))
        if approval.manager_id.role == 'dean':
            school_ids = student._get_schools_and_programs(cr, uid)[student.id]['school_ids'][0][2]
            schools = self.pool.get('aun.registrar.school').browse(cr, uid, school_ids)
            dean_user_ids = [s.name.manager_id.user_id.id for s in schools if s.name.manager_id]
            if not dean_user_ids:
                default_school_id = self.pool.get('aun.registrar.school').search(cr, SUPERUSER_ID, [('default_school','=',True)])
                schools = self.pool.get('aun.registrar.school').browse(cr, uid, default_school_id)
                dean_user_ids = [s.name.manager_id.user_id.id for s in schools if s.name.manager_id]
            if dean_user_ids:
                other_manager_user_ids = []
                for school in schools:
                    if school.name.manager_ids:
                        other_manager_user_ids += [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, [x.id for x in school.name.manager_ids])]
                if (uid in dean_user_ids or uid in other_manager_user_ids):
                    if value=='approve':
                        self._process_approvals(cr, uid, ids, approval)
                    elif value=='deny':
                        self._process_denials(cr, uid, ids, approval)
                else:
                    if value=='approve':
                        raise osv.except_osv(('Warning!'),('You cannot approve this overload.'))
                    elif value=='deny':
                        raise osv.except_osv(('Warning!'),('You cannot deny this overload.'))
            else:
                raise osv.except_osv(('Warning!'),('This overload cannot be approved or denied as no default school is set.'))
        else:
            employee_user_ids = [employee.user_id.id for employee in self.pool.get('hr.employee').browse(cr, uid, [x.id for x in approval.manager_id.employee_ids])]
            if(approval.manager_id.employee_id.user_id.id == uid or uid in employee_user_ids):
                    if value=='approve':
                        self._process_approvals(cr, uid, ids, approval)
                    elif value=='deny':
                        self._process_denials(cr, uid, ids, approval)
            else:
                if value=='approve':
                    raise osv.except_osv(('Warning!'),('You cannot approve this overload.'))
                elif value=='deny':
                    raise osv.except_osv(('Warning!'),('You cannot deny this overload.'))
        return True
    
    def approve(self, cr, uid, ids, context=None):
        self._approve_or_deny(cr, uid, ids, 'approve', context)
        return True
    
    def deny(self, cr, uid, ids, context=None):
        self._approve_or_deny(cr, uid, ids, 'deny', context)
        return True
        
overload_approval()
