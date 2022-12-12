# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api,_
from odoo.exceptions import UserError


class account_payment_register(models.TransientModel):
    _inherit = 'account.payment.register'

    loan_installment_id = fields.Many2one('loan.installment',string="Loan Installment",domain=[('state','=','approve')])
    

    @api.onchange('loan_installment_id')
    def onchange_loan_installment(self):
    	self.amount = self.loan_installment_id.emi_installment
    	self.partner_id = self.loan_installment_id.loan_id.user_id.partner_id.id

    	return


    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconcilable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        super(account_payment_register,self).post()
        for rec in self:
            if rec.loan_installment_id and rec.loan_installment_id.emi_installment == rec.amount : 
                rec.loan_installment_id.action_payment()
        return True
