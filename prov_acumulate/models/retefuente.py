from re import sub
from odoo import models, fields
from datetime import date, datetime, timedelta
from math import ceil

class ProvisionPrima(models.Model):

    _name = 'hr.contract.retefuente'
    _description = 'registro de Retencion en Fuente en pagos de nomina'

    fecha_desde = fields.Date()
    fecha_hasta = fields.Date()
    periodo = fields.Char()
    ingreso_laboral = fields.Float()
    ingresos_no_constitutivos = fields.Float()
    total_deducciones = fields.Float()
    rentas_exentas = fields.Float()
    renta_trabajador = fields.Float(string="Renta de Trabajo Exenta (25%)")
    base_retencion  = fields.Float()
    ingreso_uvt = fields.Float()
    valor = fields.Float()

    hr_contract_id = fields.Many2one(
        'hr.contract',
        string='',
    )


class HrContract(models.Model):

    _inherit = 'hr.contract'

    registro_retefuente_ids = fields.One2many(
        'hr.contract.retefuente', 'hr_contract_id')
    
    def roundup_cent(self,amount):
        return int(ceil(amount / 100.0)) * 100

    def get_last_biweek(self, payslip, codes):
        print("biweek"*100)
        date_start = fields.Date.from_string(payslip.date_from)
        end_date = date_start - timedelta(days = 1)
        start_date = date_start.replace(day=1)
        domain = [('date_from', '>=', start_date), 
                  ('date_to', '<=', end_date), 
                  ('employee_id', '=', payslip.employee_id), 
                  ('state','=', "done")
                 ]
        payslip_ids = self.env['hr.payslip'].search(domain)
        print(payslip_ids, start_date, end_date)
        amount = 0
        for slip in payslip_ids:
            print("for")
            for line in slip.line_ids:
                if line.category_id.code in codes:
                    amount += line.amount
        return amount    
class HrPayslip(models.Model):

    _inherit = 'hr.payslip'
        
    def action_payslip_done(self):
        ret_por_apli = -1
        res = super(HrPayslip, self).action_payslip_done()
        aportes_pension = aportes_fsp = aportes_salud = 0
        total_rentas_exc = total_deducciones = deducciones = total_ing_no_cons = wage = aportes_fsp = ing_lab = input = mark = amount = days = deduction = dependen_deduction = other_no_rent = 0
        uvt = self.employee_id.company.salario_uvt
        otros_ingr_no_cons = uvt*41
        date_from = self.date_from
        date_to = self.date_to

        
        #RETENCIÓN RENTAS DE TRABAJO
        for ingresos in self.line_ids:
            if ingresos.code == "1100" or ingresos.code == "1200" or ingresos.code == "1300":
                wage = ingresos.total
            if ingresos.code == "2111":
                input += ingresos.total
        ing_lab = wage + input 

        #INGRESOS NO CONSTITUTIVOS DE RENTA
        for ingresos_no_cons in self.line_ids:
            if ingresos_no_cons.code == "1008":
                aportes_salud = ingresos_no_cons.total
            if ingresos_no_cons.code == "1011":
                aportes_fsp = ingresos_no_cons.total
            if ingresos_no_cons.code == "1009":
                aportes_pension = ingresos_no_cons.total

        if input > otros_ingr_no_cons:
            total_ing_no_cons = float(otros_ingr_no_cons + aportes_fsp + aportes_pension + aportes_salud)
            print(total_ing_no_cons, "IF")
        else:
            total_ing_no_cons = float(input + aportes_fsp + aportes_pension + aportes_salud)
            print(total_ing_no_cons, "ELSE")

        subtotal1 = ing_lab - total_ing_no_cons
        print(subtotal1, total_ing_no_cons, "SUBTOTAL1")

        #DEDUCCIONES
        if self.employee_id.children != "0" or self.employee_id.disabled_children_bool == True or self.employee_id.other_dependent_people == True:
            deducciones = ing_lab * 0.1

        total_deducciones = deducciones
        
        subtotal2 = subtotal1 - deducciones
        print(subtotal2)

        #RENTAS EXCENTAS

        renta_trabajo_excenta_25 = subtotal2 * 0.25
        subtotal4 = subtotal2 - renta_trabajo_excenta_25

        ##########################################
        cifra_control = subtotal1 * 0.40
        maximo_permitido = total_deducciones + total_rentas_exc + renta_trabajo_excenta_25
        maximo_permitido_420 = uvt * 420

        print(maximo_permitido)
        menor = min(cifra_control, maximo_permitido, maximo_permitido_420)
        print(menor)
        base_ingreso_mensual = subtotal1 - menor

        ingreso_uvt = base_ingreso_mensual / uvt
        
        if ingreso_uvt <= 95 and ingreso_uvt > 0:
            ret_por_apli = 0
        if ingreso_uvt <= 150 and ingreso_uvt > 95:
            ret_por_apli = ((round(ingreso_uvt) - 95)*0.19)*uvt
        if ingreso_uvt <= 360 and ingreso_uvt > 150:
            ret_por_apli = (((round(ingreso_uvt) - 150)*0.28)+10)*uvt
        if ingreso_uvt <= 640 and ingreso_uvt > 360:
            ret_por_apli = (((round(ingreso_uvt) - 360)*0.33)+69)*uvt
        if ingreso_uvt <= 945 and ingreso_uvt > 640:
            ret_por_apli = (((round(ingreso_uvt) - 640)*0.35)+162)*uvt
        if ingreso_uvt <= 2300 and ingreso_uvt > 945:
            ret_por_apli = (((round(ingreso_uvt) - 945)*0.37)+267)*uvt
        if ingreso_uvt > 2300:
            ret_por_apli = (((round(ingreso_uvt) - 2300)*0.39)+770)*uvt

        print(ret_por_apli, "RETENCION")

        #REGISTRO EN TABLA
        print(date_from)

        for existente in self.contract_id.registro_retefuente_ids:
            print("FOR")
            if existente.periodo == existente.periodo:
                mark = 1
                print(existente.id, "ID")
            else:
                mark = 0
                print(existente.id, "ID1")

        print(mark, "MARCA")
        if ret_por_apli != 0:
            if mark == 0:
                print("ENTRAR MARCA")
                datetime = date_from.strftime("%B-%Y")
                datetime = datetime.capitalize()
                print(datetime)
                self.contract_id.registro_retefuente_ids = [(0,0,{'periodo': datetime,
                                                                'ingreso_laboral': wage,
                                                                'ingresos_no_constitutivos':total_ing_no_cons,
                                                                'total_deducciones':total_deducciones,
                                                                'rentas_exentas':total_rentas_exc,
                                                                'renta_trabajador':renta_trabajo_excenta_25,
                                                                'base_retencion':round(subtotal4),
                                                                'ingreso_uvt':round(ingreso_uvt),
                                                                'valor':ret_por_apli})]
    

    def action_payslip_cancel(self):
        super(HrPayslip, self).action_payslip_cancel()

        date_from = self.date_from

        for existente in self.contract_id.registro_retefuente_ids:
            if existente.fecha_desde == date_from:
                cancel = existente
                existente.unlink()
        