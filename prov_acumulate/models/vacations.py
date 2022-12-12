# -*- coding: utf-8 -*-

from calendar import c
from faulthandler import disable
from itertools import accumulate
from datetime import datetime, timedelta, time, date
from pytz import timezone
import pandas as pd
import holidays
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProvisionVacaciones(models.Model):

    _name = 'hr.employe.provision.vacaciones'
    _description = 'provision_vacaciones'

    dias = fields.Float()
    dias_disfrutados = fields.Float()
    pago = fields.Float(string="Valor")
    fecha_desde = fields.Date()
    fecha_hasta = fields.Date()
    fecha_pago = fields.Date()
    pago_parcial = fields.Float(string="Valor")
    pago_realizado = fields.Float(string="Pagado")
    hr_contract_id = fields.Many2one(
        'hr.contract',
        string='empleado',
    )


class HrEmployee(models.Model):

    _inherit = 'hr.contract'

    hr_employe_provision_vacaciones_id = fields.Many2one(
        'hr.employe.provision.vacaciones',
        string='provision vacaciones',
    )
    vacaciones_acumuladas_ids = fields.One2many(
        'hr.employe.provision.vacaciones', 'hr_contract_id')
    dias_totales = fields.Float(string="Dias Totales")
    pago_total = fields.Float(string="Valor total acumulado")

    def calculate_vacations_dis(self, payslip):
        base_wage = self.wage
        days = work_days = disf = day = 0
        
        for work_d in payslip.worked_days_line_ids:
            if work_d.code == "WORK100":
                work_days = work_d.number_of_days
                work_day = (work_days*15)/360
        
        
        if payslip.is_liquid:
            if not self.vacaciones_acumuladas_ids:
                vaca_total = round((base_wage/30)*work_day)
            else:
                for vac in self.vacaciones_acumuladas_ids:
                    if vac.fecha_pago == False:
                        disf += vac.dias_disfrutados
                        day = (disf*15)/360
                        vaca_total = round((base_wage/30)*day)
                    elif vac.fecha_pago == payslip.date_to:
                        disf += vac.dias_disfrutados
                        day = (disf*15)/360
                        vaca_total = round((base_wage/30)*day)
        elif payslip.vacaciones_compensadas:
            vaca_total = round((base_wage/30)*payslip.numero_dias_vac_com)
        else:
            for data in payslip.worked_days_line_ids:
                if data.code == "VACACIONES DE DISFRUTE":
                    days_vac_dis = data.number_of_days
                    vaca_total = (base_wage/30)*days_vac_dis
        return vaca_total

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def accumulate_vacations(self, date_from, date_to):
        days = 0
        mark = 0
        flag = 0
        
        datefrom = date_from
        dateto = date_to
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
            if days_work.code == "VACACIONES DE DISFRUTE":
                days += days_work.number_of_days
                flag = days_work.number_of_days
                    
        for pro_vac in self.contract_id.vacaciones_acumuladas_ids:
            if pro_vac.fecha_desde == datefrom:
                mark = 1
            else:
                mark = 0
        
        wage = self.contract_id.wage
        wage1 = wage/30
        pago_parcial = ((days*15)/360)*wage1
        
        if mark == 0:
            self.contract_id.vacaciones_acumuladas_ids = [(0, 0, {'dias': days,
                                                                  'fecha_desde': datefrom,
                                                                  'fecha_hasta': dateto,
                                                                  'pago_parcial': pago_parcial})]
        
        work_days = 0
        total_parcial = 0
        total_paga = 0
        total_pago = 0 
        disfrutados = 0
        for pago in self.contract_id.vacaciones_acumuladas_ids:
            
            total_pago += pago.pago_parcial
            total_paga += pago.pago_realizado
            work_days += pago.dias
            disfrutados += pago.dias_disfrutados

        total_dias = work_days - disfrutados
        days_vac_total = (total_dias*15)/360
        self.contract_id.dias_totales = days_vac_total
        total = total_pago - total_paga
        self.contract_id.pago_total = total
            
    def action_payslip_done(self):
        date_from = self.date_from
        date_to = self.date_to
        month = days = difference = flag = 0

        if not self.contract_id.vacaciones_acumuladas_ids:
            start_date = self.contract_id.date_start
            if date_from != start_date:
                if date_from.year == start_date.year:
                    if start_date.day == 1:
                        month = date_from.month - start_date.month
                        days = month * 30
                    elif start_date != 1:
                        month = date_from.month - start_date.month
                        days = (month * 30) - (start_date.day - 1)
                elif date_from.year != start_date.year:
                    flag = 1
                    month = date_from.month - 1
                    days = month * 30
                difference =  days
                self.previous_months_vac(difference, start_date, date_from, flag)
                self.previous_months_pri(difference, start_date, date_from, flag)
                self.previous_months_ces(difference, start_date, date_from, flag)

        if self.adj_method == 'adjustment' or self.adj_method == 'elimination':    
            for items in self.contract_id.vacaciones_acumuladas_ids:
                x = items.fecha_desde
                if x.strftime("%m") == date_from.strftime("%m"):
                    items.unlink()

        self.acumulate_cesantias(date_from, date_to)
        self.accumulate_vacations(date_from, date_to)
        self.payment_vacations()
        self.acumulate_prima(date_from, date_to)
        super(HrPayslip, self).action_payslip_done()
        
    def previous_months_vac(self, days, start_date, date_from, flag):
        wage = self.contract_id.wage
        number_days_of_vac = (days*15)/360
        total_pay = number_days_of_vac * (wage/30)
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

        self.contract_id.vacaciones_acumuladas_ids = [(0, 0, {'dias': days,
                                                             'fecha_desde': start_date_real,
                                                             'fecha_hasta': date_to,
                                                             'pago_parcial': total_pay})]




    def action_payslip_cancel(self):
        self.cancel_cesan()
        self.cancel_prima()
        if self.move_id:
            self.previous_move_id = self.move_id.id
            self.previous_move_id.ref = self.number
            self.move_id.button_cancel()
        for pro_vac in self.contract_id.vacaciones_acumuladas_ids:
            if pro_vac.fecha_desde == self.date_from:
                vac_id = pro_vac
                self.refound_vacation()
                days_vac_total = (vac_id.dias*15)/360
                self.contract_id.dias_totales -= days_vac_total
                self.contract_id.pago_total = self.contract_id.dias_totales * (self.contract_id.wage/30)
                vac_id.unlink()

        return super(HrPayslip, self).action_payslip_cancel()

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        sundays = holidays_co = horas = inc_sun =0
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(
                fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(
                fields.Date.from_string(date_to), time.max)
            year = int(day_to.year)
            # Febrero
            nb_of_days = 0
            if day_to.month == 2:
                if day_to.day == 28:
                    nb_of_days = 2
                if day_to.day == 29:
                    nb_of_days = 1
            if (day_from.month in (1, 3, 5, 7, 8, 10,
                                   12)) and (day_from.month != day_to.month):
                nb_of_days = -1
            if (day_from.month in (1, 3, 5, 7, 8, 10,
                                   12)) and (day_from.day in (1, 16)) and day_to.day == 31:
                nb_of_days = -1
            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(
                day_from, day_to, calendar=contract.resource_calendar_id)
            for day, hours, leave in day_leave_intervals:
                holiday = leave[:1].holiday_id
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 5,
                    'code': holiday.holiday_status_id.name or 'GLOBAL',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                current_leave_struct['number_of_hours'] += hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_struct['number_of_days'] += hours / work_hours
                if holiday.holiday_status_id.name == "VACACIONES DE DISFRUTE":

                    if self.date_from <= holiday.request_date_from:
                        datefrom = holiday.request_date_from
                    elif self.date_from >= holiday.request_date_from:
                        datefrom = self.date_from
                    if self.date_to >= holiday.request_date_to:
                        dateto = holiday.request_date_to
                    elif self.date_to <= holiday.request_date_to:
                        dateto = self.date_to
                    holidays_co = self._get_public_holidays_colombia(
                        year, datefrom, dateto)
                    sundays = self._get_sundays(datefrom, dateto)
                        
                
            # compute worked days
            work_data = contract.employee_id._get_work_days_data_batch(
                day_from, day_to, calendar=contract.resource_calendar_id)
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data[contract.employee_id.id]['days'] + nb_of_days + sundays + holidays_co,
                'number_of_hours': work_data[contract.employee_id.id]['hours'],
                'contract_id': contract.id,
            }

            for leavs in self.leaves_ids:
                if leavs.holiday_status_id.name == "AUSENCIA_NO_REMUNERADO":
                    if leavs.include_sunday != True:
                        print(leavs.include_sunday, "LEAVES")
                        inc_sun += 1.0
                        horas += 8.0
                
            if sundays != 0:
                for leav in leaves.values():
                    if leav['name'] == "VACACIONES DE DISFRUTE":
                        leav['number_of_days'] = leav['number_of_days'] - sundays
            if inc_sun != 0:
                for leav in leaves.values():
                    if leav['name'] == "AUSENCIA_NO_REMUNERADO":
                        print(inc_sun, "inc_sun")
                        leav['number_of_days'] = leav['number_of_days'] + inc_sun
                        leav['number_of_hours'] = leav['number_of_hours'] + horas
                        attendances['number_of_days'] = attendances['number_of_days'] - inc_sun
                        attendances['number_of_hours'] = attendances['number_of_days'] * 8.0
                    
            if holidays_co != 0:
                for leav in leaves.values():
                    if leav['name'] == "VACACIONES DE DISFRUTE":
                        leav['number_of_days'] = leav['number_of_days'] - \
                            holidays_co
                    
            for leav in leaves.values():
                if leav['name'] == "EPS":
                    if leav['number_of_days'] == 31:
                        leav['number_of_days'] -= 1
                    if attendances['number_of_days'] == -1:
                        attendances['number_of_days'] += 1
            res.append(attendances)
            res.extend(leaves.values())
        return res#super(HrPayslip, self).get_worked_day_lines(contracts, date_from, date_to)

    def _get_sundays(self, date_from, date_to):
        datefrom = date_from
        dateto = date_to
        sundays = 0
        dates_list = [(datefrom + timedelta(days=d)).strftime("%Y-%m-%d")
                      for d in range((dateto - datefrom).days + 1)]
        for dates in dates_list:
            temp = pd.Timestamp(dates).day_name()
            if temp == 'Sunday':
                sundays += 1
        return sundays

    def _get_public_holidays_colombia(self, year, date_from, date_to):
        list_holidays = []
        for i in holidays.CO(years=year).items():
            list_holidays.append(i[0].strftime("%Y-%m-%d"))
        datefrom = date_from
        dateto = date_to
        holiday = 0
        dates_list = [(datefrom + timedelta(days=d)).strftime("%Y-%m-%d")
                      for d in range((dateto - datefrom).days + 1)]
        for dates in dates_list:
            if dates in list_holidays:
                holiday += 1
        return holiday
    
    def payment_vacations(self):
        days_a = days_p = 0
        days_dis = False  
        for x in self.worked_days_line_ids:
            if x.code == "WORK100":
                days_p = x.number_of_days
        days_a = (days_p*15)/360
        if self.vacaciones_compensadas:
            days_dis = self.numero_dias_vac_com
            if days_dis:
                totales = self.contract_id.dias_totales + days_a
                totales -= days_dis
                days_in_year = (days_dis*360)/15
                acu = self.contract_id.vacaciones_acumuladas_ids 
                for data in acu:
                    if data.dias_disfrutados < data.dias and data.dias_disfrutados == 0:
                        if days_in_year > data.dias_disfrutados:
                            if days_in_year >= data.dias:
                                days_in_year -= data.dias
                                data.dias_disfrutados = data.dias
                                data.fecha_pago = self.date_to
                                data.pago_realizado = ((data.dias_disfrutados*data.pago_parcial)/data.dias)
                            elif days_in_year < data.dias and days_in_year != 0:
                                data.dias_disfrutados = days_in_year
                                days_in_year = 0
                                data.fecha_pago = self.date_to
                                data.pago_realizado = ((data.dias_disfrutados*data.pago_parcial)/data.dias)
                                return
                    elif data.dias_disfrutados < data.dias and data.dias_disfrutados > 0:
                        resta = data.dias - data.dias_disfrutados
                        days_in_year -= resta
                        data.dias_disfrutados += resta
                        data.fecha_pago = self.date_to
                        data.pago_realizado = ((data.dias_disfrutados*data.pago_parcial)/data.dias)
                        return
        elif self.is_liquid:
            totales = self.contract_id.dias_totales + days_a
            days_dis = totales
            totales -= days_dis
            days_in_year = (days_dis*360)/15
            acu = self.contract_id.vacaciones_acumuladas_ids 
            for data in acu:
                if data.dias_disfrutados < data.dias and data.dias_disfrutados == 0:
                    if days_in_year > data.dias_disfrutados:
                        if days_in_year >= data.dias:
                            days_in_year -= data.dias
                            data.dias_disfrutados = data.dias
                            data.fecha_pago = self.date_to
                            data.pago_realizado = ((data.dias_disfrutados*data.pago_parcial)/data.dias)
                        elif days_in_year < data.dias and days_in_year != 0:
                            data.dias_disfrutados = days_in_year
                            days_in_year = 0
                            data.fecha_pago = self.date_to
                            data.pago_realizado = ((data.dias_disfrutados*data.pago_parcial)/data.dias)
                            return
                elif data.dias_disfrutados < data.dias and data.dias_disfrutados > 0:
                    resta = data.dias - data.dias_disfrutados
                    days_in_year -= resta
                    data.dias_disfrutados += resta
                    data.fecha_pago = self.date_to
                    data.pago_realizado = ((data.dias_disfrutados*data.pago_parcial)/data.dias)
                    return
            self.contract_id.dias_totales =  0
            self.contract_id.pago_total = 0
        days_dis = False
        for days in self.worked_days_line_ids:
            if days.code == "VACACIONES DE DISFRUTE":
                days_dis = days.number_of_days
        if days_dis:
            totales = self.contract_id.dias_totales + days_a
            totales -= days_dis
            days_in_year = (days_dis*360)/15
            acu = self.contract_id.vacaciones_acumuladas_ids
            for data in acu:
                if data.fecha_desde != self.date_from:
                    if data.dias_disfrutados < data.dias and data.dias_disfrutados == 0:
                        if days_in_year > data.dias_disfrutados:
                            if days_in_year >= data.dias:
                                days_in_year -= data.dias
                                data.dias_disfrutados = data.dias
                                data.fecha_pago = self.date_to
                                data.pago_realizado = ((data.dias_disfrutados*data.pago_parcial)/data.dias)
                            elif days_in_year < data.dias and days_in_year != 0:
                                data.dias_disfrutados = days_in_year
                                days_in_year = 0
                                data.fecha_pago = self.date_to
                                data.pago_realizado = ((data.dias_disfrutados*data.pago_parcial)/data.dias)
                    elif data.dias_disfrutados < data.dias and data.dias_disfrutados > 0:
                        resta = data.dias - data.dias_disfrutados
                        days_in_year -= resta
                        data.dias_disfrutados += resta
                        data.fecha_pago = self.date_to
                        data.pago_realizado = ((data.dias_disfrutados*data.pago_parcial)/data.dias)
        
    vacaciones_compensadas = fields.Boolean()
    numero_dias_vac_com = fields.Float()

    

    @api.onchange('numero_dias_vac_com')
    def _validate_max_vac_days(self):
        days_a = days_p = 0
        for x in self.worked_days_line_ids:
            if x.code == "WORK100":
                days_p = x.number_of_days
        days_a = (days_p*15)/360
        days_dis = self.numero_dias_vac_com 
        if days_dis > (self.contract_id.dias_totales + days_a):
            raise UserError(
                'El numero de dias que seleccionaste para el pago de vacaciones compensadas excede el acumulado, porfavor prueba con menos dias')

    def refound_vacation(self):
        day = days_in_work = 0
        
        for days in self.worked_days_line_ids:
            if days.code == "VACACIONES DE DISFRUTE":
                day = days.number_of_days
                days_in_work = (day*360)/15
            elif self.vacaciones_compensadas == True:
                day = self.numero_dias_vac_com
                days_in_work = (day*360)/15
            elif self.is_liquid:
                for x in self.contract_id.vacaciones_acumuladas_ids:
                    if x.fecha_pago == self.date_to:
                        day += x.dias_disfrutados
                    days_in_work = (day*360)/15
        for pro_vac in reversed(self.contract_id.vacaciones_acumuladas_ids):
            if pro_vac.dias_disfrutados != 0 and pro_vac.fecha_pago == self.date_to:
                if days_in_work > pro_vac.dias_disfrutados:
                    self.contract_id.dias_totales += (
                        (pro_vac.dias_disfrutados*15)/360)
                    days_in_work -= pro_vac.dias_disfrutados
                    pro_vac.dias_disfrutados -= pro_vac.dias_disfrutados
                    pro_vac.pago_realizado = ((pro_vac.dias_disfrutados*pro_vac.pago_parcial)/pro_vac.dias)
                    pro_vac.fecha_pago = ''
                elif days_in_work == 0:
                    return
                elif days_in_work <= pro_vac.dias_disfrutados:
                    self.contract_id.dias_totales += (
                        (days_in_work*15)/360)
                    pro_vac.dias_disfrutados -= days_in_work
                    days_in_work -= days_in_work
                    pro_vac.pago_realizado = ((pro_vac.dias_disfrutados*pro_vac.pago_parcial)/pro_vac.dias)
                    pro_vac.fecha_pago = ''
            
class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    request_date_from = fields.Date('Request Start Date', default=date.today())
    request_date_to = fields.Date('Request End Date', default=date.today())
    field_bol = fields.Boolean(invisible="0", readonly="0" )
    vacation_bool = fields.Boolean(readonly="1" )

    def _include_sunday_by_week(self, employee):

        sunday = self.env['hr.leave'].search([('employee_id.id', '=', employee.id),
                                              ('holiday_status_id', '=', "AUSENCIA_NO_REMUNERADO"),
                                              ('state', '=', "validate")])
        
        lista = []
        for x in sunday:
            lista.append(x.id)
        lines = [(4, line)
                 for line in lista]
        dic = []
        for x in range(0, len(lines)):
            sunday_1 = self.env['hr.leave'].browse(lines[x][1])
            if sunday_1.state == "validate":
                dic.append((0,0,{'empleado': sunday_1.employee_id,
                        'date_to_week': sunday_1.request_date_to.isocalendar()[1],
                        'include_sunday': sunday_1.include_sunday}))
            
        return dic

    @api.depends('date_from', 'date_to', 'employee_id', 'include_sunday')
    def _compute_number_of_days(self):
        res = super(HolidaysRequest, self)._compute_number_of_days()
        employee = self.employee_id
        days = self.number_of_days
        dato = self._include_sunday_by_week(employee)
        holidays_co = sundays = nb_of_days = 0

        for hide in self:
            if hide.holiday_status_id.name == "VACACIONES DE DISFRUTE":
                self.vacation_bool = True
            else: 
                self.vacation_bool = False
        
        for holiday in self:
            if holiday.holiday_status_id.name == "AUSENCIA_NO_REMUNERADO":
                if dato != []:
                    for i in range(0,len(dato)):
                        exist = dato[i][2]
                        if holiday.employee_id == exist['empleado'] and holiday.request_date_to.isocalendar()[1] == exist['date_to_week']:
                            if not exist['include_sunday']:
                                number_days = holiday.request_date_to - holiday.request_date_from
                                try:
                                    number_days = float(str(number_days).replace("0:00:00", "1"))
                                except:
                                    try:
                                        number_days = float(str(number_days).replace(" day, 0:00:00", ""))
                                    except:
                                        number_days = float(str(number_days).replace(" days, 0:00:00", ""))
                                if holiday.request_date_to == holiday.request_date_from:
                                    holiday.number_of_days = int(number_days)
                                else:
                                    holiday.number_of_days = int(number_days + 1)
                                holiday.field_bol = True
                                holiday.include_sunday = True
                                break
                            else:
                                if holiday.include_sunday == False:
                                    holiday.number_of_days = days + 1
                                else:
                                    holiday.number_of_days = days
                        elif holiday.request_date_to.isocalendar()[1] != exist['date_to_week']:
                            holiday.field_bol = False
                            if holiday.include_sunday == False:
                                holiday.number_of_days = days + 1
                            else:
                                holiday.number_of_days = days - 1
                        else:
                            if holiday.include_sunday == False:
                                holiday.number_of_days = days + 1
                            else:
                                holiday.number_of_days = holiday.number_of_days
                else:
                    if holiday.include_sunday == False:
                        holiday.number_of_days = days + 1
                    else:
                        holiday.number_of_days = holiday.number_of_days
            
            if holiday.date_to.month == 2:
                if holiday.date_to.day == 28:
                    nb_of_days = 2
                if holiday.date_to.day == 29:
                    nb_of_days = 1
            if (holiday.date_from.month in (1, 3, 5, 7, 8, 10, 12)) and (holiday.date_from.month != holiday.date_to.month):
                nb_of_days = -1
            if (holiday.date_from.month in (1, 3, 5, 7, 8, 10, 12)) and holiday.date_from.day == 1 and holiday.date_to.day == 31:
                nb_of_days = -1
            year = holiday.date_to.strftime("%Y")
            list_public_holidays = self._get_public_holidays_colombia(
                year=int(year))
            holiday.number_of_days += nb_of_days
            holiday.number_of_days_display = holiday.number_of_days
            if holiday.holiday_status_id.name == "VACACIONES DE DISFRUTE":
                datefrom = holiday.date_from
                dateto = holiday.date_to
                dates_list = [(datefrom + timedelta(days=d)).strftime("%Y-%m-%d")
                              for d in range((dateto - datefrom).days + 1)]
                for dates in dates_list:
                    temp = pd.Timestamp(dates).day_name()
                    if temp == 'Sunday':
                        sundays += 1
                    if str(dates) in list_public_holidays:
                        holidays_co += 1
                holiday.number_of_days -= sundays
                holiday.number_of_days -= holidays_co

            elif holiday.holiday_status_id.name != "AUSENCIA_NO_REMUNERADO" or holiday.holiday_status_id.name != "VACACIONES DE DISFRUTE":   
                if holiday.date_from and holiday.date_to:
                    holiday.number_of_days = holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)['days']
                else:
                    holiday.number_of_days = 0
        return res

    @api.depends('number_of_days')
    def _compute_number_of_days_display(self):
        res = super(HolidaysRequest, self)._compute_number_of_days_display()

        for holiday in self:
            if holiday.holiday_status_id.name == "AUSENCIA_NO_REMUNERADO": 
                holiday.number_of_days_display = holiday.number_of_days
            if holiday.holiday_status_id.name == "VACACIONES NO REMUNERADO": 
                holiday.number_of_days_display = holiday.number_of_days

        return res

    def action_approve(self):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(
                _('Leave request must be confirmed ("To Approve") in order to approve it.'))
        current_employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        self.filtered(lambda hol: hol.validation_type == 'both').write(
            {'state': 'validate1', 'first_approver_id': current_employee.id})
        self.filtered(lambda hol: not hol.validation_type ==
                      'both').action_validate()
        if not self.env.context.get('leave_fast_create'):
            self.activity_update()
        sundays = holidays_co = 0
        for _holiday in self:
            if _holiday.holiday_status_id.name == "VACACIONES DE DISFRUTE":
                year = _holiday.date_to.strftime("%Y")
                list_public_holidays = self._get_public_holidays_colombia(
                    year=int(year))
                datefrom = _holiday.date_from
                dateto = _holiday.date_to
                dates_list = [(datefrom + timedelta(days=d)).strftime("%Y-%m-%d")
                              for d in range((dateto - datefrom).days + 1)]
                for dates in dates_list:
                    temp = pd.Timestamp(dates).day_name()
                    if temp == 'Sunday':
                        sundays += 1
                    if str(dates) in list_public_holidays:
                        holidays_co += 1
                contract = self.env['hr.contract'].search(
                    [('employee_id', '=', _holiday.employee_id.id), ('state', '=', "open")])
                if (_holiday.number_of_days - sundays - holidays_co) > contract.dias_totales:
                    raise UserError(
                        'El numero de dias que seleccionaste excede el acumulado, prueba con menos dias, el acumulado actual es de ' + str(int(contract.dias_totales)) + ' dia(s)')
        return True

    def _get_public_holidays_colombia(self, year):
        list_holidays = []
        for i in holidays.CO(years=year).items():
            list_holidays.append(i[0].strftime("%Y-%m-%d"))
        return list_holidays