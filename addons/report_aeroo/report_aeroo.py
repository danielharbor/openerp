# -*- encoding: utf-8 -*-

##############################################################################
#
# Copyright (c) 2009-2011 Alistek, SIA. (http://www.alistek.com) All Rights Reserved.
#                    General contacts <info@alistek.com>
# Copyright (C) 2009  Domsense s.r.l.                                   
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os, sys, traceback
import tempfile
import report
from report.report_sxw import *
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from report.pyPdf import PdfFileWriter, PdfFileReader
from xml.dom import minidom
import base64
from osv import osv
from tools.translate import _
import tools
import time
import re
import copy

from addons import get_module_resource
import release

import aeroolib
from aeroolib.plugins.opendocument import Template, OOSerializer
from genshi.template import NewTextTemplate
import pooler
import netsvc
logger = netsvc.Logger()

from ExtraFunctions import ExtraFunctions

class Counter(object):
    def __init__(self, name, start=0, interval=1):
        self.name = name
        self._number = start
        self._interval = interval

    def next(self):
        curr_number = self._number
        self._number += self._interval
        return curr_number

    def get_inc(self):
        return self._number

    def prev(self):
        return self._number-self._interval

class Aeroo_report(report_sxw):

    def logger(self, message, level=netsvc.LOG_DEBUG):
        netsvc.Logger().notifyChannel('report_aeroo', level, message)

    def __init__(self, cr, name, table, rml=False, parser=False, header=True, store=False):
        super(Aeroo_report, self).__init__(name, table, rml, parser, header, store)
        self.logger("registering %s (%s)" % (name, table), netsvc.LOG_INFO)
        self.oo_subreports = []
        self.epl_images = []
        self.counters = {}

        pool = pooler.get_pool(cr.dbname)
        ir_obj = pool.get('ir.actions.report.xml')
        report_xml_ids = ir_obj.search(cr, 1, [('report_name', '=', name[7:])])
        if report_xml_ids:
            report_xml = ir_obj.browse(cr, 1, report_xml_ids[0])
        else:
            report_xml = False

        if report_xml and report_xml.preload_mode == 'preload':
            file_data = report_xml.report_sxw_content
            if not file_data:
                self.logger("template is not defined in %s (%s) !" % (name, table), netsvc.LOG_WARNING)
                template_io = None
            else:
                template_io = StringIO()
                template_io.write(file_data)
                style_io=self.get_styles_file(cr, 1, report_xml)
            if template_io:
                self.serializer = OOSerializer(template_io, oo_styles=style_io)

    def getObjects_mod(self, cr, uid, ids, rep_type, context):
        table_obj = pooler.get_pool(cr.dbname).get(self.table)
        if rep_type=='aeroo':
            return table_obj.browse(cr, uid, ids, list_class=browse_record_list, context=context)
        return table_obj.browse(cr, uid, ids, list_class=browse_record_list, context=context, fields_process=_fields_process)

    ##### Counter functions #####
    def _def_inc(self, name, start=0, interval=1):
        self.counters[name] = Counter(name, start, interval)

    def _get_inc(self, name):
        return self.counters[name].get_inc()

    def _prev(self, name):
        return self.counters[name].prev()

    def _next(self, name):
        return self.counters[name].next()
    #############################

    def _epl_asimage(self, data):
        from PIL import Image
        from math import ceil
        if not data:
            return ''
        img = Image.open(StringIO(base64.decodestring(data)))
        if img.format!='BMP':
            return ''
        data = base64.decodestring(data)[62:]
        line_len = int(ceil(img.size[0]/32.0)*4)
        temp_data = ''
        for n in range(img.size[1]):
            curr_pos = n*line_len
            temp_data = data[curr_pos:curr_pos+line_len][:int(img.size[0]/8)] + temp_data

        new_data = ''
        for d in temp_data:
            new_data += chr(ord(d)^255)
        self.epl_images.append(new_data)
        return img.size

    def _epl2_gw(self, start_x, start_y, data):
        if not data:
            return None
        size_x, size_y = self._epl_asimage(data)
        return 'GW'+str(start_x)+','+str(start_y)+','+str(int(size_x/8))+','+str(size_y)+',<binary_data>'

    def _include_document(self, aeroo_ooo=False):
        def include_document(data, silent=False):
            if not aeroo_ooo:
                return _("Error! Include document not available!")
            import binascii, urllib2
            dummy_fd, temp_file_name = tempfile.mkstemp(suffix='.odt', prefix='aeroo-report-')
            temp_file = open(temp_file_name, 'wb')
            if os.path.isfile(data):
                fd = file(data, 'rb')
                data = fd.read()
            else:
                error = False
                try:
                    url_file = urllib2.urlopen(data)
                    data = url_file.read()
                except urllib2.HTTPError:
                    os.unlink(temp_file_name)
                    error = _('HTTP Error 404! Not file found:')+' %s' % data
                except urllib2.URLError, e:
                    os.unlink(temp_file_name)
                    error = _('Error!')+' %s' % e
                except IOError, e:
                    os.unlink(temp_file_name)
                    error = _('Error!')+' %s' % e
                except Exception, e:
                    try:
                        data = base64.decodestring(data)
                    except binascii.Error:
                        os.unlink(temp_file_name)
                        error = _('Error! Not file found:')+' %s' % data
                if error:
                    if not silent:
                        return error
                    else:
                        return None
            try:
                temp_file.write(data)
            finally:
                temp_file.close()
            self.oo_subreports.append(temp_file_name)
            return "<insert_doc('%s')>" % temp_file_name
        return include_document

    def _subreport(self, cr, uid, output='odt', aeroo_ooo=False, context={}):
        pool = pooler.get_pool(cr.dbname)
        ir_obj = pool.get('ir.actions.report.xml')
        #### for odt documents ####
        def odt_subreport(name=None, obj=None):
            if not aeroo_ooo:
                return _("Error! Subreports not available!")
            report_xml_ids = ir_obj.search(cr, uid, [('report_name', '=', name)], context=context)
            if report_xml_ids:
                report_xml = ir_obj.browse(cr, uid, report_xml_ids[0], context=context)
                data = {'model': obj._table_name, 'id': obj.id, 'report_type': 'aeroo', 'in_format': 'oo-odt'}
                report, output = netsvc.SERVICES['report.%s' % name].create_aeroo_report(cr, uid, \
                                            [obj.id], data, report_xml, context=context, output='odt')

                dummy_fd, temp_file_name = tempfile.mkstemp(suffix='.odt', prefix='aeroo-report-')
                temp_file = open(temp_file_name, 'wb')
                try:
                    temp_file.write(report)
                finally:
                    temp_file.close()

                self.oo_subreports.append(temp_file_name)

                return "<insert_doc('%s')>" % temp_file_name
            return None
        #### for text documents ####
        def raw_subreport(name=None, obj=None):
            report_xml_ids = ir_obj.search(cr, uid, [('report_name', '=', name)], context=context)
            if report_xml_ids:
                report_xml = ir_obj.browse(cr, uid, report_xml_ids[0], context=context)
                data = {'model': obj._table_name, 'id': obj.id, 'report_type': 'aeroo', 'in_format': 'genshi-raw'}
                report, output = netsvc.SERVICES['report.%s' % name].create_genshi_raw_report(cr, uid, \
                                            [obj.id], data, report_xml, context=context, output=output)
                return report
            return None

        if output=='odt':
            return odt_subreport
        elif output=='raw':
            return raw_subreport

    def set_xml_data_fields(self, objects, parser):
        xml_data_fields = parser.localcontext.get('xml_data_fields', False)
        if xml_data_fields:
            for field in xml_data_fields:
                for o in objects:
                    if getattr(o, field):
                        xml_data = base64.decodestring(getattr(o, field))
                        xmldoc = minidom.parseString(xml_data)
                        setattr(o, field, xmldoc.firstChild)
        return objects

    def get_other_template(self, cr, uid, data, parser):
        if hasattr(parser, 'get_template'):
            pool = pooler.get_pool(cr.dbname)
            record = pool.get(data['model']).browse(cr, uid, data['id'], {})
            template = parser.get_template(cr, uid, record)
            return template
        else:
            return False

    def get_styles_file(self, cr, uid, report_xml, context=None):
        pool = pooler.get_pool(cr.dbname)
        style_io=None
        if report_xml.styles_mode!='default':
            if report_xml.styles_mode=='global':
                company_id = pool.get('res.users')._get_company(cr, uid, context=context)
                style_content = pool.get('res.company').browse(cr, uid, company_id, context=context).stylesheet_id
                style_content = style_content and style_content.report_styles or False
            elif report_xml.styles_mode=='specified':
                style_content = report_xml.stylesheet_id
                style_content = style_content and style_content.report_styles or False
            if style_content:
                style_io = StringIO()
                style_io.write(base64.decodestring(style_content))
        return style_io

    def create_genshi_raw_report(self, cr, uid, ids, data, report_xml, context=None, output='raw'):
        def preprocess(data):
            self.epl_images.reverse()
            while self.epl_images:
                img = self.epl_images.pop()
                data = data.replace('<binary_data>', img, 1)
            return data.replace('\n', '\r\n')

        if not context:
            context={}
        context = context.copy()
        objects = self.getObjects_mod(cr, uid, ids, report_xml.report_type, context)
        oo_parser = self.parser(cr, uid, self.name2, context=context)
        oo_parser.objects = objects
        self.set_xml_data_fields(objects, oo_parser) # Get/Set XML
        oo_parser.localcontext['objects'] = objects
        oo_parser.localcontext['data'] = data
        oo_parser.localcontext['user_lang'] = context.get('lang', False)
        if len(objects)>0:
            oo_parser.localcontext['o'] = objects[0]
        xfunc = ExtraFunctions(cr, uid, report_xml.id, oo_parser.localcontext)
        oo_parser.localcontext.update(xfunc.functions)
        file_data = self.get_other_template(cr, uid, data, oo_parser) or report_xml.report_sxw_content # Get other Tamplate
        ################################################
        if not file_data:
            return False, output

        oo_parser.localcontext['include_subreport'] = self._subreport(cr, uid, output='raw', aeroo_ooo=False, context=context)
        oo_parser.localcontext['epl2_gw'] = self._epl2_gw

        self.epl_images = []
        basic = NewTextTemplate(source=file_data)
        #try:
        data = preprocess(basic.generate(**oo_parser.localcontext).render().decode('utf8').encode(report_xml.charset))
        #except Exception, e:
        #    self.logger(str(e), netsvc.LOG_ERROR)
        #    return False, output

        if report_xml.content_fname:
            output = report_xml.content_fname
        return data, output

    def _aeroo_ooo_test(self, cr):
        '''
        Detect report_aeroo_ooo module
        '''
        aeroo_ooo = False
        cr.execute("SELECT id, state FROM ir_module_module WHERE name='report_aeroo_ooo'")
        helper_module = cr.dictfetchone()
        if helper_module and helper_module['state'] in ('installed', 'to upgrade'):
            aeroo_ooo = True
        return aeroo_ooo

    def create_aeroo_report(self, cr, uid, ids, data, report_xml, context=None, output='odt'):
        """ Returns an aeroo report generated with aeroolib
        """
        pool = pooler.get_pool(cr.dbname)
        if not context:
            context={}
        context = context.copy()
        if self.name=='report.printscreen.list':
            context['model'] = data['model']
            context['ids'] = ids
        
        objects = not context.get('no_objects', False) and self.getObjects_mod(cr, uid, ids, report_xml.report_type, context) or []
        oo_parser = self.parser(cr, uid, self.name2, context=context)

        oo_parser.objects = objects
        self.set_xml_data_fields(objects, oo_parser) # Get/Set XML

        oo_parser.localcontext['objects'] = objects
        oo_parser.localcontext['data'] = data
        oo_parser.localcontext['user_lang'] = context.get('lang', False)
        #if len(objects)==1:
        oo_parser.localcontext['o'] = objects[0]
        xfunc = ExtraFunctions(cr, uid, report_xml.id, oo_parser.localcontext)
        oo_parser.localcontext.update(xfunc.functions)

        style_io=self.get_styles_file(cr, uid, report_xml, context)
        if report_xml.tml_source in ('file', 'database'):
            file_data = report_xml.report_sxw_content
        else:
            file_data = self.get_other_template(cr, uid, data, oo_parser)
        if not file_data and not report_xml.report_sxw_content:
            return False, output
        #elif file_data:
        #    template_io = StringIO()
        #    template_io.write(file_data or report_xml.report_sxw_content)
        #    basic = Template(source=template_io, styles=style_io)
        else:
            if report_xml.preload_mode == 'preload' and hasattr(self, 'serializer'):
                serializer = copy.copy(self.serializer)
                serializer.apply_style(style_io)
                template_io = serializer.template
            else:
                template_io = StringIO()
                template_io.write(file_data or report_xml.report_sxw_content)
                serializer = OOSerializer(template_io, oo_styles=style_io)
            basic = Template(source=template_io, serializer=serializer)

        #if not file_data:
        #    return False, output

        #basic = Template(source=template_io, serializer=serializer)

        aeroo_ooo = context.get('aeroo_ooo', False)
        oo_parser.localcontext['include_subreport'] = self._subreport(cr, uid, output='odt', aeroo_ooo=aeroo_ooo, context=context)
        oo_parser.localcontext['include_document'] = self._include_document(aeroo_ooo)

        ####### Add counter functons to localcontext #######
        oo_parser.localcontext.update({'def_inc':self._def_inc,
                                      'get_inc':self._get_inc,
                                      'prev':self._prev,
                                      'next':self._next})

        user_name = pool.get('res.users').browse(cr, uid, uid, {}).name
        model_id = pool.get('ir.model').search(cr, uid, [('model','=',data['model'])])[0]
        model_name = pool.get('ir.model').browse(cr, uid, model_id).name

        #basic = Template(source=None, filepath=odt_path)

        basic.Serializer.add_title(model_name)
        basic.Serializer.add_creation_user(user_name)
        basic.Serializer.add_creation_date(time.strftime('%Y-%m-%dT%H:%M:%S'))
        terp = get_module_resource('report_aeroo', '__terp__.py')
        info = eval(tools.file_open(terp).read())
        basic.Serializer.add_generator_info('Aeroo Lib/%s Aeroo Reports/%s' % (aeroolib.__version__, info['version']))
        basic.Serializer.add_custom_property('Aeroo Reports %s' % info['version'], 'Generator')
        basic.Serializer.add_custom_property('OpenERP %s' % release.version, 'Software')
        basic.Serializer.add_custom_property('http://www.alistek.com/', 'URL')
        basic.Serializer.add_creation_date(time.strftime('%Y-%m-%dT%H:%M:%S'))

        try:
            data = basic.generate(**oo_parser.localcontext).render().getvalue()
        except Exception, e:
            tb_s = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            self.logger(tb_s, netsvc.LOG_ERROR)
            for sub_report in self.oo_subreports:
                os.unlink(sub_report)
            raise Exception(_("Aeroo Reports: Error while generating the report."), e, str(e), _("For more reference inspect error logs."))

        ######### OpenOffice extras #########
        DC = netsvc.SERVICES.get('openoffice')
        if (output!=report_xml.in_format[3:] or self.oo_subreports):
            if aeroo_ooo and DC:
                try:
                    DC.putDocument(data)
                    if self.oo_subreports:
                        DC.insertSubreports(self.oo_subreports)
                        self.oo_subreports = []
                    data = DC.saveByStream(report_xml.out_format.filter_name)
                    DC.closeDocument()
                    #del DC
                except Exception, e:
                    self.logger(str(e), netsvc.LOG_ERROR)
                    output=report_xml.in_format[3:]
                    self.oo_subreports = []
            else:
                output=report_xml.in_format[3:]
        elif output in ('pdf', 'doc', 'xls'):
            output=report_xml.in_format[3:]
        #####################################

        if report_xml.content_fname:
            output = report_xml.content_fname
        return data, output

    # override needed to keep the attachments' storing procedure
    def create_single_pdf(self, cr, uid, ids, data, report_xml, context=None):
        if not context:
            context={}
        if report_xml.report_type == 'aeroo':
            if report_xml.out_format.code.startswith('oo-'):
                output = report_xml.out_format.code[3:]
                return self.create_aeroo_report(cr, uid, ids, data, report_xml, context=context, output=output)
            elif report_xml.out_format.code == 'genshi-raw':
                return self.create_genshi_raw_report(cr, uid, ids, data, report_xml, context=context, output='raw')
        logo = None
        context = context.copy()
        title = report_xml.name
        rml = report_xml.report_rml_content
        oo_parser = self.parser(cr, uid, self.name2, context=context)
        objs = self.getObjects_mod(cr, uid, ids, report_xml.report_type, context)
        oo_parser.set_context(objs, data, ids, report_xml.report_type)
        processed_rml = self.preprocess_rml(etree.XML(rml),report_xml.report_type)
        if report_xml.header:
            oo_parser._add_header(processed_rml)
        if oo_parser.logo:
            logo = base64.decodestring(oo_parser.logo)
        create_doc = self.generators[report_xml.report_type]
        pdf = create_doc(etree.tostring(processed_rml),oo_parser.localcontext,logo,title.encode('utf8'))
        return (pdf, report_xml.report_type)

    def create_source_pdf(self, cr, uid, ids, data, report_xml, context=None):
        if not context:
            context={}
        pool = pooler.get_pool(cr.dbname)
        attach = report_xml.attachment
        aeroo_ooo = self._aeroo_ooo_test(cr) # Detect report_aeroo_ooo module
        context['aeroo_ooo'] = aeroo_ooo
        if attach or aeroo_ooo and report_xml.process_sep:
            objs = self.getObjects(cr, uid, ids, context)
            results = []
            for obj in objs:
                aname = attach and eval(attach, {'object':obj, 'time':time}) or False
                result = False
                if report_xml.attachment_use and aname and context.get('attachment_use', True):
                    aids = pool.get('ir.attachment').search(cr, uid, [('datas_fname','=',aname+'.pdf'),('res_model','=',self.table),('res_id','=',obj.id)])
                    if aids:
                        brow_rec = pool.get('ir.attachment').browse(cr, uid, aids[0])
                        if not brow_rec.datas:
                            continue
                        d = base64.decodestring(brow_rec.datas)
                        results.append((d,'pdf'))
                        continue
                result = self.create_single_pdf(cr, uid, [obj.id], data, report_xml, context)
                if not result:
                    return False
                try:
                    if attach and aname:
                        name = aname+'.'+result[1]
                        pool.get('ir.attachment').create(cr, uid, {
                            'name': aname,
                            'datas': base64.encodestring(result[0]),
                            'datas_fname': name,
                            'res_model': self.table,
                            'res_id': obj.id,
                            }, context=context
                        )
                        cr.commit()
                except Exception,e:
                     tb_s = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                     netsvc.Logger().notifyChannel('report', netsvc.LOG_ERROR,str(e))
                results.append(result)
            if results:
                if results[0][1]=='pdf':
                    output = PdfFileWriter()
                    for r in results:
                        reader = PdfFileReader(StringIO(r[0]))
                        for page in range(reader.getNumPages()):
                            output.addPage(reader.getPage(page))
                    s = StringIO()
                    output.write(s)
                    return s.getvalue(), results[0][1]
        return self.create_single_pdf(cr, uid, ids, data, report_xml, context)

    def create_source_odt(self, cr, uid, ids, data, report_xml, context=None):
        if not context:
            context={}
        pool = pooler.get_pool(cr.dbname)
        results = []
        attach = report_xml.attachment
        aeroo_ooo = self._aeroo_ooo_test(cr) # Detect report_aeroo_ooo module
        context['aeroo_ooo'] = aeroo_ooo
        if attach or aeroo_ooo and report_xml.process_sep:
            objs = self.getObjects_mod(cr, uid, ids, report_xml.report_type, context)
            for obj in objs:
                aname = attach and eval(attach, {'object':obj, 'time':time}) or False
                result = False
                if report_xml.attachment_use and aname and context.get('attachment_use', True):
                    aids = pool.get('ir.attachment').search(cr, uid, [('datas_fname','=',aname+'.odt'),('res_model','=',self.table),('res_id','=',obj.id)])
                    if aids:
                        brow_rec = pool.get('ir.attachment').browse(cr, uid, aids[0])
                        if not brow_rec.datas:
                            continue
                        d = base64.decodestring(brow_rec.datas)
                        results.append((d,'odt'))
                        continue
                result = self.create_single_pdf(cr, uid, [obj.id], data, report_xml, context)
                try:
                    if attach and aname:
                        name = aname+'.'+result[1]
                        pool.get('ir.attachment').create(cr, uid, {
                            'name': aname,
                            'datas': base64.encodestring(result[0]),
                            'datas_fname': name,
                            'res_model': self.table,
                            'res_id': obj.id,
                            }, context=context
                        )
                        cr.commit()
                except Exception,e:
                     self.logger(str(e), netsvc.LOG_ERROR)
                results.append(result)

        DC = netsvc.SERVICES.get('openoffice')
        if results and len(results)==1:
            return results[0]
        elif results and DC:
            results.reverse()
            data = results.pop()
            DC.putDocument(data[0])
            DC.joinDocuments([r[0] for r in results])
            result = DC.saveByStream()
            DC.closeDocument()
            return (result, data[1])
        else:
            return self.create_single_pdf(cr, uid, ids, data, report_xml, context)

    # override needed to intercept the call to the proper 'create' method
    def create(self, cr, uid, ids, data, context=None):
        pool = pooler.get_pool(cr.dbname)
        ir_obj = pool.get('ir.actions.report.xml')
        report_xml_ids = ir_obj.search(cr, uid,
                [('report_name', '=', self.name[7:])], context=context)
        if report_xml_ids:
            report_xml = ir_obj.browse(cr, uid, report_xml_ids[0], context=context)
            report_xml.report_rml = None
            report_xml.report_rml_content = None
            report_xml.report_sxw_content_data = None
            report_rml.report_sxw_content = None
            report_rml.report_sxw = None
        else:
            title = ''
            rml = tools.file_open(self.tmpl, subdir=None).read()
            report_type= data.get('report_type', 'pdf')
            class a(object):
                def __init__(self, *args, **argv):
                    for key,arg in argv.items():
                        setattr(self, key, arg)
            report_xml = a(title=title, report_type=report_type, report_rml_content=rml, name=title, attachment=False, header=self.header)

        report_type = report_xml.report_type
        if report_type in ['sxw','odt']:
            fnct = self.create_source_odt
        elif report_type in ['pdf','raw','txt','html']:
            fnct = self.create_source_pdf
        elif report_type=='html2html':
            fnct = self.create_source_html2html
        elif report_type=='mako2html':
            fnct = self.create_source_mako2html
        elif report_type=='aeroo':
            if report_xml.out_format.code in ['oo-pdf']:
                fnct = self.create_source_pdf
            elif report_xml.out_format.code in ['oo-odt','oo-ods','oo-doc','oo-xls','genshi-raw']:
                fnct = self.create_source_odt
            else:
                return super(Aeroo_report, self).create(cr, uid, ids, data, context)
        else:
            raise Exception('Unknown Report Type')
        return fnct(cr, uid, ids, data, report_xml, context)

class ReportTypeException(Exception):
    def __init__(self, value):
      self.parameter = value
    def __str__(self):
      return repr(self.parameter)

#########################################################################

import imp, sys, zipimport
from tools.config import config

def load_from_file(path, dbname, key):
    class_inst = None
    expected_class = 'Parser'

    try:
        ad = os.path.abspath(os.path.join(tools.ustr(config['root_path']), u'addons'))
        mod_path_list = map(lambda m: os.path.abspath(tools.ustr(m.strip())), config['addons_path'].split(','))
        mod_path_list.append(ad)

        for mod_path in mod_path_list:
            if os.path.lexists(mod_path+os.path.sep+path.split(os.path.sep)[0]):
                filepath=mod_path+os.path.sep+path
                filepath = os.path.normpath(filepath)
                sys.path.append(os.path.dirname(filepath))
                mod_name,file_ext = os.path.splitext(os.path.split(filepath)[-1])
                mod_name = '%s_%s_%s' % (dbname,mod_name,key)

                if file_ext.lower() == '.py':
                    py_mod = imp.load_source(mod_name, filepath)

                elif file_ext.lower() == '.pyc':
                    py_mod = imp.load_compiled(mod_name, filepath)

                if expected_class in dir(py_mod):
                    class_inst = py_mod.Parser
                return class_inst
            elif os.path.lexists(mod_path+os.path.sep+path.split(os.path.sep)[0]+'.zip'):
                zimp = zipimport.zipimporter(mod_path+os.path.sep+path.split(os.path.sep)[0]+'.zip')
                return zimp.load_module(path.split(os.path.sep)[0]).parser.Parser
    except Exception, e:
        return None

def load_from_source(source):
    expected_class = 'Parser'
    context = {'Parser':None}
    try:
        exec source in context
        return context['Parser']
    except Exception, e:
        return None

def delete_report_service(name):
    name = 'report.%s' % name
    if netsvc.service_exist( name ):
        del netsvc.SERVICES[name]

def register_report(cr, name, model, tmpl_path, parser):
    name = 'report.%s' % name
    if netsvc.service_exist( name ):
        del netsvc.SERVICES[name]
    Aeroo_report(cr, name, model, tmpl_path, parser=parser)

def unregister_report(name):
    name = 'report.%s' % name
    if netsvc.service_exist( name ):
        del netsvc.SERVICES[name]

old_register_all = report.interface.register_all
def new_register_all(db):
    value = old_register_all(db)

    cr = db.cursor()

    ########### Run OpenOffice service ###########
    try:
        from report_aeroo_ooo.report import OpenOffice_service
    except Exception, e:
        OpenOffice_service = False

    if OpenOffice_service:
        cr.execute("SELECT id, state FROM ir_module_module WHERE name='report_aeroo_ooo'")
        helper_module = cr.dictfetchone()
        helper_installed = helper_module['state']=='installed'
    if OpenOffice_service and helper_installed:
        cr.execute("SELECT host, port FROM report_oo_config")
        host, port = cr.fetchone()
        try:
            OpenOffice_service(cr, host, port)
            netsvc.Logger().notifyChannel('report_aeroo', netsvc.LOG_INFO, "OpenOffice connection successfully established")
        except Exception, e:
            netsvc.Logger().notifyChannel('report_aeroo', netsvc.LOG_WARNING, e)
    ##############################################

    cr.execute("SELECT * FROM ir_act_report_xml WHERE report_type = 'aeroo' ORDER BY id")
    records = cr.dictfetchall()
    for record in records:
        parser=rml_parse
        if record['parser_state']=='loc' and record['parser_loc']:
            parser=load_from_file(record['parser_loc'], db.dbname, record['id']) or parser
        elif record['parser_state']=='def' and record['parser_def']:
            parser=load_from_source("from report import report_sxw\n"+record['parser_def']) or parser
        register_report(cr, record['report_name'], record['model'], record['report_rml'], parser)
    cr.close()
    return value

report.interface.register_all = new_register_all

