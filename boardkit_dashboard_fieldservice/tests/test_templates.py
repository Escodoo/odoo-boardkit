# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFieldServiceDashboardTemplates(TransactionCase):
    def test_create_from_template_fieldservice_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_fieldservice.template_fieldservice_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Field Service Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("fieldservice.group_fsm_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 14)
        maps = dashboard.item_ids.filtered(lambda i: i.item_type == "map")
        self.assertTrue(maps)
        points = maps.filtered(lambda i: i.map_mode == "points")
        self.assertTrue(points)
        self.assertEqual(points[:1].latitude_field_id.name, "partner_latitude")
        self.assertEqual(points[:1].longitude_field_id.name, "partner_longitude")
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(
                item.model_name in ("fsm.order", "fsm.location")
                for item in dashboard.item_ids
            )
        )
        self.assertTrue(
            dashboard.item_ids.filtered(lambda i: i.name == "Locations without Geo")
        )

        open_orders = dashboard.item_ids.filtered(lambda i: i.name == "Open Orders")
        self.assertFalse(open_orders.date_field_id)

        completed = dashboard.item_ids.filtered(lambda i: i.name == "Completed Orders")
        self.assertEqual(completed.date_field_id.name, "date_end")
        self.assertTrue(completed.compare_previous_period)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Completion Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")

        funnel = dashboard.item_ids.filtered(lambda i: i.name == "Pipeline Funnel")
        self.assertEqual(funnel.item_type, "funnel")
        self.assertEqual(funnel.group_by_field_id.name, "stage_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Orders")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("team_id", column_names)
        self.assertIn("stage_id", column_names)
        self.assertIn("person_id", column_names)
        self.assertIn("priority", column_names)
