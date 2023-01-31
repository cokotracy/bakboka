# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = "account.move"

    opay_reference = fields.Char(string='OPay Reference', readonly=True)