from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ExpenseInvoiceWizard(models.TransientModel):
    _name = 'expense.invoice.wizard'
    _description = 'Create Invoice from Expense Wizard'

    expense_id = fields.Many2one('expense.tracker', string='Expense', required=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 domain=[('type', '=', 'purchase')], required=True)
    invoice_date = fields.Date(string='Invoice Date', default=fields.Date.today)
    due_date = fields.Date(string='Due Date', compute='_compute_due_date', store=True)
    reference = fields.Char(string='Reference')

    # Additional options
    create_payment = fields.Boolean(string='Create Payment', default=False)
    payment_journal_id = fields.Many2one('account.journal', string='Payment Journal',
                                         domain=[('type', 'in', ['bank', 'cash'])])
    payment_date = fields.Date(string='Payment Date', default=fields.Date.today)

    # Pre-filled data from expense
    amount = fields.Float(string='Amount', related='expense_id.amount', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='expense_id.currency_id', readonly=True)
    description = fields.Text(string='Description', related='expense_id.description', readonly=True)

    @api.depends('invoice_date')
    def _compute_due_date(self):
        """Compute due date based on invoice date and payment terms"""
        for wizard in self:
            if wizard.invoice_date:
                # Default to 30 days from invoice date
                wizard.due_date = fields.Date.add(wizard.invoice_date, days=30)
            else:
                wizard.due_date = False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('default_expense_id'):
            expense = self.env['expense.tracker'].browse(self._context['default_expense_id'])
            res.update({
                'partner_id': expense.partner_id.id,
                'reference': expense.name,
                'description': expense.description,
            })
        return res

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Set default account from product"""
        if self.product_id:
            if not self.product_id.property_account_expense_id:
                raise UserError(_(
                    "Please set an expense account for the product %s."
                ) % self.product_id.name)

    def action_create_invoice(self):
        """Create vendor bill from expense"""
        self.ensure_one()

        if not self.product_id.property_account_expense_id:
            raise UserError(_(
                "The selected product doesn't have an expense account configured. "
                "Please set an expense account for the product."
            ))

        # Create vendor bill
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.invoice_date,
            'invoice_date_due': self.due_date,
            'journal_id': self.journal_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'name': self.expense_id.title,
                'quantity': 1,
                'price_unit': self.expense_id.amount,
                'account_id': self.product_id.property_account_expense_id.id,
            })],
            'ref': self.reference,
        }

        invoice = self.env['account.move'].create(invoice_vals)

        # Validate invoice if in draft state
        if invoice.state == 'draft':
            invoice.action_post()

        # Link invoice to expense
        self.expense_id.write({
            'account_move_id': invoice.id,
            'state': 'paid',
            'partner_id': self.partner_id.id
        })

        # Create payment if requested
        if self.create_payment and self.payment_journal_id:
            self._create_payment(invoice)

        # Post message to expense record
        self.expense_id.message_post(
            body=_(
                "Vendor bill created: <a href=# data-oe-model=account.move data-oe-id=%(invoice_id)d>%(invoice_name)s</a>") % {
                     'invoice_id': invoice.id,
                     'invoice_name': invoice.name
                 }
        )

        # Return action to view the created invoice
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_payment(self, invoice):
        """Create payment for the invoice"""
        payment_vals = {
            'amount': abs(invoice.amount_total),
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner_id.id,
            'journal_id': self.payment_journal_id.id,
            'date': self.payment_date,
            'ref': _("Payment for %s") % invoice.name,
        }

        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()

        # Reconcile payment with invoice
        if invoice.state == 'posted':
            (invoice + payment.move_id).line_ids.filtered(
                lambda line: line.account_id == invoice.line_ids.account_id.filtered(
                    lambda acc: acc.account_type in ('asset_receivable', 'liability_payable')
                )
            ).reconcile()

        return payment