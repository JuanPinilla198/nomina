# -*- coding: utf-8 -*-

from ast import Not
from odoo import models, fields, api, exceptions, _
import re
import logging
_logger = logging.getLogger(__name__)



class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_type = fields.Selection(
        selection=[
            ('01', 'Dependiente'),
            ('02', 'Servicio domestico'),
            ('04', 'Madre comunitaria'),
            ('12', 'Aprendices del Sena en etapa lectiva'),
            ('18', 'Funcionarios publicos sin tope maximo de ibc'),
	    ('19', 'Aprendices del SENA en etapa productiva'),
            ('21', 'Estudiantes de postgrado en salud'),
	    ('22', 'Profesor de establecimiento particular'),
            ('23', 'Estudiantes aportes solo riesgos laborales'),
            ('30', 'Dependiente entidades o universidades publicas con regimen especial en salud'),
            ('31', 'Cooperados o pre cooperativas de trabajo asociado'),
            ('47', 'Trabajador dependiente de entidad beneficiaria del sistema general del participantes - aportes patronales'),
            ('51', 'Trabajador de tiempo parcial'),
            ('54', 'Pre pensionado de entidad en liquidacion'),
            ('56', 'Pre pensionado con aporte voluntario a salud'),
	    ('58', 'Estudiantes de practicas laborales en el sector publico'),
        ], string="Tipo de Empleado", required=True
        )
    employee_subtype = fields.Selection(
        selection=[
	    ('00','No Aplica'),
	    ('01','Dependiente pensionado por vejez activo'),
        ], string="Subtipo de Empleado", required=True
        )
    high_risk = fields.Boolean(string="Alto riesgo")

    document_type = fields.Selection(
        selection=[
            ('11','Registro civil'),
	    ('12','Tarjeta de identidad'),
	    ('13','Cedula de ciudadania'),
	    ('21','Tarjeta de extranjeria'),
	    ('22','Cedula de extranjeria'),
	    ('31','NIT'),
	    ('41','Pasaporte'),
	    ('42','Documento de identificacion extranjero'),
	    ('47','PEP'),
	    ('50','NIT de otro pais'),
	    ('91','NUIP'),
        ], string="Tipo de Documento", required=True
        )

    id_document_payroll = fields.Char(string="No. Documento", required=True)
    first_name = fields.Char(string="Nombre", required=True)
    second_name = fields.Char(string="Segundo Nombre")
    second_namem = fields.Char(string="Apellido M", required=True)
    second_namef = fields.Char(string="Apellido P", required=True)

    _sql_constraints = [
		('ident_unique',
		 'UNIQUE(document_type,id_document_payroll)',
		 "Identification number must be unique!"),
	]

    @api.onchange('identification_id')
    def _compute_total(self):
        for record in self:
            record.id_document_payroll = self.identification_id
    
    @api.onchange('first_name', 'second_name', 'second_namef', 'second_namem')
    def _capital_letter(self):
        if self.first_name:
            self.first_name = str(self.first_name).capitalize()
        if self.second_name:
            self.second_name = str(self.second_name).capitalize()
        if self.second_namef:
            self.second_namef = str(self.second_namef).capitalize()
        if self.second_namem:
            self.second_namem = str(self.second_namem).capitalize()

    @api.onchange('first_name', 'second_name', 'second_namef', 'second_namem')
    def _onchange_name(self):

        if self.first_name is False:
            self.first_name = ''
        if self.second_name is False:
            self.second_name = ''
        if self.second_namef is False:
            self.second_namef = ''
        if self.second_namem is False:
            self.second_namem = ''
        
        namelist = [
            self.first_name,
            self.second_name,
            self.second_namef,
            self.second_namem
        ]

        formatedlist = []
        for item in namelist:
            if item is not '':
                formatedlist.append(item)
        self.name = ' '.join(formatedlist).title()
    
    @api.model
    def get_document_type(self):
        result=[]
        for item in self.env['hr.employee'].fields_get(self)['document_type']['selection']:
            result.append({'id':item[0], 'name': item[1]})
        return result 

    @api.onchange('id_document_payroll')
    def _chech_ident(self):
        for item in self:
            if item.document_type is not 1:
                msg = _('Error! Number of digits in Identification number must be'
						'between 2 and 12')
                if len(str(item.id_document_payroll)) < 2:
                    raise exceptions.ValidationError(msg)
                elif len(str(item.id_document_payroll)) > 12:
                    raise exceptions.ValidationError(msg)
    
    @api.onchange('id_document_payroll')
    def _chech_ident(self):
        for item in self:
            if item.document_type is not 47:
                msg = _('Error! Number of digits in Identification number must be'
						'between 2 and 12')
                if len(str(item.id_document_payroll)) < 2:
                    raise exceptions.ValidationError(msg)
                elif len(str(item.id_document_payroll)) > 12:
                    raise exceptions.ValidationError(msg)

    @api.onchange('id_document_payroll')
    def _chech_ident_num(self):
        for item in self:
            if item.document_type is not 1:
                if item.id_document_payroll is not False and \
								item.document_type != 21 and \
								item.document_type != 41:
                    if re.match("^[0-9]+$", item.id_document_payroll) is None:
                        msg = _('Error! Identification number can only '
								            'have numbers')
                        raise exceptions.ValidationError(msg)

    @api.constrains('document_type', 'id_document_payroll')
    def _checkDocType(self):
        if self.document_type is not 1:
            if self.document_type is False:
                msg = _('Error! Please choose an identification type')
                raise exceptions.ValidationError(msg)
            elif self.id_document_payroll is False and self.document_type is not 43:
                msg = _('Error! Identification number is mandatory')
                raise exceptions.ValidationError(msg)

    @api.onchange('document_type')
    def onChangeDocumentType(self):
    	self.id_document_payroll = False


