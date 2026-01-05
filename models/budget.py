from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
from datetime import date , datetime, timedelta


class ExpenseBudget(models.Model):
    _name = 'expense.budget'
    _description = 'Expense Budget'
    _inherit = ['mail.thread']

    name = fields.Char(string='Budget Name', required=True)
    category_id = fields.Many2one('expense.category', string='Category', required=True)
    amount = fields.Float(string='Budget Amount', required=True, tracking=True)
    period_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom')
    ], string='Period Type', default='monthly', required=True)

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)

    # Computed fields
    spent_amount = fields.Float(string='Spent Amount', compute='_compute_spent_amount')
    remaining_amount = fields.Float(string='Remaining Amount', compute='_compute_remaining_amount')
    utilization_percentage = fields.Float(string='Utilization %', compute='_compute_utilization')

    # Related expenses
    expense_ids = fields.One2many('expense.tracker', 'budget_id', string='Expenses')
    expense_count = fields.Integer(string='Expense Count', compute='_compute_expense_count')

    # Alert thresholds
    warning_threshold = fields.Float(string='Warning Threshold %', default=80.0)
    critical_threshold = fields.Float(string='Critical Threshold %', default=95.0)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed')
    ], string='Status', default='draft', tracking=True)

    @api.depends('expense_ids.amount', 'expense_ids.state')
    def _compute_spent_amount(self):
        for budget in self:
            approved_expenses = budget.expense_ids.filtered(
                lambda x: x.state in ['approved', 'paid']
            )
            budget.spent_amount = sum(approved_expenses.mapped('amount'))

    @api.depends('amount', 'spent_amount')
    def _compute_remaining_amount(self):
        for budget in self:
            budget.remaining_amount = budget.amount - budget.spent_amount

    @api.depends('amount', 'spent_amount')
    def _compute_utilization(self):
        for budget in self:
            if budget.amount > 0:
                budget.utilization_percentage = (budget.spent_amount / budget.amount) * 100
            else:
                budget.utilization_percentage = 0.0

    def _compute_expense_count(self):
        for budget in self:
            budget.expense_count = len(budget.expense_ids)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for budget in self:
            if budget.date_from and budget.date_to:
                if budget.date_from > budget.date_to:
                    raise ValidationError(_('End date cannot be before start date.'))

    def action_view_expenses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expenses - %s' % self.name,
            'res_model': 'expense.tracker',
            'view_mode': 'tree,form',
            'domain': [('budget_id', '=', self.id)],
            'context': {'default_budget_id': self.id}
        }

    def action_activate(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})

    @api.model
    def _get_default_date_from(self):
        """Get default start date for budgets (beginning of current quarter)"""
        today = date.today()
        quarter = (today.month - 1) // 3
        return date(today.year, 3 * quarter + 1, 1)

    @api.model
    def _get_default_date_to(self):
        """Get default end date for budgets (end of current quarter)"""
        today = date.today()
        quarter = (today.month - 1) // 3
        next_quarter = quarter + 1
        if next_quarter > 3:
            return date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            return date(today.year, 3 * next_quarter + 1, 1) - timedelta(days=1)

    @api.model
    def _check_budget_alerts(self):
        """Scheduled method to check and send budget alerts"""
        # This method will be called by the cron job
        critical_budgets = self.search([
            ('state', '=', 'active'),
            ('utilization_percentage', '>=', 'critical_threshold')
        ])

        for budget in critical_budgets:
            # Send critical alerts
            pass

    def get_budget_report_data(self):
       
        self.ensure_one()

       
        data = {
            'total_budgets': self.search_count([]),
            'total_budget_amount': sum(self.search([]).mapped('amount')),
            'total_spent': sum(self.search([]).mapped('spent_amount')),
            'average_utilization': self.get_average_utilization(),
            'within_budget_count': self.search_count([('utilization_percentage', '<=', 80)]),
            'near_limit_count': self.search_count(
                [('utilization_percentage', '>', 80), ('utilization_percentage', '<=', 95)]),
            'over_budget_count': self.search_count([('utilization_percentage', '>', 95)]),
            'currency_id': self.env.user.company_id.currency_id.id,
            'company': self.env.user.company_id,
        }

        return data

    def get_utilization_report_data(self, date_from=None, date_to=None):
       
        self.ensure_one()

        if not date_from:
            date_from = date.today().replace(day=1)
        if not date_to:
            date_to = date.today()

       
        categories = self.env['expense.category'].search([])
        category_breakdown = []

        for category in categories:
            category_budgets = self.search([('category_id', '=', category.id)])
            if category_budgets:
                total_budget = sum(category_budgets.mapped('amount'))
                total_spent = sum(category_budgets.mapped('spent_amount'))
                utilization = (total_spent / total_budget * 100) if total_budget > 0 else 0

                category_breakdown.append({
                    'name': category.name,
                    'budget_amount': total_budget,
                    'spent_amount': total_spent,
                    'utilization': utilization,
                    'variance': total_budget - total_spent,
                })

       
        over_budget_items = self.search([('utilization_percentage', '>', 100)])
        over_budget_data = []

        for item in over_budget_items:
            over_budget_data.append({
                'name': item.name,
                'overspent_amount': item.spent_amount - item.amount,
                'utilization': item.utilization_percentage,
            })

        data = {
            'date_from': date_from,
            'date_to': date_to,
            'category_breakdown': category_breakdown,
            'over_budget_items': over_budget_data,
            'over_budget_count': len(over_budget_data),
            'currency_id': self.env.company.currency_id.id,
            'company': self.env.company,
        }

        return data

    def get_average_utilization(self):
       
        budgets = self.search([])
        if not budgets:
            return 0

        total_utilization = sum(budgets.mapped('utilization_percentage'))
        return total_utilization / len(budgets)