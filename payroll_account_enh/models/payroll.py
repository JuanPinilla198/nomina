# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def _get_partner_id(self, credit_account):
        """
        Get partner_id of slip line to use in account_move_line
        """
        # use partner of salary rule or fallback on employee's address
        register_partner_id = self.salary_rule_id.register_id.partner_id
        partner_id = register_partner_id.id or self.slip_id.employee_id.address_home_id.id
        if credit_account:
            if register_partner_id or self.salary_rule_id.account_credit.internal_type in ('receivable', 'payable'):
                return partner_id
        else:
            if register_partner_id or self.salary_rule_id.account_debit.internal_type in ('receivable', 'payable'):
                return partner_id
        if partner_id:
            return partner_id
        return False

class ResPartner(models.Model):
    _inherit = 'res.partner'

    ent_salud = fields.Selection([('eps', 'EPS'),
								  ('caja_comp','Caja de compensación'),
								  ('fondo_pen','Fondo de pensiones'),
								  ('arl','Aseguradora ARL')])

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    analytic_account_tag_id = fields.Many2one(
        "account.analytic.tag", string='Etiqueta Analítica')

    previous_move_id = fields.Many2one('account.move', string='Cancelled Accounting Entry Reference')

    def action_payslip_cancel(self):
        if self.move_id:
            self.previous_move_id = self.move_id.id
            self.move_id.button_cancel()
        self.write({'state': 'cancel'})

    def action_payslip_done_with_analytic(self):
        # res = super(HrPayslip, self).action_payslip_done()
        print("PAGO CON ANALITICAS")
        for slip in self:
            if not self.env.context.get('without_compute_sheet'):
                slip.compute_sheet()
            if slip.number:
                number = slip.number
            else:
                number = self.env['ir.sequence'].next_by_code('nom.salary.slip')
            slip.write({'state': 'done', 'number': number})
            
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = self.date_to
            currency = slip.company_id.currency_id or slip.journal_id.company_id.currency_id

            name = _('Payslip of %s') % (slip.employee_id.name)
            move_dict = {
                'narration': name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': date,
            }
            partner_id = False
            for line in slip.details_by_salary_rule_category:
                amount = currency.round(
                    slip.credit_note and -line.total or line.total)
                if currency.is_zero(amount):
                    continue
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id

                if debit_account_id:
                    l_partner = line._get_partner_id(credit_account=False)
                    for analytic_account in slip.analytic_account_tag_id.analytic_distribution_ids:
                        amount_new = amount / 100 * analytic_account.percentage
                        amount_debit = amount_new > 0.0 and amount_new or 0.0
                        amount_credit = amount_new < 0.0 and -amount_new or 0.0
                        debit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': l_partner,
                            'account_id': debit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount_debit,
                            'credit': amount_credit,
                            'analytic_account_id': analytic_account.account_id and analytic_account.account_id.id or False,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        if not partner_id and l_partner:
                            partner_id = l_partner
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - \
                            debit_line[2]['credit']

                if credit_account_id:
                    l_partner = line._get_partner_id(credit_account=True)
                    for analytic_account in slip.analytic_account_tag_id.analytic_distribution_ids:
                        amount_new1 = amount / 100 * analytic_account.percentage
                        amount_debit = amount_new1 < 0.0 and -amount_new1 or 0.0
                        amount_credit = amount_new1 > 0.0 and amount_new1 or 0.0
                        credit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': l_partner,
                            'account_id': credit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount_debit,
                            'credit': amount_credit,
                            'analytic_account_id': analytic_account.account_id and analytic_account.account_id.id or False,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        if not partner_id and l_partner:
                            partner_id = l_partner
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - \
                            credit_line[2]['debit']

            if currency.compare_amounts(credit_sum, debit_sum) == -1:
                # acc_id = slip.journal_id.default_credit_account_id.id
                acc_id = slip.journal_id.payment_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                        slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': partner_id,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': currency.round(debit_sum - credit_sum),
                })
                line_ids.append(adjust_credit)

            elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                # acc_id = slip.journal_id.default_debit_account_id.id
                acc_id = slip.journal_id.payment_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                        slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': partner_id,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': currency.round(credit_sum - debit_sum),
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            if slip.previous_move_id:
                slip.previous_move_id.line_ids = False
                slip.previous_move_id.line_ids = line_ids
                move = slip.previous_move_id
            else:
                move = self.env['account.move'].create(move_dict)
            slip.write({'move_id': move.id, 'date': date, 'previous_move_id': False})
            move.post()

            journal = self.env['account.move'].browse(move.id)
            caja_de_compensación = salud_empleado = salud_empresa = arl = pension_empleado = pension_empresa = ''
            for item in self.line_ids:
                if item.code == '1108' or item.code == '1208' or item.code == '1308':
                    caja_de_compensación = item.salary_rule_id.account_credit.code
                if item.code == '1008':
                    salud_empleado = item.salary_rule_id.account_credit.code
                if item.code == '1113' or item.code == '1213' or item.code == '1313':
                    salud_empresa = item.salary_rule_id.account_credit.code
                if item.code == '1110' or item.code == '1210' or item.code == '1310':
                    arl = item.salary_rule_id.account_credit.code
                if item.code == '1009':
                    pension_empleado = item.salary_rule_id.account_credit.code
                if item.code == '1115' or item.code == '1215' or item.code == '1315':
                    pension_empresa = item.salary_rule_id.account_credit.code
                
            for items in journal.line_ids:
                if items.account_id.code == caja_de_compensación:
                    items.partner_id = self.contract_id.caja_com_id
                if items.account_id.code == salud_empleado:
                    items.partner_id = self.contract_id.EPS_id
                if items.account_id.code == salud_empresa:
                    items.partner_id = self.contract_id.EPS_id
                if items.account_id.code == arl:
                    items.partner_id = self.contract_id.arl_id
                if items.account_id.code == pension_empleado:
                    items.partner_id = self.contract_id.pension_id
                if items.account_id.code == pension_empresa:
                    items.partner_id = self.contract_id.pension_id

            journal.date = self.date_to
            journal.ref = self.number
            
        # return res

    def action_payslip_done_without_analytic(self):
        # res = super(HrPayslip, self).action_payslip_done()
        print("PAGO SIN ANALITICAS")

        for slip in self:
            if not self.env.context.get('without_compute_sheet'):
                slip.compute_sheet()
            if slip.number:
                number = slip.number
            else:
                number = self.env['ir.sequence'].next_by_code('nom.salary.slip')
            slip.write({'state': 'done', 'number': number})

            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = self.date_to
            currency = slip.company_id.currency_id or slip.journal_id.company_id.currency_id

            name = _('Payslip of %s') % (slip.employee_id.name)
            move_dict = {
                'narration': name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': date,
            }
            partner_id = False
            for line in slip.details_by_salary_rule_category:
                amount = currency.round(
                    slip.credit_note and -line.total or line.total)
                if currency.is_zero(amount):
                    continue
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id

                if debit_account_id:
                    l_partner = line._get_partner_id(credit_account=False)
                    debit_line = (0, 0, {
                        'name': line.name,
                        'partner_id': l_partner,
                        'account_id': debit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount > 0.0 and amount or 0.0,
                        'credit': amount < 0.0 and -amount or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    if not partner_id and l_partner:
                        partner_id = l_partner
                    line_ids.append(debit_line)
                    debit_sum += debit_line[2]['debit'] - \
                        debit_line[2]['credit']

                if credit_account_id:
                    l_partner = line._get_partner_id(credit_account=True)
                    credit_line = (0, 0, {
                        'name': line.name,
                        'partner_id': l_partner,
                        'account_id': credit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount < 0.0 and -amount or 0.0,
                        'credit': amount > 0.0 and amount or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    if not partner_id and l_partner:
                        partner_id = l_partner
                    line_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - \
                        credit_line[2]['debit']

            if currency.compare_amounts(credit_sum, debit_sum) == -1:
                acc_id = slip.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                        slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': partner_id,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': currency.round(debit_sum - credit_sum),
                })
                line_ids.append(adjust_credit)

            elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                acc_id = slip.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                        slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': partner_id,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': currency.round(credit_sum - debit_sum),
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            if slip.previous_move_id:
                slip.previous_move_id.line_ids = False
                slip.previous_move_id.line_ids = line_ids
                move = slip.previous_move_id
            else:
                move = self.env['account.move'].create(move_dict)
            slip.write({'move_id': move.id, 'date': date, 'previous_move_id': False})
            move.post()

            journal = self.env['account.move'].browse(move.id)
            caja_de_compensación = salud_empleado = salud_empresa = arl = pension_empleado = pension_empresa = ''
            for item in self.line_ids:
                if item.code == '1108' or item.code == '1208' or item.code == '1308':
                    caja_de_compensación = item.salary_rule_id.account_credit.code
                if item.code == '1008':
                    salud_empleado = item.salary_rule_id.account_credit.code
                if item.code == '1113' or item.code == '1213' or item.code == '1313':
                    salud_empresa = item.salary_rule_id.account_credit.code
                if item.code == '1110' or item.code == '1210' or item.code == '1310':
                    arl = item.salary_rule_id.account_credit.code
                if item.code == '1009':
                    pension_empleado = item.salary_rule_id.account_credit.code
                if item.code == '1115' or item.code == '1215' or item.code == '1315':
                    pension_empresa = item.salary_rule_id.account_credit.code
                
            for items in journal.line_ids:
                if items.account_id.code == caja_de_compensación:
                    items.partner_id = self.contract_id.caja_com_id
                if items.account_id.code == salud_empleado:
                    items.partner_id = self.contract_id.EPS_id
                if items.account_id.code == salud_empresa:
                    items.partner_id = self.contract_id.EPS_id
                if items.account_id.code == arl:
                    items.partner_id = self.contract_id.arl_id
                if items.account_id.code == pension_empleado:
                    items.partner_id = self.contract_id.pension_id
                if items.account_id.code == pension_empresa:
                    items.partner_id = self.contract_id.pension_id

            journal.date = self.date_to
            journal.ref = self.number
        # return res

    def action_payslip_done(self):
        if self.analytic_account_tag_id and self.analytic_account_tag_id.analytic_distribution_ids:
            return self.action_payslip_done_with_analytic()
        else:
            return self.action_payslip_done_without_analytic()