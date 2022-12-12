# -*- coding: utf-8 -*-

from email.policy import default
from cgi import print_arguments
import zipfile
from numpy import diag_indices
from odoo import fields, models, api, _, tools
from odoo.exceptions import Warning, UserError, ValidationError

import hashlib
from datetime import datetime, timedelta, date
from pytz import timezone
from lxml import etree
import base64
import requests
import json
import uuid
import xmltodict
import http
import logging
from io import StringIO
from odoo.exceptions import ValidationError
import re

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from OpenSSL import crypto
type_ = crypto.FILETYPE_PEM
_logger = logging.getLogger("HOLI!!!!!!!")
import zipfile

try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

log = logging.getLogger('requests')
log.setLevel(logging.DEBUG)
http.client.HTTPConnection.debuglevel = 1

import base64

PAYSLIP_TEMPLATE = 'l10n_co_payroll.payslip_template'

URLSEND = {
    '1': "https://vpfe.dian.gov.co/WcfDianCustomerServices.svc?wsdl",
    '2': "https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?wsdl",
}

class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'mail.thread', 'mail.activity.mixin']

    adj_method = fields.Selection([('adjustment', 'Adjustment Note'), ('elimination', 'Elimination Note')], string='Adjustment Method')
    refund_reason = fields.Char(string='Reason')
    refund_date = fields.Date(string='Refund Date')
    document_source = fields.Char(string='Document Source')

    payslip_refunded_id = fields.Many2one("hr.payslip", copy=False)
    cune = fields.Char(copy=False)
    trackid = fields.Char(copy=False)
    date_send_dian = fields.Date(copy=False)
    note_type = fields.Selection([('1', 'Ajustar'), ('2', 'Eliminar')], copy=False)

    l10n_co_dian_status = fields.Selection(
        selection=[
            ('none', 'No Definido'),
            ('undefined', 'Sin Enviar'),
            ('not_found', 'No Encontrado'),
            ('cancelled', 'Cancelado'),
            ('valid', 'Exitoso'),
        ],
        string='DIAN status',
        help='Refers to the status of the invoice inside the DIAN system.',
        readonly=True,
        copy=False,
        required=True,
        tracking=True,
        default='undefined')
    l10n_co_pac_status = fields.Selection(
        selection=[
            ('retry', 'Retry'),
            ('to_sign', 'To sign'),
            ('signed', 'Signed'),
            ('to_cancel', 'To cancel'),
            ('cancelled', 'Cancelled')
        ],
        string='PAC status',
        help='Refers to the status of the invoice inside the PAC.',
        readonly=True,
        copy=False)

    l10n_co_payslip_attch_name = fields.Char(string='Payslip name', copy=False, readonly=True,
        help='The attachment name of the CFDI.')

    payment_method = fields.Selection([
        ('1', 'Instrumento no Definido'),
        ('2', 'Crédito ACH'),
        ('3', 'Debito ACH'),
        ('4', 'Reversión débito de demanda ACH'),
        ('5', 'Reversión crédito de demanda ACH'),
        ('6', 'Crédito de demanda ACH'),
        ('7', 'Débito de demanda ACH'),
        ('8', 'Mantener'),
        ('9', 'Clearing Nacional o Regional'),
        ('10', 'Efectivo'),
        ('11', 'Reversión Crédito Ahorro'),
        ('12', 'Reversión Débito Ahorro'),
        ('13', 'Crédito Ahorro'),
        ('14', 'Débito Ahorro'),
        ('15', 'Bookentry Crédito'),
        ('16', 'Bookentry Débito'),
        ('17', 'Concentración de la demanda en efectivo/Desembolso Crédito (CCD)'),
        ('18', 'Concentración de la demanda en efectivo / Desembolso (CCD) débito'),
        ('19', 'Crédito Pago negocio corporativo (CTP)'),
        ('20', 'Cheque'),
        ('21', 'Proyecto bancario'),
        ('22', 'Proyecto bancario certificado'),
        ('23', 'Cheque bancario'),
        ('24', 'Nota cambiaria esperando aceptación'),
        ('25', 'Cheque certificado'),
        ('26', 'Cheque Local'),
        ('27', 'Débito Pago Negocio Corporativo (CTP)'),
        ('28', 'Crédito Negocio Intercambio Corporativo (CTX)'),
        ('29', 'Débito Negocio Intercambio Corporativo (CTX)'),
        ('30', 'Transferencia Crédito'),
        ('31', 'Transferencia Débito'),
        ('32', 'Concentración Efectivo / Desembolso Crédito plus (CCD+)'),
        ('33', 'Concentración Efectivo / Desembolso Débito plus (CCD+)'),
        ('34', 'Pago y depósito pre acordado (PPD)'),
        ('35', 'Concentración efectivo ahorros / Desembolso Crédito (CCD)'),
        ('36', 'Concentración efectivo ahorros / Desembolso Débito (CCD)'),
        ('37', 'Pago Negocio Corporativo Ahorros Crédito (CTP)'),
        ('38', 'Pago Negocio Corporativo Ahorros Débito (CTP)'),
        ('39', 'Crédito Negocio Intercambio Corporativo (CTX)'),
        ('40', 'Débito Negocio Intercambio Corporativo (CTX)'),
        ('41', 'Concentración efectivo/Desembolso Crédito plus (CCD+)'),
        ('42', 'Consignación bancaria'),
        ('43', 'Concentración efectivo / Desembolso Débito plus (CCD+)'),
        ('44', 'Nota cambiaria'),
        ('45', 'Transferencia Crédito Bancario'),
        ('46', 'Transferencia Débito Interbancario'),
        ('47', 'Transferencia Débito Bancaria'),
        ('48', 'Tarjeta Crédito'),
        ('49', 'Tarjeta Débito'),
        ('50', 'Postgiro'),
        ('51', 'Telex estándar bancario francés'),
        ('52', 'Pago comercial urgente'),
        ('53', 'Pago Tesorería Urgente'),
        ('60', 'Nota promisoria'),
        ('61', 'Nota promisoria firmada por el acreedor'),
        ('62', 'Nota promisoria firmada por el acreedor, avalada por el banco'),
        ('63', 'Nota promisoria firmada por el acreedor, avalada por un tercero'),
        ('64', 'Nota promisoria firmada por el banco'),
        ('65', 'Nota promisoria firmada por un banco avalada por otro banco'),
        ('66', 'Nota promisoria firmada'),
        ('67', 'Nota promisoria firmada por un tercero avalada por un banco'),
        ('70', 'Retiro de nota por el por el acreedor'),
        ('71', 'Bonos'),
        ('72', 'Vales'),
        ('74', 'Retiro de nota por el acreedor sobre un banco'),
        ('75', 'Retiro de nota por el acreedor, avalada por otro banco'),
        ('76', 'Retiro de nota por el acreedor, sobre un banco avalada por un tercero'),
        ('77', 'Retiro de una nota por el acreedor sobre un tercero'),
        ('78', 'Retiro de una nota por el acreedor sobre un tercero avalada por un banco'),
        ('91', 'Nota bancaria transferible'),
        ('92', 'Cheque local trasferible'),
        ('93', 'Giro referenciado'),
        ('94', 'Giro urgente'),
        ('95', 'Giro formato abierto'),
        ('96', 'Método de pago solicitado no usado'),
        ('97', 'Clearing entre partners'),
        ('98', 'Cuentas de Ahorro de Tramite Simplificado (CATS)(Nequi, Daviplata, etc)'),
        ('ZZZ', 'Acuerdo mutuo'),
        ],
        string="Metodo de Pago",
        required=True,
        default='1',
        )
    
    it_is_integral = fields.Boolean(string="Es integral", compute='_calculate_integral')
    is_prima = fields.Boolean(string="Incluir Prima de Servicios")
    no_prima_days = fields.Integer(string="Dias Trabajados")
    no_vacac_liq  = fields.Integer(string="Dias Trabajados (Vacaciones)")
    no_cesan_liq = fields.Float()
    no_prima_liq = fields.Float()
    is_liquid = fields.Boolean()
    no_dias_disfrute = fields.Float()

    def refund_sheet(self):
        # for payslip in self:
        #     copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name, 'payslip_refunded_id': payslip.id})
        #     number = copied_payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
        #     copied_payslip.write({'number': number, 'payslip_refunded_id': payslip.id})
        #     copied_payslip.with_context(without_compute_sheet=True).action_payslip_done()
        # formview_ref = self.env.ref('bi_hr_payroll.view_hr_payslip_form', False)
        # treeview_ref = self.env.ref('bi_hr_payroll.view_hr_payslip_tree', False)
        # return {
        #     'name': ("Refund Payslip"),
        #     'view_mode': 'tree, form',
        #     'view_id': False,
        #     'view_type': 'form',
        #     'res_model': 'hr.payslip',
        #     'type': 'ir.actions.act_window',
        #     'target': 'current',
        #     'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
        #     'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
        #     'context': {}
        # }

        ctx = {'default_payslip_id': self.ids[0], 'default_refund_date': self.date_to}
        return {
            'name': ("Adjustment Method"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'payroll.cancel.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    def payslip_main_template(self):
        payslip_main_template = """<%(XmlNodo)s xmlns="dian:gov:co:facturaelectronica:%(XmlNodo)s" SchemaLocation="" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#"
        xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="dian:gov:co:facturaelectronica:NominaIndividual NominaIndividualElectronicaXSD.xsd">
                                    <ext:UBLExtensions>
                                        <ext:UBLExtension>
                                            <ext:ExtensionContent></ext:ExtensionContent>
                                        </ext:UBLExtension>
                                    </ext:UBLExtensions>
                                    <Novedad CUNENov="%(CUNE)s">false</Novedad>
                                    %(Periodo)s
                                    %(NumeroSecuenciaXML)s
                                    %(LugarGeneracionXML)s
                                    %(ProveedorXML)s
                                    <CodigoQR>%(CodigoQR)s</CodigoQR>
                                    %(InformacionGeneral)s
                                    %(Empleador)s
                                    %(Trabajador)s
                                    <Pago Forma="1"
                                          Metodo="%(Metodo)s" />
                                    <FechasPagos>
                                        <FechaPago>%(FechaPago)s</FechaPago>
                                    </FechasPagos>
                                    <Devengados>
                                        %(Devengados)s
                                    </Devengados>
                                    <Deducciones>
                                        %(Deducciones)s
                                    </Deducciones>
                                    <Redondeo>0.00</Redondeo>
                                    <DevengadosTotal>%(DevengadosTotal)s</DevengadosTotal>
                                    <DeduccionesTotal>%(DeduccionesTotal)s</DeduccionesTotal>
                                    <ComprobanteTotal>%(ComprobanteTotal)s</ComprobanteTotal>
                                </%(XmlNodo)s>"""
        if self.credit_note:
            if self.note_type == "1":
                payslip_main_template = """<%(XmlNodo)s xmlns="dian:gov:co:facturaelectronica:%(XmlNodo)s" SchemaLocation="" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#"
                xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
                xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="dian:gov:co:facturaelectronica:NominaIndividualDeAjuste NominaIndividualDeAjusteElectronicaXSD.xsd">
                                    <ext:UBLExtensions>
                                            <ext:UBLExtension>
                                                <ext:ExtensionContent></ext:ExtensionContent>
                                            </ext:UBLExtension>
                                        </ext:UBLExtensions>
                                        %(TipoNota)s
                                        <Reemplazar>
                                            <ReemplazandoPredecesor NumeroPred="%(NumeroPred)s" CUNEPred="%(CUNEPred)s" FechaGenPred="%(FechaGenPred)s"/>
                                            %(Periodo)s
                                            %(NumeroSecuenciaXML)s
                                            %(LugarGeneracionXML)s
                                            %(ProveedorXML)s
                                            <CodigoQR>%(CodigoQR)s</CodigoQR>
                                            %(InformacionGeneral)s
                                            %(Empleador)s
                                            %(Trabajador)s
                                            <Pago Forma="1"
                                            Metodo="%(Metodo)s" />
                                            <FechasPagos>
                                            <FechaPago>%(FechaPago)s</FechaPago>
                                            </FechasPagos>
                                            <Devengados>
                                            %(Devengados)s
                                            </Devengados>
                                            <Deducciones>
                                            %(Deducciones)s
                                            </Deducciones>
                                            <Redondeo>0.00</Redondeo>
                                            <DevengadosTotal>%(DevengadosTotal)s</DevengadosTotal>
                                            <DeduccionesTotal>%(DeduccionesTotal)s</DeduccionesTotal>
                                            <ComprobanteTotal>%(ComprobanteTotal)s</ComprobanteTotal>
                                        </Reemplazar> 
                                    </%(XmlNodo)s>"""
            if self.note_type == "2":
                payslip_main_template = """<%(XmlNodo)s xmlns="dian:gov:co:facturaelectronica:%(XmlNodo)s" SchemaLocation="" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#"
            xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
            xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="dian:gov:co:facturaelectronica:NominaIndividualDeAjuste NominaIndividualDeAjusteElectronicaXSD.xsd">
                                    <ext:UBLExtensions>
                                            <ext:UBLExtension>
                                                <ext:ExtensionContent></ext:ExtensionContent>
                                            </ext:UBLExtension>
                                        </ext:UBLExtensions>
                                        %(TipoNota)s
                                        <Eliminar>
                                            <EliminandoPredecesor NumeroPred="%(NumeroPred)s" CUNEPred="%(CUNEPred)s" FechaGenPred="%(FechaGenPred)s"></EliminandoPredecesor>
                                            %(NumeroSecuenciaXML)s
                                            %(LugarGeneracionXML)s
                                            %(ProveedorXML)s
                                            <CodigoQR>%(CodigoQR)s</CodigoQR>
                                            %(InformacionGeneral)s
                                            <Notas>A</Notas>
                                            %(Empleador)s
                                        </Eliminar> 
                                    </%(XmlNodo)s>"""
        return payslip_main_template

    def payslip_periodo_template(self):
        if self.is_liquid:
            payslip_periodo_template = """<Periodo FechaIngreso="%(FechaIngreso)s"
                                                FechaRetiro="%(FechaRetiro)s"
                                                FechaLiquidacionInicio="%(FechaLiquidacionInicio)s" 
                                                FechaLiquidacionFin="%(FechaLiquidacionFin)s"
                                                TiempoLaborado="%(TiempoLaborado)s"
                                                FechaGen="%(FechaGen)s" />"""
        else:
            payslip_periodo_template = """<Periodo FechaIngreso="%(FechaIngreso)s"
                                                FechaLiquidacionInicio="%(FechaLiquidacionInicio)s" 
                                                FechaLiquidacionFin="%(FechaLiquidacionFin)s"
                                                TiempoLaborado="%(TiempoLaborado)s"
                                                FechaGen="%(FechaGen)s" />"""
        return payslip_periodo_template

    def payslip_numero_secuencia_xml_template(self):
        if self.note_type == "2":
            payslip_numero_secuencia_xml_template = """<NumeroSecuenciaXML Consecutivo="%(Consecutivo)s"
                                                                        Prefijo="ELIM"
                                                                        Numero="%(Numero)s" />"""           
        elif self.note_type == "1":
            payslip_numero_secuencia_xml_template = """<NumeroSecuenciaXML Consecutivo="%(Consecutivo)s"
                                                                        Prefijo="ADJ"
                                                                        Numero="%(Numero)s" />"""
        else:
            payslip_numero_secuencia_xml_template = """<NumeroSecuenciaXML Consecutivo="%(Consecutivo)s"
                                                                        Prefijo="%(Prefijo)s"
                                                                        Numero="%(Numero)s" />"""
        return payslip_numero_secuencia_xml_template

    def payslip_lugar_generacion_xml_template(self):
        payslip_lugar_generacion_xml_template = """<LugarGeneracionXML Pais="%(Pais)s"
                                                                       DepartamentoEstado="%(DepartamentoEstado)s"
                                                                       MunicipioCiudad="%(MunicipioCiudad)s"
                                                                       Idioma="es" />"""
        return payslip_lugar_generacion_xml_template

    def payslip_proveedor_xml_template(self):
        payslip_proveedor_xml_template = """<ProveedorXML NIT="%(NIT)s"
                                                          DV="%(DV)s"
                                                          SoftwareID="%(SoftwareID)s"
                                                          SoftwareSC="%(SoftwareSC)s" />"""
        return payslip_proveedor_xml_template

    def payslip_informacion_general_template(self):
        payslip_informacion_general_template = """<InformacionGeneral Version="%(InfoLiteral)s"
                                                                      Ambiente="%(Ambiente)s"
                                                                      TipoXML="%(TipoXML)s"
                                                                      CUNE="%(CUNE)s"
                                                                      EncripCUNE="CUNE-SHA384"
                                                                      FechaGen="%(FechaGen)s"
                                                                      HoraGen="%(HoraGen)s"
                                                                      PeriodoNomina="%(PeriodoNomina)s"
                                                                      TipoMoneda="%(TipoMoneda)s"
                                                                      TRM="1" />"""
        if self.credit_note:
            if self.note_type == "1":
                payslip_informacion_general_template = """<InformacionGeneral Version="%(InfoLiteral)s"
                                                                        Ambiente="%(Ambiente)s"
                                                                        TipoXML="%(TipoXML)s"
                                                                        CUNE="%(CUNE)s"
                                                                        EncripCUNE="CUNE-SHA384"
                                                                        FechaGen="%(FechaGen)s"
                                                                        HoraGen="%(HoraGen)s"
                                                                        PeriodoNomina="%(PeriodoNomina)s"
                                                                        TipoMoneda="%(TipoMoneda)s"/>"""
            elif self.note_type == "2":
                payslip_informacion_general_template = """<InformacionGeneral Version="%(InfoLiteral)s"
                                                                        Ambiente="%(Ambiente)s"
                                                                        TipoXML="%(TipoXML)s"
                                                                        CUNE="%(CUNE)s"
                                                                        EncripCUNE="CUNE-SHA384"
                                                                        FechaGen="%(FechaGen)s"
                                                                        HoraGen="%(HoraGen)s"/>"""
        return payslip_informacion_general_template

    def payslip_empleador_template(self):
        payslip_empleador_template = """<Empleador RazonSocial="%(RazonSocial)s"
                                                   NIT="%(NIT)s"
                                                   DV="%(DV)s"
                                                   Pais="%(Pais)s"
                                                   DepartamentoEstado="%(DepartamentoEstado)s"
                                                   MunicipioCiudad="%(MunicipioCiudad)s"
                                                   Direccion="%(Direccion)s" />"""
        return payslip_empleador_template

    def payslip_trabajador_template(self):
        payslip_trabajador_template = """<Trabajador TipoTrabajador="%(TipoTrabajador)s"
                                                     SubTipoTrabajador="%(SubTipoTrabajador)s"
                                                     AltoRiesgoPension="%(AltoRiesgoPension)s"
                                                     TipoDocumento="%(TipoDocumento)s"
                                                     NumeroDocumento="%(NumeroDocumento)s"
                                                     PrimerApellido="%(PrimerApellido)s"
                                                     SegundoApellido="%(SegundoApellido)s"
                                                     PrimerNombre="%(PrimerNombre)s"
                                                     OtrosNombres="%(OtrosNombres)s"
                                                     LugarTrabajoPais="%(LugarTrabajoPais)s"
                                                     LugarTrabajoDepartamentoEstado="%(LugarTrabajoDepartamentoEstado)s"
                                                     LugarTrabajoMunicipioCiudad="%(LugarTrabajoMunicipioCiudad)s"
                                                     LugarTrabajoDireccion="%(LugarTrabajoDireccion)s"
                                                     SalarioIntegral="%(SalarioIntegral)s"
                                                     TipoContrato="%(TipoContrato)s"
                                                     Sueldo="%(Sueldo)s"
                                                     CodigoTrabajador="%(CodigoTrabajador)s" />"""
        return payslip_trabajador_template

    def generate_payslip_deducciones(self):
        deducciones = ded_otra = deducciones_otras = ''
        valor_otra = 0
        for line_values in self.line_ids.filtered(lambda l: l.salary_rule_id.rule_type == 'deducciones'):
            if line_values.code == '1008':
                deducciones += '<Salud Porcentaje="4" Deduccion="'+str(line_values.total)+'" />'
            if line_values.code == '1009':
                deducciones += '<FondoPension Porcentaje="4" Deduccion="'+str(line_values.total)+'" />'
            if line_values.code == '1090':
                deducciones += '<Anticipos><Anticipo>%(SAR)s</Anticipo></Anticipos>'%{"SAR": abs(line_values.total)}
            if line_values.code == '1013':
                deducciones_otras = '<OtrasDeducciones>/deduccion</OtrasDeducciones>'
                ded_otra = '<OtraDeduccion>/valor</OtraDeduccion>'
                valor_otra = line_values.total
                deducciones += deducciones_otras.replace('/deduccion', ded_otra.replace('/valor',str(valor_otra)))
            if line_values.code == '1011':
                deducciones += '<FondoSP Porcentaje="1" DeduccionSP="' + str(line_values.total) + '"/>'
            if line_values.code == '1014':
                deducciones += '<RetencionFuente>' + str(line_values.total) + '</RetencionFuente>'
        return deducciones

    def generate_payslip_devengados(self):
        devengados = ''
        dias_disfrute = self.no_dias_disfrute
        numero_liquidacion_prima = self.no_prima_liq
        sueldo = dias = False
        PagoCesan = vacacion = dias_vac_liq = prima = numero_de_dias_prima = bono = markbon = bonoepctv = bonoepctvs = PagoIntereses = markb = 0
        auxilio = viaticos_s = viaticos_ns = vacaciones = bonificacion = bonificaciones = bon = heds = hed = hens = hen = hrns = BonoEPCTVs = BonoEPCTV = BonoEPCTV1 = hrn = \
                heddfs = heddf = hrddfs = hrddf = hendfs = hendf = hrndfs = hrndf = pagotercero = pagoterceros = incapacidades =\
                PagoAlimentacionNS = comision = incapacidad = licencias = licenciasmp = licenciasr = ""
        s = ns = asal = ans = bon_ns = ""

        for wline in self.worked_days_line_ids:
            if wline.code == "WORK100":
                dias = int(wline.number_of_days)

        for line_values in self.line_ids.filtered(lambda l: l.salary_rule_id.rule_type == 'devengos'):
            if line_values.code == '1100' or line_values.code == '1200' or line_values.code == '1300':
                sueldo = line_values.total
            if line_values.code == '1305' or line_values.code == '1205' or line_values.code == '1105':
                auxilio = 'AuxilioTransporte="%s"' % (line_values.total)

            if line_values.code == '1103-1' or line_values.code == '1203-1' or line_values.code == '1303-1':
                viaticos_s = 'ViaticoManuAlojS="%s"' % (line_values.total)
                
            if line_values.code == '1103-2' or line_values.code == '1203-2' or line_values.code == '1303-2':    
                viaticos_ns = 'ViaticoManuAlojNS="%s"' % (line_values.total)

            if line_values.code == '1107-4' or line_values.code == '1207-4' or line_values.code == '1307-4':
                # Horas Extras Diurna normal
                heds = '<HEDs>heds/</HEDs>'
                for overtime in self.overtime_ids:
                    int_hour = int(overtime.num_of_hours)
                    if overtime.num_of_hours > int_hour:
                        int_hour = int_hour + 1
                    if overtime.tipo_de_hora_extra == "hora_extra_diurna_normal":
                        hed += '<HED HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                    'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                    'cantidad': int_hour,
                                                                                                                                                                    'portcentaje': '25.00',
                                                                                                                                                                    'pago': overtime.pago}

            if line_values.code == '1107-2' or line_values.code == '1207-2' or line_values.code == '1307-2':
                # Horas Extras Nocturna normal
                hens = '<HENs>hens/</HENs>'
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

            if line_values.code == '1107-1' or line_values.code == '1207-1' or line_values.code == '1307-1':
                # Recargo Nocturno normal
                hrns = '<HRNs>hrns/</HRNs>'
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

            if line_values.code == '1107-6' or line_values.code == '1207-6' or line_values.code == '1307-6':
                # Horas Extras Diurna festiva
                heddfs = '<HEDDFs>heddfs/</HEDDFs>'
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

            if line_values.code == '1107-3' or line_values.code == '1207-3' or line_values.code == '1307-3':
                # Recargo diurno festivo
                hrddfs = '<HRDDFs>hrddfs/</HRDDFs>'
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

            if line_values.code == '1107-7' or line_values.code == '1207-7' or line_values.code == '1307-7':
                # Horas Extras Diurna festiva
                hendfs = '<HENDFs>hendfs/</HENDFs>'
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

            if line_values.code == '1107-5' or line_values.code == '1207-5' or line_values.code == '1307-5':
                # Recargo Nocturno normal
                hrndfs = '<HRNDFs>hrndfs/</HRNDFs>'
                for overtime in self.overtime_ids:
                    int_hour = int(overtime.num_of_hours)
                    if overtime.num_of_hours > int_hour:
                        int_hour = int_hour + 1
                    if overtime.tipo_de_hora_extra == "recargo_nocturna_f_d":
                        hrn += '<HRNDF HoraInicio="%(hora_inicio)s" HoraFin="%(hora_fin)s" Cantidad="%(cantidad)s" Porcentaje="%(portcentaje)s" Pago="%(pago)s"/>' % {'hora_inicio': overtime.start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                      'hora_fin': overtime.end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                                                                                                                                                                      'cantidad': int_hour,
                                                                                                                                                                      'portcentaje': '110.00',
                                                                                                                                                                      'pago': overtime.pago}
            # vacaciones
            if line_values.code == '1511':
                vacaciones = '<Vacaciones><VacacionesComunes FechaInicio="' + \
                    str(self.fecha_inicio_vac) +'" FechaFin="' + \
                    str(self.fecha_fin_vac) + '" Cantidad="' + str(int(self.numero_dias_vac_dis)) + '" Pago="' + str(line_values.total) + '"/> </Vacaciones>'
            if line_values.code == '1116' or line_values.code == '1216' or line_values.code == '1316':
                if self.vacaciones_compensadas:
                    vacaciones = '<Vacaciones><VacacionesCompensadas Cantidad="' + str(int(self.numero_dias_vac_com)) + '" Pago="' + str(line_values.total) + '"/> </Vacaciones>'
                    _logger.info(vacaciones)
                else:
                    for _vacaciones in self.leaves_ids:
                        if _vacaciones.holiday_status_id.name == 'VACACIONES DE DISFRUTE':
                            cantidad = _vacaciones.duration_display
                            try:
                                cantidad = float(str(cantidad).replace(" day(s)", ""))
                            except:
                                try:
                                    cantidad = float(str(cantidad).replace(" dia(s)", ""))
                                except:
                                    cantidad = float(str(cantidad).replace(" días", ""))
                            vacaciones = '<Vacaciones><VacacionesComunes FechaInicio="' + \
                            str(_vacaciones.date_from.strftime('%Y-%m-%d')) +'" FechaFin="' + \
                            str(_vacaciones.date_to.strftime('%Y-%m-%d')) + '" Cantidad="' + str(int(cantidad)) + '" Pago="' + str(line_values.total) + '"/> </Vacaciones>'
                            _logger.info(vacaciones)
            # prima
            if line_values.code == '1118' or line_values.code == '1218' or line_values.code == '1318':
                print("primas...................##################################################################")
                prima = line_values.total
                for prima_ids in self.contract_id.prima_acumuladas_ids:
                    if prima_ids.dias_pagados != 0 and prima_ids.fecha_desde == self.date_from:
                        numero_de_dias_prima = prima_ids.dias_pagados
            # cesantias
            if line_values.code == '1119' or line_values.code == '1219' or line_values.code == '1319':
                PagoCesan = line_values.total
            # incapacidades
            if line_values.code == '1005':
                incapacidades = '<Incapacidades>incapacidad/</Incapacidades>'
                pago = line_values.total
                for line_eps in self.line_ids.filtered(lambda l: l.salary_rule_id.rule_type == 'devengos'):
                    if line_eps.code == '1006':
                        pago += line_eps.total
                for lines_leaves in self.leaves_ids:
                    if lines_leaves.holiday_status_id.name == "EPS":
                        cantidad = lines_leaves.duration_display
                        try:
                            cantidad = float(str(cantidad).replace(" day(s)", ""))
                        except:
                            try:
                                cantidad = float(str(cantidad).replace(" dia(s)", ""))
                            except:
                                cantidad = float(str(cantidad).replace(" días", ""))
                        fecha_inicio = lines_leaves.date_from
                        fecha_fin = lines_leaves.date_to
                        tipo = lines_leaves.type_leave_disease_dian
                        incapacidad = '<Incapacidad FechaInicio="' + str(fecha_inicio.strftime("%Y-%m-%d")) + '" FechaFin="' + str(fecha_fin.strftime("%Y-%m-%d")) + '" Cantidad="' + str(
                        int(cantidad)) + '" Tipo="' + str(tipo) + '" Pago="' + str(pago) + '" />'
            
            if line_values.code == '1001':
                if licencias == "":
                    licencias = '<Licencias>licenciasmp/</Licencias>'
                elif licencias == '<Licencias>licenciasmp/</Licencias>':
                    pass
                    
                for lines_leaves in self.leaves_ids:
                    if lines_leaves.holiday_status_id.name == "EPS_maternidad":
                        cantidad = lines_leaves.duration_display
                        try:
                            cantidad = float(str(cantidad).replace(" day(s)", ""))
                        except:
                            cantidad = float(str(cantidad).replace(" dia(s)", ""))
                        licenciasmp += '<LicenciaMP FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s" Pago="%(pago)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                        'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                        'cantidad': lines_leaves.duration_display,
                                                                                                                                                        'pago': line_values.total}

            if line_values.code == '1003':
                if licencias == "":
                    licencias = '<Licencias>licenciasmp/</Licencias>'
                elif licencias == '<Licencias>licenciasmp/</Licencias>':
                    pass
                    
                for lines_leaves in self.leaves_ids:
                    if lines_leaves.holiday_status_id.name == "EPS_paternidad":
                        cantidad = lines_leaves.duration_display
                        try:
                            cantidad = float(str(cantidad).replace(" day(s)", ""))
                        except:
                            cantidad = float(str(cantidad).replace(" dia(s)", ""))
                        licenciasmp += '<LicenciaMP FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s" Pago="%(pago)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                        'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                        'cantidad': lines_leaves.duration_display,
                                                                                                                                                        'pago': line_values.total}


            if line_values.code == '1004':
                if licencias == "":
                    licencias = '<Licencias>licenciasmp/</Licencias>'
                elif licencias == '<Licencias>licenciasmp/</Licencias>':
                    pass

                for lines_leaves in self.leaves_ids:
                    if lines_leaves.holiday_status_id.name == "luto":
                        cantidad = lines_leaves.duration_display
                        try:
                            cantidad = float(str(cantidad).replace(" day(s)", ""))
                        except:
                            cantidad = float(str(cantidad).replace(" dia(s)", ""))
                        licenciasmp += '<LicenciaR FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s" Pago="%(pago)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                                        'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                                        'cantidad': lines_leaves.duration_display,
                                                                                                                                                        'pago': line_values.total}

            if line_values.code == '1010':    
                if licencias == "":
                    licencias = '<Licencias>licenciasmp/</Licencias>'
                elif licencias == '<Licencias>licenciasmp/</Licencias>':
                    pass

                for lines_leaves in self.leaves_ids:
                    if lines_leaves.holiday_status_id.name == "AUSENCIA_NO_REMUNERADO":
                        cantidad = lines_leaves.duration_display
                        try:
                            cantidad = float(str(cantidad).replace(" day(s)", ""))
                        except:
                            try:
                                cantidad = float(str(cantidad).replace(" dia(s)", ""))
                            except:
                                cantidad = float(str(cantidad).replace(" días", ""))
                        licenciasmp += '<LicenciaNR FechaInicio="%(hora_inicio)s" FechaFin="%(hora_fin)s" Cantidad="%(cantidad)s"/>' % {'hora_inicio': lines_leaves.date_from.strftime("%Y-%m-%d"),
                                                                                                                                        'hora_fin': lines_leaves.date_to.strftime("%Y-%m-%d"),
                                                                                                                                        'cantidad': cantidad}
                

            if line_values.code == '1120' or line_values.code == '1220' or line_values.code == '1320':
                PagoIntereses = line_values.total
            
            if line_values.code == '1102-1' or line_values.code == '1202-1' or line_values.code == '1302-1' :
                markbon = 1
                bon = 'BonificacionS="%(amount)s"' % {'amount': str(line_values.total)}
                
            if line_values.code == '1102-2' or line_values.code == '1202-2' or line_values.code == '1302-2':
                markbon = 1
                bon_ns = 'BonificacionNS="%(amount)s"' % {'amount': str(line_values.total)}
                
            bonificacion = "<Bonificacion" + " " + bon + " " + bon_ns + " " + "/>"

            if markbon == 1:
                if bonificaciones == "":
                            bonificaciones = '<Bonificaciones>bonificacion/</Bonificaciones>'
                elif bonificaciones == '<Bonificaciones>bonificacion/</Bonificaciones>':
                    pass
            
            ##BonoEPCTVs
            if line_values.code == '1121-1' or line_values.code == '1221-1' or line_values.code == '1321-1' :
                markb = 1
                s = 'PagoS="%(amount)s"' % {'amount': str(line_values.total)}

            if line_values.code == '1121-2' or line_values.code == '1221-2' or line_values.code == '1321-2':
                markb = 1
                ns = 'PagoNS="%(amount)s"' % {'amount': str(line_values.total)}
            
            if line_values.code == '1121-3' or line_values.code == '1221-3' or line_values.code == '1321-3':
                markb = 1
                asal = 'PagoAlimentacionS="%(amount)s"' % {'amount': str(line_values.total)}
            
            if line_values.code == '1121-4' or line_values.code == '1221-4' or line_values.code == '1321-4':
                markb = 1
                ans = 'PagoAlimentacionNS="%(amount)s"' % {'amount': str(line_values.total)}

            BonoEPCTV = "<BonoEPCTV" + " " + s + " " + ns + " " + asal + " " + ans + " " + "/>" 
            
            if markb == 1:
                if BonoEPCTVs == "":
                        BonoEPCTVs = '<BonoEPCTVs>BonoEPCTV/</BonoEPCTVs>'
                elif BonoEPCTVs == '<BonoEPCTVs>BonoEPCTV/</BonoEPCTVs>':
                    pass

            if line_values.code == '1104' or line_values.code == '1204' or line_values.code == '1304':
                comision = '<Comisiones><Comision>%(comision)s</Comision></Comisiones>' % {'comision' : str(line_values.total)}
            if line_values.code == '2112':  
                pagoterceros = '<PagosTerceros>PagoTercero/</PagosTerceros>'
                pagotercero = '<PagoTercero>' + str(line_values.total) + '</PagoTercero>'
            
                    

        devengados += '<Basico DiasTrabajados="' + \
            str(dias)+'" SueldoTrabajado="'+str(sueldo)+'" />'
        if auxilio != "" or viaticos_s != "" or viaticos_ns != "":
            devengados += '<Transporte %(auxilio)s %(ViaticoManuAlojS)s %(ViaticoManuAlojNS)s/>' % {
                "ViaticoManuAlojNS": viaticos_ns, "ViaticoManuAlojS": viaticos_s, 'auxilio': auxilio}

        if heds != "":
            devengados += heds.replace("heds/", hed)
        if hens != "":
            devengados += hens.replace("hens/", hen)
        if hrns != "":
            devengados += hrns.replace("hrns/", hrn)
        if heddfs != "":
            devengados += heddfs.replace("heddfs/", heddf)
        if hrddfs != "":
            devengados += hrddfs.replace("hrddfs/", hrddf)
        if hendfs != "":
            devengados += hendfs.replace("hendfs/", hendf)
        if hrndfs != "":
            devengados += hrndfs.replace("hrndfs/", hrndf)

        if vacaciones != "":
            devengados += vacaciones

        if prima != 0:
            print(prima, numero_de_dias_prima, "prima2#################################333")
            if numero_de_dias_prima != 0:
                devengados += '<Primas Cantidad="' + str(int(numero_de_dias_prima)) + '" ' + 'Pago="' + str(prima) + '" />'
            elif numero_liquidacion_prima != 0:
                devengados += '<Primas Cantidad="' + \
                    str(numero_liquidacion_prima) + '" ' + \
                    'Pago="' + str(prima) + '" />'
        if PagoCesan != 0:
            _logger.info("andres"*20)
            devengados += '<Cesantias Pago="' + \
                str(PagoCesan) + '" ' + 'Porcentaje="12"' + \
                ' PagoIntereses="' + str(PagoIntereses) + '" />'
        # incapacidades
        if incapacidad != "":
            print("gavitest"*100)
            devengados += incapacidades.replace("incapacidad/", incapacidad)
        #Licencias
        if licencias != "":
            devengados += licencias.replace("licenciasmp/", licenciasmp)
        #Bonificacion
        if bonificaciones != "":
            devengados += bonificaciones.replace("bonificacion/", bonificacion)
        #BonoEPCTV
        if BonoEPCTVs != "":
            devengados += BonoEPCTVs.replace("BonoEPCTV/", BonoEPCTV)
        #Comision
        if comision != '':
            devengados += comision
        #Pago Terceros
        if pagoterceros != "":
            devengados += pagoterceros.replace("PagoTercero/", pagotercero)

        return devengados          

    def generate_payslip_trabajador(self, payslip_trabajador_template):
        tipoTrabajador = str(self.employee_id.employee_type)
        subTipoTrabajador = str(self.employee_id.employee_subtype)
        altoRiesgoPension = str(self.employee_id.high_risk and 'true' or 'false')
        tipoDocumento = str(self.employee_id.document_type)
        numeroDocumento = str(self.employee_id.id_document_payroll)
        primerApellido = str(self.employee_id.second_namem)
        segundoApellido = str(self.employee_id.second_namef)
        primerNombre = str(self.employee_id.first_name)
        otrosNombres = str(self.employee_id.first_name)
        lugarTrabajoPais = str(self.employee_id.address_id.country_id.code)
        lugarTrabajoDepartamentoEstado = str(self.employee_id.company.state_id.l10n_co_edi_code)
        lugarTrabajoMunicipioCiudad = str(self.employee_id.address_id.xcity.code)
        lugarTrabajoDireccion = str(self.employee_id.address_id.street)
        salarioIntegral = str(self.it_is_integral and 'true' or 'false')
        tipoContrato = str(self.contract_id.contract_type)
        sueldo = str(self.contract_id.wage)
        codigoTrabajador = str(self.employee_id.id)
        trabajador = payslip_trabajador_template % {
            'TipoTrabajador' : tipoTrabajador,
            'SubTipoTrabajador' : subTipoTrabajador,
            'AltoRiesgoPension' : altoRiesgoPension,
            'TipoDocumento' : tipoDocumento,
            'NumeroDocumento' : numeroDocumento,
            'PrimerApellido' : primerApellido,
            'SegundoApellido' : segundoApellido,
            'PrimerNombre' : primerNombre,
            'OtrosNombres' : otrosNombres,
            'LugarTrabajoPais' : lugarTrabajoPais,
            'LugarTrabajoDepartamentoEstado' : lugarTrabajoDepartamentoEstado,
            'LugarTrabajoMunicipioCiudad' : lugarTrabajoMunicipioCiudad,
            'LugarTrabajoDireccion' : lugarTrabajoDireccion,
            'SalarioIntegral' : salarioIntegral,
            'TipoContrato' : tipoContrato,
            'Sueldo' : sueldo,
            'CodigoTrabajador' : codigoTrabajador,
        }
        return trabajador

    def generate_payslip_empleador(self, payslip_empleador_template):
        RazonSocial = str(self.company_id.name)
        nit = str(self.company_id.partner_id.xidentification)
        dv = str(self.company_id.partner_id.dv)
        pais = str(self.company_id.country_id.code)
        departamentoEstado = str(self.employee_id.company.state_id.l10n_co_edi_code)
        municipioCiudad =  str(self.company_id.partner_id.xcity.code)
        direccion = str(self.company_id.street)
        empleador = payslip_empleador_template % {
            'RazonSocial' : RazonSocial,
            'NIT' : nit,
            'DV' : dv,
            'Pais' : pais,
            'DepartamentoEstado' : departamentoEstado,
            'MunicipioCiudad' : municipioCiudad,
            'Direccion' : direccion,
        }
        return empleador

    def generate_payslip_informacion_general(self, payslip_informacion_general_template):
        ambiente = str(self.company_id.is_test)
        tipoXML = str(self._get_tipo_xml())
        CUNE = str(self._generate_CUNE(self._get_date_gen(), self._get_time_colombia()))
        fechaGen = str(self._get_date_gen())
        horaGen = str(self._get_time_colombia())
        self.update({'cune': CUNE, 'date_send_dian': fechaGen})
        periodoNomina = str(self._get_periodo_nomina())
        TipoMoneda = str(self._get_currency())

        informacion_general = payslip_informacion_general_template % {
            'InfoLiteral': self.credit_note and 'V1.0: Nota de Ajuste de Documento Soporte de Pago de Nómina Electrónica' or 'V1.0: Documento Soporte de Pago de Nómina Electrónica',
            'Ambiente' : ambiente,
            'TipoXML' : tipoXML,
            'CUNE' : CUNE,
            'FechaGen' : fechaGen,
            'HoraGen' : horaGen,
            'PeriodoNomina' : periodoNomina,
            'TipoMoneda' : TipoMoneda
        }

        return informacion_general

    def generate_payslip_proveedor_xml(self, payslip_proveedor_xml_template):
        nit = str(self.company_id.partner_id.xidentification)
        dv = str(self.company_id.partner_id.dv)
        softwareID = str(self.company_id.software_identification_code_payroll)
        softwareSC = str(self._generate_software_security_code())
        proveedor_xml = payslip_proveedor_xml_template % {
            'NIT' : nit,
            'DV' : dv,
            'SoftwareID' : softwareID,
            'SoftwareSC' : softwareSC
        }
        return proveedor_xml

    def generate_payslip_lugar_generacion_xml(self, payslip_lugar_generacion_xml_template):
        pais = str(self.company_id.country_id.code)
        departamentoEstado = str(self.employee_id.company.state_id.l10n_co_edi_code)
        municipioCiudad = str(self.company_id.partner_id.xcity.code)
        lugar_generacion_xml = payslip_lugar_generacion_xml_template % {
            'Pais' : pais,
            'DepartamentoEstado' : departamentoEstado,
            'MunicipioCiudad' : municipioCiudad,
        }
        return lugar_generacion_xml

    def generate_payslip_numero_secuencia_xml(self, payslip_numero_secuencia_xml_template):
        consecutivo = str(self._get_consecutivo())
        prefijo = str(self._get_Prefijo())
        numero = str(self._get_numero())
        if "ELIM" in consecutivo:
            consecutivo = consecutivo.replace("ELIM", "")
        if "ADJ" in consecutivo:
            consecutivo = consecutivo.replace("ADJ", "")
        numero_secuencia = payslip_numero_secuencia_xml_template % {
            'Consecutivo': consecutivo,
            'Prefijo': prefijo,
            'Numero': numero,
        }
        return numero_secuencia

    def generate_payslip_periodo(self, payslip_periodo_template):
        fechaIngreso = str(self.contract_id.date_start)
        fechaLiquidacionInicio = str(self.date_from)
        FechaRetiro = str(self.contract_id.fecha_causada_retiro)
        fechaLiquidacionFin = str(self.date_to)
        tiempoLaborado = str(self._get_work_time())
        fechaGen = str(self._get_date_gen())
        payslip_periodo = payslip_periodo_template % {
            'FechaIngreso' : fechaIngreso,
            'FechaLiquidacionInicio' : fechaLiquidacionInicio,
            'FechaRetiro' : FechaRetiro,
            'FechaLiquidacionFin' : fechaLiquidacionFin,
            'TiempoLaborado' : tiempoLaborado,
            'FechaGen' : fechaGen
        }
        return payslip_periodo

    def generate_payslip_main(self, payslip_main_template):
        periodo = self.generate_payslip_periodo(self.payslip_periodo_template())
        numeroSecuenciaXML = self.generate_payslip_numero_secuencia_xml(self.payslip_numero_secuencia_xml_template())
        lugarGeneracionXML = self.generate_payslip_lugar_generacion_xml(self.payslip_lugar_generacion_xml_template())
        proveedorXML = self.generate_payslip_proveedor_xml(self.payslip_proveedor_xml_template())
        codigoQR = str(self._get_QRCode(self._get_date_gen(), self._get_time_colombia()))
        informacionGeneral = self.generate_payslip_informacion_general(self.payslip_informacion_general_template())
        empleador = self.generate_payslip_empleador(self.payslip_empleador_template())
        trabajador = self.generate_payslip_trabajador(self.payslip_trabajador_template())
        metodo = str(self._get_metodo())
        fechaPago = str(self._get_date_gen())
        devengados = self.generate_payslip_devengados()
        deducciones = self.generate_payslip_deducciones()
        devengadosTotal = self._devengados_second_decimal()
        deduccionesTotal = self._deducciones_second_decimal()
        CUNE = str(self._generate_CUNE(self._get_date_gen(), self._get_time_colombia()))
        comprobanteTotal = self._complements_second_decimal((self._get_devengos() - self._get_deducciones()))
        payslip = payslip_main_template % {
            'NumeroPred': self.payslip_refunded_id.number,
            'CUNEPred': self.payslip_refunded_id.cune,
            'FechaGenPred': self.payslip_refunded_id.date_send_dian,
            'TipoNota': '<TipoNota>%(type_note)s</TipoNota>'%{"type_note": self.note_type},
            'XmlNodo': self.credit_note and 'NominaIndividualDeAjuste' or 'NominaIndividual',
            'Periodo' : periodo,
            'NumeroSecuenciaXML' : numeroSecuenciaXML,
            'LugarGeneracionXML' : lugarGeneracionXML,
            'ProveedorXML' : proveedorXML,
            'CodigoQR' : codigoQR,
            'InformacionGeneral' : informacionGeneral,
            'Empleador' : empleador,
            'Trabajador' : trabajador,
            'Metodo' : metodo,
            'FechaPago' : fechaPago,
            'Devengados' : devengados,
            'Deducciones' : deducciones,
            'DevengadosTotal' : devengadosTotal,
            'DeduccionesTotal' : deduccionesTotal,
            'ComprobanteTotal' : comprobanteTotal,
            'CUNE': CUNE
        }
        return payslip

    def _get_work_time(self):
        diff_date = self.date_to - self.contract_id.date_start
        return diff_date.days

    def _get_time_colombia(self):
        fmt = "%H:%M:%S-05:00"
        now_utc = datetime.now(timezone('UTC'))
        now_time = now_utc.astimezone(timezone('America/Bogota'))
        now_time = now_time.strftime(fmt)
        return now_time

    def _get_date_gen(self):
        #fmt = "%H:%M:%S-05:00"
        fmt = "%Y-%m-%d"
        now_utc = datetime.now(timezone('UTC'))
        #now_time = now_utc.strftime(fmt)
        now_time = now_utc.astimezone(timezone('America/Bogota'))
        now_time = now_time.strftime(fmt)
        return now_time

    def _get_consecutivo(self):
        number = self.number
        seq_id = self.env['ir.sequence'].search([('code', '=', 'nom.salary.slip')])
        if seq_id:
            consecutivo = number.replace(seq_id.prefix, "")
            return consecutivo
        else:
            return ""

    def _get_Prefijo(self):
        seq_id = self.env['ir.sequence'].search([('code', '=', 'nom.salary.slip')])
        if seq_id:
            return seq_id.prefix
        else:
            return ""

    def _get_numero(self):
        number = self.number
        return number

    def _get_tipo_xml(self):
        tipoXML = self.credit_note and '103' or '102'
        return tipoXML

    def _get_periodo_nomina(self):
        periodo_nomina = self.contract_id.payroll_period
        return periodo_nomina

    def _get_currency(self):
        currency = self.company_id.currency_id.name
        return currency
    def _get_metodo(self):
        metodo = self.payment_method
        return metodo

    def _get_deducciones(self):
        total_deducciones = 0
        lines_deducciones = self.line_ids.filtered(lambda l: l.salary_rule_id.rule_type == 'deducciones')
        for line in lines_deducciones:
            total_deducciones += line.total
        return total_deducciones

    def _get_devengos(self):
        total_devengos = 0
        lines_devengos = self.line_ids.filtered(lambda l: l.salary_rule_id.rule_type == 'devengos')
        for line in lines_devengos:
            total_devengos += line.total
        print()
        return total_devengos

    def _generate_zip_content(self, FileNameZIP, data_xml_document, document_repository, filename):
        # Almacena archvio XML

        # Comprime archvio XML
        zip_file = document_repository + '/' + 'z' + FileNameZIP
        zf = zipfile.ZipFile(zip_file, mode="w")
        try:
            zf.writestr(filename, data_xml_document, compress_type=compression)
        finally:
            zf.close()
        

        data_xml = open(zip_file,'rb')
        data_xml = data_xml.read()
        contenido_data_xml_b64 = base64.b64encode(data_xml)
        contenido_data_xml_b64 = contenido_data_xml_b64.decode()
        return contenido_data_xml_b64

    def _generate_software_security_code(self):
        software_identification_code = self.company_id.software_identification_code_payroll
        software_pin = self.company_id.software_pin_payroll
        NroDocumento = self.number
        software_security_code = hashlib.sha384((software_identification_code + software_pin + NroDocumento).encode())
        software_security_code = software_security_code.hexdigest()
        return software_security_code

    def _complements_second_decimal(self, amount):
        amount_dec = round(((amount - int(amount)) * 100.0),2)
        amount_int = int(amount_dec)
        if amount_int % 10 == 0:
            amount = str(amount) + '0'
        else:
            amount = str(amount)
        return amount

    def _devengados_second_decimal(self):
        dev_second_decimal = self._complements_second_decimal(self._get_devengos())
        return dev_second_decimal

    def _deducciones_second_decimal(self):
        ded_second_decimal = self._complements_second_decimal(self._get_deducciones())
        return ded_second_decimal

    def _generate_CUNE(self, gen_date, gen_hours):
        NumNE = self.number
        FecNE = str(gen_date)
        HorNE = str(gen_hours).replace("-05:00","")
        ValDev = self.credit_note and self.note_type == "2" and '0.00' or self._devengados_second_decimal()
        ValDed = self.credit_note and self.note_type == "2" and '0.00' or self._deducciones_second_decimal()
        ValTolNE = self.credit_note and self.note_type == "2" and '0.00' or self._complements_second_decimal((self._get_devengos() - self._get_deducciones()))   
        NitNE = str(self.company_id.partner_id.xidentification)
        DocEmp = self.credit_note and self.note_type == "2" and '0' or str(self.employee_id.id_document_payroll)
        TipoXML = self.credit_note and '103' or '102'
        SoftwarePin = self.company_id.software_pin_payroll
        TipAmb = str(self.company_id.is_test)
        CUNE = NumNE+FecNE+HorNE+"-05:00"+str(ValDev)+str(ValDed)+ValTolNE+NitNE+DocEmp+TipoXML+SoftwarePin+TipAmb
        hash_CUNE = hashlib.sha384(CUNE.encode()).hexdigest()

        return hash_CUNE

    @api.model
    def _get_QRCode(self, gen_date, gen_hours):
        cune = self._generate_CUNE(gen_date, gen_hours)
        qrcode = ''
        if self.company_id.is_test == '2':
            qrcode = 'https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey='+cune
        else:
            qrcode = 'https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey='+cune
        return qrcode

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
                                                <wcf:fileName>%(fileName)s</wcf:fileName>
                                                <wcf:contentFile>%(contentFile)s</wcf:contentFile>
                                                <wcf:testSetId>%(testSetId)s</wcf:testSetId>
                                            </wcf:SendNominaSync>
                                        </soap:Body>
                                    </soap:Envelope>"""
        return template_SendNominaSync



    def generate_datetime_timestamp(self):
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = datetime.now(timezone('UTC'))
        #now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        Created = now_bogota.strftime(fmt)[:-3]+'Z'
        now_bogota = now_bogota + timedelta(minutes=5)
        Expires = now_bogota.strftime(fmt)[:-3]+'Z'
        timestamp = {'Created' : Created,
            'Expires' : Expires
        }
        return timestamp

    def generate_GetStatusZip_send_xml(self, template_getstatus_send_data_xml, identifier, Created, Expires,  Certificate,
        identifierSecurityToken, identifierTo, trackId):
        data_getstatus_send_xml = template_getstatus_send_data_xml % {
                        'identifier' : identifier,
                        'Created' : Created,
                        'Expires' : Expires,
                        'Certificate' : Certificate,
                        'identifierSecurityToken' : identifierSecurityToken,
                        'identifierTo' : identifierTo,
                        'trackId': trackId
                    }
        return data_getstatus_send_xml

    def generate_SendTestSetAsync_send_xml(self, template_getstatus_send_data_xml, identifier, Created, Expires,  Certificate,
        identifierSecurityToken, identifierTo, contentFile, fileName, testSetId):
        data_getstatus_send_xml = template_getstatus_send_data_xml % {
                        'identifier' : identifier,
                        'Created' : Created,
                        'Expires' : Expires,
                        'Certificate' : Certificate,
                        'identifierSecurityToken' : identifierSecurityToken,
                        'identifierTo' : identifierTo,
                        'fileName': fileName,
                        'contentFile' : contentFile,
                        'testSetId': testSetId
                    }
        return data_getstatus_send_xml
    def generate_digestvalue_to(self, elementTo):
        elementTo = etree.tostring(etree.fromstring(elementTo), method="c14n")
        elementTo_sha256 = hashlib.new('sha256', elementTo)
        elementTo_digest = elementTo_sha256.digest()
        elementTo_base = base64.b64encode(elementTo_digest)
        elementTo_base = elementTo_base.decode()
        return elementTo_base

    def generate_SignatureValue_GetStatus(self, document_repository, password, data_xml_SignedInfo_generate, archivo_pem, archivo_certificado):
        data_xml_SignatureValue_c14n = etree.tostring(etree.fromstring(data_xml_SignedInfo_generate), method="c14n")
        archivo_key = document_repository+'/'+archivo_certificado
        try:
            key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)
        except Exception as ex:
            raise ex
        try:
            signature = crypto.sign(key.get_privatekey(), data_xml_SignatureValue_c14n, 'sha256')
        except Exception as ex:
            raise ex
        SignatureValue = base64.b64encode(signature).decode()
        archivo_pem = document_repository+'/'+archivo_pem
        pem = crypto.load_certificate(crypto.FILETYPE_PEM, open(archivo_pem, 'rb').read())
        try:
            validacion = crypto.verify(pem, signature, data_xml_SignatureValue_c14n, 'sha256')
        except:
            raise "Firma para el GestStatus no fué validada exitosamente"
        return SignatureValue


    def _calculate_integral(self):
        for record in self:
            record.it_is_integral = False
            for line in record.line_ids.filtered(lambda l: l.salary_rule_id == record.company_id.rule_id):
                total_in_payslip = line.total
                total_in_company = float(record.company_id.max_salary_integral)
                if total_in_payslip > total_in_company:
                    record.it_is_integral = True


    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()
        if not self.number and self.adj_method == 'adjustment':
            sequence_code = ''
            IPC = self.env['ir.config_parameter'].sudo()
            adj_sequence = int(IPC.get_param('l10n_co_payroll.adj_sequence'))
            sequence = self.env['ir.sequence'].sudo().browse(adj_sequence)
            if sequence:
                sequence_code = sequence.code
                self.number = self.env['ir.sequence'].next_by_code(sequence_code)
        return res

    def _l10n_co_check(self):
        dian_constants = self._get_dian_constants()
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self.generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']
        cer = dian_constants['Certificate']
        headers = {'content-type': 'application/soap+xml'}
        url = URLSEND[self.company_id.is_test]

        if self.company_id.is_test == "2":
            getstatus_xml_send = self.generate_GetStatusZip_send_xml(self.template_GetStatusZip_xml(), identifier, Created, Expires,
                    cer, identifierSecurityToken, identifierTo, self.trackid)
            getstatus_xml_send = self.sign_request_post(getstatus_xml_send)
            response = requests.post(url, data=getstatus_xml_send, headers=headers)
            if response.status_code == 200:
                response_dict = xmltodict.parse(response.content)
                dian_response_dict = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("GetStatusZipResponse", {}).get("GetStatusZipResult", {}).get("b:DianResponse", {})
                if dian_response_dict.get("b:IsValid", "false") == "true":
                    self.l10n_co_dian_status = "valid"
                else:
                    self.message_post(body=dian_response_dict.get("b:StatusDescription", ''))
        else:
            getstatus_xml_send = self.generate_GetStatusZip_send_xml(self.template_GetStatus_xml(), identifier, Created, Expires,
                    cer, identifierSecurityToken, identifierTo, self.trackid)
            getstatus_xml_send = self.sign_request_post(getstatus_xml_send)
            response = requests.post(url, data=getstatus_xml_send, headers=headers)
            if response.status_code == 200:
                response_dict = xmltodict.parse(response.content)
                _logger.info(":"*600)
                _logger.info(response_dict.get("s:Envelope", {}).get("s:Body", {}))
                dian_response_dict = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("GetStatusResponse", {}).get("GetStatusResult", {})
                if dian_response_dict.get("b:IsValid", "false") == "true":
                    self.l10n_co_dian_status = "valid"
                else:
                    msg = dian_response_dict.get("b:StatusDescription", '')
                    for error in dian_response_dict.get("b:ErrorMessage", {}).get("c:string", []):
                        msg += "<p>%s</p>"%(error)
                    self.message_post(body=msg)

    def l10n_co_check_trackid_status(self):
        for record in self:
            if record.l10n_co_dian_status in ('none', 'undefined') and record.trackid:
                record._l10n_co_check()


    def _create_payslip_xml_template(self):
        '''Creates and returns a dictionnary containing 'cfdi' if the cfdi is well created, 'error' otherwise.
        '''
        self.ensure_one()
        qweb = self.env['ir.qweb']
        values = self._l10n_co_create_values()
        # self.env.ref('l10n_co_payroll.payslip_template').render(richard_payslip.ids)
        nomina = qweb._render(PAYSLIP_TEMPLATE, values=values)
        return nomina


    def _l10n_co_create_values(self):
        '''Create the values to fill the CFDI template.
        '''
        self.ensure_one()
        dian_constants = self._get_dian_constants()
        document_constant = self._generate_data_constants_document()
        gen_date = self._get_date_gen()
        gen_hours = self._get_time_colombia()
        values = {
            'record': self,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'fiscal_position': self.company_id.partner_id.property_account_position_id,
            'payment_method': self.payment_method,
            'dian_conts': dian_constants,
            'document_conts': document_constant,
            'gen_date': gen_date,
            'gen_hours': gen_hours
        }
        return values

    @api.model
    def l10n_co_payslip_get_xml_etree(self, cfdi=None):
        '''Get an objectified tree representing the cfdi.
        If the cfdi is not specified, retrieve it from the attachment.

        :param cfdi: The cfdi as string
        :return: An objectified tree
        '''
        #TODO helper which is not of too much help and should be removed
        self.ensure_one()
        if cfdi is None and self.l10n_mx_edi_cfdi:
            cfdi = base64.decodestring(self.l10n_mx_edi_cfdi)
        return fromstring(cfdi) if cfdi else None
         
    def _generate_CertDigestDigestValue(self, digital_certificate, password, document_repository, archivo_certificado):
        archivo_key = (document_repository or '') +'/'+ (archivo_certificado or '')
        key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)
        certificate = hashlib.sha256(crypto.dump_certificate(crypto.FILETYPE_ASN1, key.get_certificate()))
        CertDigestDigestValue = base64.b64encode(certificate.digest())
        CertDigestDigestValue = CertDigestDigestValue.decode()
        return CertDigestDigestValue
    
    def _get_partner_fiscal_responsability_code(self,partner_id):
        rec_partner = self.env['res.partner'].search([('id', '=', partner_id)])
        fiscal_responsability_codes = ''
        if rec_partner:
            for fiscal_responsability in rec_partner.fiscal_responsability_ids:
                fiscal_responsability_codes += ';' + fiscal_responsability.code if fiscal_responsability_codes else fiscal_responsability.code
        return fiscal_responsability_codes
    
    def _replace_character_especial(self, constant):
        if constant:
            constant = constant.replace('&','&amp;')
            constant = constant.replace('<','&lt;')
            constant = constant.replace('>','&gt;')
            constant = constant.replace('"','&quot;')
            constant = constant.replace("'",'&apos;')
        return constant

    def _generate_signature_signingtime(self):
        fmt = "%Y-%m-%dT%H:%M:%S"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        data_xml_SigningTime = now_bogota.strftime(fmt)
        return data_xml_SigningTime
    
    def _generate_signature_politics(self, document_repository):
        # Generar la referencia 2 que consiste en obtener keyvalue desde el documento de politica
        # aplicando el algoritmo SHA1 antes del 20 de septimebre de 2016 y sha256 después  de esa
        # fecha y convirtiendolo a base64. Se  puede utilizar como una constante ya que no variará
        # en años segun lo indica la DIAN.
        #
        data_xml_politics = 'dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y='
        return data_xml_politics
    
    @api.model
    def _generate_signature_ref0(self, data_xml_document, document_repository, password):
        # 1er paso. Generar la referencia 0 que consiste en obtener keyvalue desde todo el xml del
        #           documento electronico aplicando el algoritmo SHA256 y convirtiendolo a base64
        template_basic_data_fe_xml = bytes(data_xml_document, 'utf-8')
        template_basic_data_fe_xml = etree.tostring(etree.fromstring(template_basic_data_fe_xml), method="c14n", exclusive=False,with_comments=False,inclusive_ns_prefixes=None)
        data_xml_sha256 = hashlib.new('sha512', template_basic_data_fe_xml)
        data_xml_digest = data_xml_sha256.digest()
        data_xml_signature_ref_zero = base64.b64encode(data_xml_digest)
        data_xml_signature_ref_zero = data_xml_signature_ref_zero.decode()
        return data_xml_signature_ref_zero

    def _generate_data_constants_document(self):
        data_constants_document = {}
        # Genera identificadores único
        identifier = uuid.uuid4()
        data_constants_document['identifier'] = str(identifier)
        identifierkeyinfo = uuid.uuid4()
        data_constants_document['identifierkeyinfo'] = str(identifierkeyinfo)
        return data_constants_document
    
    @api.model
    def _update_signature(self, template_signature_data_xml, data_xml_signature_ref_zero, data_public_certificate_base,
                                data_xml_keyinfo_base, data_xml_politics,
                                data_xml_SignedProperties_base, data_xml_SigningTime, dian_constants,
                                data_xml_SignatureValue, data_constants_document):
        data_xml_signature = template_signature_data_xml % {'data_xml_signature_ref_zero' : data_xml_signature_ref_zero,
                                        'data_public_certificate_base' : data_public_certificate_base,
                                        'data_xml_keyinfo_base' : data_xml_keyinfo_base,
                                        'data_xml_politics' : data_xml_politics,
                                        'data_xml_SignedProperties_base' : data_xml_SignedProperties_base,
                                        'data_xml_SigningTime' : data_xml_SigningTime,
                                        'CertDigestDigestValue' : dian_constants['CertDigestDigestValue'],
                                        'IssuerName' : dian_constants['IssuerName'],
                                        'SerialNumber' : dian_constants['SerialNumber'],
                                        'SignatureValue' : data_xml_SignatureValue,
                                        'identifier' : data_constants_document['identifier'],
                                        'identifierkeyinfo' : data_constants_document['identifierkeyinfo'],
                                        }
        return data_xml_signature

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
        data_xml_SignedProperties_base = self._generate_signature_ref2(SignedProperties)
        data_xml_signature = data_xml_signature.replace("<ds:DigestValue/>","<ds:DigestValue>%s</ds:DigestValue>" % data_xml_SignedProperties_base, 1)
        #    Actualiza Signeinfo
        Signedinfo = etree.fromstring(data_xml_signature)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = Signedinfo.decode()
        data_xml_SignatureValue = self._generate_SignatureValue(dian_constants['document_repository'], dian_constants['CertificateKey'], Signedinfo, dian_constants['archivo_pem'], dian_constants['archivo_certificado'])
        SignatureValue = etree.fromstring(data_xml_signature)
        SignatureValue = etree.tostring(SignatureValue[1])
        SignatureValue = SignatureValue.decode()
        data_xml_signature = data_xml_signature.replace('-sigvalue"/>','-sigvalue">%s</ds:SignatureValue>' % data_xml_SignatureValue, 1)
        return data_xml_signature

    @api.model
    def _get_dian_constants(self):
        company = self.env.user.company_id
        partner = company.partner_id
        dian_constants = {}
        dian_constants['document_repository'] = company.document_repository                             # Ruta en donde se almacenaran los archivos que utiliza y genera la Facturación Electrónica
        dian_constants['Username'] = company.software_identification_code_payroll                               # Identificador del software en estado en pruebas o activo
        dian_constants['Password'] = hashlib.new('sha256',company.password_environment.encode()).hexdigest()     # Es el resultado de aplicar la función de resumen SHA-256 sobre la contraseña del software en estado en pruebas o activo
        dian_constants['IdentificationCode'] = partner.country_id.code                                  # Identificador de pais
        dian_constants['ProviderID'] = partner.xidentification     if partner.xidentification else ''   # ID Proveedor de software o cliente si es software propio
        dian_constants['SoftwareID'] = company.software_identification_code_payroll                             # ID del software a utilizar          # Código de seguridad del software: (hashlib.new('sha384', str(self.company_id.software_id) + str(self.company_id.software_pin)))
        dian_constants['PINSoftware'] = company.software_pin_payroll
        dian_constants['SeedCode'] = company.seed_code
        dian_constants['UBLVersionID'] = 'UBL 2.1'                                                      # Versión base de UBL usada. Debe marcar UBL 2.0
        dian_constants['ProfileID'] = 'DIAN 2.1'                                                         # Versión del Formato: Indicar versión del documento. Debe usarse "DIAN 1.0"
        dian_constants['CustomizationID'] = company.operation_type
        dian_constants['ProfileExecutionID'] = company.is_test                                          # 1 = produccción 2 = prueba
        dian_constants['SupplierAdditionalAccountID'] = '1' if partner.is_company else '2'              # Persona natural o jurídica (persona natural, jurídica, gran contribuyente, otros)
        dian_constants['SupplierID'] = partner.xidentification if partner.xidentification else ''       # Identificador fiscal: En Colombia, el NIT
        dian_constants['SupplierSchemeID'] = partner.doctype
        dian_constants['SupplierPartyName'] = self._replace_character_especial(partner.name)            # Nombre Comercial
        dian_constants['SupplierDepartment'] = partner.state_id.name                                    # Ciudad o departamento (No requerido)
        dian_constants['SupplierCityCode'] = partner.xcity.code                                         # Municipio tabla 6.4.3 res.country.state.city
        dian_constants['SupplierCityName'] = partner.xcity.name                                         # Municipio tabla 6.4.3 res.country.state.city
        dian_constants['SupplierCountrySubentity'] = partner.state_id.name                              # Ciudad o departamento tabla 6.4.2 res.country.state
        dian_constants['SupplierCountrySubentityCode'] = partner.xcity.code and partner.xcity.code[0:2]                          # Ciudad o departamento tabla 6.4.2 res.country.state
        dian_constants['SupplierCountryCode'] = partner.country_id.code                                 # País tabla 6.4.1 res.country
        dian_constants['SupplierCountryName'] = partner.country_id.name                                 # País tabla 6.4.1 res.country
        dian_constants['SupplierLine'] = partner.street                                                 # Calle
        dian_constants['SupplierRegistrationName'] = company.trade_name                                 # Razón Social: Obligatorio en caso de ser una persona jurídica. Razón social de la empresa
        dian_constants['schemeID'] = partner.dv                                                         # Digito verificador del NIT
        dian_constants['SupplierElectronicMail'] = partner.email
        dian_constants['SupplierTaxLevelCode'] = self._get_partner_fiscal_responsability_code(partner.id)                  # tabla 6.2.4 Régimes fiscal (listname) y 6.2.7 Responsabilidades fiscales
        dian_constants['Certificate'] = company.digital_certificate
        dian_constants['NitSinDV'] = partner.xidentification
        dian_constants['CertificateKey'] = company.certificate_key
        dian_constants['archivo_pem'] = company.pem
        dian_constants['archivo_certificado'] = company.certificate
        dian_constants['CertDigestDigestValue'] = self._generate_CertDigestDigestValue(company.digital_certificate, dian_constants['CertificateKey'], dian_constants['document_repository'], dian_constants['archivo_certificado'])
        dian_constants['IssuerName'] = company.issuer_name                                              # Nombre del proveedor del certificado
        dian_constants['SerialNumber'] = company.serial_number                                          # Serial del certificado
        dian_constants['TaxSchemeID'] = partner.tribute_id.code
        dian_constants['TaxSchemeName'] = partner.tribute_id.name
        dian_constants['Currency'] = company.currency_id.id
        return dian_constants
    
    def _template_signature_data_xml(self):
        template_signature_data_xml = """
                <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-%(identifier)s">
                    <ds:SignedInfo>
                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
                        <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha512"/>
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
                                        <xades:Cert>
                                            <xades:CertDigest>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha512"/>
                                                <ds:DigestValue>%(CertDigestDigestValue)s</ds:DigestValue>
                                            </xades:CertDigest>
                                            <xades:IssuerSerial>
                                                <ds:X509IssuerName>%(IssuerName)s</ds:X509IssuerName>
                                                <ds:X509SerialNumber>%(SerialNumber)s</ds:X509SerialNumber>
                                            </xades:IssuerSerial>
                                        </xades:Cert>
                                    </xades:SigningCertificate>
                                    <xades:SignaturePolicyIdentifier>
                                        <xades:SignaturePolicyId>
                                            <xades:SigPolicyId>
                                                <xades:Identifier>https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf</xades:Identifier>
                                                <xades:Description>Politica de firma para facturas electronicas de la Republica de Colombia</xades:Description>
                                            </xades:SigPolicyId>
                                            <xades:SigPolicyHash>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha512"/>
                                                <ds:DigestValue>%(data_xml_politics)s</ds:DigestValue>
                                            </xades:SigPolicyHash>
                                        </xades:SignaturePolicyId>
                                    </xades:SignaturePolicyIdentifier>
                                    <xades:SignerRole>
                                        <xades:ClaimedRoles>
                                            <xades:ClaimedRole>third party</xades:ClaimedRole>
                                        </xades:ClaimedRoles>
                                    </xades:SignerRole>
                                </xades:SignedSignatureProperties>
                            </xades:SignedProperties>
                            
                        </xades:QualifyingProperties>
                    </ds:Object>
                </ds:Signature>"""
        return template_signature_data_xml
    
    def _generate_signature_ref1(self, data_xml_keyinfo_generate, document_repository, password):
        # Generar la referencia 1 que consiste en obtener keyvalue desde el keyinfo contenido
        # en el documento electrónico aplicando el algoritmo SHA256 y convirtiendolo a base64
        data_xml_keyinfo_generate = etree.tostring(etree.fromstring(data_xml_keyinfo_generate), method="c14n")
        data_xml_keyinfo_sha256 = hashlib.new('sha512', data_xml_keyinfo_generate)
        data_xml_keyinfo_digest = data_xml_keyinfo_sha256.digest()
        data_xml_keyinfo_base = base64.b64encode(data_xml_keyinfo_digest)
        data_xml_keyinfo_base = data_xml_keyinfo_base.decode()
        return data_xml_keyinfo_base
    
    def _generate_signature_ref2(self, data_xml_SignedProperties_generate):
        # Generar la referencia 2, se obtine desde el elemento SignedProperties que se
        # encuentra en la firma aplicando el algoritmo SHA256 y convirtiendolo a base64.
        data_xml_SignedProperties_c14n = etree.tostring(etree.fromstring(data_xml_SignedProperties_generate), method="c14n")
        data_xml_SignedProperties_sha256 = hashlib.new('sha512', data_xml_SignedProperties_c14n)
        data_xml_SignedProperties_digest = data_xml_SignedProperties_sha256.digest()
        data_xml_SignedProperties_base = base64.b64encode(data_xml_SignedProperties_digest)
        data_xml_SignedProperties_base = data_xml_SignedProperties_base.decode()
        return data_xml_SignedProperties_base
    
    def _generate_SignatureValue(self, document_repository, password, data_xml_SignedInfo_generate,
            archivo_pem, archivo_certificado):
        data_xml_SignatureValue_c14n = etree.tostring(etree.fromstring(data_xml_SignedInfo_generate), method="c14n", exclusive=False, with_comments=False)
        archivo_key = document_repository+'/'+archivo_certificado
        try:
            key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        try:
            signature = crypto.sign(key.get_privatekey(), data_xml_SignatureValue_c14n, 'sha512')
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        SignatureValue = base64.b64encode(signature)
        SignatureValue = SignatureValue.decode()
        archivo_pem = document_repository+'/'+archivo_pem
        pem = crypto.load_certificate(crypto.FILETYPE_PEM, open(archivo_pem, 'rb').read())
        try:
            validacion = crypto.verify(pem, signature, data_xml_SignatureValue_c14n, 'sha512')
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
        response = requests.request("POST", "http://apps.kiai.co/api/Mediador/FirmarXmlNomina", data=payload, headers=headers, auth=("900395252", "tufactura.co@softwareestrategico.com"))
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    
    def sign_request_post(self, post_xml_to_sign):
        dian_constants = self._get_dian_constants()
        parser = etree.XMLParser(remove_blank_text=True)
        data_xml_send = etree.tostring(etree.XML(post_xml_to_sign, parser=parser))
        data_xml_send = data_xml_send.decode()
        #   Generar DigestValue Elemento to y lo reemplaza en el xml
        ElementTO = etree.fromstring(data_xml_send)
        ElementTO = etree.tostring(ElementTO[0])
        ElementTO = etree.fromstring(ElementTO)
        ElementTO = etree.tostring(ElementTO[2])
        DigestValueTO = self.generate_digestvalue_to(ElementTO)
        data_xml_send = data_xml_send.replace('<ds:DigestValue/>','<ds:DigestValue>%s</ds:DigestValue>' % DigestValueTO)
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
        SignatureValue = self.generate_SignatureValue_GetStatus(dian_constants['document_repository'], password, Signedinfo, dian_constants['archivo_pem'], dian_constants['archivo_certificado'])
        data_xml_send = data_xml_send.replace('<ds:SignatureValue/>','<ds:SignatureValue>%s</ds:SignatureValue>' % SignatureValue)
        return data_xml_send

    def send_2_validate(self):
        # INCIO VALIDACIONES
        mensaje = ''
        # VERIFICA INFORMACIÓN DE LA COMPAÑIA
        company = self.company_id
        contract = self.contract_id
        employee = self.employee_id
        partner = company.partner_id
        if not company.document_repository:
            mensaje += '- Se debe asociar un repositorio en donde se almacenarán los archivos de Nómina Electrónica.' + '\n'
        if not company.software_identification_code:
            mensaje += '- No se encuentra registrado el código de identificación del software.' + '\n'
        if not company.software_pin_payroll:
            mensaje += '- No se encuentra el PIN del Software.' + '\n'
        if not company.digital_certificate:
            mensaje += '- No se ha registrado el certificado digital.' + '\n'
        if not company.certificate_key:
            mensaje += '- No se ha registrado la clave del certificado.' + '\n'
        if not company.issuer_name:
            mensaje += '- No se ha registrado el proveedor del certificado.' + '\n'
        if not company.serial_number:
            mensaje += '- No se ha registrado el serial del certificado.' + '\n'
        # VERIFICA INFORMACIÓN DE LA COMPAÑIA EN EL APARTADO DE CONTACTO
        if not partner.country_id.code:
            mensaje += '- Su Empresa no tiene registrado el país.' + '\n'
        if not partner.xidentification:
            mensaje += '- Su Empresa no tiene registrado el NIT.' + '\n'
        if not partner.company_type:
            mensaje += '- Su Empresa no está identificada como persona juríduca o persona natural.' + '\n'
        if not partner.doctype:
            mensaje += '- Su Empresa no tiene asociada un Tipo de documento.' + '\n'
        if not partner.state_id:
            mensaje += '- Su Empresa no tiene asociada un Estado/Departamento.' + '\n'
        if not partner.xcity:
            mensaje += '- Su Empresa no tiene asociada un municipio.' + '\n'
        if not partner.street:
            mensaje += '- Su Empresa no tiene asocida una dirección.' + '\n'
        # VERIFICA LA INFORMACIÓN DEL CONTRATO
        if not contract.date_start:
            mensaje += '- El Contrato no tiene una Fecha de inicio.' + '\n'
        if not contract.contract_type:
            mensaje += '- El Contrato no tiene definido el Tipo de Contrato.' + '\n'
        if not contract.payroll_period:
            mensaje += '- El Contrato no tiene definido el Periodo Nómina.' + '\n'
        # VERIFICA LA INFORMACIÓN DEL EMPLEADO
        if not employee.first_name:
            mensaje += '- El Empleado no tiene definido el Nombre.' + '\n'
        if not employee.second_namef:
            mensaje += '- El Contrato no tiene definido el Primer Apellido.' + '\n'
        if not employee.second_namem:
            mensaje += '- El Empleado no tiene definido el Segundo Apellido.' + '\n'
        if not employee.document_type:
            mensaje += '- El Empleado no tiene definido el Tipo de Documento.' + '\n'
        if not employee.id_document_payroll:
            mensaje += '- El Empleado no tiene definido el Número de Documento.' + '\n'
        if not employee.employee_type:
            mensaje += '- El Empleado no tiene definido el Tipo de Empleado.' + '\n'
        if not employee.employee_subtype:
            mensaje += '- El Empleado no tiene definido el Subtipo de Empleado.' + '\n'
        if not employee.address_id:
            mensaje += '- El Empleado no tiene definido la Dirección Laboral.' + '\n'
        #VERIFICA DATOS DE LA NÓMINA
        if not self.payment_method:
            mensaje += '- La Nómina no tiene definido el Método de Pago.' + '\n'
        if not self.contract_id:
            mensaje += '- La Nómina no tiene definido un Contrato.' + '\n'
        if self.is_liquid == True and contract.fecha_causada_retiro == False:
            mensaje += '- Esta Liquidación no tiene definida la Fecha de causación.' + '\n'        
        for data_line in self.line_ids:
            if data_line.salary_rule_id.rule_type == False:
                regla = data_line.name
                mensaje += '- la Regla %s no tienen definido el Tipo de Afectación' % regla + '\n'
        if mensaje:
            raise ValidationError(mensaje)
        #FIN VALIDACIONES
        
        parser = etree.XMLParser(remove_blank_text=True)
        code_doc = self.credit_note and '103' or '102'
        dian_constants = self._get_dian_constants()
        result = self._create_payslip_xml_template()
        result = result.decode('utf-8')
        payslip_template = self.payslip_main_template()
        result = self.generate_payslip_main(payslip_template)
        result = '<?xml version="1.0" encoding="UTF-8"?>' + result
        _logger.info(result)
        result = base64.b64encode(result.encode("utf-8"))
        archivo_key = dian_constants['document_repository'] + '/' + dian_constants['archivo_certificado']
        CerificadoEmpleadorB64 = open(archivo_key, 'rb').read()
        CerificadoEmpleadorB64 = base64.b64encode(CerificadoEmpleadorB64)
        PinCertificadoB64 = base64.b64encode(dian_constants['CertificateKey'].encode("ascii"))
        NitEmpleador = dian_constants['NitSinDV']
        result = self.generate_xmlsigned(code_doc, result, CerificadoEmpleadorB64, PinCertificadoB64, NitEmpleador)
        if result.get("XmlsNominasB64", []) and result.get("XmlsNominasB64", [])[0].get("Firmado", False):
            result = result.get("XmlsNominasB64", []) and result.get("XmlsNominasB64", [])[0].get("XmlB64", "")
        year_digits = fields.Date.today().strftime('%-y')
        filename = ('nie%s%s00000001.xml' % (self.company_id.partner_id.xidentification, year_digits))
        Document = self._generate_zip_content(filename.replace("xml", 'zip'), base64.b64decode(result), dian_constants['document_repository'], filename)
        self.l10n_co_payslip_attch_name = filename
        template_GetStatus_xml = self.company_id.is_test == '1' and self.template_SendNominaSync_xml() or self.template_SendNominaSyncTest_xml()
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self.generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']
        cer = dian_constants['Certificate']
        data_xml_send = self.generate_SendTestSetAsync_send_xml(template_GetStatus_xml, identifier, Created, Expires,
                    cer, identifierSecurityToken, identifierTo, Document, filename, self.company_id.identificador_set_pruebas_payroll)
        msg = ""
        
        data_xml_send = self.sign_request_post(data_xml_send)
        headers = {'content-type': 'application/soap+xml'}
        url = URLSEND[self.company_id.is_test]
        response = requests.post(url, data=data_xml_send, headers=headers)
        
        if response.status_code == 200:
            if self.company_id.is_test == "2":
                response_dict = xmltodict.parse(response.content)
                trackId = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendTestSetAsyncResponse", {}).get("SendTestSetAsyncResult", {}).get("b:ZipKey", '')
                self.trackid = trackId
                getstatus_xml_send = self.generate_GetStatusZip_send_xml(self.template_GetStatusZip_xml(), identifier, Created, Expires,
                        cer, identifierSecurityToken, identifierTo, trackId)
                getstatus_xml_send = self.sign_request_post(getstatus_xml_send)
                response = requests.post(url, data=getstatus_xml_send, headers=headers)
                response_dict = xmltodict.parse(response.content)
                dian_response_dict = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("GetStatusZipResponse", {}).get("GetStatusZipResult", {}).get("b:DianResponse", {})
                if dian_response_dict.get("b:IsValid", "false") == "true":
                    self.l10n_co_dian_status = "valid"
                else:
                    msg = dian_response_dict.get("b:StatusDescription", '')
            else:
                _logger.info("-"*600)
                response_dict = xmltodict.parse(response.content)
                self.trackid = response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:XmlDocumentKey", '')
                if response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:IsValid", "false") == "false":
                    msg += "<p>Se encontraron los siguientes errores:</p>"
                for ms_error in response_dict.get("s:Envelope", {}).get("s:Body", {}).get("SendNominaSyncResponse", {}).get("SendNominaSyncResult", {}).get("b:ErrorMessage", {}).get("c:string", []):
                    msg += "<p>" + ms_error + "</p>"
        else:
            msg = "Ha ocurrido algún problema con el servicio del DIAN, por favor intente enviar nuevamente el documento"
        
        if result:
            attachment_id = self.env['ir.attachment'].create({
                'name': filename,
                'res_id': self.id,
                'res_model': self._name,
                'datas': result,
                # 'datas': filename #self.decode_base64(filename),
                'description': 'Nomina test',
                })
            self.message_post(
                body=msg,
                attachment_ids=[attachment_id.id])


    # def decode_base64(self, data, altchars=b'+/'):
    #     """Decode base64, padding being optional.

    #     :param data: Base64 data as an ASCII byte string
    #     :returns: The decoded byte string.

    #     """
    #     data = re.sub(rb'[^a-zA-Z0-9%s]+' % altchars, b'', data)  # normalize
    #     missing_padding = len(data) % 4
    #     if missing_padding:
    #         data += b'='* (4 - missing_padding)
    #     return base64.b64decode(data, altchars)