# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrTimesheetDashboardTemplates(TransactionCase):
    def test_create_from_template_timesheet_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_hr_timesheet.template_timesheet_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Timesheet Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("hr_timesheet.group_hr_timesheet_approver"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertEqual(len(dashboard.filter_ids), 3)
        self.assertTrue(
            all(
                item.model_name == "account.analytic.line"
                for item in dashboard.item_ids
            )
        )

        hours = dashboard.item_ids.filtered(lambda i: i.name == "Hours Logged")
        self.assertEqual(hours.aggregation, "sum")
        self.assertEqual(hours.measure_field_id.name, "unit_amount")
        self.assertTrue(hours.compare_previous_period)
        self.assertEqual(hours.date_field_id.name, "date")

        today = dashboard.item_ids.filtered(lambda i: i.name == "Today Hours")
        self.assertFalse(today.date_field_id)

        by_project = dashboard.item_ids.filtered(lambda i: i.name == "Hours by Project")
        self.assertEqual(by_project.item_type, "bar_horizontal")
        self.assertEqual(by_project.group_by_field_id.name, "project_id")

        share = dashboard.item_ids.filtered(
            lambda i: i.name == "Hours by Project Share"
        )
        self.assertEqual(share.item_type, "doughnut")
        self.assertEqual(share.group_by_field_id.name, "project_id")
        self.assertEqual(share.measure_field_id.name, "unit_amount")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Timesheets")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("employee_id", column_names)
        self.assertIn("project_id", column_names)
        self.assertIn("unit_amount", column_names)
        self.assertIn("task_id", column_names)
