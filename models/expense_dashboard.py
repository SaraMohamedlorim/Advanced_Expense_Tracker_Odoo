from odoo import models, fields, api, _
from datetime import date


class ExpenseDashboard(models.Model):
    _name = "expense.tracker.dashboard"
    _description = "Expense Tracker Dashboard"

   
    total_expenses = fields.Monetary(string="Total Expenses", compute="_compute_dashboard_data",
                                     currency_field="company_currency_id")
    monthly_expenses = fields.Monetary(string="This Month Expenses", compute="_compute_dashboard_data",
                                       currency_field="company_currency_id")
    pending_approval = fields.Integer(string="Pending Approval", compute="_compute_dashboard_data")
    budget_utilization = fields.Float(string="Budget Utilization (%)", compute="_compute_dashboard_data")

    remaining_budget = fields.Monetary(string="Remaining Budget", compute="_compute_dashboard_data",
                                   currency_field="company_currency_id")


   
    company_currency_id = fields.Many2one("res.currency", string="Company Currency",
                                          default=lambda self:  self.env.user.company_id.currency_id)

   
    recent_expenses = fields.One2many("expense.tracker", "dashboard_id", string="Recent Expenses")

   

    @api.depends('recent_expenses')
    def _compute_dashboard_data(self):
       
        for record in self:
            expenses = self.env['expense.tracker'].search([])
            total_expenses = sum(exp.amount_company_currency for exp in expenses)
            record.total_expenses = total_expenses

           
            current_month = date.today().month
            record.monthly_expenses = sum(
                exp.amount_company_currency for exp in expenses if exp.date and exp.date.month == current_month
            )

           
            record.pending_approval = len(expenses.filtered(lambda e: e.state == 'submitted'))

           
            budgets = self.env['expense.budget'].search([])
            total_budget = sum(b.amount for b in budgets)


            total_budget_expenses = 0.0

            for budget in budgets:
                related_expenses = self.env['expense.tracker'].search([
                    ('category_id', '=', budget.category_id.id),
                    ('budget_id', '=', budget.id)
                ])
                total_budget_expenses += sum(related_expenses.mapped('amount_company_currency'))

            record.budget_utilization = (total_expenses / total_budget * 100) if total_budget else 0.0
            record.remaining_budget = total_budget - total_expenses

