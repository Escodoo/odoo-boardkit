# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAttendanceDashboardTemplates(TransactionCase):
    def test_create_from_template_attendance_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_hr_attendance.template_attendance_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Attendance Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "hr.attendance" for item in dashboard.item_ids)
        )

        checked_in = dashboard.item_ids.filtered(lambda i: i.name == "Checked In Now")
        self.assertFalse(checked_in.date_field_id)

        hours = dashboard.item_ids.filtered(lambda i: i.name == "Hours Worked")
        self.assertEqual(hours.aggregation, "sum")
        self.assertEqual(hours.measure_field_id.name, "worked_hours")
        self.assertTrue(hours.compare_previous_period)
        self.assertEqual(hours.date_field_id.name, "check_in")

        overtime = dashboard.item_ids.filtered(lambda i: i.name == "Overtime Hours")
        self.assertEqual(overtime.measure_field_id.name, "overtime_hours")

        by_dept = dashboard.item_ids.filtered(lambda i: i.name == "Hours by Department")
        self.assertEqual(by_dept.item_type, "bar_horizontal")
        self.assertEqual(by_dept.group_by_field_id.name, "department_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Attendances")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("employee_id", column_names)
        self.assertIn("check_in", column_names)
        self.assertIn("worked_hours", column_names)
        self.assertIn("overtime_hours", column_names)
