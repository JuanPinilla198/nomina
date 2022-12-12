# -*- coding: utf-8 -*-
# Copyright © 2020 Quemari Developers - All Rights Reserved
# Author      Quemari Developers

# local application/library specific imports
from odoo import _, api, fields, models, tools, exceptions
import xlsxwriter
import base64

# Events log's
import logging
_logger = logging.getLogger(__name__)


class PayslipReportWizard(models.TransientModel):
    """
    This wizard is meant to filter the results for the sales by date or supplier report.
    """
    _name = 'payslip.report.wizard'

    xls_file = fields.Binary(string='Download')
    name = fields.Char(string='File name', size=64)
    state = fields.Selection([('choose', 'choose'),
                              ('download', 'download')], default="choose", string="Status")
    payslip_ids = fields.Many2many('hr.payslip', string="Payslip Ref.")
    date_from = fields.Date(string=('Initial date.'), required=True)
    date_to = fields.Date(string=('End date.'), required=True)
    analitic_account_city = fields.Many2many('account.analytic.account', string="City", domain="[('parent_id','=', False)]")
    analitic_account_company = fields.Many2one('account.analytic.account', string="Company")

    @api.onchange('analitic_account_city')
    def on_change_analitic_account_city(self):
        domain = {}
        if self.analitic_account_city:
            domain_analitic_account_company = [
               
            ]
            domain['domain'] = {
                    'analitic_account_company': domain_analitic_account_company,
                }
        return domain


    def print_report_xls(self):

        domain = [('date', '<=', self.date_to), ('date', '>=', self.date_from), ('state', '=', 'done')]
        if self.analitic_account_city: 
            domain.append(('parent_analytic_id','in', self.analitic_account_city.id))

        if self.analitic_account_company:
            domain.append(('analytic_account_id','in', self.analitic_account_company.id))

        slip_ids = self.env['hr.payslip'].search(domain)
        if slip_ids:
            xls_filename = 'Payslip Report.xlsx'
            workbook = xlsxwriter.Workbook('/tmp/' + xls_filename)
            worksheet = workbook.add_worksheet("Batch Payslip Report")
            
            text_center = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
            text_center.set_text_wrap()
            font_bold_center = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
            font_bold_right = workbook.add_format({'bold': True})
            font_bold_right.set_num_format('###0.00')
            number_format = workbook.add_format()
            number_format.set_num_format('###0.00')
            
            worksheet.set_column('A:AZ', 18)
            for i in range(3):
                worksheet.set_row(i, 18)
            worksheet.write(0, 1, 'Company Name', font_bold_center)
            worksheet.merge_range(0, 2, 0, 3, self.env.user.company_id.name or '', text_center)
            row = 3
            worksheet.merge_range(row, 0, row + 1, 0, 'No #', font_bold_center)
            worksheet.merge_range(row, 1, row + 1, 1, 'Payslip Ref', font_bold_center)
            worksheet.merge_range(row, 2, row + 1, 2, 'Employee', font_bold_center)
            worksheet.merge_range(row, 3, row + 1, 3, 'Designation', font_bold_center)
            worksheet.merge_range(row, 4, row + 1, 4, 'Period', font_bold_center)
            
            col = 5
            worksheet.set_row(row + 1, 30)
            result = self.get_header(slip_ids)
            col_lst = []
            # make the header by category
            for item in result:
                for categ_id, salary_rule_ids in item.items():
                    if not salary_rule_ids:
                        continue
                    if len(salary_rule_ids) == 1:
                        worksheet.write(row, col, categ_id.name, font_bold_center)
                        worksheet.write(row + 1, col, salary_rule_ids[0].name, text_center)
                        col += 1
                        col_lst.append(salary_rule_ids[0])
                    else:
                        rule_count = len(salary_rule_ids) - 1
                        worksheet.merge_range(row, col, row, col + rule_count, categ_id.name, font_bold_center)
                        for rule_id in salary_rule_ids.sorted(key=lambda l: l.sequence):
                            worksheet.write(row + 1, col, rule_id.name, text_center)
                            col += 1
                            col_lst.append(rule_id)
            row += 3
            sr_no = 1
            total_rule_sum_dict = {}
            # print the data of payslip
            for payslip in slip_ids:
                worksheet.write(row, 0, sr_no, text_center)
                worksheet.write(row, 1, payslip.number)
                worksheet.write(row, 2, payslip.employee_id.name)
                worksheet.write(row, 3, payslip.employee_id.job_id.name or '')
                worksheet.write(row, 4, str(payslip.date_from) + ' - ' + str(payslip.date_to) or '')
                col = 5
                for col_rule_id in col_lst:
                    line_id = payslip.line_ids.filtered(lambda l: l.salary_rule_id.id == col_rule_id.id)
                    amount = line_id.total or 0.0
                    worksheet.write(row, col, amount, number_format)
                    col += 1
                    total_rule_sum_dict.setdefault(col_rule_id, [])
                    total_rule_sum_dict[col_rule_id].append(amount)
                row += 1
                sr_no += 1
            # print the footer
            col = 5
            row += 1
            worksheet.write(row, 4, "Total", font_bold_center)
            for col_rule_id in col_lst:
                worksheet.write(row, col, sum(total_rule_sum_dict.get(col_rule_id)), font_bold_right)
                col += 1
            workbook.close()
            action = self.env.ref('payslip_report.action_wizard_payslip_report_excel').read()[0]
            action['res_id'] = self.id
            self.write({'state': 'download',
                        'name': xls_filename,
                        'xls_file': base64.b64encode(open('/tmp/' + xls_filename, 'rb').read())})
            return action
        else:
            raise exceptions.Warning(_('Not records found!.'))



    def print_report_pdf(self):
        data = self.read()[0]
        return self.env.ref('payslip_report.action_print_payslip_pdf_report').report_action([], data=data)

    


    def get_header(self, slip_ids):
        category_list_ids = self.env['hr.salary.rule.category'].search([])
        # find all the rule by category
        col_by_category = {}
        for payslip in slip_ids:
            for line in payslip.line_ids:
                col_by_category.setdefault(line.category_id, [])
                col_by_category[line.category_id] += line.salary_rule_id.ids
        for categ_id, rule_ids in col_by_category.items():
            col_by_category[categ_id] = self.env['hr.salary.rule'].browse(set(rule_ids)).filtered(lambda rule:rule.dont_show_in_report == False)
        # make the category wise rule
        result = []
        for categ_id in category_list_ids:
            rule_ids = col_by_category.get(categ_id)
            if not rule_ids:
                continue
            result.append({categ_id: rule_ids.sorted(lambda l: l.sequence)})
        return result


    def action_go_back(self):
        action = self.env.ref('payslip_report.action_wizard_payslip_report_excel').read()[0]
        action['res_id'] = self.id
        self.write({'state': 'choose'})
        return action


class payslip_report_report_payslip_template(models.AbstractModel):
    _name = 'report.payslip_report.report_payslip_template'


    def get_analytic_data(self, analytic_id):
        result = self.env['account.analytic.account'].browse(analytic_id)
        return result

    @api.model
    def _get_report_values(self, docids, data=None):

        report = self.env['ir.actions.report']._get_report_from_name('payslip_report.report_payslip_template')
        wizard_id = self.env['payslip.report.wizard'].browse(data.get('id'))

        domain = [('date', '<=', wizard_id.date_to), ('date', '>=', wizard_id.date_from), ('state', '=', 'done')]
        if wizard_id.analitic_account_city: 
            domain.append(('parent_analytic_id','=', wizard_id.analitic_account_city.id))

        if wizard_id.analitic_account_company:
            domain.append(('analytic_account_id','in', wizard_id.analitic_account_company.ids))
        
        slip_ids = self.env['hr.payslip'].search(domain)

        if slip_ids:
            grouped_data = {}
            for slip in slip_ids:
                list_data = grouped_data.get(slip.analytic_account_id.id, [])
                if slip.analytic_account_id.id in grouped_data:
                    list_data.append(slip)
                    grouped_data.update({slip.analytic_account_id.id: list_data})
                else:
                    list_data.append(slip)
                    grouped_data[slip.analytic_account_id.id] = list_data
            get_header = wizard_id.get_header(slip_ids)
            get_rule_list = []

            for header_dict in get_header:
                for rule_ids in header_dict.values():
                    for rule_id in rule_ids:
                        if not rule_id.dont_show_in_report:
                            get_rule_list.append(rule_id)
            _logger.info("-"*300)
            _logger.info(grouped_data)
            return {
                'doc_ids': self.ids,
                'doc_model': report,
                'docs': slip_ids,
                'data': data,
                'slip_ids': slip_ids,
                'grouped_data': grouped_data,
                '_get_header': get_header,
                '_get_rule_list': get_rule_list,
                'get_analytic_data': self.get_analytic_data
            }
        else:
            raise exceptions.Warning(_('Not records found!.'))

        

    


