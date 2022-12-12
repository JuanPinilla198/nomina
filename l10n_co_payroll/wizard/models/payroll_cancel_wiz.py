# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime


class PayrollCancelWizard(models.TransientModel):
    _name = 'payroll.cancel.wizard'
    _description = 'Payroll Cancel Wizard'

    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    adj_method = fields.Selection([('adjustment', 'Adjustment Note'), ('elimination', 'Elimination Note')], string='Adjustment Method')
    reason = fields.Char(string='Reason')
    refund_date = fields.Date(string='Refund Date')

    def action_reverse(self):
        fecha = self.env['hr.payslip'].search([('date_from','=',self.payslip_id.date_from),
                                               ('employee_id','=',self.payslip_id.employee_id.id),
                                               ('state','=','done')])

        sequence_code = ''
        IPC = self.env['ir.config_parameter'].sudo()
        vals = {'refund_reason': self.reason, 'refund_date': self.refund_date, 'adj_method': self.adj_method, 'credit_note': True, 'name': _('Refund: ') + self.payslip_id.name, 'payslip_refunded_id': self.payslip_id.id, 'document_source': self.payslip_id.number, 'note_type' : self.adj_method}
        if self.adj_method == 'adjustment':
            adj_sequence = int(IPC.get_param('l10n_co_payroll.adj_sequence'))
            sequence = self.env['ir.sequence'].sudo().browse(adj_sequence)
            vals['note_type'] = "1"
            if sequence:
                sequence_code = sequence.code
        elif self.adj_method == 'elimination':
            elim_sequence = int(IPC.get_param('l10n_co_payroll.elim_sequence'))
            sequence = self.env['ir.sequence'].sudo().browse(elim_sequence)
            vals['note_type'] = "2"
            #print("estoy aqui en el ajuste")
            #print(self.adj_method)
            if sequence:
                sequence_code = sequence.code
        copied_payslip = self.payslip_id.copy(vals)
        if self.adj_method == 'elimination':
            # copied_payslip.with_context(without_compute_sheet=True).action_payslip_done()
            copied_payslip.action_payslip_done()
            copied_payslip.number = self.env['ir.sequence'].next_by_code(sequence_code)
            #print("estoy aqui en el ajuste")
            #print(self.adj_method)
        #if self.adj_method == 'adjustment':
            # copied_payslip.with_context(without_compute_sheet=True).action_payslip_done()
            #copied_payslip.action_payslip_done()
            #copied_payslip.number = self.env['ir.sequence'].next_by_code(sequence_code)
        formview_ref = self.env.ref('bi_hr_payroll.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('bi_hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }
