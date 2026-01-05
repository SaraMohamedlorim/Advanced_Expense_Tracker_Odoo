from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import csv
import base64
import io
from datetime import datetime


class ExpenseImportWizard(models.TransientModel):
    _name = 'expense.import.wizard'
    _description = 'Import Expenses from CSV Wizard'

    csv_file = fields.Binary(string='CSV File', required=True)
    filename = fields.Char(string='Filename')
    import_type = fields.Selection([
        ('create', 'Create New Expenses'),
        ('update', 'Update Existing Expenses')
    ], string='Import Type', default='create', required=True)

    # Mapping fields
    title_column = fields.Char(string='Title Column', default='title', required=True)
    amount_column = fields.Char(string='Amount Column', default='amount', required=True)
    category_column = fields.Char(string='Category Column', default='category', required=True)
    date_column = fields.Char(string='Date Column', default='date', required=True)
    description_column = fields.Char(string='Description Column', default='description')

    # Options
    date_format = fields.Selection([
        ('%Y-%m-%d', 'YYYY-MM-DD'),
        ('%m/%d/%Y', 'MM/DD/YYYY'),
        ('%d/%m/%Y', 'DD/MM/YYYY'),
        ('%d-%m-%Y', 'DD-MM-YYYY'),
    ], string='Date Format', default='%Y-%m-%d', required=True)

    delimiter = fields.Selection([
        (',', 'Comma (,)'),
        (';', 'Semicolon (;)'),
        ('\t', 'Tab')
    ], string='Delimiter', default=',', required=True)

    # Results
    import_result = fields.Text(string='Import Result', readonly=True)
    total_records = fields.Integer(string='Total Records', readonly=True)
    successful_imports = fields.Integer(string='Successful Imports', readonly=True)
    failed_imports = fields.Integer(string='Failed Imports', readonly=True)

    def _parse_csv_file(self):
        """Parse the uploaded CSV file and return the data"""
        self.ensure_one()

        if not self.csv_file:
            raise UserError(_("Please upload a CSV file first."))

        try:
            csv_data = base64.b64decode(self.csv_file).decode('utf-8')
            csv_file = io.StringIO(csv_data)

            # Try to detect dialect
            sample = csv_data[:1024]
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)

            reader = csv.DictReader(csv_file, delimiter=self.delimiter)
            records = list(reader)

            if not records:
                raise UserError(_("The CSV file appears to be empty or has no valid data."))

            return records

        except Exception as e:
            raise UserError(_("Error reading CSV file: %s") % str(e))

    def _validate_record(self, record):
        """Validate a single record from CSV"""
        errors = []

        # Check required fields
        if not record.get(self.title_column):
            errors.append(_("Title is required"))

        if not record.get(self.amount_column):
            errors.append(_("Amount is required"))
        else:
            try:
                float(record[self.amount_column])
            except ValueError:
                errors.append(_("Amount must be a valid number"))

        if not record.get(self.category_column):
            errors.append(_("Category is required"))

        if not record.get(self.date_column):
            errors.append(_("Date is required"))
        else:
            try:
                datetime.strptime(record[self.date_column], self.date_format)
            except ValueError:
                errors.append(_("Date format is invalid. Expected: %s") % self.date_format)

        return errors

    def _get_or_create_category(self, category_name):
        """Get existing category or create a new one"""
        category = self.env['expense.category'].search([
            ('name', '=ilike', category_name.strip())
        ], limit=1)

        if not category:
            category = self.env['expense.category'].create({
                'name': category_name.strip(),
                'code': category_name.strip()[:10].upper()
            })

        return category

    def _create_expense_from_record(self, record):
        """Create an expense record from CSV data"""
        # Parse date
        date_str = record[self.date_column]
        date_obj = datetime.strptime(date_str, self.date_format).date()

        # Get or create category
        category = self._get_or_create_category(record[self.category_column])

        # Create expense
        expense_vals = {
            'title': record[self.title_column].strip(),
            'amount': float(record[self.amount_column]),
            'category_id': category.id,
            'date': date_obj,
            'state': 'draft',
            'user_id': self.env.user.id,
        }

        # Add description if available
        if self.description_column and record.get(self.description_column):
            expense_vals['description'] = record[self.description_column].strip()

        return self.env['expense.tracker'].create(expense_vals)

    def _update_expense_from_record(self, record):
        """Update existing expense record from CSV data"""
        # This would require a unique identifier in the CSV
        # For simplicity, we'll use title + date as identifier
        title = record[self.title_column].strip()
        date_str = record[self.date_column]
        date_obj = datetime.strptime(date_str, self.date_format).date()

        expense = self.env['expense.tracker'].search([
            ('title', '=', title),
            ('date', '=', date_obj)
        ], limit=1)

        if expense:
            category = self._get_or_create_category(record[self.category_column])

            update_vals = {
                'amount': float(record[self.amount_column]),
                'category_id': category.id,
            }

            if self.description_column and record.get(self.description_column):
                update_vals['description'] = record[self.description_column].strip()

            expense.write(update_vals)
            return expense
        else:
            return None

    def action_preview_import(self):
        """Preview the import data before actual import"""
        self.ensure_one()

        records = self._parse_csv_file()
        preview_data = []

        for i, record in enumerate(records[:10]):  # Show first 10 records
            errors = self._validate_record(record)
            preview_data.append({
                'line_number': i + 2,  # +2 because of header and 1-based indexing
                'title': record.get(self.title_column, ''),
                'amount': record.get(self.amount_column, ''),
                'category': record.get(self.category_column, ''),
                'date': record.get(self.date_column, ''),
                'errors': errors,
                'is_valid': len(errors) == 0
            })

        # Return action to show preview
        return {
            'type': 'ir.actions.act_window',
            'name': _('Import Preview'),
            'res_model': 'expense.import.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_import_wizard_id': self.id,
                'default_preview_data': str(preview_data),
            }
        }

    def action_import(self):
        """Perform the actual import"""
        self.ensure_one()

        records = self._parse_csv_file()
        results = {
            'successful': [],
            'failed': []
        }

        for i, record in enumerate(records):
            line_number = i + 2  # +2 because of header and 1-based indexing

            try:
                # Validate record
                errors = self._validate_record(record)
                if errors:
                    results['failed'].append({
                        'line_number': line_number,
                        'record': record,
                        'errors': errors
                    })
                    continue

                # Create or update expense
                if self.import_type == 'create':
                    expense = self._create_expense_from_record(record)
                    results['successful'].append({
                        'line_number': line_number,
                        'expense': expense,
                        'action': 'created'
                    })
                else:
                    expense = self._update_expense_from_record(record)
                    if expense:
                        results['successful'].append({
                            'line_number': line_number,
                            'expense': expense,
                            'action': 'updated'
                        })
                    else:
                        results['failed'].append({
                            'line_number': line_number,
                            'record': record,
                            'errors': [_("No matching expense found to update")]
                        })

            except Exception as e:
                results['failed'].append({
                    'line_number': line_number,
                    'record': record,
                    'errors': [str(e)]
                })

        # Update results
        self.write({
            'total_records': len(records),
            'successful_imports': len(results['successful']),
            'failed_imports': len(results['failed']),
            'import_result': self._format_import_result(results)
        })

        # Show result summary
        if results['failed']:
            message = _(
                "Import completed with some errors.\n\n"
                "Successful: %(success)d\n"
                "Failed: %(failed)d\n"
                "Total: %(total)d"
            ) % {
                          'success': len(results['successful']),
                          'failed': len(results['failed']),
                          'total': len(records)
            }
        else:
            message = _(
                "Import completed successfully!\n\n"
                "Imported: %(count)d expenses"
            ) % {'count': len(results['successful'])}
            message_type = 'success'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Result'),
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }

    def _format_import_result(self, results):
        """Format the import results as text"""
        lines = []

        lines.append(_("IMPORT RESULTS"))
        lines.append("=" * 50)
        lines.append(_("Total records processed: %d") % self.total_records)
        lines.append(_("Successful: %d") % len(results['successful']))
        lines.append(_("Failed: %d") % len(results['failed']))
        lines.append("")

        if results['failed']:
            lines.append(_("FAILED RECORDS:"))
            lines.append("-" * 30)
            for failed in results['failed']:
                lines.append(_("Line %d:") % failed['line_number'])
                lines.append("  - %s: %s" % (self.title_column, failed['record'].get(self.title_column, '')))
                for error in failed['errors']:
                    lines.append("  - ERROR: %s" % error)

        if results['successful']:
            lines.append(_("SUCCESSFUL RECORDS:"))
            lines.append("-" * 30)
            for success in results['successful'][:20]:  # Show first 20 successful
                lines.append(_("Line %d: %s (%s)") % (
                    success['line_number'],
                    success['expense'].title,
                    success['action']
                ))

            if len(results['successful']) > 20:
                lines.append(_("... and %d more") % (len(results['successful']) - 20))

        return "\n".join(lines)

    def download_template(self):
        """Download a CSV template file"""
        template_data = [
            ['title', 'amount', 'category', 'date', 'description'],
            ['Office Supplies', '150.50', 'Office', '2024-01-15', 'Purchase of stationery'],
            ['Client Lunch', '85.00', 'Entertainment', '2024-01-16', 'Business meeting'],
            ['Software Subscription', '299.00', 'Software', '2024-01-17', 'Annual subscription'],
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(template_data)

        template_content = output.getvalue().encode('utf-8')
        output.close()

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=%(model)s&id=%(id)s&field=csv_file&filename_field=filename&download=true' % {
                'model': self._name,
                'id': self.id,
            },
            'target': 'self',
        }