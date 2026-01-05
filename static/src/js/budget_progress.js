odoo.define('expense_tracker_advanced.budget_progress', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var field_registry = require('web.field_registry');
    var core = require('web.core');
    var _t = core._t;

    // Budget Progress Field Widget
    var BudgetProgress = AbstractField.extend({
        className: 'o_field_budget_progress',
        supportedFieldTypes: ['float'],

        /**
         * @override
         */
        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            this.utilization = 0;
            this.budgetAmount = 0;
            this.spentAmount = 0;
        },

        /**
         * @override
         */
        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                return self._loadBudgetData();
            });
        },

        /**
         * Load budget data
         */
        _loadBudgetData: function () {
            var self = this;
            var budgetId = this.record.data.budget_id && this.record.data.budget_id[0];

            if (budgetId) {
                return this._rpc({
                    model: 'expense.budget',
                    method: 'read',
                    args: [[budgetId], ['amount', 'spent_amount', 'utilization_percentage']]
                }).then(function (result) {
                    if (result && result[0]) {
                        self.budgetAmount = result[0].amount;
                        self.spentAmount = result[0].spent_amount;
                        self.utilization = result[0].utilization_percentage;
                    }
                    return result;
                });
            }
            return Promise.resolve();
        },

        /**
         * @override
         */
        _render: function () {
            var $content = $('<div class="budget-progress-widget"></div>');

            if (this.budgetAmount > 0) {
                var utilization = Math.min(this.utilization, 100);
                var statusClass = utilization >= 95 ? 'critical' : utilization >= 80 ? 'warning' : 'normal';

                var html = `
                    <div class="budget-progress-header">
                        <span class="budget-progress-title">${_t('Budget Utilization')}</span>
                        <span class="budget-progress-percentage">${utilization.toFixed(1)}%</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar-background">
                            <div class="progress-bar-fill ${statusClass}" style="width: ${utilization}%">
                                <div class="progress-bar-text">${utilization.toFixed(1)}%</div>
                            </div>
                        </div>
                    </div>
                    <div class="budget-progress-details">
                        <div class="row text-center">
                            <div class="col-4">
                                <div class="detail-label">${_t('Budget')}</div>
                                <div class="detail-value">${this._formatCurrency(this.budgetAmount)}</div>
                            </div>
                            <div class="col-4">
                                <div class="detail-label">${_t('Spent')}</div>
                                <div class="detail-value">${this._formatCurrency(this.spentAmount)}</div>
                            </div>
                            <div class="col-4">
                                <div class="detail-label">${_t('Remaining')}</div>
                                <div class="detail-value ${this.budgetAmount - this.spentAmount < 0 ? 'text-danger' : ''}">
                                    ${this._formatCurrency(this.budgetAmount - this.spentAmount)}
                                </div>
                            </div>
                        </div>
                    </div>
                `;

                $content.html(html);
            } else {
                $content.html('<div class="text-muted">' + _t('No budget assigned') + '</div>');
            }

            this.$el.html($content);
        },

        /**
         * Format currency value
         */
        _formatCurrency: function (amount) {
            // This would use Odoo's currency formatting in a real implementation
            return amount.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        },

        /**
         * @override
         */
        _parseValue: function (value) {
            return value;
        },

        /**
         * @override
         */
        _formatValue: function (value) {
            return value;
        }
    });

    // Budget Utilization Field Widget
    var BudgetUtilization = AbstractField.extend({
        className: 'o_field_budget_utilization',
        supportedFieldTypes: ['float'],

        /**
         * @override
         */
        _render: function () {
            var utilization = this.value || 0;
            var statusClass = utilization >= 95 ? 'critical' : utilization >= 80 ? 'warning' : 'normal';
            var statusText = utilization >= 95 ? _t('Over Budget') :
                           utilization >= 80 ? _t('Near Limit') : _t('Within Budget');

            var html = `
                <div class="utilization-display">
                    <div class="utilization-bar">
                        <div class="utilization-fill ${statusClass}" style="width: ${Math.min(utilization, 100)}%"></div>
                    </div>
                    <div class="utilization-info">
                        <span class="utilization-value">${utilization.toFixed(1)}%</span>
                        <span class="utilization-status ${statusClass}">${statusText}</span>
                    </div>
                </div>
            `;

            this.$el.html(html);
        }
    });

    // Register the custom field widgets
    field_registry.add('budget_progress', BudgetProgress);
    field_registry.add('budget_utilization', BudgetUtilization);

    return {
        BudgetProgress: BudgetProgress,
        BudgetUtilization: BudgetUtilization,
    };
});