# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrDashboardTemplates(TransactionCase):
    def test_create_from_template_employees_overview(self):
        template = self.env.ref("boardkit_dashboard_hr.template_employees_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Employees Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("hr.group_hr_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        maps = dashboard.item_ids.filtered(lambda i: i.item_type == "map")
        self.assertTrue(maps)
        regions = maps.filtered(lambda i: i.map_mode == "regions")
        self.assertTrue(regions)
        self.assertEqual(regions[:1].group_by_field_id.name, "country_id")
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "hr.employee" for item in dashboard.item_ids)
        )

        active = dashboard.item_ids.filtered(lambda i: i.name == "Active Employees")
        self.assertFalse(active.date_field_id)

        new_hires = dashboard.item_ids.filtered(lambda i: i.name == "New Hires")
        self.assertEqual(new_hires.date_field_id.name, "create_date")
        self.assertTrue(new_hires.compare_previous_period)

        departures = dashboard.item_ids.filtered(lambda i: i.name == "Departures")
        self.assertEqual(departures.date_field_id.name, "departure_date")

        active_rate = dashboard.item_ids.filtered(lambda i: i.name == "Active Rate")
        self.assertEqual(active_rate.kpi_mode, "comparison")
        self.assertEqual(active_rate.kpi_display, "percent")

        by_dept = dashboard.item_ids.filtered(
            lambda i: i.name == "Active by Department"
        )
        self.assertEqual(by_dept.item_type, "bar_horizontal")
        self.assertEqual(by_dept.group_by_field_id.name, "department_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Employees")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("department_id", column_names)
        self.assertIn("job_id", column_names)
        self.assertIn("parent_id", column_names)
        self.assertIn("employee_type", column_names)
