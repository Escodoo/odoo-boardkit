# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestExpenseDashboardTemplates(TransactionCase):
    def test_create_from_template_expenses_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_hr_expense.template_expenses_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Expenses Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("hr_expense.group_hr_expense_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "hr.expense" for item in dashboard.item_ids)
        )

        to_report = dashboard.item_ids.filtered(lambda i: i.name == "To Report")
        self.assertFalse(to_report.date_field_id)

        approved = dashboard.item_ids.filtered(lambda i: i.name == "Approved Amount")
        self.assertEqual(approved.aggregation, "sum")
        self.assertEqual(approved.measure_field_id.name, "total_amount")
        self.assertEqual(approved.unit_type, "monetary")
        self.assertTrue(approved.compare_previous_period)
        self.assertEqual(approved.date_field_id.name, "date")

        approval = dashboard.item_ids.filtered(lambda i: i.name == "Approval Rate")
        self.assertEqual(approval.kpi_mode, "comparison")
        self.assertEqual(approval.kpi_display, "percent")

        by_cat = dashboard.item_ids.filtered(lambda i: i.name == "Amount by Category")
        self.assertEqual(by_cat.item_type, "bar_horizontal")
        self.assertEqual(by_cat.group_by_field_id.name, "product_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Expenses")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("employee_id", column_names)
        self.assertIn("total_amount", column_names)
        self.assertIn("state", column_names)
        self.assertIn("payment_mode", column_names)
