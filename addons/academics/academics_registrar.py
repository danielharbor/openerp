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
from openerp import SUPERUSER_ID
import collections
import logging
import time
import threading
import psycopg2

from openerp import netsvc
_logger = logging.getLogger(__name__)


ENROLLMENT_STATES = [
    ('registered', 'Registered'),
    ('dropped', 'Dropped'),
    ('deleted', 'Deleted')
]

SECTION_STATES = [
    ('draft', 'Draft'),
    ('active', 'Active'),
    ('cancelled', 'Cancelled')
]

HOLD_STATES = [
    ('draft', 'Draft'),
    ('done', 'Done'),
    ('cancelled', 'Cancelled')
]

ADD_DROP_STATES = [
    ('draft', 'Draft'),
    ('done', 'Done')
]

FORM_STATES = [
    ('draft', 'Draft'),
    ('pending', 'Awaiting Approval'),
    ('approved', 'approved'),
    ('denied', 'Denied'),
    ('cancelled', 'Cancelled'),
]


class res_campus(osv.osv):
    _name = 'res.campus'
    _description = 'Campus'
    _inherit = ["mail.thread"]
    _columns = {
            'name': fields.char('Name', size=128, required=True, track_visibility="onchange"),
            'building_ids': fields.one2many('res.building', 'campus_id', 'Buildings'),
        }
res_campus()

class res_building(osv.osv):
    _name = 'res.building'
    _description = 'Buildings'
    _inherit = ["mail.thread"]
    _columns = {
            'name': fields.char('Name', size=128, required=True, track_visibility="onchange"),
            'campus_id': fields.many2one('res.campus', 'Campus', ondelete="cascade", required=True, track_visibility="onchange"),
            'residence': fields.boolean('Is a Residence', track_visibility="onchange"),
            'gender': fields.selection([('M','Male'),('F','Female'),('G','General')],'Gender', track_visibility="onchange"),
            'unavailable': fields.boolean('Closed For Summer', track_visibility="onchange"),
        }
res_building()

class aun_registrar_duration(osv.osv):
    _name = "aun.registrar.duration"
    _description = "Class Duration"
    _inherit = ["mail.thread"] 
    
    def unlink(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'active': False})
    
    _columns = {
        'name': fields.char('Name', size=32, readonly=True),
        'mon': fields.boolean('Monday', track_visibility="onchange"),
        'tue': fields.boolean('Tuesday', track_visibility="onchange"),
        'wed': fields.boolean('Wednesday', track_visibility="onchange"),
        'thur': fields.boolean('Thursday', track_visibility="onchange"),
        'fri': fields.boolean('Friday', track_visibility="onchange"),
        'sat': fields.boolean('Saturday', track_visibility="onchange"),
        'sun': fields.boolean('Sunday', track_visibility="onchange"),
	    'start_time': fields.char('Start Time', size=5, required=True, track_visibility="onchange"),
        'end_time': fields.char('End Time', size=5, required=True, track_visibility="onchange"),
        'active': fields.boolean('Active', track_visibility='onchange'),
    }
    
    _defaults={
        'active':True
    }
    
    _sql_constraints = [
        ('uniq_duration', 'unique(name)', 'This duration already exists!')
    ]

    def create(self, cr, uid, vals, context=None):
        vals['start_time'] = vals['start_time'].rjust(5, '0')
        vals['end_time'] = vals['end_time'].rjust(5, '0')
        return super(aun_registrar_duration, self).create(cr, uid, vals, context)
        
    def write(self, cr, uid, ids, vals, context=None):
        duration = self.browse(cr, uid, ids, context=context)[0]
        days = []
        duration_time = []
        try:
            if vals['mon']:
                days.append("M")
        except:
            if duration.mon:
                days.append("M")
        try:
            if vals['tue']:
                days.append("T")
        except:
            if duration.tue:
                days.append("T")
        try:
            if vals['wed']:
                days.append("W")
        except:
            if duration.wed:
                days.append("W")
        try:
            if vals['thur']:
                days.append("R")
        except:
            if duration.thur:
                days.append("R")
        try:
            if vals['fri']:
                days.append("F")
        except:
            if duration.fri:
                days.append("F")            
        try:
            if vals['sat']:
                days.append("S")
        except:
            if duration.sat:
                days.append("S")
        try:
            if vals['sun']:
                days.append("U")
        except:
            if duration.sun:
                days.append("U")
        try:
            if vals['start_time']:
                vals['start_time'] = vals['start_time'].rjust(5, '0')
                duration_time.append(vals['start_time'])
        except:
            duration_time.append(duration.start_time)    
        try:
            if vals['end_time']:
                vals['end_time'] = vals['end_time'].rjust(5, '0')
                duration_time.append(vals['end_time'])
        except:
            duration_time.append(str(duration.end_time))
            
        days = ''.join(days)
        duration_time = ' - '.join(duration_time)
        name = days + ' ' + duration_time       
        vals.update({'name': name})
        return super(aun_registrar_duration, self).write(cr, uid, ids, vals, context=context)
    
    def check_duration(self, cr, uid, ids, context=None):
        duration = self.browse(cr, uid, ids,context=context)[0]
        try:
            time.strptime(duration.start_time, '%H:%M')
            time.strptime(duration.end_time, '%H:%M')
        except ValueError:
            raise osv.except_osv(_('Check Start/End Time'), _('Enter a valid time in the specified format (HH:MM)'))
      
        if time.strptime(duration.end_time, '%H:%M') <= time.strptime(duration.start_time, '%H:%M'):
            raise osv.except_osv(_('Check Duration'), _('The end time must be greater than the start time.'))
        
        if not (duration.mon or duration.tue or duration.wed or duration.thur or duration.fri or duration.sat or duration.sun):
            raise osv.except_osv(_('No day selected!'), _('You must pick at least one day of the week.'))
        return True
        
    _constraints=[
        (check_duration, 'Please verify that the end time is greater than the start time and they are both in the correct format.',['Start',' End']),
    ]

aun_registrar_duration()


class aun_registrar_location(osv.osv):
    _name = "aun.registrar.location"
    _description = "Location"
    _inherit = ["mail.thread"]
    _columns = {
        'name': fields.char('Room', size=256, required=True, track_visibility="onchange"),
	    'building_id': fields.many2one('res.building', 'Building', ondelete="cascade", required=True, track_visibility="onchange"),
        'location_type': fields.selection([('1','Lecture Hall'),('2','Lab'),('3','Lecture/Lab'),('4','Residence')],'Location Type', track_visibility="onchange", required=True),
        'capacity': fields.integer('Capacity', required=True, track_visibility="onchange"),
        'floor': fields.selection([('b','Basement'), ('0','Ground'), ('1st','1st'), ('2nd','2nd'), ('3rd','3rd'), ('4th','4th'), ('5th','5th')],'Floor', track_visibility="onchange", required=True),
        'res_room_type': fields.many2one('housing.room.type', 'Room Type', track_visibility="onchange"),
        'isactive': fields.boolean('Active', track_visibility="onchange"),
        'director_id': fields.many2many('housing.res.director','rel_rd_dorm','rooms','name', 'Rooms'),
    }
    _defaults={
        'location_type': '1',
        'isactive' : '1'
    }
    
aun_registrar_location()

class aun_registrar_term(osv.osv):
    _name = "aun.registrar.term"
    _description = "Term"
    _inherit = ["mail.thread"]
    _order = "code DESC"
    
    def _history_open_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('finalgrades_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res.append(('id', 'in', res_ids))
        return res

    def _finalgrades_open_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('finalgrades_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('finalgrades_end','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res.append(('id', 'in', res_ids))
        return res
    
    def _reservation_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('reservation_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('reservation_end','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res.append(('id', 'in', res_ids))
        return res
        
    def _is_active_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('start_date', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('end_date','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res.append(('id', 'in', res_ids))
        return res

    def _registration_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('add_drop_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('add_drop_end','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res_ids2 = self.search(cursor, user, [('reg_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('reg_end','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res_ids = list(set(res_ids + res_ids2))
        res.append(('id', 'in', res_ids))
        return res

    def _clearance_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('clearance_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('clearance_end','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res.append(('id', 'in', res_ids))
        return res

    def _admission_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('admission_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('admission_end','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res.append(('id', 'in', res_ids))
        return res
    
    def _midterm_grading_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('faculty_midterm_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('faculty_midterm_end','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res.append(('id', 'in', res_ids))
        return res
    
    def _grading_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('faculty_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('faculty_end','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res.append(('id', 'in', res_ids))
        return res
    
    def _compute_term_code(self, cr, uid, ids, code, arg, context=None):
        res={}
        for term in self.browse(cr, uid, ids):
            prefix = str(int(term.year) + int(term.name.year_adjustment))
            suffix = str(term.name.code)
            code = str(prefix + suffix)
            res[term.id] = code
        return res
 
    def on_change_date(self, cr, uid, ids, field_name, start_date, end_date, context=None):    
        result = {'value': {field_name: start_date <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= end_date}}
        return result
    
    def _check_term_start_end_dates(self, cr, uid, ids, context=None):
        term = self.browse(cr, uid, ids,context=context)[0]
        if term.start_date and term.end_date:
            return term.end_date > term.start_date
        return True
    
    def _check_reg_dates(self, cr, uid, ids, context=None):
        term = self.browse(cr, uid, ids,context=context)[0]
        if term.reg_start and term.reg_end:
            return term.reg_end > term.reg_start
        return True
    
    def _check_reg(self, cr, uid, ids, context=None):
        term = self.browse(cr, uid, ids,context=context)[0]
        if term.reg_start and term.reg_end:
            return term.reg_end < term.start_date
        return True

    def _check_add_drop_dates(self, cr, uid, ids, context=None):
        term = self.browse(cr, uid, ids,context=context)[0]
        if term.add_drop_start and term.add_drop_end:
            return term.add_drop_end > term.add_drop_start
        return True 
    
#     def _check_add_drop(self, cr, uid, ids, context=None):
#         term = self.browse(cr, uid, ids,context=context)[0]
#         if term.add_drop_start and term.add_drop_end:
#             return (term.start_date <= term.add_drop_start < term.end_date) and (term.start_date <= term.add_drop_end < term.end_date)
#         return True

    def _check_clearance_dates(self, cr, uid, ids, context=None):
        term = self.browse(cr, uid, ids,context=context)[0]
        if term.clearance_start and term.clearance_end:
            return term.clearance_end > term.clearance_start
        return True

    def _check_admission_dates(self, cr, uid, ids, context=None):
        term = self.browse(cr, uid, ids,context=context)[0]
        if term.admission_start and term.admission_end:
            return term.admission_end > term.admission_start
        return True
    
    def _check_reservation_dates(self, cr, uid, ids, context=None):
        term = self.browse(cr, uid, ids,context=context)[0]
        if term.reservation_start and term.reservation_end:
            return term.reservation_end > term.reservation_start
        return True

    def _check_faculty_midterm_dates(self, cr, uid, ids, context=None):
        term = self.browse(cr, uid, ids,context=context)[0]
        if term.faculty_midterm_start and term.faculty_midterm_end:
            return term.faculty_midterm_end > term.faculty_midterm_start
        return True
  
    def _check_faculty_dates(self, cr, uid, ids, context=None):
        term = self.browse(cr, uid, ids,context=context)[0]
        if term.faculty_start and term.faculty_end:
            return term.faculty_end > term.faculty_start
        return True
 
    def _check_finalgrades_dates(self, cr, uid, ids, context=None):
        term = self.browse(cr, uid, ids,context=context)[0]
        if term.finalgrades_start and term.finalgrades_end:
            return term.finalgrades_end > term.finalgrades_start
        return True

    def _check_dates(self, cursor, uid, ids, name, arg, context=None):
        res = {} 
        for term in self.browse(cursor, uid, ids, context=context):
            res[term.id] = {}
            res[term.id]['is_active'] = term.start_date <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= term.end_date
            res[term.id]['open_for_clearance'] = term.clearance_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= term.clearance_end
            res[term.id]['finalgrades_open'] = term.finalgrades_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= term.finalgrades_end
            res[term.id]['open_for_reservation'] = term.reservation_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= term.reservation_end
            res[term.id]['open_for_admission'] = term.admission_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= term.admission_end
            res[term.id]['open_for_registration'] = (term.reg_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= term.reg_end) or (term.add_drop_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= term.add_drop_end)
            res[term.id]['open_for_midterm_grading'] = term.faculty_midterm_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= term.faculty_midterm_end
            res[term.id]['open_for_grading'] = term.faculty_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= term.faculty_end
            res[term.id]['history_open'] = term.finalgrades_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return res

    def _get_term_name(self, cursor, uid, ids, name, arg, context=None):
        res = {}
        for term in self.browse(cursor, uid, ids, context=context):
            res[term.id] = term.name.name + ' ' + term.year
        return res

    def _populate_year(self, cr, uid, context=None):
        current_year = date.today().year
        return [(str(i), str(i)) for i in range(2005, current_year+10)]

    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'done'
        return super(aun_registrar_term, self).create(cr, uid, vals, context)

    _columns = {
		'name': fields.many2one('aun.term.term', 'Term', required=True, write=['academics.group_registrar_registrar'], track_visibility="onchange"),
        'year': fields.selection(_populate_year, 'Year', required=True, write=['academics.group_registrar_registrar'], track_visibility="onchange"),
		'term_name': fields.function(_get_term_name, string='Term Name', type='char', method=True, store=True),
        'code': fields.function(_compute_term_code, type='integer', method=True, string='Code', store=True),
        'open_for_clearance': fields.function(_check_dates, string='Open for Clearance', type='boolean', method=True, multi='checks', store=False, fnct_search=_clearance_search),
        'open_for_admission': fields.function(_check_dates, string='Open for Admission', type='boolean', method=True, multi='checks', store=False, fnct_search=_admission_search),
        'open_for_midterm_grading': fields.function(_check_dates, string='Open for Midterm Grading', type='boolean', method=True, multi='checks', store=False, fnct_search=_midterm_grading_search),
        'open_for_grading': fields.function(_check_dates, string='Open for Grading', type='boolean', method=True, multi='checks', store=False, fnct_search=_grading_search),
        'open_for_registration': fields.function(_check_dates, string='Open for Registration', type='boolean', method=True, multi='checks', store=False, fnct_search=_registration_search),
        'open_for_reservation': fields.function(_check_dates, string='Open for Reservation', type='boolean', method=True, multi='checks', store=False, fnct_search=_reservation_search),
        'finalgrades_open': fields.function(_check_dates, string='Final Grades Open', type='boolean', method=True, multi='checks', store=False, fnct_search=_finalgrades_open_search),
        'history_open': fields.function(_check_dates, string='Academic History Open', type='boolean', method=True, multi='checks', store=False, fnct_search=_history_open_search),
        'is_active': fields.function(_check_dates, string='Active', type='boolean', method=True, multi='checks', store=False, fnct_search=_is_active_search),
        'start_date': fields.datetime('Start Date', write=['academics.group_registrar_registrar'], track_visibility="onchange"),
        'end_date': fields.datetime('End Date', write=['academics.group_registrar_registrar'], track_visibility="onchange"),
        'clearance_start':fields.datetime('Clearance Start Date', track_visibility="onchange"),
        'clearance_end':fields.datetime('Clearance End Date', track_visibility="onchange"),
        'admission_start':fields.datetime('Admission Start Date', track_visibility="onchange"),
        'admission_end':fields.datetime('Admission End Date', track_visibility="onchange"),
        'reg_start': fields.datetime('Registration Start Date', track_visibility="onchange"),
        'reg_end': fields.datetime('Registration End Date', track_visibility="onchange"),
        'add_drop_start': fields.datetime('Add/Drop Start Date', track_visibility="onchange"),
        'add_drop_end': fields.datetime('Add/Drop End Date', track_visibility="onchange"),
        'reservation_start': fields.datetime('Housing Reservation Start Date', track_visibility="onchange"),
        'reservation_end': fields.datetime('Housing Reservation End Date', track_visibility="onchange"),
        'faculty_start': fields.datetime('Grading Start Date', track_visibility="onchange"),
        'faculty_end': fields.datetime('Grading End Date', track_visibility="onchange"),
        'faculty_midterm_start': fields.datetime('Midterm Grading Start Date', track_visibility="onchange"),
        'faculty_midterm_end': fields.datetime('Midterm Grading End Date', track_visibility="onchange"),
        'finalgrades_start': fields.datetime('Student Grades Start Date', track_visibility="onchange"),
        'finalgrades_end': fields.datetime('Student Grades End Date', track_visibility="onchange"),
        'admin_reg': fields.boolean('Open Admin Registration'),
		'section_ids': fields.one2many('aun.registrar.section', 'term_id', 'Sections', select=True, track_visibility="onchange"),
		'billing_date' : fields.date('Start Date', track_visibility="onchange"),
        'state': fields.selection(ADD_DROP_STATES, 'State')
    }
    _defaults={
        'state': 'draft'
    }
    
    _sql_constraints = [
        ('term_uniq', 'unique(name, year)', 'This term already exists!'),
    ]
    
    _constraints=[
        (_check_term_start_end_dates, 'Please verify that the term end date is greater than the start date.',['Start Date',' End Date']),
        (_check_reg_dates, 'The end date should be greater than the start date.',['Registration Start/End']),
        (_check_reg, 'Registration should end before the term start date.',['Registration End',]),
        (_check_add_drop_dates, 'The end date should be greater than the start date.',['Add&Drop Start/End']),
#         (_check_add_drop, 'These dates should be between the term start and end dates.',['Add&Drop Start/End']),
        (_check_clearance_dates, 'The end date should be greater than the start date.',['Clearance Start/End']),
        (_check_admission_dates, 'The end date should be greater than the start date.',['Admission Start/End']),
        (_check_reservation_dates, 'The end date should be greater than the start date.',['Reservation Start/End']),
        (_check_faculty_midterm_dates, 'The end date should be greater than the start date.',['Faculty Midterm Start/End']),
        (_check_faculty_dates, 'The end date should be greater than the start date.',['Faculty Start/End']),
        (_check_finalgrades_dates, 'The end date should be greater than the start date.',['View Final Grades Start/End']),
    ]
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['name', 'year'], context=context)
        res = []
        for record in reads:
            name = str(record['name'][1])
            name = name + ' ' + str(record['year'])
            res.append((record['id'], name))
        return res
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('term_name','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('term_name',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)
    
aun_registrar_term()


class aun_term_term(osv.osv):
    _name = "aun.term.term"
    _description = "Term"
    _inherit = ["mail.thread"]
    _order = 'code ASC'
    _columns = {
        'name': fields.char('Name', size=32, required=True, track_visibility="onchange"),
        'code': fields.integer('Code', required=True, track_visibility="onchange", help='The term with the lowest code comes first in the calendar year e.g. Fall (10) comes before Spring (20)'),
        'year_adjustment': fields.selection([('0','0'), ('-1','-1')], 'Year Adjustment', required=True, track_visibility="onchange"),
        'defaults': fields.one2many('aun.level.term.defaults', 'term_term_id', 'Level Defaults'),
        }
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'This name already exists!'),
        ('code_uniq', 'unique(code)', 'There is already a term with this code!')
    ]
    
aun_term_term()


class registrar_status(osv.osv):
    _name = "registrar.status"
    _description = "Status"
    _order = 'range_start ASC'
    _inherit = ["mail.thread"]
    _columns = {
        'name': fields.char('Name', size=32, required=True, track_visibility="onchange"),
        'range_start': fields.float('Credit Hour Range', digits=(3,2), required=True, track_visibility="onchange"),
        'range_end': fields.float('Credit Hour Range', digits=(3,2), required=True, track_visibility="onchange"),
        'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility="onchange"),
        }
 
    def _check_range(self, cr, uid, ids, context=None):
        status = self.browse(cr, uid, ids, context=context)[0]
        if status.range_start >= status.range_end:
            raise osv.except_osv(_('Check ' + status.name), _('The range end must be greater than the range start.'))
        status_ids = self.search(cr, uid, [('level_id','=',status.level_id.id),('id','not in',[status.id])])
        
        for stat in self.browse(cr, uid, status_ids):
            if (stat.range_start < status.range_start < stat.range_end or
                stat.range_start < status.range_end < stat.range_end or
                status.range_start < stat.range_end < status.range_end or
                status.range_start < stat.range_end < status.range_end or
                stat.range_start == status.range_start or
                stat.range_end == status.range_end or
                stat.range_start == status.range_end or
                stat.range_end == status.range_start):
                    raise osv.except_osv(_('Check ' + status.name), _('The status range coincides with the range for the ' + stat.name + ' status'))
        return True
   
    def _uniq_name(self, cr, uid, ids, context=None):
        status = self.browse(cr, uid, ids, context=context)[0]
        status_ids = self.search(cr, uid, [('level_id','=',status.level_id.id),('id','not in',[status.id])])       
        for stat in self.browse(cr, uid, status_ids):
            if stat.name.lower() == status.name.lower():
                raise osv.except_osv(_('Check status name!'), _('There is another status with the same name: ' + stat.name + '. The name must be unique.'))
        return True
    
    _constraints=[
        (_check_range, 'Status ranges should be chronological.', ['Range']),
        (_uniq_name, 'There is another status with the same name.', ['Name'])
    ]
    
registrar_status()


class student_state(osv.osv):
    _name = "student.state"
    _description = "Student State"
    _inherit = ["mail.thread"]
    _columns = {
        'name': fields.char('Name', size=32, required=True, track_visibility="onchange"),
        'is_active': fields.boolean('Active', help='Leave unchecked for a state that requires a date e.g. Dismissed', track_visibility="onchange"),
        'proh_reg': fields.boolean('Prohibit Add/Drop', help='Check to prohibit students in this state from registering for classes', track_visibility="onchange"),
        'transcript': fields.boolean('Prohibit Transcript', help='Check to prohibit students in this state from printing their academic transcript', track_visibility="onchange"),
        'graduated': fields.boolean('Graduated', help='Check to indicate graduated state', track_visibility="onchange"),
        'default_state': fields.boolean('Default')
        }
   
    def _uniq_name(self, cr, uid, ids, context=None):
        state = self.browse(cr, uid, ids, context=context)[0]
        state_ids = self.search(cr, uid, [('id','not in',[state.id])])       
        for s in self.browse(cr, uid, state_ids):
            if s.name.lower() == state.name.lower():
                raise osv.except_osv(_('Check state name!'), _('There is another state with the same name: ' + s.name + '. The name must be unique.'))
        return True

    def _check_default_state(self, cr, uid, ids, context=None):
        if self.search(cr, uid, [('default_state','=', True)], count=True) > 1:
            raise osv.except_osv(_('Check Default'), _('Only one state can be set as the default state.'))     
        return True
    
    _constraints=[
        (_uniq_name, 'There is another state with the same name.', ['Name']),
        (_check_default_state, 'You can only set one state as default.', ['Default'])
    ]
    
student_state()


class aun_level_term_defaults(osv.osv):
    _name = "aun.level.term.defaults"
    _description = "Level Term Defaults"
    _inherit = ["mail.thread"]
    _columns = {
        'term_term_id': fields.many2one('aun.term.term', 'Term', ondelete="cascade", track_visibility="onchange"),
        'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility="onchange"),
        'minimum_hours': fields.float('Minimum Credit Hours', digits=(3,2), required=True, track_visibility="onchange"),
        'maximum_hours': fields.float('Maximum Credit Hours', digits=(3,2), required=True, track_visibility="onchange") 
        }
    
    _sql_constraints = [
        ('term_level_uniq', 'unique(term_term_id, level_id)', 'The default already exists for this term!')
    ]
    
aun_level_term_defaults()


class aun_faculty_section(osv.osv):
    _name = "aun.faculty.section"
    _description = "Faculty Section"
    _inherit = ["mail.thread"]

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            res.append((record['id'], record.faculty_id.name))
        return res
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('faculty_id','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('faculty_id',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    def create(self, cr, uid, vals, context=None):            
        res = super(aun_faculty_section, self).create(cr, uid, vals, context)
        fs = self.browse(cr, uid, res)
        lab_or_section = fs.section_id or fs.lab_id
        section_id = lab_or_section.id if lab_or_section._name == 'aun.registrar.section' else lab_or_section.section_id.id
        if fs.faculty_id.user_id:
            ctx = dict(subscribe=True)
            self.pool.get('aun.registrar.section').message_subscribe_users(cr, SUPERUSER_ID, [section_id], [fs.faculty_id.user_id.id], context=ctx)
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        faculty_sections = self.browse(cr, uid, ids, context=context)
        for fs in faculty_sections:
            lab_or_section = fs.section_id or fs.lab_id
            section_id = lab_or_section.id if lab_or_section._name == 'aun.registrar.section' else lab_or_section.section_id.id
            if fs.faculty_id.user_id:
                ctx = dict(subscribe=True)
                self.pool.get('aun.registrar.section').message_unsubscribe_users(cr, SUPERUSER_ID, [section_id], [fs.faculty_id.user_id.id], context=ctx)
        osv.osv.unlink(self, cr, uid, ids, context=context)
        return True
    
    _columns = {
        'faculty_id': fields.many2one('hr.employee', 'Faculty', required=True, track_visibility="onchange"),
        'section_id': fields.many2one('aun.registrar.section', 'Section', ondelete='cascade'),
        'lab_id': fields.many2one('section.lab', 'Lab', ondelete='cascade'),
        'percentage': fields.float('Percentage', track_visibility="onchange"),
        'primary': fields.boolean('Primary', track_visibility="onchange"),
        }
    
    _defaults={
        'percentage': 100
        }
    
    _sql_constraints = [
        ('faculty_section_uniq', 'unique(section_id, faculty_id)', 'There is a duplicate faculty in this section!')
    ]
    
aun_faculty_section()


class section_lab(osv.osv):
    _name = "section.lab"
    _description = "Lab"
    _inherit = ["mail.thread"]
    
    def _has_enrollment(self, cr, uid, ids, field_name, arg=None, context=None):
        res={}
        for lab in self.browse(cr, uid, ids):
            if lab.enrollment_ids:
                res[lab.id] = True
            else:
                res[lab.id] = False
        return res

    def _get_faculty(self, cursor, uid, ids, name, arg, context=None):
        res = {}
        for lab in self.browse(cursor, uid, ids, context=context):
            res[lab.id] = [(6, 0, [fs.faculty_id.id for fs in lab.faculty])]
        return res
 
    def write(self, cr, uid, ids, vals, context=None):
        res = super(section_lab, self).write(cr, uid, ids, vals, context=context)
        lab = self.browse(cr, uid, ids, context=context)[0]        
        faculty_emp_ids = [fs.faculty_id.id for fs in lab.faculty]
        enr_obj = self.pool.get('aun.registrar.enrollment')
        lab_enr_ids = enr_obj.search(cr, uid, [('lab_id','=',lab.id)])
        super(aun_registrar_enrollment, enr_obj).write(cr, uid, lab_enr_ids, {'faculty_emp_ids': [(6, 0, faculty_emp_ids)]})
        return res
 
    #if there are students registered for lab, drop their enrollments and change the lab state to cancelled, else delete the lab completely
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}       
        enr_obj = self.pool.get('aun.registrar.enrollment')
        unlink_lab_ids = []
        for lab_id in ids:
            lab_enr_ids = enr_obj.search(cr, uid, [('lab_id','=',lab_id),('state','=','registered')])
            if lab_enr_ids:
                '''super(aun_registrar_enrollment, enr_obj).write(cr, uid, lab_enr_ids, {'state': 'dropped', 'active': False}, context=context)
                super(section_lab, self).write(cr, uid, lab_id, {'state': 'cancelled', 'mandatory': False}, context=context)
                
                add_drop_obj = self.pool.get('aun.add.drop')
                for enr in enr_obj.browse(cr, uid, lab_enr_ids):
                    add_drop_id = add_drop_obj.search(cr, uid, [('term_id','=',enr.term_id.id),('student_id','=',enr.student_id.id)], context=context)
                    super(aun_add_drop, add_drop_obj).write(cr, uid, add_drop_id, {'labs': [(3, lab_id)]})'''
                raise osv.except_osv(_('Invalid'), _('There are students already registered for the deleted lab(s). Cancel the section to drop them.')) 
            else:
                unlink_lab_ids.append(lab_id)
        osv.osv.unlink(self, cr, uid, unlink_lab_ids, context=context)
        return True
    
    def _get_enrolled(self, cr, uid, ids, enrolled, arg, context=None):
        res = {}
        enr_obj = self.pool.get('aun.registrar.enrollment')
        for lab_id in ids:
            lab_enr_ids = enr_obj.search(cr, uid, [('lab_id','=',lab_id),('state','=','registered')])
            res[lab_id] = len(lab_enr_ids)
        return res
    
    def _get_enrollments(self, cr, uid, ids, context=None):
        cr.execute("""SELECT DISTINCT lab_id FROM aun_registrar_enrollment
                                    WHERE id = ANY(%s)""", (list(ids),))
        return [i[0] for i in cr.fetchall()]

    _columns = {
        'name': fields.char('Description', size=32, required=True, track_visibility="onchange"),
        'section_id': fields.many2one('aun.registrar.section', 'Section', required=True, ondelete='cascade', track_visibility="onchange"),
        'term_id': fields.related('section_id', 'term_id', type='many2one', relation='aun.registrar.term', string='Term', store=True, readonly=True),
        'course_id': fields.related('section_id', 'course_id', type='many2one', relation='aun.registrar.course', string='Course', store=True, readonly=True),
        'mandatory': fields.boolean('Mandatory', track_visibility="onchange"),
        'capacity': fields.integer('Capacity', required=True, track_visibility="onchange"),
        'enrollment_ids': fields.one2many('aun.registrar.enrollment', 'lab_id', 'Enrollees', domain=[('state','=','registered')]),
        'enrolled': fields.function(_get_enrolled, method=True, type='integer', string='Enrolled',
                            store={
                                'aun.registrar.enrollment': (_get_enrollments, ['state'], 10)
                            }),
        'duration_id': fields.many2one('aun.registrar.duration', 'Time', track_visibility="onchange"),
        'location_id': fields.many2one('aun.registrar.location', 'Location', track_visibility="onchange"),
        'faculty': fields.one2many('aun.faculty.section', 'lab_id', 'Faculty'),
        'faculty_tree': fields.function(_get_faculty, string='Faculty', type='many2many', method=True, store=False, relation='hr.employee'),
        'has_enrollment': fields.function(_has_enrollment, method=True, type='boolean', string='Has Enrollment', store=False),
        'state': fields.selection(SECTION_STATES, 'Status', size=16, readonly=True, track_visibility="onchange")
        }
    _defaults = {
        'mandatory': True,
        'state': 'active'
        }    
    _sql_constraints = [
        ('name_uniq', 'unique(section_id, name)', 'Lab description must be unique!')
    ]
    
section_lab()

class registrar_settings(osv.osv):
    _name = "registrar.settings"
    _description = "Registrar Settings"
    _inherit = ["mail.thread"]  

    def write(self, cr, uid, ids, vals, context=None):
        settings = self.browse(cr, uid, ids, context=context)[0]
        updated = False
        if 'include_current_hrs' in vals:
            if vals['include_current_hrs'] != settings.include_current_hrs:
                updated = True
        res = super(registrar_settings, self).write(cr, uid, ids, vals, context=context)
        if updated:
            self.pool.get('aun.registrar.enrollment').update_all_students_gpa_info(cr, uid, context=context)
        return res
    
    def on_change_include_current_hrs(self, cr, uid, ids, context=None):
        return {'warning': {'title': _('Warning'), 'message': _('Please note that after you click save, the computation might take a while.')}}
        
    def on_change_level(self, cr, uid, ids, context=None):
        return {'value': {'status_id': False}}
    
    _columns = {
        'name': fields.char('Name'),
        'interval': fields.integer('Minimum Class Interval', required=True, help='Minimum class interval in minutes', track_visibility="onchange"),
        'allow_prereq': fields.boolean('Permit prerequisites without grade requirement', track_visibility="onchange"),
        'include_current_hrs': fields.boolean('Include credits for active term', track_visibility="onchange"),
        }
     
registrar_settings()


class aun_registrar_course(osv.osv):
    _name = "aun.registrar.course"
    _description = "Course"
    _inherit = ["mail.thread"]
    

    def _has_section(self, cr, uid, ids, field_name, arg=None, context=None):
        res={}
        for course in self.browse(cr, uid, ids):
            if course.section_ids:
                res[course.id] = True
            else:
                res[course.id] = False
        return res

    _columns = {
        'name': fields.char('Name', size=8, track_visibility="onchange"),
        'subject_id': fields.many2one('course.subject', 'Subject', required=True, track_visibility="onchange"),
        'school_id': fields.related('subject_id', 'school_id', type='many2one', relation='aun.registrar.school', string="School",store=True,readonly=True,track_visibility="onchange"),
        'code': fields.char('Course Code', size=4, required=True, track_visibility="onchange"),
        'create_date': fields.date('Date Created', readonly=True, select=True, track_visibility="onchange"),
        'end_date': fields.date('Date Ended', readonly=True, select=True, track_visibility="onchange"),
        'active': fields.boolean('Active', track_visibility="onchange"),
	    'course_name': fields.char('Course Title', size=32, required=True, track_visibility="onchange"),
        'description': fields.text('Description', track_visibility="onchange"),
        'repeat_limits': fields.one2many('aun.registrar.repeat', 'course_id', 'Repeat Limit'),
        'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility="onchange"),
        'status_id': fields.many2one('registrar.status', 'Status', required=True, domain="[('level_id','=',level_id)]", track_visibility="onchange"),
        'grademode_id': fields.many2one('aun.registrar.grademode', 'Grade Mode', required=True, track_visibility="onchange"),
        'course_type_id': fields.many2one('course.type', 'Type', required=True, track_visibility="onchange"),
	    'section_ids': fields.one2many('aun.registrar.section', 'course_id', 'Sections'),
        'prerequisite_ids': fields.one2many('aun.registrar.cat.prerequisite', 'course_id', 'Prerequisites'),
        'corequisite_ids': fields.one2many('registrar.corequisite', 'course_id', 'Co-Requisites'),
        'equivalents': fields.many2many('aun.registrar.course','rel_course_equivalent','id','equivalents', 'Equivalent Courses'),
        'credit_low': fields.float('Minimum Credit Hours', digits=(3,2), required=True, track_visibility="onchange"),
        'credit_high': fields.float('Maximum Credit Hours', digits=(3,2), required=True, track_visibility="onchange"),
        'billing_low': fields.float('Minimum Billing Hours', digits=(3,2), required=True, track_visibility="onchange"),
        'billing_high': fields.float('Maximum Billing Hours', digits=(3,2), required=True, track_visibility="onchange"),
        'has_section': fields.function(_has_section, method=True, type='boolean', string='Has Section', store=False),
        'exclude': fields.boolean('Exclude from repeat')
        }
    _defaults={
        'active': True,
        'credit_low': 3,
        'credit_high': 3,
        'billing_low': 3,
        'billing_high': 3
        }
    
    def unlink(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'active': False})

    def write(self, cr, uid, ids, vals, context=None):
        course = self.browse(cr, uid, ids, context=context)[0]
        subj_obj = self.pool.get('course.subject')
        name = ''
        try:
            name = subj_obj.browse(cr, uid, vals['subject_id']).name
        except:
            name = course.subject_id.name
        try:
            name += ' ' + vals['code']
        except:
            name += ' ' + course.code
            
        if name != course.name:        
            vals.update({'name': name})
        return super(aun_registrar_course, self).write(cr, uid, ids, vals, context=context)

    def on_change_level(self, cr, uid, ids, context=None):
        return {'value': {'status_id': False}}

    def _check_prereq_recursion(self, cr, uid, ids, context=None):
        course = self.browse(cr, uid, ids,context=context)[0]
        prerequisites = course.prerequisite_ids
        for prerequisite in prerequisites:
            lines = prerequisite.prerequisite_ids
            for line in lines:
                if line.prerequisite_id.id == course.id:
                    raise osv.except_osv(_('Check Prerequisites!'), _('A course cannot be a prerequisite for itself: ' + prerequisite.catalogue_id.name_get()[0][1] + ' catalog.'))
        return True
    
    def _check_coreq_recursion(self, cr, uid, ids, context=None):
        course = self.browse(cr, uid, ids,context=context)[0]
        corequisites = course.corequisite_ids
        for corequisite in corequisites:
            coreqs = corequisite.corequisites
            for coreq in coreqs:
                if coreq.id == course.id:
                    raise osv.except_osv(_('Check Corequisites!'), _('A course cannot be a corequisite to itself: ' + corequisite.catalogue_id.name_get()[0][1] + ' catalog.'))
        return True
    
    def _check_credit_and_billing(self, cr, uid, ids, context=None):
        course = self.browse(cr, uid, ids,context=context)[0]
        if course.credit_low < 0:
            raise osv.except_osv(_('Check Credit!'), _('The minimum credit cannot be less than zero.'))
        if course.billing_low < 0:
            raise osv.except_osv(_('Check Credit!'), _('The minimum billing cannot be less than zero.'))
        if course.credit_low > course.credit_high:
            raise osv.except_osv(_('Check Credit!'), _('The minimum credit cannot be greater than the maximum credit.'))
        if course.billing_low > course.billing_high:
            raise osv.except_osv(_('Check Billing!'), _('The minimum billing cannot be greater than the maximum billing.'))
        return True

    _sql_constraints = [
        ('course_uniq', 'unique(name)', 'There is another course with the same name!')
    ]
    
    _constraints = [
        (_check_prereq_recursion, 'A course cannot be a prerequisite to itself!', ['Prerequisites']),
        (_check_coreq_recursion, 'A course cannot be a corequisite to itself!', ['Corequisites']),
        (_check_credit_and_billing, 'Credit and billing high should be greater than credit and billing low!', ['Credit/Billing'])
    ]

aun_registrar_course()

class aun_registrar_repeat(osv.osv):
    _name = "aun.registrar.repeat"
    _description = "Repeat Limit"
    
    def _populate_limit(self, cr, uid, context=None):
        return [(str(i), str(i)) for i in range(100)]
    
    _columns = {
        'limit': fields.selection(_populate_limit, 'Limit', required=True, track_visibility="onchange"),
        'catalogue_id': fields.many2one('aun.registrar.catalogue', 'Catalogue', ondelete="cascade", required=True, track_visibility="onchange"),
        'course_id': fields.many2one('aun.registrar.course', 'Course', ondelete="cascade", track_visibility="onchange")        
    }

    _sql_constraints = [
        ('cat_course_uniq', 'unique(catalogue_id, course_id)', 'There is a duplicate catalogue in the repeat limit!'),
    ]
    
aun_registrar_repeat()

class gpa_info(osv.osv):
    _name = "gpa.info"
    _description = "GPA info"
    _order = "term_id DESC"

    def fields_get(self, cr, uid, fields=None, context=None):
        res = super(gpa_info, self).fields_get(cr, uid, fields, context)
        student_obj = self.pool.get('res.partner')
        student_id = student_obj.search(cr, SUPERUSER_ID, [('user_ids','in',uid),('student','=',True)])
        if student_id:
            term_obj = self.pool.get('aun.registrar.term')
            term_ids = term_obj.search(cr, uid, [], context=None)
            terms = term_obj.browse(cr, uid, term_ids, context=None)
            for term in terms:
                finalgrade_id = self.search(cr, uid, [('term_id','=',term.id), ('student_id','in',student_id)], context=None)
                if finalgrade_id:
                    grade_hold = student_obj.get_holds(cr, SUPERUSER_ID, student_id[0])['grades']
                    if grade_hold:
                        holds = student_obj.browse(cr, uid, student_id[0], context=context).holds
                        hold_names = ', '.join(list(set([hold.hold_id.name for hold in holds if hold.hold_id.grades and hold.is_active])))
                        raise osv.except_osv(_('Hold Restriction!'), _('You have the following hold(s) on your record: ' + hold_names))
        return res

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):       
            for record in reads:
                name = record.term_id.name_get()[0][1]
                res.append((record['id'], name))
        else:
            for record in reads:
                name = record.student_id.name + '/' + record.term_id.name_get()[0][1]
                res.append((record['id'], name))
        return res 
   
    def unlink(self, cr, uid, ids, context=None):
        if context.get('delete'):
            osv.osv.unlink(self, cr, uid, ids, context=context)
        else:
            raise osv.except_osv(_('Invalid action !'), _('GPA information cannot be deleted.'))

    def get_term_attempted_hours(self, cr, uid, term_id, student_id, level_gpa_id, context=None):
        enr_obj = self.pool.get('aun.registrar.enrollment')
        ids = enr_obj.search(cr, uid, [('student_id','=',student_id), ('term_id','=',term_id), ('level_gpa_id','=',level_gpa_id), ('state','=','registered')])
        enrollments = enr_obj.browse(cr, uid, ids)
        total_hrs = 0
        for enrollment in enrollments:
            if enrollment.grade.attempted:
                total_hrs += enrollment.credit
        return '{0:.2f}'.format(total_hrs)
 
    def get_term_transfer_attempted_hours(self, cr, uid, term_id, student_id, level_gpa_id, context=None):
        tce_obj = self.pool.get('transfer.course.equivalent')
        ids = tce_obj.search(cr, uid, [('student_id','=',student_id), ('term_id','=',term_id), ('level_gpa_id','=',level_gpa_id)])
        transfers = tce_obj.browse(cr, uid, ids)
        total_hrs = 0
        for transfer in transfers:
            if transfer.grade_id.attempted:
                total_hrs += transfer.credit
        return '{0:.2f}'.format(total_hrs)
   
    def get_term_quality_points(self, cr, uid, term_id, student_id, level_gpa_id, context=None):
        enr_obj = self.pool.get('aun.registrar.enrollment')
        ids = enr_obj.search(cr, uid, [('student_id','=',student_id), ('term_id','=',term_id), ('level_gpa_id','=',level_gpa_id), ('state','=','registered'), ('repeat','not in',['E'])])
        enrollments = enr_obj.browse(cr, uid, ids)
        points = 0.00
        for enrollment in enrollments:
            try:
                points += (enrollment.grade.quality_points * enrollment.credit)
            except Exception:
                points = points
        if(points == 0.00):
            return '0.00'
        return '{0:.2f}'.format(points)

    def get_term_transfer_quality_points(self, cr, uid, term_id, student_id, level_gpa_id, context=None):
        tce_obj = self.pool.get('transfer.course.equivalent')
        ids = tce_obj.search(cr, uid, [('student_id','=',student_id), ('term_id','=',term_id), ('level_gpa_id','=',level_gpa_id), ('repeat','not in',['E'])])
        transfers = tce_obj.browse(cr, uid, ids)
        points = 0.00
        for transfer in transfers:
            try:
                points += (transfer.grade_id.quality_points * transfer.credit)
            except Exception:
                points = points
        if(points == 0.00):
            return '0.00'
        return '{0:.2f}'.format(points)
    
    def get_term_passed_hours(self, cr, uid, term_id, student_id, level_gpa_id, context=None):
        enr_obj = self.pool.get('aun.registrar.enrollment')
        ids = enr_obj.search(cr, uid, [('student_id','=',student_id), ('term_id','=',term_id), ('level_gpa_id','=',level_gpa_id), ('state','=','registered'), ('repeat','not in',['E'])])
        enrollments = enr_obj.browse(cr, uid, ids)
        total_hrs = 0
        for enrollment in enrollments:
            if enrollment.grade.passed:
                total_hrs += enrollment.credit
        if(total_hrs == 0):
            return '0.00'
        return '{0:.2f}'.format(total_hrs)
    
    def get_term_transfer_passed_hours(self, cr, uid, term_id, student_id, level_gpa_id, context=None):
        tce_obj = self.pool.get('transfer.course.equivalent')
        ids = tce_obj.search(cr, uid, [('student_id','=',student_id), ('term_id','=',term_id), ('level_gpa_id','=',level_gpa_id), ('repeat','not in',['E'])])
        transfers = tce_obj.browse(cr, uid, ids)
        total_hrs = 0
        for transfer in transfers:
            if transfer.grade_id.passed:    
                total_hrs += float(transfer.credit)
        if(total_hrs == 0):
            return '0.00'
        return '{0:.2f}'.format(total_hrs)
    
    def get_term_earned_hours(self, cr, uid, term_id, student_id, level_gpa_id, context=None):
        enr_obj = self.pool.get('aun.registrar.enrollment')
        ids = enr_obj.search(cr, uid, [('student_id','=',student_id), ('term_id','=',term_id), ('level_gpa_id','=',level_gpa_id), ('state','=','registered'), ('repeat','not in',['E'])])
        enrollments = enr_obj.browse(cr, uid, ids)
        total_hrs = 0
        for enrollment in enrollments:
            if enrollment.grade.earned:
                total_hrs += enrollment.credit
        if(total_hrs == 0):
            return '0.00'
        return '{0:.2f}'.format(total_hrs)
    
    def get_term_transfer_earned_hours(self, cr, uid, term_id, student_id, level_gpa_id, context=None):
        tce_obj = self.pool.get('transfer.course.equivalent')
        ids = tce_obj.search(cr, uid, [('student_id','=',student_id), ('term_id','=',term_id), ('level_gpa_id','=',level_gpa_id), ('repeat','not in',['E'])])
        transfers = tce_obj.browse(cr, uid, ids)
        total_hrs = 0
        for transfer in transfers:
            if transfer.grade_id.earned:
                total_hrs += transfer.credit
        if(total_hrs == 0):
            return '0.00'
        return '{0:.2f}'.format(total_hrs)

    def get_term_gpa_hours(self, cr, uid, term_id, student_id, level_gpa_id, context=None):
        enr_obj = self.pool.get('aun.registrar.enrollment')
        ids = enr_obj.search(cr, uid, [('student_id','=',student_id), ('term_id','=',term_id), ('level_gpa_id','=',level_gpa_id), ('state','=','registered'), ('repeat','not in',['E'])])
        enrollments = enr_obj.browse(cr, uid, ids)
        total_hrs = 0
        for enrollment in enrollments:
            if enrollment.grade.gpa:
                total_hrs += enrollment.credit
        if(total_hrs == 0):
            return '0.00'
        return '{0:.2f}'.format(total_hrs)
    
    def get_term_transfer_gpa_hours(self, cr, uid, term_id, student_id, level_gpa_id, context=None):
        tce_obj = self.pool.get('transfer.course.equivalent')
        ids = tce_obj.search(cr, uid, [('student_id','=',student_id), ('term_id','=',term_id), ('level_gpa_id','=',level_gpa_id), ('repeat','not in',['E'])])
        transfers = tce_obj.browse(cr, uid, ids)
        total_hrs = 0
        for transfer in transfers:
            if transfer.grade_id.gpa:
                total_hrs += transfer.credit
        if(total_hrs == 0):
            return '0.00'
        return '{0:.2f}'.format(total_hrs)
    
    def get_term_gpa(self, cr, uid, quality_points, gpa_hours, context=None):
        value = 0
        if('{0:.2f}'.format(float(gpa_hours)) == '0.00'):
            return gpa_hours
        else:
            value = float(quality_points)/float(gpa_hours)
        if(value == 0):
            return '0.00'
        return str(round(value, 2))
    
    def get_terms_cgpa(self, cr, uid, student_id, record_type, level_gpa_id, context=None):
        gpa_info_obj = self.pool.get('gpa.info')
        t_ids = []
        gpa_info_ids = gpa_info_obj.search(cr, uid, [('student_id','=',student_id),('level_gpa_id','=',level_gpa_id)])
        gpa_infos = gpa_info_obj.browse(cr, uid, gpa_info_ids)

        for info in gpa_infos:
            if info.term_id.id not in t_ids:
                t_ids.append(info.term_id.id)
        
        term_obj = self.pool.get('aun.registrar.term')     
        term_ids = term_obj.search(cr, uid, [('id','in',t_ids)], order='code ASC')
         
        attempted_hours = passed_hours = earned_hours = quality_points = gpa_hours = cgpa = 0
        
        if record_type == 'institution':
            for term_id in term_ids:
                ids = gpa_info_obj.search(cr, uid, [('term_id','=',term_id),('student_id','=',student_id)])
                if ids:
                    gpa_info = gpa_info_obj.browse(cr, uid, ids[0])
                    quality_points += gpa_info.quality_points
                    gpa_hours += gpa_info.gpa_hours
                    attempted_hours += gpa_info.attempted_hours
                    passed_hours += gpa_info.passed_hours
                    earned_hours += gpa_info.earned_hours   
                    cgpa = gpa_info_obj.get_term_gpa(cr, uid, quality_points, gpa_hours)
                    gpa_info_obj.write(cr, SUPERUSER_ID, ids[0],{'c_attempted_hours': attempted_hours,
                                                                 'c_passed_hours': passed_hours,
                                                                 'c_earned_hours': earned_hours,
                                                                 'c_quality_points': quality_points,
                                                                 'c_gpa_hours': gpa_hours,
                                                                 'cgpa': cgpa
                                                                 }, context=context)
        else:
            for term_id in term_ids:
                ids = gpa_info_obj.search(cr, uid, [('term_id','=',term_id), ('student_id','=',student_id)])
                if ids:
                    gpa_info = gpa_info_obj.browse(cr, uid, ids[0])
                    quality_points += gpa_info.t_quality_points
                    gpa_hours += gpa_info.t_gpa_hours
                    attempted_hours += gpa_info.t_attempted_hours
                    passed_hours += gpa_info.t_passed_hours
                    earned_hours += gpa_info.t_earned_hours
                    cgpa = gpa_info_obj.get_term_gpa(cr, uid, quality_points, gpa_hours)
                    gpa_info_obj.write(cr, SUPERUSER_ID, ids[0],{'tc_attempted_hours': attempted_hours,
                                                                 'tc_passed_hours': passed_hours,
                                                                 'tc_earned_hours': earned_hours,
                                                                 'tc_quality_points': quality_points,
                                                                 'tc_gpa_hours': gpa_hours,
                                                                 'tcgpa': cgpa
                                                                 }, context=context)
                    
        lg_obj = self.pool.get('level.gpa')
        student_obj = self.pool.get('res.partner')
        level_gpa_id = lg_obj.search(cr, SUPERUSER_ID, [('student_id','=',student_id),('current','=',True)])
        if level_gpa_id:
            level_gpa = lg_obj.browse(cr, SUPERUSER_ID, level_gpa_id[0])
            total_credits = level_gpa.total_credits
            cgpa = level_gpa.cgpa
            o_cgpa = level_gpa.o_cgpa
            vals = {}
            if level_gpa.student_id.cgpa != o_cgpa:
                vals['cgpa'] = o_cgpa
            if level_gpa.student_id.total_credits != total_credits:
                vals['total_credits'] = total_credits
            student_obj.write(cr, SUPERUSER_ID, [student_id], vals, context=context)

        return True
    
    def repair_gpa_info(self, cr, uid, ids, context=None):
        gpa_info = self.browse(cr, uid, ids)[0]
        enr_obj = self.pool.get('aun.registrar.enrollment')
        enr_ids = enr_obj.search(cr, uid, [('student_id','=',gpa_info.student_id.id),('term_id','=',gpa_info.term_id.id),('level_gpa_id','=',gpa_info.level_gpa_id.id),('lab','=',False)])
        for enr_id in enr_ids:
            enr_obj._update_gpa_info(cr, uid, enr_id)
        return True

    def _get_info(self, cr, uid, ids, name, arg, context=None):
        res = {}
        finalgrade_obj = self.pool.get('aun.student.finalgrades')
        tce_obj = self.pool.get('transfer.course.equivalent')
        honors_obj = self.pool.get('registrar.honors')
        for info in self.browse(cr, SUPERUSER_ID, ids, context=context):
            res[info.id] = {}
            finalgrade_ids = finalgrade_obj.search(cr, SUPERUSER_ID, [('term_id','=',info.term_id.id),('student_id','=',info.student_id.id)])
            honors_id = honors_obj.search(cr, SUPERUSER_ID, [('level_id','=',info.student_id.level_id.id),('gpa_from','<=',info.gpa),('gpa_to','>=',info.gpa)])
            transfer_course_ids = tce_obj.search(cr, SUPERUSER_ID, [('term_id','=',info.term_id.id),('student_id','=',info.student_id.id)])
            transfer_courses = tce_obj.browse(cr, SUPERUSER_ID, transfer_course_ids)
            institution_ids = list(set([tc.transfer_course_id.transfer_info_id.institution_id.id for tc in transfer_courses]))
            res[info.id]['finalgrade_ids'] = [(6, 0, finalgrade_ids)] if finalgrade_ids else False
            res[info.id]['transfer_course_ids'] = [(6, 0, transfer_course_ids)] if transfer_course_ids else False
            res[info.id]['institution_ids'] = [(6, 0, institution_ids)] if institution_ids else False
            res[info.id]['honors_id'] = honors_id[0] if honors_id else False
            res[info.id]['institution'] = True if finalgrade_obj.search(cr, SUPERUSER_ID, [('term_id','=',info.term_id.id),('student_id','=',info.student_id.id)]) else False
            res[info.id]['transfer'] = True if tce_obj.search(cr, SUPERUSER_ID, [('term_id','=',info.term_id.id),('student_id','=',info.student_id.id)]) else False
            student_infos = self.search(cr, uid, [('student_id','=',info.student_id.id),('level_gpa_id','=',info.level_gpa_id.id)])
            latest_info_id = False
            for s_info in self.browse(cr, uid, student_infos):
                if finalgrade_obj.search(cr, uid, [('student_id','=',s_info.student_id.id),('term_id','=',s_info.term_id.id)]):
                    latest_info_id = s_info.id
                    break
            res[info.id]['latest_info'] = True if latest_info_id and latest_info_id == info.id else False
            res[info.id]['o_attempted_hours'] = info.c_attempted_hours + info.tc_attempted_hours
            res[info.id]['o_passed_hours'] = info.c_passed_hours + info.tc_passed_hours
            res[info.id]['o_earned_hours'] = info.c_earned_hours + info.tc_earned_hours
            res[info.id]['o_quality_points'] = info.c_quality_points + info.tc_quality_points
            res[info.id]['o_gpa_hours'] = info.c_gpa_hours + info.tc_gpa_hours
            res[info.id]['o_cgpa'] = float(self.get_term_gpa(cr, uid, info.c_quality_points + info.tc_quality_points, info.c_gpa_hours + info.tc_gpa_hours))
        return res
      
    _columns = {
        'image_medium': fields.related('student_id', 'image_medium', type='binary', readonly=True, string='Image', store=False),
        'term_id': fields.many2one('aun.registrar.term', 'Term', ondelete="cascade", select=False, required=True, readonly=True),
        'student_id': fields.many2one('res.partner', 'Student ID', domain=[('student','=',True)], ondelete="cascade", select=False, required=True, readonly=True),
        'fname': fields.related('student_id', 'fname', type='char', string="First Name", store=False),
        'lname': fields.related('student_id', 'lname', type='char', string="Last Name", store=False),
        'level_gpa_id': fields.many2one('level.gpa', 'Level GPA', readonly=True, required=True),
        'finalgrade_ids': fields.function(_get_info, string='Institution Credit', type='many2many', method=True, multi='gpa', store=False, relation='aun.student.finalgrades'),
        'institution_ids': fields.function(_get_info, string='Transfer Institution(s)', type='many2many', method=True, multi='gpa', store=False, relation='transfer.institution'),
        'transfer_course_ids': fields.function(_get_info, string='Transfer Credit', type='many2many', method=True, multi='gpa', store=False, relation='transfer.course.equivalent'),
        'honors_id': fields.function(_get_info, string='Honors', type='many2one', select=False, method=True, multi='gpa', store=True, relation='registrar.honors'),
        'program_ids': fields.many2many('registrar.program', 'rel_gpa_info_program', 'gpa_info_id', 'program_id', 'Program(s)', readonly=True),
        'school_ids': fields.many2many('aun.registrar.school', 'rel_gpa_info_school', 'gpa_info_id', 'school_id', 'School(s)', readonly=True),
        'major_ids': fields.many2many('aun.registrar.major', 'rel_gpa_info_major', 'gpa_info_id', 'major_id', 'Major(s)', readonly=True),
        'minor_ids': fields.many2many('aun.registrar.major', 'rel_gpa_info_minor', 'gpa_info_id', 'minor_id', 'Minor(s)', readonly=True),
        'conc_ids': fields.many2many('aun.registrar.major', 'rel_gpa_info_conc', 'gpa_info_id', 'conc_id', 'Concentration(s)', readonly=True),
        'level_id': fields.related('level_gpa_id', 'level_id', type='many2one', relation='aun.registrar.level', string='Level', store=True, readonly=True),
        'attempted_hours': fields.float('Attempted Hours', digits=(3,2), readonly=True),
        'quality_points': fields.float('Quality Points', digits=(3,2), readonly=True),
        'passed_hours': fields.float('Passed Hours', digits=(3,2), readonly=True),
        'earned_hours': fields.float('Earned Hours', digits=(3,2), readonly=True),
        'gpa_hours': fields.float('GPA Hours', digits=(3,2), readonly=True),
        'gpa': fields.float('GPA', digits=(3,2), readonly=True),
        't_attempted_hours': fields.float('Attempted Hours', digits=(3,2), readonly=True),
        't_quality_points': fields.float('Quality Points', digits=(3,2), readonly=True),
        't_passed_hours': fields.float('Transfer Passed Hours', digits=(3,2), readonly=True),
        't_earned_hours': fields.float('Earned Hours', digits=(3,2), readonly=True),
        't_gpa_hours': fields.float('GPA Hours', digits=(3,2), readonly=True),
        't_gpa': fields.float('GPA', digits=(3,2), readonly=True), 
        'c_attempted_hours': fields.float('Attempted Hours', digits=(3,2), readonly=True),
        'c_passed_hours': fields.float('Passed Hours', digits=(3,2), readonly=True),
        'c_earned_hours': fields.float('Earned Hours', digits=(3,2), readonly=True),
        'c_quality_points': fields.float('Quality Points', digits=(3,2), readonly=True),
        'c_gpa_hours': fields.float('GPA Hours', digits=(3,2), readonly=True),
        'cgpa': fields.float('CGPA', digits=(3,2), readonly=True),
        'tc_attempted_hours': fields.float('Attempted Hours', digits=(3,2), readonly=True),
        'tc_passed_hours': fields.float('Passed Hours', digits=(3,2), readonly=True),
        'tc_earned_hours': fields.float('Earned Hours', digits=(3,2), readonly=True),
        'tc_quality_points': fields.float('Quality Points', digits=(3,2), readonly=True),
        'tc_gpa_hours': fields.float('GPA Hours', digits=(3,2), readonly=True),
        'tcgpa': fields.float('CGPA', digits=(3,2), readonly=True),
        'o_attempted_hours': fields.function(_get_info, type='float', method=True, string='Attempted Hours', multi='gpa', store=False),
        'o_passed_hours': fields.function(_get_info, type='float', method=True, string='Passed Hours', multi='gpa', store=False),
        'o_earned_hours': fields.function(_get_info, type='float', method=True, string='Earned Hours', multi='gpa', store=False),
        'o_quality_points': fields.function(_get_info, type='float', method=True, string='Quality Points', multi='gpa', store=False),
        'o_gpa_hours': fields.function(_get_info, type='float', method=True, string='GPA Hours', multi='gpa', store=False),
        'o_cgpa': fields.function(_get_info, type='float', method=True, string='CGPA', multi='gpa', store=False),
        'standing_id': fields.many2one('aun.registrar.standing', 'Academic Standing', select=False, readonly=True),
        'transfer': fields.function(_get_info, type='boolean', method=True, multi='gpa', string='Transfer', store=False),
        'institution': fields.function(_get_info, type='boolean', method=True, multi='gpa', string='Institution', store=False),
        'latest_info': fields.function(_get_info, type='boolean', method=True, multi='gpa', string='Latest Info', store=False),
        'graduated': fields.related('student_id', 'graduated', type='boolean', string="Graduated", store=False)
    }
gpa_info()


class res_partner(osv.osv):
    _inherit = 'res.partner'
    
#     def _get_current_credit_hours(self, cr, uid, ids, enrolled_hours, arg, context=None):
#        res = {}
#        student = self.browse(cr, uid, ids)[0]
#        cr.execute("""
#        SELECT aun_registrar_course.credit FROM 
#        res_partner,aun_registrar_enrollment,
#        aun_registrar_term,aun_registrar_section,
#        aun_registrar_course 
#        WHERE
#        res_partner.id = aun_registrar_enrollment.student_id AND 
#        aun_registrar_enrollment.section_id = aun_registrar_section.id AND 
#        aun_registrar_section.term_id = aun_registrar_term.id AND 
#        aun_registrar_section.course_id = aun_registrar_course.id AND 
#        aun_registrar_term.state = 'active' AND
#        aun_registrar_enrollment.state = 'registered' AND
#        res_partner.d =(%s)""" % student.id)
#        sql_res = cr.fetchall()
#        a = 0
#        for i in sql_res:
#            a = a + int(i[0])
#        res[student.id] = a
#        return res
           
    def _get_status(self, cr, uid, ids, status_id, arg, context=None):
        res={}
        status_obj = self.pool.get('registrar.status')
        honors_obj = self.pool.get('institutional.honors')
        lg_obj = self.pool.get('level.gpa')
        for student in self.browse(cr, SUPERUSER_ID, ids):
            res[student.id] = {}
            total_credits = 0.0
            cgpa = 0.0
            level_gpa_id = lg_obj.search(cr, SUPERUSER_ID, [('student_id','=',student.id),('current','=',True)])
            if level_gpa_id:
                level_gpa = lg_obj.browse(cr, SUPERUSER_ID, level_gpa_id[0])
                total_credits = level_gpa.total_credits
                cgpa = level_gpa.cgpa
            status_id = status_obj.search(cr, SUPERUSER_ID, [('level_id','=',student.level_id.id),('range_start','<=',total_credits),('range_end','>=',total_credits)])            
            honors_id = honors_obj.search(cr, SUPERUSER_ID, [('gpa_from','<=',cgpa),('gpa_to','>=',cgpa)])
            res[student.id]['status_id'] = status_id[0] if status_id else False
            res[student.id]['honors_id'] = honors_id[0] if honors_id else False
            
        return res
   
    def _get_schools_and_programs(self, cr, uid, ids, name, arg, context=None):
        res = {}
        uid = SUPERUSER_ID
        mc_obj = self.pool.get('aun.registrar.major.course')
        enr_obj = self.pool.get('aun.registrar.enrollment')
        for student in self.browse(cr, SUPERUSER_ID, ids, context=None):
            res[student.id] = {}
            major_ids = [major.id for major in student.major_ids]
            major_course_ids = mc_obj.search(cr, uid, [('catalogue_id','=',student.catalogue_id.id),('major_id','in',major_ids),('level_id','=',student.level_id.id)], context=None)
            major_courses = mc_obj.browse(cr, uid, major_course_ids, context=None)
            school_ids = list(set([mc.school_id.id for mc in major_courses]))
            program_ids = list(set([mc.program_id.id for mc in major_courses]))
            res[student.id]['school_ids'] = [(6, 0, school_ids)]
            res[student.id]['program_ids'] = [(6, 0, program_ids)]
            stud_school_ids = [s.id for s in student.schools]
            if list(set(stud_school_ids) - set(school_ids)) or list(set(school_ids) - set(stud_school_ids)):
                self.write(cr, uid, [student.id], {'schools': [(6, 0, school_ids)]})
                enr_ids = enr_obj.search(cr, uid, [('student_id','=',student.id),('state','=','registered')])
                super(aun_registrar_enrollment, enr_obj).write(cr, uid, enr_ids, {'school_ids': [(6, 0, school_ids)]}, context=context)
        return res

    def get_holds(self, cr, uid, student_id, context=None):
        holds = {}
        holds['registration'] = False
        holds['grades'] = False
        holds['enr_ver'] = False
        holds['graduation'] = False
        holds['transcript'] = False
  
        if not student_id:
            return holds
        student = self.browse(cr, uid, student_id, context=context)
        for hold in student.holds:
            if hold.is_active:
                if not holds['registration']:
                    holds['registration'] = hold.hold_id.registration
                if not holds['grades']:
                    holds['grades'] = hold.hold_id.grades
                if not holds['enr_ver']:
                    holds['enr_ver'] = hold.hold_id.enr_ver
                if not holds['graduation']:
                    holds['graduation'] = hold.hold_id.graduation
                if not holds['transcript']:
                    holds['transcript'] = hold.hold_id.transcript
        return holds

    def create(self, cr, uid, vals, context=None):
        res = super(res_partner, self).create(cr, uid, vals, context)
        if 'student' in vals and vals['student']:
            lg_obj = self.pool.get('level.gpa')
            other_lg_ids = lg_obj.search(cr, SUPERUSER_ID, {'student_id': res, 'current': True})
            if other_lg_ids:
                lg_obj.write(cr, SUPERUSER_ID, other_lg_ids, {'current': False})
            lg_obj.create(cr, SUPERUSER_ID, {'student_id': res,
                                             'level_id': vals['level_id'],
                                             'admission_date': vals['admission_date'],
                                             'term_admitted': vals['term_admitted'],
                                             'student_state_id': vals['student_state_id'],
                                             'major_ids': [(6, 0, vals['major_ids'][0][2])],
                                             'minor_ids': [(6, 0, vals['minor_ids'][0][2])],
                                             'conc_ids': [(6, 0, vals['concentration_ids'][0][2])],
                                             'current': True})

#             term_admitted = self.pool.get('aun.registrar.term').browse(cr, uid, vals['term_admitted'])
#             term_term = term_admitted.name
#             term_year = term_admitted.year
#             catalogue_obj = self.pool.get('aun.registrar.catalogue')
#             catalogue_id = catalogue_obj.search(cr,uid, [('start_year','=', str(int(term_year) + int(term_term.year_adjustment)))])
#             if not catalogue_id:
#                 raise osv.except_osv(_('Contact the Registrar!'), _('There is no matching catalogue for this applicant\'s enrollment year!'))
#             vals['catalogue_id'] = catalogue_id[0]
#              
#             #check if major is in admission catalogue
#             if vals['major_ids']:
#                 mc_obj = self.pool.get('aun.registrar.major.course')
#                 major_ids = mc_obj.search(cr, uid, [('major_id','in',vals['major_ids'][0][2]),('level_id','=',vals['level_id']),('catalogue_id','=',catalogue_id[0])])
#                 if not major_ids:
#                     major = self.pool.get('aun.registrar.major').browse(cr, uid, vals['major_ids'][0][2][0]).name
#                     raise osv.except_osv(_('Major Unavailable!'), _(major + ' is not in the admission catalogue for this student! Please select another major!'))
        return res

    def write(self, cr, uid, ids, vals, context=None):
        lg_obj = self.pool.get('level.gpa')
        res = {}
        for partner in self.browse(cr, uid, ids):
            if partner.student or ('student' in vals and vals['student']):
                if 'admission_date' in vals or 'level_id' in vals or 'student_state_id' in vals or 'major_ids' in vals or 'minor_ids' in vals or 'concentration_ids' in vals or 'catalogue_id' in vals:
                    res['student_id'] = partner.id
                    res['catalogue_id'] = vals['catalogue_id'] if 'catalogue_id' in vals else partner.catalogue_id.id
                    res['admission_date'] = vals['admission_date'] if 'admission_date' in vals else partner.admission_date
                    res['term_admitted'] = vals['term_admitted'] if 'term_admitted' in vals else partner.term_admitted.id
                    res['level_id'] = vals['level_id'] if 'level_id' in vals else partner.level_id.id
                    res['student_state_id'] = vals['student_state_id'] if 'student_state_id' in vals else partner.student_state_id.id
                    res['graduation_class'] = vals['graduation_class'] if 'graduation_class' in vals else partner.graduation_class
                    res['date_of_state'] = vals['date_of_state'] if 'date_of_state' in vals else partner.date_of_state
                    res['major_ids'] = [(6, 0, vals['major_ids'][0][2])] if 'major_ids' in vals else [(6, 0, [major.id for major in partner.major_ids])]
                    res['minor_ids'] = [(6, 0, vals['minor_ids'][0][2])] if 'minor_ids' in vals and vals['minor_ids'] else [(6, 0, [minor.id for minor in partner.minor_ids])]
                    res['conc_ids'] = [(6, 0, vals['concentration_ids'][0][2])] if 'concentration_ids' in vals and vals['concentration_ids'] else [(6, 0, [conc.id for conc in partner.concentration_ids])]
                    res['current'] = True
                    prev_level_gpa_id = lg_obj.search(cr, SUPERUSER_ID, [('student_id','=',partner.id),('current','=',True)])
                    level_gpa_id = lg_obj.search(cr, SUPERUSER_ID, [('student_id','=',partner.id),('level_id','=',res['level_id']),('admission_date','=',res['admission_date'])])
                    if level_gpa_id != prev_level_gpa_id:
                        enr_ids = self.pool.get('aun.registrar.enrollment').search(cr, SUPERUSER_ID, [('student_id','=',partner.id),('level_gpa_id','in',prev_level_gpa_id)])
                        if not enr_ids:
                            lg_obj.unlink(cr, SUPERUSER_ID, prev_level_gpa_id)           
                    if level_gpa_id:
                        other_lg_ids = lg_obj.search(cr, SUPERUSER_ID, [('id','not in',level_gpa_id),('student_id','=',partner.id),('current','=',True)])
                        lg_obj.write(cr, SUPERUSER_ID, other_lg_ids, {'current': False})
                        lg_obj.write(cr, SUPERUSER_ID, level_gpa_id, res)
                    else:
                        other_lg_ids = lg_obj.search(cr, SUPERUSER_ID, [('student_id','=',partner.id),('current','=',True)])
                        lg_obj.write(cr, SUPERUSER_ID, other_lg_ids, {'current': False})
                        lg_obj.create(cr, SUPERUSER_ID, res)

        return super(res_partner, self).write(cr, uid, ids, vals, context=context)

    def create_user(self, cr, uid, ids, context=None):
        user_obj = self.pool.get('res.users')
        student = self.browse(cr, uid, ids)[0]
        if (student.user_ids == []):
                group1 = self.pool.get('ir.model.data').get_object(cr, uid, 'academics', 'group_registrar_student')
                group2 = self.pool.get('ir.model.data').get_object(cr, uid, 'portal', 'group_portal')
                user = user_obj.create(cr,uid,{
                                                     'name': student.name,
                                                     'login': student.name,
                                                     'email': student.email,
                                                     'partner_id': student.id,
                                                     'groups_id': [(6, 0, [group1.id,group2.id])],
                                                     'tz': "Africa/Lagos"
                                                         })
                user_obj.write(cr,uid,user,{'login':student.name},context=context)
                ctx = dict(create_user=True)
                user_obj.action_reset_password(cr, SUPERUSER_ID, [user], context=ctx)
        else:
            raise osv.except_osv(_('User already exists!'), _('Click reset password button'))
        return True
    
    def reset_password(self, cr, uid, ids, context=None):
        user_obj = self.pool.get('res.users')
        student = self.browse(cr, uid, ids)[0]
        if (student.user_ids == []):
            raise osv.except_osv(_('No User!'), _('This student does not have a user account, click create user button'))
        else:
            user_ids = [user.id for user in student.user_ids]
            user_obj.action_reset_password(cr, uid, user_ids)
        return True
    
    def create_users(self, cr, uid, ids, context=None):
        idss = self.search(cr, uid, [('student','=','True')])
        students = self.browse(cr, uid, idss)
        for student in students:
            self.create_user(cr, uid, [student.id], context)
        return True
    
    def on_change_state(self, cr, uid, ids, student_state_id, context=None):
        res = {}
        student = self.browse(cr, uid, ids)[0]   
        state = self.pool.get('student.state').browse(cr, uid, student_state_id)
        if state.graduated:
            graduation_hold = self.get_holds(cr, uid, ids[0])['graduation']
            if graduation_hold:
                hold_names = ', '.join(list(set([hold.hold_id.name for hold in student.holds if hold.hold_id.graduation])))
                res['value'] = {'student_state_id': student.student_state_id.id}
                res['warning'] = {'title': _('Hold Restriction!'), 'message': _('The following hold(s) are on this student\'s record: ' + hold_names)}
                return res
        return {'value': {'is_active': state.is_active, 'graduated': state.graduated, 'graduation_class': False, 'date_of_state': False}}    

    def on_change_level(self, cr, uid, ids, context=None):
        return {'value': {'major_ids': False, 'minor_ids': False, 'concentration_ids': False}}

    def on_change_majors(self, cr, uid, ids, majors, minors, concentrations, level_id, catalogue_id, catalogue, context=None):
        val = {}
        warning = {}
        student = self.browse(cr, uid, ids)[0]
        major_ids = majors[0][2]
        minor_ids = minors[0][2]
        mc_obj = self.pool.get('aun.registrar.major.course')
        if catalogue and catalogue_id:
            catalogue_obj = self.pool.get('aun.registrar.catalogue')
            catalogue = catalogue_obj.browse(cr, uid, catalogue_id)
            cat_major_courses = catalogue.major_course_ids
            cat_major_ids = []
            for mc in cat_major_courses:
                cat_major_ids.append(mc.major_id.id)
            major_ids = [m for m in major_ids if m in cat_major_ids]
            minor_ids = [m for m in minor_ids if m in cat_major_ids]
            val['major_ids'] = [(6, 0, major_ids)]
            if student.student:
                term_term = student.term_admitted.name
                term_year = student.term_admitted.year
                admission_catalogue_id = catalogue_obj.search(cr, SUPERUSER_ID, [('start_year','<=', str(int(term_year) + int(term_term.year_adjustment))),('end_year','>',str(int(term_year) + int(term_term.year_adjustment)))])
                if admission_catalogue_id:
                    admission_catalogue = catalogue_obj.browse(cr, uid, admission_catalogue_id)[0]
                    if catalogue.code < admission_catalogue.code:
                        warning = {'title': _('Invalid Catalog'), 'message': _('This catalog is older than the student\'s admission catalog: ' + admission_catalogue.name_get()[0][1])}
                        val.update({'catalogue_id': False})
                else:
                    warning = {'title': _('Invalid Catalog'), 'message': _('There is no catalog for the student\'s enrollment year.')}
                    val.update({'catalogue_id': False})

        concs = self.pool.get('aun.registrar.major').browse(cr, uid, concentrations[0][2])
        conc_ids = []
        for conc in concs:
            for concentration in conc.conc_ids:
                if concentration.major_course_id.major_id.id in major_ids and conc.id not in conc_ids:
                    conc_ids.append(conc.id)

        minor_ids = [m for m in minor_ids if m not in major_ids]
        major_course_ids = mc_obj.search(cr, uid, [('catalogue_id','=',catalogue_id),('major_id','in',major_ids),('level_id','=',level_id)], context=None)
        major_courses = mc_obj.browse(cr, uid, major_course_ids, context=None)
        school_ids = list(set([mc.school_id.id for mc in major_courses]))
        program_ids = list(set([mc.program_id.id for mc in major_courses]))
        val.update({'minor_ids': [(6, 0, minor_ids)], 'concentration_ids': [(6, 0, conc_ids)], 'program_ids': [(6, 0, program_ids)], 'school_ids': [(6, 0, school_ids)]})
        return {'value': val, 'warning': warning}

    def _populate_class(self, cr, uid, context=None):
        current_year = date.today().year
        return [(str(i), str(i)) for i in range(2009, current_year+3)]
  
    _columns = {
        'applicant': fields.boolean('Applicant', track_visibility="onchange"),
        'student': fields.boolean('Student', track_visibility="onchange"),
        'admission_date': fields.date('Date Admitted', readonly=True, select=True),
        'app_id': fields.many2one('aun.applicant', 'Application', ondelete="cascade", track_visibility="onchange"),
        'fname': fields.char('First Name', size=64, track_visibility="onchange"),
        'mname': fields.char('Middle Name', size=64, track_visibility="onchange"),
        'lname': fields.char('Surname', size=64, track_visibility="onchange"),
        'dob': fields.date('Date of Birth', track_visibility="onchange"),
        'personal_email': fields.char('Personal Email', size=64, track_visibility="onchange"),
        'sex': fields.selection([('M','Male'),('F','Female')],'Gender', track_visibility="onchange"),
        'city_of_birth': fields.char('City Of Birth', size=64, track_visibility="onchange"),
        'state_of_origin': fields.char('State of Origin', size=64, track_visibility="onchange"),
        'sem_id': fields.many2one('aun.registrar.term', 'Application Term', track_visibility="onchange"),
        'major_ids': fields.many2many('aun.registrar.major', 'rel_major_student', 'student_id', 'major_id', 'Major(s)', track_visibility="onchange", groups="academics.group_registrar_ass_registrar,academics.group_registrar_student,academics.group_academic_advisor,academics.group_registrar_faculty,academics.group_registrar_dean"),
        'minor_ids': fields.many2many('aun.registrar.major', 'rel_minor_student', 'student_id', 'major_id', 'Minor(s)', track_visibility="onchange", groups="academics.group_registrar_ass_registrar,academics.group_registrar_student,academics.group_academic_advisor,academics.group_registrar_faculty,academics.group_registrar_dean"),
        'concentration_ids': fields.many2many('aun.registrar.major', 'rel_concentration_student', 'student_id', 'concentration_id', 'Concentration(s)', track_visibility="onchange", groups="academics.group_registrar_ass_registrar,academics.group_registrar_student,academics.group_academic_advisor,academics.group_registrar_faculty,academics.group_registrar_dean"),    
        'school_ids':fields.function(_get_schools_and_programs, string='Fnct School(s)', type='many2many', method=True, multi='program_info', relation='aun.registrar.school', store=False, track_visibility="onchange", groups="academics.group_registrar_ass_registrar,academics.group_registrar_student,academics.group_academic_advisor,academics.group_registrar_faculty,academics.group_registrar_dean"),
        'program_ids': fields.function(_get_schools_and_programs, string='Program(s)', type='many2many', method=True, multi='program_info', relation='registrar.program', store=False, track_visibility="onchange", groups="academics.group_registrar_ass_registrar,academics.group_registrar_student,academics.group_academic_advisor,academics.group_registrar_faculty,academics.group_registrar_dean"),
        'guardians': fields.one2many('res.guardian','partner_id','Guardians', track_visibility="onchange"),        
        'enrollment_ids': fields.one2many('aun.registrar.enrollment', 'student_id', 'Enrollments', domain=[('lab','=',False)]),
        'status_id': fields.function(_get_status, string='Status', type='many2one', method=True, store=True, multi='gpa', relation='registrar.status'),
        'honors_id': fields.function(_get_status, string='Honors', type='many2one', method=True, store=True, multi='gpa', relation='institutional.honors'),
        'cgpa': fields.float('CGPA', digits=(3,2)),
        'total_credits': fields.float('Total Credits', digits=(3,2)),
        'schools': fields.many2many('aun.registrar.school', 'rel_student_shool', 'student_id', 'school_id', 'School(s)'),
        'student_state_id': fields.many2one('student.state', 'Student Status', track_visibility="onchange"),
        'is_active': fields.boolean('Active'),
        'graduated': fields.boolean('Graduated'),
        'date_of_state': fields.date('Date', track_visibility="onchange"),
        'graduation_class': fields.selection(_populate_class, 'Graduation Class', track_visibility="onchange"),
        'term_admitted': fields.many2one('aun.registrar.term', 'Term Admitted', readonly=True, track_visibility="onchange"),
        'standing_id': fields.many2one('aun.registrar.standing', 'Current Standing', readonly=True, track_visibility="onchange"),
        'catalogue_id': fields.many2one('aun.registrar.catalogue', 'Catalogue', track_visibility="onchange"),
        'level_id': fields.many2one('aun.registrar.level', 'Level', track_visibility="onchange"),
        'level_gpa_ids': fields.one2many('level.gpa', 'student_id', 'Level GPA', groups="academics.group_registrar_ass_registrar,academics.group_academic_advisor,academics.group_registrar_dean"),
        'holds': fields.one2many('aun.registrar.hold.assignment', 'student_id', 'Holds'),
		'clearance_ids': fields.one2many('term.clearance', 'student_id', 'Clearance', readonly=True, groups="academics.group_registrar_ass_registrar,academics.group_registrar_student,academics.group_bursar,academics.group_registrar_dean"),
		'director_id': fields.one2many('housing.res.director','name', 'RD'),
        'payment_ids': fields.one2many('account.voucher','partner_id', 'Payments')
        }

    _defaults = {
        'total_credits': 0.0,
        'cgpa': 0.0
        }
    
    def _check_student_id(self, cr, uid, ids, context=None):
        student = self.browse(cr, uid, ids, context=context)[0]
        student_ids = self.search(cr, uid, [('id','not in',[student.id]),('student','=',True),('name','=',student.name)])      
        if student_ids:
            raise osv.except_osv(_('Check Student ID!'), _('Student ID must be unique.' + student.name))
        return True
    
    _constraints =[
        (_check_student_id, 'Student ID must be unique.', ['Student ID'])
    ]

res_partner()

class res_guardian(osv.osv):
    _name = 'res.guardian'
    _description = 'Guardians'
    _inherit = ["mail.thread"]
    _columns = {
            'name': fields.selection([('aunt','Aunt'),('brother','Brother'),('child','Child'),('father','Father'),('friend','Friend'),('grandparent','Grandparent'),('guardian','Guardian'),('husband','Husband'),('mother','Mother'),('other','Other'),('sister','Sister'),('uncle','Uncle'),('wife','Wife')],'Relationship Type' ),
            'prefix': fields.selection([('mr','Mr'),('mrs','Mrs'),('dr','Dr'),('chief','Chief'),('alhaji','Alhaji'),('sir','Sir')],'Prefix' ),
            'fname': fields.char('First Name', size=32 ),
            'mname': fields.char('Middle Name', size=32),
            'lname': fields.char('Surname', size=32 ),
            'phone': fields.char('Phone Number', size=16 ),
            'email': fields.char('Email', size=64),
            'employer': fields.char('Employer', size=64),
            'add': fields.text('Address'),
            'city': fields.char('City', size=64),
            'state': fields.many2one('res.country.state', 'State'),
            'country': fields.many2one('res.country', 'Country'),
            'priority': fields.selection([('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9')], 'Priority'),
            'deceased': fields.boolean('Deceased'),
            'partner_id': fields.many2one('res.partner', 'Student'),
            }
    _defaults={}
    
res_guardian()

class aun_registrar_section(osv.osv):
    _name = "aun.registrar.section"
    _description = "Section"
    _inherit = ["mail.thread"]
    _order = "term_id DESC, name DESC"
    
    def _has_enrollment(self, cr, uid, ids, field_name, arg=None, context=None):
        res={}
        for section in self.browse(cr, uid, ids):
            if section.enrollment_ids:
                res[section.id] = True
            else:
                res[section.id] = False
        return res

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, ['|',('name','=',name),('course_id','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, ['|',('name',operator,name),('course_id',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)
    
    def create(self, cr, uid, vals, context=None):
        course_sections = self.search(cr,uid, [('course_id','=', vals['course_id']),('term_id','=',vals['term_id'])])
        term_sections = self.search(cr,uid, [('term_id','=',vals['term_id'])])
        term = self.pool.get('aun.registrar.term').browse(cr, uid, vals['term_id'])
        section_count = len(course_sections)
        section_count += 1
        if term_sections:
            sections = map(int, [s.name for s in self.browse(cr, uid, term_sections, context=context)])
            section_number = max(sections) + 1
        else:
            section_number = str(term.code) + '1'
        vals['section_no'] = section_count
        vals['name'] = str(section_number)
        vals['state'] = 'active'
        res = super(aun_registrar_section, self).create(cr, uid, vals, context)
  
        #add registrar to section followers
        group = self.pool.get('ir.model.data').get_object(cr, uid, 'academics', 'group_registrar_ass_registrar')
        group = cr.execute("select uid from res_groups_users_rel WHERE gid=(%s)" %group.id)
        s = cr.fetchall()
        group = []
        for a in s:
            group.append(a[0])
  
        self.message_subscribe_users(cr, SUPERUSER_ID, [res], group, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        super(aun_registrar_section, self).write(cr, uid, ids, vals, context=context)
        section = self.browse(cr, uid, ids, context=context)[0]
        if context and not context.get('subscribe'):
            self._check_primary_faculty_and_percentages(cr, uid, ids)
            self._check_labs(cr, uid, ids, section.no_of_labs)
            sec_faculty_ids = []
            no_user_id = []
            for fs in section.faculty:
                if fs.faculty_id.user_id:
                    sec_faculty_ids.append(fs.faculty_id.id)
                else:
                    no_user_id.append(fs.faculty_id.name)
            for lab in section.labs:
                for fs in lab.faculty:
                    if not fs.faculty_id.user_id:
                        no_user_id.append(fs.faculty_id.name)               
            if no_user_id:
                raise osv.except_osv(_('Contact Human Resources!'), _(', '.join(list(set(no_user_id))) + [' does not have a user account.', ' do not have user accounts.'][len(no_user_id) > 1]))
             
            primary_faculty_user_id = [fs.faculty_id.user_id.id for fs in section.faculty if fs.primary]
            if primary_faculty_user_id:
                if section.primary_faculty_user_id != primary_faculty_user_id[0]:
                    super(aun_registrar_section, self).write(cr, uid, ids, {'primary_faculty_user_id': primary_faculty_user_id[0]})
             
            #update enrollment faculty_emp_ids(faculty search field) on change of section faculty or lab faculty
            enr_obj = self.pool.get('aun.registrar.enrollment')
            if 'faculty' in vals:
                section_enr_ids = enr_obj.search(cr, uid, [('lab','=',False),('section_id','=',section.id)])
                if section_enr_ids:
                    section_enr = enr_obj.browse(cr, uid, section_enr_ids[0])
                    enr_faculty_ids = [f.id for f in section_enr.faculty_emp_ids]
                    if list(set(sec_faculty_ids)-set(enr_faculty_ids)) or list(set(enr_faculty_ids)-set(sec_faculty_ids)):
                        super(aun_registrar_enrollment, enr_obj).write(cr, uid, section_enr_ids, {'faculty_emp_ids': [(6, 0, sec_faculty_ids)]})
             
        return True
    
    #change the state of the section's labs to cancelled and set the section state as cancelled
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        enr_obj = self.pool.get('aun.registrar.enrollment')
        lab_obj = self.pool.get('section.lab')
        sections = self.browse(cr, uid, ids, context=context)
        for section in sections:
            if section.state == "cancelled": 
                continue
            for lab in section.labs:
                if lab.state == "cancelled":
                    continue
                super(section_lab, lab_obj).write(cr, uid, lab.id, {'state': 'cancelled'}, context=context)
            enr_ids = enr_obj.search(cr, uid, [('section_id','=',section.id),('state','=','registered'),('lab','=',False)])
            enr_obj.unlink(cr, uid, enr_ids, context=context)
            super(aun_registrar_section, self).write(cr, uid, section.id, {'state': 'cancelled', 'active': False}, context=context)
            
        ir_obj = self.pool.get('ir.model.data')
        et_obj = self.pool.get('email.template')
        student_template = ir_obj.get_object(cr, uid, 'academics', 'section_cancelled')
        faculty_template = ir_obj.get_object(cr, uid, 'academics', 'faculty_section_cancelled')
        assert student_template._name == 'email.template' and faculty_template._name == 'email.template'
        for record in enr_obj.browse(cr, uid, enr_ids, context) + section.faculty:
            if record._name == 'aun.registrar.enrollment':
                name = record.student_id.name
                email = record.student_id.email
            else:
                name = record.faculty_id.name
                email = record.faculty_id.work_email
            if not email:
                raise osv.except_osv(_("Cannot send email: user has no email address."), name)
            
        for record in enr_obj.browse(cr, uid, enr_ids, context) + section.faculty:
            if record._name == 'aun.registrar.enrollment':
                et_obj.send_mail(cr, uid, student_template.id, record.id, True, context=context)
            else:
                et_obj.send_mail(cr, uid, faculty_template.id, record.id, True, context=context)
        
        return True
        
    def _get_enrolled(self, cr, uid, ids, enrolled, arg, context=None):
        res = {}
        enr_obj = self.pool.get('aun.registrar.enrollment')
        for section_id in ids:
            section_enr_ids = enr_obj.search(cr, uid, [('section_id','=',section_id),('lab','=',False),('state','=','registered')])
            res[section_id] = len(section_enr_ids)
        return res
    
    def _get_enrollments(self, cr, uid, ids, context=None):
        cr.execute("""SELECT DISTINCT section_id FROM aun_registrar_enrollment 
                                    WHERE id = ANY(%s)""", (list(ids),))
        return [i[0] for i in cr.fetchall()]
    
    def on_change_term(self, cr, uid, ids, term_id, context=None):
        result = {'value': {
            'faculty': False,
            'duration_id': False,
            'location_id': False,
            }
        }           
        return result
    
    def on_change_location(self, cr, uid, ids, term_id, duration_id, location_id, max_size, context=None):
        res = {}
        if not location_id:
            return res
        if not term_id:
            raise osv.except_osv(_('No term selected!'), _('Please select a term first'))
            return res
        if not duration_id:
            return {'value': {'term_id': False}}       
        
        unavail_rooms = self.get_unavail_rooms(cr, uid, ids, duration_id, term_id, context)
        less_capacity_rooms = self.pool.get('aun.registrar.location').search(cr, uid, [('capacity','<',max_size)])
        if location_id in less_capacity_rooms:
            res['warning'] = {'title': _('Location Capacity'), 'message': _('The location selected has a smaller capacity than the class capacity')}
        if location_id in unavail_rooms:
            res['warning'] = {'title': _('Location Occupied'), 'message': _('The location selected is occupied for this class time')}
        return res

    def get_unavail_rooms(self, cr, uid, ids, duration_id, term_id, context=None):
        unavail_rooms = []
        section_obj = self.pool.get('aun.registrar.section')
        duration_obj = self.pool.get('aun.registrar.duration')
        lab_obj = self.pool.get('section.lab')
        section_ids = section_obj.search(cr, uid, [('id','not in',ids),('duration_id','!=',False),('location_id','!=',False),('term_id','=',term_id),('state','=','active')])
        lab_ids = lab_obj.search(cr, uid, [('duration_id','!=',False),('location_id','!=',False),('term_id','=',term_id),('state','=','active')])
        sections = section_obj.browse(cr, uid, section_ids)
        labs = lab_obj.browse(cr, uid, lab_ids)
        sections_and_labs = sections + labs
        duration = duration_obj.browse(cr, uid, duration_id, context=context)

        for s in sections_and_labs:
            d = duration.name
            dd = s.duration_id.name
            d_coll = collections.Counter(d[:-14])
            dd_coll = collections.Counter(dd[:-14])
            common = d_coll & dd_coll
            if common:
                t = d[-13:].replace(':','').split()
                tt = dd[-13:].replace(':','').split()
                t.remove("-")
                tt.remove("-")
                t = map(int, t)
                tt = map(int, tt)
                if (tt[0] < t[0] < tt[1]) or (tt[0] < t[1] < tt[1]) or (t[0]==tt[0] and t[1]==tt[1]):
                    unavail_rooms.append(s.location_id.id)
        return unavail_rooms
   
    def on_change_duration(self, cr, uid, ids, filter_rooms, duration_id, location_id, max_size, term_id, context=None):
        res = {}
        if not duration_id:
            return {'value': {'filter_rooms': False}}
        if not max_size:
            return {'value': {'filter_rooms': False}}

        unavail_rooms = self.get_unavail_rooms(cr, uid, ids, duration_id, term_id, context)
        less_capacity_rooms = self.pool.get('aun.registrar.location').search(cr, uid, [('capacity','<',max_size)])
        if filter_rooms:
            res['value'] = {'location_id': False}
            res['domain'] = {'location_id': [('id','not in',unavail_rooms),('capacity','>=',max_size)]}
        else:
            res['domain'] = {'location_id': [('id','not in',[])]}
            if location_id:
                if location_id in less_capacity_rooms:
                    res['warning'] = {'title': _('Location Capacity'), 'message': _('The location selected has a smaller capacity than the class capacity')}
                if location_id in unavail_rooms:
                    res['warning'] = {'title': _('Location Occupied'), 'message': _('The location selected is occupied for this class time')}
        return res

    def on_change_capacity(self, cr, uid, context=None):
        return {'value': {'filter_rooms': False, 'location_id': False}}

    def _check_time_conflict(self, cr, uid, ids, context=None):
        section = self.browse(cr, uid, ids, context=context)[0]
        if section.filter_rooms:
            conflicts = []
            for lab in section.labs:
                if not lab.duration_id:
                    continue
                d = section.duration_id.name
                dd = lab.duration_id.name
                d_coll = collections.Counter(d[:-14])
                dd_coll = collections.Counter(dd[:-14])
                common = d_coll & dd_coll
                if common:
                    t = d[-13:].replace(':','').split()
                    tt = dd[-13:].replace(':','').split()
                    t.remove("-")
                    tt.remove("-")
                    t = map(int, t)
                    tt = map(int, tt)
                    if (tt[0] < t[0] < tt[1]) or (tt[0] < t[1] < tt[1]) or (t[0]==tt[0] and t[1]==tt[1]):
                        conflicts.append(lab.name)
            if conflicts:
                raise osv.except_osv(_('Time Conflict!'), _('There seems to be a time conflict between this section and its ' + ['lab: ','labs: '][len(conflicts) > 1] + ', '.join(conflicts)))        
        return True
    
    #check should be on section_lab for percentage to work
    def _check_primary_faculty_and_percentages(self, cr, uid, ids, context=None):
        section = self.browse(cr, uid, ids, context=context)[0]
        lab_percentages = []
        lab_faculty = []
        for lab in section.labs:
            lab_faculty = lab.faculty
            for f in lab_faculty:
                lab_percentages.append(f.percentage)
                if f.primary:
                    raise osv.except_osv(_('Check Primary Faculty!'), _('A lab faculty cannot be the primary faculty for the section.'))         
        
        if section.faculty:
            primary = [f for f in section.faculty if f.primary]
            if len(primary) == 0:
                raise osv.except_osv(_('Select Primary Faculty!'), _('There is no primary faculty for this section.'))       
            if len(primary) > 1:
                raise osv.except_osv(_('Check Primary Faculty!'), _('Select one primary faculty for this section.'))
        
        #percentage check on faculty
#         if section.faculty or lab_percentages:
#             percentages = [f.percentage for f in section.faculty]
#             print percentages
#             percentages += lab_percentages
#             print percentages
#             if sum(percentages) != 100:
#                 raise osv.except_osv(_('Percentage Error!'), _('The total faculty percentage for this section must be equal to 100%'))           
        return True

    #make sure the no of labs required is not more than the labs available and the no of labs is not less than the no of mandatory labs
    def _check_labs(self, cr, uid, ids, no_of_labs, context=None):
        lab_obj = self.pool.get('section.lab')
        lab_ids = lab_obj.search(cr, uid, [('section_id','=',ids[0]),('state','=','active')])
        if no_of_labs > len(lab_ids):
            raise osv.except_osv(_('Number of Labs Required!'), _('Ensure that there are as many labs as are required for this section.'))
        mandatory_lab_ids = lab_obj.search(cr, uid, [('mandatory','=',True),('section_id','=',ids[0]),('state','=','active')]) 
        if no_of_labs < len(mandatory_lab_ids):
            raise osv.except_osv(_('Number of Labs Required!'), _('Ensure that the number of labs required is at least the number of mandatory labs.'))
        return True

    def _check_grading(self, cursor, uid, ids, name, arg, context=None):
        res={}
        for section in self.browse(cursor, uid, ids):
            res[section.id] = section.grading_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= section.grading_end
        return res
    
    def _grading_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('grading_start', '<=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('grading_end','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
        res.append(('id', 'in', res_ids))
        return res
    
    def on_change_grading_date(self, cr, uid, ids, grading_start, grading_end, context=None):    
        result = {'value': {'open_for_grading': grading_start <= datetime.now().strftime('%Y-%m-%d %H:%M:%S') <= grading_end}}
        return result

    def on_change_course(self, cr, uid, ids, course_id, context=None):
        if course_id:
            course = self.pool.get('aun.registrar.course').browse(cr, uid, course_id)
            result = {'value': {
                        'course_name': course.course_name,
                        'credit_low': course.credit_low,
                        'credit_high': course.credit_high,
                        'billing_low': course.billing_low,
                        'billing_high': course.billing_high,
                        'level_id': course.level_id.id,
                        'status_id': course.status_id.id,
                        'grademode_id': course.grademode_id.id
                        }}
        else:
            result = {'value': {
                        'course_name': False,
                        'credit_low': False,
                        'credit_high': False,
                        'billing_low': False,
                        'billing_high': False,
                        'level_id': False,
                        'status_id': False,
                        'grademode_id': False
                        }}
        return result

    def _check_grading_dates(self, cr, uid, ids, context=None):
        section = self.browse(cr, uid, ids,context=context)[0]
        if section.grading_start and section.grading_end:
            return section.grading_end > section.grading_start
        return True
    
    def _get_faculty(self, cursor, uid, ids, name, arg, context=None):
        res = {} 
        for section in self.browse(cursor, uid, ids, context=context): 
            res[section.id] = {}
            res[section.id]['faculty_tree'] = [(6, 0, [x.faculty_id.id for x in section.faculty])]
            res[section.id]['faculty_char'] = ', '.join([x.faculty_id.name for x in section.faculty])
        return res

    def on_change_level(self, cr, uid, ids, level_id, course_id, status_id, context=None):
        if level_id:
            if course_id:
                course = self.pool.get('aun.registrar.course').browse(cr, uid, course_id)
                if course.level_id.id != level_id:
                    return {'value': {'status_id': False}}
                if status_id and status_id != course.status_id.id:
                    return {'value': {'status_id': False}}
        return {}

    def on_change_value(self, cr, uid, ids, value, course_id, field_name, context=None):
        res = value
        warning = {}
        if course_id:
            course = self.pool.get('aun.registrar.course').browse(cr, uid, course_id)
            if field_name[:6] == 'credit' and (value < course.credit_low or value > course.credit_high):
                res = course.credit_low if value < course.credit_low else course.credit_high
                warning = {
                        'title': _('Invalid ' + ['Maximum','Minimum'][field_name[7:]=='low'] + ' Credit'),
                        'message': _('The amount should be ' + ['less than or equal to the maximum', 'greater than or equal to the minimum'][value < course.credit_low] + ' credit hours for the course: ' + str(res) + ' credit hours')
                        }
            if field_name[:7] == 'billing' and (value < course.billing_low or value > course.billing_high):
                res = course.billing_low if value < course.billing_low else course.billing_high
                warning = {
                        'title': _('Invalid ' + ['Maximum','Minimum'][field_name[8:]=='low'] + ' Billing'),
                        'message': _('The amount should be ' + ['less than or equal to the maximum', 'greater than or equal to the minimum'][value < course.billing_low] + ' billing hours for the course: ' + str(res) + ' billing hours')
                        }
        return {'value': {field_name: res}, 'warning': warning}
    
    def copy(self, cr, uid, ids, default=None, context=None):
        if context is None:
            context={}
        if not default:
            default = {}
        context = context.copy()
        default = default.copy()
        if self.browse(cr, uid, ids).state == 'cancelled':
            if context.get('duplicate'):
                return False
            else:
                raise osv.except_osv(_('Invalid!'), _('This section has been cancelled. It cannot be duplicated'))                                 
        
        default['enrollment_ids'] = False
        return super(aun_registrar_section, self).copy(cr, uid, ids, default=default, context=context) 
       
    _columns = {
		'course_id': fields.many2one('aun.registrar.course', 'Course', ondelete="cascade", select=False, required=True, readonly=False, domain=[('active','=',True)], track_visibility="onchange"),
        'name': fields.char('CRN', size=16, readonly=True, track_visibility="onchange"),
        'course_name': fields.char('Course Title', size=128, required=True, track_visibility="onchange"),
        'subject_id': fields.related('course_id', 'subject_id', type='many2one', relation="course.subject", string="Subject", store=True, readonly=True),
        'school_id': fields.related('subject_id', 'school_id', type='many2one', relation='aun.registrar.school', store=True,readonly=True,string="School",track_visibility="onchange"),
        'grademode_id': fields.many2one('aun.registrar.grademode', 'Grade Mode', required=True, track_visibility="onchange"),
        'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility="onchange"),
        'status_id': fields.many2one('registrar.status', 'Status Required', required=True, domain="[('level_id','=',level_id)]", track_visibility="onchange"),
        'section_no': fields.integer('No.', size=4, readonly=True, help='Section Number', track_visibility="onchange"),
		'term_id': fields.many2one('aun.registrar.term', 'Term', ondelete="cascade", select=False, required=True, track_visibility="onchange"),
        'duration_id': fields.many2one('aun.registrar.duration', 'Time', select=False, readonly=False, track_visibility="onchange"),
		'location_id': fields.many2one('aun.registrar.location', 'Location', select=False, track_visibility="onchange"),
        'enrollment_ids': fields.one2many('aun.registrar.enrollment', 'section_id', 'Enrollees', domain=[('state','=','registered')]),
        'max_size': fields.integer('Capacity', track_visibility="onchange"),
        'filter_rooms': fields.boolean('Filter Available Locations'),
        'no_of_labs': fields.integer('Number of Labs Required', help='Number of labs required to satisfy the course requirement', track_visibility="onchange"),
        'state': fields.selection(SECTION_STATES, 'Class Status', size=16, readonly=True, track_visibility="onchange"),
        'enrolled': fields.function(_get_enrolled, method=True, type='integer', string='Enrolled',
                                    store={
                                        'aun.registrar.enrollment': (_get_enrollments, ['state'], 10)
                                    }),
        'faculty': fields.one2many('aun.faculty.section', 'section_id', 'Faculty', track_visibility="onchange"),
        'faculty_tree':fields.function(_get_faculty, string='Faculty', type='many2many', method=True, multi='faculty', store=False, relation='hr.employee'),
        'faculty_char':fields.function(_get_faculty, string='Faculty', type='char', method=True, multi='faculty', store=False),
        'primary_faculty_user_id': fields.many2one('res.users', 'Primary Faculty', track_visibility="onchange"),
        'labs': fields.one2many('section.lab', 'section_id', 'Labs', track_visibility="onchange"),
        'credit_low': fields.float('Minimum Credit Hours', digits=(3,2), track_visibility="onchange"),
        'credit_high': fields.float('Maximum Credit Hours', digits=(3,2), track_visibility="onchange"),
        'billing_low': fields.float('Minimum Billing Hours', digits=(3,2), track_visibility="onchange"),
        'billing_high': fields.float('Maximum Billing Hours', digits=(3,2), track_visibility="onchange"),
        'open_for_grading':fields.function(_check_grading, string='Open For Grading', type='boolean', method=True, store=False, fnct_search=_grading_search, help='Open for grading'),
        'grading_start': fields.datetime('Start Date', track_visibility="onchange"),
        'grading_end': fields.datetime('End Date', track_visibility="onchange"),
        'has_enrollment': fields.function(_has_enrollment, method=True, type='boolean', string='Has Enrollment', store=False),
        'active': fields.boolean('Active')
    }

    _defaults={
        'state': lambda *a: 'draft',
        'active': True
    }
    
    def _check_credit_and_billing(self, cr, uid, ids, context=None):
        section = self.browse(cr, uid, ids,context=context)[0]
        if section.credit_low > section.credit_high:
            raise osv.except_osv(_('Check Credit!'), _('The minimum credit cannot be greater than the maximum credit'))
        if section.billing_low > section.billing_high:
            raise osv.except_osv(_('Check Billing!'), _('The minimum billing cannot be greater than the maximum billing'))
        return True
    
    _sql_constraints = [
        ('uniq_crn', 'unique(name)', 'The section CRN must be unique!')
    ]
    
    _constraints =[
        (_check_time_conflict, 'Section time conflicts with its lab(s).',['Labs']),
#         (_check_primary_faculty_and_percentages, 'The total percentage of faculty work must be 100%',['percentage']),
        (_check_grading_dates, 'The end date should be greater than the start date.',['Grading Start/End']),
        (_check_credit_and_billing, 'Credit and billing high should be greater than credit and billing low!', ['Credit/Billing'])
    ]
   
aun_registrar_section()


class aun_registrar_level(osv.osv):
    _name = "aun.registrar.level"
    _description = "Level"
    _inherit = ["mail.thread"]
    _columns = {
        'name': fields.char('Name', required=True, size=32, track_visibility="onchange"),
        'status_ids': fields.one2many('registrar.status', 'level_id', 'Status', track_visibility="onchange"),
        'honors_ids': fields.one2many('registrar.honors', 'level_id', 'Honors', track_visibility="onchange"),
        'active': fields.boolean('Active')
        }
    _defaults = {
        'active': True
        }
    
    def unlink(self, cr, uid, ids, context=None):
        app_type_obj = self.pool.get('aun.application.type')
        app_type_ids = app_type_obj.search(cr, uid, [('level_id','in',ids)])
        app_type_obj.write(cr, uid, app_type_ids, {'active': False})
        self.write(cr, uid, ids, {'active': False})
        return True
    
    _sql_constraints = [
        ('uniq_level', 'unique(name)', 'Level name must be unique!')
    ]

aun_registrar_level()


class aun_registrar_grademode(osv.osv):
    _name = "aun.registrar.grademode"
    _description = "Grade Mode"
    _inherit = ["mail.thread"]
    _columns = {
        'name': fields.char('Name', required=True, size=32, track_visibility="onchange"),
        'description': fields.text('Description', track_visibility="onchange"),
        'grade_id': fields.one2many('aun.registrar.grade', 'grademode_id', 'Grades')
        }

    _sql_constraints = [
        ('uniq_grademode', 'unique(name)', 'Grademodes must be unique!')
    ]

aun_registrar_grademode()


class course_subject(osv.osv):
    _name = "course.subject"
    _description = "Subjects"
    _inherit = ["mail.thread"]

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        for record in reads:
            name = record.name + ' - ' + record.title
            res.append((record['id'], name))
        return res    

    _columns = {
        'name': fields.char('Code', size=4, required=True, track_visibility="onchange"),
        'title': fields.char('Title', size=32, required=True, track_visibility="onchange"),
        'school_id': fields.many2one('aun.registrar.school', 'School', required=True, track_visibility="onchange")
        }

    _sql_constraints = [
        ('uniq_subject', 'unique(name)', 'Subject codes must be unique!')
    ]

course_subject()


class course_type(osv.osv):
    _name = "course.type"
    _description = "Course Types"
    _inherit = ["mail.thread"]
    _columns = {
        'name': fields.char('Name', size=32, required=True, track_visibility="onchange"),
        'description': fields.text('Description', track_visibility="onchange"),
        }

    _sql_constraints = [
        ('uniq_course_type', 'unique(name)', 'Course types must be unique!')
    ]

course_type()


class registrar_program(osv.osv):
    _name = "registrar.program"
    _description = "Programs"
    _inherit = ["mail.thread"]
       
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        for record in reads:
            name = record.name + ' - ' + record.title
            res.append((record['id'], name))
        return res
        
    _columns = {
        'title': fields.char('Program Name', size=64, required=True, track_visibility="onchange"),
        'name': fields.char('Code', size=10, required=True, track_visibility="onchange"),
        'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility="onchange"),
        'description': fields.text('Description', track_visibility="onchange"),
        'major_course_ids': fields.one2many('aun.registrar.major.course', 'major_id', 'Major Course'),
    }

    def _uniq_name_and_title(self, cr, uid, ids, context=None):
        program = self.browse(cr, uid, ids, context=context)[0]
        program_ids = self.search(cr, uid, [('id','not in',[program.id])])      
        for prog in self.browse(cr, uid, program_ids):
            if prog.name.lower() == program.name.lower():
                raise osv.except_osv(_('Check Program Code!'), _('There is another program with the same code: ' + prog.name + '. The code must be unique!'))
            if prog.title.lower() == program.title.lower():
                raise osv.except_osv(_('Check program Title!'), _('There is another program with the same title: ' + prog.title + '. The program title must be unique!'))                
        return True
    
    _constraints=[
        (_uniq_name_and_title, 'There is another program with the same code or title.', ['Code'])
    ]

registrar_program()


class registrar_honors(osv.osv):
    _name = "registrar.honors"
    _description = "Honors"
    _inherit = ["mail.thread"]
        
    _columns = {
        'name': fields.char('Name', size=32, required=True, track_visibility="onchange"),
        'gpa_from': fields.float('From(GPA)', required=True, track_visibility="onchange"),
        'gpa_to': fields.float('To(GPA)', required=True, track_visibility="onchange"),
        'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility="onchange")
        }
      
    def _check_range(self, cr, uid, ids, context=None):
        honors = self.browse(cr, uid, ids, context=context)[0]
        if honors.gpa_from >= honors.gpa_to:
            raise osv.except_osv(_('Check ' + honors.name), _('The GPA range end must be greater than the range start.'))
        honors_ids = self.search(cr, uid, [('level_id','=',honors.level_id.id),('id','not in',[honors.id])])
        
        for honor in self.browse(cr, uid, honors_ids):
            if (honor.gpa_from < honors.gpa_from < honor.gpa_to or
                honor.gpa_from < honors.gpa_to < honor.gpa_to or
                honors.gpa_from < honor.gpa_to < honors.gpa_to or
                honors.gpa_from < honor.gpa_to < honors.gpa_to or
                honor.gpa_from == honors.gpa_from or
                honor.gpa_to == honors.gpa_to or
                honor.gpa_from == honors.gpa_to or
                honor.gpa_to == honors.gpa_from):
                    raise osv.except_osv(_('Check ' + honors.name), _('The GPA range coincides with the range for the ' + honor.name))
        return True
    
    _constraints=[
        (_check_range, 'Honors ranges should be chronological.', ['Range'])
    ]

    _sql_constraints = [
        ('uniq_name', 'unique(level_id,name)', 'Honors must be unique.')
    ]
       
registrar_honors()


class institutional_honors(osv.osv):
    _name = "institutional.honors"
    _description = "Institutional Honors"
    _inherit = ["mail.thread"]
        
    _columns = {
        'name': fields.char('Name', size=32, required=True, track_visibility="onchange"),
        'gpa_from': fields.float('From(GPA)', required=True, track_visibility="onchange"),
        'gpa_to': fields.float('To(GPA)', required=True, track_visibility="onchange")
        }
    
    def _check_range(self, cr, uid, ids, context=None):
        honors = self.browse(cr, uid, ids, context=context)[0]
        if honors.gpa_from >= honors.gpa_to:
            raise osv.except_osv(_('Check ' + honors.name), _('The GPA range end must be greater than the range start.'))
        honors_ids = self.search(cr, uid, [('id','not in',[honors.id])])
        
        for honor in self.browse(cr, uid, honors_ids):
            if (honor.gpa_from < honors.gpa_from < honor.gpa_to or
                honor.gpa_from < honors.gpa_to < honor.gpa_to or
                honors.gpa_from < honor.gpa_to < honors.gpa_to or
                honors.gpa_from < honor.gpa_to < honors.gpa_to or
                honor.gpa_from == honors.gpa_from or
                honor.gpa_to == honors.gpa_to or
                honor.gpa_from == honors.gpa_to or
                honor.gpa_to == honors.gpa_from):
                    raise osv.except_osv(_('Check ' + honors.name), _('The GPA range coincides with the range for the ' + honor.name))
        return True
 
    def _uniq_name(self, cr, uid, ids, context=None):
        honors = self.browse(cr, uid, ids, context=context)[0]
        honor_ids = self.search(cr, uid, [('id','not in',[honors.id])])       
        for honor in self.browse(cr, uid, honor_ids):
            if honor.name.lower() == honors.name.lower():
                raise osv.except_osv(_('Check honors name!'), _('There is another honor with the same name: ' + honor.name + '. The name must be unique.'))
        return True
    
    _constraints=[
        (_check_range, 'Honors ranges should be chronological.', ['Range']),
        (_uniq_name, 'There is another honor with the same name.', ['Name'])
    ]

institutional_honors()


class aun_registrar_grade(osv.osv):
    _name = "aun.registrar.grade"
    _description = "Grade"
    _inherit = ["mail.thread"]
    _order = 'numeric_value DESC'

    _columns = {
        'name': fields.char('Grade Code', size=16, required=True, track_visibility="onchange"),
        'level_id': fields.many2one('aun.registrar.level', 'Level', ondelete="cascade", select=False, required=True, track_visibility="onchange"),
        'grademode_id': fields.many2one('aun.registrar.grademode', 'Grade Mode', ondelete="cascade", select=False, required=True, track_visibility="onchange"),
        #'abbreviation': fields.char('Abbreviation', size=16),
        'quality_points': fields.float('Quality Points', track_visibility="onchange"),
        'attempted': fields.boolean('Attempted', track_visibility="onchange"),
        'passed': fields.boolean('Passed', track_visibility="onchange"),
        'earned': fields.boolean('Earned', track_visibility="onchange"),
        'gpa': fields.boolean('GPA', track_visibility="onchange"),
        'default_grade': fields.boolean('Default', track_visibility="onchange"),
        'status_indicator': fields.boolean('Active', track_visibility="onchange"),
        'numeric_value': fields.integer('Numeric Value', track_visibility="onchange"),
        'repeat_indicator': fields.boolean('Repeat Indicator', track_visibility="onchange"),
        'web_indicator': fields.boolean('Web Indicator', track_visibility="onchange"),
        'midterm': fields.boolean('Midterm', track_visibility="onchange"),
        'refund': fields.boolean('Refund', track_visibility="onchange")
        }
    
    def _check_default_grade(self, cr, uid, ids, context=None):
        if self.search(cr, uid, [('default_grade','=', True)], count=True) > 1:
            raise osv.except_osv(_('Check Default'), _('Only one grade can be set as the default grade.'))
        return True

    _sql_constraints = [
        ('name_uniq', 'unique(name, level_id, grademode_id)', 'This grade already exists for this level and grade mode!')
    ]

    _constraints=[
        (_check_default_grade, 'You can only set one grade as default.', ['Default'])
    ] 
aun_registrar_grade()
 


class transfer_institution(osv.osv):
    _name = "transfer.institution"
    _description = "Transfer Institution"
    _inherit = ["mail.thread"]    
    
    _columns = {
        'name': fields.char('Institution Name', size=128, required=True, track_visibility="onchange"),
        'code': fields.char('Institution Code', size=32, required=True, track_visibility="onchange")
        }
    
    def _uniq_name_and_code(self, cr, uid, ids, context=None):
        institution = self.browse(cr, uid, ids, context=context)[0]
        institution_ids = self.search(cr, uid, [('id','not in',[institution.id])])
        for inst in self.browse(cr, uid, institution_ids):
            if inst.name.lower() == institution.name.lower():
                raise osv.except_osv(_('Check Institution Name!'), _('There is another institution with the same name: ' + inst.name + '. The name must be unique!'))
            if inst.code.lower() == institution.code.lower():
                raise osv.except_osv(_('Check Institutuion Code!'), _('There is another institution with the same code: ' + inst.code + '. The institution code must be unique!'))                
        return True
    
    _constraints=[
        (_uniq_name_and_code, 'There is another institution with the same name or code.', ['Name/Code'])
    ]

transfer_institution()



class transfer_info(osv.osv):
    _name = "transfer.info"
    _description = "Transfer Information"
    _inherit = ["mail.thread"]
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        for record in reads:
            name = record.student_id.name + ' / ' + record.institution_id.name
            res.append((record['id'], name))
        return res
 
    def on_change_student(self, cr, uid, ids, student_id, context=None):          
        if not student_id:
            return {'value': {'fname': False, 'lname': False, 'level_id': False}}
        student = self.pool.get('res.partner').browse(cr, uid, student_id)
        return {'value': {'fname': student.fname, 'lname': student.lname, 'level_id': student.level_id.id, 'image_medium': student.image_medium}}
   
    _columns = {
        'student_id': fields.many2one('res.partner', 'Student', track_visibility="onchange", required=True, domain=[('student','=',True)]),
        'fname': fields.related('student_id', 'fname', type='char', string='First Name', readonly=True, store=False),
        'lname': fields.related('student_id', 'lname', type='char', string='Last Name', readonly=True, store=False),
        'image_medium': fields.related('student_id', 'image_medium', type='binary', readonly=True, string='Image', store=False),
        'institution_id': fields.many2one('transfer.institution', 'Transfer Institution', required=True, track_visibility="onchange"),
        'transcript_date': fields.date('Transcript Receipt Date', track_visibility="onchange"),
        'official': fields.boolean('Official', track_visibility="onchange"),
        'attendance_terms': fields.char('Attendance Term(s)', size=64, track_visibility="onchange"),
        'acceptance_date': fields.date('Acceptance Date', track_visibility="onchange"),
        'effective_term_ids': fields.many2many('aun.registrar.term','rel_transfer_info_eff_term','t_info_id','term_id','Effective Term(s)', track_visibility="onchange"),
        'level_id': fields.related('student_id', 'level_id', type='many2one', relation='aun.registrar.level', string='Apply to Level', store=False, readonly=True),
        'degree': fields.many2one('registrar.program', 'Transfer Degree', track_visibility="onchange"),
        'attendance_date_from': fields.date('Attendance Begin Date'),
        'attendance_date_to': fields.date('Attendance End Date'),
        'transfer_course_ids': fields.one2many('transfer.course', 'transfer_info_id', 'Transfer Course(s)', track_visibility="onchange"),
        }

    def _check_term(self, cr, uid, ids, context=None):
        transfer_info = self.browse(cr, uid, ids, context=context)[0]
        effective_term_ids = [t.id for t in transfer_info.effective_term_ids]
        effective_term_names = [t.name_get()[0][1] for t in transfer_info.effective_term_ids]
        transfer_courses = transfer_info.transfer_course_ids
        equiv_courses = []
        for tc in transfer_courses:
            equiv_courses += tc.equiv_course_ids
        wrong_term_courses = []
        for ec in equiv_courses:
            if ec.term_id.id not in effective_term_ids:
                wrong_term_courses.append(ec.course_id.name)
                
        if wrong_term_courses:
            raise osv.except_osv(_('Invalid Term!'), _('The term selection for ' + ', '.join(wrong_term_courses) + ' is not ' + ['the effective term', 'one of the effective terms'][len(transfer_info.effective_term_ids) > 1] + ' selected (' + [', '.join(effective_term_names),'None'][len(effective_term_names)==0] + ') for this transfer period.'))
        
        equiv_term_names = [ec.term_id.name_get()[0][1] for ec in equiv_courses]
        unused_terms = list(set(effective_term_names) - set(equiv_term_names))
        if unused_terms:
            raise osv.except_osv(_('Unused Term!'), _('Remove unused effective ' + ['term: ', 'terms: '][len(unused_terms) > 1] + ', '.join(unused_terms)))
        
        return True
    
    def _check_multiple_courses(self, cr, uid, ids, context=None):
        transfer_info = self.browse(cr, uid, ids, context=context)[0]
        transfer_courses = transfer_info.transfer_course_ids
        equiv_courses = []
        for tc in transfer_courses:
            equiv_courses += tc.equiv_course_ids
        
        courses = [c.course_id.name for c in equiv_courses]
        if len(courses) != len(set(courses)):
            courses = collections.Counter(courses)
            duplicate_courses = [i for i in courses if courses[i] > 1]
            raise osv.except_osv(_('Duplicate Course(s)!'), _(['This course is', 'These courses are'][len(duplicate_courses) > 1] + ' duplicated in this transfer period: ' + ', '.join(duplicate_courses)))                             
        
        '''#not sure if registrar wants this check
        enr_obj = self.pool.get('aun.registrar.enrollment')
        registered_courses = []
        for course in equiv_courses:
            enr_id = enr_obj.search(cr, uid, [('term_id','=',course.term_id.id),('course_id','=',course.course_id.id),('student_id','=',course.student_id.id),('state','=','registered'),('lab','=',False)])
            if enr_id:
                registered_courses.append(course.course_id.name)
        if registered_courses:
            raise osv.except_osv(_('Duplicate Course(s)!'), _('The student is registered for ' + ['this course','these courses'][len(registered_courses) > 1] + ' in the same transfer term: ' + ', '.join(registered_courses)))'''
                
        '''#check for ungraded enrollments in previous terms
        ungraded_courses = []
        for c in equiv_courses:
            enr_id = enr_obj.search(cr, uid, [('student_id','=',c.student_id.id),('term_id','not in',[c.term_id.id]),('course_id','=',c.course_id.id),('state','=','registered'),('grade','=',False),('lab','=',False)], context=context)
            if enr_id:
                ungraded_courses.append(c.course_id.name)
        if ungraded_courses:              
            raise osv.except_osv(_('Course Restriction!'), _('The student\'s previous enrollment in the following ' + ['course has','courses have'][len(ungraded_courses) > 1] + ' not been graded: ' + ', '.join(ungraded_courses)))'''
        return True

    '''def _check_level(self, cr, uid, ids, context=None):
        transfer_info = self.browse(cr, uid, ids, context=context)[0]
        transfer_courses = transfer_info.transfer_course_ids
        student_level = transfer_info.student_id.level_id
        equiv_courses = []
        for tc in transfer_courses:
            equiv_courses += tc.equiv_course_ids
        
        courses = [c.course_id.name for c in equiv_courses if c.course_id.level_id.id != student_level.id]
        if courses:
            raise osv.except_osv(_('Check Course Level!'), _(['This course', 'These courses'][len(courses) > 1] + ' are not on the student\'s current level(' + student_level.name + '): '+ ', '.join(courses)))                             
        
        return True'''

    def _check_attendance_dates(self, cr, uid, ids, context=None):
        info = self.browse(cr, uid, ids,context=context)[0]
        if info.attendance_date_from and info.attendance_date_to:
            return info.attendance_date_to > info.attendance_date_from
        return True
               
    _constraints = [
        (_check_multiple_courses, 'Duplicate Course.',['Course']),
        (_check_attendance_dates, 'The end date should be greater than the start date.',['Attendance Dates']),
        (_check_term, 'Wrong term selection.',['Equivalent Course Term']),
#         (_check_level, 'Wrong level selection.',['Equivalent Course Level']),
    ]
    
transfer_info()

   

class transfer_course(osv.osv):
    _name = "transfer.course"
    _description = "Transfer Course Detail"
    _inherit = ["mail.thread"]
    
    _columns = {
        'name': fields.char('Course Title', size=32, required=True, track_visibility="onchange"),
        'subject': fields.char('Subject', size=32, required=True, track_visibility="onchange"),
        'course_no': fields.char('Course Number(s)', size=32, required=True, track_visibility="onchange"),
        'credit': fields.float('Hours', digits=(3,2), required=True, track_visibility="onchange"),
        'grade_ids': fields.many2many('aun.registrar.grade', 'rel_t_course_grade', 't_course_id', 'grade_id', 'Grade', required=True, track_visibility="onchange"),
        'equiv_course_ids': fields.one2many('transfer.course.equivalent', 'transfer_course_id', 'Equivalent Course(s)', required=True, track_visibility="onchange"),
        'transfer_info_id': fields.many2one('transfer.info', 'Transfer Information', required=True),
        'student_id': fields.many2one('res.partner', 'Student', domain=[('student','=',True)])
        }

transfer_course()



class transfer_course_equivalent(osv.osv):
    _name = "transfer.course.equivalent"
    _description = "Transfer Course Equivalent"
    _inherit = ["mail.thread"]

    def unlink(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancelled', 'active': False})
        return True

    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'done'
        vals['transfer_course_id']
        tc = self.pool.get('transfer.course').browse(cr, uid, vals['transfer_course_id'])
        student = tc.transfer_info_id.student_id                    

        lg_obj = self.pool.get('level.gpa')
        level_gpa_id = lg_obj.search(cr, uid, [('student_id','=',student.id),('level_id','=',student.level_id.id),('admission_date','=',student.admission_date),('student_state_id','=',student.student_state_id.id),('current','=',True)])
        if level_gpa_id:
            level_gpa_id = level_gpa_id[0]
        else:
            other_lg_ids = lg_obj.search(cr, SUPERUSER_ID, [('student_id','=', student.id),('current','=',True)])
            lg_obj.write(cr, SUPERUSER_ID, other_lg_ids, {'current': False})
            level_gpa_id = lg_obj.create(cr, SUPERUSER_ID, {'student_id': student.id,
                                                            'level_id': student.level_id.id,
                                                            'admission_date': student.admission_date,
                                                            'term_admitted': student.term_admitted.id,
                                                            'major_ids': [(6, 0, [major.id for major in student.major_ids])],
                                                            'minor_ids': [(6, 0, [minor.id for minor in student.minor_ids])],
                                                            'conc_ids': [(6, 0, [conc.id for conc in student.concentration_ids])],
                                                            'student_state_id': student.student_state_id.id,
                                                            'date_of_state': student.date_of_state,
                                                            'current': True})

        vals['level_gpa_id'] = level_gpa_id
        res = super(transfer_course_equivalent, self).create(cr, uid, vals, context)
        enr_obj = self.pool.get('aun.registrar.enrollment')
        course = self.browse(cr, uid, res)
        other_transfer_ids = self.get_transfer_equiv_ids(cr, uid, course, False, False)
        enrollment_ids = enr_obj.get_equiv_enr_ids(cr, uid, False, student, course.course_id.id, False, True)

        if vals['repeat'] == 'I':
            if not(other_transfer_ids or enrollment_ids):
                raise osv.except_osv(_('Invalid'), _('The student has only taken ' + course.course_id.name + ' once. It is included automatically.'))

        if not vals['repeat'] and not course.course_id.exclude:
            latest_course = True
            if other_transfer_ids or enrollment_ids:
                transfers = self.browse(cr, uid, other_transfer_ids) if other_transfer_ids else []
                enrollments = enr_obj.browse(cr, uid, enrollment_ids) if enrollment_ids else []
                for enr in transfers + enrollments:
                    if enr.term_id.code > course.term_id.code:
                        latest_course = False
                if latest_course:
                    super(transfer_course_equivalent, self).write(cr, uid, res, {'repeat': 'I'})
                    super(transfer_course_equivalent, self).write(cr, uid, other_transfer_ids, {'repeat': 'E'})
                    super(aun_registrar_enrollment, enr_obj).write(cr, uid, enrollment_ids, {'repeat': 'E'})
                    for transfer_id in other_transfer_ids:
                        self._update_gpa_info(cr, uid, transfer_id)
                    for enrollment_id in enrollment_ids:
                        enr_obj._update_gpa_info(cr, uid, enrollment_id)
        self._update_gpa_info(cr, uid, res)         
        return res
 
    def write(self, cr, uid, ids, vals, context=None):
        enr_obj = self.pool.get('aun.registrar.enrollment')
        course = self.browse(cr, uid, ids, context=context)[0]
        course_id = vals['course_id'] if 'course_id' in vals else course.course_id.id
        other_transfer_ids = self.get_transfer_equiv_ids(cr, uid, course, False, False)
        enrollment_ids = enr_obj.get_equiv_enr_ids(cr, uid, False, course.student_id, course_id, False, True)

        if 'repeat' in vals and vals['repeat'] == 'I' and not course.course_id.exclude:
            if not(other_transfer_ids or enrollment_ids):
                raise osv.except_osv(_('Invalid'), _('The student has only taken ' + course.course_id.name + ' once. It is included automatically.'))
            super(transfer_course_equivalent, self).write(cr, uid, other_transfer_ids, {'repeat': 'E'})
            super(aun_registrar_enrollment, enr_obj).write(cr, uid, enrollment_ids, {'repeat': 'E'})
            for transfer_id in other_transfer_ids:
                self._update_gpa_info(cr, uid, transfer_id)
            for enrollment_id in enrollment_ids:
                enr_obj._update_gpa_info(cr, uid, enrollment_id)
            
        res = super(transfer_course_equivalent, self).write(cr, uid, ids, vals, context=context)
        if 'repeat' in vals or 'credit' in vals or 'grade_id' in vals or 'state' in vals:
            self._update_gpa_info(cr, uid, ids[0])
        return res

    def _update_gpa_info(self, cr, uid, transfer_id, context=None):
        equiv_course = self.browse(cr, uid, transfer_id, context=context)
        gpa_info_obj = self.pool.get('gpa.info')
        student_obj = self.pool.get('res.partner')
        term_id = equiv_course.term_id.id
        student_id = equiv_course.student_id.id
        majors = equiv_course.student_id.major_ids
        minors = equiv_course.student_id.minor_ids
        concs = equiv_course.student_id.concentration_ids

        school_ids = student_obj.browse(cr, uid, student_id)._get_schools_and_programs(cr, uid)[student_id]['school_ids'][0][2]
        program_ids = student_obj.browse(cr, uid, student_id)._get_schools_and_programs(cr, uid)[student_id]['program_ids'][0][2]
        major_ids = [major.id for major in majors]
        minor_ids = [minor.id for minor in minors]
        conc_ids = [conc.id for conc in concs]
        
        level_gpa_id = equiv_course.level_gpa_id.id
        student_term_info_id = gpa_info_obj.search(cr, uid, [('term_id','=',term_id),('student_id','=',student_id),('level_gpa_id','=',level_gpa_id)])
        if student_term_info_id:
            gpa_info = gpa_info_obj.browse(cr, uid, student_term_info_id[0])
        
        t_attempted_hours = gpa_info_obj.get_term_transfer_attempted_hours(cr, uid, term_id, student_id, level_gpa_id)
        t_quality_points = gpa_info_obj.get_term_transfer_quality_points(cr, uid, term_id, student_id, level_gpa_id)
        t_passed_hours = gpa_info_obj.get_term_transfer_passed_hours(cr, uid, term_id, student_id, level_gpa_id)
        t_earned_hours = gpa_info_obj.get_term_transfer_earned_hours(cr, uid, term_id, student_id, level_gpa_id)
        t_gpa_hours = gpa_info_obj.get_term_transfer_gpa_hours(cr, uid, term_id, student_id, level_gpa_id)
        t_gpa = gpa_info_obj.get_term_gpa(cr, uid, t_quality_points, t_gpa_hours)
         
        gpa_info_deleted = False
        transfer = True
        if student_term_info_id:
            gpa_info = gpa_info_obj.browse(cr, uid, student_term_info_id[0])
            t_course_ids = self.search(cr, uid, [('term_id','=',term_id),('student_id','=',student_id)])
            if not t_course_ids:
                transfer = False
                if not gpa_info.institution:
                    ctx = dict(delete = True)
                    gpa_info_obj.unlink(cr, SUPERUSER_ID, student_term_info_id, context=ctx)
                    gpa_info_deleted = True
        if not gpa_info_deleted:
            if student_term_info_id:
                gpa_info_obj.write(cr, SUPERUSER_ID, student_term_info_id[0],{
                                                   't_attempted_hours': t_attempted_hours,                   
                                                   't_quality_points': t_quality_points,
                                                   't_passed_hours': t_passed_hours,
                                                   't_earned_hours': t_earned_hours,
                                                   't_gpa_hours': t_gpa_hours,
                                                   't_gpa': t_gpa
                                                   })
            elif transfer:
                student_term_info_id = gpa_info_obj.create(cr, SUPERUSER_ID, {
                                                    'school_ids': [(6, 0, school_ids)],
                                                    'program_ids': [(6, 0, program_ids)],
                                                    'major_ids': [(6, 0, major_ids)],
                                                    'minor_ids': [(6, 0, minor_ids)],
                                                    'conc_ids': [(6, 0, conc_ids)],
                                                    'level_gpa_id': level_gpa_id,
                                                    'term_id': term_id,
                                                    'student_id': student_id,
                                                    't_attempted_hours': t_attempted_hours,
                                                    't_quality_points': t_quality_points,
                                                    't_passed_hours': t_passed_hours,
                                                    't_earned_hours': t_earned_hours,
                                                    't_gpa_hours': t_gpa_hours,
                                                    't_gpa': t_gpa
                                                    })
        gpa_info_obj.get_terms_cgpa(cr, uid, student_id, 'transfer', level_gpa_id)
        return True
    
    def get_transfer_equiv_ids(self, cr, uid, transfer_equiv, student, course_id, context=None):
        if transfer_equiv:
            student_id = transfer_equiv.student_id.id
            course_id = transfer_equiv.course_id.id
            level_gpa_id = transfer_equiv.level_gpa_id.id
            transfer_ids = self.search(cr, uid, [('id','!=',transfer_equiv.id),('student_id','=',student_id),('level_gpa_id','=',level_gpa_id)])        
            equivalent_ids = [c.id for c in transfer_equiv.course_id.equivalents]
        else:
            level_gpa_id = self.pool.get('level.gpa').search(cr, uid, [('student_id','=',student.id),('level_id','=',student.level_id.id),('admission_date','=',student.admission_date),('student_state_id','=',student.student_state_id.id),('current','=',True)])
            if level_gpa_id:
                level_gpa_id = level_gpa_id[0]
            else:
                raise osv.except_osv(_('Check student level!'), _('Check level GPA.'))
            transfer_ids = self.search(cr, uid, [('student_id','=',student.id),('level_gpa_id','=',level_gpa_id)])
            equivalents = self.pool.get('aun.registrar.course').browse(cr, uid, course_id).equivalents
            equivalent_ids = [c.id for c in equivalents]

        transfers = self.browse(cr, uid, transfer_ids)
        transfer_equiv_ids = [t.id for t in transfers if course_id in [x.id for x in t.course_id.equivalents] or 
                             t.course_id.id in equivalent_ids or 
                             course_id == t.course_id.id]
        return transfer_equiv_ids

    def on_change_course(self, cr, uid, ids, course_id, context=None):
        result = {'value': {'name': False}}
        if course_id:
            course = self.pool.get('aun.registrar.course').browse(cr, uid, course_id)
            result = {'value': {'name': course.course_name, 'credit': course.credit_low}}
        return result

    def on_change_credit(self, cr, uid, ids, credit, course_id, context=None):
        if not course_id:
            return {'value': {'credit': False}, 'warning': {'title': _('No course'), 'message': _('Please select a course first!')}}
        course = self.pool.get('aun.registrar.course').browse(cr, uid, course_id)
        res = credit
        warning = {}
        if (credit < course.credit_low or credit > course.credit_high):
            res = course.credit_low if credit < course.credit_low else course.credit_high
            warning = {
                    'title': _('Invalid Credit'),
                    'message': _('The amount should be ' + ['less than or equal to the maximum', 'greater than or equal to the minimum'][credit < course.credit_low] + ' credit hours for the course: ' + str(res) + ' credit hours')
                    }
        return {'value': {'credit': res}, 'warning': warning}
    
    def on_change_grademode(self, cr, uid, ids, grademode_id, grade_id, context=None):
        res = {}
        if not grademode_id:
            return res
        grade_obj = self.pool.get('aun.registrar.grade')
        if grade_id:
            grade = grade_obj.browse(cr, uid, grade_id)
            if grade.grademode_id.id != grademode_id:
                res['grade_id'] = False
        return {'value': res}  

    def on_change_repeat(self, cr, uid, ids, repeat, student_id, course_id, context=None):
        if repeat == 'I':
            if not student_id:
                return {'value': {'repeat': False}, 'warning': {'title': _('No student'), 'message': _('Ensure that you have selected a student for this transfer!')}}
            if not course_id:
                return {'value': {'repeat': False}, 'warning': {'title': _('No course'), 'message': _('Please select a course first!')}}
            course = self.pool.get('aun.registrar.course').browse(cr, uid, course_id)
            if course.exclude:
                return {}
            else:
                enr_obj = self.pool.get('aun.registrar.enrollment')
                student = self.pool.get('res.partner').browse(cr, uid, student_id)
                other_transfer_ids = self.get_transfer_equiv_ids(cr, uid, False, student, course_id)
                enrollment_ids = enr_obj.get_equiv_enr_ids(cr, uid, False, student, course_id, False, True)
                res = repeat
                warning = {}
                if not(other_transfer_ids or enrollment_ids):
                    res = False
                    warning = {
                            'title': _('Invalid '),
                            'message': _('This is the only enrollment for the student in this course.')
                            }
                return {'value': {'repeat': res}, 'warning': warning}
        else:
            return {}
    
    _columns = {
        'name': fields.char('Title', size=64, required=True, track_visibility="onchange"),
        'student_id': fields.related('transfer_course_id', 'transfer_info_id', 'student_id', type='many2one', relation="res.partner", string="Student", store=True),
        'term_id': fields.many2one('aun.registrar.term', 'Term', required=True, track_visibility="onchange"),
        'course_id': fields.many2one('aun.registrar.course', 'Course', required=True, track_visibility="onchange"),
        'credit': fields.float('Hours', digits=(3,2), required=True, track_visibility="onchange"),
        'grademode_id': fields.many2one('aun.registrar.grademode', 'Grademode', required=True, track_visibility="onchange"),
        'grade_id': fields.many2one('aun.registrar.grade', 'Grade', required=True, track_visibility="onchange"),
        'repeat': fields.selection((('I','I'), ('E','E')),'Repeat', track_visibility="onchange"),
        'transfer_course_id': fields.many2one('transfer.course', 'Transfer Course', required=True),
        'level_gpa_id': fields.many2one('level.gpa', 'Level GPA', required=True),
        'level_id': fields.related('level_gpa_id', 'level_id', type='many2one', relation='aun.registrar.level', string='Level', store=True, readonly=True),
        'state': fields.selection(HOLD_STATES, 'State'),
        'active': fields.boolean('Active')
        }
    _defaults={
        'state': 'draft',
        'active': True
        }

transfer_course_equivalent()



class aun_add_drop(osv.osv):
    _name='aun.add.drop'
    _description='Add Drop Form'
    _inherit = ["mail.thread"]

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):       
            for record in reads:
                name = record.term_id.name_get()[0][1]
                res.append((record['id'], name))
        else:
            for record in reads:
                name = record.student_id.name + '/' + record.term_id.name_get()[0][1]
                res.append((record['id'], name))
        return res

    def fields_get(self, cr, uid, fields=None, context=None):
        term_ids = self.pool.get('aun.registrar.term').search(cr, uid, [('open_for_registration','=',True)])  #'|',('is_active','=',True),
        student_obj = self.pool.get('res.partner')
        student_id = student_obj.search(cr, uid, [('user_ids','in',uid),('student','=',True)])
        if student_id:
            if not term_ids:
                raise osv.except_osv(_('Registration Closed!'), _('No term is open for add/drop!'))      
            registration_hold = student_obj.get_holds(cr, uid, student_id[0])['registration']
            if registration_hold:
                holds = student_obj.browse(cr, uid, student_id[0], context=context).holds
                hold_names = ', '.join(list(set([hold.hold_id.name for hold in holds if hold.hold_id.registration and hold.is_active])))
                raise osv.except_osv(_('Hold Restriction!'), _('You have the following hold(s) on your record: ' + hold_names))
        return super(aun_add_drop, self).fields_get(cr, uid, fields, context)                

    def create(self, cr, uid, vals, context=None):
        section_ids = []
        lab_ids = []
        if 'section_ids' in vals and vals['section_ids']:
            context = dict(add_drop = True)
            for section_id in vals['section_ids']:
                if section_id[2]['action'] == 'add':
                    section_ids.append(section_id[2]['section_id'])
                    lab_ids += section_id[2]['lab_ids'][0][2]
                
        if 'sections' in vals and vals['sections']:
            section_ids += vals['sections'][0][2]
            if 'labs' in vals and vals['labs']:
                lab_ids += vals['labs'][0][2]
        
        if section_ids:
            self.check_standing(cr, uid, vals['student_id'])
#             self.check_major(cr, uid, vals['student_id'], section_ids)
            self.check_repeat_limit(cr, uid, vals['student_id'], section_ids)
            self.check_multiple_courses(cr, uid, vals['student_id'], vals['term_id'], section_ids)
            self.check_level_and_status(cr, uid, vals['student_id'], section_ids)
            self.check_class_size(cr, uid, vals['student_id'], section_ids, lab_ids)
            self.check_prerequisites(cr, uid, vals['student_id'], section_ids)
            self.check_corequisites(cr, uid, vals['student_id'], section_ids)
            self.check_time_conflict(cr, uid, vals['student_id'], section_ids, lab_ids)
            
        if 'sections' in vals and vals['sections']:
            for section_id in vals['sections'][0][2]:
                self.create_enrollments(cr, uid, vals['student_id'], section_id, vals['labs'][0][2])

        vals['state'] = 'done'
        res = super(aun_add_drop, self).create(cr, uid, vals, context=context)
        self.check_credit_hours(cr, uid, vals['student_id'], vals['term_id'])
        student = self.pool.get('res.partner').browse(cr, uid, vals['student_id'])
        if not student.user_ids:
            raise osv.except_osv(_("This student does not have a user account, Contact Administrator"), student.name)
        self.message_subscribe_users(cr, SUPERUSER_ID, [res], [student.user_ids[0].id], context=dict(add_drop = True))
        return res
        
    def write(self, cr, uid, ids, vals, context=None):
        add_drop = self.browse(cr, uid, ids, context=context)[0]
        student_id = add_drop.student_id.id
        term_id = add_drop.term_id.id
        if not (add_drop.term_id.open_for_registration or 'section_ids' in vals):
            if context is None:
                raise osv.except_osv(_('Term Restriction!'), _('This term is currently closed for registration.'))
        enr_obj = self.pool.get('aun.registrar.enrollment')
        original_sections = add_drop.sections
        original_labs = add_drop.labs
        original_section_ids = [s.id for s in original_sections]
        original_lab_ids = [l.id for l in original_labs]
        
        application_section_ids = [s.section_id.id for s in add_drop.section_ids if s.action == 'add' and s.state not in ['denied','cancelled']]
        application_lab_ids = []
        for section in add_drop.section_ids:
            if section.action == 'add' and section.state not in ['denied','cancelled']:
                application_lab_ids += [l.id for l in section.lab_ids]
        
        applications_added = False
        if 'section_ids' in vals and vals['section_ids']:
            applications_added = True
            for section_id in vals['section_ids']:
                if type(section_id[2]) == dict and section_id[2]['action'] == 'add':
                    application_section_ids.append(section_id[2]['section_id'])
                    application_lab_ids += section_id[2]['lab_ids'][0][2]
        
        sections_added = []
        sections_dropped = []
        if 'sections' in vals:
            if type(vals['sections'][0]) == tuple:
                updated_section_ids = [vals['sections'][0][1]]
                if context is not None:
                    if context.get('add'):
                        sections_dropped = []
                        sections_added = updated_section_ids
                    elif context.get('drop'):
                        return super(aun_add_drop, self).write(cr, uid, ids, vals, context=context)
            else:
                updated_section_ids = vals['sections'][0][2]
                sections_dropped = list(set(original_section_ids) - set(updated_section_ids))
                sections_added = list(set(updated_section_ids) - set(original_section_ids))
        else:
            updated_section_ids = original_section_ids
        
        labs_added = []
        labs_dropped = []
        if 'labs' in vals:
            if type(vals['labs'][0]) == tuple:
                updated_lab_ids = [vals['labs'][0][1]]
                if context is not None:
                    if context.get('add'):
                        labs_dropped = []
                        labs_added = updated_lab_ids
                    elif context.get('drop'):
                        labs_added = []
                        labs_dropped = updated_lab_ids
            else:
                updated_lab_ids = vals['labs'][0][2]
                labs_dropped = list(set(original_lab_ids) - set(updated_lab_ids))
                labs_added = list(set(updated_lab_ids) - set(original_lab_ids))
        else:
            updated_lab_ids = original_lab_ids
        
        if sections_dropped:
            enr_ids = enr_obj.search(cr, uid, [('section_id','in',sections_dropped), ('student_id','=',student_id), ('state','=','registered')], context=context)
            enr_obj.unlink(cr, uid, enr_ids, context=context)

        if labs_dropped:
            lab_enr_ids = enr_obj.search(cr, uid, [('student_id','=',student_id),('lab_id','in',labs_dropped),('section_id','not in',sections_dropped),('state','=','registered')], context=context)
            super(aun_registrar_enrollment, enr_obj).write(cr, SUPERUSER_ID, lab_enr_ids, {'state': 'dropped', 'active': False})

        if application_section_ids or updated_section_ids or updated_lab_ids:
            all_section_ids = list(set(updated_section_ids + application_section_ids))
            all_lab_ids = list(set(updated_lab_ids + application_lab_ids))
            if applications_added or sections_added or labs_added:
                self.check_standing(cr, uid, student_id)
#             self.check_major(cr, uid, student_id, sections_added)
            self.check_repeat_limit(cr, uid, student_id, all_section_ids)
            self.check_multiple_courses(cr, uid, student_id, term_id, all_section_ids)
            self.check_level_and_status(cr, uid, student_id, all_section_ids)
            self.check_class_size(cr, uid, student_id, all_section_ids, all_lab_ids)
            self.check_prerequisites(cr, uid, student_id, all_section_ids)
            self.check_corequisites(cr, uid, student_id, all_section_ids)
            self.check_time_conflict(cr, uid, student_id, all_section_ids, all_lab_ids)

            for section_id in updated_section_ids:
                self.create_enrollments(cr, uid, student_id, section_id, updated_lab_ids)

            self.check_credit_hours(cr, uid, student_id, term_id)

        return super(aun_add_drop, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        add_drops = self.browse(cr, uid, ids, context=context)      
        for ad in add_drops:
            if ad.sections:
                raise osv.except_osv(_('Invalid action!'), _('You have to drop the enrollment(s) in ' + ad.term_id.name.name + ' ' + ad.term_id.year + ' before you can delete the add/drop record for the term.'))
        self.write(cr, uid, ids, {'active': False}, context=context)
        return True                      

    def get_student_id(self, cr, uid, context=None):
        res = False
        if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student"):
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            res = user.partner_id.id
        return res

    def on_change_student_term(self, cr, uid, ids, student_id, term_id, field, context=None):          
        res = {}
        warning = {}
        if field == 'student_id':
            if student_id:
                student_obj = self.pool.get('res.partner')
                registration_hold = student_obj.get_holds(cr, uid, student_id)['registration']
                student = student_obj.browse(cr, uid, student_id)
                if registration_hold:
                    hold_names = ', '.join(list(set([hold.hold_id.name for hold in student.holds if hold.hold_id.registration and hold.is_active])))
                    warning = {'title': _('Hold Restriction!'), 'message': _('The following hold(s) are on this student\'s record: ' + hold_names)}
                    res['term_id'] = False
                    res['student_id'] = False

                res['fname'] = student.fname
                res['lname'] = student.lname
                res['image_medium'] = student.image_medium
            else:
                res['fname'] = False
                res['lname'] = False
                res['image_medium'] = False
            
        if field == 'term_id':
            res['sections'] = False
            res['section_ids'] = False
            if term_id:
                term = self.pool.get('aun.registrar.term').browse(cr, uid, term_id)
                if self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student") and term.admin_reg:
                    warning = {'title': _('Registration closed!'), 'message': _(term.term_name + ' is currently closed for registration.')}
                    res['term_id'] = False
                res['open_for_registration'] = term.open_for_registration
                res['admin_reg'] = term.admin_reg
                res['is_active'] = term.is_active
            else:
                res['open_for_registration'] = False
                res['admin_reg'] = False
                res['is_active'] = False
            
        overload_obj = self.pool.get('course.overload')
        overload_ids = overload_obj.search(cr, SUPERUSER_ID, [('student_id','=',student_id),('term_id','=',term_id),('state','=','approved')])
        if overload_ids:
            res['credits_allowed'] = overload_obj.browse(cr, uid, overload_ids[0]).credits_allowed
        else:
            res['credits_allowed'] = overload_obj.get_limits(cr, uid, student_id, term_id)['maximum_hours'][0]
        return {'value': res, 'warning': warning}

    def on_change_sections(self, cr, uid, ids, sections, labs, context=None):
        section_ids = sections[0][2]
        current_lab_ids = labs[0][2]
        lab_ids = []
        sections = self.pool.get('aun.registrar.section').browse(cr, uid, section_ids)
        total_credits = 0
        for section in sections:
            total_credits += section.credit_low
            labs = section.labs
            for lab in labs:
                if lab.mandatory or lab.id in current_lab_ids:
                    lab_ids.append(lab.id)
        return {'value': {'labs': [(6, 0, lab_ids)],'total_credits': total_credits}}

    def create_enrollments(self, cr, uid, student_id, section_id, lab_ids, context=None):
        enr_obj = self.pool.get('aun.registrar.enrollment')
        section_obj = self.pool.get('aun.registrar.section')
        lg_obj = self.pool.get('level.gpa')
        student = self.pool.get('res.partner').browse(cr, uid, student_id)
        level_gpa_id = lg_obj.search(cr, uid, [('student_id','=',student_id),('level_id','=',student.level_id.id),('admission_date','=',student.admission_date)])
        if level_gpa_id:
            level_gpa_id = level_gpa_id[0]
        else:
            other_lg_ids = lg_obj.search(cr, SUPERUSER_ID, [('student_id','=', student_id),('current','=',True)])
            lg_obj.write(cr, SUPERUSER_ID, other_lg_ids, {'current': False})
            level_gpa_id = lg_obj.create(cr, SUPERUSER_ID, {'student_id': student_id,
                                                            'level_id': student.level_id.id,
                                                            'admission_date': student.admission_date,
                                                            'term_admitted': student.term_admitted.id,
                                                            'major_ids': [(6, 0, [major.id for major in student.major_ids])],
                                                            'minor_ids': [(6, 0, [minor.id for minor in student.minor_ids])],
                                                            'conc_ids': [(6, 0, [conc.id for conc in student.concentration_ids])],
                                                            'student_state_id': student.student_state_id.id,
                                                            'date_of_state': student.date_of_state,
                                                            'current': True})
        section = section_obj.browse(cr, uid, section_id)
        parent_id = (enr_obj.search(cr, uid, [('section_id','=',section_id),
                                             ('student_id','=',student_id),
                                             ('state','=','registered'),
                                             ('level_gpa_id','=',level_gpa_id)])
                                             or
                     enr_obj.create(cr, uid, {'section_id': section_id,
                                 'student_id': student_id,
                                 'course_name': section.course_name,
                                 'credit': section.credit_low,
                                 'billing': section.billing_low,
                                 'grademode_id': section.grademode_id.id,
                                 'level_gpa_id': level_gpa_id})
                     )
        
        self.pool.get('aun.add.drop').check_credit_hours(cr, uid, student_id, section.term_id.id)
        if section.labs:
            section_lab_ids = [l.id for l in section.labs]
            mandatory_labs = []
            for lab in section.labs:
                if lab.mandatory and lab.id not in lab_ids:
                    mandatory_labs.append(lab.course_id.name + ' ' + lab.name)
            if mandatory_labs:
                raise osv.except_osv(_('Lab Restriction!'), _(', '.join(mandatory_labs) + [' is a mandatory lab', ' are mandatory labs'][len(mandatory_labs) > 1] + ' for ' + section.course_id.name))
            if len(list(set(section_lab_ids) & set(lab_ids))) != section.no_of_labs and section.no_of_labs != 0:
                raise osv.except_osv(_('Lab Restriction!'), _('You must pick ' + str(section.no_of_labs) + [' lab', ' labs'][section.no_of_labs > 1] + ' for ' + section.course_id.name))                 
            lab_obj = self.pool.get('section.lab')
            for lab_id in list(set(section_lab_ids) & set(lab_ids)):
                lab = lab_obj.browse(cr, uid, lab_id)
                (enr_obj.search(cr, uid, [('section_id','=',section_id),
                                             ('student_id','=',student_id),
                                             ('lab_id','=',lab.id),
                                             ('parent_id','=',parent_id[0] if type(parent_id) == list else parent_id),
                                             ('state','=','registered'),
                                             ('level_gpa_id','=',level_gpa_id)])
                                             or 
                    enr_obj.create(cr, uid, {'section_id': section_id,
                                             'student_id': student_id,
                                             'lab': True,
                                             'lab_id': lab.id,
                                             'credit': 0,
                                             'billing': 0,
                                             'grademode_id': section.grademode_id.id,
                                             'parent_id': parent_id[0] if type(parent_id) == list else parent_id,
                                             'course_name': lab.name,
                                             'level_gpa_id': level_gpa_id})
                )
        return {}

    def check_standing(self, cr, uid, student_id, context=None):
        student_obj = self.pool.get('res.partner')
        student = student_obj.browse(cr, uid, student_id, context=context)
        if student.standing_id:
            if student.standing_id.proh_reg:
                raise osv.except_osv(_('Standing Restriction!'), _(['The student\'s', 'Your'][self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student")] + ' current academic standing prohibits registration: ' + student.standing_id.name))
        return {}

    def check_repeat_limit(self, cr, uid, student_id, section_ids, context=None):
        student_obj = self.pool.get('res.partner')
        override_obj = self.pool.get('aun.registrar.override')
        section_obj = self.pool.get('aun.registrar.section')
        enr_obj = self.pool.get('aun.registrar.enrollment')
        lg_obj = self.pool.get('level.gpa')
        student = student_obj.browse(cr, uid, student_id, context=context)
        student_catalogue = student.catalogue_id
        sections = section_obj.browse(cr, uid, section_ids)
           
        res = []
        for section in sections:
            repeat_limits = section.course_id.repeat_limits
            if repeat_limits:
                override_repeat_limit = override_obj.search(cr, SUPERUSER_ID, [('override_repeat_limit','=',True),('student_id','=',student_id),('section_id','=',section.id),('state','=','approved')])
                if override_repeat_limit:
                    continue
                if student_catalogue:
                    latest_code = 0
                    latest_repeat_limit = []
                    for repeat_limit in repeat_limits:
                        if latest_code < repeat_limit.catalogue_id.code <= student_catalogue.code:
                            latest_repeat_limit = repeat_limit
                            latest_code = repeat_limit.catalogue_id.code
                    if latest_repeat_limit:
                        if latest_repeat_limit.limit:
                            level_gpa_id = lg_obj.search(cr, uid, [('student_id','=',student_id),('level_id','=',student.level_id.id),('admission_date','=',student.admission_date),('student_state_id','=',student.student_state_id.id),('current','=',True)])
                            if level_gpa_id:
                                level_gpa_id = level_gpa_id[0]
                            else:
                                raise osv.except_osv(_('Contact Registrar!'), _('Check Academic History'))
                            course_repeat_limit = latest_repeat_limit.limit
                            course_enrollment_ids = enr_obj.search(cr, uid, [('course_id','=',section.course_id.id),('student_id','=',student_id),('level_gpa_id','=',level_gpa_id),('state','=','registered'),('lab','=',False)])                    
                            if len(course_enrollment_ids) > int(course_repeat_limit):
                                res.append(section.course_id.name)
        if res:
            raise osv.except_osv(_('Repeat Limit Restriction!'), _(['The student has', 'You have'][self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student")] + ' reached the repeat limit for: ' + ', '.join(res)))
        
        return {}
  
#     def check_major(self, cr, uid, student_id, section_ids, context=None):
#         student_obj = self.pool.get('res.partner')
#         override_obj = self.pool.get('aun.registrar.override')
#         section_obj = self.pool.get('aun.registrar.section')
#         student = student_obj.browse(cr, uid, student_id, context=context)
#         sections = section_obj.browse(cr, uid, section_ids)
#         courses = []
#         for major in student.major_ids:
#             courses += list(set(major.course_ids + major.minor_course_ids))
#             for concentration in major.concentration_ids:
#                 courses = list(set(courses + concentration.course_ids))
#         for minor in student.minor_ids:
#             courses = list(set(courses + minor.minor_course_ids))
#         course_ids = [course.id for course in courses]
#                    
#         res = []
#         for section in sections:
#             override_major = override_obj.search(cr, SUPERUSER_ID, [('override_major','=',True),('student_id','=',student_id),('section_id','=',section.id),('state','=','approved')])
#             if section.course_id.id not in course_ids and not override_major:
#                 res.append(section.course_id.name)
#         if res:
#             raise osv.except_osv(_('Major Restriction!'), _('You cannot enroll for the following ' + ['course: ','courses: '][len(res) > 1] + ', '.join(res)))
#         
#         return {}
     
    def check_multiple_courses(self, cr, uid, student_id, term_id, section_ids, context=None):
        section_obj = self.pool.get('aun.registrar.section') 
        courses = [section_obj.browse(cr, uid, s).course_id.name for s in section_ids]
        if len(courses) != len(set(courses)):
            courses = collections.Counter(courses)
            duplicate_courses = [i for i in courses if courses[i] > 1]
            raise osv.except_osv(_('Course Restriction!'), _(['This course is', 'These courses are'][len(duplicate_courses) > 1] + ' duplicated in your add/drop: ' + ', '.join(duplicate_courses)))                             
        
        '''#check for ungraded enrollments in previous terms
        enr_obj = self.pool.get('aun.registrar.enrollment')
        sections = section_obj.browse(cr, uid, section_ids)
        ungraded_enr_ids = []
        for s in sections:
            enr_id = enr_obj.search(cr, uid, [('student_id','=',student_id),('term_id','not in',[term_id]),('course_id','=',s.course_id.id),('state','=','registered'),('grade','=',False),('lab','=',False)], context=context)
            if enr_id:
                ungraded_enr_ids.append(enr_id[0])
        if ungraded_enr_ids:
            ungraded_enrs = enr_obj.browse(cr, uid, ungraded_enr_ids)
            course_names = [enr.course_id.name for enr in ungraded_enrs]               
            raise osv.except_osv(_('Course Restriction!'), _('Your previous enrollment in the following ' + ['course has','courses have'][len(course_names) > 1] + ' not been graded: ' + ', '.join(course_names)))'''
        return {}
    
    def check_class_size(self, cr, uid, student_id, section_ids, lab_ids, context=None):
        enr_obj = self.pool.get('aun.registrar.enrollment')
        ad_obj = self.pool.get('add.drop.application')
        section_obj = self.pool.get('aun.registrar.section')
        override_obj = self.pool.get('aun.registrar.override')
        lab_obj = self.pool.get('section.lab')
        sections = section_obj.browse(cr, uid, section_ids)
        labs = lab_obj.browse(cr, uid, lab_ids)
        full_classes = []
        full_labs = []
        for s in sections:
            enr_id = enr_obj.search(cr, uid, [('student_id','=',student_id),('section_id','=',s.id),('state','=','registered')])
            add_drop_app_id = ad_obj.search(cr, uid, [('student_id','=',student_id),('section_id','=',s.id),('state','not in',['draft'])])
            override_class_size = override_obj.search(cr, SUPERUSER_ID, [('override_class_size','=',True),('student_id','=',student_id),('section_id','=',s.id),('state','=','approved')])
            if s.enrolled >= s.max_size and not (enr_id or add_drop_app_id or override_class_size):
                full_classes.append(s.course_id.name + ' (' + s.name + ')')
        if full_classes:
            raise osv.except_osv(_('Class Restriction!'), _(['This class is full: ', 'These classes are full: '][len(full_classes) > 1] + ', '.join(full_classes)))                             
        
        for l in labs:
            lab_enr_id = enr_obj.search(cr, uid, [('student_id','=',student_id),('lab_id','=',l.id),('state','=','registered')])
            add_drop_app_id = ad_obj.search(cr, uid, [('student_id','=',student_id),('section_id','=',l.section_id.id),('state','not in',['draft'])])
            if l.enrolled >= l.capacity and not (lab_enr_id or add_drop_app_id):
                full_labs.append(l.course_id.name + ' (' + l.name + ')')
        if full_labs:
            raise osv.except_osv(_('Lab Restriction!'), _(['This lab is full: ', 'These labs are full: '][len(full_labs) > 1] + ', '.join(full_labs)))
        
        return {}

    def check_level_and_status(self, cr, uid, student_id, section_ids, context=None):
        section_obj = self.pool.get('aun.registrar.section')
        override_obj = self.pool.get('aun.registrar.override')
        sections = section_obj.browse(cr, uid, section_ids)
        student = self.pool.get('res.partner').browse(cr, uid, student_id)      
        courses = []
        for s in sections:
            override_level = override_obj.search(cr, SUPERUSER_ID, [('override_level','=',True),('student_id','=',student_id),('section_id','=',s.id),('state','=','approved')])
            override_status = override_obj.search(cr, SUPERUSER_ID, [('override_status','=',True),('student_id','=',student_id),('section_id','=',s.id),('state','=','approved')])
            if s.level_id.id != student.level_id.id and not override_level:
                courses.append(s.course_id.name + ' (' + s.level_id.name + ' course)')
            elif s.status_id.range_start > student.status_id.range_start and not (override_level or override_status):
                courses.append(s.course_id.name + ' (' + s.status_id.name + ' course)')
        
        if courses:
            raise osv.except_osv(_('Status Restriction!'), _(['The student does not meet', 'You do not meet'][self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student")] + ' the status/level requirement(s) for ' + ', '.join(courses)))                             
        
        return {}

    def check_corequisites(self, cr, uid, student_id, section_ids, context=None):
        enr_obj = self.pool.get('aun.registrar.enrollment')
        course_obj = self.pool.get('aun.registrar.course')
        override_obj = self.pool.get('aun.registrar.override')
        student = self.pool.get('res.partner').browse(cr, uid, student_id)
        sections = self.pool.get('aun.registrar.section').browse(cr, uid, section_ids)
        course_ids = [s.course_id.id for s in sections]
        student_catalogue = student.catalogue_id
        
        res = []
        for section in sections:
            corequisites = section.course_id.corequisite_ids
            if corequisites:
                unmet_coreqs = []
                override_corequisite = override_obj.search(cr, SUPERUSER_ID, [('override_corequisite','=',True),('student_id','=',student_id),('section_id','=',section.id),('state','=','approved')])
                if override_corequisite:
                    continue
                if student_catalogue:
                    latest_code = 0
                    latest_corequisite = []
                    for corequisite in corequisites:
                        if latest_code < corequisite.catalogue_id.code <= student_catalogue.code:
                            latest_corequisite = corequisite
                            latest_code = corequisite.catalogue_id.code
                    if latest_corequisite:
                        coreqs = latest_corequisite.corequisites
                        coreq_ids = [c.id for c in coreqs]
                        for coreq_id in coreq_ids:
                            unmet = True
                            if coreq_id in course_ids:
                                unmet = False
                            else:
                                coreq_enr_ids = enr_obj.search(cr, uid, [('course_id','=',coreq_id),('student_id','=',student_id),('state','=','registered'),('repeat','not in',['E'])])
                                if coreq_enr_ids:
                                    for enr_id in coreq_enr_ids:
                                        coreq_enr = enr_obj.browse(cr, uid, enr_id)
                                        if coreq_enr.grade.passed:
                                            unmet = False
                            if unmet:
                                coreq = course_obj.browse(cr, uid, coreq_id)
                                unmet_coreqs.append(coreq.name)
                if unmet_coreqs:
                    res.append(section.course_id.name + ': ' + ', '.join(unmet_coreqs))                        
        
        if res:
            raise osv.except_osv(_('Corequisite Restriction'), _(['The student has not met', 'You have not met'][self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student")] + ' the corequisite(s) requirement for' + '\n' + '\n'.join(res)))
                                
        return {}

    def check_prerequisites(self, cr, uid, student_id, section_ids, context=None):
        student = self.pool.get('res.partner').browse(cr, uid, student_id)
        section_obj = self.pool.get('aun.registrar.section')
        enr_obj = self.pool.get('aun.registrar.enrollment')
        override_obj = self.pool.get('aun.registrar.override')
        student_catalogue = student.catalogue_id
        course_ids = [section_obj.browse(cr, uid, s).course_id.id for s in section_ids]
        
        settings_obj = self.pool.get('registrar.settings')
        settings_id = settings_obj.search(cr, SUPERUSER_ID, [])
        if not settings_id:
            raise osv.except_osv(_('Contact the Administrator!'), _('Settings has not been created!'))
        allow_prereq = settings_obj.browse(cr, SUPERUSER_ID, settings_id[0]).allow_prereq
              
        for section_id in section_ids:
            section = section_obj.browse(cr, uid, section_id)
            prerequisites = section.course_id.prerequisite_ids
            if prerequisites:
                override_prerequisite = override_obj.search(cr, SUPERUSER_ID, [('override_prerequisite','=',True),('student_id','=',student_id),('section_id','=',section.id),('state','=','approved')])
                if override_prerequisite:
                    continue
                if student_catalogue:
                    latest_code = 0
                    latest_prerequisite = []
                    for prerequisite in prerequisites:
                        if latest_code < prerequisite.catalogue_id.code <= student_catalogue.code:
                            latest_prerequisite = prerequisite
                            latest_code = prerequisite.catalogue_id.code
                    if latest_prerequisite:
                        statements = latest_prerequisite.prerequisite_ids
                        expr = ''
                        reqs = ''
                        for line in statements:
                            value = False
                            if line.prerequisite_id:
                                equivalents = line.prerequisite_id.equivalents
                                equivalent_ids = [e.id for e in equivalents]
                                equivalent_ids.append(line.prerequisite_id.id)      
                                enrollment_ids = enr_obj.search(cr, uid, [('course_id','in',equivalent_ids),('student_id','=',student_id),('state','=','registered'),('repeat','not in',['E'])])   
                                if enrollment_ids:
                                    for prereq_enrollment in enr_obj.browse(cr, uid, enrollment_ids):
                                        if prereq_enrollment.grade:
                                            if float(prereq_enrollment.grade.numeric_value) >= float(line.grade_requirement.numeric_value):
                                                value = True
                                                break
                                        elif allow_prereq and prereq_enrollment.term_id.start_date < section.term_id.start_date:
                                            value = True
                                            break
                                if not value:
                                    tce_obj = self.pool.get('transfer.course.equivalent')
                                    transfer_ids = tce_obj.search(cr, uid, [('student_id','=',student_id), ('course_id','in',equivalent_ids), ('repeat','not in',['E'])])
                                    if transfer_ids:
                                        for transfer in tce_obj.browse(cr, uid, transfer_ids):
                                            if float(transfer.grade_id.numeric_value) >= float(line.grade_requirement.numeric_value):
                                                value = True
                                                break
                                if not value:
                                    if line.concurrency and (set(equivalent_ids) & set(course_ids)):
                                        value = True
                            elif line.test_id:
                                if student.app_id:
                                    tr_obj = self.pool.get('test.result')
                                    result_ids = tr_obj.search(cr, SUPERUSER_ID, [('app_id','=',student.app_id.id),('test_id','=',line.test_id.id)])
                                    if result_ids:
                                        for res_id in result_ids:
                                            result = tr_obj.browse(cr, SUPERUSER_ID, res_id)
                                            if result.score == line.score:
                                                value = True
                                                break
                                            scores = result.score + ', ' + line.score
                                            sorted_scores = self.pool.get('test.code').sort_scores(scores)
                                            if sorted_scores[1].replace(' ','') == result.score:
                                                value = True
                                                break
                            reqs += '\n'
                            if line.andor:
                                expr += str(line.andor)
                                reqs += str(line.andor)
                                reqs += '\n'
                            if line.open:
                                expr += str(line.open)
                                reqs += str(line.open)
                            expr += str(value)
                             
                            done = ' \n*NOT SATISFIED*'
                            if value:
                                done = ' \n*SATISFIED*'
                                
                            if line.prerequisite_id:
                                reqs = reqs + line.prerequisite_id.name + '; Grade Required: ' + line.grade_requirement.name + done
                            elif line.test_id:
                                reqs = reqs + line.test_id.name + '; Score Required: ' + line.score + done
                            
                            if line.close:
                                expr += str(line.close)
                                reqs += str(line.close)
                                                      
                        expr = expr.replace('&', ' and ')
                        expr = expr.replace('|', ' or ')
                        reqs = reqs.replace('&', ' and ')
                        reqs = reqs.replace('|', ' or ')
                             
                        if not eval(expr):
                            raise osv.except_osv(_('Prerequisite Restriction'), _(['The student has not met', 'You have not met'][self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student")] + ' the prerequisite requirement for this course (' + section.course_id.name +  '): '  + reqs))
                else:
                    raise osv.except_osv(_('Catalogue Restriction!'), _(['The student has not been', 'You have not been'][self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student")] + ' been assigned a catalogue.'))              
        return {}

    def check_credit_hours(self, cr, uid, student_id, term_id, context=None):
        overload_obj = self.pool.get('course.overload')
        enr_obj = self.pool.get('aun.registrar.enrollment')
        enr_ids = enr_obj.search(cr, SUPERUSER_ID, [('term_id','=',term_id),('student_id','=',student_id),('state','=','registered')])
        enr_credits = [e.credit for e in enr_obj.browse(cr, SUPERUSER_ID, enr_ids)]
        total_credits = sum(enr_credits)
        overload_id = overload_obj.search(cr, SUPERUSER_ID, [('term_id','=',term_id),('student_id','=',student_id),('state','=','approved')])
        if overload_id:
            overload = overload_obj.browse(cr, SUPERUSER_ID, overload_id)[0]
            if total_credits > overload.credits_allowed:
                raise osv.except_osv(_('Overload Limit!'), _('You cannot exceed the credit hours on your overload: ' + '{0:.2f}'.format(overload.credits_allowed) + ' Credit Hours'))                  
        else:
            limits = overload_obj.get_limits(cr, SUPERUSER_ID, student_id, term_id)
            limit_max = limits['maximum_hours'][0]
            max_source = limits['maximum_hours'][1]
#             limit_min = limits['minimum_hours'][0]
#             min_source = limits['minimum_hours'][1]
            if total_credits > limit_max:
                raise osv.except_osv(_('Credit Hour Limit!'), _('You cannot exceed the credit hour limit for ' + max_source + ': ' + '{0:.2f}'.format(limit_max) + ' Credit Hours'))
#             if total_credits < limit_min:
#                 raise osv.except_osv(_('Credit Hour Limit!'), _(['The student', 'You'][self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student")] + ' cannot take less than the credit hour limit for ' + min_source + ': ' + '{0:.2f}'.format(limit_min) + ' Credit Hours'))
        return {}

    def check_time_conflict(self, cr, uid, student_id, section_ids, lab_ids, context=None):
        override_obj = self.pool.get('aun.registrar.override')
        section_obj = self.pool.get('aun.registrar.section')
        sections = section_obj.browse(cr, uid, section_ids)
        sections = [s for s in sections if s.duration_id and not override_obj.search(cr, SUPERUSER_ID, [('override_time_conflict','=',True),('student_id','=',student_id),('section_id','=',s.id),('state','=','approved')])]
        lab_obj = self.pool.get('section.lab')
        labs = lab_obj.browse(cr, uid, lab_ids)
        labs = [l for l in labs if l.duration_id and not override_obj.search(cr, SUPERUSER_ID, [('override_time_conflict','=',True),('student_id','=',student_id),('section_id','=',l.section_id.id),('state','=','approved')])]
        sections_and_labs = sections + labs
        settings_obj = self.pool.get('registrar.settings')
        settings_id = settings_obj.search(cr, SUPERUSER_ID, [])
        if not settings_id:
            raise osv.except_osv(_('Contact the Administrator!'), _('Settings has not been created!'))
        interval = settings_obj.browse(cr, SUPERUSER_ID, settings_id[0]).interval
        conflicts = []
        for s in sections_and_labs:
            d = s.duration_id.name
            for ss in sections_and_labs:
                if s.id != ss.id:
                    dd = ss.duration_id.name
                    d_coll = collections.Counter(d[:-14])
                    dd_coll = collections.Counter(dd[:-14])
                    common = d_coll & dd_coll
                    if common:
                        t = d[-13:].replace(':','').split()
                        tt = dd[-13:].replace(':','').split()
                        t.remove("-")
                        tt.remove("-")
                        t = map(int, t)
                        tt = map(int, tt)
                        if (tt[0] < t[0]-interval < tt[1]) or (tt[0] < t[1]+interval < tt[1]) or (t[0]==tt[0] and t[1]==tt[1]):
                            if ss._table_name == 'section.lab' and s._table_name == 'aun.registrar.section':
                                if (ss.course_id.name + '(' + ss.name + ')' + ' & ' + s.course_id.name) not in conflicts: 
                                    conflicts.append(s.course_id.name + ' & ' + ss.course_id.name + '(' + ss.name + ')')
                            elif ss._table_name == 'aun.registrar.section' and s._table_name == 'section.lab':
                                if (ss.course_id.name + ' & ' + s.course_id.name + '(' + s.name + ')') not in conflicts: 
                                    conflicts.append(s.course_id.name + '(' + s.name + ')' + ' & ' + ss.course_id.name)
                            elif ss._table_name == 'section.lab' and s._table_name == 'section.lab':
                                if (ss.course_id.name + '(' + ss.name + ')' + ' & ' + s.course_id.name + '(' + s.name + ')') not in conflicts: 
                                    conflicts.append(s.course_id.name + '(' + s.name + ')' + ' & ' + ss.course_id.name + '(' + ss.name + ')')
                            elif ss._table_name == 'aun.registrar.section' and s._table_name == 'aun.registrar.section':
                                if (ss.course_id.name + ' & ' + s.course_id.name) not in conflicts:
                                    conflicts.append(s.course_id.name + ' & ' + ss.course_id.name)
                                
        if conflicts:                        
            raise osv.except_osv(_('Time Conflict!'), _('The following courses conflict on this add drop: ' + '\n' + '\n'.join(conflicts)))
        
        return True

    def _check_student_state(self, cr, uid, ids, context=None):
        state = self.browse(cr, uid, ids,context=context)[0].student_id.student_state_id
        if state.proh_reg:
            raise osv.except_osv(_('Status Restriction!'), _(['The student\'s current status', 'Your current student status'][self.pool.get('ir.model.access').check_groups(cr, uid, "academics.group_registrar_student")] + ' prohibits add/drop: ' + state.name))
        return True
    
    def _check_multiple_add_drop(self, cr, uid, ids, context=None):
        add_drop = self.browse(cr, uid, ids, context=context)[0]
        if self.search(cr, uid, [('student_id','=',add_drop.student_id.id),('term_id','=',add_drop.term_id.id),('active','=',True)], count=True) > 1:
            raise osv.except_osv(_('Multiple Add/Drop!'), _('You already have an add/drop form for ' + add_drop.term_id.term_name + '. Click on the record and click edit to add or drop classes.'))
        return True

    def _get_sections(self, cursor, uid, ids, name, arg, context=None):
        res = {}
        for add_drop in self.browse(cursor, uid, ids, context=context):
            res[add_drop.id] = {}
            res[add_drop.id]['sections_list'] = [(6, 0, [s.id for s in add_drop.sections])]
            res[add_drop.id]['labs_list'] = [(6, 0, [l.id for l in add_drop.labs])]
            res[add_drop.id]['sections_bool'] = True if add_drop.sections else False
            res[add_drop.id]['labs_bool'] = True if add_drop.labs else False
        return res
    
    def _get_credits(self, cr, uid, ids, name, arg, context=None):
        overload_obj = self.pool.get('course.overload')
        enr_obj = self.pool.get('aun.registrar.enrollment')
        res = {}
        for add_drop in self.browse(cr, uid, ids, context=context):
            res[add_drop.id] = {}
            student_id = add_drop.student_id.id
            term_id = add_drop.term_id.id
            overload_ids = overload_obj.search(cr, SUPERUSER_ID, [('student_id','=',student_id),('term_id','=',term_id),('state','=','approved')])
            if overload_ids:
                res[add_drop.id]['credits_allowed'] = overload_obj.browse(cr, uid, overload_ids[0]).credits_allowed
            else:
                res[add_drop.id]['credits_allowed'] = overload_obj.get_limits(cr, uid, student_id, term_id)['maximum_hours'][0]
            
            total_credits = 0
            enr_ids = enr_obj.search(cr, SUPERUSER_ID, [('student_id','=',student_id),('term_id','=',term_id),('state','=','registered'),('repeat','not in',['E'])])
            for enr in enr_obj.browse(cr, SUPERUSER_ID, enr_ids):
                total_credits += enr.credit
            res[add_drop.id]['total_credits'] = total_credits
         
        return res
            
    _columns={
          'student_id': fields.many2one('res.partner', 'Student ID', required=True, domain=[('student','=',True)], track_visibility="onchange"),
          'term_id': fields.many2one('aun.registrar.term', 'Term', required=True, domain=['|',('admin_reg','=',True),('open_for_registration','=',True)], track_visibility="onchange"),  #'|',('is_active','=',True)
          'major_ids': fields.related('student_id', 'major_ids', type='many2many', relation="aun.registrar.major", string='Major(s)', readonly=True, store=False),
          'minor_ids': fields.related('student_id', 'minor_ids', type='many2many', relation="aun.registrar.major", string='Minor(s)', readonly=True, store=False),
          'concentration_ids': fields.related('student_id', 'concentration_ids', type='many2many', relation="aun.registrar.major", string='Concentration(s)', readonly=True, store=False),
          'school_ids': fields.related('student_id', 'schools', type='many2many', relation="aun.registrar.school", string='School(s)', readonly=True, store=False),
          'sections': fields.many2many('aun.registrar.section', 'rel_add_drop_section','add_drop_id','section_id','Section(s)', track_visibility="onchange"),
          'labs': fields.many2many('section.lab', 'rel_add_drop_lab','add_drop_id','lab_id','Lab(s)', track_visibility="onchange"),
          'section_ids': fields.one2many('add.drop.application', 'add_drop_id', 'Sections'),
          'fname': fields.related('student_id', 'fname', type='char', relation='res.partner', string='First Name', readonly=True, store=False),
          'lname': fields.related('student_id', 'lname', type='char', relation='res.partner', string='Last Name', readonly=True, store=False),
          'sections_list': fields.function(_get_sections, string='Your courses', type='many2many', method=True, multi='add_drop', store=False, relation='aun.registrar.section'),
          'labs_list': fields.function(_get_sections, string='Your labs', type='many2many', method=True, multi='add_drop', store=False, relation='section.lab'),
          'sections_bool': fields.function(_get_sections, string='Sections', type='boolean', method=True, multi='add_drop', store=False),
          'labs_bool': fields.function(_get_sections, string='Labs', type='boolean', method=True, multi='add_drop', store=False),
          'state': fields.selection(ADD_DROP_STATES, 'State'),
          'credits_allowed': fields.function(_get_credits, string='Credits Allowed', type='float', multi='credits', method=True, store=False),
          'total_credits': fields.function(_get_credits, string='Total Credits Added', type='float', multi='credits', method=True, store=False),
          'open_for_registration': fields.related('term_id', 'open_for_registration', type='boolean', string='Open for registration', readonly=True, store=False),
          'is_active': fields.related('term_id', 'is_active', type='boolean', string='Active', readonly=True, store=False),
          'admin_reg': fields.related('term_id', 'admin_reg', type='boolean', string='Admin Reg', readonly=True, store=False),
          'image_medium': fields.related('student_id', 'image_medium', type='binary', readonly=True, string='Image', store=False),
          'create_date': fields.datetime('Creation Date', readonly=True, select=True),
          'active': fields.boolean('Active')
        }
    _defaults={
        'student_id': get_student_id,
        'state': 'draft',
        'active': True
        }
    
    _constraints =[
        (_check_student_state, 'Your current student status prohibits registration!',['Student Status']),
        (_check_multiple_add_drop, 'You cannot create multiple add/drop in the same term', ['Add/Drop'])
    ]
    
aun_add_drop


class aun_student_finalgrades(osv.osv):
    _name = "aun.student.finalgrades"
    _description = "Final Grades"
    _inherit = ["mail.thread"]

#     def _get_enrollment_gpa_info(self, cursor, uid, ids, name, arg, context=None):     
#         res = {} 
#         for finalgrade in self.browse(cursor, SUPERUSER_ID, ids, context=context):
#             res[finalgrade.id] = {}
#             res[finalgrade.id]['attempted'] = [0, finalgrade.enrollment_id.credit][finalgrade.grade.attempted]
#             res[finalgrade.id]['earned'] = [0, finalgrade.enrollment_id.credit][finalgrade.grade.earned and finalgrade.repeat != 'E']
#             res[finalgrade.id]['gpa'] = [0, finalgrade.enrollment_id.credit][finalgrade.grade.gpa and finalgrade.repeat != 'E']
#             res[finalgrade.id]['quality_points'] = [0, finalgrade.grade.quality_points * finalgrade.enrollment_id.credit][finalgrade.repeat != 'E']
#         return res
    
    _columns = {
        'enrollment_id':fields.many2one('aun.registrar.enrollment', 'Enrollment', required=True, ondelete="cascade"),
        'section_id': fields.related('enrollment_id', 'section_id', type='many2one', relation="aun.registrar.section", string="Section", store=True, readonly=True),
        'course_id': fields.related('enrollment_id', 'course_id', type='many2one', relation="aun.registrar.course", string="Course", store=True, readonly=True),
        'course_name': fields.related('enrollment_id', 'course_name', type='char', string="Title", store=True, readonly=True),        
        'credit': fields.related('enrollment_id', 'credit', type='float', string="Hours", store=False, readonly=True),
        'term_id': fields.related('enrollment_id', 'term_id', type='many2one', relation="aun.registrar.term", string="Term", store=True, readonly=True),
        'faculty': fields.related('enrollment_id', 'faculty_emp_ids', type='many2many', relation="hr.employee", string="Faculty", store=False, readonly=True),
        'student_id': fields.related('enrollment_id', 'student_id', type='many2one', relation="res.partner", string="Student ID", store=True, readonly=True),
        'grade': fields.related('enrollment_id', 'grade', type='many2one', relation="aun.registrar.grade", string="Grade", store=False, readonly=True),
        'duration_id': fields.related('enrollment_id', 'duration_id', type='many2one', relation="aun.registrar.duration", string="Time", store=True),
        'repeat': fields.related('enrollment_id', 'repeat', type='char', string="Repeat", store=False, readonly=True),
#         'attempted': fields.function(_get_enrollment_gpa_info, string='Attempted', type='float', method=True, multi='enr_gpa_info', store=False, help='Attempted Hours'),
#         'earned': fields.function(_get_enrollment_gpa_info, string='Earned', type='float', method=True, multi='enr_gpa_info', store=False, help='Earned Hours'),
#         'gpa': fields.function(_get_enrollment_gpa_info, string='GPA', type='float', method=True, multi='enr_gpa_info', store=False, help='GPA Hours'),
#         'quality_points': fields.function(_get_enrollment_gpa_info, string='Quality Points', type='float', method=True, multi='enr_gpa_info', store=False, help='Quality Points'),
    }
    
    def fields_get(self, cr, uid, fields=None, context=None):
        res = super(aun_student_finalgrades, self).fields_get(cr, uid, fields, context)
        student_obj = self.pool.get('res.partner')
        student_id = student_obj.search(cr, SUPERUSER_ID, [('user_ids','in',uid),('student','=',True)])
        if student_id:
            grade_hold = student_obj.get_holds(cr, SUPERUSER_ID, student_id[0])['grades']
            if grade_hold:
                holds = student_obj.browse(cr, uid, student_id[0], context=context).holds
                hold_names = ', '.join([hold.hold_id.name for hold in holds if hold.hold_id.grades and hold.is_active])
                raise osv.except_osv(_('Hold Restriction!'), _('You have theee following hold(s) on your record: ' + hold_names))                   
        return res

aun_student_finalgrades()


class level_gpa(osv.osv):
    _name = "level.gpa"
    _description = "Student Level GPA"
    
    #gpa_info is ordered by term DESC
    def _get_latest_gpa_info(self, cr, uid, ids, name, arg, context=None):
        res = {}
        gi_obj = self.pool.get('gpa.info')
        term_obj = self.pool.get('aun.registrar.term')
        for gpa in self.browse(cr, uid, ids):
            res[gpa.id] = {}
            total_credits = 0.0
            res[gpa.id]['o_attempted_hours'] = 0.0
            res[gpa.id]['o_passed_hours'] = 0.0
            res[gpa.id]['o_earned_hours'] = 0.0
            res[gpa.id]['o_quality_points'] = 0.0
            res[gpa.id]['o_gpa_hours'] = 0.0
            res[gpa.id]['o_cgpa'] = 0.0
            info_ids = gi_obj.search(cr, uid, [('student_id','=',gpa.student_id.id),('level_gpa_id','=',gpa.id)])
            res[gpa.id]['latest_gpa_info_id'] = info_ids[0] if info_ids else False
            res[gpa.id]['transfer'] = False
                
            if info_ids:
                infos = gi_obj.browse(cr, uid, info_ids)
                if self.pool.get('transfer.course.equivalent').search(cr, uid, [('student_id','=',gpa.student_id.id)]):
                    res[gpa.id]['transfer'] = True
                gpa_info = infos[0]
                res[gpa.id]['o_attempted_hours'] = gpa_info.c_attempted_hours + gpa_info.tc_attempted_hours
                res[gpa.id]['o_passed_hours'] = gpa_info.c_passed_hours + gpa_info.tc_passed_hours
                res[gpa.id]['o_earned_hours'] = gpa_info.c_earned_hours + gpa_info.tc_earned_hours
                res[gpa.id]['o_quality_points'] = gpa_info.c_quality_points + gpa_info.tc_quality_points
                res[gpa.id]['o_gpa_hours'] = gpa_info.c_gpa_hours + gpa_info.tc_gpa_hours
                res[gpa.id]['o_cgpa'] = float(gi_obj.get_term_gpa(cr, uid, gpa_info.c_quality_points + gpa_info.tc_quality_points, gpa_info.c_gpa_hours + gpa_info.tc_gpa_hours))
                total_credits = gpa_info.tc_earned_hours + gpa_info.c_earned_hours
            settings_obj = self.pool.get('registrar.settings')
            settings_id = settings_obj.search(cr, SUPERUSER_ID, [])
            if not settings_id:
                raise osv.except_osv(_('Contact the Administrator!'), _('Settings has not been created!'))
            include_current_hrs = settings_obj.browse(cr, SUPERUSER_ID, settings_id[0]).include_current_hrs
            if include_current_hrs:
                enr_obj = self.pool.get('aun.registrar.enrollment')
                active_enr_ids = []
                active_term_ids = term_obj.search(cr, uid, [('is_active','=',True)])
                for active_term_id in active_term_ids:
                    active_enr_ids += enr_obj.search(cr, uid, [('student_id','=',gpa.student_id.id),('term_id','=',active_term_id),('grade','=',False),('state','=','registered')])
                for enr in enr_obj.browse(cr, uid, active_enr_ids):
                    if enr.section_id.level_id.id == gpa.level_id.id:
                        total_credits += enr.credit

            res[gpa.id]['total_credits'] = total_credits
        return res

    def _get_schools_and_programs(self, cr, uid, ids, name, arg, context=None):
        res = {}
        student_obj = self.pool.get('res.partner')
        for lg in self.browse(cr, SUPERUSER_ID, ids, context=None):
            res[lg.id] = {}
            student_id = lg.student_id.id
            school_ids = student_obj.browse(cr, SUPERUSER_ID, student_id)._get_schools_and_programs(cr, SUPERUSER_ID)[student_id]['school_ids'][0][2]
            program_ids = student_obj.browse(cr, SUPERUSER_ID, student_id)._get_schools_and_programs(cr, SUPERUSER_ID)[student_id]['program_ids'][0][2]
            res[lg.id]['school_ids'] = [(6, 0, school_ids)]
            res[lg.id]['program_ids'] = [(6, 0, program_ids)]
        return res

    _columns = {
        'student_id': fields.many2one('res.partner', 'Student', required=True),
        'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, readonly=True),
        'admission_date': fields.date('Date Admitted', required=True, readonly=True),
        'term_admitted': fields.many2one('aun.registrar.term', 'Term Admitted', readonly=True),
        'major_ids': fields.many2many('aun.registrar.major', 'rel_level_gpa_major', 'level_gpa_id', 'major_id', 'Major(s)', readonly=True),
        'minor_ids': fields.many2many('aun.registrar.major', 'rel_level_gpa_minor', 'level_gpa_id', 'minor_id', 'Minor(s)', readonly=True),
        'conc_ids': fields.many2many('aun.registrar.major', 'rel_level_gpa_conc', 'level_gpa_id', 'conc_id', 'Concentration(s)', readonly=True),
        'school_ids':fields.function(_get_schools_and_programs, string='School(s)', type='many2many', method=True, multi='program_info', relation='aun.registrar.school', store=False),
        'program_ids': fields.function(_get_schools_and_programs, string='Program(s)', type='many2many', method=True, multi='program_info', relation='registrar.program', store=False),
        'catalogue_id': fields.many2one('aun.registrar.catalogue', 'Catalog', readonly=True),
        'graduation_class': fields.char('Graduation Class', readonly=True),
        'latest_gpa_info_id': fields.function(_get_latest_gpa_info, type='many2one', method=True, string='Latest GPA Info', multi='gpa_info', relation='gpa.info', store=False),
        'attempted_hours': fields.related('latest_gpa_info_id', 'c_attempted_hours', type='float', string='Attempted Hours', store=False, readonly=True),
        'passed_hours': fields.related('latest_gpa_info_id', 'c_passed_hours', type='float', string='Passed Hours', store=False, readonly=True),
        'earned_hours': fields.related('latest_gpa_info_id', 'c_earned_hours', type='float', string='Earned Hours', store=False, readonly=True),
        'quality_points': fields.related('latest_gpa_info_id', 'c_quality_points', type='float', string='Quality Points', store=False, readonly=True),
        'gpa_hours': fields.related('latest_gpa_info_id', 'c_gpa_hours', type='float', string='GPA Hours', store=False, readonly=True),
        'cgpa': fields.related('latest_gpa_info_id', 'cgpa', type='float', string='CGPA', store=False, readonly=True),
        't_attempted_hours': fields.related('latest_gpa_info_id', 'tc_attempted_hours', type='float', string='Attempted Hours', store=False, readonly=True),
        't_passed_hours': fields.related('latest_gpa_info_id', 'tc_passed_hours', type='float', string='Passed Hours', store=False, readonly=True),
        't_earned_hours': fields.related('latest_gpa_info_id', 'tc_earned_hours', type='float', string='Earned Hours', store=False, readonly=True),
        't_quality_points': fields.related('latest_gpa_info_id', 'tc_quality_points', type='float', string='Quality Points', store=False, readonly=True),
        't_gpa_hours': fields.related('latest_gpa_info_id', 'tc_gpa_hours', type='float', string='GPA Hours', store=False, readonly=True),
        't_cgpa': fields.related('latest_gpa_info_id', 'tcgpa', type='float', string='CGPA', store=False, readonly=True),        
        'o_attempted_hours': fields.function(_get_latest_gpa_info, type='float', method=True, string='Attempted Hours', multi='gpa_info', store=False),
        'o_passed_hours': fields.function(_get_latest_gpa_info, type='float', method=True, string='Passed Hours', multi='gpa_info', store=False),
        'o_earned_hours': fields.function(_get_latest_gpa_info, type='float', method=True, string='Earned Hours', multi='gpa_info', store=False),
        'o_quality_points': fields.function(_get_latest_gpa_info, type='float', method=True, string='Quality Points', multi='gpa_info', store=False),
        'o_gpa_hours': fields.function(_get_latest_gpa_info, type='float', method=True, string='GPA Hours', multi='gpa_info', store=False),
        'o_cgpa': fields.function(_get_latest_gpa_info, type='float', method=True, string='CGPA', multi='gpa_info', store=False),
        'total_credits': fields.function(_get_latest_gpa_info, type='float', method=True, string='Total Credits', multi='gpa_info', store=False),
        'student_state_id': fields.many2one('student.state', 'State', readonly=True, track_visibility="onchange"),
        'date_of_state': fields.date('Date', readonly=True),
        'transfer': fields.function(_get_latest_gpa_info, type='boolean', method=True, multi='gpa_info', string='Transfer', store=False),
        'current': fields.boolean('Current', readonly=True),
        'graduated': fields.related('student_state_id', 'graduated', type='boolean', string='Graduated', store=False),
        'is_active': fields.related('student_state_id', 'is_active', type='boolean', string='Active', store=False)
    }
    
    def _check_current_level(self, cr, uid, ids, context=None):
        student_id = self.browse(cr, uid, ids)[0].student_id.id
        if self.search(cr, uid, [('student_id','=',student_id),('current','=',True)], count=True) > 1:
            return False
        return True
    
    _constraints = [
        (_check_current_level, 'A student cannot have more than one current level gpa.', ['Level GPA'])
    ]

level_gpa()



class aun_registrar_enrollment(osv.osv):
    _name = "aun.registrar.enrollment"
    _description = "Enrollment"
    _inherit = ["mail.thread"]
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        for record in reads:
            name = record.student_id.name + '/' + record.section_id.name
            res.append((record['id'], name))
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        enrollments = self.browse(cr, uid, ids, context=context)
        for enr in enrollments:
            if enr.lab:
                if enr.parent_id.id not in [e.id for e in enrollments if not e.lab]:
                    if enr.parent_id.state == 'registered':
                        raise osv.except_osv(_('Invalid action!'), _("Drop the class to automatically drop the lab or drop it from the add/drop form if it is not a 'mandatory' lab."))
            else:
                if enr.grade:
                    raise osv.except_osv(_('Invalid action!'), _('You cannot drop a course that has already been assigned a grade.'))
                
                if not enr.term_id.admin_reg:
                    if not enr.term_id.open_for_registration and ((context is not None and not context.get('drop')) or context is None):
                        raise osv.except_osv(_('Term Restriction!'), _('This term is currently closed for registration.'))

                if enr.state == 'registered':
                    add_drop_obj = self.pool.get('aun.add.drop')
                    add_drop_id = add_drop_obj.search(cr, uid, [('term_id','=',enr.term_id.id),('student_id','=',enr.student_id.id)], context=context)
                    lab_enr_ids = self.search(cr, uid, [('parent_id','=',enr.id),('state','=','registered')])
                    lab_enrs = self.browse(cr, uid, lab_enr_ids)
                    for lab_enr in lab_enrs:
                        super(aun_add_drop, add_drop_obj).write(cr, uid, add_drop_id, {'labs': [(3, lab_enr.lab_id.id)]}, context=context)
                    super(aun_add_drop, add_drop_obj).write(cr, uid, add_drop_id, {'sections': [(3, enr.section_id.id)]}, context=context)
                    
                    # Cancel or Refund Invoice
                    self.refund_student(cr, uid, [enr.id])
                    if not context.get('delete'):
                        lab_enr_ids = self.search(cr, uid, [('parent_id','=',enr.id),('state','=','registered')])
                        self.write(cr, SUPERUSER_ID, [enr.id], {'state': 'dropped', 'active': False}, context=context)
                        super(aun_registrar_enrollment, self).write(cr, SUPERUSER_ID, lab_enr_ids, {'state': 'dropped', 'active': False}, context=context)

                #delete any approved add applications for the section
                ad_obj = self.pool.get('add.drop.application')
                ad_obj.unlink(cr, uid, ad_obj.search(cr, uid, [('student_id','=',enr.student_id.id),('section_id','=',enr.section_id.id),('action','=','add'),('state','=','approved')]), context=dict(delete_approved = True))
                
                if context.get('delete'):
                    lab_enr_ids = self.search(cr, uid, [('parent_id','=',enr.id)])
                    self.write(cr, uid, ids, {'state': 'deleted', 'active': False}, context=context)
                    super(aun_registrar_enrollment, self).write(cr, uid, lab_enr_ids, {'state': 'deleted', 'active': False}, context=context)
                self._update_gpa_info(cr, uid, enr.id)
        return True

    def refund_student(self, cr, uid, ids, context=None):
#         COMMENT
        enr = self.browse(cr, uid, ids, context=context)[0]
        charge_obj = self.pool.get('term.charges')
        for charge in enr.charge_ids:
            charge_obj.unlink(cr,SUPERUSER_ID,[charge.id])
        return True
    
    def on_change_repeat(self, cr, uid, ids, repeat, course_id, grade, context=None):
        course = self.pool.get('aun.registrar.course').browse(cr, uid, course_id)
        if repeat and not grade:
            return {'value': {'repeat': False}, 'warning': {'title': _('No grade'), 'message': _('No grade has been entered for this enrollment!')}}
        if repeat == 'I' and not course.exclude:
            enrollment = self.browse(cr, uid, ids, context=context)[0]
            tce_obj = self.pool.get('transfer.course.equivalent')
            transfer_ids = tce_obj.get_transfer_equiv_ids(cr, uid, False, enrollment.student_id, course_id)
            equiv_enr_ids = self.get_equiv_enr_ids(cr, uid, enrollment, False, False, False, True)

            res = repeat
            warning = {}
            if not(transfer_ids or equiv_enr_ids):
                res = False
                warning = {
                        'title': _('Invalid '),
                        'message': _('There is only one enrollment for this course.')
                        }
            return {'value': {'repeat': res}, 'warning': warning}
        else:
            return {}
        
    def on_change_grade(self, cr, uid, ids, grade, context=None):
        if not grade:
            return {'value': {'repeat': False}}
        enrollment = self.browse(cr, uid, ids, context=context)[0]
        old_grade = enrollment.grade
        new_grade = self.pool.get('aun.registrar.grade').browse(cr,uid,grade)
        warning = False
        if (not old_grade and new_grade.refund) or (old_grade.refund == False and new_grade.refund):
            warning = {
                'title': _('Warning '),
                'message': _("This action will refund this student's tuition for this course using the bursar refund rules")
                }
        if (old_grade.refund and not grade) or (old_grade.refund and new_grade.refund == False):
            warning = {
                'title': _('Warning '),
                'message': _("This action will charge this student the full tuition fee for this course.")
                }
        if warning:
            return {'warning': warning}
        return True

    def write(self, cr, uid, ids, vals, context=None):
        enrollment = self.browse(cr, uid, ids, context=context)[0]
        tce_obj = self.pool.get('transfer.course.equivalent')
        student_id = enrollment.student_id.id
        course_id = enrollment.section_id.course_id.id
        transfer_ids = tce_obj.get_transfer_equiv_ids(cr, uid, False, enrollment.student_id, course_id)
        equiv_enr_ids = self.get_equiv_enr_ids(cr, uid, enrollment, False, False, False, True)
        
        if 'grade' in vals and vals['grade']:
            old_grade = enrollment.grade
            new_grade = self.pool.get('aun.registrar.grade').browse(cr,uid,vals['grade'])
            if (not old_grade and new_grade.refund) or (old_grade.refund == False and new_grade.refund):
                self.refund_student(cr, uid, [enrollment.id])
                for charge in enrollment.charge_ids:
                    super(aun_registrar_enrollment, self).write(cr, uid, ids, {'charge_ids': [(1,charge,{'enrollment_id': False})]})
            if (old_grade.refund and not vals['grade']) or (old_grade.refund and new_grade.refund == False):
                self.charge_student(cr, uid, [enrollment.id])
        if 'billing' in vals:
            dif = vals['billing'] - enrollment.billing
            self.charge_student(cr, uid, [enrollment.id],dif)
        if 'repeat' in vals:
            repeat = vals['repeat']
            if repeat == 'I':
                if not(transfer_ids or equiv_enr_ids):
                    raise osv.except_osv(_('Invalid'), _('There is only one enrollment for this course. It is included automatically.'))
                if not enrollment.section_id.course_id.exclude:
                    super(aun_registrar_enrollment, self).write(cr, uid, equiv_enr_ids, {'repeat': 'E'})
                    super(transfer_course_equivalent, tce_obj).write(cr, uid, transfer_ids, {'repeat': 'E'})
                    for enrollment_id in equiv_enr_ids:
                        self._update_gpa_info(cr, uid, enrollment_id)
                    for transfer_id in transfer_ids:
                        tce_obj._update_gpa_info(cr, uid, transfer_id)
        else:
            repeat = enrollment.repeat
           
        #repeat is only set automatically for the latest enrollment on grade entry (only if no grade prior to entry)
        if not repeat and not enrollment.section_id.course_id.exclude:
            if not enrollment.grade and 'grade' in vals:
                latest_enrollment = True
                if transfer_ids or equiv_enr_ids:
                    enrollments = self.browse(cr, uid, equiv_enr_ids) if equiv_enr_ids else []
                    transfers = tce_obj.browse(cr, uid, transfer_ids) if transfer_ids else []
                    for enr in enrollments + transfers:
                        if enr.term_id.code > enrollment.term_id.code:
                            latest_enrollment = False
                    if latest_enrollment:
                        vals['repeat'] = 'I'
                        super(aun_registrar_enrollment, self).write(cr, uid, equiv_enr_ids, {'repeat': 'E'})
                        super(transfer_course_equivalent, tce_obj).write(cr, uid, transfer_ids, {'repeat': 'E'})
                        for enrollment_id in equiv_enr_ids:
                            self._update_gpa_info(cr, uid, enrollment_id)
                        for transfer_id in transfer_ids:
                            tce_obj._update_gpa_info(cr, uid, transfer_id)
           
        res = super(aun_registrar_enrollment, self).write(cr, uid, ids, vals, context=context)
        self.pool.get('aun.add.drop').check_credit_hours(cr, uid, student_id, enrollment.term_id.id)
        if 'grade' in vals or 'credit' in vals or 'repeat' in vals or 'state' in vals:
            self._update_gpa_info(cr, uid, ids[0])
        return res
    
    def on_change_grademode(self, cr, uid, ids, grademode_id, grade_id, midterm_grade_id, context=None):
        res = {}
        if not grademode_id:
            return res
        grade_obj = self.pool.get('aun.registrar.grade')
        if grade_id:
            grade = grade_obj.browse(cr, uid, grade_id)
            if grade.grademode_id.id != grademode_id:
                res['grade'] = False
        if midterm_grade_id:
            midterm_grade = grade_obj.browse(cr, uid, midterm_grade_id)
            if midterm_grade.grademode_id.id != grademode_id:
                res['midterm_grade'] = False
        return {'value': res}
 
    def permanent_delete(self, cr, uid, ids, context=None):
        enrollment = self.browse(cr, uid, ids, context=context)[0]
        ctx = dict(delete = True)
        self.unlink(cr, uid, [enrollment.id], context=ctx)
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'academics', 'registrar_academic_history')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        return result

    def get_equiv_enr_ids(self, cr, uid, enrollment, student, course_id, use_term, check_course, context=None):
        if enrollment:
            if use_term:
                term_ids = [enrollment.term_id.id]
            else:
                term_ids = self.pool.get('aun.registrar.term').search(cr, uid, [])
            student_id = enrollment.student_id.id
            course_id = enrollment.section_id.course_id.id
            level_gpa_id = enrollment.level_gpa_id.id
            enr_ids = self.search(cr, uid, [('id','!=',enrollment.id),('student_id','=',student_id),('term_id','in',term_ids),('lab','=',False),('state','=','registered'),('level_gpa_id','=',level_gpa_id)])
            equivalent_ids = [c.id for c in enrollment.section_id.course_id.equivalents]
        else:
            level_gpa_id = self.pool.get('level.gpa').search(cr, uid, [('student_id','=',student.id),('level_id','=',student.level_id.id),('admission_date','=',student.admission_date),('student_state_id','=',student.student_state_id.id),('current','=',True)])
            if level_gpa_id:
                level_gpa_id = level_gpa_id[0]
            else:
                raise osv.except_osv(_('Check student level!'), _('Check level GPA.'))
            enr_ids = self.search(cr, uid, [('student_id','=',student.id),('lab','=',False),('state','=','registered'),('level_gpa_id','=',level_gpa_id)])
            equivalents = self.pool.get('aun.registrar.course').browse(cr, uid, course_id).equivalents
            equivalent_ids = [c.id for c in equivalents]
        
        enrollments = self.browse(cr, uid, enr_ids)
        equiv_enr_ids = [e.id for e in enrollments if course_id in [c.id for c in e.section_id.course_id.equivalents] or 
                         e.section_id.course_id.id in equivalent_ids or 
                         (check_course and course_id == e.section_id.course_id.id)]
        return equiv_enr_ids
    
    def on_change_value(self, cr, uid, ids, value, section_id, field_name, context=None):
        section = self.pool.get('aun.registrar.section').browse(cr, uid, section_id)
        res = value
        warning = {}
        if field_name == 'billing':
            warning = {
                'title': _('Warning '),
                'message': _("This action will charge or refund this student the difference in tuition for this course.")
                }
        if field_name == 'credit' and (value < section.credit_low or value > section.credit_high):
            res = section.credit_low if value < section.credit_low else section.credit_high
            warning = {
                    'title': _('Invalid Credit'),
                    'message': _('The amount should be ' + ['less than or equal to the maximum', 'greater than or equal to the minimum'][value < section.credit_low] + ' credit hours for the course section: ' + str(res) + ' credit hours')
                    }
        if field_name == 'billing' and (value < section.billing_low or value > section.billing_high):
            res = section.billing_low if value < section.billing_low else section.billing_high
            warning = {
                    'title': _('Invalid Billing'),
                    'message': _('The amount should be ' + ['less than or equal to the maximum', 'greater than or equal to the minimum'][value < section.billing_low] + ' billing hours for the course section: ' + str(res) + ' billing hours')
                    }
        return {'value': {field_name: res}, 'warning': warning}
    
    def _get_enrollment_info(self, cursor, uid, ids, name, arg, context=None):
        res = {} 
        for enr in self.browse(cursor, SUPERUSER_ID, ids, context=context):
            res[enr.id] = {}
            if enr.lab:
                if enr.lab_id:
                    res[enr.id]['duration_id'] = enr.lab_id.duration_id.id
                    res[enr.id]['location_id'] = enr.lab_id.location_id.id
                    res[enr.id]['faculty'] = [(6, 0, [x.faculty_id.id for x in enr.lab_id.faculty])]
                else:
                    res[enr.id]['duration_id'] = False
                    res[enr.id]['location_id'] = False
                    res[enr.id]['faculty'] = [(6, 0, [])]
            else:
                res[enr.id]['duration_id'] = enr.section_id.duration_id.id
                res[enr.id]['location_id'] = enr.section_id.location_id.id
                res[enr.id]['faculty'] = [(6, 0, [x.faculty_id.id for x in enr.section_id.faculty])]
        return res
    
    def _has_lab(self, cr, uid, ids, field_name, arg=None, context=None):
        res={}
        for enr in self.browse(cr, uid, ids):
            if enr.child_ids:
                res[enr.id] = True
            else:
                res[enr.id] = False
        return res
        
    _columns = {
        'section_id': fields.many2one('aun.registrar.section', 'CRN', ondelete="cascade", select=False, readonly=True, required=True, track_visibility="onchange"),
        'section_no': fields.related('section_id', 'section_no', type='integer', relation="aun.registrar.section", string="No.", store=False, readonly=True, help="Section Number"),
        'course_name': fields.char('Title', size=128, required=True, track_visibility="onchange"),
        'grademode_id': fields.many2one('aun.registrar.grademode', 'Grade Mode', required=True, track_visibility="onchange"),
        'credit': fields.float('Credit Hours', digits=(3,2), track_visibility="onchange"),
        'billing': fields.float('Billing Hours', digits=(3,2), track_visibility="onchange"),        
        'course_id': fields.related('section_id', 'course_id', type='many2one', relation="aun.registrar.course", readonly=True, string="Course", store=True),
        'subject_id': fields.related('section_id', 'course_id', 'subject_id', type='many2one', relation="course.subject", string="Subject", store=True, readonly=True),
        'term_id': fields.related('section_id', 'term_id', type='many2one', relation="aun.registrar.term", string="Term", store=True, readonly=True),
        'student_id': fields.many2one('res.partner', 'Student ID', ondelete="cascade", select=False, readonly=True, track_visibility="onchange", domain=[('student','=',True)]),
        'fname': fields.related('student_id', 'fname', type='char', string="First Name", readonly=True, store=True),
        'lname': fields.related('student_id', 'lname', type='char', string="Last Name", readonly=True, store=True),
        'midterm_grade': fields.many2one('aun.registrar.grade', 'Midterm Grade', track_visibility="onchange"),
        'grade': fields.many2one('aun.registrar.grade', 'Final Grade', track_visibility="onchange"),
        'school_ids': fields.many2many('aun.registrar.school', 'rel_enrollment_school', 'enrollment_id', 'school_id', 'School'), #field to make enrollment searchable by school
        'duration_id': fields.function(_get_enrollment_info, string='Time', type='many2one', method=True, multi='enr_info', store=True, relation='aun.registrar.duration'),
        'location_id': fields.function(_get_enrollment_info, string='Location', type='many2one', method=True, multi='enr_info', store=True, relation='aun.registrar.location'),
        'faculty': fields.function(_get_enrollment_info, string='Faculty', type='many2many', method=True, multi='enr_info', store=False, relation='hr.employee'),
        'faculty_emp_ids': fields.many2many('hr.employee', 'rel_enrollment_employee', 'enrollment_id', 'emp_id', 'Faculty'), #field to make faculty field searchable in enrollment
        'repeat': fields.selection((('I','I'), ('E','E')), 'Repeat', track_visibility="onchange"),
        'lab': fields.boolean('Lab', readonly=True),
        'lab_id': fields.many2one('section.lab', 'Lab', readonly=True),
        'parent_id': fields.many2one('aun.registrar.enrollment', 'Class', readonly=True),
        'child_ids': fields.one2many('aun.registrar.enrollment', 'parent_id', 'Lab(s)', readonly=True),
        'has_lab': fields.function(_has_lab, method=True, type='boolean', string='Has Lab', store=False),
        'level_gpa_id': fields.many2one('level.gpa', 'Level GPA', readonly=True, required=False),
        'level_id': fields.related('level_gpa_id', 'level_id', type='many2one', relation='aun.registrar.level', string='Level', store=True, readonly=True),
        'state': fields.selection(ENROLLMENT_STATES, 'Status', size=16, readonly=True, track_visibility="onchange"),
        'charge_ids': fields.one2many('term.charges', 'enrollment_id', 'Charges'),
        'image_medium': fields.related('student_id', 'image_medium', type='binary', readonly=True, string='Image', store=False),
        'email': fields.related('student_id', 'email', type='char', string='Email', store=False),
        'active': fields.boolean('Active')
        }
    
    _defaults = {
        'active': True
        }
    
    def _check_enrollments(self, cr, uid, ids, context=None):
        enrollment = self.browse(cr, uid, ids)[0]
        student_id = enrollment.student_id.id
        term_id = enrollment.section_id.term_id.id
        course = enrollment.section_id.course_id
        lab = enrollment.lab_id
        level_gpa_id = enrollment.level_gpa_id.id
        equiv_enr_ids = self.get_equiv_enr_ids(cr, uid, enrollment, False, False, True, False)
        equiv_courses = [e.section_id.course_id.name for e in self.browse(cr, uid, equiv_enr_ids)] if equiv_enr_ids else []
        
        if enrollment.lab:
            if self.search(cr, uid, [('student_id','=',student_id),('lab_id','=',lab.id),('state','=','registered'),('level_gpa_id','=',level_gpa_id)], count=True) > 1:
                raise osv.except_osv(_('Class restriction!'), _('You cannot register twice for the same lab: ' + lab.section_id.course_id.name + '(' + lab.name + ')'))
        else:
            if self.search(cr, uid, [('student_id','=',student_id),('course_id','=',course.id),('term_id','=',term_id),('lab','=',False),('state','=','registered'),('level_gpa_id','=',level_gpa_id)], count=True) > 1:
                raise osv.except_osv(_('Class restriction!'), _('You cannot register twice for the same course: ' + course.name))
            if equiv_courses:
                raise osv.except_osv(_('Course equivalent restriction!'), _('The following is/are equivalent(s) of ' + course.name + ': ' + ', '.join(equiv_courses)))

        return True
    
    _constraints = [
        (_check_enrollments, 'You cannot register twice for the same class/lab.', ['Enrollments'])
    ]

    def _update_gpa_info(self, cr, uid, enrollment_id, context=None):
        enrollment = self.browse(cr, uid, enrollment_id, context=context)
        finalgrades_obj = self.pool.get('aun.student.finalgrades')
        gpa_info_obj = self.pool.get('gpa.info')
        student_obj = self.pool.get('res.partner')
        term_id = enrollment.term_id.id
        student_id = enrollment.student_id.id
        majors = enrollment.student_id.major_ids
        minors = enrollment.student_id.minor_ids
        concs = enrollment.student_id.concentration_ids
        
        school_ids = student_obj.browse(cr, uid, student_id)._get_schools_and_programs(cr, uid)[student_id]['school_ids'][0][2]
        program_ids = student_obj.browse(cr, uid, student_id)._get_schools_and_programs(cr, uid)[student_id]['program_ids'][0][2]
        major_ids = [major.id for major in majors]
        minor_ids = [minor.id for minor in minors]
        conc_ids = [conc.id for conc in concs]
        
        finalgrade_id = finalgrades_obj.search(cr, uid, [('enrollment_id','=',enrollment.id)])
        level_gpa_id = enrollment.level_gpa_id.id
        student_term_info_id = gpa_info_obj.search(cr, uid, [('term_id','=',term_id),('student_id','=',student_id),('level_gpa_id','=',level_gpa_id)])
        if student_term_info_id:
            gpa_info = gpa_info_obj.browse(cr, uid, student_term_info_id[0])
        
        attempted_hours = gpa_info_obj.get_term_attempted_hours(cr, uid, term_id, student_id, level_gpa_id)
        quality_points = gpa_info_obj.get_term_quality_points(cr, uid, term_id, student_id, level_gpa_id)
        passed_hours = gpa_info_obj.get_term_passed_hours(cr, uid, term_id, student_id, level_gpa_id)
        earned_hours = gpa_info_obj.get_term_earned_hours(cr, uid, term_id, student_id, level_gpa_id)
        gpa_hours = gpa_info_obj.get_term_gpa_hours(cr, uid, term_id, student_id, level_gpa_id)
        gpa = gpa_info_obj.get_term_gpa(cr, uid, quality_points, gpa_hours)

        deleted = False
        institution = True
        if enrollment.grade and enrollment.state == 'registered':
            if not finalgrade_id:         
                finalgrade_id = finalgrades_obj.create(cr, uid, {'enrollment_id': enrollment.id}, context=context)
        else:
            if finalgrade_id:
                finalgrades_obj.unlink(cr, uid, finalgrade_id)
            if student_term_info_id:
                finalgrade_ids = finalgrades_obj.search(cr, uid, [('term_id','=',term_id),('student_id','=',student_id)])
                if not finalgrade_ids:
                    institution = False
                    if not gpa_info.transfer:
                        ctx = dict(delete = True)
                        gpa_info_obj.unlink(cr, SUPERUSER_ID, student_term_info_id, context=ctx)
                        deleted = True
        
        if not deleted and enrollment.state == 'registered':
            if student_term_info_id:
                gpa_info_obj.write(cr, SUPERUSER_ID, student_term_info_id[0],{
                       'attempted_hours': attempted_hours,
                       'quality_points': quality_points,
                       'passed_hours': passed_hours,
                       'earned_hours': earned_hours,
                       'gpa_hours': gpa_hours,
                       'gpa': gpa
                       })
            elif term_id and student_id and institution:
                student_term_info_id = gpa_info_obj.create(cr, SUPERUSER_ID, {
                        'school_ids': [(6, 0, school_ids)],
                        'program_ids': [(6, 0, program_ids)],
                        'major_ids': [(6, 0, major_ids)],
                        'minor_ids': [(6, 0, minor_ids)],
                        'conc_ids': [(6, 0, conc_ids)],
                        'level_gpa_id': level_gpa_id,
                        'term_id': term_id,
                        'student_id': student_id,
                        'attempted_hours': attempted_hours,
                        'quality_points': quality_points,
                        'passed_hours': passed_hours,
                        'earned_hours': earned_hours,
                        'gpa_hours': gpa_hours,
                        'gpa': gpa
                        })
        gpa_info_obj.get_terms_cgpa(cr, uid, student_id, 'institution', level_gpa_id)
        return True
    
    def update_all_students_gpa_info(self, cr, uid, context=None):
        active_term_ids = self.pool.get('aun.registrar.term').search(cr, uid, [('is_active','=',True)])
        enr_ids = self.search(cr, uid, [('term_id','in',active_term_ids),('lab','=',False)])
        a=1
        for enr_id in enr_ids:
            print str(a) + ' of ' + str(len(enr_ids))
            a+=1
            self._update_gpa_info(cr, uid, enr_id)
         
        #send email to partner_ids after update
#         model_pool = self.pool.get('mail.thread')
#         thread_id=0
#         body = 'body'
#         subject = 'subject'
#         new_msg_id = model_pool.message_post(cr, SUPERUSER_ID,[thread_id], type='comment',subject=subject,body=body,subtype='mail.mt_comment', context=context)
#         partner_ids = [6]
#         if partner_ids:
#             self.pool.get('mail.message').write(cr, SUPERUSER_ID,[new_msg_id], {'partner_ids': [(6,0,partner_ids)]}, context=context)
#         self.pool.get('mail.notification')._notify(cr,SUPERUSER_ID, new_msg_id, partner_ids, context=context)

        return True
    
    def create(self, cr, uid, vals, context=None):
        student_obj = self.pool.get('res.partner')  
        registration_hold = student_obj.get_holds(cr, uid, vals['student_id'])['registration']
        if registration_hold:
            holds = student_obj.browse(cr, uid, vals['student_id'], context=context).holds
            hold_names = ', '.join(list(set([hold.hold_id.name for hold in holds if hold.hold_id.registration and hold.is_active])))
            raise osv.except_osv(_('Hold Restriction!'), _('You have the following hold(s) on your record: ' + hold_names))
         
        vals['state'] = 'registered'
        res = super(aun_registrar_enrollment, self).create(cr, uid, vals, context)
         
        #delete any approved drop applications for the section
        ad_obj = self.pool.get('add.drop.application')
        drop_ids = ad_obj.search(cr, SUPERUSER_ID, [('student_id','=',vals['student_id']),('section_id','=',vals['section_id']),('action','=','drop'),('state','=','approved')])
        ad_obj.unlink(cr, SUPERUSER_ID, drop_ids, context=dict(delete_approved = True))
         
        section = self.pool.get('aun.registrar.section').browse(cr, uid, vals['section_id'], context=context)
        if 'lab' in vals:
            lab = self.pool.get('section.lab').browse(cr, uid, vals['lab_id'])
            faculty_emp_ids = [fs.faculty_id.id for fs in lab.faculty]
        else:
            faculty_emp_ids = [fs.faculty_id.id for fs in section.faculty]
         
        super(aun_registrar_enrollment, self).write(cr, SUPERUSER_ID, res, {'faculty_emp_ids': [(6, 0, faculty_emp_ids)]}, context)
 
        # make student follower of the section
        student = self.pool.get('res.partner').browse(cr, uid, vals['student_id'])
        if not student.user_ids:
            raise osv.except_osv(_("This student does not have a user account, Contact Administrator"), student.name)
        self.pool.get('aun.registrar.section').message_subscribe_users(cr, SUPERUSER_ID, [section.id], [student.user_ids[0].id], context=context)
    
        # Create Invoice
        self.charge_student(cr, uid, [res])
        return res
    
    def charge_students(self, cr, uid, ids, context=None):
        enrs= self.browse(cr, SUPERUSER_ID, self.search(cr, SUPERUSER_ID, [('term_id','=',118),('state','=','registered')]), context)
        i = 1
        for enr in enrs:
            print i
            if not enr.charge_ids:
                self.charge_student(cr, uid, [enr.id])
            i = i + 1
        return True

    def charge_student(self, cr, uid, ids, billing=None, context=None):
        enrollment = self.browse(cr, SUPERUSER_ID, ids, context=context)[0]
        student = enrollment.student_id
        if enrollment.term_id.start_date:
            invoice_date = enrollment.term_id.start_date[:10]
        else:
            raise osv.except_osv(_('No term start date!'), _('There is no start date for this term, please contact registrar!'))
        if billing:
            course_billing = billing
        else:
            course_billing = enrollment.billing
        charge_obj = self.pool.get('term.charges')
        account_obj = self.pool.get('student.account')
        clearance_obj = self.pool.get('term.clearance')
        fee_obj = self.pool.get('fee.structure')
         
        fee = fee_obj.browse(cr, SUPERUSER_ID, fee_obj.search(cr, SUPERUSER_ID, [('term_id','=',enrollment.term_id.id),('level_id','=',student.level_id.id)]))
        if (fee):
            fee = fee[0]
        else:
            raise osv.except_osv(_('No Fee Structure!'), _('There is no fee structure for this term, please contact bursar!'))
         
        clearance = (clearance_obj.search(cr, uid, [('student_id','=',enrollment.student_id.id),('term_id','=',enrollment.term_id.id)])
                                             or 
                     clearance_obj.create(cr, uid, {'student_id': enrollment.student_id.id,'term_id': enrollment.term_id.id}))
        clearance = clearance_obj.browse(cr,uid,clearance[0] if type(clearance) == list else clearance)
        account = (account_obj.search(cr, SUPERUSER_ID, [('student_id','=',enrollment.student_id.id)])
                                             or 
                     account_obj.create(cr, SUPERUSER_ID, {'student_id': enrollment.student_id.id}))
        if (fee.type == "credit"):
            super(aun_registrar_enrollment, self).write(cr, SUPERUSER_ID, enrollment.id, {'charge_ids': [(0,0,{
                                'detail_id' : fee.tuition_detail_id.id,
                                'name': fee.tuition_detail_id.desc,
                                'term_id': enrollment.term_id.id,
                                'charge':fee.tuition_price * course_billing,
                                'invoice_date': invoice_date,
                                'clearance_id': account[0] if type(account) == list else account,
                                'system': True
                                })]}, context)
        if clearance.fee_charge == False:
            for line in fee.comp_fees:
                charge_obj.create(cr, SUPERUSER_ID,{
                               'detail_id' : line.detail_id.id,
                               'name': line.detail_id.desc,
                               'term_id': enrollment.term_id.id,
                               'charge': line.charge,
                               'invoice_date': invoice_date,
                               'clearance_id': account[0] if type(account) == list else account,
                               'system': True
                               })
            clearance_obj.write(cr,SUPERUSER_ID,clearance.id,{'fee_charge': True})
        return True
            
    
aun_registrar_enrollment()


class aun_registrar_cat_prerequisite(osv.osv):
    _name = "aun.registrar.cat.prerequisite"
    _description = "Prerequisites"
    _rec_name = "catalogue_id"
    _inherit = ["mail.thread"]
    _columns = {
        'course_id': fields.many2one('aun.registrar.course', 'Course', required=True),
        'catalogue_id': fields.many2one('aun.registrar.catalogue', 'Catalogue', ondelete="cascade", required=True, track_visibility="onchange"),
        'prerequisite_ids': fields.one2many('aun.registrar.course.prerequisite', 'cat_id', 'Prerequisites'),
        'active': fields.boolean('Active')
    }
    
    _defaults={
        'active': True
    }
    
    _sql_constraints = [
        ('name_uniq', 'unique(course_id, catalogue_id)', 'There is a duplicate catalogue in the prerequisites for this course!'),
    ]
    
    def unlink(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'active': False}, context=context)
        return True
  
    def validate_prerequisite(self, cr, uid, ids, context=None):
        prerequisite = self.browse(cr, uid, ids, context=context)[0]
        start_year = prerequisite.catalogue_id.start_year
        end_year = prerequisite.catalogue_id.end_year
        statements = prerequisite.prerequisite_ids
        expr = ''
        for line in statements:
            if line.test_id:
                if line.test_id.scores:
                    if line.score not in line.test_id.scores.replace(' ','').split(','):
                        raise osv.except_osv(_('Check '+start_year+"/"+end_year+' catalog'), _(line.score + ' is not an acceptable score for the selected test.'))                    
                else:
                    self.pool.get('test.code').validate_score(line.test_id.name, line.score, line.test_id.low, line.test_id.high, line.test_id.score_type)
            
            if line.andor:
                expr += str(line.andor)
            if line.open:
                expr += str(line.open)
            expr += ' True '     
            if line.close:
                expr += str(line.close)
            
                
        expr = expr.replace('&', ' and ')
        expr = expr.replace('|', ' or ')
        expr2 = expr.replace('True', 'False')
        
        try:
            eval(expr)
            eval(expr2)
        except:
            raise osv.except_osv(_('Check Prerequisites'), _('Invalid prerequisite expression for the '+start_year+"/"+end_year+" catalogue."))        
        return True         
          
    
    _constraints=[
        (validate_prerequisite, 'The prerequisite expression is invalid.', ['prerequisite_id']),
    ]

aun_registrar_cat_prerequisite()


class aun_registrar_course_prerequisite(osv.osv):
    _name = "aun.registrar.course.prerequisite"
    _description = "Prerequisites"
    _inherit = ["mail.thread"]
 
    def create(self, cr, uid, vals, context=None):
        if 'score' in vals and vals['score']:
            vals['score'] = vals['score'].strip()
        return super(aun_registrar_course_prerequisite, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'score' in vals:
            vals['score'] = vals['score'].strip()
        return super(aun_registrar_course_prerequisite, self).write(cr, uid, ids, vals, context=context)
   
    def on_change_test(self, cr, uid, ids, test_id, context=None):
        res = {}
        if test_id:
            res = {'value': {'prerequisite_id': False}}
        return res
    
    def on_change_prerequisite(self, cr, uid, ids, prerequisite_id, context=None):
        res = {}
        if prerequisite_id:
            res = {'value': {'test_id': False}}
        return res
   
    _columns = {
        'course_id': fields.many2one('aun.registrar.course', 'Active Course'),
        'andor': fields.selection([('&','AND'), ('|','OR')], 'And/Or', track_visibility="onchange"),
        'open': fields.selection([('(','(')], '(', track_visibility="onchange"),
        'close': fields.selection([(')',')')], ')', track_visibility="onchange"),
        'cat_id': fields.many2one('aun.registrar.cat.prerequisite', 'Course', required=True),
        'test_id': fields.many2one('test.code', 'Test', track_visibility="onchange"),
        'score': fields.char('Score', size=32, track_visibility="onchange"),
        'prerequisite_id': fields.many2one('aun.registrar.course', 'Prerequisite', track_visibility="onchange"),
        'grade_requirement': fields.many2one('aun.registrar.grade', 'Grade Requirement', track_visibility="onchange"),
        'concurrency': fields.boolean('Concurrency', track_visibility="onchange"),
        'active': fields.boolean('Active')
    }
    
    _defaults = {
        'active': True
    }
    
    _sql_constraints = [
        ('cat_course_uniq', 'unique(cat_id, prerequisite_id)', 'You have a duplicate course in one of your prerequisites!'),
        ('cat_test_uniq', 'unique(cat_id, test_id)', 'You have a duplicate test in one of your prerequisites!')
    ]
    
aun_registrar_course_prerequisite()


class category_course(osv.osv):
    _name = "category.course"
    _description = "Category Course"
    _inherit = ["mail.thread"]
   
    _columns = {
        'andor': fields.selection([('&','AND'), ('|','OR')],'And/Or', track_visibility="onchange"),
        'cat_id': fields.many2one('registrar.cat.category', 'Category', ondelete="cascade"),
        'conc_id': fields.many2one('registrar.concentration', 'Concentration', ondelete="cascade"),
        'major_course_id': fields.many2one('aun.registrar.major.course', 'Major Course', ondelete="cascade"),
        'minor_course_id': fields.many2one('aun.registrar.major.course', 'Minor Course', ondelete="cascade"),
        'subject_id': fields.many2one('course.subject', 'Subject', ondelete="cascade", required=True, track_visibility="onchange"),
        'level_from': fields.selection([('100','100'),('200','200'),('300','300'),('400','400'),('500','500'),('600','600'),('700','700'),('800','800'),('900','900')], 'Level From', track_visibility="onchange"),
        'level_to': fields.selection([('100','100'),('200','200'),('300','300'),('400','400'),('500','500'),('600','600'),('700','700'),('800','800'),('900','900')], 'Level To', track_visibility="onchange"),
        'course_id': fields.many2one('aun.registrar.course', 'Course', ondelete="cascade", domain="[('subject_id','=',subject_id)]"),
        'credit': fields.float('Credits', digits=(3,2), track_visibility="onchange"),
        'grade_requirement': fields.many2one('aun.registrar.grade', 'Grade Requirement', track_visiblity="onchange")
    }
    
    def on_change_subject(self, cr, uid, ids, subject_id, course_id, context=None):
        res = {}
        if not subject_id:
            return res
        course_obj = self.pool.get('aun.registrar.course')
        if course_id:
            course = course_obj.browse(cr, uid, course_id)
            if course.subject_id.id != subject_id:
                res['course_id'] = False
        return {'value': res}
 
    def on_change_course(self, cr, uid, ids, course_id, context=None):
        result = {'value': {'credit': False}}
        if course_id:
            course = self.pool.get('aun.registrar.course').browse(cr, uid, course_id)
            result = {'value': {'credit': course.credit_low}}
        return result

    def create(self, cr, uid, vals, context=None):
        if 'course_id' in vals and vals['course_id']:
            credit = self.pool.get('aun.registrar.course').browse(cr, uid, vals['course_id']).credit_low
            vals['credit'] = credit
        res = super(category_course, self).create(cr, uid, vals, context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if 'course_id' in vals and vals['course_id']:
            credit = self.pool.get('aun.registrar.course').browse(cr, uid, vals['course_id']).credit_low
            vals['credit'] = credit
        return super(category_course, self).write(cr, uid, ids, vals, context=context)

    _sql_constraints = [
        ('cat_course_uniq', 'unique(cat_id, course_id)', 'You have a duplicate course in one of your categories!'),
    ]
    
category_course()


class registrar_corequisite(osv.osv):
    _name = "registrar.corequisite"
    _description = "Corequisites"
    _columns = {
        'course_id': fields.many2one('aun.registrar.course', 'Course', required=True),
        'catalogue_id': fields.many2one('aun.registrar.catalogue', 'Catalogue', required=True),
        'corequisites': fields.many2many('aun.registrar.course', 'rel_course_corequisite', 'course_id', 'corequisite_id', 'Co-Requisites', required=True)
    }
    
    _sql_constraints = [
        ('cat_uniq', 'unique(course_id, catalogue_id)', 'There is a duplicate catalogue in the corequisites for this course!')
    ]
      
registrar_corequisite()


class registrar_category(osv.osv):
    _name = "registrar.category"
    _description = "Categories"
    _inherit = ["mail.thread"]
    _columns = {
        'name': fields.char('Category', size=256, track_visibility="onchange"),
        'description': fields.text('Description', track_visibility="onchange"),
    }
registrar_category()


class registrar_cat_category(osv.osv):
    _name = "registrar.cat.category"
    _description = "Categories"
    _inherit = ["mail.thread"]
    _columns = {
        'name': fields.many2one('registrar.category', 'Category', ondelete="cascade", required=True, track_visibility="onchange"),        
        'catalogue_id': fields.many2one('aun.registrar.catalogue', 'Catalogue', ondelete="cascade"),
        'major_course_id': fields.many2one('aun.registrar.major.course', 'Major Course', ondelete="cascade"),
        'conc_id': fields.many2one('registrar.concentration', 'Concentration', ondelete="cascade"),
        'course_ids': fields.one2many('category.course', 'cat_id', 'Courses'),
        'grade_requirement': fields.many2one('aun.registrar.grade', 'Grade Requirement', required=True, track_visibility="onchange"),
        'req_credit_hrs': fields.float('Required Credit Hours', digits=(3,2), required=True, track_visibility="onchange"),    
        'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility="onchange"),
    }
    
    _sql_constraints = [
        ('uniq_cat_category', 'unique(name,level_id,catalogue_id)', 'Gen Eds must be unique for each level!')
    ]
    
    def validate_expr(self, cr, uid, ids, context=None):
        category = self.browse(cr, uid, ids, context=context)[0]
        statements = category.course_ids
        expr = ''
        for line in statements:
            if line.andor:
                expr += str(line.andor)
            expr += ' True '
                
        expr = expr.replace('&', ' and ')
        expr = expr.replace('|', ' or ')
        expr2 = expr.replace('True', 'False')
        
        try:
            eval(expr)
            eval(expr2)
        except:
            if category.catalogue_id:
                raise osv.except_osv(_('Check Categories'), _('Invalid course expression for ' + category.name.name)) 
            if category.major_course_id:
                raise osv.except_osv(_('Check Major Categories'), _('Invalid course expression for ' + category.name.name + ' in ' + category.major_course_id.major_id.name + ' ('+ category.major_course_id.program_id.name + ')'))
            if category.conc_id:
                raise osv.except_osv(_('Check Concentration Categories'), _('Invalid course expression for ' + category.name.name + ' in the ' + category.conc_id.name + ' concentration.'))  
        return True
    
    _constraints=[
        (validate_expr, 'The course expression is invalid.', ['prerequisite_id']),
    ]

registrar_cat_category()


class aun_registrar_major(osv.osv):
    _name = "aun.registrar.major"
    _description = "Majors"
    _inherit = ["mail.thread"]
    
    def _get_hod_users(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for major in self.browse(cr, uid, ids, context=context):
            employee_ids = [x.id for x in major.hod_ids]
            employees = self.pool.get('hr.employee').browse(cr, uid, employee_ids)
            user_ids = [employee.user_id.id for employee in employees]
            res[major.id] = [(6, 0, user_ids)]
        return res  

    _columns = {
        'name': fields.char('Major', size=64, required=True, track_visibility="onchange"),
        'description': fields.text('Description', track_visibility="onchange"),
        'major_course_ids': fields.one2many('aun.registrar.major.course', 'major_id', 'Major Courses'),
        'conc_ids': fields.one2many('registrar.concentration', 'conc_major_id', 'Concentrations'),
        'hod_id': fields.many2one('hr.employee', 'HOD', track_visibility="onchange"),
        'hod_ids': fields.many2many('hr.employee', 'rel_major_employee', 'major_id', 'employee_id', 'Other HODs'),
        'hod_user_ids': fields.function(_get_hod_users, string='HOD users', type='many2many', store=False, relation='res.users'),
        'major': fields.boolean('Major', track_visibility="onchange"),
        'minor': fields.boolean('Minor', track_visibility="onchange"),
        'conc': fields.boolean('Concentration', track_visibility="onchange"),
        'no_school': fields.boolean('No School', track_visibility="onchange")
    }
    
    def _check_no_school(self, cr, uid, ids, context=None):
        if self.search(cr, uid, [('no_school','=', True)], count=True) > 1:
            raise osv.except_osv(_('Check No School'), _('Only one major can be defined without a school. This should be the \'undeclared\' major.'))     
        return True
    
    _constraints=[
        (_check_no_school, 'Only one major can be defined without a school. This should be the undeclared major.', ['No School'])
    ]

aun_registrar_major()


class aun_registrar_major_course(osv.osv):
    _name = "aun.registrar.major.course"
    _description = "Major"
    _inherit = ["mail.thread"]

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.major_id.name
            res.append((record['id'], name))
        return res   

    def on_change_program(self, cr, uid, ids, program_id, context=None):
        if not program_id:
            return {'value': {'level_id': False}}
        program = self.pool.get('registrar.program').browse(cr, uid, program_id)
        return {'value': {'level_id': program.level_id.id}}

    def on_change_major(self, cr, uid, ids, major_id, context=None):
        res = {}
        if not major_id:
            return {'value': {'major_only': False, 'minor_only': False, 'no_school': False}}
        major = self.pool.get('aun.registrar.major').browse(cr, uid, major_id)
        major_only = True if major.major and not major.minor else False
        minor_only = True if major.minor and not major.major else False
        
        if major_only:
            res['minor_course_ids'] = False
        if minor_only:
            res['program_id'] = False
        if major.no_school:
            res.update({'program_id': False, 'school_id': False, 'grade_requirement': False})
        res.update({'major_only': major_only, 'minor_only': minor_only, 'no_school': major.no_school})
        return {'value': res}

    _columns = {
        'catalogue_id': fields.many2one('aun.registrar.catalogue', 'Catalogue', required=True, track_visibility="onchange"),
        'major_id': fields.many2one('aun.registrar.major', 'Major', required=True, track_visibility="onchange"),
        'program_id': fields.many2one('registrar.program', 'Program', track_visibility="onchange"),
        'category_ids': fields.one2many('registrar.cat.category', 'major_course_id', 'Gen Eds'),
        'course_ids': fields.one2many('category.course', 'major_course_id', 'Major Courses'),
        'minor_course_ids': fields.one2many('category.course', 'minor_course_id', 'Minor Courses'),
        'concentration_ids': fields.one2many('registrar.concentration', 'major_course_id', 'Concentrations'),
        'grade_requirement': fields.many2one('aun.registrar.grade', 'Grade Requirement', track_visibility="onchange"),
        'school_id': fields.many2one('aun.registrar.school', 'School', track_visibility="onchange"),
        'level_id': fields.related('program_id', 'level_id', type='many2one', relation='aun.registrar.level', string='Level', store=True, readonly=True),
        'major_only': fields.boolean('Major Only'),
        'minor_only': fields.boolean('Minor Only'),
        'no_school': fields.boolean('No School')
    }
    
    _sql_constraints = [
        ('uniq_cat_major', 'unique(catalogue_id,level_id,major_id)', 'Majors must be unique for each level!')
    ]
 
    def write(self, cr, uid, ids, vals, context=None):
        res = super(aun_registrar_major_course, self).write(cr, uid, ids, vals, context=context)
        major_course = self.browse(cr, uid, ids, context=context)[0]        
        statements = major_course.course_ids
        if statements:
            expr = ''
            for line in statements:
                if line.andor:
                    expr += str(line.andor)
                expr += ' True '
                    
            expr = expr.replace('&', ' and ')
            expr = expr.replace('|', ' or ')
            expr2 = expr.replace('True', 'False')
            
            try:
                eval(expr)
                eval(expr2)
            except:
                raise osv.except_osv(_('Check Major Courses'), _('Invalid course expression for ' + major_course.major_id.name + ' (' + major_course.program_id.name + ') major')) 

        statements = major_course.minor_course_ids
        if statements:
            expr = ''
            for line in statements:
                if line.andor:
                    expr += str(line.andor)
                expr += ' True '
                    
            expr = expr.replace('&', ' and ')
            expr = expr.replace('|', ' or ')
            expr2 = expr.replace('True', 'False')
            
            try:
                eval(expr)
                eval(expr2)
            except:
                raise osv.except_osv(_('Check Minor Courses'), _('Invalid course expression for ' + major_course.major_id.name + ' minor')) 

        return res
    
aun_registrar_major_course()


class registrar_concentration(osv.osv):
    _name = "registrar.concentration"
    _description = "Concentration"
    _inherit = ["mail.thread"]
    _columns = {
        'name': fields.char('Concentration', size=256, required=True, track_visibility="onchange"),
        'conc_major_id': fields.many2one('aun.registrar.major', 'Concentration', required=True, domain=[('conc','=',True)]),
        'req_credit_hrs': fields.float('Required Credit Hours', digits=(3,2), required=True, track_visibility="onchange"),
        'category_ids': fields.one2many('registrar.cat.category', 'conc_id', 'Gen Eds'),
        'grade_requirement': fields.many2one('aun.registrar.grade', 'Grade Requirement', required=True, track_visibility="onchange"),
        'description': fields.text('Description', track_visibility="onchange"),
        'major_course_id': fields.many2one('aun.registrar.major.course', 'Major', required=True, ondelete="cascade", track_visibility="onchange"),
        'course_ids': fields.one2many('category.course', 'conc_id', 'Courses')
    }
    
    def write(self, cr, uid, ids, vals, context=None):
        res = super(registrar_concentration, self).write(cr, uid, ids, vals, context=context)
        concentration = self.browse(cr, uid, ids, context=context)[0]
        statements = concentration.course_ids
        if statements:
            expr = ''
            for line in statements:
                if line.andor:
                    expr += str(line.andor)
                expr += ' True '
                    
            expr = expr.replace('&', ' and ')
            expr = expr.replace('|', ' or ')
            expr2 = expr.replace('True', 'False')
            
            try:
                eval(expr)
                eval(expr2)
            except:
                raise osv.except_osv(_('Check Concentration Courses'), _('Invalid course expression for ' + concentration.name + ' in ' + concentration.major_course_id.major_id.name))

        if not (statements or concentration.category_ids):
            raise osv.except_osv(_('No Concentration Information'), _('No information entered for ' + concentration.name + ' in ' + concentration.major_course_id.major_id.name))
        return res
    
    def on_change_conc(self, cr, uid, ids, conc_id, context=None):
        name = False
        if conc_id:
            name = self.pool.get('aun.registrar.major').browse(cr, uid, conc_id).name
        return {'value': {'name': name}}
    
registrar_concentration()


class aun_registrar_catalogue(osv.osv):
    _name = "aun.registrar.catalogue"
    _description = "Catalogue Management"
    _inherit = ["mail.thread"]
    _order = "start_year DESC"

    def compute_catalogue_code(self, cr, uid, ids, name, arg, context=None):
        res={}
        catalogue = self.browse(cr, uid, ids)[0]
        end_year = str(int(catalogue.end_year))
        code = str(int(catalogue.start_year)) + end_year[2:]
        res[catalogue.id] = code
        return res

    def _populate_year(self, cr, uid, context=None):
        current_year = date.today().year
        return [(str(i), str(i)) for i in range(2005, current_year+10)]

    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'done'
        return super(aun_registrar_catalogue, self).create(cr, uid, vals, context)

    _columns = {
        'code':fields.function(compute_catalogue_code, type='char', method=True, string='Code', store=True),
        'start_year': fields.selection(_populate_year, 'Catalogue Begins', required=True, track_visibility="onchange"),
        'end_year': fields.selection(_populate_year, 'Catalogue Ends', required=True, track_visibility="onchange"),
        'category_ids': fields.one2many('registrar.cat.category', 'catalogue_id', 'Gen Eds'),
        'major_course_ids': fields.one2many('aun.registrar.major.course', 'catalogue_id', 'Majors/Minors'),
        'state': fields.selection(ADD_DROP_STATES, 'State')
    }
    _defaults = {
        'state': 'draft'
    }

    def check_catalogue_year(self, cr, uid, ids, context=None):
        catalogue = self.browse(cr, uid, ids, context=context)[0]
        if int(catalogue.start_year) >= int(catalogue.end_year):
            raise osv.except_osv(_('Invalid!'), _('The end year must be greater than the start year.'))
        catalogue_ids = self.search(cr, uid, [('id','not in',[catalogue.id])])
        catalogues = [self.browse(cr, uid, c) for c in catalogue_ids]
        for cat in catalogues:
            if ((int(cat.start_year) < int(catalogue.start_year) < int(cat.end_year)) or
                (int(cat.start_year) < int(catalogue.end_year) < int(cat.end_year)) or
                (int(catalogue.start_year) < int(cat.start_year) < int(catalogue.end_year)) or
                (int(catalogue.start_year) < int(cat.end_year) < int(catalogue.end_year)) or
                (int(cat.start_year) == int(catalogue.start_year)) or
                (int(cat.end_year) == int(catalogue.end_year))):
                    raise osv.except_osv(_('Invalid!'), _('Catalogs should be chronological. Your dates coincide with the ' + cat.name_get()[0][1] + ' catalog.'))
        return True

    _constraints=[
        (check_catalogue_year, 'Catalogs should be chronological.', ['Start/End Year'])
    ]   

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['start_year', 'end_year'], context=context)
        res = []
        for record in reads:
            name = record['start_year'] + '-' + record['end_year']
            res.append((record['id'], name))
        return res
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('start_year','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('start_year',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    def copy(self, cr, uid, ids, default=None, context=None):
        if context is None:
            context={}
        if not default:
            default = {}
        context = context.copy()
        default = default.copy()    
        if context.get('duplicate'):
            return super(aun_registrar_catalogue, self).copy(cr, uid, ids, default=default, context=context)
        raise osv.except_osv(_('Invalid!'), _('Please click on the \'Duplicate Catalog\' link under the Catalogs menu in the left pane.'))
       
aun_registrar_catalogue()


class aun_registrar_school(osv.osv):
    _name = 'aun.registrar.school'
    _inherit = ["mail.thread"]
    _description = 'AUN Schools'
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        res = []
        for record in reads:
            name = record.code + ' - ' + record.name.name
            res.append((record['id'], name))
        return res
    
    _columns = {
        'name': fields.many2one('hr.department', 'School', required=True, track_visibility="onchange"),
        'manager_id': fields.related('name', 'manager_id', type='many2one', relation='hr.employee', string='Dean', readonly=True),
        'manager_ids': fields.related('name', 'manager_ids', type='many2many', relation='hr.employee', string='Other Managers', readonly=True),
        'code': fields.char('Code', size=8, required=True, track_visibility="onchange"),
        'description': fields.text('Description', track_visibility="onchange"),
        'major_course_ids': fields.one2many('aun.registrar.major.course', 'major_id', 'Major Course'),
        'default_school': fields.boolean('Default', track_visibility="onchange")
    }

    def _check_default_school(self, cr, uid, ids, context=None):
        school_ids = self.search(cr, uid, [('default_school','=',True)])
        if len(school_ids) > 1:
            raise osv.except_osv(_('Check Default'), _('You can only set one school as default'))     
        return True
    
    _sql_constraints = [
        ('uniq_school', 'unique(name)', 'This school already exists!')
    ]
    
    _constraints=[
        (_check_default_school, 'Only one school can be set as the default.', ['Default'])
    ]
    
aun_registrar_school()


class aun_registrar_standing(osv.osv):
    _name='aun.registrar.standing'
    _description='Academic Standing Code Validation'
    _inherit = ["mail.thread"]
    _columns={
              'name': fields.char('Standing', size=32, required=True, track_visibility="onchange"),
              'description': fields.text('Description', track_visibility="onchange"),
              'dean_list': fields.boolean('Dean List', track_visibility="onchange"),
              'prob_ind': fields.boolean('Probation Indicator', track_visibility="onchange"),
              'proh_reg': fields.boolean('Prohibit Registration', track_visibility="onchange"),
              'minimum_hours': fields.float('Minimum Hours', digits=(3,2), track_visibility="onchange"),
              'maximum_hours': fields.float('Maximum Hours', digits=(3,2), track_visibility="onchange"),
              'default_standing': fields.boolean('Default', track_visibility="onchange")
        }

    def _check_default_standing(self, cr, uid, ids, context=None):
        standing_ids = self.search(cr, uid, [('default_standing','=',True)])
        if len(standing_ids) > 1:
            raise osv.except_osv(_('Check Default'), _('You can only set one standing as default'))     
        return True
    
    _constraints=[
        (_check_default_standing, 'Only one standing can be set as the default.', ['Default'])
    ]    
    
aun_registrar_standing



class aun_registrar_standing_rules(osv.osv):
    _name='aun.registrar.standing.rules'
    _description='Academic Standing Rules'
    _inherit = ["mail.thread"]

    _columns={
              'old_standing': fields.many2one('aun.registrar.standing', 'Old Standing', required=True, track_visibility="onchange"),
              'term_id':fields.many2one('aun.registrar.term', 'Term', required=True, track_visibility="onchange"),
              'min_term_hours':fields.float('Minimum Term Hours', required=True, track_visibility="onchange"),
              'max_term_hours':fields.float('Maximum Term Hours', required=True, track_visibility="onchange"),  
              'min_term_gpa':fields.float('Minimum Term GPA', required=True, track_visibility="onchange"),
              'max_term_gpa':fields.float('Maximum Term GPA', required=True, track_visibility="onchange"), 
              'min_cumulative_hours':fields.float('Minimum Cumulative Hours', required=True, track_visibility="onchange"),
              'max_cumulative_hours':fields.float('Maximum Cumulative Hours', required=True, track_visibility="onchange"),
              'min_cumulative_gpa':fields.float('Minimum Cumulative GPA', required=True, track_visibility="onchange"),  
              'max_cumulative_gpa':fields.float('Maximum Cumulative GPA', required=True, track_visibility="onchange"),
              'min_overall_gpa':fields.float('Minimum Overall GPA',required=True, track_visibility="onchange"),  
              'max_overall_gpa':fields.float('Maximum Overall GPA',required=True, track_visibility="onchange"),
              'new_standing': fields.many2one('aun.registrar.standing', 'New Standing', required=True, track_visibility="onchange"), 
              'level_id': fields.many2one('aun.registrar.level', 'Level', required=True, track_visibility="onchange")            
        }
    
    _defaults={
#               'min_term_hours': 0.00,
#               'min_term_gpa': 0.00,
#               'min_cumulative_hours': 0.00,
#               'min_cumulative_gpa': 0.00,
#               'min_overall_gpa': 0.00,
               'max_term_hours': 999.00,
               'max_term_gpa': 4.00,
               'max_cumulative_hours': 999.00,
               'max_cumulative_gpa': 4.00,
               'max_overall_gpa': 4.00
        }
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.level_id.name + ': ' + record.old_standing.name + ' - ' + record.new_standing.name
            res.append((record['id'], name))
        return res
            
aun_registrar_standing_rules



class aun_registrar_hold(osv.osv):
    _name='aun.registrar.hold'
    _description='Academic Holds'
    _inherit = ["mail.thread"]
    _columns={
              'name': fields.char('Description', size=64, required=True, track_visibility="onchange"),
              'registration':fields.boolean('Registration', track_visibility="onchange"),
              'enr_ver':fields.boolean('Enrollment Verification', track_visibility="onchange"),
              'transcript':fields.boolean('Transcript', track_visibility="onchange"),
              'graduation':fields.boolean('Graduation', track_visibility="onchange"),
              'grades':fields.boolean('Grade', track_visibility="onchange"),
              'ar':fields.boolean('A/R', track_visibility="onchange"),
              'application':fields.boolean('Application', track_visibility="onchange"),
              'compliance':fields.boolean('Compliance', track_visibility="onchange"),
              'group_ids': fields.many2many('res.groups', 'rel_hold_group', 'hold_id', 'group_id', 'Groups')
        }
    
aun_registrar_hold

class aun_registrar_hold_assignment(osv.osv):
    _name='aun.registrar.hold.assignment'
    _description='Academic Hold Assignment'
    _inherit=["mail.thread"]    

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.hold_id.name
            res.append((record['id'], name))
        return res
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('hold_id','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('hold_id',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)
    
    def _check_active(self, cursor, uid, ids, name, arg, context=None):
        res = {} 
        for hold in self.browse(cursor, uid, ids, context=context):
            res[hold.id] = (hold.start_date <= datetime.now().strftime('%Y-%m-%d') <= hold.end_date) and hold.active
        return res

    def _is_active_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        res = []
        res_ids = self.search(cursor, user, [('start_date', '<=', datetime.now().strftime('%Y-%m-%d')), ('end_date','>=',datetime.now().strftime('%Y-%m-%d'))])
        res.append(('id', 'in', res_ids))
        return res

    _columns={
          'student_id': fields.many2one('res.partner', 'Student ID', required=True, readonly=True, states={'draft': [('readonly', False)]}, domain=[('student','=',True)], track_visibility="onchange"),
          'fname': fields.related('student_id', 'fname', type='char', string="First Name", readonly=True, store=False),
          'lname': fields.related('student_id', 'lname', type='char', string="Last Name", readonly=True, store=False),
          'image_medium': fields.related('student_id', 'image_medium', type='binary', readonly=True, string='Image', store=False),              
          'hold_id': fields.many2one('aun.registrar.hold', 'Hold Type', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility="onchange"),
          'hold_run_id': fields.many2one('hold.run', 'Hold Batch', readonly=True),
          'note': fields.text('Note', readonly=True, states={'draft': [('readonly', False)]}, track_visibility="onchange"),
          'start_date': fields.date('From', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility="onchange"),
          'end_date': fields.date('To', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility="onchange"),
          'is_active': fields.function(_check_active, string='Is Active', type='boolean', method=True, store=False, fnct_search=_is_active_search),
          'state': fields.selection(HOLD_STATES, 'State', track_visibility="onchange"),
          'active': fields.boolean('Active')
        }
    
    _defaults={
        'state': lambda *a: 'draft',
        'active': True
    }
    
    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'done'
        if vals['end_date'] <= vals['start_date']:
            raise osv.except_osv(_('Hold Restriction!'), _('The end date must be greater than the start date.'))
        return super(aun_registrar_hold_assignment, self).create(cr, uid, vals, context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for hold_assgnmt in self.browse(cr, uid, ids):
            hold = hold_assgnmt.hold_id
            user = self.pool.get('res.users').browse(cr, uid, uid)
            if not(set(user.groups_id) & set(hold.group_ids)):
                groups = [g.name for g in hold.group_ids]
                if groups:
                    raise osv.except_osv(_('Hold Restriction!'), _('Only ' + ['this group','these groups'][len(groups) > 1] + ' can remove the ' + hold.name + ': ' + ', '.join(groups)))
                else:
                    raise osv.except_osv(_('Hold Restriction!'), _('Only the system administrator can remove the ' + hold.name))
    
        self.write(cr, uid, ids, {'state': 'cancelled', 'active': False}, context=context)
        return True

    def delete_hold(self, cr, uid, ids, context=None):
        self.unlink(cr, uid, ids, context=context)
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'academics', 'admission_student_action')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        return result

    def on_change_date(self, cr, uid, ids, start_date, end_date, context=None):    
        result = {'value': {'is_active': start_date <= datetime.now().strftime('%Y-%m-%d') <= end_date}}
        return result

    def on_change_hold(self, cr, uid, ids, hold_id, context=None):
        if not hold_id:
            return {}
        hold = self.pool.get('aun.registrar.hold').browse(cr, uid, hold_id)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        if not(set(user.groups_id) & set(hold.group_ids)):
            return {'value': {'hold_id': False}, 'warning': {'title': _('Hold Restriction'), 'message': _('You are not allowed to assign this hold type!')}}
        return True
    
    def on_change_student(self, cr, uid, ids, student_id, context=None):          
        if not student_id:
            return {'value': {'fname': False, 'lname': False, 'level_id': False}}
        student = self.pool.get('res.partner').browse(cr, uid, student_id)
        return {'value': {'fname': student.fname, 'lname': student.lname, 'image_medium': student.image_medium}}
    
    def check_student_holds(self, cr, uid, ids, context=None):
        hold_assgnmt = self.browse(cr, uid, ids, context=context)[0]
        student = hold_assgnmt.student_id
        for hold in student.holds:
            if (hold.id != hold_assgnmt.id and hold.hold_id.id == hold_assgnmt.hold_id.id and ((hold.start_date <= hold_assgnmt.start_date < hold.end_date) or (hold.start_date < hold_assgnmt.end_date <= hold.end_date) or
                (hold_assgnmt.start_date < hold.start_date and hold_assgnmt.end_date > hold.end_date))):
                raise osv.except_osv(_(hold.hold_id.name), _('For the time period specified, this hold is on the following student\'s record: '+student.fname+' '+student.lname+'('+student.name+')'))
        return True
    
    _constraints=[
        (check_student_holds, 'One or more students already have this hold on their record for the time period specified.', ['Student(s)'])
    ]
    
aun_registrar_hold_assignment

class hold_run(osv.osv):
    _name = 'hold.run'
    _description = 'Hold Batches'
    _inherit=['mail.thread']
    _columns = {
        'name': fields.char('Name', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'),
        'hold_id': fields.many2one('aun.registrar.hold', 'Hold', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility="onchange"),
        'hold_ids': fields.one2many('aun.registrar.hold.assignment', 'hold_run_id', 'Holds', readonly=True, track_visibility='onchange'),
        'state': fields.selection(HOLD_STATES, 'State', track_visibility="onchange"),
        'start_date': fields.date('Date From', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'),
        'end_date': fields.date('Date To', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange'),
        'note': fields.text('Note', readonly=True, states={'draft': [('readonly', False)]}, track_visibility="onchange"),
        'active': fields.boolean('Active')
    }
    _defaults={
        'state': 'draft',
        'active': True
    }
    
    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'done'
        if vals['end_date'] <= vals['start_date']:
            raise osv.except_osv(_('Hold Restriction!'), _('The end date must be greater than the start date.'))
        return super(hold_run, self).create(cr, uid, vals, context)
    
    def on_change_hold(self, cr, uid, ids, hold_id, context=None):
        if not hold_id:
            return {}
        hold = self.pool.get('aun.registrar.hold').browse(cr, uid, hold_id)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        if not(set(user.groups_id) & set(hold.group_ids)):
            return {'value': {'hold_id': False}, 'warning': {'title': _('Hold Restriction'), 'message': _('You are not allowed to assign this hold type!')}}
        return True
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}      
        hold_obj = self.pool.get('aun.registrar.hold.assignment')
        hold_runs = self.browse(cr, uid, ids, context=context)
        for hold_run in hold_runs:
            hold = hold_run.hold_id
            user = self.pool.get('res.users').browse(cr, uid, uid)
            if not(set(user.groups_id) & set(hold.group_ids)):
                groups = [g.name for g in hold.group_ids]
                if groups:
                    raise osv.except_osv(_('Hold Restriction!'), _('Only ' + ['this group','these groups'][len(groups) > 1] + ' can remove the ' + hold.name + ': ' + ', '.join(groups)))
                else:
                    raise osv.except_osv(_('Hold Restriction!'), _('Only the system administrator can delete the ' + hold.name))
            hold_assgnmt_ids = hold_obj.search(cr, uid, [('hold_run_id','=',hold_run.id),('state','not in',['cancelled'])])
            hold_obj.write(cr, uid, hold_assgnmt_ids, {'state': 'cancelled', 'active': False}, context=context)
        self.write(cr, uid, ids, {'state': 'cancelled', 'active': False}, context=context)
        return True

hold_run()
