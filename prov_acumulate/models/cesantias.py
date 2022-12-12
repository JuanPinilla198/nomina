from itertools import accumulate
from odoo import models, fields
from datetime import datetime, timedelta, time


class Provisioncesantias(models.Model):

    _name = 'hr.contract.provision.cesantias'
    _description = 'provision cesantias'

    fecha_desde = fields.Date()
    fecha_hasta = fields.Date()
    fecha_pago_nomina = fields.Date()
    valor = fields.Float()
    dias = fields.Float()
    id_nom = fields.Char()
    pago = fields.Float()

    hr_contract_id = fields.Many2one(
        'hr.contract',
        string='',
    )


class Provisioncesantias(models.Model):

    _name = 'hr.contract.interes.provision.cesantias'
    _description = 'provision interes cesantias'

    fecha_desde_i = fields.Date()
    fecha_hasta_i = fields.Date()
    fecha_pago_nomina_i = fields.Date()
    valor_i = fields.Float()
    dias_i = fields.Float()
    id_nom_i = fields.Char()
    pago = fields.Float()
    pago_anterior = fields.Float()

    hr_contract_id = fields.Many2one(
        'hr.contract',
        string='',
    )


class HrContract(models.Model):

    _inherit = 'hr.contract'

    total_acumulado_cesantias = fields.Float()
    cesantias_acumuladas_ids = fields.One2many(
        'hr.contract.provision.cesantias', 'hr_contract_id')

    total_intereses_cesantias = fields.Float()
    dias_acumulados = fields.Float()
    pago_cesantias = fields.Float()
    intereses_cesantias_acumuladas_ids = fields.One2many(
        'hr.contract.interes.provision.cesantias', 'hr_contract_id')

    def calculate_cesantias(self, payslip):
        total = 0
        for cesan in self.cesantias_acumuladas_ids:
            if payslip.date_from.strftime("%Y") == cesan.fecha_desde.strftime("%Y"):
                total += cesan.valor
        valor = total
        return valor

    def calculate_int_cesantias(self, payslip):
        total = 0
        for cesan in self.intereses_cesantias_acumuladas_ids:
            if payslip.date_from.strftime("%Y") == cesan.fecha_desde_i.strftime("%Y"):
                total += cesan.valor_i
        valor = total
        return valor

    def prov_int_ces(self, payslip, pcesan):
        variable = 0
        dias = 0
        anterior = 0
        variable_ant = 0
        total_int = 0
        dias_ = 0
        
        for worked_days in payslip.worked_days_line_ids:
            if worked_days.code == "WORK100":
                work_days = worked_days.number_of_days 

        if payslip.date_to.day > 15 and payslip.date_to.month == 12 or payslip.is_liquid:
            if self.cesantias_acumuladas_ids:
                for total_inces in self.intereses_cesantias_acumuladas_ids:
                    total = total_inces.pago
                    intereses = total_inces.pago_anterior
                    anterior_i = total_inces.valor_i
                for x in self.cesantias_acumuladas_ids:
                    anterior += x.valor 
                    dias += x.dias
                    if payslip.date_from != x.fecha_desde  and x.fecha_pago_nomina == False:
                        result = round((((anterior) + pcesan)*0.12*(((dias) + work_days)/360)) - (intereses))
                    else:
                        result = round(anterior_i)
            elif not self.cesantias_acumuladas_ids and payslip.is_liquid:
                result = round((pcesan)*0.12*((work_days)/360))
            else:
                result = round(((pcesan)*0.12*((work_days)/360)) - self.total_intereses_cesantias)        

        elif self.cesantias_acumuladas_ids:
            for i in self.intereses_cesantias_acumuladas_ids:
                if i.fecha_desde_i.strftime("%Y") == payslip.date_from.strftime("%Y"):
                    anterior = i.valor_i
            for x in self.cesantias_acumuladas_ids:
                if payslip.date_from != x.fecha_desde and x.fecha_pago_nomina == False and x.fecha_desde.strftime("%Y") == payslip.date_from.strftime("%Y"):
                    variable = variable + x.valor
                    dias = dias + x.dias
                    result = round(((variable + pcesan)*0.12*((dias + work_days)/360)) - self.total_intereses_cesantias)
                elif x.fecha_desde.strftime("%Y") != payslip.date_from.strftime("%Y"):
                    for i in self.cesantias_acumuladas_ids:
                        if payslip.date_from.strftime("%Y") == i.fecha_desde.strftime("%Y"):
                            variable_ant += i.valor
                            dias_ += i.dias
                    for j in self.intereses_cesantias_acumuladas_ids:
                        if payslip.date_from.strftime("%Y") == j.fecha_desde_i.strftime("%Y"):
                            total_int += j.valor_i
                    result =  round((((variable_ant/2) + pcesan)*0.12*(((dias_/2) + work_days)/360)) - (total_int/2))
                elif payslip.date_from.strftime("%m") == '01' and  payslip.date_from.day == '01':
                    result = round(pcesan*0.12*(work_days/360))
                else:
                    result = round(anterior)
        else:
            print("ENTRA AQUI")
            result = round(((pcesan)*0.12*((work_days)/360)) - self.total_intereses_cesantias) 
                    
        return result

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'


    def previous_months_ces(self, days, start_date, date_from, flag):

        valor = 0
        for data in self.line_ids:
            if data.code == "1111" or data.code == "1211" or data.code == "1311":
                valor = data.total
        total_pay =  days * (valor/30)

        intereses = ((total_pay)*0.12*((days)/360))

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

        self.contract_id.cesantias_acumuladas_ids = [(0, 0, {'dias': days,
                                                             'fecha_desde': start_date_real,
                                                             'fecha_hasta': date_to,
                                                             'valor': total_pay})]
    
        self.contract_id.intereses_cesantias_acumuladas_ids = [(0, 0, {'valor_i': intereses,
                                                                        'dias_i': days,
                                                                        'pago_anterior': intereses,
                                                                        'fecha_desde_i': start_date_real,
                                                                        'fecha_hasta_i': date_to})]
        
    def acumulate_cesantias(self, date_from, date_to):

        if not self.env.context.get('without_compute_sheet'):
            self.compute_sheet()
        mark = days = valor = _pago_cesan = _pago_int_cesan = accum_days = 0
        date_nom_pay = False
        id_nom = self.id
        for pago in self.line_ids:
            if pago.code == "1119" or pago.code == "1219" or pago.code == "1319":
                _pago_cesan = pago.total
            if pago.code == "1120" or pago.code == "1220" or pago.code == "1320":
                _pago_int_cesan = pago.total
        for days_work in self.worked_days_line_ids:
            print("estos son los numero")
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
            if data.code == "1111" or data.code == "1211" or data.code == "1311":
                print("Si entra")
                valor = data.total
            if data.code == "1112" or data.code == "1212" or data.code == "1312":
                print("Si entra")
                valor_incesan = data.total
        for pro_cesa in self.contract_id.cesantias_acumuladas_ids:

            if pro_cesa.fecha_desde == date_from:
                mark = 1
            else:
                mark = 0
        print(mark)
        if mark == 0:
            
            if _pago_cesan != 0:
                date_nom_pay = self.date_to

                self.contract_id.cesantias_acumuladas_ids = [(0, 0, {'valor': valor,
                                                                     'id_nom': id_nom,
                                                                     'dias': days,
                                                                     'pago': _pago_cesan,
                                                                     'fecha_desde': date_from,
                                                                     'fecha_hasta': date_to})]
                self.contract_id.total_acumulado_cesantias += valor - _pago_cesan
            else:
                self.contract_id.cesantias_acumuladas_ids = [(0, 0, {'valor': valor,
                                                                    'id_nom': id_nom,
                                                                    'dias': days,
                                                                    'fecha_desde': date_from,
                                                                    'fecha_hasta': date_to})] 
                self.contract_id.total_acumulado_cesantias += valor - _pago_cesan

            if _pago_cesan != 0:
                total = acumulado = dias = intereses1 = pago_ant = 0

                for accum in self.contract_id.cesantias_acumuladas_ids:
                    if accum.fecha_desde.strftime("%Y") == self.date_from.strftime("%Y"):
                        acumulado += accum.valor
                        dias += accum.dias

                for values in self.contract_id.intereses_cesantias_acumuladas_ids:
                    if values.fecha_desde_i.strftime("%Y") == self.date_from.strftime("%Y"):
                        pago_ant = values.pago_anterior
                        total += values.valor_i
                
                intereses = ((acumulado)*0.12*((dias)/360)) 
                intereses1 = intereses - pago_ant
                print(intereses, intereses1, "INTERESES")

                self.contract_id.intereses_cesantias_acumuladas_ids = [(0, 0, {'valor_i': intereses1,
                                                                               'id_nom_i': id_nom,
                                                                               'dias_i': days,
                                                                               'pago': total + intereses1,
                                                                               'fecha_desde_i': date_from,
                                                                               'fecha_hasta_i': date_to})]

                for i in self.contract_id.intereses_cesantias_acumuladas_ids:
                    pago_t = i.pago

                self.contract_id.pago_cesantias = pago_t
                self.contract_id.dias_acumulados = accum_days - accum_days
                self.contract_id.total_intereses_cesantias = total - pago_t
            
            else:
                intereses = pago_ant = work_days = accum_days = dias = accum = total_acc = dias_ac = mes = pcesa = acumulado_de_cesantias_ = 0
               
                for x in self.line_ids:
                    if x.code == "1111":
                        pcesa = x.total
                                
                for values_int in self.contract_id.intereses_cesantias_acumuladas_ids:
                    if values_int.fecha_desde_i.strftime("%Y") == self.date_from.strftime("%Y"):
                        mes = int(values_int.fecha_desde_i.strftime("%m"))
                    else:
                        mes = 0
                
                dif_mes = int(self.date_from.strftime("%m")) - mes

                if  dif_mes < 1 and dif_mes != 0: 
                    acumulado_de_cesantias1 = dias_acc = 0
                    mes_n = int(self.date_from.strftime("%m")) - 1
                    
                    for next_days in self.worked_days_line_ids:
                        work_d = next_days.number_of_days

                    for ces_acc in self.contract_id.cesantias_acumuladas_ids:
                        accum += ces_acc.valor
                        if mes_n == int(ces_acc.fecha_desde.strftime("%m")) and ces_acc.fecha_desde.strftime("%Y") == self.date_from.strftime("%Y"):
                            acumulado_de_cesantias1 = accum
                    for mes in self.contract_id.intereses_cesantias_acumuladas_ids:
                        dias += mes.dias_i 
                        if mes_n == int(mes.fecha_desde_i.strftime("%m")) and mes.fecha_desde_i.strftime("%Y") == self.date_from.strftime("%Y"):
                            dias_acc = dias                            
                            pago_ant = mes.pago_anterior

                    intereses = ((acumulado_de_cesantias1 + pcesa)*0.12*((dias_acc + work_d)/360)) 
                    intereses1 = intereses - pago_ant
                else:
                    flag = 0
                    for acumulado in self.contract_id.cesantias_acumuladas_ids:
                        if acumulado.fecha_desde.strftime("%Y") == self.date_from.strftime("%Y"):
                            acumulado_de_cesantias_ += acumulado.valor

                    for next_days in self.worked_days_line_ids:
                        work_d = next_days.number_of_days

                    for mes in self.contract_id.intereses_cesantias_acumuladas_ids:
                        mes_ant = int(self.date_from.strftime("%m")) - 1
                        pago_ant = mes.pago_anterior
                        print(pago_ant, "ANTERIOR-------------------------------------------")
                        if (mes_ant == int(mes.fecha_desde_i.strftime("%m")) or mes.fecha_desde_i.strftime("%m") == self.date_from.strftime("%m")) and mes.fecha_desde_i.strftime("%Y") == self.date_from.strftime("%Y"):
                            pago_ant = mes.pago_anterior
                    for values in self.contract_id.cesantias_acumuladas_ids:
                        if self.date_from.strftime("%m") == '01' and self.date_from.day < 15:
                            accum_days = work_d
                        elif values.fecha_desde.strftime("%Y") == self.date_from.strftime("%Y"):
                            accum_days += values.dias

                    intereses =  (acumulado_de_cesantias_*0.12*((accum_days)/360)) 
                    intereses1 = intereses - pago_ant

                self.contract_id.intereses_cesantias_acumuladas_ids = [(0, 0, {'valor_i': intereses1,
                                                                               'id_nom_i': id_nom,
                                                                               'dias_i': days,
                                                                               'pago_anterior': intereses,
                                                                               'fecha_desde_i': date_from,
                                                                               'fecha_hasta_i': date_to})]

                for i in self.contract_id.intereses_cesantias_acumuladas_ids:
                    if i.fecha_desde_i.strftime("%Y") == self.date_from.strftime("%Y"): 
                        total_acc += i.valor_i 
                        dias_ac += i.dias_i
                    
                self.contract_id.dias_acumulados = dias_ac
                self.contract_id.total_intereses_cesantias = total_acc

        if date_nom_pay == self.date_to:
            for data in self.contract_id.cesantias_acumuladas_ids:
                if data.fecha_hasta.year == date_nom_pay.year:
                    if not data.fecha_pago_nomina:
                        data.fecha_pago_nomina = date_nom_pay
                        
            for data in self.contract_id.intereses_cesantias_acumuladas_ids:
                if data.fecha_hasta_i.year == date_nom_pay.year:
                    if not data.fecha_pago_nomina_i:
                        data.fecha_pago_nomina_i = date_nom_pay 

            

    def cancel_cesan(self):
        valor = 0
        valor_i = 0
        dias_ = 0
        ultimo_pago = 0
        for cesan in self.contract_id.cesantias_acumuladas_ids:
            if self.date_to == cesan.fecha_pago_nomina:
                cesan.fecha_pago_nomina = ''
        
        for incesan in self.contract_id.intereses_cesantias_acumuladas_ids:
            if self.date_to == incesan.fecha_pago_nomina_i:
                incesan.fecha_pago_nomina_i = ''

        for pro_cesan in self.contract_id.cesantias_acumuladas_ids:
            if pro_cesan.fecha_desde == self.date_from:
                if pro_cesan.pago != 0:
                    cesa_id = pro_cesan
                    valor_pago = pro_cesan.pago 
                    valor = pro_cesan.valor
                    cesa_id.unlink()
                    self.contract_id.total_acumulado_cesantias += (valor_pago - valor)
                else:
                    cesa_id = pro_cesan
                    valor = pro_cesan.valor
                    cesa_id.unlink()
                    self.contract_id.total_acumulado_cesantias -= valor
        for pro_cesan_int in self.contract_id.intereses_cesantias_acumuladas_ids:
            if pro_cesan_int.fecha_desde_i == self.date_from:
                if pro_cesan_int.pago != 0:
                    cesa_id = pro_cesan_int
                    valor_pago = pro_cesan_int.pago
                    valor_i = pro_cesan_int.valor_i
                    days_i = pro_cesan_int.dias_i
                    cesa_id.unlink()
                    self.contract_id.total_intereses_cesantias += (valor_pago - valor_i)
                else:
                    cesa_id = pro_cesan_int
                    valor_i = pro_cesan_int.valor_i
                    days_i = pro_cesan_int.dias_i
                    cesa_id.unlink()
                    self.contract_id.total_intereses_cesantias -= valor_i
        for x in self.contract_id.intereses_cesantias_acumuladas_ids:
            if x.fecha_desde_i.strftime("%Y") == self.date_from.strftime("%Y"): 
                dias_ += x.dias_i
                ultimo_pago += x.valor_i
            self.contract_id.total_intereses_cesantias = ultimo_pago
            self.contract_id.dias_acumulados = dias_
        
