# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectDashboardTemplates(TransactionCase):
    def test_create_from_template_project_overview(self):
        template = self.env.ref("boardkit_dashboard_project.template_project_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Project Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "project.task" for item in dashboard.item_ids)
        )

        open_tasks = dashboard.item_ids.filtered(lambda i: i.name == "Open Tasks")
        self.assertFalse(open_tasks.date_field_id)

        done = dashboard.item_ids.filtered(lambda i: i.name == "Done Tasks")
        self.assertEqual(done.date_field_id.name, "date_end")
        self.assertTrue(done.compare_previous_period)

        completion = dashboard.item_ids.filtered(lambda i: i.name == "Completion Rate")
        self.assertEqual(completion.kpi_mode, "comparison")
        self.assertEqual(completion.kpi_display, "percent")

        by_project = dashboard.item_ids.filtered(
            lambda i: i.name == "Open Tasks by Project"
        )
        self.assertEqual(by_project.item_type, "bar_horizontal")
        self.assertEqual(by_project.group_by_field_id.name, "project_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Tasks")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("project_id", column_names)
        self.assertIn("stage_id", column_names)
        self.assertIn("date_deadline", column_names)
        self.assertIn("priority", column_names)
