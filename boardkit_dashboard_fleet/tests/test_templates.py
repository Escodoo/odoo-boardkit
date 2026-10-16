# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestFleetDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = ("boardkit_dashboard_fleet.template_fleet_overview",)

    def test_create_from_template_fleet_overview(self):
        template = self.env.ref("boardkit_dashboard_fleet.template_fleet_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Fleet Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("fleet.fleet_group_manager"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertFalse(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "fleet.vehicle" for item in dashboard.item_ids)
        )

        active = dashboard.item_ids.filtered(lambda i: i.name == "Active Vehicles")
        self.assertFalse(active.date_field_id)

        new_vehicles = dashboard.item_ids.filtered(lambda i: i.name == "New Vehicles")
        self.assertEqual(new_vehicles.date_field_id.name, "acquisition_date")
        self.assertTrue(new_vehicles.compare_previous_period)

        write_offs = dashboard.item_ids.filtered(lambda i: i.name == "Write-offs")
        self.assertEqual(write_offs.date_field_id.name, "write_off_date")

        active_rate = dashboard.item_ids.filtered(lambda i: i.name == "Active Rate")
        self.assertEqual(active_rate.kpi_mode, "comparison")
        self.assertEqual(active_rate.kpi_display, "percent")

        by_brand = dashboard.item_ids.filtered(lambda i: i.name == "Active by Brand")
        self.assertEqual(by_brand.item_type, "bar_horizontal")
        self.assertEqual(by_brand.group_by_field_id.name, "brand_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Vehicles")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("driver_id", column_names)
        self.assertIn("model_id", column_names)
        self.assertIn("license_plate", column_names)
        self.assertIn("state_id", column_names)
