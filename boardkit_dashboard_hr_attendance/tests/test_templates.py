# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestAttendanceDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = ("boardkit_dashboard_hr_attendance.template_attendance_overview",)

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
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("hr_attendance.group_hr_attendance_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "kpi"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        # Odoo 16 keeps overtime in its own per-day model.
        self.assertEqual(
            set(dashboard.item_ids.mapped("model_name")),
            {"hr.attendance", "hr.attendance.overtime"},
        )

        checked_in = dashboard.item_ids.filtered(lambda i: i.name == "Checked In Now")
        self.assertFalse(checked_in.date_field_id)

        hours = dashboard.item_ids.filtered(lambda i: i.name == "Hours Worked")
        self.assertEqual(hours.aggregation, "sum")
        self.assertEqual(hours.measure_field_id.name, "worked_hours")
        self.assertTrue(hours.compare_previous_period)
        self.assertEqual(hours.date_field_id.name, "check_in")

        overtime = dashboard.item_ids.filtered(lambda i: i.name == "Overtime Hours")
        self.assertEqual(overtime.model_name, "hr.attendance.overtime")
        self.assertEqual(overtime.measure_field_id.name, "duration")
        # Missing time is stored as negative overtime and would offset the sum.
        self.assertIn("('duration', '>', 0)", overtime.domain)

        missing = dashboard.item_ids.filtered(lambda i: i.name == "Missing Hours")
        self.assertIn("('duration', '<', 0)", missing.domain)

        # department_id is not stored on hr.attendance in Odoo 16.
        weekly = dashboard.item_ids.filtered(lambda i: i.name == "Hours per Week")
        self.assertEqual(weekly.group_by_field_id.name, "check_in")
        self.assertEqual(weekly.group_by_granularity, "week")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Attendances")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("employee_id", column_names)
        self.assertIn("check_in", column_names)
        self.assertIn("worked_hours", column_names)
