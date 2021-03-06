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
import datetime
from datetime import date
import time
from openerp import SUPERUSER_ID,tools,netsvc
import openerp.addons.decimal_precision as dp

PAYMENT_PLAN_OPTIONS = [
    ('least', 'at least'),
    ('equal', 'equal to'),
]

# PAYMENT_PLAN_TYPES = [
#     ('percent', 'Percentage'),
#     ('fixed', 'Fixed Amount')
# ]

PAYMENT_PLAN_LINE_TYPES = [
    ('percent', 'Percentage'),
#     ('fixed', 'Fixed Amount'),
    ('balance', 'Balance')
]

PAYMENT_PLAN_STATES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('approved', 'Approved'),
    ('paid', 'Paid'),
    ('rejected', 'Rejected'),
    ('cancelled', 'Cancelled')
]

PAYMENT_PLAN_DATES = [
    ('start', 'Term Start Date'),
    ('registration_start', 'Registration Start Date'),
    ('registration_end', 'Registration End Date'),
    ('clearance', 'Clearance Date')
]

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
            'student': fields.boolean('Student'),
            'term_id': fields.many2one('aun.registrar.term', 'Term', readonly=True, states={'draft':[('readonly',False)]}, track_visibility = "onchange"),
            'detail_id': fields.many2one('detail.code','Detail Code', readonly=True, states={'draft':[('readonly',False)]}, track_visibility = "onchange"),
            'detail_name': fields.related('detail_id', 'desc', type='char', string="Detail Code", store=True, readonly=True),
        }

account_invoice()
    
class account_voucher(osv.osv):
    _inherit = 'account.voucher'
    _columns = {
            'student': fields.boolean('Student'),
            'term_id': fields.many2one('aun.registrar.term', 'Term', readonly=True, states={'draft':[('readonly',False)]}, track_visibility = "onchange"),
        }
    
    def validate_all_payments(self, cr, uid, ids, context=None):
        uid = SUPERUSER_ID
        records =  self.search(cr,uid,[('student','=',True),('state','=','draft')],order='date ASC',limit=10)
        x = 1
        for rec in records:
            print x
            r = self.browse(cr,uid,rec)
            res = self.recompute_voucher_lines(cr, uid, [r.id], r.partner_id.id, r.journal_id.id, r.amount, r.company_id.currency_id.id, r.type, r.date)
            if 'line_cr_ids' in res['value']:
                i = 0
                for a in res['value']['line_cr_ids']:
                    arr = [0,0,{}]
                    arr[2] = a
                    res['value']['line_cr_ids'][i] = tuple(arr)
                    i = i + 1
            if 'line_dr_ids' in res['value']:
                j = 0
                for a in res['value']['line_dr_ids']:
                    arr = [0,0,{}]
                    arr[2] = a
                    res['value']['line_dr_ids'][j] = tuple(arr)
                    j = j + 1
            self.write(cr, uid, r.id, res['value'])
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(SUPERUSER_ID, 'account.voucher', r.id, 'proforma_voucher', cr)
            x += 1
        return True
            
    def write(self, cr, uid, ids, vals, context=None):
        if 'state' in vals:
            state = vals['state']
        else:
            return super(account_voucher, self).write(cr, uid, ids, vals, context=context)
        account_obj = self.pool.get('student.account')
#         payment_obj = self.pool.get('term.payments')
        if state == 'posted':
            pays = self.browse(cr, uid, ids)
            for pay in pays:
                if pay.student == True and pay.type == 'receipt' and pay.amount != 0.0:
                    c_ids = account_obj.search(cr, SUPERUSER_ID, [('student_id','=',pay.partner_id.id)])
                    if not c_ids:
                        c_ids = [account_obj.create(cr, SUPERUSER_ID, {
                                                   'student_id': pay.partner_id.id,
                                                   })]
#                     name = pay.journal_id.name + " Payment"
#                     payment_obj.create(cr, uid, {
#                                                    'clearance_id': c_ids[0],
#                                                    'name': name,
#                                                    'payment': pay.amount,
#                                                    'payment_id': pay.id,
#                                                    'term_id': pay.term_id.id,
#                                                    'date': pay.date
#                                                    })
#         elif state == 'cancel':
#             for i in ids:
#                 pay = self.browse(cr, uid, i)
#                 if pay.student == True:
#                     payments = payment_obj.search(cr, uid, [('payment_id','=',i)])
#                     if payments:
#                         payment_obj.unlink(cr, uid, payments)
        return super(account_voucher, self).write(cr, uid, ids, vals, context=context)

account_voucher()

class detail_category_code(osv.osv):
    _name = 'detail.category.code'
    _columns = {
            'name': fields.char('Code', size=4, required=True),
            'desc': fields.char('Description', size=32, required=True),
            }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'This detail code category already exists')
        ]
detail_category_code()

class detail_code(osv.osv):
    _name = 'detail.code'
    _columns = {
            'category_id': fields.many2one('detail.category.code', 'Category', track_visibility = "onchange", required=True),
            'name': fields.char('Code', size=4, required=True),
            'desc': fields.char('Description', size=32, required=True),
            'priority': fields.integer('Priority'),
            'negative': fields.boolean('Allow Negative Balance After Clearance'),
            'refund': fields.boolean('Refundable'),
            'journal_id': fields.many2one('account.journal', 'Journal', required=True, domain=[('type','=','sale')], track_visibility='onchange'),
            'debit_acc': fields.many2one('account.account', 'Debit Account',required=True, domain=[('type','in',['receivable','payable'])], help="The debit account used for this detail code."),
            'income_acc': fields.many2one('account.account', 'Credit Account',required=True, help="The income account used for this detail code."),
            'fund_acc_id': fields.many2one('account.analytic.account', 'Fund Account', required=True, track_visibility='onchange'),
            'group_ids': fields.many2many('res.groups', 'rel_detail_group', 'detail_id', 'group_id', 'Groups')
            }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'This detail code already exists')
        ]
detail_code()

class refund_rule(osv.osv):
    _name = 'refund.rule'
    _order = 'start_date ASC'
    
    def _check_start_end_dates(self, cr, uid, ids, context=None):
        rule = self.browse(cr, uid, ids,context=context)[0]
        if rule.start_date and rule.end_date:
            return rule.end_date > rule.start_date
        return True
    
    def _check_percent(self, cr, uid, ids, context=None):
        rule = self.browse(cr, uid, ids,context=context)[0]
        return rule.percent < 1 and rule.percent > 0
    
    _columns = {
            'fee_id': fields.many2one('fee.structure', 'Fee Structure', required=True),
            'start_date': fields.date('From',required=True),
            'end_date': fields.date('To',required=True),
            'percent': fields.float('Percentage', help="Enter a number between 0 and 1", required=True)
            }
    _constraints=[
        (_check_start_end_dates, 'Please verify that the term end date is greater than the start date.',['Start Date',' End Date']),
        (_check_percent, 'Please verify that the percentage is between 0 and 1',['Percent']),
    ]
refund_rule()

class academics_fees(osv.osv):
    _name = 'academics.fees'
    _inherit = ["mail.thread"]
    _columns = {
            'detail_id': fields.many2one('detail.code', 'Detail Code', track_visibility = "onchange", required=True),
            'name': fields.related('detail_id', 'desc', type='char', string='Description', readonly=True),
            'charge': fields.float('Charge', track_visibility = "onchange", required=True),
            'comp_fee_id': fields.many2one('fee.structure', 'Fee', track_visibility = "onchange"),
            'other_fee_id': fields.many2one('fee.structure', 'Fee', track_visibility = "onchange"),
#             'rec_account_id': fields.many2one('account.account', ' Receivable Account', domain = "[('type','=', 'receivable')]", track_visibility = "onchange", help="The Receivable account used for this Payment."),
        }
    def on_change_detail_code(self, cr, uid, ids, detail_id, context=None):
        code_obj = self.pool.get('detail.code')
        code = code_obj.browse(cr,uid,detail_id,context)
        return {'value': {'name': code.desc}}
    
academics_fees()

class room_fees(osv.osv):
    _name = 'room.fees'
    _description = 'Room Fees'
    _columns = {
            'fee_id': fields.many2one('fee.structure', 'Fee', track_visibility = "onchange"),
            'detail_id': fields.many2one('detail.code', 'Detail Code', track_visibility = "onchange", required=True),
            'room_type': fields.many2one('housing.room.type', 'Room Type', required=True),
            'charge': fields.float('Charge', required=True),
#             'rec_acc': fields.many2one('account.account', ' Receivable Account', domain = "[('type','=', 'receivable')]", required=True, help="The Receivable account used for housing."),
        }

room_fees()

class housing_meal_fees(osv.osv):
    _name = 'housing.meal.fees'
    _description = 'Meal Fees'
    _columns = {
            'fee_id': fields.many2one('fee.structure', 'Fee', track_visibility = "onchange"),
            'detail_id': fields.many2one('detail.code', 'Detail Code', track_visibility = "onchange", required=True),
            'meal_type': fields.many2one('housing.meal.type', 'Meal Type', required=True),
            'number': fields.float('Number of Meals', required=True),
            'charge': fields.float('Charge', required=True),
#             'rec_acc': fields.many2one('account.account', ' Receivable Account', domain = "[('type','=', 'receivable')]", required=True, help="The Receivable account used for housing."),
        }
housing_meal_fees()

class fee_structure(osv.osv):
    _name = 'fee.structure'
    _rec_name = 'term_id'
    _description = 'Fees Configuration'
    _inherit = ["mail.thread"]
    
    def _refund_rules(self, cr, uid, ids, context=None):
        rules = self.browse(cr, uid, ids,context=context)[0].refund_rules
        counter = 1
        a = len(rules)
        while counter < a:
            first_date = datetime.datetime.strptime(rules[counter-1].end_date, tools.DEFAULT_SERVER_DATE_FORMAT)
            first_date = str(first_date + datetime.timedelta(days=1))[:10]
            next_date = rules[counter].start_date
            if first_date != next_date:
                return False
            counter +=1
        return True
    
    def _make_editable(self, cr, uid, ids, name, arg, context=None):
        res = {}
        invoice_obj = self.pool.get('account.invoice')
        for structure in self.browse(cr, SUPERUSER_ID, ids, context=None):
            res[structure.id] = True
            invs = invoice_obj.search(cr,uid,[('term_id','=',structure.term_id.id),('state','!=','draft')])
            if invs:
                res[structure.id] = False  
        return res

        
    _columns = {
            'term_id': fields.many2one('aun.registrar.term', 'Term', required=True, track_visibility = "onchange"),
            'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility = "onchange"),
            'tuition_detail_id': fields.many2one('detail.code', 'Detail Code', required=True, track_visibility = "onchange"),
            'tuition_price': fields.float('Price', required=True, track_visibility = "onchange"),
#             'tuition_rec_acc': fields.many2one('account.account', ' Receivable Account', domain = "[('type','=', 'receivable')]", required=True, track_visibility = "onchange", help="The Receivable account used for tuition."),
            'type': fields.selection([('credit','Per Credit'),('flat','Flat Rate')],'Fee Type', required=True, track_visibility = "onchange"), 
            'comp_fees': fields.one2many('academics.fees', 'comp_fee_id', 'Mandatory Fees', track_visibility = "onchange"),
            'housing_fees': fields.one2many('room.fees', 'fee_id', 'Housing Fees'),
            'refund_rules': fields.one2many('refund.rule', 'fee_id', 'Refund Rules'),
            'meal_fees': fields.one2many('housing.meal.fees', 'fee_id', 'Meal Fees'),
            'other_fees': fields.one2many('academics.fees', 'other_fee_id', 'Optional Fees'),
            'min_balance': fields.float('Minimum Balance for Clearance', track_visibility = "onchange"),
            'edit': fields.function(_make_editable, string='Editable', type='boolean', method=True, store=False, track_visibility="onchange")
        }
    _defaults={
            'type': 'credit',
        }
    
    _constraints=[
        (_refund_rules, 'The start date of a new line must be one day after the end date of the previous line.',['Refund Rules']),
    ]

    _sql_constraints = [
        ('term_uniq', 'unique(term_id,level_id)', 'Fee Structure for this term already exists!')
        ]
    
fee_structure()

class term_clearance(osv.osv):
    _name = 'term.clearance'
    _description = 'Term Clearance'
    _inherit = ["mail.thread"]
    _order = 'term_id DESC, student_id ASC'
    
    def case_unclear(self, cr, uid, ids, context=None):
        clearance = self.browse(cr, SUPERUSER_ID, ids, context=None)[0]
        if clearance.state == 'draft':
            raise osv.except_osv(_('Invalid'), _('This student is not cleared for the semester!'))
        self.write(cr, uid, ids, {'state': 'draft', 'date_clear': False}, context=context)
        return True
        
    def _get_clearance_values(self, cr, uid, ids, name, arg, context=None):
        res = {}
        uid = SUPERUSER_ID
        enr_obj = self.pool.get('aun.registrar.enrollment')
        room_obj = self.pool.get('housing.room.students')
        for clearance in self.browse(cr, SUPERUSER_ID, ids, context=None):
            res[clearance.id] = {}
            res[clearance.id]['credit_hours'] = 0.0
            res[clearance.id]['room_type'] = False
            res[clearance.id]['meal_plan'] = False
            enrs = enr_obj.browse(cr,uid,enr_obj.search(cr,uid,[('term_id','=',clearance.term_id.id),('student_id','=',clearance.student_id.id),('state','=','registered')]))
            for enr in enrs:
                res[clearance.id]['credit_hours'] += enr.credit
            room = room_obj.browse(cr,uid,room_obj.search(cr,uid,[('term_id','=',clearance.term_id.id),('student_id','=',clearance.student_id.id),('state','not in',['reject','cancel'])]))
            if room:
                res[clearance.id]['room_type'] = room[0].room_type.id
                res[clearance.id]['meal_plan'] = room[0].meal_id.id
        return res
    
    
    
    _columns = {
            'student_id': fields.many2one('res.partner', 'Student', domain=[('student','=',True)], required=True, readonly=True),
            'term_id': fields.many2one('aun.registrar.term', 'Term', required=True, readonly=True),
            'credit_hours': fields.function(_get_clearance_values, string='Credit Hours', type='float', method=True, multi='clearance', store=False, track_visibility="onchange"),
            'room_id': fields.function(_get_clearance_values, string='Room', type='many2one', method=True, relation='housing.room.students', multi='clearance', store=False, track_visibility="onchange"),
            'room_type': fields.function(_get_clearance_values, string='Room Type', type='many2one', method=True, relation='housing.room.type', multi='clearance', store=False, track_visibility="onchange"),
            'meal_plan': fields.function(_get_clearance_values, string='Meal Type', type='many2one', method=True, relation='housing.meal.type', multi='clearance', store=False, track_visibility="onchange"),
            'fee_charge': fields.boolean('Fee Charges', readonly=True),
            'credit_limit': fields.float('Credit Limit', digits=(3,2), track_visibility="onchange"),
            'payment_plan': fields.many2one('bursar.payment.plan.form', 'Payment Plan', readonly=True),
            'state': fields.selection([('draft','Not Cleared'), ('cleared','Cleared')],'State', readonly=True, track_visibility="onchange"),
            'date_clear': fields.date('Date Cleared')
    }
    _defaults={
        'state': 'draft',
        }
    
term_clearance()

class student_account(osv.osv):
    _name = 'student.account'
    _description = 'Student Account'
    _inherit = ["mail.thread"]
    _order = 'student_id ASC'

    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for clearance in self.browse(cr, SUPERUSER_ID, ids, context=context):
            res[clearance.id] = {
                'total_charge': 0.0,
                'total_payment': 0.0,
#                 'balance': 0.0,
            }
            for charge in clearance.charges:
                res[clearance.id]['total_charge'] += charge.charge
            for payment in clearance.payments:
                res[clearance.id]['total_payment'] += payment.payment
#             res[clearance.id]['balance'] = res[clearance.id]['total_charge'] - res[clearance.id]['total_payment']
            
        return res
    

    _columns = {
            'student_id': fields.many2one('res.partner', 'Student ID', readonly=True, required=True, track_visibility = "onchange"),
            'applicant': fields.boolean('Applicant', readonly=True),
            'name': fields.related('student_id', 'name', type='char', relation="res.partner", string="Student"),
            'charges': fields.one2many('term.charges','clearance_id', 'Charges'),
            'payments': fields.related('student_id','payment_ids', type='one2many', relation='account.voucher', string='Payments', readonly=True, groups="academics.group_bursary_staff,academics.group_registrar_student"),
#             'balance': fields.function(_amount_all, type = 'float', digits_compute=dp.get_precision('Account'), string='Total Balance', track_visibility='onchange', multi='all'),
            'p_balance': fields.related('student_id', 'credit', type='float', relation="res.partner", string="Balance", store=False, readonly=True, track_visibility = "onchange"),
            'fname': fields.related('student_id', 'fname', type='char', relation="res.partner", string="First Name", store=False, readonly=True),
            'lname': fields.related('student_id', 'lname', type='char', relation="res.partner", string="Last Name", store=False, readonly=True),
            'payment_plan_id': fields.many2one('bursar.payment.plan.form', 'Active Payment Plan', readonly=True, track_visibility = "onchange"),
        }

    _sql_constraints = [
        ('student_uniq', 'unique(student_id)', 'Student account already exists!')
        ]
    
student_account()

class term_charges(osv.osv):
    _name = 'term.charges'
    _description = 'Term Charges'
    _inherit = ["mail.thread"]
    _order = 'term_id DESC, invoice_date DESC'
    
    def on_change_detail_code(self, cr, uid, ids, detail_id, context=None):
        if not detail_id:
            return {}
        code =self.pool.get('detail.code').browse(cr, uid, detail_id)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        if not self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_bursary_staff"):
            if code.group_ids and (not(set(user.groups_id) & set(code.group_ids))):
                return {'value': {'detail_id': False,'name': False}, 'warning': {'title': _('Detail Code Restriction'), 'message': _('You are not allowed to charge a student with this detail code!')}}
        return {'value': {'name': code.desc}}
    
    def on_change_term_id(self, cr, uid, ids, student_id, detail_id, term_id, context=None):
        fee_obj = self.pool.get('fee.structure')
        acad_fee_obj = self.pool.get('academics.fees')
        student = self.pool.get('res.partner').browse(cr,uid,student_id)
        price = 0.0
        fee = fee_obj.browse(cr, SUPERUSER_ID, fee_obj.search(cr, SUPERUSER_ID, [('term_id','=',term_id),('level_id','=',student.level_id.id)]))
        if fee:
            fee = fee[0]
            detail_fee = (acad_fee_obj.browse(cr, SUPERUSER_ID, acad_fee_obj.search(cr, SUPERUSER_ID, [('comp_fee_id','=',fee.id),('detail_id','=',detail_id)])) or
            acad_fee_obj.browse(cr, SUPERUSER_ID, acad_fee_obj.search(cr, SUPERUSER_ID, [('other_fee_id','=',fee.id),('detail_id','=',detail_id)])))
            if detail_fee:
                price = detail_fee[0].charge
        else:
            warning = {
                        'title': ('Invalid'),
                        'message': ('No fee structure for this term, please contact the bursar!')
                        }
            return {'warning': warning}
        return {'value': {'charge': price}}
    
    def create(self, cr, uid, vals, context=None):
        fee_obj = self.pool.get('fee.structure')
        invoice_obj = self.pool.get('account.invoice')
        code_obj = self.pool.get('detail.code')
        invoice_line_obj = self.pool.get('account.invoice.line')
        code = code_obj.browse(cr,uid,vals['detail_id'],context)
        if vals['charge'] == 0.0:
            return True
        if 'invoice_date' not in vals:
            vals['invoice_date'] = date.today()
        res = super(term_charges, self).create(cr, uid, vals, context)
        charge = self.browse(cr,uid,res,context)
        if vals['charge'] < 0:
            if uid != SUPERUSER_ID:
                if code.refund:
                    if not self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_bursary_staff"):
                        raise osv.except_osv(_('Invalid'), _('You are not allowed reverse transactions!'))
                else:
                    raise osv.except_osv(_('Invalid'), _('This detail code is not refundable'))
        else:
            fee = fee_obj.browse(cr, SUPERUSER_ID, fee_obj.search(cr, SUPERUSER_ID, [('term_id','=',charge.term_id.id),('level_id','=',charge.clearance_id.student_id.level_id.id)]))
            if (fee):
                fee = fee[0]
            else:
                raise osv.except_osv(_('No Fee Structure!'), _('There is no fee structure for this term, please contact bursar!'))
            if code.negative == False:
                clearance_obj = self.pool.get('term.clearance')
                clearance = clearance_obj.browse(cr, SUPERUSER_ID, clearance_obj.search(cr, SUPERUSER_ID, [('term_id','=',charge.term_id.id),('student_id','=',charge.clearance_id.student_id.id)]))
                if clearance:
                    if clearance[0].state == 'cleared':
                        if clearance[0].payment_plan and clearance[0].payment_plan.state != 'paid':
                            sql = "SELECT SUM(charge) FROM term_charges WHERE term_id =" + str(charge.term_id.id) + 'and clearance_id =' + str (charge.clearance_id.id)
                            cr.execute(sql)
                            total_charges = cr.fetchone()
                            if clearance[0].payment_plan.amount_due - total_charges[0] < 0.0:
                                raise osv.except_osv(_('Invalid'), _('This transaction exceeds your active payment plan allowance by ₦'+ str(-(clearance[0].payment_plan.amount_due - total_charges[0]))))
                        elif vals['charge'] > (charge.clearance_id.student_id.credit * -1):
                            if clearance[0].credit_limit > 0.0:
                                sql = "SELECT SUM(charge) FROM term_charges WHERE term_id =" + str(charge.term_id.id) + 'and clearance_id =' + str (charge.clearance_id.id)
                                cr.execute(sql)
                                total_charges = cr.fetchone()
                                if (clearance[0].credit_limit - total_charges[0]) < 0.0:
                                    raise osv.except_osv(_('Invalid'), _('This transaction exceeds your current credit/scholarship limit allowance by ₦'+ str(-(clearance[0].credit_limit - total_charges[0]))))
                            else:
                                raise osv.except_osv(_('Insufficient Funds'), _('You do not have enough money in your student account to complete this action.'))
                    elif clearance[0].state != 'cleared' and clearance[0].payment_plan:
                        sql = "SELECT SUM(charge) FROM term_charges WHERE term_id =" + str(charge.term_id.id) + 'and clearance_id =' + str (charge.clearance_id.id)
                        cr.execute(sql)
                        total_charges = cr.fetchone()
                        if clearance[0].payment_plan.amount_due - total_charges[0] < 0.0:
                            raise osv.except_osv(_('Invalid'), _('This transaction exceeds your active payment plan allowance by ₦'+ str(-(clearance[0].payment_plan.amount_due - total_charges[0])) + '. Please adjust your payment plan before proceeding.'))
        invoice = invoice_obj.create(cr,SUPERUSER_ID,{
                               'name': vals['name'],
                               'partner_id': charge.clearance_id.student_id.id,
                               'state': "draft",
                               'account_id': charge.detail_id.debit_acc.id,
                               'term_id': vals['term_id'],
                               'student': 1,
                               'user_id': uid,
                               'date_invoice': vals['invoice_date'],
                               'detail_id' : vals['detail_id'],
                               'journal_id': charge.detail_id.journal_id.id
                               })
        invoice_line_obj.create(cr,SUPERUSER_ID,{
                               'invoice_id': invoice,
                               'quantity': 1,
                               'account_id': charge.detail_id.income_acc.id,
                               'account_analytic_id': charge.detail_id.fund_acc_id.id,
                               'name': vals['name'],
                               'price_unit': vals['charge']
                               })
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(SUPERUSER_ID, 'account.invoice', invoice, 'invoice_open', cr)
        self.write(cr, uid, res, {'invoice_id': invoice})
        return res
    
        
    def unlink(self, cr, uid, ids, context=None):
        fee_obj = self.pool.get('fee.structure')
        invoice_obj = self.pool.get('account.invoice')
        d= str(date.today())
        for charge in self.browse(cr,uid,ids):
            fee = fee_obj.browse(cr,uid,fee_obj.search(cr,uid,[('term_id','=',charge.term_id.id),('level_id','=',charge.clearance_id.student_id.level_id.id)]))[0]
            percent = 0
            if fee.refund_rules:
                rules = fee.refund_rules
                if d < rules[0].start_date:
                    percent = 1
                else:
                    for rule in rules:
                        if rule.end_date >= d and d >= rule.start_date:
                            percent = rule.percent
                            break
            else:
                percent = 1
            if percent > 0:
                ref = self.refund_student(cr, uid, [charge.id], percent, context)
                refund = self.browse(cr,uid,ref)
                refund = refund.invoice_id
                if percent == 1:
                    inv = charge.invoice_id
                    if not inv.reconciled:
                        movelines = inv.move_id.line_id
                        reconcile_obj = self.pool.get('account.move.reconcile')
                        account_m_line_obj = self.pool.get('account.move.line')
                        period = inv.period_id.id
                        to_reconcile_ids = {}
                        for line in movelines:
                            if line.account_id.id == inv.account_id.id:
                                to_reconcile_ids[line.account_id.id] = [line.id]
                            if type(line.reconcile_id) != osv.orm.browse_null:
                                reconcile_obj.unlink(cr, uid, line.reconcile_id.id)
                        for tmpline in  refund.move_id.line_id:
                            if tmpline.account_id.id == inv.account_id.id:
                                to_reconcile_ids[tmpline.account_id.id].append(tmpline.id)
                        for account in to_reconcile_ids:
                            account_m_line_obj.reconcile(cr, uid, to_reconcile_ids[account],
                                            writeoff_period_id=period,
                                            writeoff_journal_id = inv.journal_id.id,
                                            writeoff_acc_id=inv.account_id.id
                                            )
                    osv.osv.unlink(self, cr, uid, ids, context=context)
                    osv.osv.unlink(self, cr, uid, ref, context=context)
        return True
    
    def refund_student(self, cr, uid, ids, percent, context=None):
        charge = self.browse(cr,uid,ids)[0]
        refund = self.create(cr,uid,{
                               'detail_id' : charge.detail_id.id,
                               'name': charge.name + " Refund",
                               'term_id': charge.term_id.id,
                               'charge':charge.charge * percent * -1,
                               'clearance_id': charge.clearance_id.id,
                               'invoice_date': charge.invoice_date
                               })
        return refund
    
    _columns = {
            'name': fields.char('Description', required=True),
            'charge': fields.float('Charge', required=True),
            'detail_id': fields.many2one('detail.code', 'Detail Code', required=True),
            'term_id': fields.many2one('aun.registrar.term', 'Term', required=True),
            'invoice_id': fields.many2one('account.invoice', 'Invoice', ondelete="cascade"),
            'clearance_id': fields.many2one('student.account', 'Student',required=True),
            'enrollment_id': fields.many2one('aun.registrar.enrollment', 'Enrollment'),
            'meal_id': fields.many2one('housing.room.students', 'Enrollment'),
            'payment_plan_id': fields.many2one('bursar.payment.plan.form', 'Payment Plan'),
            'create_date': fields.datetime('Date', readonly=True),
            'invoice_date': fields.date('Invoice Date'),
            'system':fields.boolean('System', readonly=True)
        }
term_charges()

class bursar_payment_plan(osv.osv):
    _name = "bursar.payment.plan"
    _order = "name"
    _inherit = ["mail.thread"]
    _description = "Payment Plan"
    
    def _validate_fields(self, cr, uid, ids, context=None):
        plan = self.browse(cr, uid, ids,context=context)[0]
        surcharge = False
        equal = []
        types = []
        options = []
        down = []
        total = 0.0
        for line in plan.line_ids:
            total+= line.value
            options.append(line.options)
            types.append(line.p_type)
            if line.surcharge > 0.0:
                surcharge = True
            if line.equal:
                equal.append(line)
            if line.is_down_payment:
                down.append(line)
                
        if len(down) > 1:
            raise osv.except_osv(_('Invalid'), _('Down payment lines must not be more than one.'))
        if surcharge and not plan.surcharge_detail_id:
            raise osv.except_osv(_('Invalid'), _('Service Charge Detail Code must be set if service charge is more than 0'))
        if plan.late_payment_fee < 0:
            raise osv.except_osv(_('Invalid'), _('Late Payment Fee cannot be a negative value!'))
        if plan.late_payment_fee > 0 and not plan.late_detail_id:
            raise osv.except_osv(_('Invalid'), _('Late Payment Detail Code must be set if late payment charge is more than 0'))
        if len(equal) == 1:
            raise osv.except_osv(_('Invalid'), _('Equal Installments must be more than one'))
        if len(equal) > 1:
            i = 1
            valid = True
            while i < len(equal):
                if equal[0].p_type != equal[i].p_type:
                    valid = False
                    break
                if equal[0].options != equal[i].options:
                    valid = False
                    break
                if equal[0].value != equal[i].value:
                    valid = False
                    break
                i +=1
            if valid == False:
                raise osv.except_osv(_('Invalid'), _('Type, Option and Value on equal lines must be the same!'))
        if 'least' in options and 'balance' not in types:
            raise osv.except_osv(_('Invalid'), _("At least one installment type must be 'balance' if any payment option is 'at least'"))
        if 'least' not in options and 'balance' not in types and total != 1:
            raise osv.except_osv(_('Invalid'), _('The values of all the payment lines must be equal to 1 (100%)'))
        return True
    
    _columns = {
        'name': fields.char('Name', size=64, required=True, track_visibility = "onchange"),
        'late_detail_id': fields.many2one('detail.code', 'Detail Code', track_visibility = "onchange"),
        'late_payment_fee': fields.float('Charge', track_visibility = "onchange"),
        'active': fields.boolean('Active', track_visibility = "onchange", help="If the active field is set to False, it will allow you to hide the payment plan without removing it."),
        'note': fields.text('Description', track_visibility = "onchange",required=True), 
        'surcharge_detail_id': fields.many2one('detail.code', 'Detail Code', track_visibility = "onchange"),
        'line_ids': fields.one2many('bursar.payment.plan.line', 'payment_id', 'Installments', track_visibility = "onchange"),
    }

    _constraints=[
        (_validate_fields, 'Invalid Configuration',['Form']),
    ]
    _defaults = {
        'active': True
    }
bursar_payment_plan()

class bursar_payment_plan_line(osv.osv):
    _name = "bursar.payment.plan.line"
    _description = "Payment Plan"
    _inherit = ["mail.thread"]
    _order = 'is_down_payment DESC'
    
    def on_change_type(self, cr, uid, ids, p_type, context=None):
        if p_type == 'balance':
            return {'value': {'options': [],'value':0}}
        return True
    
    def on_change_down_payment(self, cr, uid, ids, is_down_payment, context=None):
        if is_down_payment == True:
            return {'value': {'date_from': 'clearance'}}
        return True
    
    def _validate_fields(self, cr, uid, ids, context=None):
        line = self.browse(cr, uid, ids,context=context)[0]
        if line.p_type == 'percent':
            if line.value > 1 or line.value < 0:
                raise osv.except_osv(_('Invalid'), _('Installment Percentage must be between 0 and 1, e.g 60% will be 0.60'))
        if line.surcharge > 1 or line.surcharge < 0:
            raise osv.except_osv(_('Invalid'), _('Service Charge must be between 0 and 1, e.g 60% will be 0.60'))
        return True
    
    _columns = {
        'payment_id': fields.many2one('bursar.payment.plan', 'Payment Plan', required=True, ondelete='cascade'),
        'is_down_payment': fields.boolean('Is Down Payment'),
        'days': fields.integer('Days', track_visibility="onchange"),
        'date_from': fields.selection(PAYMENT_PLAN_DATES, 'Date', track_visibility="onchange"),
        'p_type': fields.selection(PAYMENT_PLAN_LINE_TYPES, 'Type', required=True, track_visibility="onchange"),
        'options': fields.selection(PAYMENT_PLAN_OPTIONS, 'Option', track_visibility="onchange"),
        'value': fields.float('Value', track_visibility = "onchange"),
        'after': fields.char('Payment', readonly=True),
        'surcharge': fields.float('Service Charge', track_visibility = "onchange"),
        'equal': fields.boolean('Equal?', track_visibility = "onchange")
    }
    _defaults = {
        'after': ' days after '
    }
    _constraints=[
        (_validate_fields, 'Invalid Configuration',['Form']),
    ]
bursar_payment_plan_line()

class bursar_payment_plan_form(osv.osv):
    _name = "bursar.payment.plan.form"
    _inherit = ["mail.thread", 'ir.needaction_mixin']
    _description = "Payment Plan Application"
    
    def _needaction_domain_get (self, cr, uid, context=None):
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_bursar"):
            return [('state','=','submitted')]
        return False
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.student_id.name + '-' + record.payment_id.name + '-' + record.term_id.name_get()[0][1]
            res.append((record['id'], name))
        return res
    
    def create(self, cr, uid, vals, context=None):
        dup = self.search(cr,uid,[('student_id','=',vals['student_id']),('term_id','=',vals['term_id']),('state','not in',['cancelled','rejected'])])
        if (dup):
            raise osv.except_osv(_('Invalid'), _('You cannot have multiple payment plans in one term'))
        vals['state'] = 'submitted'
        res = super(bursar_payment_plan_form, self).create(cr, uid, vals, context)
        group = self.pool.get('ir.model.data').get_object(cr, uid, 'academics', 'group_bursar')
        group = cr.execute("select uid from res_groups_users_rel WHERE gid=(%s)" %group.id)
        s = cr.fetchall()
        group = []
        for a in s:
            group.append(a[0])
        student = self.pool.get('res.partner').browse(cr,uid,[vals['student_id']])[0]
        if student.user_ids:
            group.append(student.user_ids[0].id)
        else:
            raise osv.except_osv(_("This student does not have a user account, Contact Administrator"), student.name)
        self.message_subscribe_users(cr, SUPERUSER_ID, [res] , group, context=context)
        return res
    
    def on_change_student_id(self, cr, uid, ids, student_id, context=None):
        if student_id:
            stud_obj = self.pool.get('res.partner')
            student = stud_obj.browse(cr,uid,student_id)
        return {'value': {'term_id': [],'fname': student.fname, 'lname':student.lname}}
    
    def on_change_term_id(self, cr, uid, ids, term_id, student_id, context=None):
        if term_id:
            clearance_obj = self.pool.get('student.account')
            charge_obj = self.pool.get('term.charges')
            term_obj = self.pool.get('aun.registrar.term')
            student = self.pool.get('res.partner').browse(cr,uid,student_id,context)
            fee_obj = self.pool.get('fee.structure')
            clearance = clearance_obj.search(cr,uid, [('student_id','=',student_id)])[0]
            fee = fee_obj.browse(cr, uid, fee_obj.search(cr, uid, [('term_id','=',term_id),('level_id','=',student.level_id.id)]),context=None)
            if (fee):
                fee = fee[0]
            else:
                warning = {
                            'title': ('Invalid'),
                            'message': ('No fee structure for this term, please contact the bursar!')
                        }
                return {'value': {'term_id': []},'warning': warning}
            if clearance:
                total = 0.0
                charges = charge_obj.browse(cr, uid, charge_obj.search(cr, uid, [('term_id','=',term_id),('clearance_id','=',clearance)]),context=None)
                for charge in charges:
                    total += charge.charge
                term = term_obj.browse(cr,uid,term_id)
                l_terms = term_obj.search(cr,uid, [('code','>',term.code)])
                other = 0.0
                for l_term in l_terms:
                    o_charges = charge_obj.browse(cr, uid, charge_obj.search(cr, uid, [('term_id','=',l_term),('clearance_id','=',clearance)]),context=None)
                    for o_charge in o_charges:
                        other += o_charge.charge
                balance = student.credit - other
                if balance > total:
                    warning = {
                            'title': ('Invalid'),
                            'message': ('You are not qualified for a payment plan because you owe N' + str(balance - total) + ' from previous terms. ')
                        }
                    return {'value': {'term_id': []},'warning': warning}
                total = total + fee.min_balance
            if total > 0:
                return {'value': {'payment_id': [],'total_charge': total,'amount':total}}
            else:
                warning = {
                            'title': ('Invalid'),
                            'message': ('You do not have any charges for this term!')
                        }
                return {'value': {'term_id': []},'warning': warning}
        else:
            return True
        
    def on_change_amount(self, cr, uid, ids, amount, total_charge, context=None):
        if amount and total_charge and amount < total_charge:
            warning = {
                            'title': ('Invalid'),
                            'message': ('You have charges of N ' + str(total_charge) +' for this term, The amount requested must be greater than or equal to this amount')
                        }
            return {'value': {'amount': total_charge},'warning': warning}
        return True
        
    def on_change_payment_id(self, cr, uid, ids, payment_id, total_charge, term_id, student_id, context=None):
        lines = []
        note = ''
        if payment_id:
            plan_obj = self.pool.get('bursar.payment.plan')
            term_obj = self.pool.get('aun.registrar.term')
            plan = plan_obj.browse(cr, uid, payment_id)
            note = plan.note
            total = total_charge
            i = 1
            bal = 0.0
            balance = []
            term = term_obj.browse(cr,uid,term_id)
            for line in plan.line_ids:
                if line.p_type == 'balance':
                    balance.append(line)
                else:
                    if line.p_type == 'percent':
                        amount = total * line.value
                        bal += amount
                    if line.date_from == 'start':
                        s_date = term.start_date
                    elif line.date_from == 'registration_start':
                        s_date = term.reg_start
                    elif line.date_from == 'registration_end':
                        s_date = term.reg_end  
                    elif line.date_from == 'clearance':
                        s_date = datetime.datetime.now().strftime('%Y-%m-%d')   
                    due_date =  datetime.datetime.strptime(s_date[:10], tools.DEFAULT_SERVER_DATE_FORMAT)+ datetime.timedelta(days=(line.days))
                    surcharge = line.surcharge * amount
                    if line.is_down_payment == False:
                        name = 'Installment ' + str(i)
                    else: 
                        name = 'Down Payment'
                    lines.append({'amount': amount,
                                  'min_amount': amount,
                                  'surcharge': surcharge,
                                  'total': amount + surcharge,
                                  'name': name,
                                  'max_date': str(due_date)[:10],
                                  'due_date': str(due_date)[:10],
                                  'config_line_id': line.id
                                  })
                    amount += amount
                    if line.is_down_payment == False:
                        i +=1
            if balance:
                bal = (total - bal) / len(balance)
                for line in balance:
                    if line.date_from == 'start':
                        s_date = term.start_date
                    elif line.date_from == 'registration_start':
                        s_date = term.reg_start
                    elif line.date_from == 'registration_end':
                        s_date = term.reg_end  
                    elif line.date_from == 'clearance':
                        s_date = datetime.datetime.now().strftime('%Y-%m-%d')
                        if s_date < term.start_date:
                            s_date = term.start_date
                    due_date =  datetime.datetime.strptime(s_date[:10], tools.DEFAULT_SERVER_DATE_FORMAT)+ datetime.timedelta(days=(line.days))
                    surcharge = line.surcharge * bal
                    if line.is_down_payment == False:
                        name = 'Installment ' + str(i)
                    else: 
                        name = 'Down Payment'
                    lines.append({'amount': bal,
                                  'surcharge': surcharge,
                                  'total': bal + surcharge,
                                  'name': 'Installment ' + str(i),
                                  'max_date': str(due_date)[:10],
                                  'due_date': str(due_date)[:10],
                                  'config_line_id': line.id
                                  })
                    if line.is_down_payment == False:
                        i +=1
#         else:
#             raise osv.except_osv(_('No Charges'), _('You have no charges for this semester, please see bursar!'))
        
        return {'value': {'note': note, 'installment_ids': lines}}
    
    def _check_total(self, cr, uid, ids, context=None):
        plan = self.browse(cr, uid, ids,context=context)[0]
        if plan.state not in ['cancelled','paid']:
            total = 0.0
            equals = []
            e_names = []
            for line in plan.installment_ids:
                if line.config_line_id.equal == True:
                    equals.append(line.amount)
                    e_names.append(line.name)
                if plan.state == 'approved':
                    total += line.amount
                else :
                    total += line.amount
            if len(set(equals)) > 1:
                e_names = ' and '.join(e_names)
                raise osv.except_osv(_('Check Installment Amounts'), _(e_names + ' must be equal!'))
    
            if str(total) != str(plan.amount):
                print str(total)
                print str(plan.amount)
                raise osv.except_osv(_('Check Installment Amounts'), _('Your payment installments are not equal to the total charge!'))
        return True
    
    def on_change_down_payment(self, cr, uid, ids, down_payment, payment_id, context=None):
        charge = 0
        if down_payment and payment_id:
            plan_obj = self.pool.get('bursar.payment.plan')
            plan = plan_obj.browse(cr,uid,payment_id)
            charge = plan.down_surcharge * down_payment
        return {'value': {'down_surcharge': charge}}
    
    def _get_term_charge(self, cr, uid, ids, name, args, context=None):
        res = {}
        uid = SUPERUSER_ID
        for plan in self.browse(cr, uid, ids, context=context):
            clearance_obj = self.pool.get('student.account')
            charge_obj = self.pool.get('term.charges')
            fee_obj = self.pool.get('fee.structure')
            clearance = clearance_obj.search(cr,SUPERUSER_ID, [('student_id','=',plan.student_id.id)])[0]
            fee = fee_obj.browse(cr, uid, fee_obj.search(cr, uid, [('term_id','=',plan.term_id.id),('level_id','=',plan.student_id.level_id.id)]),context=None)[0]
            if clearance:
                total = 0.0
                charges = charge_obj.browse(cr, uid, charge_obj.search(cr, uid, [('term_id','=',plan.term_id.id),('clearance_id','=',clearance)]),context=None)
                for charge in charges:
                    total += charge.charge
                total = total + fee.min_balance
                res[plan.id] = total
        return res
       
    def _get_term_balance(self, cr, uid, ids, name, args, context=None):
        res = {}
        uid = SUPERUSER_ID
        for plan in self.browse(cr, uid, ids, context=context):
            clearance_obj = self.pool.get('student.account')
            charge_obj = self.pool.get('term.charges')
            term_obj = self.pool.get('aun.registrar.term')
            fee_obj = self.pool.get('fee.structure')
            clearance = clearance_obj.search(cr,uid, [('student_id','=',plan.student_id.id)])[0]
            fee = fee_obj.browse(cr, uid, fee_obj.search(cr, uid, [('term_id','=',plan.term_id.id),('level_id','=',plan.student_id.level_id.id)]),context=None)[0]
            if clearance:
                l_terms = term_obj.search(cr,uid, [('code','>',plan.term_id.code)])
                other = 0.0
                for l_term in l_terms:
                    o_charges = charge_obj.browse(cr, uid, charge_obj.search(cr, uid, [('term_id','=',l_term),('clearance_id','=',clearance)]),context=None)
                    for o_charge in o_charges:
                        other += o_charge.charge
                balance = plan.student_id.credit - other
                total = balance
                res[plan.id] = total
                if total <= 0 and plan.state != 'paid':
                    self.write(cr,SUPERUSER_ID, plan.id, {'state': 'paid', 'active': False})
        return res
    
    def _get_amount_due(self, cr, uid, ids, name, args, context=None):
        res = {}
        for plan in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for line in plan.installment_ids:
                total += line.total
            res[plan.id] = total
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        self.case_cancel(cr,uid,ids)
        return True
    
    def case_cancel(self, cr, uid, ids, context=None):
        plan = self.browse(cr, uid, ids, context=context)[0]
        clearance_obj = self.pool.get('term.clearance')
        clearance = clearance_obj.browse(cr, SUPERUSER_ID, clearance_obj.search(cr, SUPERUSER_ID, [('term_id','=',plan.term_id.id),('student_id','=',plan.student_id.id)]))
        if clearance:
            if clearance[0].state == 'cleared':
                raise osv.except_osv(_('Invalid'), _('You cannot cancel a payment plan after student has done clearance for the term'))
            else:
                clearance_obj.write(cr,uid,clearance[0].id,{'payment_plan':[]})
        if plan.surcharge_ids:
            charge_obj = self.pool.get('term.charges')
            for surcharge in plan.surcharge_ids:
                charge_obj.unlink(cr,SUPERUSER_ID,[surcharge.id])
        self.write(cr, uid, ids, {'state': 'cancelled', 'active': False}, context=context)
        return True
    
    def case_reject(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'rejected', 'active': False}, context=context)
        return True
    
    def case_approve(self, cr, uid, ids, context=None):
        #Create invoice for surcharge
        plan = self.browse(cr, uid, ids, context=context)[0]
        line_obj = self.pool.get('bursar.payment.plan.form.line')
        for line in plan.installment_ids:
            line_obj.write(cr,uid,line.id,{'f_surcharge': line.surcharge})
        charge_obj = self.pool.get('term.charges')
        account_obj = self.pool.get('student.account')
        account = (account_obj.search(cr, uid, [('student_id','=',plan.student_id.id)])
                                             or 
                     account_obj.create(cr, uid, {'student_id': plan.student_id.id}))
        surcharges = []
        for line in plan.installment_ids:
            if line.surcharge > 0.0:
                surcharges.append({'amount': line.surcharge, 'date': line.due_date})
        res = {}
        for surcharge in surcharges:
            charge_obj.create(cr, SUPERUSER_ID,{
                               'detail_id' : plan.payment_id.surcharge_detail_id.id,
                               'name': plan.payment_id.surcharge_detail_id.desc,
                               'term_id': plan.term_id.id,
                               'charge':surcharge['amount'],
                               'invoice_date': surcharge['date'],
                               'payment_plan_id': ids[0],
                               'clearance_id': account[0] if type(account) == list else account,
                               })
        res['state'] = 'approved'
        self.write(cr, uid, ids, res)
        # Add payment plan to clearance
        clearance_obj = self.pool.get('term.clearance')
        clearance = clearance_obj.search(cr,uid, [('term_id','=',plan.term_id.id),('student_id','=',plan.student_id.id)])
        if clearance:
            clearance_obj.write(cr,uid,clearance,{'payment_plan': plan.id})
        else:
            raise osv.except_osv(_('Invalid'), _('This Student Has No Courses Registered For This Term!'))
        return True

    _columns = {
        'student_id': fields.many2one('res.partner','Student', domain="[('student','=',True)]", required=True),
        'fname': fields.related('student_id', 'fname', type='char', relation="res.partner", string="First Name", store=False, readonly=True),
        'lname': fields.related('student_id', 'lname', type='char', relation="res.partner", string="Last Name", store=False, readonly=True),
        'term_id': fields.many2one('aun.registrar.term','Term', required=True),
        'note': fields.related('payment_id', 'note', type='text', string="Description", store=False, readonly=True),
        'payment_id': fields.many2one('bursar.payment.plan', 'Payment Plan', required=True, track_visibility="onchange"),
        'amount': fields.float('Total Amount', digits=(3,2), required=True, track_visibility="onchange"),
        'total_charge': fields.function(_get_term_charge, type = 'float', digits_compute=dp.get_precision('Account'), string='Total Charge', track_visibility='onchange'),
        'balance': fields.function(_get_term_balance, type = 'float', digits_compute=dp.get_precision('Account'), string='Balance', track_visibility='onchange'),
        'installment_ids': fields.one2many('bursar.payment.plan.form.line', 'payment_id', 'Payments'),
        'state': fields.selection(PAYMENT_PLAN_STATES, 'State', required=True, track_visibility="onchange"),
        'amount_due': fields.function(_get_amount_due, type = 'float', digits_compute=dp.get_precision('Account'), string='Amount Due', track_visibility='onchange'),
        'surcharge_ids': fields.one2many('term.charges', 'payment_plan_id', 'Surcharges'),
        'override': fields.boolean('Override'),
        'active': fields.boolean('Active')
    }
    
    _constraints=[
        (_check_total, 'Your payment installments are not equal to the total charge!',['Total Charge']),
    ]
    _defaults={
            'state': 'draft',
            'active': True
        }
bursar_payment_plan_form()

class bursar_payment_plan_form_line(osv.osv):
    _name = "bursar.payment.plan.form.line"
    _inherit = ["mail.thread"]
    _description = "Payment Plan Application"
    
    def _get_surcharge(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                'total': 0.0,
                'surcharge': 0.0,
            }
            amount = 0.0
            if line.payment_id.state != 'approved':
                charge = line.config_line_id.surcharge * line.amount
            else:
                charge = line.f_surcharge
            res[line.id]['surcharge'] = charge
            res[line.id]['total'] = charge + line.amount
            total_charge = line.payment_id.total_charge
            if line.config_line_id.p_type == 'percent':
                amount = total_charge * line.config_line_id.value
#             elif line.config_line_id.p_type == 'fixed':
#                 amount = line.config_line_id.value
            res[line.id]['min_amount'] = amount
        return res
    
    def on_change_amount(self, cr, uid, ids, amount, config_line_id, context=None):
        line_obj = self.pool.get('bursar.payment.plan.line')
        line = line_obj.browse(cr,uid,config_line_id)
        charge = line.surcharge * amount
        total = charge + amount
        return {'value': {'surcharge': charge,'total':total}}
    
    def _check_date(self, cr, uid, ids, context=None):
        line = self.browse(cr, uid, ids,context=context)[0]
        if not line.payment_id.override:
            if line.due_date > line.max_date:
                max_date = time.strftime("%a %b %d %Y",time.strptime(line.max_date,"%Y-%m-%d"))
                raise osv.except_osv(_('Invalid Due Date on '+ line.name), _('Please select a date less than or equal to ' + max_date))
        return True
    
    def _check_amount(self, cr, uid, ids, context=None):
        line = self.browse(cr, uid, ids,context=context)[0]
        if not line.payment_id.override:
            if line.config_line_id.p_type == 'percent':
                if line.config_line_id.options == 'equal':
                    if line.amount != line.min_amount:
                        raise osv.except_osv(_('Invalid Amount on '+ line.name), _('Your Payment must be equal to N' + str(line.min_amount)))
                elif line.config_line_id.options == 'least':
                    if line.amount < line.min_amount:
                        raise osv.except_osv(_('Invalid Amount on '+ line.name), _('Your Payment must be at least N' + str(line.min_amount)))
#         elif line.config_line_id.p_type == 'fixed':
#             if line.config_line_id.options == 'equal':
#                 if line.amount != line.min_amount:
#                     raise osv.except_osv(_('Invalid Amount on '+ line.name), _('Your Payment must be equal to N' + str(line.min_amount)))
#             elif line.config_line_id.options == 'least':
#                 if line.amount < line.min_amount:
#                     raise osv.except_osv(_('Invalid Amount on '+ line.name), _('Your Payment must be at least N' + str(line.min_amount)))

        return True
    
    _columns = {
        'name': fields.char('Name', required = True, readonly=True),
        'payment_id': fields.many2one('bursar.payment.plan.form', 'Payment Plan', required=True, ondelete='cascade'),
        'amount': fields.float('Installment Amount', track_visibility = "onchange", required=True),
        'min_amount': fields.function(_get_surcharge, type = 'float', digits_compute=dp.get_precision('Account'), string='Min Amount', multi='all'),
        'surcharge': fields.function(_get_surcharge, type = 'float', digits_compute=dp.get_precision('Account'), string='Service Charge', track_visibility='onchange', multi='all'),
        'f_surcharge': fields.float('Service Charge', digits_compute=dp.get_precision('Account'), readonly=True),
        'total': fields.function(_get_surcharge, type = 'float', digits_compute=dp.get_precision('Account'), string='Total Amount Due', track_visibility='onchange', multi='all'),
        'due_date': fields.date('Due Date', track_visibility = "onchange", required=True),
        'max_date': fields.date('Max Date', required=True),
        'config_line_id': fields.many2one('bursar.payment.plan.line', 'Configuration Line', required=True),
    }
    _constraints=[
        (_check_date, 'Check Due Date',['Due Date']),
        (_check_amount, 'Check Amount',['Amount']),
    ]
bursar_payment_plan_form()