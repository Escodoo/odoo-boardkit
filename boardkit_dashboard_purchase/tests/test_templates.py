# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseDashboardTemplates(TransactionCase):
    def test_create_from_template_purchase_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_purchase.template_purchase_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Purchase Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("purchase.group_purchase_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "purchase.order" for item in dashboard.item_ids)
        )

        untaxed = dashboard.item_ids.filtered(lambda i: i.name == "Untaxed Total")
        self.assertEqual(untaxed.aggregation, "sum")
        self.assertEqual(untaxed.measure_field_id.name, "amount_untaxed")
        self.assertEqual(untaxed.unit_type, "monetary")
        self.assertTrue(untaxed.compare_previous_period)
        self.assertEqual(untaxed.date_field_id.name, "date_approve")

        rfqs = dashboard.item_ids.filtered(lambda i: i.name == "RFQs")
        self.assertFalse(rfqs.date_field_id)

        confirmation = dashboard.item_ids.filtered(
            lambda i: i.name == "Confirmation Rate"
        )
        self.assertEqual(confirmation.kpi_mode, "comparison")
        self.assertEqual(confirmation.kpi_display, "percent")
        self.assertEqual(confirmation.model_2_name, "purchase.order")

        status_chart = dashboard.item_ids.filtered(
            lambda i: i.name == "Orders by Status"
        )
        self.assertEqual(status_chart.item_type, "doughnut")
        self.assertEqual(status_chart.group_by_field_id.name, "state")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Orders")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("invoice_status", column_names)
        self.assertIn("user_id", column_names)
        self.assertIn("amount_untaxed", column_names)
