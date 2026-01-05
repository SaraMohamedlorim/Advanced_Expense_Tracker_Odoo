odoo.define('expense_tracker_advanced.chart_rendering', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var utils = require('web.utils');
    var _t = core._t;

    // Base Chart Widget
    var BaseChart = Widget.extend({
        template: 'BaseChart',
        chart: null,

        init: function (parent, options) {
            this._super(parent);
            this.options = options || {};
            this.data = this.options.data || {};
            this.config = this.options.config || {};
        },

        start: function () {
            var self = this;
            return this._super().then(function () {
                self._renderChart();
                return self;
            });
        },

        _renderChart: function () {
            // To be implemented by child classes
        },

        updateData: function (newData) {
            this.data = newData;
            if (this.chart) {
                this.chart.data = this._processData(newData);
                this.chart.update();
            }
        },

        _processData: function (data) {
            return data;
        },

        destroy: function () {
            if (this.chart) {
                this.chart.destroy();
            }
            this._super();
        }
    });

    // Pie Chart Widget
    var PieChart = BaseChart.extend({
        template: 'PieChart',

        _renderChart: function () {
            if (typeof Chart === 'undefined') {
                console.warn('Chart.js not loaded');
                return;
            }

            var ctx = this.$el.find('canvas')[0];
            if (!ctx) return;

            var processedData = this._processData(this.data);

            this.chart = new Chart(ctx, {
                type: 'pie',
                data: processedData,
                options: _.extend({
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    var label = context.label || '';
                                    var value = context.raw || 0;
                                    var total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    var percentage = Math.round((value / total) * 100);
                                    return `${label}: ${utils.format.currency(value, null, {})} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }, this.config)
            });
        },

        _processData: function (data) {
            return {
                labels: data.labels || [],
                datasets: [{
                    data: data.values || [],
                    backgroundColor: data.colors || [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                        '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            };
        }
    });

    // Bar Chart Widget
    var BarChart = BaseChart.extend({
        template: 'BarChart',

        _renderChart: function () {
            if (typeof Chart === 'undefined') return;

            var ctx = this.$el.find('canvas')[0];
            if (!ctx) return;

            var processedData = this._processData(this.data);

            this.chart = new Chart(ctx, {
                type: 'bar',
                data: processedData,
                options: _.extend({
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }, this.config)
            });
        },

        _processData: function (data) {
            return {
                labels: data.labels || [],
                datasets: [{
                    label: data.label || _t('Values'),
                    data: data.values || [],
                    backgroundColor: data.backgroundColor || '#714B67',
                    borderColor: data.borderColor || '#5a3a52',
                    borderWidth: 1
                }]
            };
        }
    });

    // Line Chart Widget
    var LineChart = BaseChart.extend({
        template: 'LineChart',

        _renderChart: function () {
            if (typeof Chart === 'undefined') return;

            var ctx = this.$el.find('canvas')[0];
            if (!ctx) return;

            var processedData = this._processData(this.data);

            this.chart = new Chart(ctx, {
                type: 'line',
                data: processedData,
                options: _.extend({
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    elements: {
                        line: {
                            tension: 0.4
                        }
                    }
                }, this.config)
            });
        },

        _processData: function (data) {
            return {
                labels: data.labels || [],
                datasets: data.datasets || [{
                    label: data.label || _t('Values'),
                    data: data.values || [],
                    borderColor: data.borderColor || '#714B67',
                    backgroundColor: data.backgroundColor || 'rgba(113, 75, 103, 0.1)',
                    fill: true
                }]
            };
        }
    });

    // Chart Manager
    var ChartManager = Widget.extend({
        init: function (parent, chartsConfig) {
            this._super(parent);
            this.chartsConfig = chartsConfig || {};
            this.charts = {};
        },

        start: function () {
            var self = this;
            return this._super().then(function () {
                self._initializeCharts();
                return self;
            });
        },

        _initializeCharts: function () {
            var self = this;

            _.each(this.chartsConfig, function (config, chartId) {
                var $container = self.$el.find('#' + chartId);
                if ($container.length) {
                    self.charts[chartId] = self._createChart(config.type, config);
                }
            });
        },

        _createChart: function (type, config) {
            var chart;

            switch (type) {
                case 'pie':
                    chart = new PieChart(this, config);
                    break;
                case 'bar':
                    chart = new BarChart(this, config);
                    break;
                case 'line':
                    chart = new LineChart(this, config);
                    break;
                default:
                    console.warn('Unknown chart type:', type);
                    return null;
            }

            chart.appendTo(this.$el.find('#' + config.container));
            return chart;
        },

        updateChart: function (chartId, data) {
            var chart = this.charts[chartId];
            if (chart) {
                chart.updateData(data);
            }
        },

        refreshAll: function () {
            var self = this;
            return this._rpc({
                model: 'expense.tracker',
                method: 'get_chart_data',
                args: [{}]
            }).then(function (data) {
                _.each(self.charts, function (chart, chartId) {
                    if (data[chartId]) {
                        chart.updateData(data[chartId]);
                    }
                });
            });
        },

        destroy: function () {
            _.each(this.charts, function (chart) {
                if (chart) {
                    chart.destroy();
                }
            });
            this._super();
        }
    });

    // Utility functions for chart data processing
    var ChartUtils = {
        processExpenseByCategory: function (expenseData) {
            var categories = {};

            _.each(expenseData, function (expense) {
                var category = expense.category_id[1];
                var amount = expense.amount;

                if (categories[category]) {
                    categories[category] += amount;
                } else {
                    categories[category] = amount;
                }
            });

            return {
                labels: Object.keys(categories),
                values: Object.values(categories)
            };
        },

        processMonthlyTrend: function (expenseData) {
            var monthlyData = {};

            _.each(expenseData, function (expense) {
                var date = new Date(expense.date);
                var monthKey = date.getFullYear() + '-' + (date.getMonth() + 1).toString().padStart(2, '0');

                if (monthlyData[monthKey]) {
                    monthlyData[monthKey] += expense.amount;
                } else {
                    monthlyData[monthKey] = expense.amount;
                }
            });

            // Sort by date
            var sortedMonths = Object.keys(monthlyData).sort();
            var labels = sortedMonths.map(function (month) {
                var [year, monthNum] = month.split('-');
                return new Date(year, monthNum - 1).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short'
                });
            });

            return {
                labels: labels,
                values: sortedMonths.map(function (month) { return monthlyData[month]; })
            };
        },

        generateColors: function (count) {
            var baseColors = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
                '#8AC926', '#1982C4', '#6A4C93', '#F15BB5'
            ];

            var colors = [];
            for (var i = 0; i < count; i++) {
                colors.push(baseColors[i % baseColors.length]);
            }
            return colors;
        }
    };

    return {
        BaseChart: BaseChart,
        PieChart: PieChart,
        BarChart: BarChart,
        LineChart: LineChart,
        ChartManager: ChartManager,
        ChartUtils: ChartUtils
    };
});