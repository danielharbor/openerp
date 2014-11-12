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
from datetime import date

class clearance(osv.osv_memory):
    _name = "clearance"
    _description = "Clearance"
    
    def _calculate_values(self, cr, uid, ids, name, arg, context=None):
        res = {}
        room_obj = self.pool.get('housing.room.students')
        account_obj = self.pool.get('student.account')
        charge_obj = self.pool.get('term.charges')
        clearance_obj = self.pool.get('term.clearance')
        
        for clearance in self.browse(cr, SUPERUSER_ID, ids, context=None):
            res[clearance.id] = {}
            res[clearance.id]['credit_hours'] = 0.0
            res[clearance.id]['term_charge'] = 0.0
            t_clearance = clearance_obj.browse(cr,uid,clearance_obj.search(cr,uid,[('term_id','=',clearance.term_id.id),('student_id','=',clearance.student_id.id)]))[0]
            if t_clearance.payment_plan:
                res[clearance.id]['payment_plan'] = t_clearance.payment_plan.id
            account = account_obj.search(cr,uid, [('student_id','=',clearance.student_id.id)])[0]
            charges = charge_obj.browse(cr, uid, charge_obj.search(cr, uid, [('term_id','=',clearance.term_id.id),('clearance_id','=',account)]),context=None)
            for charge in charges:
                res[clearance.id]['term_charge'] += charge.charge
            res[clearance.id]['credit_hours'] = t_clearance.credit_hours
            room = room_obj.browse(cr,uid,room_obj.search(cr,uid,[('term_id','=',clearance.term_id.id),('student_id','=',clearance.student_id.id),('state','not in',['reject','cancel'])]))
            if room:
                res[clearance.id]['room'] = room[0].room_id.building_id.name + " " + room[0].room_id.name
                res[clearance.id]['meal_plan'] = room[0].meal_id.name
            fee_obj = self.pool.get('fee.structure')
            fee = fee_obj.browse(cr, uid, fee_obj.search(cr, uid, [('term_id','=',clearance.term_id.id),('level_id','=',clearance.student_id.level_id.id)]),context=None)[0]
            res[clearance.id]['min_balance'] = fee.min_balance
        return res
    
    _columns = {
            'student_id': fields.many2one('res.partner', 'Student', required=True, domain=[('student','=',True)]),
            'term_id': fields.many2one('aun.registrar.term', 'Term', help='Term to do clearance for', required=True),
            'override_charges': fields.boolean('Override Charges'),
            'credit_limit': fields.float('Credit/Scholarship Limit', digits=(3,2), track_visibility="onchange"),
            'credit_hours': fields.function(_calculate_values, string='Total Credit Hours', type='float', method=True, multi='clearance', store=False),
            'room': fields.function(_calculate_values, string='Room', type='char', method=True, multi='clearance', store=False),
            'meal_plan': fields.function(_calculate_values, string='Meal Plan', type='char', method=True, multi='clearance', store=False),
            'term_charge': fields.function(_calculate_values, string='Total Term Charge', type='float', method=True, multi='clearance', store=False),
            'min_balance': fields.function(_calculate_values, string='Minimum Balance for Clearance', type='float', method=True, multi='clearance', store=False),
            'payment_plan': fields.function(_calculate_values, string='Payment Plan', type='many2one', relation = "bursar.payment.plan.form", method=True, multi='clearance', store=False)
        }
    
    
    def on_change_student_id(self, cr, uid, ids, context=None):
        return {'value': {'term_id':[]}}
    
    def on_change_term_id(self, cr, uid, ids, student_id, term_id, context=None):
        if term_id and student_id:
            room_obj = self.pool.get('housing.room.students')
            account_obj = self.pool.get('student.account')
            charge_obj = self.pool.get('term.charges')
            student_obj = self.pool.get('res.partner')
            clearance_obj = self.pool.get('term.clearance')
            fee_obj = self.pool.get('fee.structure')
            clearance = clearance_obj.browse(cr,uid,clearance_obj.search(cr,uid,[('term_id','=',term_id),('student_id','=',student_id)]))
            if clearance:
                clearance = clearance[0]
            else:
                warning = {
                        'title': ('Invalid'),
                        'message': ('You have No Courses Registered For This Term!')
                    }
                return {'value': {'term_id': []}, 'warning': warning}
            if clearance.state == 'cleared':
                warning = {
                        'title': ('Invalid'),
                        'message': ('You have already done your clearance for this term!')
                    }
                return {'value': {'term_id': []}, 'warning': warning}
            payment_plan =[]
            if clearance.payment_plan:
                payment_plan = clearance.payment_plan.id
            account = account_obj.search(cr,uid, [('student_id','=',student_id)])[0]
            student = student_obj.browse(cr,uid,student_id)
            fee = fee_obj.browse(cr, uid, fee_obj.search(cr, uid, [('term_id','=',term_id),('level_id','=',student.level_id.id)]),context=None)
            if fee:
                fee = fee[0]
            else:
                warning = {
                        'title': ('Invalid'),
                        'message': ('No fee structure for this term, please contact the bursar!')
                    }
                return {'value': {'term_id': []}, 'warning': warning}
            total = 0.0
            charges = charge_obj.browse(cr, uid, charge_obj.search(cr, uid, [('term_id','=',term_id),('clearance_id','=',account)]),context=None)
            for charge in charges:
                total += charge.charge
            credit_hours = clearance.credit_hours
            room = room_obj.browse(cr,uid,room_obj.search(cr,uid,[('term_id','=',term_id),('student_id','=',student_id),('state','not in',['reject','cancel'])]))
            if room:
                room_id = room[0].room_id.building_id.name + " " + room[0].room_id.name
                meal_plan = room[0].meal_id.name
            else:
                room_id = "You have not reserved any room, proceed with clearance ONLY if you do not want to stay on campus."
                meal_plan = "You have not chosen any meal plan, proceed with clearance ONLY if you do not want a meal plan."
            return {'value': {'min_balance':fee.min_balance,'credit_hours':credit_hours,'term_charge':total,'room':room_id,'meal_plan':meal_plan,'payment_plan':payment_plan,'student_balance':clearance.student_id.credit}}
        else:
            return True
    
    def student_clearance(self, cr, uid, ids, context=None):
        dt = self.browse(cr, uid, ids, context = context)[0]
        if dt.credit_hours == 0:
            raise osv.except_osv(('Invalid!'), ('You have No Courses Registered!'))
        clearance_obj = self.pool.get('term.clearance')
        charge_obj = self.pool.get('term.charges')
        account_obj = self.pool.get('student.account')
        term_obj = self.pool.get('aun.registrar.term')
        student_obj = self.pool.get('res.partner')
        student = student_obj.browse(cr,uid,dt.student_id.id)
        account = account_obj.search(cr,uid, [('student_id','=',dt.student_id.id)])[0]
        clearance = clearance_obj.browse(cr,uid,clearance_obj.search(cr,uid,[('term_id','=',dt.term_id.id),('student_id','=',dt.student_id.id)]))[0]
        other = 0.0
        l_terms = term_obj.search(cr,uid, [('code','>',dt.term_id.code)])
        for l_term in l_terms:
            charges = charge_obj.browse(cr, uid, charge_obj.search(cr, uid, [('term_id','=',l_term),('clearance_id','=',account)]),context=None)
            for charge in charges:
                other += charge.charge
        balance = student.credit - other
        if balance <= (dt.min_balance * -1):
            clearance_obj.write(cr, uid, clearance.id, {'state': 'cleared','date_clear': date.today()}, context=context)
            warning = {
                    'title': ('Success!'),
                    'message': ('You have been successfully cleared for ' + dt.term_id.name_get()[0][1] + ', you can check into your selected room and proceed to attend classes.')
                }
        elif clearance.payment_plan:
            if balance - clearance.payment_plan.amount_due<= (dt.min_balance * -1):
                clearance_obj.write(cr, uid, clearance.id, {'state': 'cleared','date_clear': date.today()}, context=context)
                warning = {
                    'title': ('Success!'),
                    'message': ('You have been successfully cleared for ' + dt.term_id.name_get()[0][1] + ' with a payment plan, you can check into your selected room and proceed to attend classes.')
                }
            else:
                raise osv.except_osv(('Insufficient Funds'), ('You need to pay at least N'+ str(balance - clearance.payment_plan.amount_due - (dt.min_balance * -1)) + " before you can be cleared for this semester."))
        elif dt.override_charges:
            if dt.credit_limit >= (dt.term_charge + dt.min_balance):
                clearance_obj.write(cr, uid, clearance.id, {'state': 'cleared','credit_limit':dt.credit_limit,'date_clear': date.today()}, context=context)
            else:
                raise osv.except_osv(('Insufficient Funds'), ('You need to pay at least N'+ str((dt.term_charge + dt.min_balance)-dt.credit_limit) + " before you can be cleared for this semester."))

        else:
            raise osv.except_osv(('Insufficient Funds'), ('You need to pay at least N'+ str(balance - (dt.min_balance * -1)) + " before you can be cleared for this semester."))

        
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'academics', 'aun_student_action')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        return result
    
clearance()