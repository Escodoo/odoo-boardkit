# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHolidaysDashboardTemplates(TransactionCase):
    def test_create_from_template_time_off_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_hr_holidays.template_time_off_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Time Off Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "hr.leave" for item in dashboard.item_ids)
        )

        to_approve = dashboard.item_ids.filtered(lambda i: i.name == "To Approve")
        self.assertFalse(to_approve.date_field_id)

        days_off = dashboard.item_ids.filtered(lambda i: i.name == "Days Off")
        self.assertEqual(days_off.aggregation, "sum")
        self.assertEqual(days_off.measure_field_id.name, "number_of_days")
        self.assertTrue(days_off.compare_previous_period)
        self.assertEqual(days_off.date_field_id.name, "date_from")

        approval = dashboard.item_ids.filtered(lambda i: i.name == "Approval Rate")
        self.assertEqual(approval.kpi_mode, "comparison")
        self.assertEqual(approval.kpi_display, "percent")

        by_type = dashboard.item_ids.filtered(lambda i: i.name == "Days by Type")
        self.assertEqual(by_type.item_type, "bar_horizontal")
        self.assertEqual(by_type.group_by_field_id.name, "holiday_status_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Requests")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("employee_id", column_names)
        self.assertIn("holiday_status_id", column_names)
        self.assertIn("number_of_days", column_names)
        self.assertIn("state", column_names)
