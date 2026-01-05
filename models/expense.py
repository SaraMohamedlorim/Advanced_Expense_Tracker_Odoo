from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date


class Expense(models.Model):
    _name = 'expense.tracker'
    _description = 'Expense Tracker'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Expense Reference', required=True, default=lambda self: _('New'))
    dashboard_id = fields.Many2one('expense.tracker.dashboard', string='Dashboard')
    title = fields.Char(string='Title', required=True, tracking=True)
    amount = fields.Float(string='Amount', required=True, tracking=True)
    category_id = fields.Many2one('expense.category', string='Category', required=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today, required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id)
    amount_company_currency = fields.Float(string='Amount in Company Currency', compute='_compute_company_currency')



    # Advanced fields
    description = fields.Text(string='Description')
    receipt = fields.Binary(string='Receipt')
    receipt_filename = fields.Char(string='Receipt Filename')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid')
    ], string='Status', default='draft', tracking=True)

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one('res.partner', string='Vendor')
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Credit Card'),
        ('bank', 'Bank Transfer'),
        ('digital', 'Digital Payment')
    ], string='Payment Method')

    # Budget tracking
    budget_id = fields.Many2one('expense.budget', string='Budget',  required=True, ondelete='set null')
    budget_percentage = fields.Float(string='Budget Usage %', compute='_compute_budget_percentage')

    # Accounting integration
    account_move_id = fields.Many2one('account.move', string='Journal Entry')

    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)', 'Expense amount must be positive.'),
    ]

    # Fields for dashboard
    total_expenses = fields.Float(compute='_compute_dashboard_fields', string='Total Expenses')
    monthly_expenses = fields.Float(compute='_compute_dashboard_fields', string='Monthly Expenses')
    pending_approval = fields.Integer(compute='_compute_dashboard_fields', string='Pending Approval')
    budget_utilization = fields.Float(compute='_compute_dashboard_fields', string='Budget Utilization')

    @api.depends('state', 'amount', 'date')
    def _compute_dashboard_fields(self):
        # This is a simplified computation. In a real scenario, you might want to compute these per record or for the entire model.
        # Since dashboard is about overall data, we might compute these in a different way.
        # For now, we set them to 0 for each record.
        for record in self:
            record.total_expenses = 0
            record.monthly_expenses = 0
            record.pending_approval = 0
            record.budget_utilization = 0

    # We can also create a method to get the data for the charts
    @api.model
    def get_expense_data_for_dashboard(self):
        # Get total expenses
        total_expenses = self.search_count([])

        # Get monthly expenses: current month
        first_day_of_month = datetime.now().replace(day=1)
        monthly_expenses = self.search_count([('date', '>=', first_day_of_month)])

        # Pending approval: count of expenses in 'submitted' state
        pending_approval = self.search_count([('state', '=', 'submitted')])

        # Budget utilization: this might require budget model, so we skip for now
        budget_utilization = 0

        return {
            'total_expenses': total_expenses,
            'monthly_expenses': monthly_expenses,
            'pending_approval': pending_approval,
            'budget_utilization': budget_utilization,
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('expense.tracker') or _('New')
        return super().create(vals_list)

    @api.depends('amount', 'currency_id', 'company_id.currency_id')
    def _compute_company_currency(self):
        for record in self:
            if record.currency_id and record.company_id.currency_id:
                if record.currency_id == record.company_id.currency_id:
                    record.amount_company_currency = record.amount
                else:
                    # In a real implementation, you would use the exchange rate
                    record.amount_company_currency = record.amount
            else:
                record.amount_company_currency = record.amount

    @api.depends('amount', 'budget_id.amount')
    def _compute_budget_percentage(self):
        for record in self:
            if record.budget_id and record.budget_id.amount > 0:
                record.budget_percentage = (record.amount / record.budget_id.amount) * 100
            else:
                record.budget_percentage = 0.0

    def action_submit(self):
        self.write({'state': 'submitted'})
        self.message_post(body=_('Expense submitted for approval'))

    def action_approve(self):
        self.write({'state': 'approved'})
        self.message_post(body=_('Expense approved'))

    def action_reject(self):
        self.write({'state': 'rejected'})
        self.message_post(body=_('Expense rejected'))

    def action_mark_paid(self):
        self.write({'state': 'paid'})
        self.message_post(body=_('Expense marked as paid'))

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        self.message_post(body=_('Expense reset to draft'))

    def action_create_invoice(self):
        # Create a vendor bill from expense
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Vendor Bill'),
            'res_model': 'expense.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_expense_id': self.id}
        }
    

    def action_open_invoice_wizard(self):
        
        self.ensure_one()
        return {
            'name': 'Create Vendor Bill',
            'type': 'ir.actions.act_window',
            'res_model': 'expense.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_expense_id': self.id,
            }
        }

    @api.constrains('date')
    def _check_date(self):
        for record in self:
            if record.date > date.today():
                raise ValidationError(_('Expense date cannot be in the future.'))