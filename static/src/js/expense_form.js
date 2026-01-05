odoo.define('expense_tracker_advanced.expense_form', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');
    var field_utils = require('web.field_utils');
    var core = require('web.core');
    var _t = core._t;

    // Expense Form Controller
    var ExpenseFormController = FormController.extend({
        custom_events: _.extend({}, FormController.prototype.custom_events, {
            'receipt_uploaded': '_onReceiptUploaded',
            'category_changed': '_onCategoryChanged',
            'amount_changed': '_onAmountChanged',
        }),

        /**
         * @override
         */
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.budgetData = {};
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
         * Load budget data for the current user/company
         */
        _loadBudgetData: function () {
            var self = this;
            return this._rpc({
                model: 'expense.budget',
                method: 'get_available_budgets',
                args: [this.renderer.state.context]
            }).then(function (data) {
                self.budgetData = data;
                return data;
            });
        },

        /**
         * Handle receipt upload event
         */
        _onReceiptUploaded: function (event) {
            var file = event.data.file;
            var $preview = this.$el.find('.receipt-preview-container');

            if (file) {
                var reader = new FileReader();
                reader.onload = function (e) {
                    $preview.html(
                        '<img src="' + e.target.result + '" class="receipt-preview-image" alt="Receipt Preview"/>' +
                        '<div class="mt-2">' + file.name + '</div>'
                    );
                };
                reader.readAsDataURL(file);
            }
        },

        /**
         * Handle category change event
         */
        _onCategoryChanged: function (event) {
            var categoryId = event.data.categoryId;
            this._updateBudgetSuggestions(categoryId);
        },

        /**
         * Handle amount change event
         */
        _onAmountChanged: function (event) {
            var amount = event.data.amount;
            this._checkBudgetLimits(amount);
        },

        /**
         * Update budget suggestions based on selected category
         */
        _updateBudgetSuggestions: function (categoryId) {
            var $budgetField = this.$el.find('.o_field_widget[name="budget_id"]');
            var budgets = this.budgetData[categoryId] || [];

            // Update budget field options
            if (budgets.length === 1) {
                // Auto-select if only one budget available
                this.renderer.trigger('field_changed', {
                    dataPointID: this.renderer.state.id,
                    changes: { budget_id: budgets[0].id }
                });
            }

            // Show budget information
            this._displayBudgetInfo(categoryId);
        },

        /**
         * Display budget information for the selected category
         */
        _displayBudgetInfo: function (categoryId) {
            var $budgetInfo = this.$el.find('.budget-progress-container');
            var budgets = this.budgetData[categoryId] || [];

            if (budgets.length > 0) {
                var budget = budgets[0]; // Show first active budget
                var utilization = (budget.spent_amount / budget.amount) * 100;

                var html = `
                    <div class="budget-progress-header">
                        <h4 class="budget-progress-title">${_t('Budget:')} ${budget.name}</h4>
                        <span class="budget-progress-percentage">${utilization.toFixed(1)}%</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar-background">
                            <div class="progress-bar-fill ${utilization >= 95 ? 'critical' : utilization >= 80 ? 'warning' : 'normal'}"
                                 style="width: ${Math.min(utilization, 100)}%">
                            </div>
                            <div class="progress-bar-text">${utilization.toFixed(1)}%</div>
                        </div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-4">
                            <small class="text-muted">${_t('Budget:')}</small><br>
                            <strong>${field_utils.format.float(budget.amount)}</strong>
                        </div>
                        <div class="col-4">
                            <small class="text-muted">${_t('Spent:')}</small><br>
                            <strong>${field_utils.format.float(budget.spent_amount)}</strong>
                        </div>
                        <div class="col-4">
                            <small class="text-muted">${_t('Remaining:')}</small><br>
                            <strong>${field_utils.format.float(budget.remaining_amount)}</strong>
                        </div>
                    </div>
                `;

                $budgetInfo.html(html).show();
            } else {
                $budgetInfo.hide();
            }
        },

        /**
         * Check budget limits and show warnings
         */
        _checkBudgetLimits: function (amount) {
            var categoryId = this.renderer.state.data.category_id && this.renderer.state.data.category_id[0];
            if (!categoryId) return;

            var budgets = this.budgetData[categoryId] || [];
            if (budgets.length === 0) return;

            var budget = budgets[0];
            var newTotal = budget.spent_amount + amount;
            var newUtilization = (newTotal / budget.amount) * 100;

            if (newUtilization >= 100) {
                this._showBudgetWarning(_t('This expense will exceed the budget limit!'), 'danger');
            } else if (newUtilization >= 95) {
                this._showBudgetWarning(_t('This expense will bring budget utilization to over 95%'), 'warning');
            } else if (newUtilization >= 80) {
                this._showBudgetWarning(_t('This expense will bring budget utilization to over 80%'), 'info');
            } else {
                this._hideBudgetWarning();
            }
        },

        /**
         * Show budget warning message
         */
        _showBudgetWarning: function (message, type) {
            var $warning = this.$el.find('.budget-warning');
            if ($warning.length === 0) {
                $warning = $('<div class="budget-warning alert"></div>');
                this.$el.find('.o_form_sheet').prepend($warning);
            }

            $warning.removeClass('alert-info alert-warning alert-danger')
                   .addClass('alert-' + type)
                   .html('<i class="fa fa-exclamation-triangle mr-2"></i>' + message)
                   .show();
        },

        /**
         * Hide budget warning message
         */
        _hideBudgetWarning: function () {
            this.$el.find('.budget-warning').hide();
        },

        /**
         * @override
         */
        _onSave: function () {
            // Perform additional validation before saving
            if (this._validateExpense()) {
                return this._super.apply(this, arguments);
            }
            return $.Deferred().reject();
        },

        /**
         * Validate expense data before saving
         */
        _validateExpense: function () {
            var data = this.renderer.state.data;
            var errors = [];

            // Check required fields
            if (!data.title || data.title.trim() === '') {
                errors.push(_t('Title is required'));
            }

            if (!data.amount || data.amount <= 0) {
                errors.push(_t('Amount must be greater than 0'));
            }

            if (!data.category_id) {
                errors.push(_t('Category is required'));
            }

            if (!data.date) {
                errors.push(_t('Date is required'));
            }

            // Show errors if any
            if (errors.length > 0) {
                this.do_warn(_t('Validation Error'), errors.join('\n'));
                return false;
            }

            return true;
        },

        /**
         * Custom action handlers
         */
        _onAction: function (event) {
            var action = event.data.attr;

            switch (action) {
                case 'action_submit':
                    this._onSubmitExpense();
                    break;
                case 'action_approve':
                    this._onApproveExpense();
                    break;
                case 'action_reject':
                    this._onRejectExpense();
                    break;
                case 'action_mark_paid':
                    this._onMarkPaid();
                    break;
                default:
                    this._super.apply(this, arguments);
            }
        },

        /**
         * Submit expense for approval
         */
        _onSubmitExpense: function () {
            var self = this;
            this._rpc({
                model: 'expense.tracker',
                method: 'action_submit',
                args: [[this.renderer.state.res_id]]
            }).then(function () {
                self.trigger_up('reload');
                self.do_notify(_t('Success'), _t('Expense submitted for approval'));
            });
        },

        /**
         * Approve expense
         */
        _onApproveExpense: function () {
            var self = this;
            this._rpc({
                model: 'expense.tracker',
                method: 'action_approve',
                args: [[this.renderer.state.res_id]]
            }).then(function () {
                self.trigger_up('reload');
                self.do_notify(_t('Success'), _t('Expense approved'));
            });
        },

        /**
         * Reject expense
         */
        _onRejectExpense: function () {
            var self = this;
            this._rpc({
                model: 'expense.tracker',
                method: 'action_reject',
                args: [[this.renderer.state.res_id]]
            }).then(function () {
                self.trigger_up('reload');
                self.do_notify(_t('Success'), _t('Expense rejected'));
            });
        },

        /**
         * Mark expense as paid
         */
        _onMarkPaid: function () {
            var self = this;
            this._rpc({
                model: 'expense.tracker',
                method: 'action_mark_paid',
                args: [[this.renderer.state.res_id]]
            }).then(function () {
                self.trigger_up('reload');
                self.do_notify(_t('Success'), _t('Expense marked as paid'));
            });
        }
    });

    // Expense Form Renderer
    var ExpenseFormRenderer = FormRenderer.extend({
        events: _.extend({}, FormRenderer.prototype.events, {
            'change .o_field_widget[name="category_id"]': '_onCategoryChange',
            'change .o_field_widget[name="amount"]': '_onAmountChange',
            'change .receipt-upload input': '_onReceiptUpload',
        }),

        /**
         * @override
         */
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
        },

        /**
         * Handle category change
         */
        _onCategoryChange: function (event) {
            var categoryId = $(event.target).val();
            this.trigger('category_changed', { categoryId: categoryId });
        },

        /**
         * Handle amount change
         */
        _onAmountChange: function (event) {
            var amount = parseFloat($(event.target).val()) || 0;
            this.trigger('amount_changed', { amount: amount });
        },

        /**
         * Handle receipt upload
         */
        _onReceiptUpload: function (event) {
            var file = event.target.files[0];
            if (file) {
                this.trigger('receipt_uploaded', { file: file });
            }
        },

        /**
         * @override
         */
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._enhanceFormUI();
                return self;
            });
        },

        /**
         * Enhance form UI with custom styling and behaviors
         */
        _enhanceFormUI: function () {
            // Add custom classes to fields
            this.$el.find('.o_field_widget[name="amount"]').addClass('amount-field');

            // Enhance status bar
            this._enhanceStatusBar();

            // Setup receipt upload area
            this._setupReceiptUpload();
        },

        /**
         * Enhance status bar with custom styling
         */
        _enhanceStatusBar: function () {
            var $statusBar = this.$el.find('.o_statusbar_status');
            $statusBar.find('.btn').addClass('status-action-btn');
        },

        /**
         * Setup receipt upload area with drag and drop
         */
        _setupReceiptUpload: function () {
            var $uploadArea = this.$el.find('.receipt-upload-area');
            var $fileInput = this.$el.find('.receipt-upload input[type="file"]');

            if ($uploadArea.length && $fileInput.length) {
                // Drag and drop functionality
                $uploadArea.on('dragover', function (e) {
                    e.preventDefault();
                    $(this).addClass('dragover');
                });

                $uploadArea.on('dragleave', function (e) {
                    e.preventDefault();
                    $(this).removeClass('dragover');
                });

                $uploadArea.on('drop', function (e) {
                    e.preventDefault();
                    $(this).removeClass('dragover');
                    var files = e.originalEvent.dataTransfer.files;
                    if (files.length > 0) {
                        $fileInput[0].files = files;
                        $fileInput.trigger('change');
                    }
                });

                // Click to upload
                $uploadArea.on('click', function () {
                    $fileInput.trigger('click');
                });
            }
        }
    });

    // Register the custom components
    FormView.include({
        config: _.extend({}, FormView.prototype.config, {
            Controller: ExpenseFormController,
            Renderer: ExpenseFormRenderer,
        }),
    });

    return {
        ExpenseFormController: ExpenseFormController,
        ExpenseFormRenderer: ExpenseFormRenderer,
    };
});