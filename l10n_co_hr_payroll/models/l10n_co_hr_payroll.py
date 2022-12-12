# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


import babel
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone

from odoo import api, fields, models, tools, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    eps = fields.Char(
        string='EPS',
        help='Ingrese la EPS'
    )

    caja_compensacion = fields.Char(
        string='Caja de compensación',
        help='Aquí se debe ingresar la caja de compensación'
    )

    fondo_pension = fields.Char(
        string='Fondo de pensiones',
        help='Aquí se debe ingresar la caja de compensación'
    )

    aseguradora_riesgo = fields.Char(
        string='Nombre de aseguradora ARL',
        help='Aquí se debe diligenciar el nombre de la aseguradora'
    )

    clase_riesgo = fields.Selection(
        string='Clase de riesgo',
        selection=[('1', 'Tipo I'),
                   ('2', 'Tipo II'),
                   ('3', 'Tipo III'),
                   ('4', 'Tipo IV'),
                   ('5', 'Tipo V')]
    )

    rodamiento = fields.Monetary(
        string='Rodamiento'
    )

    porcentaje_comision = fields.Float(
        string='Porcentaje de comisión',
        help='Aquí debe ingresar el porcentaje de comisión, que será calculada en base a las ventas que ingresará en nómina.'
    )

    comision_es_prestacional = fields.Boolean(
        string='¿La comisión es prestacional?',
        help='Si la comisión es prestacional, habilite.'
    )

    bono_es_prestacional = fields.Boolean(
        string='¿El bono es prestacional?',
        help='Si el bono es prestacional, habilite.'
    )

    rodamiento_es_prestacional = fields.Boolean(
        string='¿El rodamiento es prestacional?',
        help='Si el rodamiento es prestacional, habilite.'
    )

    tipo_contrato = fields.Selection(
        string='Tipo de contrato',
        selection=[('1', 'Término fijo'),
                   ('2', 'Término Indefinido'),
                   ('3', 'Obra o labor'),
                   ('4', 'Aprendizaje'),
                   ('5', 'Temporal, ocasional o accidental'),]
    )

    retiro = fields.Selection(
        string='Motivo de retiro',
        selection=[('1', 'Renuncia'),
                   ('2', 'Expiración del plazo fijo pactado'),
                   ('3', 'Mutuo consentimiento'),
                   ('4', 'Muerte del trabajador'),
                   ('5', 'Terminación de la obra o labor contratada'),]
    )

    fecha_causada_retiro = fields.Date(string='Fecha de causación')

    EPS_id = fields.Many2one(
        'res.partner',
        string='EPS',
        domain=[('ent_salud', '=', 'eps')],
        )

    pension_id = fields.Many2one(
        'res.partner',
        string='Fondo de Pension',
        domain=[('ent_salud', '=', 'fondo_pen')]
        )
    
    caja_com_id = fields.Many2one(
        'res.partner',
        string='Caja de compensación',
        domain=[('ent_salud', '=', 'caja_comp')]
        )
    arl_id = fields.Many2one(
        'res.partner',
        string='Aseguradora ARL',
        domain=[('ent_salud', '=', 'arl')]
        )

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    spouse_fiscal_status = fields.Selection([
        ('without income', 'Without Income'),
        ('with income', 'With Income')
    ], string='Tax status for spouse', groups="hr.group_hr_user")
    disabled = fields.Boolean(
        string="Disabled", help="If the employee is declared disabled by law", groups="hr.group_hr_user")
    disabled_spouse_bool = fields.Boolean(
        string='Disabled Spouse', help='if recipient spouse is declared disabled by law', groups="hr.group_hr_user")
    disabled_children_bool = fields.Boolean(
        string='Disabled Children', help='if recipient children is/are declared disabled by law', groups="hr.group_hr_user")
    resident_bool = fields.Boolean(
        string='Nonresident', help='if recipient lives in a foreign country', groups="hr.group_hr_user")
    disabled_children_number = fields.Integer(
        'Number of disabled children', groups="hr.group_hr_user")
    dependent_children = fields.Integer(string='Considered number of dependent children', groups="hr.group_hr_user")
    other_dependent_people = fields.Boolean(
        string="Other Dependent People", help="If other people are dependent on the employee", groups="hr.group_hr_user")
    other_senior_dependent = fields.Integer(
        '# seniors (>=65)', help="Number of seniors dependent on the employee, including the disabled ones", groups="hr.group_hr_user")
    other_disabled_senior_dependent = fields.Integer(
        '# disabled seniors (>=65)', groups="hr.group_hr_user")
    other_juniors_dependent = fields.Integer(
        '# people (<65)', help="Number of juniors dependent on the employee, including the disabled ones", groups="hr.group_hr_user")
    other_disabled_juniors_dependent = fields.Integer(
        '# disabled people (<65)', groups="hr.group_hr_user")
    dependent_seniors = fields.Integer(compute='_compute_dependent_people',
                                       string="Considered number of dependent seniors", groups="hr.group_hr_user")
    dependent_juniors = fields.Integer(compute='_compute_dependent_people',
                                       string="Considered number of dependent juniors", groups="hr.group_hr_user")
    spouse_net_revenue = fields.Float(
        string="Spouse Net Revenue", help="Own professional income, other than pensions, annuities or similar income", groups="hr.group_hr_user")
    spouse_other_net_revenue = fields.Float(string="Spouse Other Net Revenue",
                                            help='Own professional income which is exclusively composed of pensions, annuities or similar income', groups="hr.group_hr_user")
    company = fields.Many2one('res.company',
                              default=1,
                              required=True,
                              string = "Valores de compañia")

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = []

        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(
            structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(
            rule_ids, key=lambda x:x[1])]
        inputs = self.env['hr.salary.rule'].browse(
            sorted_rule_ids).mapped('input_ids')

        for contract in contracts:
            """for input in inputs:
                input_data = {
                    'name': input.name,
                    'code': input.code,
                    'contract_id': contract.id,
                }
                res += [input_data]"""
            ventas = {
                'name': 'Comisión',
                'code': 'VENTAS',
                'contract_id': contract.id,
            }
            bono = {
                'name': 'Bonificación salarial',
                'code': 'BONO',
                'contract_id': contract.id,
            }
            bono_ns = {
                'name': 'Bonificación No salarial',
                'code': 'BONO_NS',
                'contract_id': contract.id,
            }
            rodamiento = {
                'name': 'Viaticos Salarial',
                'code': 'ViaticoManuAlojS',
                #'amount': contract.rodamiento,
                'contract_id': contract.id,
            }
            rodamiento_ns = {
                'name': 'Viaticos No Salarial',
                'code': 'ViaticoManuAlojNS',
                'amount': contract.rodamiento,
                'contract_id': contract.id,
            }
            cesantias = {
                'name': 'Cesantias',
                'code': 'cesan',
                #'amount': contract.rodamiento,
                'contract_id': contract.id,
            }
            vacaciones = {
                'name': 'Vacaciones',
                'code': 'vac',
                #'amount': contract.rodamiento,
                'contract_id': contract.id,
            }

            liquid = {
                'name': 'Liquidacion de empleado',
                'code': 'liq',
                #'amount': contract.rodamiento,
                'contract_id': contract.id,
            }

            otros_devengos = {
                'name': 'Otros devengos',
                'code': 'odev',
                #'amount': contract.rodamiento,
                'contract_id': contract.id,
            }

            sal_prom = {
                'name': 'Salario Base',
                'code': 'sal_prom',
                'contract_id': contract.id,
            }

            PagoAlimentacionS = {
                'name': 'PagoAlimentacionS',
                'code': 'PagoAlimentacionS',
                'contract_id': contract.id,
            }

            PagoAlimentacionNS = {
                'name': 'PagoAlimentacionNS',
                'code': 'PagoAlimentacionNS',
                'contract_id': contract.id,
            }

            BonoEPCTVs_Pago_Salarial = {
                'name': 'BonoEPCTVs Pago Salarial',
                'code': 'PagoS',
                'contract_id': contract.id,
            }

            BonoEPCTVs_Pago_NO_Salarial = {
                'name': 'BonoEPCTVs Pago No Salarial',
                'code': 'PagoNS',
                'contract_id': contract.id,
            }

            fsp = {
                'name': 'Fondo de solidaridad pensional (FSP)',
                'code': 'fsp',
                'contract_id': contract.id,
            }

            vac_sig = {
                'name': 'Vacaciones Periodo Siguiente',
                'code': 'vac_sig',
                'contract_id': contract.id,
            }

            vac_ded = {
                'name': 'Deduccion Vacaciones (Otros periodos)',
                'code': 'vac_ded',
                'contract_id': contract.id,
            }

            oded = {
                'name': 'Otras Deducciones',
                'code': 'oded',
                'contract_id': contract.id,
            }

            res.append(ventas)
            res.append(rodamiento)
            res.append(rodamiento_ns)
            res.append(bono)
            res.append(bono_ns)
            res.append(PagoAlimentacionS)
            res.append(PagoAlimentacionNS)
            res.append(BonoEPCTVs_Pago_Salarial)
            res.append(BonoEPCTVs_Pago_NO_Salarial)
            res.append(cesantias)
            res.append(vacaciones)
            res.append(fsp)
            res.append(oded)
            res.append(vac_ded)
            res.append(vac_sig)
            #res.append(liquid)
            #res.append(otros_devengos)
            res.append(sal_prom)

        return res
