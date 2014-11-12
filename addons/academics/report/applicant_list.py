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

class applicant_list_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(applicant_list_report, self).__init__(cr, uid,name, context)
        self.localcontext.update({ 
            'time': time,
            'get_id': self._get_id
        })

        def _get_id(self, app_id):
           self.pool.get('aun.applicant').search(self.cr, self.uid, [])
        return self.pool.get('aun.applicant').browse(self.cr, self.uid, ids)

report_sxw.report_sxw('report.aun.applicant','aun.applicant', 'academics/report/applicant_list.rml', parser=applicant_list_report, header=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
