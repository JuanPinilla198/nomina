# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    adj_sequence = fields.Many2one('ir.sequence', string='Adjustment Note Sequence')
    elim_sequence = fields.Many2one('ir.sequence', string='Elimination Note Sequence')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IPC = self.env['ir.config_parameter'].sudo()

        if IPC.get_param('l10n_co_payroll.adj_sequence') and str(IPC.get_param('l10n_co_payroll.adj_sequence')).isnumeric():
            res.update(
                adj_sequence=int(IPC.get_param('l10n_co_payroll.adj_sequence')),
            )
        if IPC.get_param('l10n_co_payroll.elim_sequence') and str(IPC.get_param('l10n_co_payroll.elim_sequence')).isnumeric():
            res.update(
                elim_sequence=int(IPC.get_param('l10n_co_payroll.elim_sequence')),
            )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IPC = self.env['ir.config_parameter'].sudo()
        IPC.set_param('l10n_co_payroll.adj_sequence', self.adj_sequence and self.adj_sequence.id or False)
        IPC.set_param('l10n_co_payroll.elim_sequence', self.elim_sequence and self.elim_sequence.id or False)
