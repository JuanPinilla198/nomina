from odoo import models, fields, api, _
from datetime import datetime, timedelta, date

class AdjustMethod(models.TransientModel):
    _name = 'adjust.method'

    method = fields.Selection(String="Método",
                                    selection=[
                                        ('nota_ajuste', 'Nota de ajuste'),
                                        ('nota_eliminacion', 'Nota de eliminación'),
                                    ])
    reason = fields.Char(String="Razón")
    date_adjustnote = fields.Date(String="Fecha", default=date.today())

    def action_reverse(self):

        x = self.env['payroll.payroll.window'].browse(self._context['dian_doc_id'])
        dat = {}
        for payslip in x.table_ids:
            if payslip.employee_id.id in dat:
                date_t = payslip.date_to
                dat[payslip.employee_id.id]['date_to'] = date_t

            else:
                dat[payslip.employee_id.id] = {}
                date_f = payslip.date_from
                dat[payslip.employee_id.id]['date_from'] = date_f
                date_t = payslip.date_to
                dat[payslip.employee_id.id]['date_to'] = date_t
        
        fecha = self.env['hr.payslip'].search([('date_from','=',dat[payslip.employee_id.id]['date_from']),
                                               ('employee_id','=',x.employee.id),
                                               ('state','=','done')])
        
        sequence_code = ''
        IPC = self.env['ir.config_parameter'].sudo()
        if self.method == 'nota_ajuste':
            adj_sequence = int(IPC.get_param('l10n_co_payroll.adj_sequence'))
            sequence = self.env['ir.sequence'].sudo().browse(adj_sequence)
            if sequence:
                sequence_code = sequence.code
            note_type_field = '1'
            adj_method_field = 'adjustment'
        elif self.method == 'nota_eliminacion':
            elim_sequence = int(IPC.get_param('l10n_co_payroll.elim_sequence'))
            sequence = self.env['ir.sequence'].sudo().browse(elim_sequence)
            if sequence:
                sequence_code = sequence.code
            note_type_field = '2'
            adj_method_field = 'elimination'
        vals = {'refund_reason': self.reason, 'date_adjustnote': self.date_adjustnote, 'note_type': note_type_field,'adj_method':adj_method_field , 'credit_note': True, 'employee_id': x.employee.id, 'date_from':dat[payslip.employee_id.id]['date_from'],'date_to':dat[payslip.employee_id.id]['date_to'], 'contract_id': x.employee.contract_id.id, 'struct_id': x.employee.contract_id.struct_id.id}
        payslip_ = self.env['hr.payslip'].create(vals)
        x1 = payslip_.get_worked_day_lines(x.employee.contract_id, dat[payslip.employee_id.id]['date_from'],dat[payslip.employee_id.id]['date_to'] )
        payslip_.worked_days_line_ids = x1
        payslip_.compute_sheet()
        

        formview_ref = self.env.ref('hr_payroll.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
        
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % payslip_.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }
        
       

        