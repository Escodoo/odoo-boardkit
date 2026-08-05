# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockDashboardTemplates(TransactionCase):
    def test_create_from_template_stock_overview(self):
        template = self.env.ref("boardkit_dashboard_stock.template_stock_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Inventory Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("stock.group_stock_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "stock.picking" for item in dashboard.item_ids)
        )

        ready = dashboard.item_ids.filtered(lambda i: i.name == "Ready Transfers")
        self.assertFalse(ready.date_field_id)

        done = dashboard.item_ids.filtered(lambda i: i.name == "Done Transfers")
        self.assertEqual(done.date_field_id.name, "date_done")
        self.assertTrue(done.compare_previous_period)

        completion = dashboard.item_ids.filtered(lambda i: i.name == "Completion Rate")
        self.assertEqual(completion.kpi_mode, "comparison")
        self.assertEqual(completion.kpi_display, "percent")

        by_type = dashboard.item_ids.filtered(
            lambda i: i.name == "Transfers by Operation Type"
        )
        self.assertEqual(by_type.item_type, "bar_horizontal")
        self.assertEqual(by_type.group_by_field_id.name, "picking_type_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Transfers")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("picking_type_id", column_names)
        self.assertIn("scheduled_date", column_names)
        self.assertIn("date_done", column_names)
