odoo.define('expense_tracker_advanced.dashboard', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');
    var core = require('web.core');
    var _t = core._t;

    var ExpenseDashboardRenderer = FormRenderer.extend({
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._renderCharts();
                return self;
            });
        },

        _renderCharts: function () {
            // Check if Chart.js is available
            if (typeof Chart === 'undefined') {
                console.warn('Chart.js is not loaded.');
                return;
            }

            // Render Category Chart
            var categoryCtx = document.getElementById('categoryChart');
            if (categoryCtx) {
                new Chart(categoryCtx, {
                    type: 'pie',
                    data: {
                        labels: ['Office', 'Travel', 'Meals'],
                        datasets: [{
                            data: [300, 50, 100],
                            backgroundColor: [
                                'rgb