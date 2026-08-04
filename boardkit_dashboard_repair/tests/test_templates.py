# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRepairDashboardTemplates(TransactionCase):
    def test_create_from_template_repair_overview(self):
        template = self.env.ref("boardkit_dashboard_repair.template_repair_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Repair Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("stock.group_stock_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "repair.order" for item in dashboard.item_ids)
        )

        open_orders = dashboard.item_ids.filtered(lambda i: i.name == "Open Orders")
        self.assertFalse(open_orders.date_field_id)

        repaired = dashboard.item_ids.filtered(lambda i: i.name == "Repaired")
        self.assertEqual(repaired.date_field_id.name, "schedule_date")
        self.assertTrue(repaired.compare_previous_period)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Repair Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")

        by_product = dashboard.item_ids.filtered(lambda i: i.name == "Open by Product")
        self.assertEqual(by_product.item_type, "bar_horizontal")
        self.assertEqual(by_product.group_by_field_id.name, "product_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Orders")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("product_id", column_names)
        self.assertIn("state", column_names)
        self.assertIn("partner_id", column_names)
        self.assertIn("user_id", column_names)
