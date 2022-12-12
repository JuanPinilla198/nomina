from odoo import models, fields, api, _
from datetime import datetime, timedelta, time


class ProvisionPrima(models.Model):

    _name = 'hr.contract.provision.prima'
    _description = 'provision prima'

    fecha_desde = fields.Date()
    fecha_hasta = fields.Date()
    fecha_pago_nomina = fields.Date()
    valor = fields.Float()
    dias_pagados = fields.Float()
    dias = fields.Float()
    id_nom = fields.Char()
    pagado = fields.Float()

    hr_contract_id = fields.Many2one(
        'hr.contract',
        string='',
    )


class HrContract(models.Model):

    _inherit = 'hr.contract'

    total_acumulado = fields.Float()
    total_de_dias_acumulados_pri = fields.Float()
    prima_acumuladas_ids = fields.One2many(
        'hr.contract.provision.prima', 'hr_contract_id')

    def _calculate_payment_prima(self, date_to, payslip):
        valor = pago1 = pago2 = 0
        year = date_to.year
        month = date_to.month
        for data in self.prima_acumuladas_ids:
            if data.fecha_hasta.year == year:
                if month <= 6:
                    if data.fecha_hasta.month in [1,2,3,4,5,6]:
                        valor += data.valor
                if month == 12 and month > 6:
                    if data.fecha_hasta.month in [7,8,9,10,11,12]:
                        valor += data.valor
            if payslip.is_liquid:
                if data.fecha_pago_nomina == payslip.date_to or (data.fecha_hasta.year == year and data.fecha_pago_nomina == False):
                    pago1 += data.valor
                valor = pago1
                print(pago1,valor, "QUE HAY AQUI")
                

        return valor


class HrPayslip(models.Model):

    _inherit = 'hr.payslip'

    def previous_months_pri(self, days, start_date, date_from,flag):
        
        valor = 0
        for data in self.line_ids:
            if data.code == "1109" or data.code == "1209" or data.code == "1309":
                valor = data.total
        date_to_month = date_from.month - 1
        if (date_to_month in (1, 3, 5, 7, 8, 10, 12)):
            date_to_day = 31
        if (date_to_month in (4, 6, 9, 11)):
            date_to_day = 30
        if date_to_month == 2:
            if not date_from.year % 4:
                if not date_from.year % 100:
                    if not date_from.year % 400:
                        date_to_day = 29
                    else:
                        date_to_day = 28
                else:
                    date_to_day = 29
            else:
                date_to_day = 28
        if date_to_month < 10:
            date_to_month = str('0' + str(date_to_month))
        date_to = str(date_to_day) + str(date_to_month) + str(date_from.year)
        date_to = datetime.strptime(date_to, '%d%m%Y').date()

        if flag == 1:
            start_date_real = "0101" + str(date_from.year)
            start_date_real = datetime.strptime(start_date_real, '%d%m%Y').date()
        else:
            start_date_real = start_date

        if start_date.month <= 6 and date_from.month <= 6:
            total_pay = days * (valor/30)
            self.contract_id.prima_acumuladas_ids = [(0, 0, {'dias': days,
                                                             'fecha_desde': start_date_real,
                                                             'fecha_hasta': date_to,
                                                             'valor': total_pay})]
        elif start_date.month >= 7 and date_from.month <= 12:
            total_pay = days * (valor/30)
            self.contract_id.prima_acumuladas_ids = [(0, 0, {'dias': days,
                                                             'fecha_desde': start_date_real,
                                                             'fecha_hasta': date_to,
                                                             'valor': total_pay})]
        elif start_date.month <= 6 and date_from.month >= 7:

            if start_date.day == 1:
                difference_days = 0
            else:
                difference_days = start_date.day - 1 

            first_half_year_date = '30' + '06' + str(date_from.year)
            first_half_year_date = datetime.strptime(first_half_year_date, '%d%m%Y').date()
            first_half_year_month = 7 - start_date_real.month
            first_half_year_days = (first_half_year_month * 30) - difference_days
            first_half_year_pay = first_half_year_month * valor

            second_half_year_date = '01' + '07' + str(date_from.year)
            second_half_year_date = datetime.strptime(second_half_year_date, '%d%m%Y').date()
            second_half_year_month = date_from.month - 7
            second_half_year_days = second_half_year_month * 30
            second_half_year_pay = second_half_year_month * valor

            self.contract_id.prima_acumuladas_ids = [(0, 0, {'dias': first_half_year_days,
                                                             'dias_pagados': first_half_year_days,
                                                             'fecha_desde': start_date_real,
                                                             'fecha_hasta': first_half_year_date,
                                                             'fecha_pago_nomina': first_half_year_date,
                                                             'valor': first_half_year_pay,
                                                             'pagado':first_half_year_pay})]
            self.contract_id.prima_acumuladas_ids = [(0, 0, {'dias': second_half_year_days,
                                                             'fecha_desde': second_half_year_date,
                                                             'fecha_hasta': date_to,
                                                             'valor': second_half_year_pay})]
        

    def acumulate_prima(self, date_from, date_to):

        mark = days = valor = _pago = dias = 0
        date_nom_pay = False
        id_nom = self.id
        for days_work in self.worked_days_line_ids:
            if days_work.code == "WORK100":
                days += days_work.number_of_days
            if days_work.code == "EPS":
                days += days_work.number_of_days
            if days_work.code == "luto":
                days += days_work.number_of_days
            if days_work.code == "EPS_paternidad":
                days += days_work.number_of_days
            if days_work.code == "EPS_maternidad":
                days += days_work.number_of_days
            if days_work.code == "incapacidad_ARL":
                days += days_work.number_of_days
        for data in self.line_ids:
            if data.code == "1109" or data.code == "1209" or data.code == "1309":
                valor = data.total
            if data.code == "1118" or data.code == "1218" or data.code == "1318":#codigo si existe pago de prima
                date_nom_pay = self.date_to
                _pago = data.total
                _dias = self.contract_id.total_de_dias_acumulados_pri
                print(date_nom_pay, _pago, "PAgooo")
        for pro_pri in self.contract_id.prima_acumuladas_ids:
            if pro_pri.fecha_pago_nomina == False:
                if pro_pri.fecha_desde.strftime("%Y") == self.date_from.strftime("%Y"):
                    dias += pro_pri.dias
            if pro_pri.fecha_desde == date_from:
                mark = 1
            else:
                mark = 0

        if mark == 0:
            num_days = pago_t = 0
            if _pago != 0:
                _dias = days + dias
                print("IF")
                self.contract_id.prima_acumuladas_ids = [(0, 0, {'valor': valor,
                                                             'id_nom': id_nom,
                                                             'dias': days,
                                                             'dias_pagados' : _dias,
                                                             'pagado' : _pago,
                                                             'fecha_desde': date_from,
                                                             'fecha_hasta': date_to})]
                
                for x in self.contract_id.prima_acumuladas_ids:
                    if x.fecha_desde.strftime("%Y") == self.date_from.strftime("%Y"):
                        num_days += x.dias 
                        pago_t += x.valor
                        print(num_days, pago_t,"PAGO TOTAL")
                self.contract_id.total_de_dias_acumulados_pri = num_days - _dias
                self.contract_id.total_acumulado = pago_t - _pago

            else:
                self.contract_id.prima_acumuladas_ids = [(0, 0, {'valor': valor,
                                                                'id_nom': id_nom,
                                                                'dias': days,
                                                                'fecha_desde': date_from,
                                                                'fecha_hasta': date_to})]
                for x in self.contract_id.prima_acumuladas_ids:
                    num_days += x.dias 
                self.contract_id.total_de_dias_acumulados_pri = num_days
            print(_pago)
            self.contract_id.total_acumulado += valor - _pago
        if date_nom_pay == self.date_to:
            for data in self.contract_id.prima_acumuladas_ids:
                if data.fecha_hasta.month in [1, 2, 3, 4, 5, 6] and data.fecha_hasta.year == date_nom_pay.year:
                    if not data.fecha_pago_nomina:
                        data.fecha_pago_nomina = date_nom_pay
                if data.fecha_hasta.month in [7, 8, 9, 10, 11, 12] and data.fecha_hasta.year == date_nom_pay.year:
                    if not data.fecha_pago_nomina:
                        data.fecha_pago_nomina = date_nom_pay

    def cancel_prima(self):
        valor = 0
        for acu_prim in self.contract_id.prima_acumuladas_ids:
            if self.date_to == acu_prim.fecha_pago_nomina:
                acu_prim.fecha_pago_nomina = ''

        for pro_pri in self.contract_id.prima_acumuladas_ids:
            if pro_pri.fecha_desde == self.date_from:
                if pro_pri.pagado != 0:
                    pri_id = pro_pri
                    valor = pro_pri.pagado
                    valor_mes = pro_pri.valor
                    dias_trabajados = pro_pri.dias_pagados   
                    self.contract_id.total_acumulado += (valor - valor_mes)
                    self.contract_id.total_de_dias_acumulados_pri = (dias_trabajados - pro_pri.dias)          
                    pri_id.unlink() 
                else:
                    pri_id = pro_pri
                    valor = pro_pri.valor
                    valor_dias = pro_pri.dias 
                    pri_id.unlink()                
                    self.contract_id.total_acumulado -= valor
                    self.contract_id.total_de_dias_acumulados_pri -= valor_dias