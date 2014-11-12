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
from datetime import date, datetime
import datetime
from openerp import SUPERUSER_ID
import collections
import logging
import time
import threading
import psycopg2
from openerp import tools
from openerp import netsvc
from openerp.addons.academics.academics_registrar import gpa_info
_logger = logging.getLogger(__name__)



class transcript_request(osv.osv):
    _name = 'transcript.request'
    _description = 'Transcript Request'
    _inherit=['mail.thread','ir.needaction_mixin']
    _order = 'create_date DESC'
    
    def _needaction_domain_get(self, cr, uid, context=None):
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_ass_registrar"):
            return [('state','=','in_progress')]
        return False
    
    def on_change_student(self, cr, uid, ids, student_id, context=None):
        term_ids = level_ids = level_id = fname = mname = lname = issue_to = False
        street = street2 = street3 = city = state_id = country_id = phone = zip = False
        if student_id:
            student = self.pool.get('res.partner').browse(cr, SUPERUSER_ID, student_id, context)
            if student.fname:
                fname = student.fname
            if student.mname:
                mname = student.mname
            if student.lname:
                lname = student.lname
            if fname and mname and lname:
                issue_to = fname+' '+mname+' '+lname
            elif fname and lname:
                issue_to = fname +' '+ lname
            else:
                issue_to = ''
            street = student.street
            street2 = student.street2
            city = student.city
            state_id = student.state_id.id
            country_id = student.country_id.id
            zip = student.zip
            phone = student.phone
            level_gpas = student.level_gpa_ids
            if level_gpas:
                level_ids = []
                for level_gpa in level_gpas:
                    if level_gpa.level_id:
                        level_ids.append(level_gpa.level_id.id)
                        level_id = level_gpa.level_id.id
            if level_ids:
                info_ids = self.pool.get('gpa.info').search(cr, uid, [('student_id','=', student_id),('level_id', 'in', level_ids)])
                if info_ids:
                    term_ids = []
                    gpa_infos = self.pool.get('gpa.info').browse(cr, uid, info_ids)
                    for gpa_info in gpa_infos:
                        if gpa_info.term_id:
                            term_ids.append(gpa_info.term_id.id)
                    if term_ids:
                        term_ids = list(set(term_ids))
        return {'value': {'fname':fname, 'mname':mname, 'lname':lname, 'level_id':level_id,'level_ids':[(6, 0, level_ids)], 'lg_term_ids':[(6, 0,term_ids)], 'lg_level_ids':[(6, 0, level_ids)], 'issue_to':issue_to,
                          'street': street,'street2': street2,'street3': street3,'city': city,'state_id': state_id,'country_id': country_id,'zip': zip,'phone': phone}}
    
    def _get_order_no(self, cr, uid, context=None):        
        return str(int(time.mktime(datetime.datetime.now().timetuple())))

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.student_id.name+'/'+record.order_no
            res.append((record.id, name))
        return res

    def _get_student_id(self, cr, uid, context=None):
        res = False
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            res = user.partner_id.id
        return res
    
    def on_change_copies(self, cr, uid, ids, copies, context=None):
        res = copies
        warning = {}
        if (copies <= 0): 
            warning = {'title': _('Invalid Copies'),'message': _('Number of copies must be greater than zero.')}
            res = 1
        return {'value': {'copies': res}, 'warning': warning}
    
    def on_change_state(self, cr, uid, ids, state_id, context=None):
        if state_id:
            country_id = self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id
            return {'value':{'country_id':country_id}}
        return {}
    
    def submit_request(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'in_progress'}, context=context)  
        return True
    
    def validate(self, cr, uid, ids, context=None):
        transcript = self.browse(cr, uid, ids)[0] 
        credit = transcript.student_id.credit
        charge = transcript.transcript_charge * transcript.copies
        if credit > 0 and charge > 0:
            raise osv.except_osv(('Payment Issue!'), ('This student has an outstanding balance.')) 
        else:
            self.write(cr, uid, ids, {'state':'to_print'}, context=context)  
        return True
    
    def generate_invoice(self, cr, uid, ids, context=None):
        transcript = self.browse(cr, uid, ids)[0]
        setting_ids = self.pool.get('registrar.settings').search(cr, SUPERUSER_ID, [])
        if setting_ids:
            setting = self.pool.get('registrar.settings').browse(cr, SUPERUSER_ID, setting_ids)[0]
            if setting.transcript_detail_code:
                if transcript.billing_term:
                    detail_id = setting.transcript_detail_code
                    account_obj = self.pool.get('student.account')
                    charge_obj = self.pool.get('term.charges')
                    account = (account_obj.search(cr, SUPERUSER_ID, [('student_id','=',transcript.student_id.id)]) or account_obj.create(cr, uid, {'student_id': transcript.student_id.id}))
                    invoice_id = charge_obj.create(cr, SUPERUSER_ID,{
                                   'detail_id' : detail_id.id,
                                   'name': detail_id.desc,
                                   'term_id': transcript.billing_term.id,
                                   'charge': transcript.transcript_charge * transcript.copies,
                                   'clearance_id': account[0] if type(account) == list else account,
                                   'system':True
                                   })
                    if invoice_id:
                        self.write(cr, uid, ids,{'invoice_id': invoice_id})
                    else:
                        raise osv.except_osv(('Invoice Error!'), ('Could not create invoice.')) 
                else:
                    raise osv.except_osv(('Term Error!'), ('There is no billing term for this transcript.')) 
            else:
                raise osv.except_osv(('Contact the Administrator!'), ('You need to specify a detail code for transcript in registrar settings.')) 
        else:
            raise osv.except_osv(('Contact the Administrator!'), ('Settings has not been created!'))
        return True
    
    def print_transcript(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        if context is None:
            context = {}
        datas = {'ids': [data['student_id'][0]]}
        context['active_id'] = data['student_id'][0]
        context['active_ids'] = [data['student_id'][0]]
        datas['model'] = 'res.partner'
        datas['copies'] = range(data['copies'])
        info = self.read(cr, uid, ids)[0]
        datas['form'] = info
        self.write(cr, uid, ids, {'print_date':  datetime.datetime.now(), 'state':'done'})
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'official_transcript',
            'datas': datas,
            'context': context,
        }
            
    def set_to_draft(self, cr, uid, ids, context=None):
        transcript = self.browse(cr, SUPERUSER_ID, ids)[0]
        if transcript.invoice_id:
            account_obj = self.pool.get('student.account')
            charge_obj = self.pool.get('term.charges')
            account = (account_obj.search(cr, SUPERUSER_ID, [('student_id','=',transcript.student_id.id)]) or account_obj.create(cr, SUPERUSER_ID, {'student_id': transcript.student_id.id}))
            charge_obj.unlink(cr,SUPERUSER_ID, [transcript.invoice_id.id])
#             
#             
#             invoice_id = charge_obj.create(cr, SUPERUSER_ID,{
#                            'detail_id' : transcript.invoice_id.detail_id.id,
#                            'name': transcript.invoice_id.detail_id.desc,
#                            'term_id': transcript.billing_term.id,
#                            'charge': -transcript.transcript_charge * transcript.copies,
#                            'clearance_id': account[0] if type(account) == list else account,
#                            'system':True
#                            })
#             if invoice_id:
#                 self.write(cr, uid, ids,{'invoice_id': False})
#             else:
#                 raise osv.except_osv(('Invoice Error!'), ('Could not refund invoice.')) 
        self.write(cr, uid, ids, {'state':'draft'}, context=context)  
        return True
    
    def _get_currency(self, cr, uid, context=None):
        res = False
        ids = self.pool.get('res.currency').search(cr, uid, [('name','=','NGN')])
        if ids:
            return ids[0]
        return res
            
    def on_change_level(self, cr, uid, ids, student_id, level_id, context=None):
        first_term = last_term = standing_id = level_gpa_id = transfer = False 
        attempted_hours = passed_hours = earned_hours = quality_points = gpa_hours = cgpa = 0
        t_attempted_hours = t_passed_hours = t_earned_hours = t_quality_points = t_gpa_hours = t_cgpa = 0
        o_attempted_hours = o_passed_hours =  o_earned_hours = o_quality_points = o_gpa_hours = o_cgpa = 0
        if level_id and student_id:
            gpa_info_ids = self.pool.get('gpa.info').search(cr, uid, [('student_id','=',student_id),('level_id','=',level_id)])
            if gpa_info_ids:
                gpa_infos = self.pool.get('gpa.info').browse(cr, uid, gpa_info_ids)
                if gpa_infos[0]:
                    last_term = gpa_infos[0].term_id.id
                    standing_id = gpa_infos[0].standing_id.id
                if gpa_infos[-1]:  
                    first_term = gpa_infos[-1].term_id.id
                level_gpa_ids = self.pool.get('level.gpa').search(cr, uid, [('student_id', '=',student_id),('level_id','=',level_id)])
                if level_gpa_ids:
                    level_gpa = self.pool.get('level.gpa').browse(cr, uid, level_gpa_ids)[0]
                    level_gpa_id = level_gpa.id
                    transfer = level_gpa.transfer
                    attempted_hours = level_gpa.attempted_hours
                    passed_hours = level_gpa.passed_hours
                    earned_hours = level_gpa.earned_hours    
                    quality_points = level_gpa.quality_points  
                    gpa_hours = level_gpa.gpa_hours 
                    cgpa = level_gpa.cgpa  
                    t_attempted_hours = level_gpa.t_attempted_hours
                    t_passed_hours = level_gpa.t_passed_hours
                    t_earned_hours = level_gpa.t_earned_hours    
                    t_quality_points = level_gpa.t_quality_points  
                    t_gpa_hours = level_gpa.t_gpa_hours 
                    t_cgpa = level_gpa.t_cgpa 
                    o_attempted_hours = level_gpa.o_attempted_hours
                    o_passed_hours = level_gpa.o_passed_hours
                    o_earned_hours = level_gpa.o_earned_hours    
                    o_quality_points = level_gpa.o_quality_points  
                    o_gpa_hours = level_gpa.o_gpa_hours 
                    o_cgpa = level_gpa.o_cgpa 
                                           
        return {'value': {'first_term': first_term, 'last_term': last_term, 'standing_id': standing_id,'level_gpa_id': level_gpa_id, 'transfer':transfer,
                          'attempted_hours':attempted_hours,'passed_hours':passed_hours,'earned_hours':earned_hours,'quality_points':quality_points,
                          'gpa_hours':gpa_hours,'cgpa':cgpa,'t_attempted_hours':t_attempted_hours,'t_passed_hours':t_passed_hours,'t_earned_hours':t_earned_hours,
                          't_quality_points':t_quality_points,'t_gpa_hours':t_gpa_hours,'t_cgpa':t_cgpa,'o_attempted_hours':o_attempted_hours,'o_passed_hours':o_passed_hours,
                          'o_earned_hours':o_earned_hours,'o_quality_points':o_quality_points,'o_gpa_hours':o_gpa_hours,'o_cgpa':o_cgpa}}
    
    def _get_billing_term(self, cr, uid, context=None):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        term_ids = self.pool.get('aun.registrar.term').search(cr, uid, [('start_date','<=',now),('end_date','>=',now)]),
        if term_ids:
            return term_ids[0]
        return False
    
    def get_transcript_total(self, cr, uid, ids, name, arg, context=None):
        res={}
        for transcript in self.browse(cr, uid, ids, context=context):
            res[transcript.id] = transcript.transcript_charge * transcript.copies
        return res
    
    def get_current_student_status(self, cr, uid, ids, name, arg, context=None):
        res={}
        for transcript in self.browse(cr, uid, ids, context=context):
            res[transcript.id] = {}
            level_gpa = False
            gpa_info_ids = self.pool.get('gpa.info').search(cr, uid, [('student_id','=',transcript.student_id.id),('level_id','=',transcript.level_id.id)])
            if gpa_info_ids:
                gpa_infos = self.pool.get('gpa.info').browse(cr, uid, gpa_info_ids)
                if gpa_infos[0]:
                    res[transcript.id]['last_term'] = gpa_infos[0].term_id.id
                    res[transcript.id]['standing_id'] = gpa_infos[0].standing_id.id
                if gpa_infos[-1]:  
                    res[transcript.id]['first_term'] = gpa_infos[-1].term_id.id
                level_gpa_ids = self.pool.get('level.gpa').search(cr, uid, [('student_id', '=',transcript.student_id.id),('level_id','=',transcript.level_id.id)])
                if level_gpa_ids:
                    level_gpa = self.pool.get('level.gpa').browse(cr, uid, level_gpa_ids)[0]
                    level_gpa = level_gpa.id
            res[transcript.id]['level_gpa_id'] = level_gpa
        return res
    
    _columns = {
            'order_no': fields.char('Reference No.', size=16, required=True, readonly=True,track_visibility="onchange"),
            'track_no': fields.char('Tracking Number', size=16, track_visibility='onchange'),
            'student_track_no':fields.related('track_no', string='Tracking Number', type='char', readonly=True),
            'student_id': fields.many2one('res.partner', 'Student ID', required=True, track_visibility="onchange"),
            'issue_to': fields.char('Issue To', size=64, required=True, track_visibility="onchange"),
            'fname': fields.related('student_id', 'fname', type='char', readonly=True, string="First Name", store=False),
            'mname': fields.related('student_id', 'mname', type='char', readonly=True,string="Middle Name", store=False),
            'lname': fields.related('student_id', 'lname', type='char', readonly=True,string="Last Name", store=False),
            'street': fields.char('Street', size=32, required=True, track_visibility="onchange"),
            'street2': fields.char('Street2', size=32, track_visibility="onchange"),
            'street3': fields.char('Street3', size=32, track_visibility="onchange"),
            'city': fields.char('City', required=True, size=64,track_visibility="onchange"),
            'state_id': fields.many2one('res.country.state', 'State', required=True, track_visibility="onchange"),
            'country_id': fields.many2one('res.country', 'Country', required=True, track_visibility="onchange"),
            'zip' : fields.char('ZIP', track_visibility="onchange"),
            'phone': fields.char('Phone', track_visibility="onchange"),
            'lg_level_ids': fields.many2many('aun.registrar.level', 'rel_transcript_request_lg', 'student_id', 'level_id', 'Level(s)'),
            'level_ids': fields.many2many('aun.registrar.level', 'rel_transcript_request', 'student_id', 'level_id', 'Level(s)', domain="[('id','in',lg_level_ids[0][2])]", required=True, track_visibility="onchange"),
            'lg_term_ids': fields.many2many('aun.registrar.term', 'rel_transcript_term_lg', 'student_id', 'term_id', 'Term(s)', track_visibility='onchange'),
            'term_ids': fields.many2many('aun.registrar.term', 'rel_transcript_term', 'student_id', 'term_id', 'Term(s)', domain="[('id','in',lg_term_ids[0][2])]", track_visibility='onchange'),
            'create_date': fields.datetime('Request Date', readonly=True, track_visibility="onchange"),
            'copies': fields.integer('Number of Copies', required=True, track_visibility="onchange"),
            'print_date': fields.datetime('Print Date', readonly=True, track_visibility="onchange"),
            'print_transcript': fields.selection([('asap','As soon as possible'),('grade_hold','Hold for Grades'),('degree_hold','Hold for Degree')],'Print Transcript', required=True, track_visibility="onchange"),
            'invoice_id': fields.many2one('term.charges', 'Invoice', readonly=True, track_visibility="onchange"),
            'billing_term': fields.many2one('aun.registrar.term', 'Billing Term', required=False, track_visibility="onchange"),
            'transcript_charge': fields.float('Transcript Charge'),
            'shipping_charge': fields.float('Shipping Charge'),
            'total': fields.function(get_transcript_total, type="float", string="Total Amount"),
            'currency_id': fields.many2one('res.currency', 'Currency', required=True, track_visibility='onchange'),
            'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility='onchange', domain="[('id','in',lg_level_ids[0][2])]"),
            'first_term':fields.function(get_current_student_status, multi = "student_status", type="many2one", relation="aun.registrar.term", string="First Term"),
            'last_term':fields.function(get_current_student_status, multi = "student_status", type="many2one", relation="aun.registrar.term", string="Last Term"),
            'standing_id':fields.function(get_current_student_status, multi = "student_status", type="many2one", relation="aun.registrar.standing", string="Academic Standing"),
            'level_gpa_id':fields.function(get_current_student_status, multi = "student_status", type="many2one", relation="level.gpa", string="Level GPA"),
            'attempted_hours': fields.related('level_gpa_id', 'attempted_hours', type='float', string='Attempted Hours', store=False, readonly=True),
            'passed_hours': fields.related('level_gpa_id', 'passed_hours', type='float', string='Passed Hours', store=False, readonly=True),
            'earned_hours': fields.related('level_gpa_id', 'earned_hours', type='float', string='Earned Hours', store=False, readonly=True),
            'quality_points': fields.related('level_gpa_id', 'quality_points', type='float', string='Quality Points', store=False, readonly=True),
            'gpa_hours': fields.related('level_gpa_id', 'gpa_hours', type='float', string='GPA Hours', store=False, readonly=True),
            'cgpa': fields.related('level_gpa_id', 'cgpa', type='float', string='CGPA', store=False, readonly=True),
            't_attempted_hours': fields.related('level_gpa_id', 't_attempted_hours', type='float', string='Attempted Hours', store=False, readonly=True),
            't_passed_hours': fields.related('level_gpa_id', 't_passed_hours', type='float', string='Passed Hours', store=False, readonly=True),
            't_earned_hours': fields.related('level_gpa_id', 't_earned_hours', type='float', string='Earned Hours', store=False, readonly=True),
            't_quality_points': fields.related('level_gpa_id', 't_quality_points', type='float', string='Quality Points', store=False, readonly=True),
            't_gpa_hours': fields.related('level_gpa_id', 't_gpa_hours', type='float', string='GPA Hours', store=False, readonly=True),
            't_cgpa': fields.related('level_gpa_id', 't_cgpa', type='float', string='CGPA', store=False, readonly=True),        
            'o_attempted_hours': fields.related('level_gpa_id', 'o_attempted_hours', type='float', string='Attempted Hours', store=False, readonly=True),
            'o_passed_hours': fields.related('level_gpa_id', 'o_passed_hours', type='float', string='Passed Hours', store=False, readonly=True),
            'o_earned_hours': fields.related('level_gpa_id', 'o_earned_hours', type='float', string='Earned Hours', store=False, readonly=True),
            'o_quality_points': fields.related('level_gpa_id', 'o_quality_points', type='float', string='Quality Points', store=False, readonly=True),
            'o_gpa_hours': fields.related('level_gpa_id', 'o_gpa_hours', type='float', string='GPA Hours', store=False, readonly=True),
            'o_cgpa': fields.related('level_gpa_id', 'o_cgpa', type='float', string='CGPA', store=False, readonly=True),  
            'transfer': fields.related('level_gpa_id', 'transfer', type='boolean', string='Transfer', store=False, readonly=True),  
            'state': fields.selection([('draft','Draft'),('in_progress','In Progress'),('to_print','To Print'),('refuse','Refused'),('done','Done')],'Status', required=True, track_visibility="onchange"),
        }
    
    _defaults={
               'order_no': _get_order_no,
               'print_transcript': 'asap',
               'student_id': _get_student_id,
               'copies': 1,
               'state': 'draft',
               'currency_id': _get_currency,
               'transcript_charge': 3000,
               'billing_term': _get_billing_term
        }
    
    _sql_constraints = [
        ('uniq_order_no', 'unique(order_no)', 'You cannot duplicate a transcript request!')
    ]
    
    
class registrar_settings(osv.osv):
    _name = "registrar.settings"
    _inherit = "registrar.settings"
    _columns = {
                'transcript_detail_code': fields.many2one('detail.code', 'Transcript Detail Code', required=False, track_visibility='onchange')    
        }