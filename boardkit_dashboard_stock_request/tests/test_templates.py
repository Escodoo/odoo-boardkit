# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockRequestDashboardTemplates(TransactionCase):
    def test_create_from_template_stock_request_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_stock_request.template_stock_request_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Stock Request Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("stock_request.group_stock_request_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "stock.request" for item in dashboard.item_ids)
        )

        requested_qty = dashboard.item_ids.filtered(lambda i: i.name == "Requested Qty")
        self.assertEqual(requested_qty.aggregation, "sum")
        self.assertEqual(requested_qty.measure_field_id.name, "product_uom_qty")
        self.assertTrue(requested_qty.compare_previous_period)
        self.assertEqual(requested_qty.date_field_id.name, "expected_date")

        drafts = dashboard.item_ids.filtered(lambda i: i.name == "Draft Requests")
        self.assertFalse(drafts.date_field_id)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Completion Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")
        self.assertEqual(rate.model_2_name, "stock.request")

        status_chart = dashboard.item_ids.filtered(
            lambda i: i.name == "Requests by Status"
        )
        self.assertEqual(status_chart.item_type, "doughnut")
        self.assertEqual(status_chart.group_by_field_id.name, "state")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Requests")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("product_uom_qty", column_names)
        self.assertIn("warehouse_id", column_names)
        self.assertIn("requested_by", column_names)
