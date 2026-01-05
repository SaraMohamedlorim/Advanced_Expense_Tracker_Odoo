{
    'name': 'Advanced Expense Tracker',
    'version': '1.0.0',
    'category': 'Accounting/Finance',
    'summary': 'Comprehensive expense tracking and management system with advanced features',
    'description': """
Advanced Expense Tracker
========================

A complete expense management solution with budgeting, reporting, analytics, 
and accounting integration.

🌟 Key Features:
----------------
• Expense recording with advanced categorization
• Budget planning and real-time monitoring  
• Multi-level approval workflows
• Receipt attachment and management
• Multi-currency support
• Advanced reporting and analytics
• CSV import/export capabilities
• Budget alerts and notifications
• Accounting integration (vendor bills, payments)
• Mobile-friendly responsive interface
• Role-based security and access control
• Dashboard with visual analytics
• Recurring budget alerts
• Expense templates and bulk operations

📊 Advanced Capabilities:
-------------------------
• Real-time budget utilization tracking
• Automated approval workflows
• Vendor bill creation from expenses
• Advanced search and filtering
• Pivot tables and graphical reports
• Email and chat notifications
• Custom alert thresholds
• Data export in multiple formats
• Audit trail and activity logging
• Multi-company support

🔒 Security Features:
---------------------
• Role-based access control
• Record-level security rules
• Approval hierarchy
• Audit trails
• Data encryption

🛠 Technical Features:
----------------------
• REST API ready
• Web responsive design
• Modular architecture
• Easy customization
• Performance optimized
    """,

    'author': 'Sara Mohamed',
    'website': 'https://www.sara.com',
    'depends': [
        'base',
        'account',
        'mail',
        'web',
        'portal',
        'base_setup',
        'base_automation',
    ],

     'images': [
        'static/description/dollar.png',
    ],

    'icon': '/Advanced_Expense_Tracker/static/description/dollar.png',

    'data': [
        # Security
        'security/expense_security.xml',
        'security/ir.model.access.csv',

        # Data sequences
        'data/expense_sequence.xml',
        'data/expense_category_data.xml',
        # 'data/mail_template_data.xml',
        'data/action_rules.xml',



        # Views
        # 'views/menu_views.xml',
        'views/category_views.xml',
        'views/expense_views.xml',
        'views/budget_views.xml',
        'views/dashboard_views.xml',
        'views/menu_views.xml',
        



        # Reports
        'reports/expense_reports.xml',
        'reports/expense_templetes.xml',
        'reports/budget_reports.xml',

        # Wizards
        'wizards/expense_invoice_wizard.xml',
        'wizards/expense_import_wizard.xml',
        # 'wizards/budget_alert_wizard.xml',

        # # Actions
        # 'data/action_rules.xml',
    ],


    'assets': {
        'web.assets_backend': [
            # CSS Files
            'expense_tracker_advanced/static/src/css/dashboard.css',
            'expense_tracker_advanced/static/src/css/form_views.css',
            'expense_tracker_advanced/static/src/css/tree_views.css',

            # JS Files
            'expense_tracker_advanced/static/src/js/dashboard.js',
            'expense_tracker_advanced/static/src/js/expense_form.js',
            'expense_tracker_advanced/static/src/js/budget_progress.js',
            'expense_tracker_advanced/static/src/js/chart_rendering.js',

            # Libraries
            'expense_tracker_advanced/static/src/lib/chartjs/Chart.min.js',
        ],

        'web.assets_frontend': [
            'expense_tracker_advanced/static/src/css/portal.css',
        ],

        'web.assets_qweb': [
            'expense_tracker_advanced/static/src/xml/dashboard_templates.xml',
            'expense_tracker_advanced/static/src/xml/expense_templates.xml',
            'expense_tracker_advanced/static/src/xml/budget_templates.xml',
        ],
    },

   

    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',



}