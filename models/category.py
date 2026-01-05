from odoo import models, fields, api


class ExpenseCategory(models.Model):
    _name = 'expense.category'
    _description = 'Expense Category'
    _order = 'name'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('expense.category', string='Parent Category')
    child_ids = fields.One2many('expense.category', 'parent_id', string='Subcategories')
    color = fields.Integer(string='Color Index')

    # Budget settings
    has_budget = fields.Boolean(string='Has Budget Control')
    default_budget_amount = fields.Float(string='Default Budget Amount')

    # Accounting integration
    account_id = fields.Many2one('account.account', string='Expense Account')

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Category name must be unique.'),
    ]