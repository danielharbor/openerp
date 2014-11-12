from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import date
from openerp import SUPERUSER_ID


class housing_room_type(osv.osv):
    _name = 'housing.room.type'
    _description = 'Room Type'
    _inherit = ["mail.thread"]
    _columns = {
            'name': fields.char('Room Type', size=64, required=True, track_visibility = "onchange"),
            'capacity': fields.selection([('1','1'), ('2','2'), ('3','3'), ('4','4'), ('5','5'),('99999','Unlimited')],'Capacity', required=True, track_visibility = "onchange"),
            'credit_limit': fields.float('Mininum Balance For Reservation', track_visibility = "onchange"),
        }
housing_room_type()


class housing_meal_type(osv.osv):
    _name = 'housing.meal.type'
    _description = 'meal Type'
    _inherit = ["mail.thread"]
    _columns = {
            'name': fields.char('Meal Type', size=64, required=True, track_visibility = "onchange"),
            'admin': fields.boolean('Admin Only'),
        }
housing_meal_type()

class housing_res_director(osv.osv):
        _name = 'housing.res.director'
        _description = 'Residence Directors'
        _inherit = ["mail.thread"]
        _columns = {
                'name': fields.many2one('res.partner', 'Residence Director', required=True, track_visibility = "onchange"),
                'rooms': fields.many2many('aun.registrar.location','rel_rd_dorm','name','rooms', 'Rooms', required=True, domain = [('location_type','=','4')], track_visibility = "onchange"),
            }
        _sql_constraints = [
        ('name_uniq', 'unique(name)', 'This Residence Director already exists!')
    ]
housing_res_director()

class housing_room_students(osv.osv):
    _name = 'housing.room.students'
    _description = 'Room/Meal Reservation'
    _inherit = ["mail.thread", 'ir.needaction_mixin']
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        for record in reads:
            name = record.student_id.name
            name = name + ' - ' + record.term_id.name.name + " " + record.term_id.year + " - " + record.dorm_id.name + " " + record.room_id.name
            res.append((record['id'], name))
        return res
    
    def on_change_term_id(self, cr, uid, ids, term_id, context=None):
        return {'value': {'campus_id': []}}
    
    def on_change_student_id(self, cr, uid, ids, context=None):
        return {'value': {'campus_id': []}}
    
    def on_change_campus_id(self, cr, uid, ids, campus_id, student_id, term_id, context=None):
        term = self.pool.get('aun.registrar.term').browse(cr,uid,term_id)
        student = self.pool.get('res.partner').browse(cr,uid,student_id)
        if (term.name.name in ['Summer I','Summer II']):
            return {'domain': {'dorm_id': [('campus_id','=',campus_id),('unavailable','=',False),('residence','=',True),('gender','in',[student.sex,'G'])]},'value': {'dorm_id': []}}
        
        return {'domain': {'dorm_id': [('campus_id','=',campus_id),('residence','=',True),('gender','in',[student.sex,'G'])]},'value': {'dorm_id': []}}

    def on_change_dorm_id(self, cr, uid, ids, dorm_id, context=None):
        ids= self.pool.get('aun.registrar.location').search(cr, uid, [('building_id','=',dorm_id),('location_type','=','4')])
        rooms = self.pool.get('aun.registrar.location').browse(cr, uid, ids)
        types = []
        for room in rooms:
            if (room.res_room_type):
                types.append(room.res_room_type.id)
        types = list(set(types))
        return {'domain': {'room_type': [('id','in',types)]},'value': {'room_type': []}}
    
    def on_change_room_type(self, cr, uid, ids, dorm_id, term_id, room_type, context=None):
        result = []
        warning ={}
        if (room_type):
            ids= self.pool.get('aun.registrar.location').search(cr, SUPERUSER_ID, [('res_room_type','=',room_type),('building_id','=',dorm_id),('isactive','=',True)])
            rooms = self.pool.get('aun.registrar.location').browse(cr, SUPERUSER_ID, ids)
            for room in rooms:
                res = self.pool.get('housing.room.students').search(cr, SUPERUSER_ID, [('term_id','=',term_id),('room_id','=',room.id),('state','not in',('cancel','reject'))])
                count = len(res)
                if (int(count) < int(room.res_room_type.capacity)):
                    result.append(room.id)
            if (result == []):
                warning = {
                    'title': _('No Available Rooms'),
                    'message': _('There are no available rooms of the selected type in this Residence Hall')
                }
        return {'domain': {'room_id': [('id','in',result)]},'value': {'room_id': []}, 'warning': warning}
    
    def on_change_room_id(self, cr, uid, ids, room_id, term_id, context=None):
        spaces = 0
        ids = self.pool.get('housing.room.students').search(cr, SUPERUSER_ID, [('term_id','=',term_id),('room_id','=',room_id),('state','not in',('cancel','reject'))])
        res = self.pool.get('housing.room.students').browse(cr, SUPERUSER_ID, ids)
        count = len(ids)
        occupants = ""
        if (res):
            for r in res:
                occupants = occupants + " " + r.student_id.name
        else:
            occupants = "None"    
        if (room_id):
            room = self.pool.get('aun.registrar.location').browse(cr, SUPERUSER_ID, room_id)
            spaces = int(room.res_room_type.capacity) - int(count)
        return {'value': {'spaces_left': spaces, 'occupants': occupants},}
    
    def case_approve(self, cr, uid, ids, context=None):
        self.charge_student(cr, uid, ids)
        self.write(cr, uid, ids, {'state': 'approve'}, context=context)
        template = self.pool.get('ir.model.data').get_object(cr, uid, 'academics', 'housing_email_approve')
        mail_obj = self.pool.get('mail.mail')
        assert template._name == 'email.template'
        for user in self.browse(cr, uid, ids, context):
            if not user.student_id.email:
                raise osv.except_osv(_("Cannot send email: user has no email address."), user.student_id.name)
            mail_id = self.pool.get('email.template').send_mail(cr, uid, template.id, user.id, True, context=context)
            mail_state = mail_obj.read(cr, uid, mail_id, ['state'], context=context)
            if mail_state and mail_state['state'] == 'exception':
                raise osv.except_osv(_("Cannot send email: no outgoing email server configured.\nYou can configure it under Settings/General Settings."), user.student_id.name)
        return True
    
    def case_reject(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'reject', 'active': False}, context=context)
        template = self.pool.get('ir.model.data').get_object(cr, uid, 'academics', 'housing_email_reject')
        mail_obj = self.pool.get('mail.mail')
        assert template._name == 'email.template'
        for user in self.browse(cr, uid, ids, context):
            if not user.student_id.email:
                raise osv.except_osv(_("Cannot send email: user has no email address."), user.student_id.name)
            mail_id = self.pool.get('email.template').send_mail(cr, uid, template.id, user.id, True, context=context)
            mail_state = mail_obj.read(cr, uid, mail_id, ['state'], context=context)
            if mail_state and mail_state['state'] == 'exception':
                raise osv.except_osv(_("Cannot send email: no outgoing email server configured.\nYou can configure it under Settings/General Settings."), user.student_id.name)

        return True
    
    def charge_students(self, cr, uid, ids, context=None):
        enrs= self.browse(cr, SUPERUSER_ID, self.search(cr, SUPERUSER_ID, [('term_id','=',118),('state','=','approve')]), context)
        i = 1
        for enr in enrs:
            print i
            if not enr.room_charge_id:
                self.charge_student(cr, uid, [enr.id])
            i = i + 1
        return True
    
    def case_done(self, cr, uid, ids, context=None):
        clearance_obj = self.pool.get('term.clearance')
        res = self.browse(cr, uid, ids,context=context)[0]
        clearance = clearance_obj.browse(cr, SUPERUSER_ID, clearance_obj.search(cr, SUPERUSER_ID, [('term_id','=',res.term_id.id),('student_id','=',res.student_id.id)]))
        if clearance:
            if clearance[0].state == 'cleared':
                self.write(cr, uid, ids, {'state': 'done'}, context=context)
            else:
                raise osv.except_osv(_('Invalid'), _('This student has not been cleared. Please see the bursar!'))
        else:
            raise osv.except_osv(_('Invalid'), _('This student has not registered for courses!'))
        return True
    
    def case_check_in(self, cr, uid, ids, context=None):
        res = self.browse(cr, uid, ids,context=context)[0]
        dup = self.pool.get('housing.room.students').search(cr,uid,[('student_id','=',res.student_id.id),('state','in',['check_in'])])
        if (dup):
            record = self.browse(cr, uid, dup[0],context=context)
            raise osv.except_osv(_("Invalid"), "This student is still checked in to " + record.room_id.building_id.name + " " + record.room_id.name + " for "+ record.term_id.name_get()[0][1] + " and must be checked out first.")

        self.write(cr, uid, ids, {'state': 'check_in'}, context=context)
        return True
    
    def case_check_out(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'check_out', 'active': False}, context=context)
        return True
    
    def case_cancel(self, cr, uid, ids, context=None):
        self.refund_student(cr, uid, ids)
        self.write(cr, uid, ids, {'state': 'cancel', 'active': False}, context=context)
        return True
    
    def case_reset(self, cr, uid, ids, context=None):
        room = self.browse(cr,uid,ids)[0]
        self.refund_student(cr, uid, ids)
        for charge in room.meal_charge_ids:
            super(housing_room_students, self).write(cr, SUPERUSER_ID, ids, {'charge_ids': [(1,charge,{'meal_id': False})]})
        self.write(cr, uid, ids, {'state': 'new', 'room_charge_id': False}, context=context)
        return True
    
    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'new'
        res = super(housing_room_students, self).create(cr, uid, vals, context)
        group = self.pool.get('ir.model.data').get_object(cr, uid, 'academics', 'group_housing_staff')
        group = cr.execute("select uid from res_groups_users_rel WHERE gid=(%s)" %group.id)
        s = cr.fetchall()
        group = []
        for a in s:
            group.append(a[0])
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_housing_staff"):
            student = self.pool.get('res.partner').browse(cr,uid,[vals['student_id']])[0]
            if student.user_ids:
                group.append(student.user_ids[0].id)
            else:
                raise osv.except_osv(_("This student does not have a user account, Contact Administrator"), student.name)
        self.message_subscribe_users(cr, SUPERUSER_ID, [res] , group, context=context)
        
        template = self.pool.get('ir.model.data').get_object(cr, uid, 'academics', 'housing_email')
        mail_obj = self.pool.get('mail.mail')
        assert template._name == 'email.template'
        for user in self.browse(cr, uid, [res], context):
            if not user.student_id.email:
                raise osv.except_osv(_("Cannot send email: user has no email address."), user.student_id.name)
            mail_id = self.pool.get('email.template').send_mail(cr, SUPERUSER_ID, template.id, user.id, True, context=context)
            mail_state = mail_obj.read(cr, SUPERUSER_ID, mail_id, ['state'], context=context)
            if mail_state and mail_state['state'] == 'exception':
                raise osv.except_osv(_("Cannot send email: no outgoing email server configured.\nYou can configure it under Settings/General Settings."), user.student_id.name)

        return res
    
    def charge_student(self, cr, uid, ids, context=None):
        room = self.browse(cr, SUPERUSER_ID, ids, context=context)[0]
        student = room.student_id
        if room.term_id.start_date:
            invoice_date = room.term_id.start_date[:10]
        else:
            raise osv.except_osv(_('No term start date!'), _('There is no start date for this term, please contact registrar!'))
        charge_obj = self.pool.get('term.charges')
        room_fee_obj = self.pool.get('room.fees')
        meal_fee_obj = self.pool.get('housing.meal.fees')
        account_obj = self.pool.get('student.account')
        fee_obj = self.pool.get('fee.structure')
        
        fee = fee_obj.search(cr, SUPERUSER_ID, [('term_id','=',room.term_id.id),('level_id','=',student.level_id.id)])
        if (fee):
            fee = fee[0]
        else:
            raise osv.except_osv(_('No Fee Structure!'), _('There is no fee structure for this term, please contact bursar!'))
        
        account = (account_obj.search(cr, SUPERUSER_ID, [('student_id','=',room.student_id.id)])
                                             or 
                     account_obj.create(cr, SUPERUSER_ID, {'student_id': room.student_id.id}))
        room_fee = room_fee_obj.search(cr, SUPERUSER_ID, [('fee_id','=',fee),('room_type','=',room.room_id.res_room_type.id)])
        if room_fee:
            room_fee = room_fee_obj.browse(cr, SUPERUSER_ID, room_fee)[0]
        else:
            raise osv.except_osv(_('No Room Charge Defined!'), _('There is no charge for this room type defined in this term, please contact bursar!'))
        if room_fee.charge > 0.0:
            charge = charge_obj.create(cr,SUPERUSER_ID,{'detail_id' : room_fee.detail_id.id,
                                                    'name': room_fee.detail_id.desc,
                                                    'term_id': room.term_id.id,
                                                    'charge':room_fee.charge,
                                                    'invoice_date': invoice_date,
                                                    'clearance_id': account[0] if type(account) == list else account,
                                                    'system': True
                                                    })
            self.write(cr,SUPERUSER_ID,room.id,{'room_charge_id': charge})
        meal_fee = meal_fee_obj.search(cr, SUPERUSER_ID, [('fee_id','=',fee),('meal_type','=',room.meal_id.id)])
        if meal_fee:
            meal_fee = meal_fee_obj.browse(cr, SUPERUSER_ID, meal_fee)[0]
        else:
            raise osv.except_osv(_('No Meal Charge Defined!'), _('There is no charge for this meal type defined in this term, please contact bursar!'))
        if meal_fee.charge > 0.0:
            super(housing_room_students, self).write(cr, SUPERUSER_ID, room.id, {'meal_charge_ids': [(0,0,{
                            'detail_id' : meal_fee.detail_id.id,
                            'name': meal_fee.detail_id.desc,
                            'term_id': room.term_id.id,
                            'charge':meal_fee.charge,
                            'invoice_date': invoice_date,
                            'clearance_id': account[0] if type(account) == list else account,
                            'system': True
                            })]}, context)    
        return True
    
    def refund_student(self, cr, uid, ids, context=None):
        for a in ids:
            room = self.browse(cr, SUPERUSER_ID, a, context=context)
            charge_obj = self.pool.get('term.charges')
            if room.room_charge_id:
                charge_obj.unlink(cr,SUPERUSER_ID,[room.room_charge_id.id])
            if room.meal_charge_ids:
                for charge in room.meal_charge_ids:
                    charge_obj.unlink(cr,SUPERUSER_ID,[charge.id])
        return True
    
   
    def _needaction_domain_get (self, cr, uid, context=None):
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_housing_staff"):
            return [('state','=','new')]
        return False
    
    def check_duplicate(self, cr, uid, ids, context=None):
        res = self.browse(cr, uid, ids,context=context)[0]
        dup = self.pool.get('housing.room.students').search(cr,uid,[('student_id','=',res.student_id.id),('term_id','=',res.term_id.id),('state','not in',['cancel','reject']),('id','!=',res.id)])
        if not dup:
            dup = self.pool.get('housing.room.students').search(cr,uid,[('student_id','=',res.student_id.id),('term_id','=',res.term_id.id),('state','in',['check_out']),('active','=',False),('id','!=',res.id)])
        if (dup):
            dup = self.browse(cr, uid, dup[0], context)
            print dup.state
            return False
        return True
    
    def check_availability(self, cr, uid, ids, context=None):
        rec = self.browse(cr, uid, ids,context=context)[0]
        res = self.pool.get('housing.room.students').search(cr, SUPERUSER_ID, [('term_id','=',rec.term_id.id),('room_id','=',rec.room_id.id),('state','not in',('cancel','reject'))])
        count = len(res)
        if (int(count) > int(rec.room_id.res_room_type.capacity)):
            return False
        return True
    
    def get_student_id(self, cr, uid, context=None):
        res = ""
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            res = user.partner_id.id
        return res
            
    _columns = {
            'term_id': fields.many2one('aun.registrar.term', 'Term', ondelete="cascade", required=True, track_visibility = "onchange"),
            'campus_id': fields.related('room_id', 'building_id', 'campus_id', type='many2one', relation="res.campus", string="Campus", store=False),
            'dorm_id': fields.related('room_id', 'building_id', type='many2one', relation="res.building", string="Building", store=True),
            'room_type': fields.related('room_id', 'res_room_type', type='many2one', relation="housing.room.type", string="Room Type", store=False),
            'room_id': fields.many2one('aun.registrar.location', 'Room', ondelete="cascade", required=True, track_visibility = "onchange"),
            'student_id': fields.many2one('res.partner', 'Student ID', ondelete="cascade", required=True, track_visibility = "onchange"),
            'meal_id': fields.many2one('housing.meal.type', 'Meal Plan', ondelete="cascade", required=True, track_visibility = "onchange"),
            'spaces_left': fields.char('Spaces Left', size=2, readonly=True, store = False),
            'occupants': fields.text('Occupants', readonly=True, store = False),
            'state': fields.selection([('draft','Draft'),('new','Submitted'), ('approve','Approved'), ('reject','Rejected'), ('done','Assigned'), ('cancel','Cancelled'),('check_in','Checked In'),('check_out','Checked Out')],'State', required=True, track_visibility = "onchange"),
            'fname': fields.related('student_id','fname',type = "char", relation="res.partner", string ="First Name", store = False, readonly = True),
            'lname': fields.related('student_id','lname',type = "char", relation="res.partner", string ="Surname", store = False, readonly = True),
            'create_date': fields.datetime('Create Date'),
            'room_charge_id': fields.many2one('term.charges', 'Housing Charge', track_visibility = "onchange"),
            'meal_charge_ids': fields.one2many('term.charges', 'meal_id', 'Meal Charges', track_visibility = "onchange"),
            'active': fields.boolean('Active')
        }
    _defaults = {
            'student_id' : get_student_id,
            'state' : 'draft',
            'active': True
        }

    _constraints =[
        (check_duplicate, """You cannot have multiple reservations for one term, Please Cancel Your Previous 
        Reservation before creating a new one""",['student ID']),
        (check_availability, "This room is fully booked, Please select another room",['Room'])
    ]
    
    def unlink(self, cr, uid, ids, context=None):
        self.case_cancel(cr,uid,ids)
        return True    
    
    
#    def _check_assignment(self, cr, uid, ids, context=None):
#        assign = self.browse(cr, uid, ids, context=context)[0]
#        assignment_obj = self.pool.get('housing.room.students')
#        assignment_ids = assignment_obj.search(cr, uid, []) 
#        all_assignments = self.browse(cr, uid, assignment_ids, context=context)
#        assignments = all_assignments[:len(all_assignments)-1]
#        for ass in assignments:
#            if ass.room_id.id == assign.room_id.id and ass.student_id.id == assign.student_id.id and ass.term_id.id == assign.term_id.id and ass.dorm_id.id == assign.dorm_id.id:
#                return False
#        return True

housing_room_students()


