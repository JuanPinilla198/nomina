from odoo import fields, models, api

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    salario_minimo = fields.Float("Salario Minimo", default='1000000')
    salario_uvt = fields.Float("Salario UVT", default="38004")
    aux_transporte = fields.Float("Auxilio de transporte", default="117172")