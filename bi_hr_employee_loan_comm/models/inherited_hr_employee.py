# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import datetime


class Hr_Employee(models.Model):
	_inherit = 'hr.employee'
   
	loan_ids = fields.One2many('loan.request','employee_id')
	policy_ids = fields.Many2many('loan.policies','rel_hr_employee_policies_id',string="Employees")
	allow_multiple_loan = fields.Boolean(string="Allow Multiple Loans")


	def get_installment_loan(self,id,date_from,date_to) :
		installment_rec = self.env['loan.installment'].sudo().search([('employee_id','=',self.id),('date_from','=',date_from),
																	('date_to','=',date_to),('state','=','unpaid')])
		

		amount =0.0
		for rec in installment_rec:
			loan = self.env['loan.request'].sudo().search([('id','=',rec.loan_id.id)])
			if loan.loan_type_id.disburse_method == 'direct':
				pass
			else :
				amount += rec.principal_amount      
		return amount

	def get_principal_amount(self,date_from) :
		
		loan = self.env['loan.request'].sudo().search([('employee_id','=',self.id),('stage','=','approve')])
		amount = 0.0
		for rec in loan:
			if rec.loan_type_id.disburse_method == 'direct':
				pass
			if rec.approve_date.month == date_from.month:
				amount += rec.principal_amount
		return amount
			   
	def get_interest_loan(self,id,date_from,date_to) :
		installment_rec = self.env['loan.installment'].sudo().search([('employee_id','=',id),('date_from','=',date_from),
																	('date_to','=',date_to),('state','=','unpaid')])
		interest = 0.0
		for rec in installment_rec:
			if rec.pay_from_payroll == True :
				pass
			else :
				interest+=rec.interest_amount
		return interest  


class EmployeePublic(models.Model):
	_inherit = 'hr.employee.public'

	loan_ids = fields.One2many('loan.request','employee_id')
	policy_ids = fields.Many2many('loan.policies','rel_hr_employee_policies_id',string="Employees")
	allow_multiple_loan = fields.Boolean(string="Allow Multiple Loans")
		


class Hr_paysleep(models.Model):
	_inherit = "hr.payslip"

	def compute_sheet(self):
		for payslip in self:
			# number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
			# delete old payslip lines
			payslip.line_ids.unlink()
			# set the list of contract for which the rules have to be applied
			# if we don't give the contract, then the rules to apply should be for all current contracts of the employee
			contract_ids = payslip.contract_id.ids or \
				payslip.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
			
			lines = [(0, 0, line) for line in payslip._get_payslip_lines(contract_ids, payslip.id)]

			# payslip.write({'line_ids': lines, 'number': number})
			payslip.write({'line_ids': lines})
		return True

	def action_payslip_done(self):
		res = super(Hr_paysleep, self).action_payslip_done()
		for payslip in self:
			payslip.compute_sheet()
			installment_rec = self.env['loan.installment'].sudo().search([('employee_id','=',payslip.employee_id.id),('date_from','=',payslip.date_from),
																		('date_to','=',payslip.date_to)],order="id desc")
			if installment_rec :
				for rec in installment_rec:
					loan = self.env['loan.request'].sudo().search([('id','=',rec.loan_id.id)])
					if loan.loan_type_id.disburse_method == 'payroll':
						if rec.state not in ['paid','postpone']:
							name_of = rec.employee_id.name
				
							debit_line = (0,0,{'account_id' : rec.loan_id.disburse_journal_id.default_credit_account_id.id,
												'employee_id' : rec.employee_id.id, 
												'name' : 'Loan Of ' + name_of,
												'debit' : rec.emi_installment,
												'credit' : 0.0
												})


							credit_line = (0,0,{'account_id' : rec.loan_id.employee_account_id.id,
												'employee_id' : rec.employee_id.id,
												'name' : 'Loan Of ' + name_of,
												'debit' : 0.0,
												'credit' : rec.emi_installment
												})
							move_line =[debit_line,credit_line]
							payslip.move_id.update({'loan_ids': rec.loan_id,'is_loan_slip' : True})
							rec.state = 'paid'
							payslip.move_id.write({'line_ids' : move_line})
							payslip.write({'state': 'done'})
							loans = self.env['loan.request'].search([('employee_id','=',rec.employee_id.id)])
							rec.update({'state':'paid', 'accounting_entry_id': payslip.move_id})
							for record in loans:
								record.write({'move_entries': [(4, payslip.move_id.id)]})    
						else:
							pass         
					else:
						pass