from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class BudgetAlertWizard(models.TransientModel):
    _name = 'budget.alert.wizard'
    _description = 'Budget Alert Configuration Wizard'

    budget_id = fields.Many2one('expense.budget', string='Budget', required=True)
    alert_type = fields.Selection([
        ('warning', 'Warning Alert'),
        ('critical', 'Critical Alert'),
        ('custom', 'Custom Alert')
    ], string='Alert Type', required=True, default='warning')

    # Alert configuration
    threshold_percentage = fields.Float(
        string='Threshold Percentage',
        help='Send alert when budget utilization reaches this percentage'
    )
    custom_message = fields.Text(string='Custom Message')

    # Notification settings
    notify_users = fields.Many2many(
        'res.users',
        string='Notify Users',
        help='Users who will receive this alert'
    )
    notify_via_email = fields.Boolean(string='Send Email Notification', default=True)
    notify_via_chat = fields.Boolean(string='Send Chat Notification', default=True)

    # Alert message
    message = fields.Text(
        string='Alert Message',
        compute='_compute_message',
        readonly=False,
        store=True
    )

    # Schedule options
    schedule_type = fields.Selection([
        ('immediate', 'Send Immediately'),
        ('scheduled', 'Schedule for Future')
    ], string='Schedule', default='immediate')

    scheduled_date = fields.Datetime(string='Scheduled Date')

    # Recurrence
    is_recurring = fields.Boolean(string='Recurring Alert')
    recurrence_interval = fields.Integer(string='Repeat Every', default=1)
    recurrence_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string='Recurrence Unit', default='weeks')

    # Results
    alert_sent = fields.Boolean(string='Alert Sent', readonly=True)
    sent_date = fields.Datetime(string='Sent Date', readonly=True)

    @api.depends('alert_type', 'threshold_percentage', 'custom_message', 'budget_id')
    def _compute_message(self):
        """Compute the alert message based on type and budget data"""
        for wizard in self:
            if wizard.alert_type == 'warning' and wizard.budget_id:
                wizard.message = _(
                    "Budget Warning Alert\n\n"
                    "Budget: %(budget_name)s\n"
                    "Current Utilization: %(utilization).1f%%\n"
                    "Threshold: %(threshold).1f%%\n"
                    "Spent Amount: %(spent).2f\n"
                    "Remaining Amount: %(remaining).2f\n\n"
                    "This budget is approaching its limit. Please review your expenses."
                ) % {
                                     'budget_name': wizard.budget_id.name,
                                     'utilization': wizard.budget_id.utilization_percentage,
                                     'threshold': wizard.threshold_percentage,
                                     'spent': wizard.budget_id.spent_amount,
                                     'remaining': wizard.budget_id.remaining_amount,
                                 }
            elif wizard.alert_type == 'critical' and wizard.budget_id:
                wizard.message = _(
                    "CRITICAL BUDGET ALERT\n\n"
                    "Budget: %(budget_name)s\n"
                    "Current Utilization: %(utilization).1f%%\n"
                    "Threshold: %(threshold).1f%%\n"
                    "Spent Amount: %(spent).2f\n"
                    "Remaining Amount: %(remaining).2f\n\n"
                    "⚠️ This budget has exceeded its critical threshold! "
                    "Immediate action required."
                ) % {
                                     'budget_name': wizard.budget_id.name,
                                     'utilization': wizard.budget_id.utilization_percentage,
                                     'threshold': wizard.threshold_percentage,
                                     'spent': wizard.budget_id.spent_amount,
                                     'remaining': wizard.budget_id.remaining_amount,
                                 }
            elif wizard.alert_type == 'custom':
                wizard.message = wizard.custom_message or _("Custom budget alert")

    @api.constrains('threshold_percentage')
    def _check_threshold_percentage(self):
        """Validate threshold percentage"""
        for wizard in self:
            if wizard.alert_type in ['warning', 'critical']:
                if not 0 <= wizard.threshold_percentage <= 100:
                    raise ValidationError(_("Threshold percentage must be between 0 and 100."))

    @api.constrains('scheduled_date')
    def _check_scheduled_date(self):
        """Validate scheduled date"""
        for wizard in self:
            if wizard.schedule_type == 'scheduled' and wizard.scheduled_date:
                if wizard.scheduled_date < fields.Datetime.now():
                    raise ValidationError(_("Scheduled date cannot be in the past."))

    def _send_email_notification(self, partner_ids, subject, body):
        """Send email notification to specified partners"""
        if not partner_ids:
            return

        mail_template = self.env.ref('expense_tracker_advanced.email_template_budget_alert')

        for partner_id in partner_ids:
            mail_template.with_context(
                custom_subject=subject,
                custom_body=body,
                budget=self.budget_id
            ).send_mail(
                self.id,
                force_send=True,
                email_values={'recipient_ids': [(4, partner_id)]}
            )

    def _send_chat_notification(self, user_ids, message):
        """Send chat notification to specified users"""
        if not user_ids:
            return

        # Create a chat message in the budget record
        self.budget_id.message_post(
            body=message,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            partner_ids=user_ids.mapped('partner_id').ids
        )

        # Alternatively, you could use the mail.channel method for direct chat
        # This is a simplified version
        for user in user_ids:
            if user != self.env.user:
                self.env['mail.message'].create({
                    'model': 'res.users',
                    'res_id': user.id,
                    'body': message,
                    'subject': 'Budget Alert',
                    'partner_ids': [(4, user.partner_id.id)],
                })

    def _create_recurring_alert(self):
        """Create a recurring alert schedule"""
        if not self.is_recurring:
            return

        cron = self.env['ir.cron'].create({
            'name': _('Recurring Budget Alert: %s') % self.budget_id.name,
            'model_id': self.env.ref('expense_tracker_advanced.model_budget_alert_wizard').id,
            'state': 'code',
            'code': 'model._trigger_recurring_alert(%d)' % self.id,
            'interval_number': self.recurrence_interval,
            'interval_type': self.recurrence_unit,
            'numbercall': -1,  # Unlimited
            'active': True,
        })

        return cron

    def _trigger_recurring_alert(self):
        """Method called by cron for recurring alerts"""
        # This would check current budget status and send alert if conditions are met
        if self.budget_id.utilization_percentage >= self.threshold_percentage:
            self.action_send_alert()

    def action_test_alert(self):
        """Send a test alert to current user"""
        self.ensure_one()

        test_users = self.env.user
        subject = _("TEST: Budget Alert - %s") % self.budget_id.name
        body = _("This is a test alert for budget monitoring.\n\n") + self.message

        # Send test notifications
        if self.notify_via_email:
            self._send_email_notification(
                test_users.partner_id.ids,
                subject,
                body
            )

        if self.notify_via_chat:
            self._send_chat_notification(test_users, body)

        # Show confirmation
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test Alert Sent'),
                'message': _('Test alert has been sent to your account.'),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_send_alert(self):
        """Send the budget alert to specified users"""
        self.ensure_one()

        if not self.notify_users:
            raise UserError(_("Please select at least one user to notify."))

        partner_ids = self.notify_users.mapped('partner_id').ids
        subject = _("Budget Alert - %s") % self.budget_id.name

        # Send notifications based on user preferences
        if self.notify_via_email:
            self._send_email_notification(partner_ids, subject, self.message)

        if self.notify_via_chat:
            self._send_chat_notification(self.notify_users, self.message)

        # Create an activity on the budget record
        self.budget_id.activity_schedule(
            act_type_xmlid='mail.mail_activity_data_todo',
            summary=_('Budget Alert Sent'),
            note=self.message,
            user_id=self.env.user.id
        )

        # Update wizard state
        self.write({
            'alert_sent': True,
            'sent_date': fields.Datetime.now()
        })

        # Create recurring alert if needed
        if self.is_recurring:
            self._create_recurring_alert()

        # Post message to budget record
        self.budget_id.message_post(
            body=_("Budget alert sent to: %s") % ", ".join(self.notify_users.mapped('name')),
            subject=subject
        )

        # Show success message
        message = _(
            "Budget alert has been sent successfully to %d user(s)."
        ) % len(self.notify_users)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Alert Sent'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window_close'
                }
            }
        }

    def action_view_budget(self):
        """Open the related budget record"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget'),
            'res_model': 'expense.budget',
            'res_id': self.budget_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def create_default_alerts(self):
        """Create default budget alerts for all active budgets nearing their limits"""
        active_budgets = self.env['expense.budget'].search([
            ('state', '=', 'active'),
            ('utilization_percentage', '>=', 80)
        ])

        for budget in active_budgets:
            alert_type = 'critical' if budget.utilization_percentage >= 95 else 'warning'

            # Find budget manager or category responsible users
            notify_users = self.env['res.users'].search([
                ('groups_id', 'in', self.env.ref('expense_tracker_advanced.group_expense_manager').id)
            ])

            if notify_users:
                self.create({
                    'budget_id': budget.id,
                    'alert_type': alert_type,
                    'threshold_percentage': budget.utilization_percentage,
                    'notify_users': [(6, 0, notify_users.ids)],
                    'notify_via_email': True,
                    'notify_via_chat': True,
                }).action_send_alert()