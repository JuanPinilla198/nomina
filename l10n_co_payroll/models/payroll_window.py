from dataclasses import is_dataclass
from email import message
from email.policy import default
from warnings import WarningMessage
from OpenSSL import crypto
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.backends import default_backend
from re import template
import logging
_logger = logging.getLogger("ENTRANDO A CONSOLA")

from numpy import append
from odoo import fields, models, _,modules, api
from odoo.http import request
from datetime import datetime, timedelta, date
from pytz import timezone
import zipfile
import base64
import requests
import json
import uuid
import xmltodict
import hashlib
import logging
import time

from cryptography.x509 import oid

OID_NAMES = {
    oid.NameOID.COMMON_NAME: 'CN',
    oid.NameOID.COUNTRY_NAME: 'C',
    oid.NameOID.DOMAIN_COMPONENT: 'DC',
    oid.NameOID.EMAIL_ADDRESS: 'E',
    oid.NameOID.GIVEN_NAME: 'G',
    oid.NameOID.LOCALITY_NAME: 'L',
    oid.NameOID.ORGANIZATION_NAME: 'O',
    oid.NameOID.ORGANIZATIONAL_UNIT_NAME: 'OU',
    oid.NameOID.SURNAME: 'SN',
    oid.NameOID.STATE_OR_PROVINCE_NAME: 'S',
    oid.NameOID.TITLE: 'T',
    oid.NameOID.SERIAL_NUMBER: 'SERIALNUMBER',
}

def _get_reversed_rdns_name(rdns):
    """
    Gets the rdns String name, but in the right order. xmlsig original function produces a reversed order
    :param rdns: RDNS object
    :type rdns: cryptography.x509.RelativeDistinguishedName
    :return: RDNS name
    """
    name = ''
    for rdn in reversed(rdns):
        for attr in rdn._attributes:
            if len(name) > 0:
                name = name + ','
            if attr.oid in OID_NAMES:
                name = name + OID_NAMES[attr.oid]
            else:
                name = name + attr.oid._name
            name = name + '=' + attr.value
    return name

from odoo.exceptions import Warning, UserError, ValidationError
_logger = logging.getLogger()
type_ = crypto.FILETYPE_PEM
_logger = logging.getLogger("NÓMINA ELECTRONICA")
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED
try:
    from lxml import etree
except:
    _logger.warning(
        "Cannot import  etree *************************************")
try:
    import base64
except ImportError:
    _logger.warning(
        'Cannot import base64 library *****************************')

PAYSLIP_TEMPLATE = 'l10n_co_payroll.payslip_template'
URLSEND = {
    '1': "https://vpfe.dian.gov.co/WcfDianCustomerServices.svc?wsdl",
    '2': "https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?wsdl"
}


class PayrollWindow(models.Model):
    _name = 'payroll.payroll.window'

    # Fechas
    date_from = fields.Date(string='Desde')
    date_to = fields.Date(string='Hasta')

    # Datos personales
    name = fields.Char(string="Número nómina")
    employee = fields.Many2one(
        'hr.employee',
        string='Nombre',
        readonly="1")
    tipo_doc = fields.Selection(String="Número de documento",
                                selection=[
                                    ('102', 'Documento Soporte de Pago de Nómina Electrónica'),
                                    ('103', 'Nota de Ajuste de Documento Soporte de Pago de Nómina Electrónica'),
                                ], readonly="1")
    fecha_doc = fields.Date(String="Fecha de documento", readonly="1")
    cliente_email = fields.Char(String="E-mail cliente", readonly="1")
    fecha_env = fields.Datetime(String="Fecha de envío e-mail", readonly="1")

    # Datos envío
    nom_arc_xml = fields.Char(String="Nombre archivo XML", readonly="1")
    fecha_env_xml = fields.Datetime(String="Fecha de envío XML", readonly="1")
    respuesta_env = fields.Selection(String="Respuesta",
                                     selection=[
                                         ('1', '1'),
                                         ('2', '2'),
                                     ], readonly="1")
    fecha_con_dian = fields.Datetime(
        String="Fecha consulta DIAN", readonly="1")
    respuesta_con = fields.Selection(String="Respuesta de envío",
                                     selection=[
                                         ('1', '1'),
                                         ('2', '2'),
                                     ], readonly="1")
    nombre_zip = fields.Char(String="Nombre archivo .Zip", readonly="1")
    cune = fields.Char(String="CUNE", readonly="1")

    # Respuesta

    respuesta_dian = fields.Text(String="Respuesta DIAN", readonly="1")
    contenido = fields.Text(String="Contenido XML del documento", readonly="1")
    contenido_env = fields.Text(
        String="Contenido XML de la respuesta DIAN", readonly="1")
    contenido_con = fields.Text(
        String="Contenido XML de envío de consulta de documento DIAN", readonly="1"
    )
    file_xml = fields.Binary()
    estado = fields.Selection([('rechazada', 'Rechazada'),
                               ('en_proceso', 'En proceso'),
                               ('exitosa', 'Exitosa')
                              ]
    )
    table_ids = fields.One2many(
        'hr.payslip', 'table_payslip'
    )

    documentos_dian_ids = fields.Many2one(
        'payroll.wizard.window')

    consolidados_table1_ids = fields.One2many(
        'consolidate.documents', 'consolidate1_id', string="Documentos Consolidados")

class ConsolidateDocuments(models.Model):
    _name = 'consolidate.documents'

    employee = fields.Many2one(
        'hr.employee',
        string='Empleado')
    payroll_number = fields.Char(string="Estado de consolidación")
    total_wage = fields.Char(string='Salario total')
    total_accruals = fields.Char(string="Devengos totales")
    total_deductions = fields.Char(string="Deducciones totales")
    consolidate_id = fields.Many2one(
        'payroll.wizard.window', invisible=True)
    consolidate1_id = fields.Many2one(
        'payroll.payroll.window', invisible=True)

class WizardInherit(models.Model):
    _inherit = 'hr.payslip'

    table = fields.Many2one(
        'payroll.wizard.window'
    )
    table_payslip = fields.Many2one(
        'payroll.payroll.window'
    ) 

class WizardWindow(models.Model):
    _name = 'payroll.wizard.window'

    cune = fields.Char(invisible="1")
    date_send_dian = fields.Char(invisible="1")
    date_from = fields.Date(String="Desde", required=True)
    date_to = fields.Date(String="Hasta",  required=True)
    campo = fields.Boolean()
    trackid = fields.Char(copy=False)

    table_ids = fields.One2many(
        'hr.payslip', 'table')
    
    consolidados_table_ids = fields.One2many(
        'consolidate.documents', 'consolidate_id', string="Documentos Consolidados")
    
    emision_nominas = fields.One2many('payroll.payroll.window', 'documentos_dian_ids')

    name = fields.Many2one(
        'hr.employee',
        string='Nombre',
        invisible="1")
    number = ''
    estado = fields.Selection([('rechazada', 'Rechazada'),
                               ('en_proceso', 'En proceso'),
                               ('exitosa', 'Exitosa')
                              ]
                             )
    l10n_co_payslip_attch_name = fields.Char(string='Payslip name', copy=False, readonly=True,
                                             help='The attachment name of the CFDI.')


    def FillInTable(self, date_from, date_to, lines):

        fill_in_table = self.env['hr.payslip'].search([('date_from', '>=', date_from),
                                                       ('date_to', '<=',date_to),
                                                       ('state', '=', 'done')])
        lista = []
        for x in fill_in_table:
            lista.append(x.id)
        lines = [(4, line)
                 for line in lista]
        return lines

    
    def cargar(self):
        for payslip in self:
            date_f = payslip.date_from
            date_t = payslip.date_to
            lines = [(0, 0, line)
                    for line in self]
            datos = self.FillInTable(date_f, date_t, lines)
            self.table_ids = datos
        
        self.SecondPage()

    @api.onchange('date_from', 'date_to')
    def _dates_(self):
        existing_date = self.env['payroll.wizard.window'].search([('date_from','=', self.date_from),
                                                                   ('date_to', '=', self.date_to)])
        if len(existing_date) != 0:
            self.campo = False
            return {
            'warning': {
                'title': 'Precaución!',
                'message': 'Ya existen lotes con las fechas ingresadas'}
            }
        elif len(existing_date) == 0 and self.date_from != False and self.date_to != False:
            self.campo = True
        
        
        
    def SecondPage(self):
        cond_dic = {}
        hr_payslip = self.env['hr.payslip']
        deducciones_total = self._get_deducciones_total_wizard()
        devengos_total = self._get_devengos_total_wizard()
        for cons in self.table_ids:
            comprobanteTotal = self._complements_second_decimal_wizard(
                (devengos_total[cons.employee_id.id]['Total'] - deducciones_total[cons.employee_id.id]['Total']))

            employee_name = cons.employee_id.id

            if cons.employee_id.id in cond_dic:
                cond_dic[cons.employee_id.id]['Name'] = employee_name   
                cond_dic[cons.employee_id.id]['DevengadosTotal'] = self._complements_second_decimal_wizard(devengos_total[cons.employee_id.id]['Total'])
                cond_dic[cons.employee_id.id]['DeduccionesTotal'] = self._complements_second_decimal_wizard(deducciones_total[cons.employee_id.id]['Total'])
                cond_dic[cons.employee_id.id]['ComprobanteTotal'] = comprobanteTotal
            else:
                cond_dic[cons.employee_id.id] = {}
                cond_dic[cons.employee_id.id]['Name'] = employee_name   
                cond_dic[cons.employee_id.id]['DevengadosTotal'] = self._complements_second_decimal_wizard(devengos_total[cons.employee_id.id]['Total'])
                cond_dic[cons.employee_id.id]['DeduccionesTotal'] = self._complements_second_decimal_wizard(deducciones_total[cons.employee_id.id]['Total'])
                cond_dic[cons.employee_id.id]['ComprobanteTotal'] = comprobanteTotal

            

        lista =[]
        for records in cond_dic.values():
            lista.append((0, 0, {'employee': records['Name'],
                                'payroll_number': "Por realizar",
                                'total_deductions': records['DeduccionesTotal'],
                                'total_accruals': records['DevengadosTotal'],
                                'total_wage': records['ComprobanteTotal']}))

        self.consolidados_table_ids = lista

    def fill_in_consolidates(self, date_from, date_to, employee, lines):

        dian_documents = self.env['payroll.payroll.window'].search([('employee', '=', employee),
                                                                    ('date_from','>=', date_from),
                                                                    ('date_to', '<=', date_to)])
        lista = []
        for x in dian_documents:
            lista.append(x.id)
        lines = [(0, 0, line)
                 for line in lista]
        return lines

    def PayslipObject(self):
        dic_emp = {}
        dic = []
        seq = []
        for payslip in self:
            date_f = payslip.date_from
            date_t = payslip.date_to
            for documents_id in self.table_ids:
                if documents_id.employee_id.id in dic_emp:
                    pass
                else:
                    dic_emp[documents_id.employee_id.id] = {}
                    dic_emp[documents_id.employee_id.id]['name'] = [documents_id.employee_id.name]
                lines = [(0, 0, line)
                        for line in self]
                busqueda_datos = self.fill_in_consolidates(date_f, date_t, dic_emp[documents_id.employee_id.id]['name'], lines)
                dic.append(busqueda_datos)
        exist = {}
        for i in range(0, len(dic)):
            if dic[i] == []:
                self.document_consolidate()
            else:
                dato = dic[i][0][2]
                datos = self.env['payroll.payroll.window'].browse(dato)
                if datos.estado == 'rechazada':
                    if datos in exist:
                        pass
                    else:
                        exist = datos
                        self.consolidate_again(datos)


    def consolidate_again(self, datos):
        hr_payslip = self.env['hr.payslip']
        payslip_pt = hr_payslip.payslip_periodo_template()
        payslip_ns = hr_payslip.payslip_numero_secuencia_xml_template()
        payslip_lgt = hr_payslip.payslip_lugar_generacion_xml_template()
        payslip_pxt = hr_payslip.payslip_proveedor_xml_template()
        payslip_igt = hr_payslip.payslip_informacion_general_template()
        payslip_et = hr_payslip.payslip_empleador_template()
        payslip_tt = hr_payslip.payslip_trabajador_template()
        deducciones_total = self._get_deducciones_total_wizard()
        devengos_total = self._get_devengos_total_wizard()

        dic = temp = template_cons = {}

        for payslip in datos.table_ids:
            comprobanteTotal = self._complements_second_decimal_wizard(
                (devengos_total[payslip.employee_id.id]['Total'] - deducciones_total[payslip.employee_id.id]['Total']))

            if payslip.employee_id.id in dic:
                XmlNodo = 'NominaIndividual'
                
                dic[payslip.employee_id.id]['XmlNodo'] = XmlNodo
                dic[payslip.employee_id.id]['CUNE'] = {}
                dic[payslip.employee_id.id]['Periodo'] = self.generate_payslip_periodo_wizard(
                    payslip_pt, payslip)
                dic[payslip.employee_id.id]['NumeroSecuenciaXML'] = {}
                dic[payslip.employee_id.id]['LugarGeneracionXML'] = self.generate_payslip_lugar_generacion_xml_wizard(
                    payslip_lgt, payslip)
                dic[payslip.employee_id.id]['ProveedorXML'] = {}
                dic[payslip.employee_id.id]['CodigoQR'] = {}
                dic[payslip.employee_id.id]['InformacionGeneral'] = {}
                dic[payslip.employee_id.id]['Empleador'] = self.generate_payslip_empleador_wizard(
                    payslip_et, payslip)
                dic[payslip.employee_id.id]['Trabajador'] = self.generate_payslip_trabajador_wizard(
                    payslip_tt, payslip)
                dic[payslip.employee_id.id]['Metodo'] = str(
                    self._get_metodo_wizard(payslip))
                dic[payslip.employee_id.id]['FechaPago'] = str(
                    hr_payslip._get_date_gen())
                dic[payslip.employee_id.id]['Devengados'] = {}
                dic[payslip.employee_id.id]['Deducciones'] = {}
                dic[payslip.employee_id.id]['DevengadosTotal'] = hr_payslip._complements_second_decimal(devengos_total[payslip.employee_id.id]['Total'])
                dic[payslip.employee_id.id]['DeduccionesTotal'] = hr_payslip._complements_second_decimal(deducciones_total[payslip.employee_id.id]['Total'])
                dic[payslip.employee_id.id]['ComprobanteTotal'] = comprobanteTotal
                dic[payslip.employee_id.id]['payslips_is'].append(payslip.id)

            else:
                dic[payslip.employee_id.id] = {}
                l10n_co_create = self._l10n_co_create_values_wizard(
                    payslip)
                XmlNodo = 'NominaIndividual'
                dic[payslip.employee_id.id] = {}
                dic[payslip.employee_id.id]['XmlNodo'] = XmlNodo
                dic[payslip.employee_id.id]['CUNE'] = {}
                dic[payslip.employee_id.id]['Periodo'] = self.generate_payslip_periodo_wizard(
                    payslip_pt, payslip)
                dic[payslip.employee_id.id]['NumeroSecuenciaXML'] = {}
                dic[payslip.employee_id.id]['LugarGeneracionXML'] = self.generate_payslip_lugar_generacion_xml_wizard(
                    payslip_lgt, payslip)
                dic[payslip.employee_id.id]['ProveedorXML'] = {}
                dic[payslip.employee_id.id]['CodigoQR'] = {}
                dic[payslip.employee_id.id]['InformacionGeneral'] = {}
                dic[payslip.employee_id.id]['Empleador'] = self.generate_payslip_empleador_wizard(
                    payslip_et, payslip)
                dic[payslip.employee_id.id]['Trabajador'] = self.generate_payslip_trabajador_wizard(
                    payslip_tt, payslip)
                dic[payslip.employee_id.id]['Metodo'] = str(
                    self._get_metodo_wizard(payslip))
                dic[payslip.employee_id.id]['FechaPago'] = str(
                    hr_payslip._get_date_gen())
                dic[payslip.employee_id.id]['Devengados'] = {}
                dic[payslip.employee_id.id]['Deducciones'] = {}
                dic[payslip.employee_id.id]['DevengadosTotal'] = hr_payslip._complements_second_decimal(devengos_total[payslip.employee_id.id]['Total'])
                dic[payslip.employee_id.id]['DeduccionesTotal'] = hr_payslip._complements_second_decimal(deducciones_total[payslip.employee_id.id]['Total'])
                dic[payslip.employee_id.id]['ComprobanteTotal'] = comprobanteTotal
                dic[payslip.employee_id.id]['payslips_is'] = [payslip.id]
        doc_dic = {}
        for documents_id in self.table_ids:
            if documents_id.employee_id.id in doc_dic:
                doc_dic[documents_id.employee_id.id]['IDS'].append(documents_id.id)
            else:
                doc_dic[documents_id.employee_id.id] = {}
                doc_dic[documents_id.employee_id.id]['IDS'] = [documents_id.id]
        
        doc_id = {}
        for ids in self.table_ids:
            if ids.employee_id.id in doc_id:
                doc_id[ids.employee_id.id]['payslips_is'].append(ids.id)
                pass
            else:
                doc_id[ids.employee_id.id] = {}
                doc_id[ids.employee_id.id]['payslips_is'] = [ids.id]
                doc_id[ids.employee_id.id]['IDS'] = ids.employee_id.id_document_payroll

        template = hr_payslip.payslip_main_template()
        for x1, y1 in dic.items():
            if dic[x1]['Devengados'] == {}:   
                devs = doc_dic[x1]['IDS']
                dev = self.generate_payslip_devengados_wizard(devs)
                dic[x1]['Devengados'] = dev
            if dic[x1]['Deducciones'] == {}:   
                deds = doc_dic[x1]['IDS']
                ded = self.generate_payslip_deducciones_wizard(deds)
                dic[x1]['Deducciones'] = ded
            if dic[x1]['NumeroSecuenciaXML'] == {}:        
                consecutivo = datos.name
                prefijo = consecutivo.replace(consecutivo, "NE")
                numero = consecutivo.replace('NE', '')
                dic_cons = {
                    'Consecutivo': numero,
                    'Prefijo': str(prefijo),
                    'Numero': str(consecutivo),
                }
                template_cons = payslip_ns % dic_cons
                dic[x1]['NumeroSecuenciaXML'] = template_cons
            if dic[x1]['ProveedorXML'] == {}:
                dic[x1]['ProveedorXML'] = self.generate_payslip_proveedor_xml_wizard(
                        payslip_pxt, payslip, dic_cons)
            if dic[x1]['CUNE'] == {}:
                dic_cune = str(self._generate_CUNE_wizard(
                    payslip, dic_cons, hr_payslip._get_date_gen(), hr_payslip._get_time_colombia(), x1, doc_id[x1]['IDS'], devengos_total, deducciones_total))
                dic[x1]['CUNE'] = dic_cune
            if dic[x1]['CodigoQR'] == {}:
                dic_qr = str(self._get_QRCode_wizard(
                    payslip, dic_cons, hr_payslip._get_date_gen(), hr_payslip._get_time_colombia(), x1, doc_id[x1]['IDS'], devengos_total, deducciones_total))
                dic[x1]['CodigoQR'] = dic_qr
            if dic[x1]['InformacionGeneral'] == {}:
                dic_info, type_xml = self.generate_payslip_informacion_general_wizard(
                    payslip_igt, payslip, dic_cons, hr_payslip._get_date_gen(), hr_payslip._get_time_colombia(), x1, doc_id[x1]['IDS'], devengos_total, deducciones_total)
                dic[x1]['InformacionGeneral'] = dic_info
            xml = template % y1
            temp[x1] = xml
            self._SendDianDocuments(payslip, x1, temp, dic_cons)
            data_xml_document, attachment_id, msg, nombre_zip, estado = self.send_2_validate(payslip, temp, x1, dic_cons, dic_cune)

        datos.fecha_doc = str(hr_payslip._get_date_gen())
        datos.file_xml = attachment_id
        datos.nombre_zip = nombre_zip.replace("xml", "zip")
        datos.cune = dic_cune
        datos.respuesta_dian = msg
    
    def document_consolidate(self):
        hr_payslip = self.env['hr.payslip']
        payslip_pt = hr_payslip.payslip_periodo_template()
        payslip_ns = hr_payslip.payslip_numero_secuencia_xml_template()
        payslip_lgt = hr_payslip.payslip_lugar_generacion_xml_template()
        payslip_pxt = hr_payslip.payslip_proveedor_xml_template()
        payslip_igt = hr_payslip.payslip_informacion_general_template()
        payslip_et = hr_payslip.payslip_empleador_template()
        payslip_tt = hr_payslip.payslip_trabajador_template()
        devengados = hr_payslip.generate_payslip_devengados()
        deducciones_total = self._get_deducciones_total_wizard()
        devengos_total = self._get_devengos_total_wizard()
        dates = self.DatesComplementaries()
        trabajador = ""

        dic = temp = template_cons = emps = {}
        for payslip in self.table_ids:
            comprobanteTotal = self._complements_second_decimal_wizard(
                (devengos_total[payslip.employee_id.id]['Total'] - deducciones_total[payslip.employee_id.id]['Total']))

            date_from_ = dates[payslip.employee_id.id]['date_from']
            date_to_ = dates[payslip.employee_id.id]['date_to']
            dian_documents = self.env['payroll.payroll.window'].search([('employee', '=', payslip.employee_id.id),
                                                                        ('date_from','>=', date_from_),
                                                                        ('date_to', '<=', date_to_)])

            if dian_documents:
                pass
            else:
                
                if payslip.employee_id.id in dic:
                    XmlNodo = 'NominaIndividual'
                   
                    dic[payslip.employee_id.id]['XmlNodo'] = XmlNodo
                    dic[payslip.employee_id.id]['CUNE'] = {}
                    dic[payslip.employee_id.id]['Periodo'] = self.generate_payslip_periodo_wizard(
                        payslip_pt, payslip)
                    dic[payslip.employee_id.id]['NumeroSecuenciaXML'] = {}
                    dic[payslip.employee_id.id]['LugarGeneracionXML'] = self.generate_payslip_lugar_generacion_xml_wizard(
                        payslip_lgt, payslip)
                    dic[payslip.employee_id.id]['ProveedorXML'] = {}
                    dic[payslip.employee_id.id]['CodigoQR'] = {}
                    dic[payslip.employee_id.id]['InformacionGeneral'] = {}
                    dic[payslip.employee_id.id]['Empleador'] = self.generate_payslip_empleador_wizard(
                        payslip_et, payslip)
                    dic[payslip.employee_id.id]['Trabajador'] = self.generate_payslip_trabajador_wizard(
                        payslip_tt, payslip)
                    dic[payslip.employee_id.id]['Metodo'] = str(
                        self._get_metodo_wizard(payslip))
                    dic[payslip.employee_id.id]['FechaPago'] = str(
                        hr_payslip._get_date_gen())
                    dic[payslip.employee_id.id]['Devengados'] = {}
                    dic[payslip.employee_id.id]['Deducciones'] = {}
                    dic[payslip.employee_id.id]['DevengadosTotal'] = hr_payslip._complements_second_decimal(devengos_total[payslip.employee_id.id]['Total'])
                    dic[payslip.employee_id.id]['DeduccionesTotal'] = hr_payslip._complements_second_decimal(deducciones_total[payslip.employee_id.id]['Total'])
                    dic[payslip.employee_id.id]['ComprobanteTotal'] = comprobanteTotal
                    dic[payslip.employee_id.id]['payslips_is'].append(payslip.id)

                else:
                    dic[payslip.employee_id.id] = {}
                    l10n_co_create = self._l10n_co_create_values_wizard(
                        payslip)
                    XmlNodo = 'NominaIndividual'
                    dic[payslip.employee_id.id] = {}
                    dic[payslip.employee_id.id]['XmlNodo'] = XmlNodo
                    dic[payslip.employee_id.id]['CUNE'] = {}
                    dic[payslip.employee_id.id]['Periodo'] = self.generate_payslip_periodo_wizard(
                        payslip_pt, payslip)
                    dic[payslip.employee_id.id]['NumeroSecuenciaXML'] = {}
                    dic[payslip.employee_id.id]['LugarGeneracionXML'] = self.generate_payslip_lugar_generacion_xml_wizard(
                        payslip_lgt, payslip)
                    dic[payslip.employee_id.id]['ProveedorXML'] = {}
                    dic[payslip.employee_id.id]['CodigoQR'] = {}
                    dic[payslip.employee_id.id]['InformacionGeneral'] = {}
                    dic[payslip.employee_id.id]['Empleador'] = self.generate_payslip_empleador_wizard(
                        payslip_et, payslip)
                    dic[payslip.employee_id.id]['Trabajador'] = self.generate_payslip_trabajador_wizard(
                        payslip_tt, payslip)
                    dic[payslip.employee_id.id]['Metodo'] = str(
                        self._get_metodo_wizard(payslip))
                    dic[payslip.employee_id.id]['FechaPago'] = str(
                        hr_payslip._get_date_gen())
                    dic[payslip.employee_id.id]['Devengados'] = {}
                    dic[payslip.employee_id.id]['Deducciones'] = {}
                    dic[payslip.employee_id.id]['DevengadosTotal'] = hr_payslip._complements_second_decimal(devengos_total[payslip.employee_id.id]['Total'])
                    dic[payslip.employee_id.id]['DeduccionesTotal'] = hr_payslip._complements_second_decimal(deducciones_total[payslip.employee_id.id]['Total'])
                    dic[payslip.employee_id.id]['ComprobanteTotal'] = comprobanteTotal
                    dic[payslip.employee_id.id]['payslips_is'] = [payslip.id]
        doc_dic = {}
        for documents_id in self.table_ids:
            if documents_id.employee_id.id in doc_dic:
                doc_dic[documents_id.employee_id.id]['IDS'].append(documents_id.id)
            else:
                doc_dic[documents_id.employee_id.id] = {}
                doc_dic[documents_id.employee_id.id]['IDS'] = [documents_id.id]
        consolidate = {}
        for documents_ids in self.consolidados_table_ids:
            consolidate[documents_ids.employee.id] = {}
            consolidate[documents_ids.employee.id] = documents_ids.id
        doc_id = {}
        for ids in self.table_ids:
            if ids.employee_id.id in doc_id:
                doc_id[ids.employee_id.id]['payslips_is'].append(ids.id)
                pass
            else:
                doc_id[ids.employee_id.id] = {}
                doc_id[ids.employee_id.id]['payslips_is'] = [ids.id]
                doc_id[ids.employee_id.id]['IDS'] = ids.employee_id.id_document_payroll

        template = hr_payslip.payslip_main_template()
        for x1, y1 in dic.items():
            if dic[x1]['Devengados'] == {}:   
                devs = doc_dic[x1]['IDS']
                dev = self.generate_payslip_devengados_wizard(devs)
                dic[x1]['Devengados'] = dev
            if dic[x1]['Deducciones'] == {}:   
                deds = doc_dic[x1]['IDS']
                ded = self.generate_payslip_deducciones_wizard(deds)
                dic[x1]['Deducciones'] = ded
            if dic[x1]['NumeroSecuenciaXML'] == {}:        
                dic_cons = self.generate_payslip_numero_secuencia_xml_wizard()
                template_cons = payslip_ns % dic_cons
                dic[x1]['NumeroSecuenciaXML'] = template_cons
            if dic[x1]['ProveedorXML'] == {}:
                dic[x1]['ProveedorXML'] = self.generate_payslip_proveedor_xml_wizard(
                        payslip_pxt, payslip, dic_cons)
            if dic[x1]['CUNE'] == {}:
                dic_cune = str(self._generate_CUNE_wizard(
                    payslip, dic_cons, hr_payslip._get_date_gen(), hr_payslip._get_time_colombia(), x1, doc_id[x1]['IDS'], devengos_total, deducciones_total))
                dic[x1]['CUNE'] = dic_cune
            if dic[x1]['CodigoQR'] == {}:
                dic_qr = str(self._get_QRCode_wizard(
                    payslip, dic_cons, hr_payslip._get_date_gen(), hr_payslip._get_time_colombia(), x1, doc_id[x1]['IDS'], devengos_total, deducciones_total))
                dic[x1]['CodigoQR'] = dic_qr
            if dic[x1]['InformacionGeneral'] == {}:
                dic_info, type_xml = self.generate_payslip_informacion_general_wizard(
                    payslip_igt, payslip, dic_cons, hr_payslip._get_date_gen(), hr_payslip._get_time_colombia(), x1, doc_id[x1]['IDS'], devengos_total, deducciones_total)
                dic[x1]['InformacionGeneral'] = dic_info
            xml = template % y1
            temp[x1] = xml
            self._SendDianDocuments(payslip, x1, temp, dic_cons)
            data_xml_document, attachment_id, msg, nombre_zip, estado = self.send_2_validate(payslip, temp, x1, dic_cons, dic_cune)
            self.ChargeDianDocuments(payslip, x1, dic_cons, temp, dic_cune, data_xml_document, attachment_id, msg, dic_cons, nombre_zip, type_xml, estado, doc_id[x1]['payslips_is'],consolidate[x1],dates)
        return """{
                    'name': 'l10n_co_payroll.payroll.window.tree',
                    'view_type': 'tree',
                    'view_mode': 'tree',
                    'view_id': self.env.ref('l10n_co_payroll.payroll_window_tree').id,
                    'res_model': 'payroll.payroll.window',
                    'context': {},
                    #'type': 'ir.actions.act_window',
                    'target': 'current',
                }"""

    def DatesComplementaries(self):
        dat = {}
        for payslip in self.table_ids:
            if payslip.employee_id.id in dat:
                date_t = payslip.date_to
                dat[payslip.employee_id.id]['date_to'] = date_t

            else:
                dat[payslip.employee_id.id] = {}
                date_f = payslip.date_from
                dat[payslip.employee_id.id]['date_from'] = date_f
                date_t = payslip.date_to
                dat[payslip.employee_id.id]['date_to'] = date_t
        return dat

    def generate_payslip_numero_secuencia_xml_wizard(self):
        template_cons1 = {}
        consecutivo = self._get_consecutivo_wizard()
        seq_id = self.env['ir.sequence'].search([('code', '=', 'ne.seq')])
        prefijo = seq_id.prefix
        numero = str(self._get_numero_wizard(consecutivo))
        template_cons1 = {
            'Consecutivo': numero,
            'Prefijo': str(prefijo),
            'Numero': str(consecutivo),
        }
        return template_cons1

    def _get_consecutivo_wizard(self):
        sequence = self.env['ir.sequence'].next_by_code('ne.seq')
        return sequence

    def _get_numero_wizard(self, seq):
        numero = seq.replace('NE', '')
        return numero

    def generate_payslip_periodo_wizard(self, payslip_pt, payslip):
        hr_payslip = self.env['hr.payslip']
        emp = payslip.employee_id.id
        dates = self.DatesComplementaries()
        date_gen = hr_payslip._get_date_gen()
        diff_date = dates[payslip.employee_id.id]['date_to'] - \
            payslip.contract_id.date_start
        fechaIngreso = str(payslip.contract_id.date_start)
        fechaLiquidacionInicio = str(
            dates[payslip.employee_id.id]['date_from'])
        fechaLiquidacionFin = str(dates[payslip.employee_id.id]['date_to'])
        tiempoLaborado = str(diff_date.days + 1)
        FechaRetiro = str(payslip.contract_id.fecha_causada_retiro)
        fechaGen = str(date_gen)
        payslip_periodo = payslip_pt % {
            'FechaIngreso': fechaIngreso,
            'FechaLiquidacionInicio': fechaLiquidacionInicio,
            'FechaRetiro': FechaRetiro,
            'FechaLiquidacionFin': fechaLiquidacionFin,
            'TiempoLaborado': tiempoLaborado,
            'FechaGen': fechaGen
        }
        return payslip_periodo

    def generate_payslip_lugar_generacion_xml_wizard(self, payslip_lgt, payslip):
        pais = str(payslip.company_id.country_id.code)
        departamentoEstado = str(payslip.company_id.state_id.l10n_co_edi_code)
        municipioCiudad = str(payslip.company_id.partner_id.xcity.code)
        lugar_generacion_xml = payslip_lgt % {
            'Pais': pais,
            'DepartamentoEstado': departamentoEstado,
            'MunicipioCiudad': municipioCiudad,
        }
        return lugar_generacion_xml

    def generate_payslip_proveedor_xml_wizard(self, payslip_pxt, payslip, dic_cons):
        nit = str(payslip.company_id.partner_id.xidentification)
        dv = str(payslip.company_id.partner_id.dv)
        softwareID = str(
            payslip.company_id.software_identification_code_payroll)
        softwareSC = str(self._generate_software_security_code_wizard(payslip, dic_cons))
        proveedor_xml = payslip_pxt % {
            'NIT': nit,
            'DV': dv,
            'SoftwareID': softwareID,
            'SoftwareSC': softwareSC
        }
        return proveedor_xml

    def _generate_software_security_code_wizard(self, payslip, dic_cons):
        company = self.env.user.company_id
        software_identification_code = company.software_identification_code_payroll
        software_pin = company.software_pin_payroll
        NroDocumento = dic_cons['Numero']
        software_security_code = hashlib.sha384(
             (software_identification_code + software_pin + NroDocumento).encode())
        software_security_code = software_security_code.hexdigest()
        #software_security_code = '123456789'
        return software_security_code

    
    def _create_payslip_xml_template(self, payslip):
        '''Creates and returns a dictionnary containing 'cfdi' if the cfdi is well created, 'error' otherwise.
        '''
        self.ensure_one()
        qweb = self.env['ir.qweb']
        values = self._l10n_co_create_values_wizard(payslip)
        nomina = qweb.render(PAYSLIP_TEMPLATE, values=values)
        return nomina

    
    def _l10n_co_create_values_wizard(self, payslip):
        '''Create the values to fill the CFDI template.
        '''
        emp = payslip.employee_id.id
        dates = self.DatesComplementaries()
        hr_payslip = self.env['hr.payslip']
        self.ensure_one()
        dian_constants = self._get_dian_constants(payslip)
        document_constant = self._generate_data_constants_document()
        gen_date = hr_payslip._get_date_gen()
        gen_hours = hr_payslip._get_time_colombia()
        values = {
            'record': payslip,
            'date_from': dates[payslip.employee_id.id]['date_from'],
            'date_to': dates[payslip.employee_id.id]['date_to'],
            'fiscal_position': payslip.company_id.partner_id.property_account_position_id,
            'payment_method': payslip.payment_method,
            'dian_conts': dian_constants,
            'document_conts': document_constant,
            'gen_date': gen_date,
            'gen_hours': gen_hours
        }
        return values

    def _complements_second_decimal_wizard(self, amount):
        amount_dec = round(((amount - int(amount)) * 100.0), 2)
        amount_int = int(amount_dec)
        if amount_int % 10 == 0:
            amount = str(amount) + '0'
        else:
            amount = str(amount)
        return amount

    def _complements_second_decimal_total_wizard(self, amount):
        amount = str(int(amount)) + (str((amount - int(amount)))[1:4])
        amount = self._complements_second_decimal_wizard(float(amount))
        return amount

    def _devengados_second_decimal_wizard(self, x1, devengos_total):
        dev_second_decimal = self._complements_second_decimal_wizard(
            devengos_total[x1]['Total'])
        return dev_second_decimal

    def _deducciones_second_decimal_wizard(self, x1, deducciones_total):
        ded_second_decimal = self._complements_second_decimal_wizard(
            deducciones_total[x1]['Total'])
        return ded_second_decimal

    def _generate_CUNE_wizard(self, payslip, dic_cons, gen_date, gen_hours, x1, ids, devengos_total, deducciones_total):
        hr_payslip = self.env['hr.payslip']
        NumNE = dic_cons['Numero']
        FecNE = str(gen_date)
        HorNE = str(gen_hours)
        ValDev = payslip.credit_note and payslip.note_type == "2" and '0.00' or self._devengados_second_decimal_wizard(x1,devengos_total)
        ValDed = payslip.credit_note and payslip.note_type == "2" and '0.00' or self._deducciones_second_decimal_wizard(x1,deducciones_total)
        total_devengos = devengos_total
        total_deducciones = deducciones_total
        ValTolNE = payslip.credit_note and payslip.note_type == "2" and '0.00' or self._complements_second_decimal_wizard(
            (total_devengos[x1]['Total'] - total_deducciones[x1]['Total']))
        NitNE = str(payslip.company_id.partner_id.xidentification)
        DocEmp = payslip.credit_note and '0' and payslip.note_type == "2" or str(
            ids)
        TipoXML = payslip.credit_note and '103' or '102'
        SoftwarePin = payslip.company_id.software_pin_payroll
        TipAmb = str(payslip.company_id.is_test)
        CUNE = NumNE + FecNE + HorNE + str(ValDev)+str(ValDed)+ValTolNE+NitNE + DocEmp + TipoXML + SoftwarePin + TipAmb
              #NE472 2022-09-20 09:13:48-05:00 1117172.00 80000.00 1037172.00 901228066 1085342252 102 22222 2
        hash_CUNE = hashlib.sha384(CUNE.encode())
        hash_CUNE = hash_CUNE.hexdigest()

        return hash_CUNE

    @api.model
    def _get_QRCode_wizard(self, payslip, dic_cons, gen_date, gen_hours, x1, ids, devengos_total, deducciones_total):
        cune = self._generate_CUNE_wizard(
            payslip, dic_cons, gen_date, gen_hours, x1, ids, devengos_total, deducciones_total)
        qrcode = ''
        if payslip.company_id.is_test == '2':
            qrcode = 'https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey='+cune
        else:
            qrcode = 'https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey='+cune
        return qrcode

    def generate_payslip_informacion_general_wizard(self, payslip_igt, payslip, dic_cons, gen_date, gen_hours, x1, ids, devengos_total, deducciones_total):
        hr_payslip = self.env['hr.payslip']
        ambiente = str(payslip.company_id.is_test)
        tipoXML = str(self._get_tipo_xml_wizard(payslip))
        CUNE = str(self._generate_CUNE_wizard(
            payslip, dic_cons, gen_date, gen_hours, x1, ids, devengos_total, deducciones_total))
        fechaGen = str(hr_payslip._get_date_gen())
        horaGen = str(hr_payslip._get_time_colombia())
        self.update({'cune': CUNE, 'date_send_dian': fechaGen})
        periodoNomina = str(self._get_periodo_nomina_wizard(payslip))
        TipoMoneda = str(self._get_currency_wizard(payslip))

        informacion_general = payslip_igt % {
            'InfoLiteral': payslip.credit_note and 'V1.0: Nota de Ajuste de Documento Soporte de Pago de Nómina Electrónica' or 'V1.0: Documento Soporte de Pago de Nómina Electrónica',
            'Ambiente': ambiente,
            'TipoXML': tipoXML,
            'CUNE': CUNE,
            'FechaGen': fechaGen,
            'HoraGen': horaGen,
            'PeriodoNomina': periodoNomina,
            'TipoMoneda': TipoMoneda
        }

        return informacion_general, tipoXML

    def _get_tipo_xml_wizard(self, payslip):
        tipoXML = payslip.credit_note and '103' or '102'
        return tipoXML

    def _get_periodo_nomina_wizard(self, payslip):
        periodo_nomina = payslip.contract_id.payroll_period
        return periodo_nomina

    def _get_currency_wizard(self, payslip):
        currency = payslip.company_id.currency_id.name
        return currency

    def generate_payslip_empleador_wizard(self, payslip_et, payslip):
        RazonSocial = str(payslip.company_id.name)
        nit = str(payslip.company_id.partner_id.xidentification)
        dv = str(payslip.company_id.partner_id.dv)
        pais = str(payslip.company_id.country_id.code)
        departamentoEstado = str(payslip.company_id.state_id.l10n_co_edi_code)
        municipioCiudad = str(payslip.company_id.partner_id.xcity.code)
        direccion = str(payslip.company_id.street)
        empleador = payslip_et % {
            'RazonSocial': RazonSocial,
            'NIT': nit,
            'DV': dv,
            'Pais': pais,
            'DepartamentoEstado': departamentoEstado,
            'MunicipioCiudad': municipioCiudad,
            'Direccion': direccion,
        }
        return empleador

    def generate_payslip_trabajador_wizard(self, payslip_tt, payslip):
        tipoTrabajador = str(payslip.employee_id.employee_type)
        subTipoTrabajador = str(payslip.employee_id.employee_subtype)
        altoRiesgoPension = str(
            payslip.employee_id.high_risk and 'true' or 'false')
        tipoDocumento = str(payslip.employee_id.document_type)
        numeroDocumento = str(payslip.employee_id.id_document_payroll)
        primerApellido = str(payslip.employee_id.second_namef)
        segundoApellido = str(payslip.employee_id.second_namem)
        primerNombre = str(payslip.employee_id.first_name)
        otrosNombres = str(payslip.employee_id.second_name)
        lugarTrabajoPais = str(payslip.employee_id.address_id.country_id.code)
        lugarTrabajoDepartamentoEstado = str(
            payslip.employee_id.address_id.state_id.l10n_co_edi_code)
        lugarTrabajoMunicipioCiudad = str(
            payslip.employee_id.address_id.xcity.code)
        lugarTrabajoDireccion = str(payslip.employee_id.address_id.street)
        salarioIntegral = str(payslip.it_is_integral and 'true' or 'false')
        tipoContrato = str(payslip.contract_id.contract_type)
        sueldo = str(payslip.contract_id.wage)
        codigoTrabajador = str(payslip.employee_id.id)

        employee_data = {
            'TipoTrabajador': tipoTrabajador,
            'SubTipoTrabajador': subTipoTrabajador,
            'AltoRiesgoPension': altoRiesgoPension,
            'TipoDocumento': tipoDocumento,
            'NumeroDocumento': numeroDocumento,
            'PrimerApellido': primerApellido,
            'SegundoApellido': segundoApellido,
            'PrimerNombre': primerNombre,
            'OtrosNombres': otrosNombres,
            'LugarTrabajoPais': lugarTrabajoPais,
            'LugarTrabajoDepartamentoEstado': lugarTrabajoDepartamentoEstado,
            'LugarTrabajoMunicipioCiudad': lugarTrabajoMunicipioCiudad,
            'LugarTrabajoDireccion': lugarTrabajoDireccion,
            'SalarioIntegral': salarioIntegral,
            'TipoContrato': tipoContrato,
            'Sueldo': sueldo,
            'CodigoTrabajador': codigoTrabajador,
        }

        trabajador = payslip_tt % employee_data
        otros_nombres = """
                    OtrosNombres="%(OtrosNombres)s"
                    """
        name2 = otrosNombres
        otros_nombres = str(otros_nombres) % {'OtrosNombres': name2}

        segundo_ap = """
                    SegundoApellido="%(SegundoApellido)s"
                    """
        last_name2 = segundoApellido
        segundo_ap = str(segundo_ap) % {'SegundoApellido': last_name2}

        if payslip.employee_id.second_name == False:
            trabajador = trabajador.replace('/name2/', '')
        else:
            trabajador = trabajador.replace('/name2/', otros_nombres)
        if payslip.employee_id.second_namem == False:
            trabajador = trabajador.replace('/last_name2/', '')
        else:
            trabajador = trabajador.replace('/last_name2/', segundo_ap)

        return trabajador

    def _get_metodo_wizard(self, payslip):
        metodo = payslip.payment_method
        return metodo

    def generate_payslip_devengados_wizard(self, nominas):
        
        temp_d = dev = {}
        dic_temp_dev = {}
        datos = []
        pago = amount = bon = bon_ns = s = ns = asal = ans = numero_liquidacion_prima = PagoIntereses = PagoCesantias = prima = \
            numero_de_dias_prima = sueldo_trabajado = 0
            
        for i in range(0, len(nominas)):
            datos.append(self.env['hr.payslip'].browse(nominas[i]))
                  
        for j in range(0, len(datos)):
            nom = datos[j]
            hed = hen = hrn = heddf = hrddf = hendf = hrndf = cesantias = deveng = incapacidad_eps = incapacidad_arl = \
            licenciasm = licencias_p = licencias_r = licenciasnr = vacaciones = tem_prima = tem_prima_liq = tem_cesan = \
            pagotercero = pagoterceros = ""
            if nom.employee_id.id in dev:
                for work_days in nom.worked_days_line_ids:
                    if work_days.code == 'WORK100':
                        dev[nom.employee_id.id]['DiasTrabajados'] += int(work_days.number_of_days)
                for line_values in nom.line_ids:
                    if line_values.code == '1100' or line_values.code == '1200' or line_values.code == '1300':
                        sueldo_trabajado += line_values.total
                        dev[nom.employee_id.id]['SueldoTrabajado'] = {}
                    if line_values.code == '1105' or line_values.code == '1205' or line_values.code == '1305':
                        dev[nom.employee_id.id]['AuxilioTransporte'] += line_values.total
                    if line_values.code == '1103-1' or line_values.code == '1203-1' or line_values.code == '1303-1':
                        if 'ViaticoManutAlojS' in dev[nom.employee_id.id]:
                            dev[nom.employee_id.id]['ViaticoManutAlojS'] += line_values.total
                        else:
                            dev[nom.employee_id.id]['ViaticoManutAlojS'] = line_values.total
                    if line_values.code == '1103-2' or line_values.code == '1203-2' or line_values.code == '1303-2':
                        if 'ViaticoManutAlojNS' in dev[nom.employee_id.id]:
                            dev[nom.employee_id.id]['ViaticoManutAlojS'] += line_values.total
                        else:
                            dev[nom.employee_id.id]['ViaticoManutAlojNS'] = line_values.total
                    if line_values.code == '1107-4' or line_values.code == '1207-4' or line_values.code == '1307-4':
                        # Horas Extras Diurna normal
                        for overtime in nom.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "hora_extra_diurna_normal":
                                hed += '<HED HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'cantidad': int_hour,
                                                                                                                                                                            'portcentaje': '25.00',
                                                                                                                                                                            'pago': overtime.pago}
                        dev[nom.employee_id.id]['HEDs'] = hed
                    if line_values.code == '1107-2' or line_values.code == '1207-2' or line_values.code == '1307-2':
                        # Horas Extras Nocturna normal
                        for overtime in self.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "hora_extra_nocturno":
                                hen += '<HEN HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'cantidad': int_hour,
                                                                                                                                                                            'portcentaje': '75.00',
                                                                                                                                                                            'pago': overtime.pago}
                        dev[nom.employee_id.id]['HEDs'] = hen
                    if line_values.code == '1107-1' or line_values.code == '1207-1' or line_values.code == '1307-1':
                        # Recargo Nocturno normal
                        for overtime in nom.overtime_ids: 
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "recargo_nocturno":
                                hrn += '<HRN HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'cantidad': int_hour,
                                                                                                                                                                            'portcentaje': '35.00',
                                                                                                                                                                            'pago': overtime.pago}
                        dev[nom.employee_id.id]['HRNs'] = hrn
                    if line_values.code == '1107-6' or line_values.code == '1207-6' or line_values.code == '1307-6':
                        # Horas Extras Diurna festiva
                        for overtime in nom.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "hora_extra_diurna_festiva":
                                heddf += '<HEDDF HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'cantidad': int_hour,
                                                                                                                                                                                'portcentaje': '100.00',
                                                                                                                                                                                'pago': overtime.pago}
                        dev[nom.employee_id.id]['HEDDFs'] = heddf
                    if line_values.code == '1107-3' or line_values.code == '1207-3' or line_values.code == '1307-3':
                        # Recargo diurno festivo
                        for overtime in nom.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "h_diurna_festiva":
                                hrddf += '<HRDDF HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'cantidad': int_hour,
                                                                                                                                                                                'portcentaje': '75.00',
                                                                                                                                                                                'pago': overtime.pago}
                        dev[nom.employee_id.id]['HRDDFs'] = hrddf
                    if line_values.code == '1107-7' or line_values.code == '1207-7' or line_values.code == '1307-7':
                        # Horas Extras Diurna festiva
                        for overtime in nom.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "trabajo_extra_nocturno_domingos_festivos":
                                hendf += '<HENDF HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'cantidad': int_hour,
                                                                                                                                                                                'portcentaje': '150.00',
                                                                                                                                                                                'pago': overtime.pago}
                        dev[nom.employee_id.id]['HENDFs'] = hendf
                    if line_values.code == '1107-5' or line_values.code == '1207-5' or line_values.code == '1307-5':
                        # Recargo Nocturno normal
                        for overtime in nom.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "recargo_nocturna_f_d":
                                hrndf += '<HRNDF HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'cantidad': int_hour,
                                                                                                                                                                                'portcentaje': '110.00',
                                                                                                                                                                                'pago': overtime.pago}
                        dev[nom.employee_id.id]['HRNDFs'] = hrndf

                    if line_values.code == '1107-1' or line_values.code == '1207-1' or line_values.code == '1307-1':
                        for overtime in nom.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "recargo_nocturno":
                                hrn += '<HRN HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'cantidad': int_hour,
                                                                                                                                                                            'portcentaje': '35.00',
                                                                                                                                                                            'pago': overtime.pago}
                        dev[nom.employee_id.id]['HRNs'] = hrn

                    if line_values.code == '1511':
                        vacaciones = '<Vacaciones><VacacionesComunes FechaInicio="' + \
                            str(nom.fecha_inicio_vac) + '" FechaFin="' + \
                            str(nom.fecha_fin_vac) + '" Cantidad="' + str(int(nom.numero_dias_vac_dis)
                                                                        ) + '" Pago="' + str(line_values.total) + '"/> </Vacaciones>'
                        dev[nom.employee_id.id]['VacacionesComun'] = vacaciones

                    if line_values.code == '1116' or line_values.code == '1216' or line_values.code == '1316':
                        if nom.vacaciones_compensadas:
                            _dias = int(nom.numero_dias_vac_com)
                            if _dias == 0:
                                _dias = 1
                            vacaciones = '<Vacaciones><VacacionesCompensadas Cantidad="' + \
                                str(_dias) + '" Pago="' + \
                                str(line_values.total) + '"/> </Vacaciones>'
                            dev[nom.employee_id.id]['VacacionesComp'] = vacaciones

                        else:
                            for lines_leaves in nom.leaves_ids:
                                if lines_leaves.holiday_status_id.name == "VACACIONES DE DISFRUTE":
                                    _fecha_inicio = lines_leaves.request_date_from if lines_leaves.request_date_from >= nom.date_from else nom.date_from
                                    _fecha_fin = lines_leaves.request_date_to if lines_leaves.request_date_to <= nom.date_to else nom.date_to
                                    for days in nom.worked_days_line_ids:
                                        if days.code == 'VACACIONES DE DISFRUTE':
                                            cantidad = int(days.number_of_days)
                                    vacaciones = '<Vacaciones><VacacionesComunes FechaInicio="' + \
                                        str(_fecha_inicio) + '" FechaFin="' + \
                                        str(_fecha_fin) + '" Cantidad="' + str(cantidad) + \
                                        '" Pago="' + \
                                        str(line_values.total) + \
                                        '"/> </Vacaciones>'
                            dev[nom.employee_id.id]['VacacionesComun'] = vacaciones

                    if line_values.code == '1118' or line_values.code == '1218' or line_values.code == '1318':
                        prima = line_values.total
                        for prima_ids in nom.contract_id.prima_acumuladas_ids:
                            if prima_ids.dias_pagados != 0 and prima_ids.fecha_desde == self.date_from:
                                numero_de_dias_prima = prima_ids.dias_pagados

                    if line_values.code == '1120' or line_values.code == '1220' or line_values.code == '1320':
                        PagoIntereses = line_values.total

                    if line_values.code == '1119' or line_values.code == '1219' or line_values.code == '1319':
                        PagoCesantias = line_values.total

                    if line_values.code == '1005':
                        pago = line_values.total
                        for line_eps in nom.line_ids:
                            if line_eps.code == '1006':
                                pago += line_eps.total
                        for lines_leaves in nom.leaves_ids:
                            if lines_leaves.holiday_status_id.name == "EPS":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                fecha_inicio = lines_leaves.date_from
                                fecha_fin = lines_leaves.date_to
                                tipo = lines_leaves.type_leave_disease_dian
                                incapacidad_eps += '<Incapacidad FechaInicio="' + str(fecha_inicio.strftime("%Y-%m-%d")) + '" FechaFin="' + str(fecha_fin.strftime("%Y-%m-%d")) + '" Cantidad="' + str(
                                    int(cantidad)) + '" Tipo="' + str(tipo) + '" Pago="' + str(round(pago, 2)) + '" />'
                        if 'Incapacidad_eps' in dev[nom.employee_id.id]:
                            dev[nom.employee_id.id]['Incapacidad_eps'] = dev[nom.employee_id.id]['Incapacidad_eps'] + incapacidad_eps
                        else:
                            dev[nom.employee_id.id]['Incapacidad_eps'] = incapacidad_eps

                    if line_values.code == '1002':
                        for lines_leaves in nom.leaves_ids:
                            pago = line_values.total
                            if lines_leaves.holiday_status_id.name == "incapacidad_ARL":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                fecha_inicio = lines_leaves.date_from
                                fecha_fin = lines_leaves.date_to
                                tipo = lines_leaves.type_leave_disease_dian
                                incapacidad_arl += '<Incapacidad FechaInicio="' + str(fecha_inicio.strftime("%Y-%m-%d")) + '" FechaFin="' + str(fecha_fin.strftime("%Y-%m-%d")) + '" Cantidad="' + str(
                                    int(cantidad)) + '" Tipo="' + str(tipo) + '" Pago="' + str(round(pago)) + '" />'
                        if 'Incapacidad_arl' in dev[nom.employee_id.id]:
                            dev[nom.employee_id.id]['Incapacidad_arl'] = dev[nom.employee_id.id]['Incapacidad_arl'] + incapacidad_arl
                        else:
                            dev[nom.employee_id.id]['Incapacidad_arl'] = incapacidad_arl

                    if line_values.code == '1001':
                        for lines_leaves in nom.leaves_ids:
                            if lines_leaves.holiday_status_id.name == "EPS_maternidad":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                licenciasm += '<LicenciaMP FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s" Pago="%(pago)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                            'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                            'cantidad': lines_leaves.duration_display,
                                                                                                                                                            'pago': line_values.total}
                        if 'LicenciaM' in dev[nom.employee_id.id]:
                            dev[nom.employee_id.id]['LicenciaM'] = dev[nom.employee_id.id]['LicenciaM'] + licenciasm
                        else:
                            dev[nom.employee_id.id]['LicenciaM'] = licenciasm

                    if line_values.code == '1003':
                        for lines_leaves in nom.leaves_ids:
                            if lines_leaves.holiday_status_id.name == "EPS_paternidad":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                licencias_p += '<LicenciaMP FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s" Pago="%(pago)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                                'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                                'cantidad': lines_leaves.duration_display,
                                                                                                                                                                'pago': line_values.total}
                        if 'LicenciaP' in dev[nom.employee_id.id]:
                            dev[nom.employee_id.id]['LicenciaP'] = dev[nom.employee_id.id]['LicenciaP'] + licencias_p
                        else:
                            dev[nom.employee_id.id]['LicenciaP'] = licencias_p

                    if line_values.code == '1004':
                        for lines_leaves in nom.leaves_ids:
                            if lines_leaves.holiday_status_id.name == "luto":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                licencias_r += '<LicenciaR FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s" Pago="%(pago)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                            'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                            'cantidad': lines_leaves.duration_display,
                                                                                                                                                            'pago': line_values.total}
                        if 'LicenciaR' in dev[nom.employee_id.id]:
                            dev[nom.employee_id.id]['LicenciaR'] = dev[nom.employee_id.id]['LicenciaR'] + licencias_r
                        else:
                            dev[nom.employee_id.id]['LicenciaR'] = licencias_r

                    if line_values.code == '1010':
                        for lines_leaves in nom.leaves_ids:
                            if lines_leaves.holiday_status_id.name == "AUSENCIA_NO_REMUNERADO":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                licenciasnr += '<LicenciaNR FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                'cantidad': str(int(cantidad))}
                        if 'LicenciaNR' in dev[nom.employee_id.id]:
                            dev[nom.employee_id.id]['LicenciaNR'] = dev[nom.employee_id.id]['LicenciaNR'] + licenciasnr
                        else:
                            dev[nom.employee_id.id]['LicenciaNR'] = licenciasnr


                    

                    if line_values.code == '1102-1' or line_values.code == '1202-1' or line_values.code == '1302-1':
                        bon = bon + line_values.total
                        dev[nom.employee_id.id]['BonificacionS'] = {}

                    if line_values.code == '1102-2' or line_values.code == '1202-2' or line_values.code == '1302-2':
                        bon_ns = bon_ns + line_values.total
                        dev[nom.employee_id.id]['BonificacionNS'] = {}

                    if line_values.code == '1121-1' or line_values.code == '1221-1' or line_values.code == '1321-1':
                        s = s + line_values.total
                        dev[nom.employee_id.id]['BonoSal'] = {}

                    if line_values.code == '1121-2' or line_values.code == '1221-2' or line_values.code == '1321-2':
                        ns = ns + line_values.total
                        dev[nom.employee_id.id]['BonoNSal'] = {}

                    if line_values.code == '1121-3' or line_values.code == '1221-3' or line_values.code == '1321-3':
                        asal = asal + line_values.total
                        dev[nom.employee_id.id]['BonoAlimeS'] = {}

                    if line_values.code == '1121-4' or line_values.code == '1221-4' or line_values.code == '1321-4':
                        ans = ans + line_values.total
                        dev[nom.employee_id.id]['BonoAlimeNS'] = {}

                    if line_values.code == '2112':
                        pagotercero = '<PagoTercero>' + \
                            str(line_values.total) + '</PagoTercero>'
                        dev[nom.employee_id.id]['PagoTercero'] = pagotercero

            else:
                dev[nom.employee_id.id] = {}
                pago = amount = bon = bon_ns = s = ns = asal = ans = numero_liquidacion_prima = PagoIntereses = PagoCesantias = prima = \
                numero_de_dias_prima = sueldo_trabajado = 0
                for work_days in nom.worked_days_line_ids:
                    if work_days.code == 'WORK100':
                        dev[nom.employee_id.id]['DiasTrabajados'] = int(work_days.number_of_days)
                for line_values in nom.line_ids:
                    if line_values.code == '1100' or line_values.code == '1200' or line_values.code == '1300':
                        sueldo_trabajado = line_values.total
                        dev[nom.employee_id.id]['SueldoTrabajado'] = {}
                    if line_values.code == '1105' or line_values.code == '1205' or line_values.code == '1305':
                        dev[nom.employee_id.id]['AuxilioTransporte'] = line_values.total
                    if line_values.code == '1103-1' or line_values.code == '1203-1' or line_values.code == '1303-1':
                        dev[nom.employee_id.id]['ViaticoManutAlojS'] = line_values.total
                    if line_values.code == '1103-2' or line_values.code == '1203-2' or line_values.code == '1303-2':
                        dev[nom.employee_id.id]['ViaticoManutAlojNS'] = line_values.total
                    if line_values.code == '1107-4' or line_values.code == '1207-4' or line_values.code == '1307-4':
                        # Horas Extras Diurna normal
                        for overtime in nom.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "hora_extra_diurna_normal":
                                hed += '<HED HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'cantidad': int_hour,
                                                                                                                                                                            'portcentaje': '25.00',
                                                                                                                                                                            'pago': overtime.pago}
                        dev[nom.employee_id.id]['HEDs'] = hed
                    if line_values.code == '1107-2' or line_values.code == '1207-2' or line_values.code == '1307-2':
                        # Horas Extras Nocturna normal
                        for overtime in self.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "hora_extra_nocturno":
                                hen += '<HEN HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'cantidad': int_hour,
                                                                                                                                                                            'portcentaje': '75.00',
                                                                                                                                                                            'pago': overtime.pago}
                        dev[nom.employee_id.id]['HEDs'] = hen
                    if line_values.code == '1107-1' or line_values.code == '1207-1' or line_values.code == '1307-1':
                        # Recargo Nocturno normal
                        for overtime in self.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "recargo_nocturno":
                                hrn += '<HRN HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                            'cantidad': int_hour,
                                                                                                                                                                            'portcentaje': '35.00',
                                                                                                                                                                            'pago': overtime.pago}
                        dev[nom.employee_id.id]['HRNs'] = hrn
                    if line_values.code == '1107-6' or line_values.code == '1207-6' or line_values.code == '1307-6':
                        # Horas Extras Diurna festiva
                        for overtime in self.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "hora_extra_diurna_festiva":
                                heddf += '<HEDDF HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'cantidad': int_hour,
                                                                                                                                                                                'portcentaje': '100.00',
                                                                                                                                                                                'pago': overtime.pago}
                        dev[nom.employee_id.id]['HEDDFs'] = heddf
                    if line_values.code == '1107-3' or line_values.code == '1207-3' or line_values.code == '1307-3':
                        # Recargo diurno festivo
                        for overtime in self.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "h_diurna_festiva":
                                hrddf += '<HRDDF HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'cantidad': int_hour,
                                                                                                                                                                                'portcentaje': '75.00',
                                                                                                                                                                                'pago': overtime.pago}
                        dev[nom.employee_id.id]['HRDDFs'] = hrddf
                    if line_values.code == '1107-7' or line_values.code == '1207-7' or line_values.code == '1307-7':
                        # Horas Extras Diurna festiva
                        for overtime in self.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "trabajo_extra_nocturno_domingos_festivos":
                                hendf += '<HENDF HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'cantidad': int_hour,
                                                                                                                                                                                'portcentaje': '150.00',
                                                                                                                                                                                'pago': overtime.pago}
                        dev[nom.employee_id.id]['HENDFs'] = hendf
                    if line_values.code == '1107-5' or line_values.code == '1207-5' or line_values.code == '1307-5':
                        # Recargo Nocturno normal
                        for overtime in self.overtime_ids:
                            int_hour = int(overtime.num_of_hours)
                            if overtime.num_of_hours > int_hour:
                                int_hour = int_hour + 1
                            if overtime.tipo_de_hora_extra == "recargo_nocturna_f_d":
                                hrndf += '<HRNDF HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                                'cantidad': int_hour,
                                                                                                                                                                                'portcentaje': '110.00',
                                                                                                                                                                                'pago': overtime.pago}
                        dev[nom.employee_id.id]['HRNDFs'] = hrndf

                    if line_values.code == '1511':
                        vacaciones = '<Vacaciones><VacacionesComunes FechaInicio="' + \
                            str(nom.fecha_inicio_vac) + '" FechaFin="' + \
                            str(nom.fecha_fin_vac) + '" Cantidad="' + str(int(nom.numero_dias_vac_dis)
                                                                        ) + '" Pago="' + str(line_values.total) + '"/> </Vacaciones>'
                        dev[nom.employee_id.id]['VacacionesComun'] = vacaciones

                    if line_values.code == '1116' or line_values.code == '1216' or line_values.code == '1316':
                        if nom.vacaciones_compensadas:
                            _dias = int(nom.numero_dias_vac_com)
                            if _dias == 0:
                                _dias = 1
                            vacaciones = '<Vacaciones><VacacionesCompensadas Cantidad="' + \
                                str(_dias) + '" Pago="' + \
                                str(line_values.total) + '"/> </Vacaciones>'
                            dev[nom.employee_id.id]['VacacionesComp'] = vacaciones

                        else:
                            for lines_leaves in nom.leaves_ids:
                                if lines_leaves.holiday_status_id.name == "VACACIONES DE DISFRUTE":
                                    _fecha_inicio = lines_leaves.request_date_from if lines_leaves.request_date_from >= nom.date_from else nom.date_from
                                    _fecha_fin = lines_leaves.request_date_to if lines_leaves.request_date_to <= nom.date_to else nom.date_to
                                    for days in nom.worked_days_line_ids:
                                        if days.code == 'VACACIONES DE DISFRUTE':
                                            cantidad = int(days.number_of_days)
                                    vacaciones = '<Vacaciones><VacacionesComunes FechaInicio="' + \
                                        str(_fecha_inicio) + '" FechaFin="' + \
                                        str(_fecha_fin) + '" Cantidad="' + str(cantidad) + \
                                        '" Pago="' + \
                                        str(line_values.total) + \
                                        '"/> </Vacaciones>'
                            dev[nom.employee_id.id]['VacacionesComun'] = vacaciones

                    if line_values.code == '1118' or line_values.code == '1218' or line_values.code == '1318':
                        prima = line_values.total
                        for prima_ids in nom.contract_id.prima_acumuladas_ids:
                            if prima_ids.dias_pagados != 0 and prima_ids.fecha_desde == self.date_from:
                                numero_de_dias_prima = prima_ids.dias_pagados

                    if line_values.code == '1120' or line_values.code == '1220' or line_values.code == '1320':
                        PagoIntereses = line_values.total

                    if line_values.code == '1119' or line_values.code == '1219' or line_values.code == '1319':
                        PagoCesantias = line_values.total

                    if line_values.code == '1005':
                        pago = line_values.total
                        for line_eps in nom.line_ids:
                            if line_eps.code == '1006':
                                pago += line_eps.total
                        for lines_leaves in nom.leaves_ids:
                            if lines_leaves.holiday_status_id.name == "EPS":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                fecha_inicio = lines_leaves.date_from
                                fecha_fin = lines_leaves.date_to
                                tipo = lines_leaves.type_leave_disease_dian
                                #pago = lines_leaves.pago
                                incapacidad_eps += '<Incapacidad FechaInicio="' + str(fecha_inicio.strftime("%Y-%m-%d")) + '" FechaFin="' + str(fecha_fin.strftime("%Y-%m-%d")) + '" Cantidad="' + str(
                                    int(cantidad)) + '" Tipo="' + str(tipo) + '" Pago="' + str(round(pago, 2)) + '" />'
                        dev[nom.employee_id.id]['Incapacidad_eps'] = incapacidad_eps

                    if line_values.code == '1002':
                        for lines_leaves in nom.leaves_ids:
                            pago = line_values.total
                            if lines_leaves.holiday_status_id.name == "incapacidad_ARL":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                fecha_inicio = lines_leaves.date_from
                                fecha_fin = lines_leaves.date_to
                                tipo = lines_leaves.type_leave_disease_dian
                                incapacidad_arl += '<Incapacidad FechaInicio="' + str(fecha_inicio.strftime("%Y-%m-%d")) + '" FechaFin="' + str(fecha_fin.strftime("%Y-%m-%d")) + '" Cantidad="' + str(
                                    int(cantidad)) + '" Tipo="' + str(tipo) + '" Pago="' + str(round(pago)) + '" />'
                        dev[nom.employee_id.id]['Incapacidad_arl'] = incapacidad_arl

                    if line_values.code == '1001':
                        for lines_leaves in nom.leaves_ids:
                            if lines_leaves.holiday_status_id.name == "EPS_maternidad":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                licenciasm += '<LicenciaMP FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s" Pago="%(pago)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                            'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                            'cantidad': lines_leaves.duration_display,
                                                                                                                                                            'pago': line_values.total}
                        dev[nom.employee_id.id]['LicenciaM'] = licenciasm

                    if line_values.code == '1003':
                        for lines_leaves in nom.leaves_ids:
                            if lines_leaves.holiday_status_id.name == "EPS_paternidad":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                licencias_p += '<LicenciaMP FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s" Pago="%(pago)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                                'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                                'cantidad': lines_leaves.duration_display,
                                                                                                                                                                'pago': line_values.total}
                        dev[nom.employee_id.id]['LicenciaP'] = licencias_p

                    if line_values.code == '1004':
                        for lines_leaves in nom.leaves_ids:
                            if lines_leaves.holiday_status_id.name == "luto":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float( str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                licencias_r += '<LicenciaR FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s" Pago="%(pago)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                            'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                            'cantidad': lines_leaves.duration_display,
                                                                                                                                                            'pago': line_values.total}
                        dev[nom.employee_id.id]['LicenciaR'] = licencias_r

                    if line_values.code == '1010':
                        for lines_leaves in nom.leaves_ids:
                            if lines_leaves.holiday_status_id.name == "AUSENCIA_NO_REMUNERADO":
                                cantidad = lines_leaves.duration_display
                                try:
                                    cantidad = float(str(cantidad).replace(" day(s)", ""))
                                except:
                                    try:
                                        cantidad = float(str(cantidad).replace(" días", ""))
                                    except:
                                        cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                licenciasnr += '<LicenciaNR FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                'cantidad': str(int(cantidad))}
                        dev[nom.employee_id.id]['LicenciaNR'] = licenciasnr

                    if line_values.code == '1102-1' or line_values.code == '1202-1' or line_values.code == '1302-1':
                        bon = line_values.total
                        dev[nom.employee_id.id]['BonificacionS'] = {}

                    if line_values.code == '1102-2' or line_values.code == '1202-2' or line_values.code == '1302-2':
                        bon_ns = line_values.total
                        dev[nom.employee_id.id]['BonificacionNS'] = {}

                    if line_values.code == '1121-1' or line_values.code == '1221-1' or line_values.code == '1321-1':
                        s = line_values.total
                        dev[nom.employee_id.id]['BonoSal'] = {}

                    if line_values.code == '1121-2' or line_values.code == '1221-2' or line_values.code == '1321-2':
                        ns = line_values.total
                        dev[nom.employee_id.id]['BonoNSal'] = {}

                    if line_values.code == '1121-3' or line_values.code == '1221-3' or line_values.code == '1321-3':
                        asal = line_values.total
                        dev[nom.employee_id.id]['BonoAlimeS'] = {}

                    if line_values.code == '1121-4' or line_values.code == '1221-4' or line_values.code == '1321-4':
                        ans = line_values.total
                        dev[nom.employee_id.id]['BonoAlimeNS'] = {}

                    if line_values.code == '2112':
                        pagotercero += '<PagoTercero>' + \
                            str(line_values.total) + '</PagoTercero>'
                        dev[nom.employee_id.id]['PagoTercero'] = pagotercero

            if 'BonificacionS' in dev[nom.employee_id.id]:
                dev[nom.employee_id.id]['BonificacionS'] = str(bon)
            if 'BonificacionNS' in dev[nom.employee_id.id]:
                dev[nom.employee_id.id]['BonificacionNS'] = str(bon_ns)
            if 'BonoSal' in dev[nom.employee_id.id]:
                dev[nom.employee_id.id]['BonoSal'] = str(s)
            if 'BonoNSal' in dev[nom.employee_id.id]:
                dev[nom.employee_id.id]['BonoNSal'] = str(ns)
            if 'BonoAlimeS' in dev[nom.employee_id.id]:
                dev[nom.employee_id.id]['BonoAlimeS'] = str(asal)
            if 'BonoAlimeNS' in dev[nom.employee_id.id]:
                dev[nom.employee_id.id]['BonoAlimeNS'] = str(ans)
            if 'SueldoTrabajado' in dev[nom.employee_id.id]:
                dev[nom.employee_id.id]['SueldoTrabajado'] = self._complements_second_decimal_total_wizard(sueldo_trabajado)

            if prima != 0:
                if numero_de_dias_prima != 0:
                    tem_prima += '<Primas Cantidad="' + \
                        str(int(numero_de_dias_prima)) + '" ' + \
                        'Pago="' + str(prima) + '" />'
                    dev[nom.employee_id.id]['Primas'] = tem_prima

                elif numero_liquidacion_prima != 0:
                    tem_prima_liq += '<Primas Cantidad="' + \
                        str(numero_liquidacion_prima) + '" ' + \
                        'Pago="' + str(prima) + '" />'
                    dev[nom.employee_id.id]['Primas'] = tem_prima_liq

            if PagoCesantias != 0:
                tem_cesan += '<Cesantias Pago="' + \
                    str(PagoCesantias) + '" ' + 'Porcentaje="12"' + \
                    ' PagoIntereses="' + str(PagoIntereses) + '" />'
                dev[nom.employee_id.id]['Cesantias'] = tem_cesan

        for j in range(0, len(datos)):
            emp = datos[j]
            template_dev = """  <Basico DiasTrabajados="%(DiasTrabajados)s"
            SueldoTrabajado="%(SueldoTrabajado)s"/>
    /Transporte/
    /HEDs/
    /HENs/
    /HRNs/
    /HEDDFs/
    /HRDDFs/
    /HENDFs/
    /HRNDFs/
    /Vacaciones/
    /Primas/
    /Cesantias/
    /Incapacidad/
    /Licencias/
    /Bonificaciones/
    /BonoEPCTVs/
    /PagoTerceros/"""
            transporte = """<Transporte /AuxilioTransporte/ /ViaticoManutAloj/ />"""
            incapacidad = """<Incapacidades> /incapacidades_eps/ /incapacidades_arl/ </Incapacidades>"""
            licencias = """<Licencias> /licenciasm/ /licencias_p/ /licencias_r/ /licenciasnr/ </Licencias>"""
            bonificaciones = """<Bonificaciones> <Bonificacion BonificacionS="/amountS/" BonificacionNS="/amountNS/" /> </Bonificaciones>"""
            BonoEPCTVs = '<BonoEPCTVs> <BonoEPCTV PagoS="/BonoSal/" PagoNS="/BonoNSal/" PagoAlimentacionS="/BonoAlimS/" PagoAlimentacionNS="/BonoAlimNS/" /> </BonoEPCTVs>'
            pagoterceros = '<PagosTerceros>/PagoTercero/</PagosTerceros>'
            if emp.employee_id.id in dev:
                if 'AuxilioTransporte' in dev[emp.employee_id.id]:
                    aux_trans = self._complements_second_decimal_total_wizard(dev[emp.employee_id.id]['AuxilioTransporte'])
                    aux_t = """AuxilioTransporte="%(AuxilioTransporte)s"
                    """
                    aux_t = str(aux_t) % {'AuxilioTransporte': aux_trans}
                    transporte = transporte.replace(
                        '/AuxilioTransporte/', aux_t)

                if 'ViaticoManutAlojS' in dev[emp.employee_id.id]:
                    viaticoss = dev[emp.employee_id.id]['ViaticoManutAlojS']
                    viaticomanutalojs = """ViaticoManutAlojS="%(ViaticoManutAlojS)s"
                    """
                    viaticomanutalojs = str(viaticomanutalojs) % {
                        'ViaticoManutAlojS': viaticoss}
                    transporte = transporte.replace(
                        '/ViaticoManutAloj/', viaticomanutalojs)

                if 'ViaticoManutAlojNS' in dev[emp.employee_id.id]:
                    viaticosns = dev[emp.employee_id.id]['ViaticoManutAlojNS']
                    viaticomanutalojns = """ViaticoManutAlojNS="%(ViaticoManutAlojNS)s"
                    """
                    viaticomanutalojns = str(viaticomanutalojns) % {
                        'ViaticoManutAlojNS': viaticosns}
                    transporte = transporte.replace(
                        '/ViaticoManutAloj/', viaticomanutalojns)

                if 'AuxilioTransporte' not in dev[emp.employee_id.id]:
                    transporte = transporte.replace('/AuxilioTransporte/', '')

                if 'ViaticoManutAlojS' not in dev[emp.employee_id.id]:
                    transporte = transporte.replace('/ViaticoManutAloj/', '')

                if 'ViaticoManutAlojNS' not in dev[emp.employee_id.id]:
                    transporte = transporte.replace('/ViaticoManutAloj/', '')

                if 'AuxilioTransporte' not in dev[emp.employee_id.id] and 'ViaticoManutAlojS' not in dev[emp.employee_id.id] and 'ViaticoManutAlojNS' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/Transporte/', '')

                if 'AuxilioTransporte' or 'ViaticoManutAlojS' or 'ViaticoManutAlojNS' in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace(
                        '/Transporte/', transporte)

                if 'HEDs' in dev[emp.employee_id.id]:
                    HEDs = dev[emp.employee_id.id]['HEDs']
                    heds = """<HEDs>
        %(HEDs)s
    </HEDs>"""
                    heds = str(heds) % {'HEDs': HEDs}
                    template_dev = template_dev.replace('/HEDs/', heds)

                if 'HENs' in dev[emp.employee_id.id]:
                    HENs = dev[emp.employee_id.id]['HENs']
                    hens = """<HENs>
        %(HENs)s
    </HENs>"""
                    hens = str(hens) % {'HENs': HENs}
                    template_dev = template_dev.replace('/HENs/', hens)

                if 'HRNs' in dev[emp.employee_id.id]:
                    HRNs = dev[emp.employee_id.id]['HRNs']
                    hrns = """<HRNs>
        %(HRNs)s
    </HRNs>"""
                    hrns = str(hrns) % {'HRNs': HRNs}
                    template_dev = template_dev.replace('/HRNs/', hrns)

                if 'HEDDFs' in dev[emp.employee_id.id]:
                    HEDDFs = dev[emp.employee_id.id]['HEDDFs']
                    heddfs = """<HEDDFs>
        %(HEDDFs)s
    </HEDDFs>"""
                    heddfs = str(heddfs) % {'HEDDFs': HEDDFs}
                    template_dev = template_dev.replace('/HEDDFs/', heddfs)

                if 'HRDDFs' in dev[emp.employee_id.id]:
                    HRDDFs = dev[emp.employee_id.id]['HRDDFs']
                    hrddfs = """<HRDDFs>
        %(HRDDFs)s
    </HRDDFs>"""
                    hrddfs = str(hrddfs) % {'HRDDFs': HRDDFs}
                    template_dev = template_dev.replace('/HRDDFs/', hrddfs)

                if 'HENDFs' in dev[emp.employee_id.id]:
                    HENDFs = dev[emp.employee_id.id]['HENDFs']
                    hendfs = """<HENDFs>
        %(HENDFs)s
    </HENDFs>"""
                    hendfs = str(hendfs) % {'HENDFs': HENDFs}
                    template_dev = template_dev.replace('/HENDFs/', hendfs)

                if 'HRNDFs' in dev[emp.employee_id.id]:
                    HRNDFs = dev[emp.employee_id.id]['HRNDFs']
                    hrndfs = """<HRNDFs>
        %(HRNDFs)s
    </HRNDFs>"""
                    hrndfs = str(hrndfs) % {'HRNDFs': HRNDFs}
                    template_dev = template_dev.replace('/HRNDFs/', hrndfs)

                if 'Cesantias' in dev[emp.employee_id.id]:
                    cesantias = dev[emp.employee_id.id]['Cesantias']
                    template_dev = template_dev.replace(
                        '/Cesantias/', cesantias)

                if 'Incapacidad_eps' in dev[emp.employee_id.id]:
                    incap_eps = dev[emp.employee_id.id]['Incapacidad_eps']
                    incapacidad = incapacidad.replace(
                        '/incapacidades_eps/', incap_eps)

                if 'Incapacidad_arl' in dev[emp.employee_id.id]:
                    incap_arl = dev[emp.employee_id.id]['Incapacidad_arl']
                    incapacidad = incapacidad.replace(
                        '/incapacidades_arl/', incap_arl)

                if 'Incapacidad_eps' not in dev[emp.employee_id.id]:
                    incapacidad = incapacidad.replace(
                        '/incapacidades_eps/', '')

                if 'Incapacidad_arl' not in dev[emp.employee_id.id]:
                    incapacidad = incapacidad.replace(
                        '/incapacidades_arl/', '')

                if 'Incapacidad_eps' in dev[emp.employee_id.id] or 'Incapacidad_arl' in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace(
                        '/Incapacidad/', incapacidad)

                if 'Incapacidad_eps' not in dev[emp.employee_id.id] and 'Incapacidad_arl' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/Incapacidad/', '')

                if 'LicenciaM' in dev[emp.employee_id.id]:
                    licenciam = dev[emp.employee_id.id]['LicenciaM']
                    licencias = licencias.replace('/licenciasm/', licenciam)

                if 'LicenciaP' in dev[emp.employee_id.id]:
                    licenciap = dev[emp.employee_id.id]['LicenciaP']
                    licencias = licencias.replace('/licencias_p/', licenciap)

                if 'LicenciaR' in dev[emp.employee_id.id]:
                    licenciar = dev[emp.employee_id.id]['LicenciaR']
                    licencias = licencias.replace('/licencias_r/', licenciar)

                if 'LicenciaNR' in dev[emp.employee_id.id]:
                    licencianr = dev[emp.employee_id.id]['LicenciaNR']
                    licencias = licencias.replace('/licenciasnr/', licencianr)

                if 'LicenciaM' not in dev[emp.employee_id.id]:
                    licencias = licencias.replace('/licenciasm/', '')

                if 'LicenciaP' not in dev[emp.employee_id.id]:
                    licencias = licencias.replace('/licencias_p/', '')

                if 'LicenciaR' not in dev[emp.employee_id.id]:
                    licencias = licencias.replace('/licencias_r/', '')

                if 'LicenciaNR' not in dev[emp.employee_id.id]:
                    licencias = licencias.replace('/licenciasnr/', '')

                if 'LicenciaM' in dev[emp.employee_id.id] or 'LicenciaP' in dev[emp.employee_id.id] or 'LicenciaR' in dev[emp.employee_id.id] or 'LicenciaNR' in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace(
                        '/Licencias/', licencias)

                if 'LicenciaM' not in dev[emp.employee_id.id] and 'LicenciaP' not in dev[emp.employee_id.id] and 'LicenciaR' not in dev[emp.employee_id.id] and 'LicenciaNR' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/Licencias/', '')

                if 'BonificacionS' in dev[emp.employee_id.id]:
                    bonificacion = dev[emp.employee_id.id]['BonificacionS']
                    bonificaciones = bonificaciones.replace(
                        '/amountS/', bonificacion)

                if 'BonificacionNS' in dev[emp.employee_id.id]:
                    bonificacion_ns = dev[emp.employee_id.id]['BonificacionNS']
                    bonificaciones = bonificaciones.replace(
                        '/amountNS/', bonificacion_ns)

                if 'BonificacionS' not in dev[emp.employee_id.id]:
                    bonificaciones = bonificaciones.replace(
                        'BonificacionS="/amountS/"', '')

                if 'BonificacionNS' not in dev[emp.employee_id.id]:
                    bonificaciones = bonificaciones.replace(
                        'BonificacionNS="/amountNS/"', '')

                if 'BonificacionS' in dev[emp.employee_id.id] or 'BonificacionNS' in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace(
                        '/Bonificaciones/', bonificaciones)

                if 'BonificacionS' not in dev[emp.employee_id.id] and 'BonificacionNS' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/Bonificaciones/', '')

                if 'BonoSal' in dev[emp.employee_id.id]:
                    bonosal = dev[emp.employee_id.id]['BonoSal']
                    BonoEPCTVs = BonoEPCTVs.replace('/BonoSal/', bonosal)

                if 'BonoNSal' in dev[emp.employee_id.id]:
                    bononosal = dev[emp.employee_id.id]['BonoNSal']
                    BonoEPCTVs = BonoEPCTVs.replace('/BonoNSal/', bononosal)

                if 'BonoAlimS' in dev[emp.employee_id.id]:
                    bonoalimsal = dev[emp.employee_id.id]['BonoAlimS']
                    BonoEPCTVs = BonoEPCTVs.replace('/BonoAlimS/', bonoalimsal)

                if 'BonoAlimNS' in dev[emp.employee_id.id]:
                    bonoalimnosal = dev[emp.employee_id.id]['BonoAlimNS']
                    BonoEPCTVs = BonoEPCTVs.replace(
                        '/BonoAlimNS/', bonoalimnosal)

                if 'BonoSal' not in dev[emp.employee_id.id]:
                    BonoEPCTVs = BonoEPCTVs.replace('PagoS="/BonoSal/"', '')

                if 'BonoNSal' not in dev[emp.employee_id.id]:
                    BonoEPCTVs = BonoEPCTVs.replace('PagoNS="/BonoNSal/"', '')

                if 'BonoAlimS' not in dev[emp.employee_id.id]:
                    BonoEPCTVs = BonoEPCTVs.replace(
                        'PagoAlimentacionS="/BonoAlimS/"', '')

                if 'BonoAlimNS' not in dev[emp.employee_id.id]:
                    BonoEPCTVs = BonoEPCTVs.replace(
                        'PagoAlimentacionNS="/BonoAlimNS/"', '')

                if 'BonoSal' in dev[emp.employee_id.id] or 'BonoNSal' in dev[emp.employee_id.id] or 'BonoAlimSal' in dev[emp.employee_id.id] or 'BonoAlimNSal' in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace(
                        '/BonoEPCTVs/', BonoEPCTVs)

                if 'BonoSal' not in dev[emp.employee_id.id] and 'BonoNSal' not in dev[emp.employee_id.id] and 'BonoAlimSal' not in dev[emp.employee_id.id] and 'BonoAlimNSal' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/BonoEPCTVs/', '')

                if 'VacacionesComun' in dev[nom.employee_id.id]:
                    vacaciones_com = dev[nom.employee_id.id]['VacacionesComun']
                    template_dev = template_dev.replace(
                        '/Vacaciones/', vacaciones_com)

                if 'VacacionesComp' in dev[nom.employee_id.id]:
                    vacaciones_comp = dev[nom.employee_id.id]['VacacionesComp']
                    template_dev = template_dev.replace(
                        '/Vacaciones/', vacaciones_comp)

                if 'VacacionesComun' not in dev[nom.employee_id.id] and 'VacacionesComp' not in dev[nom.employee_id.id]:
                    template_dev = template_dev.replace('/Vacaciones/', '')

                if 'Primas' in dev[nom.employee_id.id]:
                    prima_ = dev[nom.employee_id.id]['Primas']
                    template_dev = template_dev.replace('/Primas/', prima_)

                if 'PagoTerceros' in dev[nom.employee_id.id]:
                    terceros = dev[nom.employee_id.id]['PagoTerceros']
                    pagoterceros = pagoterceros.replace(
                        '/PagoTercero/', terceros)
                    template_dev = template_dev.replace(
                        '/PagoTerceros/', pagoterceros)

                if 'HEDs' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/HEDs/', '')

                if 'HENs' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/HENs/', '')

                if 'HRNs' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/HRNs/', '')

                if 'HEDDFs' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/HEDDFs/', '')

                if 'HRDDFs' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/HRDDFs/', '')

                if 'HENDFs' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/HENDFs/', '')

                if 'HRNDFs' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/HRNDFs/', '')

                if 'Primas' not in dev[nom.employee_id.id]:
                    template_dev = template_dev.replace('/Primas/', '')

                if 'Cesantias' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/Cesantias/', '')

                if 'Incapacidad_eps' not in dev[emp.employee_id.id] and 'Incapacidad_arl' not in dev[emp.employee_id.id]:
                    template_dev = template_dev.replace('/Incapacidad/', '')

                if 'PagoTerceros' not in dev[nom.employee_id.id]:
                    template_dev = template_dev.replace('/PagoTerceros/', '')

            if emp.employee_id.id in dic_temp_dev:
                
                pass
            else:
                dic_temp_dev[emp.employee_id.id] = template_dev
            
        for x, y in dev.items():
            temp_dev = dic_temp_dev[x]
            deveng = temp_dev % y
            temp_d[x] = deveng
        return temp_d[x]

    def generate_payslip_deducciones_wizard(self, nominas):
        temp_ded = ded = {}
        dic_temp_ded = {}
        datos = []
        salud = FondoPension = Anticipos = FondoSP = ReteFuente = deducciones = 0
        for i in range(0, len(nominas)):
            datos.append(self.env['hr.payslip'].browse(nominas[i]))
                  
        for j in range(0, len(datos)):
            nom = datos[j]
            temp_salud = temp_fondopension = temp_fondosp = temp_anticipos = temp_retefuente = temp_deducciones = ''

            if nom.employee_id.id in ded:
                for line_values in nom.line_ids:
                    if line_values.code == '1008':
                        salud = salud + line_values.total
                        ded[nom.employee_id.id]['Salud'] = {}
                    if line_values.code == '1009':
                        FondoPension = FondoPension + line_values.total
                        ded[nom.employee_id.id]['FondoPension'] = {}
                    if line_values.code == 'SAR':
                        Anticipos = Anticipos + line_values.total
                        ded[nom.employee_id.id]['Anticipos'] = {}
                    if line_values.code == '1011':
                        FondoSP = FondoSP + line_values.total
                        ded[nom.employee_id.id]['FondoSP'] = {}
                    if line_values.code == '1014':
                        ReteFuente = ReteFuente + line_values.total
                        ded[nom.employee_id.id]['RetencionFuente'] = {}
            else:
                ded[nom.employee_id.id] = {}
                for line_values in nom.line_ids:
                    if line_values.code == '1008':
                        salud = line_values.total
                        ded[nom.employee_id.id]['Salud'] = {}
                    if line_values.code == '1009':
                        FondoPension = line_values.total
                        ded[nom.employee_id.id]['FondoPension'] = {}
                    if line_values.code == 'SAR':
                        Anticipos = line_values.total
                        ded[nom.employee_id.id]['Anticipos'] = {}
                    if line_values.code == '1011':
                        FondoSP = line_values.total
                        ded[nom.employee_id.id]['FondoSP'] = {}
                    if line_values.code == '1014':
                        ReteFuente = line_values.total
                        ded[nom.employee_id.id]['RetencionFuente'] = {}

            if 'Salud' in ded[nom.employee_id.id]:
                ded[nom.employee_id.id]['Salud'] = self._complements_second_decimal_total_wizard(salud)

            if 'FondoPension' in ded[nom.employee_id.id]:
                ded[nom.employee_id.id]['FondoPension'] = self._complements_second_decimal_total_wizard(FondoPension)

            if 'Anticipos' in ded[nom.employee_id.id]:
                ded[nom.employee_id.id]['Anticipos'] = Anticipos

            if 'FondoSP' in ded[nom.employee_id.id]:
                ded[nom.employee_id.id]['FondoSP'] = FondoSP

            if 'RetencionFuente' in ded[nom.employee_id.id]:
                ded[nom.employee_id.id]['RetencionFuente'] = ReteFuente

        for emp in ded.keys():
            template_ded = """/Salud/
        /FondoPension/
        /FondoSP/
        /Anticipos/
        /RetencionFuente/"""
            if emp in ded:
                if 'Salud' in ded[emp]:
                    ded_salud = ded[emp]['Salud']
                    temp_salud = '<Salud Porcentaje="4" Deduccion="' + \
                        str(ded_salud)+'" />'
                    template_ded = template_ded.replace('/Salud/', temp_salud)

                if 'FondoPension' in ded[emp]:
                    ded_fondopension = ded[emp]['FondoPension']
                    temp_fondopension = '<FondoPension Porcentaje="4" Deduccion="' + \
                        str(ded_fondopension)+'" />'
                    template_ded = template_ded.replace(
                        '/FondoPension/', temp_fondopension)

                if 'FondoSP' in ded[emp]:
                    ded_fondosp = ded[emp]['FondoSP']
                    temp_fondosp = '<FondoSP Porcentaje="1" DeduccionSP="' + \
                        str(ded_fondosp) + '"/>'
                    template_ded = template_ded.replace(
                        '/FondoSP/', temp_fondosp)

                if 'Anticipos' in ded[emp]:
                    ded_anticipos = ded[emp]['Anticipos']
                    temp_anticipos = '<Anticipos><Anticipo>%(SAR)s</Anticipo></Anticipos>' % {
                        "SAR": abs(ded_anticipos)}
                    template_ded = template_ded.replace(
                        '/Anticipos/', temp_anticipos)

                if 'RetencionFuente' in ded[emp]:
                    ded_retefuente = ded[emp]['RetencionFuente']
                    temp_retefuente = '<RetencionFuente>' + \
                        str(ded_retefuente) + '</RetencionFuente>'
                    template_ded = template_ded.replace(
                        '/RetencionFuente/', temp_retefuente)

                if 'Salud' not in ded[emp]:
                    template_ded = template_ded.replace('/Salud/', '')

                if 'FondoPension' not in ded[emp]:
                    template_ded = template_ded.replace('/FondoPension/', '')

                if 'FondoSP' not in ded[emp]:
                    template_ded = template_ded.replace('/FondoSP/', '')

                if 'Anticipos' not in ded[emp]:
                    template_ded = template_ded.replace('/Anticipos/', '')

                if 'RetencionFuente' not in ded[emp]:
                    template_ded = template_ded.replace(
                        '/RetencionFuente/', '')

            if emp in dic_temp_ded:
                pass
            else:
                dic_temp_ded[emp] = template_ded

        for x, y in ded.items():
            temp_d = dic_temp_ded[x]
            deducciones = temp_d % y
            temp_ded[x] = deducciones
        return temp_ded[x]

    def _get_deducciones_total_wizard(self):

        ded_total = {}
        for emp in self.table_ids:
            total_deducciones = 0
            if emp.employee_id.id in ded_total:
                lines_deducciones = emp.line_ids.filtered(
                    lambda l: l.salary_rule_id.rule_type == 'deducciones')
                for line in lines_deducciones:
                    total_deducciones += line.total
                if 'Total' in ded_total[emp.employee_id.id]:
                    ded_total[emp.employee_id.id]['Total'] = round(
                        ded_total[emp.employee_id.id]['Total'] + total_deducciones, 2)
                else:
                    ded_total[emp.employee_id.id]['Total'] = round(
                        total_deducciones, 2)
            else:
                ded_total[emp.employee_id.id] = {}
                lines_deducciones = emp.line_ids.filtered(
                    lambda l: l.salary_rule_id.rule_type == 'deducciones')
                for line in lines_deducciones:
                    total_deducciones += line.total
                ded_total[emp.employee_id.id]['Total'] = round(
                    total_deducciones, 2)
        return ded_total

    def _get_devengos_total_wizard(self):
        dev_total = {}
        for emp in self.table_ids:
            total_devengos = 0
            if emp.employee_id.id in dev_total:
                lines_devengos = emp.line_ids.filtered(
                    lambda l: l.salary_rule_id.rule_type == 'devengos')
                for line in lines_devengos:
                    total_devengos += line.total
                if 'Total' in dev_total[emp.employee_id.id]:
                    dev_total[emp.employee_id.id]['Total'] = round(
                        dev_total[emp.employee_id.id]['Total'] + total_devengos, 2)
                else:
                    dev_total[emp.employee_id.id]['Total'] = round(
                        total_devengos, 2)
            else:
                dev_total[emp.employee_id.id] = {}
                lines_devengos = emp.line_ids.filtered(
                    lambda l: l.salary_rule_id.rule_type == 'devengos')
                for line in lines_devengos:
                    total_devengos += line.total
                dev_total[emp.employee_id.id]['Total'] = round(
                    total_devengos, 2)  
        return dev_total
    
    def ChargeDianDocuments(self, payslip, employee_id, consecutive, temp, dic_cune, data_xml_document, attachment_id, msg, dic_cons, _nombre_zip, type_xml, estado, payslips_document, documentos, dates):
        
        base = {}
        hr_payslip = self.env['hr.payslip']
        dian_documents = self.env['payroll.payroll.window']
        payslip_ns = payslip.payslip_numero_secuencia_xml_template()
        employee_name = employee_id
        date_from = dates[employee_id]['date_from']
        date_to = dates[employee_id]['date_to']
        fechaGen = str(hr_payslip._get_date_gen())
        employee_email = "example@example.com"  # payslip.employee_id.work_eamil
        file_name = consecutive['Numero']
        #document = self._SendDianDocuments(payslip, employee_id, temp, dic_cons)
        nombre_zip = _nombre_zip
        cune = dic_cune
        

        if employee_id in base:
            base[employee_id] = {
                'name': file_name,
                'employee': employee_name,
                'date_from': date_from,
                'date_to': date_to,
                'fecha_doc': fechaGen,
                'cliente_email': employee_email,
                'fecha_env': fechaGen,
                #'contenido' : data_xml_document,
                'nom_arc_xml': nombre_zip.replace("xml", "zip"),
                'cune': cune,
                'nombre_zip': nombre_zip.replace("xml", "zip"),
                'file_xml' : attachment_id,
                'respuesta_dian' : msg,
                'consolidados_table1_ids':[(6, 0, documentos)],
                'tipo_doc' : type_xml, 
                'estado' : estado,
                'table_ids':[(6, 0, payslips_document)]
            }

        else:
            base[employee_id] = {}
            base[employee_id] = {
                'name': file_name,
                'employee': employee_name,
                'date_from': date_from,
                'date_to': date_to,
                'fecha_doc': fechaGen,
                'cliente_email': employee_email,
                'fecha_env': fechaGen,
                #'contenido' : data_xml_document,
                'nom_arc_xml': nombre_zip.replace("xml", "zip"),
                'cune': cune,
                'nombre_zip': nombre_zip.replace("xml", "zip"),
                'file_xml' : attachment_id,
                'respuesta_dian' : msg,
                'consolidados_table1_ids':[(6, 0, documentos)],
                'tipo_doc' : type_xml, 
                'estado' : estado,
                'table_ids':[(6, 0, payslips_document)]
            }
        documentos_dian = dian_documents.create(base[employee_id])
        self.consolidados_table_ids.payroll_number = "Nómina consolidada"


        self.InheritWindow(documentos_dian)
        
    def InheritWindow(self, documentos_dian):
        lista = []
        for ids in documentos_dian:
            lista.append((4, ids.id))
            self.env.cr.commit()
            self.emision_nominas = lista

        

    def _SendDianDocuments(self, payslip, emp, payslip_xml, dic_cons):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        company = self.env['res.company'].sudo().search(
            [('id', '=', user.company_id.id)])
        dian_documents = self.env['payroll.payroll.window']
        dian_constants = self._get_dian_constants(payslip_xml)
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self.generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']
        cer = dian_constants['Certificate']
        data_xml_document = payslip_xml[emp]
        #xml = self.send_2_validate(payslip, payslip_xml, emp, dic_cons, dic_cune)
        #return xml

    def generate_digestvalue_to(self, elementTo):
        # Generar el digestvalue de to
        elementTo = etree.tostring(etree.fromstring(elementTo), method="c14n")
        elementTo_sha256 = hashlib.new('sha256', elementTo)
        elementTo_digest = elementTo_sha256.digest()
        elementTo_base = base64.b64encode(elementTo_digest)
        elementTo_base = elementTo_base.decode()
        return elementTo_base

    def generate_SignatureValue_GetStatus(self, document_repository, password, data_xml_SignedInfo_generate, archivo_pem, archivo_certificado):
        data_xml_SignatureValue_c14n = etree.tostring(
            etree.fromstring(data_xml_SignedInfo_generate), method="c14n")
        archivo_key = document_repository+'/'+archivo_certificado
        try:
            key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)
        except Exception as ex:
            raise ex
        try:
            signature = crypto.sign(
                key.get_privatekey(), data_xml_SignatureValue_c14n, 'sha256')
        except Exception as ex:
            raise ex
        SignatureValue = base64.b64encode(signature).decode()
        archivo_pem = document_repository+'/'+archivo_pem
        pem = crypto.load_certificate(
            crypto.FILETYPE_PEM, open(archivo_pem, 'rb').read())
        try:
            validacion = crypto.verify(
                pem, signature, data_xml_SignatureValue_c14n, 'sha256')
        except:
            raise "Firma para el GestStatus no fué validada exitosamente"
        return SignatureValue

    
    def _generate_SignatureValue(self, document_repository, password, data_xml_SignedInfo_generate,
                                 archivo_pem, archivo_certificado):
        data_xml_SignatureValue_c14n = etree.tostring(etree.fromstring(
            data_xml_SignedInfo_generate), method="c14n", exclusive=False, with_comments=False)
        archivo_key = document_repository+'/'+archivo_certificado
        try:
            key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        try:
            signature = crypto.sign(
                key.get_privatekey(), data_xml_SignatureValue_c14n, 'sha512')
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        SignatureValue = base64.b64encode(signature)
        SignatureValue = SignatureValue.decode()
        archivo_pem = document_repository+'/'+archivo_pem
        pem = crypto.load_certificate(
            crypto.FILETYPE_PEM, open(archivo_pem, 'rb').read())
        try:
            validacion = crypto.verify(
                pem, signature, data_xml_SignatureValue_c14n, 'sha512')
        except:
            raise ValidationError("Firma no fué validada exitosamente")
        #serial = key.get_certificate().get_serial_number()
        return SignatureValue

    def generate_xmlsigned(self, tipoxml, xml, CerificadoEmpleadorB64, PinCertificadoB64, NitEmpleador):

        headers = {
            'Content-Type': 'application/json'
        }
        payload = json.dumps({
            "xmlsNominasB64": [
                {
                    "TipoXML": tipoxml,
                    "XmlB64": xml.decode("utf-8"),
                    "CerificadoEmpleadorB64": CerificadoEmpleadorB64.decode("utf-8"),
                    "PinCertificadoB64": PinCertificadoB64.decode("utf-8"),
                    "NitEmpleador": NitEmpleador,
                    "Firmado": False,
                    "Mensaje": "Sin firmar"
                }
            ]
        })
        response = requests.request("POST", "http://apps.kiai.co/api/Mediador/FirmarXmlNomina",
                                    data=payload, headers=headers, auth=("900395252", "tufactura.co@softwareestrategico.com"))
        if response.status_code == 200:
            return response.json()
        else:
            return {}

    def _generate_signature_ref0(self, data_xml_document, document_repository, password):
        # 1er paso. Generar la referencia 0 que consiste en obtener keyvalue desde todo el xml del
        #           documento electronico aplicando el algoritmo SHA512 y convirtiendolo a base64
        template_basic_data_fe_xml = data_xml_document
        template_basic_data_fe_xml = etree.tostring(etree.fromstring(template_basic_data_fe_xml), method="c14n", exclusive=False,with_comments=False,inclusive_ns_prefixes=None)
        data_xml_sha512 = hashlib.new('sha512', template_basic_data_fe_xml)
        data_xml_digest = data_xml_sha512.digest()
        data_xml_signature_ref_zero = base64.b64encode(data_xml_digest)
        data_xml_signature_ref_zero = data_xml_signature_ref_zero.decode()
        return data_xml_signature_ref_zero

        

    @api.model
    def _generate_signature_ref0_(self, data_xml_document, document_repository, password):
        # 1er paso. Generar la referencia 0 que consiste en obtener keyvalue desde todo el xml del
        #           documento electronico aplicando el algoritmo SHA256 y convirtiendolo a base64
        template_basic_data_fe_xml = data_xml_document
        template_basic_data_fe_xml = etree.tostring(
            etree.fromstring(template_basic_data_fe_xml),
            method="c14n",
            exclusive=False,
            with_comments=False,
            inclusive_ns_prefixes=None
        )
        data_xml_sha256 = hashlib.new("sha256", template_basic_data_fe_xml)
        data_xml_digest = data_xml_sha256.digest()
        data_xml_signature_ref_zero = base64.b64encode(data_xml_digest)
        data_xml_signature_ref_zero = data_xml_signature_ref_zero.decode()
        return data_xml_signature_ref_zero


    
    def _generate_signature_ref1_(self, data_xml_keyinfo_generate, document_repository, password):
        # Generar la referencia 1 que consiste en obtener keyvalue desde el keyinfo contenido
        # en el documento electrónico aplicando el algoritmo SHA256 y convirtiendolo a base64
        data_xml_keyinfo_generate = etree.tostring(
            etree.fromstring(data_xml_keyinfo_generate), method="c14n")
        data_xml_keyinfo_sha256 = hashlib.new(
            'sha512', data_xml_keyinfo_generate)
        data_xml_keyinfo_digest = data_xml_keyinfo_sha256.digest()
        data_xml_keyinfo_base = base64.b64encode(data_xml_keyinfo_digest)
        data_xml_keyinfo_base = data_xml_keyinfo_base.decode()
        return data_xml_keyinfo_base

    def _generate_signature_ref1(self, data_xml_keyinfo_generate, document_repository, password):
        # Generar la referencia 1 que consiste en obtener keyvalue desde el keyinfo contenido
        # en el documento electrónico aplicando el algoritmo SHA512 y convirtiendolo a base64
        data_xml_keyinfo_generate = etree.tostring(etree.fromstring(data_xml_keyinfo_generate), method="c14n")
        data_xml_keyinfo_sha512 = hashlib.new('sha512', data_xml_keyinfo_generate)
        data_xml_keyinfo_digest = data_xml_keyinfo_sha512.digest()
        data_xml_keyinfo_base = base64.b64encode(data_xml_keyinfo_digest)
        data_xml_keyinfo_base = data_xml_keyinfo_base.decode()
        return data_xml_keyinfo_base

    
    def _generate_signature_ref2(self, data_xml_SignedProperties_generate):
        # Generar la referencia 2, se obtine desde el elemento SignedProperties que se
        # encuentra en la firma aplicando el algoritmo SHA256 y convirtiendolo a base64.
        data_xml_SignedProperties_c14n = etree.tostring(
            etree.fromstring(data_xml_SignedProperties_generate), method="c14n")
        data_xml_SignedProperties_sha256 = hashlib.new(
            'sha512', data_xml_SignedProperties_c14n)
        data_xml_SignedProperties_digest = data_xml_SignedProperties_sha256.digest()
        data_xml_SignedProperties_base = base64.b64encode(
            data_xml_SignedProperties_digest)
        data_xml_SignedProperties_base = data_xml_SignedProperties_base.decode()
        return data_xml_SignedProperties_base

    
    def _generate_signature_politics(self, document_repository):
        # Generar la referencia 2 que consiste en obtener keyvalue desde el documento de politica
        # aplicando el algoritmo SHA1 antes del 20 de septimebre de 2016 y sha256 después  de esa
        # fecha y convirtiendolo a base64. Se  puede utilizar como una constante ya que no variará
        # en años segun lo indica la DIAN.
        #
        data_xml_politics = 'dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y='
        return data_xml_politics

    
    def _generate_signature_signingtime(self):
        fmt = "%Y-%m-%dT%H:%M:%S"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        data_xml_SigningTime = now_bogota.strftime(fmt)
        return data_xml_SigningTime

    def _replace_character_especial(self, constant):
        if constant:
            constant = constant.replace('&', '&amp;')
            constant = constant.replace('<', '&lt;')
            constant = constant.replace('>', '&gt;')
            constant = constant.replace('"', '&quot;')
            constant = constant.replace("'", '&apos;')
        return constant

    def _get_partner_fiscal_responsability_code(self, partner_id):
        rec_partner = self.env['res.partner'].search([('id', '=', partner_id)])
        fiscal_responsability_codes = ''
        if rec_partner:
            for fiscal_responsability in rec_partner.fiscal_responsability_ids:
                fiscal_responsability_codes += ';' + \
                    fiscal_responsability.code if fiscal_responsability_codes else fiscal_responsability.code
        return fiscal_responsability_codes

    def _generate_CertDigestDigestValue_(self, digital_certificate, password, document_repository, archivo_certificado):
        archivo_key = document_repository + '/'+archivo_certificado
        key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)
        certificate = hashlib.sha256(crypto.dump_certificate(
            crypto.FILETYPE_ASN1, key.get_certificate()))
        CertDigestDigestValue = base64.b64encode(certificate.digest())
        CertDigestDigestValue = CertDigestDigestValue.decode()
        return CertDigestDigestValue

    
    def _generate_CertDigestDigestValue(self, digital_certificate, password, document_repository, archivo_certificado):
        archivo_key = document_repository +'/'+archivo_certificado
        crt = open(archivo_key, mode='rb').read()
        key = crypto.load_pkcs12(crt, password)
        certificate = hashlib.sha512(crypto.dump_certificate(crypto.FILETYPE_ASN1, key.get_certificate()))
        CertDDV = base64.b64encode(certificate.digest())
        CertDDV = CertDDV.decode()
        x509 = key.get_certificate().to_cryptography()
        CertDigestDigestValue = [{
            'CertDigestDigestValue0': CertDDV,
            'IssuerName0': _get_reversed_rdns_name(x509.issuer.rdns),
            'SerialNumber0': x509.serial_number
        }]
        ca = key.get_ca_certificates()
        c = 0
        for cert in reversed(ca):
            certificate = hashlib.sha512(crypto.dump_certificate(crypto.FILETYPE_ASN1, cert))
            CertDDV = base64.b64encode(certificate.digest())
            CertDDV = CertDDV.decode()
            x509 = cert.to_cryptography()
            c += 1 
            CertDigestDigestValue.append({
                'CertDigestDigestValue%s'%c: CertDDV,
                'IssuerName%s'%c: _get_reversed_rdns_name(x509.issuer.rdns),
                'SerialNumber%s'%c: x509.serial_number
                })

        return CertDigestDigestValue

    def _get_reversed_rdns_name(rdns):
        """
        Gets the rdns String name, but in the right order. xmlsig original function produces a reversed order
        :param rdns: RDNS object
        :type rdns: cryptography.x509.RelativeDistinguishedName
        :return: RDNS name
        """
        name = ''
        for rdn in reversed(rdns):
            for attr in rdn._attributes:
                if len(name) > 0:
                    name = name + ','
                if attr.oid in OID_NAMES:
                    name = name + OID_NAMES[attr.oid]
                else:
                    name = name + attr.oid._name
                name = name + '=' + attr.value
        return name
    #############################################################################################################

    def _generate_data_constants_document(self):
        data_constants_document = {}
        # Genera identificadores único
        identifier = uuid.uuid4()
        data_constants_document['identifier'] = str(identifier)
        identifierkeyinfo = uuid.uuid4()
        data_constants_document['identifierkeyinfo'] = str(identifierkeyinfo)
        return data_constants_document

    @api.model
    def _generate_signature_(self, data_xml_document, template_signature_data_xml, dian_constants, data_constants_document):
        data_xml_keyinfo_base = ''
        data_xml_politics = ''
        data_xml_SignedProperties_base = ''
        data_xml_SigningTime = ''
        data_xml_SignatureValue = ''
        # Generar clave de referencia 0 para la firma del documento (referencia ref0)
        # Actualizar datos de signature
        #    Generar certificado publico para la firma del documento en el elemento keyinfo
        data_public_certificate_base = dian_constants['Certificate']
        #    Generar clave de politica de firma para la firma del documento (SigPolicyHash)
        data_xml_politics = self._generate_signature_politics(
            dian_constants['document_repository'])
        #    Obtener la hora de Colombia desde la hora del pc
        data_xml_SigningTime = self._generate_signature_signingtime()
        #    Generar clave de referencia 0 para la firma del documento (referencia ref0)
        #    1ra. Actualización de firma ref0 (leer todo el xml sin firma)
        parser = etree.XMLParser(remove_blank_text=True)
       
        data_xml_signature_ref_zero = self._generate_signature_ref0(
            data_xml_document, dian_constants['document_repository'], dian_constants['CertificateKey'])
        data_xml_signature = self._update_signature(template_signature_data_xml,
                                                    data_xml_signature_ref_zero, data_public_certificate_base,
                                                    data_xml_keyinfo_base, data_xml_politics,
                                                    data_xml_SignedProperties_base, data_xml_SigningTime,
                                                    dian_constants, data_xml_SignatureValue, data_constants_document)
        """data_xml_signature = etree.tostring(
            etree.XML(data_xml_signature, parser=parser))
        data_xml_signature = data_xml_signature.decode()"""
        
        #    Actualiza Keyinfo
        KeyInfo = etree.fromstring(data_xml_signature)
        KeyInfo = etree.tostring(KeyInfo[2])
        KeyInfo = KeyInfo.decode()
        data_xml_keyinfo_base = self._generate_signature_ref1(
            KeyInfo, dian_constants['document_repository'], dian_constants['CertificateKey'])
        data_xml_signature = data_xml_signature.replace(
            "<ds:DigestValue/>", "<ds:DigestValue>%s</ds:DigestValue>" % data_xml_keyinfo_base, 1)
        #    Actualiza SignedProperties
        SignedProperties = etree.fromstring(data_xml_signature)
        SignedProperties = etree.tostring(SignedProperties[3])
        SignedProperties = etree.fromstring(SignedProperties)
        SignedProperties = etree.tostring(SignedProperties[0])
        SignedProperties = etree.fromstring(SignedProperties)
        SignedProperties = etree.tostring(SignedProperties[0])
        SignedProperties = SignedProperties.decode()
        data_xml_SignedProperties_base = self._generate_signature_ref2(
            SignedProperties)
        data_xml_signature = data_xml_signature.replace(
            "<ds:DigestValue/>", "<ds:DigestValue>%s</ds:DigestValue>" % data_xml_SignedProperties_base, 1)
        #    Actualiza Signeinfo
        Signedinfo = etree.fromstring(data_xml_signature)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = Signedinfo.decode()
        data_xml_SignatureValue = self._generate_SignatureValue(
            dian_constants['document_repository'], dian_constants['CertificateKey'], Signedinfo, dian_constants['archivo_pem'], dian_constants['archivo_certificado'])
        SignatureValue = etree.fromstring(data_xml_signature)
        SignatureValue = etree.tostring(SignatureValue[1])
        SignatureValue = SignatureValue.decode()
        data_xml_signature = data_xml_signature.replace(
            '-sigvalue"/>', '-sigvalue">%s</ds:SignatureValue>' % data_xml_SignatureValue, 1)
        data_xml_signature = etree.tostring(
            etree.XML(data_xml_signature, parser=parser))
        data_xml_signature = data_xml_signature.decode()
        return data_xml_signature

    def _generate_zip_content(self, FileNameZIP, data_xml_document, document_repository, filename):
        # Almacena archvio XML

        # Comprime archvio XML
        zip_file = document_repository + '/' + FileNameZIP
        zf = zipfile.ZipFile(zip_file, mode="w")
        try:
            zf.writestr(filename, data_xml_document, compress_type=compression)
        finally:
            zf.close()

        data_xml = open(zip_file, 'rb')
        data_xml = data_xml.read()
        contenido_data_xml_b64 = base64.b64encode(data_xml)
        contenido_data_xml_b64 = contenido_data_xml_b64.decode()
        return contenido_data_xml_b64

    
    def l10n_co_check_trackid_status(self):
        for record in self:
            if record.l10n_co_dian_status in ('none', 'undefined') and record.trackid:
                record._l10n_co_check()

    def generate_GetStatusZip_send_xml(self, template_getstatus_send_data_xml, identifier, Created, Expires,  Certificate,
                                       identifierSecurityToken, identifierTo, trackId):
        data_getstatus_send_xml = template_getstatus_send_data_xml % {
            'identifier': identifier,
            'Created': Created,
            'Expires': Expires,
            'Certificate': Certificate,
            'identifierSecurityToken': identifierSecurityToken,
            'identifierTo': identifierTo,
            'trackId': trackId
        }
        return data_getstatus_send_xml

    def generate_SendTestSetAsync_send_xml(self, template_getstatus_send_data_xml, identifier, Created, Expires,  Certificate,
                                           identifierSecurityToken, identifierTo, contentFile, fileName, testSetId):
        
        data_getstatus_send_xml = template_getstatus_send_data_xml % {
            'identifier': identifier,
            'Created': Created,
            'Expires': Expires,
            'Certificate': Certificate,
            'identifierSecurityToken': identifierSecurityToken,
            'identifierTo': identifierTo,
            'fileName': fileName,
            'contentFile': contentFile,
            'testSetId': testSetId
        }
        return data_getstatus_send_xml

    @api.model
    def _generate_signature(self, data_xml_document, template_signature_data_xml, dian_constants, data_constants_document):
        data_xml_keyinfo_base = ''
        data_xml_politics = ''
        data_xml_SignedProperties_base = ''
        data_xml_SigningTime = ''
        data_xml_SignatureValue = ''
        # Generar clave de referencia 0 para la firma del documento (referencia ref0)
        # Actualizar datos de signature
        #    Generar certificado publico para la firma del documento en el elemento keyinfo
        data_public_certificate_base = dian_constants['Certificate']
        #    Generar clave de politica de firma para la firma del documento (SigPolicyHash)
        data_xml_politics = self._generate_signature_politics(dian_constants['document_repository'])
        #    Obtener la hora de Colombia desde la hora del pc
        data_xml_SigningTime = self._generate_signature_signingtime()
        #    Generar clave de referencia 0 para la firma del documento (referencia ref0)
        #    1ra. Actualización de firma ref0 (leer todo el xml sin firma)
        data_xml_signature_ref_zero = self._generate_signature_ref0(data_xml_document, dian_constants['document_repository'], dian_constants['CertificateKey'])
        data_xml_signature = self._update_signature(template_signature_data_xml,
                                data_xml_signature_ref_zero, data_public_certificate_base,
                                data_xml_keyinfo_base, data_xml_politics,
                                data_xml_SignedProperties_base, data_xml_SigningTime,
                                dian_constants, data_xml_SignatureValue, data_constants_document)
        parser = etree.XMLParser(remove_blank_text=True)
        data_xml_signature = etree.tostring(etree.XML(data_xml_signature, parser=parser))
        data_xml_signature = data_xml_signature.decode()
        #    Actualiza Keyinfo
        KeyInfo = etree.fromstring(data_xml_signature)
        KeyInfo = etree.tostring(KeyInfo[2])
        KeyInfo = KeyInfo.decode()

        xmlns = 'xmlns="dian:gov:co:facturaelectronica:%(XmlNodo)s" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' % {'XmlNodo': 'NominaIndividual'} #mucho ojo
        KeyInfo = KeyInfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' %xmlns)
        data_xml_keyinfo_base = self._generate_signature_ref1(KeyInfo, dian_constants['document_repository'], dian_constants['CertificateKey'])
        data_xml_signature = data_xml_signature.replace("<ds:DigestValue/>","<ds:DigestValue>%s</ds:DigestValue>" % data_xml_keyinfo_base, 1)
        #    Actualiza SignedProperties
        SignedProperties = etree.fromstring(data_xml_signature)
        SignedProperties = etree.tostring(SignedProperties[3])
        SignedProperties = etree.fromstring(SignedProperties)
        SignedProperties = etree.tostring(SignedProperties[0])
        SignedProperties = etree.fromstring(SignedProperties)
        SignedProperties = etree.tostring(SignedProperties[0])
        SignedProperties = SignedProperties.decode()
        SignedProperties = SignedProperties.replace('xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )

        data_xml_SignedProperties_base = self._generate_signature_ref2(SignedProperties)
        data_xml_signature = data_xml_signature.replace("<ds:DigestValue/>","<ds:DigestValue>%s</ds:DigestValue>" % data_xml_SignedProperties_base, 1)
        #    Actualiza Signeinfo
        Signedinfo = etree.fromstring(data_xml_signature)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = Signedinfo.decode()
        Signedinfo = Signedinfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )

        data_xml_SignatureValue = self._generate_SignatureValue(dian_constants['document_repository'], dian_constants['CertificateKey'], Signedinfo, dian_constants['archivo_pem'], dian_constants['archivo_certificado'])
        data_xml_signature = data_xml_signature.replace('-sigvalue"/>','-sigvalue">%s</ds:SignatureValue>' % data_xml_SignatureValue, 1)
        return data_xml_signature

    
    def _l10n_co_check(self, payslip):
        dian_documents = self.env['payroll.payroll.window']
        dian_constants = self._get_dian_constants(payslip)
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self.generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']
        cer = dian_constants['Certificate']
        headers = {'content-type': 'application/soap+xml'}
        url = URLSEND[payslip.company_id.is_test]

        if payslip.company_id.is_test == "2":
            getstatus_xml_send = self.generate_GetStatusZip_send_xml(self.template_GetStatusZip_xml(), identifier, Created, Expires,
                                                                     cer, identifierSecurityToken, identifierTo, self.trackid)
            getstatus_xml_send = self.sign_request_post(
                getstatus_xml_send, payslip)
            response = requests.post(
                url, data=getstatus_xml_send, headers=headers)
            if response.status_code == 200:
                response_dict = xmltodict.parse(response.content)
                dian_response_dict = response_dict.get("s:Envelope", {}).get("s:Body", {}).get(
                    "GetStatusZipResponse", {}).get("GetStatusZipResult", {}).get("b:DianResponse", {})
                if dian_response_dict.get("b:IsValid", "false") == "true":
                    self.l10n_co_dian_status = "valid"
                '''else:
                    dian_documents.message_post(body=dian_response_dict.get(
                        "b:StatusDescription", ''))'''
        else:
            getstatus_xml_send = self.generate_GetStatusZip_send_xml(self.template_GetStatus_xml(), identifier, Created, Expires,
                                                                     cer, identifierSecurityToken, identifierTo, self.trackid)
            getstatus_xml_send = self.sign_request_post(
                getstatus_xml_send, payslip)
            response = requests.post(
                url, data=getstatus_xml_send, headers=headers)
            if response.status_code == 200:
                response_dict = xmltodict.parse(response.content)
                dian_response_dict = response_dict.get("s:Envelope", {}).get(
                    "s:Body", {}).get("GetStatusResponse", {}).get("GetStatusResult", {})
                if dian_response_dict.get("b:IsValid", "false") == "true":
                    self.l10n_co_dian_status = "valid"
                else:
                    msg = dian_response_dict.get("b:StatusDescription", '')
                    for error in dian_response_dict.get("b:ErrorMessage", {}).get("c:string", []):
                        msg += "<p>%s</p>" % (error)
                    '''dian_documents.message_post(body=msg)'''

    @api.model
    def _update_signature(self, template_signature_data_xml, data_xml_signature_ref_zero, data_public_certificate_base,
                          data_xml_keyinfo_base, data_xml_politics,
                          data_xml_SignedProperties_base, data_xml_SigningTime, dian_constants,
                          data_xml_SignatureValue, data_constants_document):

        data_xml_signature = template_signature_data_xml % {'data_xml_signature_ref_zero': data_xml_signature_ref_zero,
                                                            'data_public_certificate_base': data_public_certificate_base,
                                                            'data_xml_keyinfo_base': data_xml_keyinfo_base,
                                                            'data_xml_politics': data_xml_politics,
                                                            'data_xml_SignedProperties_base': data_xml_SignedProperties_base,
                                                            'data_xml_SigningTime': data_xml_SigningTime,
                                                            'CertDigestDigestValue': dian_constants['CertDigestDigestValue'],
                                                            'IssuerName': dian_constants['IssuerName'],
                                                            'SerialNumber': dian_constants['SerialNumber'],
                                                            'SignatureValue': data_xml_SignatureValue,
                                                            'identifier': data_constants_document['identifier'],
                                                            'identifierkeyinfo': data_constants_document['identifierkeyinfo'],
                                                            }
        return data_xml_signature

    def _get_dian_constants(self, payslip):
        company = self.env.user.company_id
        partner = company.partner_id
        dian_constants = {}
        # Ruta en donde se almacenaran los archivos que utiliza y genera la Facturación Electrónica
        dian_constants['document_repository'] = company.document_repository
        # Identificador del software en estado en pruebas o activo
        dian_constants['Username'] = company.software_identification_code_payroll
        # Es el resultado de aplicar la función de resumen SHA-256 sobre la contraseña del software en estado en pruebas o activo
        dian_constants['Password'] = hashlib.new(
            'sha256', company.password_environment.encode()).hexdigest()
        # Identificador de pais
        dian_constants['IdentificationCode'] = partner.country_id.code
        # ID Proveedor de software o cliente si es software propio
        dian_constants['ProviderID'] = partner.xidentification if partner.xidentification else ''
        # ID del software a utilizar          # Código de seguridad del software: (hashlib.new('sha384', str(payslip.company_id.software_id) + str(payslip.company_id.software_pin)))
        dian_constants['SoftwareID'] = company.software_identification_code_payroll
        dian_constants['PINSoftware'] = company.software_pin_payroll
        dian_constants['SeedCode'] = company.seed_code
        # Versión base de UBL usada. Debe marcar UBL 2.0
        dian_constants['UBLVersionID'] = 'UBL 2.1'
        # Versión del Formato: Indicar versión del documento. Debe usarse "DIAN 1.0"
        dian_constants['ProfileID'] = 'DIAN 2.1'
        dian_constants['CustomizationID'] = company.operation_type
        # 1 = produccción 2 = prueba
        dian_constants['ProfileExecutionID'] = company.is_test
        # Persona natural o jurídica (persona natural, jurídica, gran contribuyente, otros)
        dian_constants['SupplierAdditionalAccountID'] = '1' if partner.is_company else '2'
        # Identificador fiscal: En Colombia, el NIT
        dian_constants['SupplierID'] = partner.xidentification if partner.xidentification else ''
        dian_constants['SupplierSchemeID'] = partner.doctype
        dian_constants['SupplierPartyName'] = self._replace_character_especial(
            partner.name)            # Nombre Comercial
        # Ciudad o departamento (No requerido)
        dian_constants['SupplierDepartment'] = partner.state_id.name
        # Municipio tabla 6.4.3 res.country.state.city
        dian_constants['SupplierCityCode'] = partner.xcity.code
        # Municipio tabla 6.4.3 res.country.state.city
        dian_constants['SupplierCityName'] = partner.xcity.name
        # Ciudad o departamento tabla 6.4.2 res.country.state
        dian_constants['SupplierCountrySubentity'] = partner.state_id.name
        # Ciudad o departamento tabla 6.4.2 res.country.state
        dian_constants['SupplierCountrySubentityCode'] = partner.xcity.code[0:2]
        # País tabla 6.4.1 res.country
        dian_constants['SupplierCountryCode'] = partner.country_id.code
        # País tabla 6.4.1 res.country
        dian_constants['SupplierCountryName'] = partner.country_id.name
        # Calle
        dian_constants['SupplierLine'] = partner.street
        # Razón Social: Obligatorio en caso de ser una persona jurídica. Razón social de la empresa
        dian_constants['SupplierRegistrationName'] = company.trade_name
        # Digito verificador del NIT
        dian_constants['schemeID'] = partner.dv
        dian_constants['SupplierElectronicMail'] = partner.email
        # tabla 6.2.4 Régimes fiscal (listname) y 6.2.7 Responsabilidades fiscales
        dian_constants['SupplierTaxLevelCode'] = self._get_partner_fiscal_responsability_code(
            partner.id)
        dian_constants['Certificate'] = company.digital_certificate
        dian_constants['NitSinDV'] = partner.xidentification
        dian_constants['CertificateKey'] = company.certificate_key
        dian_constants['archivo_pem'] = company.pem
        dian_constants['archivo_certificado'] = company.certificate
        dian_constants['CertDigestDigestValue'] = self._generate_CertDigestDigestValue(
            company.digital_certificate, dian_constants['CertificateKey'], dian_constants['document_repository'], dian_constants['archivo_certificado'])
        # Nombre del proveedor del certificado
        dian_constants['IssuerName'] = company.issuer_name
        # Serial del certificado
        dian_constants['SerialNumber'] = company.serial_number
        dian_constants['TaxSchemeID'] = partner.tribute_id.code
        dian_constants['TaxSchemeName'] = partner.tribute_id.name
        dian_constants['Currency'] = company.currency_id.id
        CertDigest = self._generate_CertDigestDigestValue(company.digital_certificate, dian_constants['CertificateKey'], dian_constants['document_repository'], dian_constants['archivo_certificado'])
        for crt in CertDigest:
            dian_constants.update(crt)
        dian_constants['ContCertDigestDigestValue'] = len(CertDigest)
        return dian_constants

    def _template_signature_data_xml(self):
        template_signature_data_xml = """
                <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-%(identifier)s">
                    <ds:SignedInfo>
                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
                        <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha512"/>
                        <ds:Reference Id="xmldsig-%(identifier)s-ref0" URI="">
                            <ds:Transforms>
                                <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                            </ds:Transforms>
                            <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha512"/>
                            <ds:DigestValue>%(data_xml_signature_ref_zero)s</ds:DigestValue>
                        </ds:Reference>
                        <ds:Reference URI="#xmldsig-%(identifierkeyinfo)s-keyinfo">
                            <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha512"/>
                            <ds:DigestValue>%(data_xml_keyinfo_base)s</ds:DigestValue>
                        </ds:Reference>
                        <ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-%(identifier)s-signedprops">
                            <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha512"/>
                            <ds:DigestValue>%(data_xml_SignedProperties_base)s</ds:DigestValue>
                        </ds:Reference>
                    </ds:SignedInfo>
                    <ds:SignatureValue Id="xmldsig-%(identifier)s-sigvalue">%(SignatureValue)s</ds:SignatureValue>
                    <ds:KeyInfo Id="xmldsig-%(identifierkeyinfo)s-keyinfo">
                        <ds:X509Data>
                            <ds:X509Certificate>%(data_public_certificate_base)s</ds:X509Certificate>
                        </ds:X509Data>
                    </ds:KeyInfo>
                    <ds:Object>
                        <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" Target="#xmldsig-%(identifier)s">
                            <xades:SignedProperties Id="xmldsig-%(identifier)s-signedprops">
                                <xades:SignedSignatureProperties>
                                    <xades:SigningTime>%(data_xml_SigningTime)s</xades:SigningTime>
                                    <xades:SigningCertificate>
                                        <xades:Cert/>
                                    </xades:SigningCertificate>
                                    <xades:SignaturePolicyIdentifier>
                                        <xades:SignaturePolicyId>
                                            <xades:SigPolicyId>
                                                <xades:Identifier>https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf</xades:Identifier>
                                                <xades:Description>Política de firma para facturas electrónicas de la República de Colombia.</xades:Description>
                                            </xades:SigPolicyId>
                                            <xades:SigPolicyHash>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha512"/>
                                                <ds:DigestValue>%(data_xml_politics)s</ds:DigestValue>
                                            </xades:SigPolicyHash>
                                        </xades:SignaturePolicyId>
                                    </xades:SignaturePolicyIdentifier>
                                    <xades:SignerRole>
                                        <xades:ClaimedRoles>
                                            <xades:ClaimedRole>supplier</xades:ClaimedRole>
                                        </xades:ClaimedRoles>
                                    </xades:SignerRole>
                                </xades:SignedSignatureProperties>
                            </xades:SignedProperties>
                        </xades:QualifyingProperties>
                    </ds:Object>
                </ds:Signature>"""
        return template_signature_data_xml    

    def _template_signature_data_xml_(self):
        """template_signature_data_xml = 
                <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="%(identifier)s">
                    <ds:SignedInfo>
                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315" />
                        <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256" />
                        <ds:Reference Id="xmldsig-%(identifier)s-ref0" URI="">
                            <ds:Transforms>
                                <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature" />
                            </ds:Transforms>
                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256" />
                            <ds:DigestValue>%(data_xml_signature_ref_zero)s</ds:DigestValue>
                        </ds:Reference>
                        <ds:Reference Id="xmldsig-%(identifierkeyinfo)s-ref1" URI="#KeyInfo">
                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256" />
                            <ds:DigestValue>%(data_xml_keyinfo_base)s</ds:DigestValue>
                        </ds:Reference>
                        <ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-%(identifier)s-signedprops">
                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256" />
                            <ds:DigestValue>%(data_xml_SignedProperties_base)s</ds:DigestValue>
                        </ds:Reference>
                    </ds:SignedInfo>
                    <ds:SignatureValue Id="xmldsig-%(data_xml_SignedProperties_base)s-sigvalue">%(SignatureValue)s</ds:SignatureValue>
                    <ds:KeyInfo Id="KeyInfo">
                        <ds:X509Data>
                            <ds:X509Certificate>%(data_public_certificate_base)s</ds:X509Certificate>
                        </ds:X509Data>
                    </ds:KeyInfo>
                    <ds:Object>
                        <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" Target="#xmldsig-%(identifier)s">
                            <xades:SignedProperties Id="xmldsig-%(identifier)s-signedprops">
                                <xades:SignedSignatureProperties>
                                    <xades:SigningTime>%(data_xml_SigningTime)s</xades:SigningTime>
                                    <xades:SigningCertificate>
                                        <xades:Cert>
                                            <xades:CertDigest>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256" />
                                                <ds:DigestValue>rbOe7W+EdDtpKjbKW+dx+95Gk/DEfNQzX9e3H1Cy+mU=</ds:DigestValue>
                                            </xades:CertDigest>
                                            <xades:IssuerSerial>
                                                <ds:X509IssuerName>C=CO,L=Bogota D.C.,O=Andes SCD.,OU=Division de certificacion entidad final,CN=CA ANDES SCD S.A. Clase II,1.2.840.113549.1.9.1=#1614696e666f40616e6465737363642e636f6d2e636f</ds:X509IssuerName>
                                                <ds:X509SerialNumber>1634039876081436951</ds:X509SerialNumber>
                                            </xades:IssuerSerial>
                                        </xades:Cert>
                                        <xades:Cert>
                                            <xades:CertDigest>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256" />
                                                <ds:DigestValue>Cs7emRwtXWVYHJrqS9eXEXfUcFyJJBqFhDFOetHu8ts=</ds:DigestValue>
                                            </xades:CertDigest>
                                            <xades:IssuerSerial>
                                                <ds:X509IssuerName>C=CO,L=Bogota D.C.,O=Andes SCD,OU=Division de certificacion,CN=ROOT CA ANDES SCD S.A.,1.2.840.113549.1.9.1=#1614696e666f40616e6465737363642e636f6d2e636f</ds:X509IssuerName>
                                                <ds:X509SerialNumber>3184328748892787122</ds:X509SerialNumber></xades:IssuerSerial></xades:Cert><xades:Cert><xades:CertDigest><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256" /><ds:DigestValue>PbsKGMpB0A2Y9NAz6F8LkU5nR+ONJASyK9D/bRTdbZ0=</ds:DigestValue></xades:CertDigest><xades:IssuerSerial><ds:X509IssuerName>C=CO,L=Bogota D.C.,O=Andes SCD,OU=Division de certificacion,CN=ROOT CA ANDES SCD S.A.,1.2.840.113549.1.9.1=#1614696e666f40616e6465737363642e636f6d2e636f</ds:X509IssuerName><ds:X509SerialNumber>4951343590990220136</ds:X509SerialNumber></xades:IssuerSerial></xades:Cert></xades:SigningCertificate><xades:SignaturePolicyIdentifier><xades:SignaturePolicyId><xades:SigPolicyId><xades:Identifier>https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf</xades:Identifier></xades:SigPolicyId><xades:SigPolicyHash><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256" /><ds:DigestValue>dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y=</ds:DigestValue></xades:SigPolicyHash></xades:SignaturePolicyId></xades:SignaturePolicyIdentifier><xades:SignerRole><xades:ClaimedRoles><xades:ClaimedRole>third party</xades:ClaimedRole></xades:ClaimedRoles></xades:SignerRole></xades:SignedSignatureProperties></xades:SignedProperties></xades:QualifyingProperties></ds:Object></ds:Signature>"""
        template_signature_data_xml = """
                <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-%(identifier)s">
                    <ds:SignedInfo>
                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
                        <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha512"/>
                        <ds:Reference Id="xmldsig-%(identifier)s-ref0" URI="">
                            <ds:Transforms>
                                <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                            </ds:Transforms>
                            <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha512"/>
                            <ds:DigestValue>%(data_xml_signature_ref_zero)s</ds:DigestValue>
                        </ds:Reference>
                        <ds:Reference URI="#xmldsig-%(identifierkeyinfo)s-keyinfo">
                            <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha512"/>
                            <ds:DigestValue>%(data_xml_keyinfo_base)s</ds:DigestValue>
                        </ds:Reference>
                        <ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-%(identifier)s-signedprops">
                            <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha512"/>
                            <ds:DigestValue>%(data_xml_SignedProperties_base)s</ds:DigestValue>
                        </ds:Reference>
                    </ds:SignedInfo>
                    <ds:SignatureValue Id="xmldsig-%(identifier)s-sigvalue">%(SignatureValue)s</ds:SignatureValue>
                    <ds:KeyInfo Id="xmldsig-%(identifierkeyinfo)s-keyinfo">
                        <ds:X509Data>
                            <ds:X509Certificate>%(data_public_certificate_base)s</ds:X509Certificate>
                        </ds:X509Data>
                    </ds:KeyInfo>
                    <ds:Object>
                        <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" Target="#xmldsig-%(identifier)s">
                            <xades:SignedProperties Id="xmldsig-%(identifier)s-signedprops">
                                <xades:SignedSignatureProperties>
                                    <xades:SigningTime>%(data_xml_SigningTime)s</xades:SigningTime>
                                    <xades:SigningCertificate>
                                        <xades:Cert/>
                                    </xades:SigningCertificate>
                                    <xades:SignaturePolicyIdentifier>
                                        <xades:SignaturePolicyId>
                                            <xades:SigPolicyId>
                                                <xades:Identifier>https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf</xades:Identifier>
                                                <xades:Description>Política de firma para facturas electrónicas de la República de Colombia.</xades:Description>
                                            </xades:SigPolicyId>
                                            <xades:SigPolicyHash>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha512"/>
                                                <ds:DigestValue>%(data_xml_politics)s</ds:DigestValue>
                                            </xades:SigPolicyHash>
                                        </xades:SignaturePolicyId>
                                    </xades:SignaturePolicyIdentifier>
                                    <xades:SignerRole>
                                        <xades:ClaimedRoles>
                                            <xades:ClaimedRole>supplier</xades:ClaimedRole>
                                        </xades:ClaimedRoles>
                                    </xades:SignerRole>
                                </xades:SignedSignatureProperties>
                            </xades:SignedProperties>
                        </xades:QualifyingProperties>
                    </ds:Object>
                </ds:Signature>"""
        return template_signature_data_xml

    def template_SendNominaSyncTest_xml(self):
        template_SendNominaSync = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
                                        <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
                                            <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                                                <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                                                    <wsu:Created>%(Created)s</wsu:Created>
                                                    <wsu:Expires>%(Expires)s</wsu:Expires>
                                                </wsu:Timestamp>
                                                <wsse:BinarySecurityToken
                                                EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"
                                                ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
                                                wsu:Id="X509-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
                                                <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                                                    <ds:SignedInfo>
                                                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                                            <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                                                        </ds:CanonicalizationMethod>
                                                        <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                                                        <ds:Reference URI="#id-%(identifierTo)s">
                                                            <ds:Transforms>
                                                                <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                                                    <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                                                                </ds:Transform>
                                                            </ds:Transforms>
                                                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                                            <ds:DigestValue></ds:DigestValue>
                                                        </ds:Reference>
                                                    </ds:SignedInfo>
                                                    <ds:SignatureValue></ds:SignatureValue>
                                                    <ds:KeyInfo Id="KI-%(identifier)s">
                                                        <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                                                            <wsse:Reference URI="#X509-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                                                        </wsse:SecurityTokenReference>
                                                    </ds:KeyInfo>
                                                </ds:Signature>
                                            </wsse:Security>
                                            <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/SendTestSetAsync</wsa:Action>
                                            <wsa:To wsu:Id="id-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
                                        </soap:Header>
                                        <soap:Body>
                                            <wcf:SendTestSetAsync>
                                                <wcf:fileName>%(fileName)s</wcf:fileName>
                                                <wcf:contentFile>%(contentFile)s</wcf:contentFile>
                                                <wcf:testSetId>%(testSetId)s</wcf:testSetId>
                                            </wcf:SendTestSetAsync>
                                        </soap:Body>
                                    </soap:Envelope>"""
        return template_SendNominaSync

    def template_GetStatusZip_xml(self):
        template_GetStatusZip = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
                                        <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
                                            <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                                                <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                                                    <wsu:Created>%(Created)s</wsu:Created>
                                                    <wsu:Expires>%(Expires)s</wsu:Expires>
                                                </wsu:Timestamp>
                                                <wsse:BinarySecurityToken
                                                EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"
                                                ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
                                                wsu:Id="X509-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
                                                <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                                                    <ds:SignedInfo>
                                                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                                            <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                                                        </ds:CanonicalizationMethod>
                                                        <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                                                        <ds:Reference URI="#id-%(identifierTo)s">
                                                            <ds:Transforms>
                                                                <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                                                    <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                                                                </ds:Transform>
                                                            </ds:Transforms>
                                                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                                            <ds:DigestValue></ds:DigestValue>
                                                        </ds:Reference>
                                                    </ds:SignedInfo>
                                                    <ds:SignatureValue></ds:SignatureValue>
                                                    <ds:KeyInfo Id="KI-%(identifier)s">
                                                        <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                                                            <wsse:Reference URI="#X509-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                                                        </wsse:SecurityTokenReference>
                                                    </ds:KeyInfo>
                                                </ds:Signature>
                                            </wsse:Security>
                                            <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/GetStatusZip</wsa:Action>
                                            <wsa:To wsu:Id="id-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
                                        </soap:Header>
                                        <soap:Body>
                                            <wcf:GetStatusZip>
                                                <wcf:trackId>%(trackId)s</wcf:trackId>
                                            </wcf:GetStatusZip>
                                        </soap:Body>
                                    </soap:Envelope>"""
        return template_GetStatusZip

    def template_GetStatus_xml(self):
        template_GetStatusZip = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
                                        <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
                                            <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                                                <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                                                    <wsu:Created>%(Created)s</wsu:Created>
                                                    <wsu:Expires>%(Expires)s</wsu:Expires>
                                                </wsu:Timestamp>
                                                <wsse:BinarySecurityToken
                                                EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"
                                                ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
                                                wsu:Id="X509-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
                                                <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                                                    <ds:SignedInfo>
                                                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                                            <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                                                        </ds:CanonicalizationMethod>
                                                        <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                                                        <ds:Reference URI="#id-%(identifierTo)s">
                                                            <ds:Transforms>
                                                                <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                                                    <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                                                                </ds:Transform>
                                                            </ds:Transforms>
                                                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                                            <ds:DigestValue></ds:DigestValue>
                                                        </ds:Reference>
                                                    </ds:SignedInfo>
                                                    <ds:SignatureValue></ds:SignatureValue>
                                                    <ds:KeyInfo Id="KI-%(identifier)s">
                                                        <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                                                            <wsse:Reference URI="#X509-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                                                        </wsse:SecurityTokenReference>
                                                    </ds:KeyInfo>
                                                </ds:Signature>
                                            </wsse:Security>
                                            <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/GetStatus</wsa:Action>
                                            <wsa:To wsu:Id="id-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
                                        </soap:Header>
                                        <soap:Body>
                                            <wcf:GetStatus>
                                                <wcf:trackId>%(trackId)s</wcf:trackId>
                                            </wcf:GetStatus>
                                        </soap:Body>
                                    </soap:Envelope>"""
        return template_GetStatusZip

    def generate_datetime_timestamp(self):
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = datetime.now(timezone('UTC'))
        #now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        Created = now_bogota.strftime(fmt)[:-3]+'Z'
        now_bogota = now_bogota + timedelta(minutes=5)
        Expires = now_bogota.strftime(fmt)[:-3]+'Z'
        timestamp = {'Created': Created,
                     'Expires': Expires
                     }
        return timestamp

    def sign_request_post(self, post_xml_to_sign, payslip):
        dian_constants = self._get_dian_constants(payslip)
        parser = etree.XMLParser(remove_blank_text=True)
        data_xml_send = etree.tostring(
            etree.XML(post_xml_to_sign, parser=parser))
        data_xml_send = data_xml_send.decode()
        #   Generar DigestValue Elemento to y lo reemplaza en el xml
        ElementTO = etree.fromstring(data_xml_send)
        ElementTO = etree.tostring(ElementTO[0])
        ElementTO = etree.fromstring(ElementTO)
        ElementTO = etree.tostring(ElementTO[2])
        DigestValueTO = self.generate_digestvalue_to(ElementTO)
        data_xml_send = data_xml_send.replace(
            '<ds:DigestValue/>', '<ds:DigestValue>%s</ds:DigestValue>' % DigestValueTO)
        #   Generar firma para el header de envío con el Signedinfo
        Signedinfo = etree.fromstring(data_xml_send)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[2])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = Signedinfo.decode()
        Signedinfo = Signedinfo.replace('<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">',
                                        '<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia" xmlns:wsa="http://www.w3.org/2005/08/addressing">')
        password = dian_constants['CertificateKey']
        SignatureValue = self.generate_SignatureValue_GetStatus(
            dian_constants['document_repository'], password, Signedinfo, dian_constants['archivo_pem'], dian_constants['archivo_certificado'])
        data_xml_send = data_xml_send.replace(
            '<ds:SignatureValue/>', '<ds:SignatureValue>%s</ds:SignatureValue>' % SignatureValue)
        return data_xml_send

    def _generate_data_constants_document(self):
        data_constants_document = {}
        # Genera identificadores único
        identifier = uuid.uuid4()
        data_constants_document['identifier'] = str(identifier)
        identifierkeyinfo = uuid.uuid4()
        data_constants_document['identifierkeyinfo'] = str(identifierkeyinfo)
        return data_constants_document

    def send_2_validate(self, payslip, temp, emp, dic_cons, dic_cune):
        
        company = self.env.user.company_id
        code_doc = payslip.credit_note and '103' or '102'
        company_id = self.env.user.company_id
        data_constants_document = self._generate_data_constants_document()
        dian_constants = self._get_dian_constants(payslip)
        parser = etree.XMLParser(remove_blank_text=True)
        payslip_template = temp[emp]
        payslip_template = '<?xml version="1.0" encoding="UTF-8"?>' + payslip_template
        xml = payslip_template.encode('utf-8')
        template_basic_data_nomina_individual_xml = etree.tostring(etree.XML(xml, parser=parser), encoding="UTF-8")
        template_basic_data_nomina_individual_xml = template_basic_data_nomina_individual_xml.decode()
        data_xml_document = template_basic_data_nomina_individual_xml
        data_xml_document = data_xml_document.replace("<ext:ExtensionContent/>","<ext:ExtensionContent></ext:ExtensionContent>")
        template_signature_data_xml = self._template_signature_data_xml()
        template_signature_data_xml = self._template_signature_data_cert_xml(dian_constants, template_signature_data_xml)
        data_xml_signature = self._generate_signature(data_xml_document, template_signature_data_xml, dian_constants, data_constants_document)
        xml = data_xml_signature.encode('utf-8')
        data_xml_signature = etree.tostring(etree.XML(xml, parser=parser), encoding="UTF-8")
        data_xml_signature = data_xml_signature.decode()

        data_xml_document = data_xml_document.replace("<ext:ExtensionContent></ext:ExtensionContent>",
                                                          "<ext:ExtensionContent>%s</ext:ExtensionContent>" % data_xml_signature)
        data_xml_document = '<?xml version="1.0" encoding="UTF-8"?>' + data_xml_document
        year_digits = fields.Date.today().strftime('%-y')
        numero_nombre = dic_cons['Consecutivo']
        ceros = (8 - len(numero_nombre))* "0"
        
        filename = ('nie%s%s%s%s.xml' % (company_id.partner_id.xidentification, year_digits, ceros, numero_nombre))
        Document = self._generate_zip_content(filename.replace("xml", 'zip'), data_xml_document, dian_constants['document_repository'], filename)
        self.l10n_co_payslip_attch_name = filename
        template_SendNominaSync_xml = company.is_test == '1' and self.template_SendNominaSync_xml() or self.template_SendNominaSyncTest_xml() 
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self.generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']
        cer = dian_constants['Certificate']
        data_xml_send = self.generate_SendTestSetAsync_send_xml(template_SendNominaSync_xml, identifier, Created, Expires,
                    cer, identifierSecurityToken, identifierTo, Document, filename, company_id.identificador_set_pruebas_payroll)
        msg = ""
        
        data_xml_send = self.sign_request_post(data_xml_send, payslip)
        headers = {'content-type': 'application/soap+xml'}
        url = URLSEND[company_id.is_test]
        #return data_xml_document, Document, msg, filename
        try:
            response = requests.post(url, data=data_xml_send, headers=headers)
            time.sleep(10)

        except:
            raise UserError("No existe conexión con servidor DIAN")
        response_dict = xmltodict.parse(response.content)
        status_code = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:StatusCode", "")
        if response.status_code == 200:
            if company_id.is_test == "2":
                response_dict = xmltodict.parse(response.content)
                status_code = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:StatusCode", "")
                """if status_code == "66" or status_code == "99":
                    error = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:ErrorMessage", "").get("c:string", "")
                    if type(error) == list:
                        for elements in error:
                            msg += elements + "\n"
                    elif type(error) == str:
                        msg = error
                    return data_xml_document, Document, msg, filename """
                #self.trackid = trackId
                getstatus_xml_send = self.generate_GetStatusZip_send_xml(self.template_GetStatus_xml(), identifier, Created, Expires,
                        cer, identifierSecurityToken, identifierTo, dic_cune)
                getstatus_xml_send = self.sign_request_post(getstatus_xml_send, payslip)
                time.sleep(1)
                try:
                    response_get_status = requests.post(url, data=getstatus_xml_send, headers=headers)
                except:
                    _logger.info("no se pudo obtener el estado")
                
                #response_dict = xmltodict.parse(response_get_status.content)
                get_sattus_dic = xmltodict.parse(response_get_status.content)
                _get_status_code = get_sattus_dic.get("s:Envelope", {}).get("s:Body", {}).get("GetStatusResponse", {}).get("GetStatusResult", {}).get("b:StatusCode", "")
                if _get_status_code == "66" or _get_status_code == "99":
                    error = get_sattus_dic.get("s:Envelope", {}).get("s:Body", {}).get("GetStatusResponse", {}).get("GetStatusResult", {}).get("b:ErrorMessage", "").get("c:string", "")
                    if type(error) == list:
                        for elements in error:
                            msg += elements + "\n"
                    elif type(error) == str:
                        msg = error
                    return data_xml_document, Document, msg, filename, "rechazada"
                elif _get_status_code == "00":
                    msg = get_sattus_dic.get("s:Envelope", {}).get("s:Body", {}).get("GetStatusResponse", {}).get("GetStatusResult", {}).get("b:StatusMessage", "")
                    return data_xml_document, Document, msg, filename, "exitosa"
                
            else:
                response_dict = xmltodict.parse(response.content)
                status = self.trackid = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:XmlDocumentKey", '')
                response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:IsValid", "false")
                status = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:IsValid", "false")
                if status == "false":
                    error = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:ErrorMessage", "").get("c:string", "")
                    if type(error) == list:
                        for elements in error:
                            msg += elements + "\n"
                    elif type(error) == str:
                        msg = error
                    return data_xml_document, Document, msg, filename, "rechazada"
                elif status == "true":
                    msg = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:StatusMessage", "")
                    return data_xml_document, Document, msg, filename, "exitosa"
                    
        else:
            msg = "Ha ocurrido algún problema con el servicio de DIAN, por favor intente enviar nuevamente el documento"
        
        if data_xml_document:
            attachment_id = self.env['ir.attachment'].create({
                'name': filename,
                'res_id': self.id,
                'res_model': self._name,
                'datas': base64.b64encode(data_xml_document.encode()),
                'datas_fname': filename,
                'description': 'Nomina test',
                })
            return data_xml_document, Document, msg, filename

    
           
       
    def template_SendNominaSync_xml(self):
        template_SendNominaSync = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
                                        <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
                                            <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                                                <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                                                    <wsu:Created>%(Created)s</wsu:Created>
                                                    <wsu:Expires>%(Expires)s</wsu:Expires>
                                                </wsu:Timestamp>
                                                <wsse:BinarySecurityToken
                                                EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"
                                                ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
                                                wsu:Id="X509-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
                                                <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                                                    <ds:SignedInfo>
                                                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                                            <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                                                        </ds:CanonicalizationMethod>
                                                        <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                                                        <ds:Reference URI="#id-%(identifierTo)s">
                                                            <ds:Transforms>
                                                                <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                                                    <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                                                                </ds:Transform>
                                                            </ds:Transforms>
                                                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                                            <ds:DigestValue></ds:DigestValue>
                                                        </ds:Reference>
                                                    </ds:SignedInfo>
                                                    <ds:SignatureValue></ds:SignatureValue>
                                                    <ds:KeyInfo Id="KI-%(identifier)s">
                                                        <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                                                            <wsse:Reference URI="#X509-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                                                        </wsse:SecurityTokenReference>
                                                    </ds:KeyInfo>
                                                </ds:Signature>
                                            </wsse:Security>
                                            <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/SendNominaSync</wsa:Action>
                                            <wsa:To wsu:Id="id-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
                                        </soap:Header>
                                        <soap:Body>
                                            <wcf:SendNominaSync>
                                                <wcf:contentFile>%(contentFile)s</wcf:contentFile>
                                            </wcf:SendNominaSync>
                                        </soap:Body>
                                    </soap:Envelope>"""
        return template_SendNominaSync


    def _template_signature_data_cert_xml(self, dian_constants, template_signature_data_xml):
        CertDigestDigestValue = """<xades:Cert>
                                        <xades:CertDigest>
                                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha512"/>
                                            <ds:DigestValue>%(CertDigestDigestValue0)s</ds:DigestValue>
                                        </xades:CertDigest>
                                        <xades:IssuerSerial>
                                            <ds:X509IssuerName>%(IssuerName0)s</ds:X509IssuerName>
                                            <ds:X509SerialNumber>%(SerialNumber0)s</ds:X509SerialNumber>
                                        </xades:IssuerSerial>
                                    </xades:Cert>"""
        x = ''
        for cont in range(dian_constants['ContCertDigestDigestValue']):
            nro = cont-1
            CertDigestDigestValue = CertDigestDigestValue.replace('CertDigestDigestValue%s'%nro,'CertDigestDigestValue%s'%cont)
            CertDigestDigestValue = CertDigestDigestValue.replace('IssuerName%s'%nro,'IssuerName%s'%cont)
            CertDigestDigestValue = CertDigestDigestValue.replace('SerialNumber%s'%nro,'SerialNumber%s'%cont)
            convert = CertDigestDigestValue % {
                                'CertDigestDigestValue%s'%cont: dian_constants['CertDigestDigestValue%s'%cont],
                                'IssuerName%s'%cont: dian_constants['IssuerName%s'%cont],
                                'SerialNumber%s'%cont: dian_constants['SerialNumber%s'%cont],
                            }
            x += convert

        template_signature_data_xml = template_signature_data_xml.replace('<xades:Cert/>', x)
        return template_signature_data_xml


    def _send_2_validate(self, payslip, temp, emp):
        company = self.env.user.company_id
        dian_documents = self.env['payroll.payroll.window']
        parser = etree.XMLParser(remove_blank_text=True)
        code_doc = payslip.credit_note and '103' or '102'
        dian_constants = self._get_dian_constants(payslip)
        result = self._create_payslip_xml_template(payslip)
        result = result.decode('utf-8')
        result = temp[emp]
        #result = etree.tostring(etree.XML(result, parser=parser))
        #result = result.decode()
        result = '<?xml version="1.0" encoding="UTF-8"?>' + result
        signature = self._generate_signature(result, self._template_signature_data_xml(), self._get_dian_constants(self.env['hr.payslip']), self._generate_data_constants_document())
        
        result = result.replace("<ext:ExtensionContent/>", signature)
        result = base64.b64encode(result.encode("utf-8"))
        archivo_key = dian_constants['document_repository'] + \
            '/' + dian_constants['archivo_certificado']
        CerificadoEmpleadorB64 = open(archivo_key, 'rb').read()
        CerificadoEmpleadorB64 = base64.b64encode(CerificadoEmpleadorB64)
        PinCertificadoB64 = base64.b64encode(
            dian_constants['CertificateKey'].encode("ascii"))
        NitEmpleador = dian_constants['NitSinDV']
        #result = self.generate_xmlsigned(
            #code_doc, result, CerificadoEmpleadorB64, PinCertificadoB64, NitEmpleador)


        #if result.get("XmlsNominasB64", []) and result.get("XmlsNominasB64", [])[0].get("Firmado", False):
         #   result = result.get("XmlsNominasB64", []) and result.get(
          #      "XmlsNominasB64", [])[0].get("XmlB64", "")
        year_digits = fields.Date.today().strftime('%-y')
        filename = ('nie%s%s00000001.xml' % (company.partner_id.xidentification, year_digits))
        Document = self._generate_zip_content(filename.replace("xml", 'zip'), base64.b64decode(
            result), dian_constants['document_repository'], filename)
        self.l10n_co_payslip_attch_name = filename
        template_GetStatus_xml = company.is_test == '1' and self.template_SendNominaSync_xml() or self.template_SendNominaSyncTest_xml()
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self.generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']
        cer = dian_constants['Certificate']
        data_xml_send = self.generate_SendTestSetAsync_send_xml(template_GetStatus_xml, identifier, Created, Expires,
                                                                cer, identifierSecurityToken, identifierTo, Document, filename, payslip.company_id.identificador_set_pruebas_payroll)
        msg = ""

        data_xml_send = self.sign_request_post(data_xml_send, payslip)

        headers = {'content-type': 'application/soap+xml'}

        
        url = URLSEND[company.is_test]
        
        try:
            response = requests.post(url, data=data_xml_send, headers=headers)
            time.sleep(1)
        except:
            raise UserError("No existe conexión con servidor DIAN")

        if response.status_code == 200:
            if payslip.company_id.is_test == "2":
                response_dict = xmltodict.parse(response.content)
                trackId = response_dict.get("s:Envelope", {}).get("s:Body", {}).get(
                    "SendTestSetAsyncResponse", {}).get("SendTestSetAsyncResult", {}).get("b:ZipKey", '')
                self.trackid = trackId
                getstatus_xml_send = self.generate_GetStatusZip_send_xml(self.template_GetStatusZip_xml(), identifier, Created, Expires,
                                                                         cer, identifierSecurityToken, identifierTo, trackId)
                getstatus_xml_send = self.sign_request_post(
                    getstatus_xml_send, payslip)
                response = requests.post(
                    url, data=getstatus_xml_send, headers=headers)
                response_dict = xmltodict.parse(response.content)
                dian_response_dict = response_dict.get("s:Envelope", {}).get("s:Body", {}).get(
                    "GetStatusZipResponse", {}).get("GetStatusZipResult", {}).get("b:DianResponse", {})
                if dian_response_dict.get("b:IsValid", "false") == "true":
                    self.l10n_co_dian_status = "valid"
                else:
                    msg = dian_response_dict.get("b:StatusDescription", '')
            else:
                response_dict = xmltodict.parse(response.content)
                self.trackid = response_dict.get("s:Envelope", {}).get("s:Body", {}).get(
                    "SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:XmlDocumentKey", '')
                if response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:IsValid", "false") == "false":
                    msg += "<p>Se encontraron los siguientes errores:</p>"
                for ms_error in response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:ErrorMessage", {}).get("c:string", []):
                    _logger.info(
                        ms_error, "error de la frese?...................................................?????????????????????????'")
                    msg += "<p>" + ms_error + "</p>"
        else:
            msg = "Ha ocurrido algún problema con el servicio del DIAN, por favor intente enviar nuevamente el documento"

        if result:
            attachment_id = self.env['ir.attachment'].create({
                'name': filename,
                'res_id': self.id,
                'res_model': self._name,
                'datas': result,
                'datas_fname': filename,
                'description': 'Nomina test',
            })

            '''dian_documents.message_post(
                body=msg,
                attachment_ids=[attachment_id.id],
                subtype='account.mt_invoice_validated')'''
        return result