# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMaintenanceDashboardTemplates(TransactionCase):
    def test_create_from_template_maintenance_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_maintenance.template_maintenance_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Maintenance Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("maintenance.group_equipment_manager"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "maintenance.request" for item in dashboard.item_ids)
        )

        open_req = dashboard.item_ids.filtered(lambda i: i.name == "Open Requests")
        self.assertFalse(open_req.date_field_id)

        done = dashboard.item_ids.filtered(lambda i: i.name == "Done Requests")
        self.assertEqual(done.date_field_id.name, "close_date")
        self.assertTrue(done.compare_previous_period)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Completion Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")

        funnel = dashboard.item_ids.filtered(lambda i: i.name == "Pipeline Funnel")
        self.assertEqual(funnel.item_type, "funnel")
        self.assertEqual(funnel.group_by_field_id.name, "stage_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Requests")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("equipment_id", column_names)
        self.assertIn("stage_id", column_names)
        self.assertIn("maintenance_type", column_names)
        self.assertIn("user_id", column_names)
