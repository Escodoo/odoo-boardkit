# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestAccountDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = ("boardkit_dashboard_account.template_account_invoicing",)

    def test_create_from_template_account_invoicing(self):
        template = self.env.ref("boardkit_dashboard_account.template_account_invoicing")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Invoicing Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("account.group_account_invoice"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertFalse(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "account.move" for item in dashboard.item_ids)
        )
        # Sums must stay in company currency to be comparable.
        for item in dashboard.item_ids.filtered(lambda i: i.aggregation == "sum"):
            self.assertTrue(item.measure_field_id.name.endswith("_signed"))

        total = dashboard.item_ids.filtered(lambda i: i.name == "Total Invoiced")
        self.assertEqual(total.aggregation, "sum")
        self.assertEqual(total.measure_field_id.name, "amount_total_signed")
        self.assertTrue(total.compare_previous_period)
        self.assertEqual(total.unit_type, "monetary")

        outstanding = dashboard.item_ids.filtered(lambda i: i.name == "Outstanding AR")
        self.assertEqual(outstanding.measure_field_id.name, "amount_residual_signed")
        self.assertFalse(outstanding.date_field_id)

        collected = dashboard.item_ids.filtered(lambda i: i.name == "Collected")
        self.assertEqual(collected.measure_field_id.name, "amount_total_signed")
        self.assertTrue(collected.compare_previous_period)

        collection = dashboard.item_ids.filtered(lambda i: i.name == "Collection Rate")
        self.assertEqual(collection.kpi_mode, "comparison")
        self.assertEqual(collection.kpi_display, "percent")
        self.assertEqual(collection.model_2_name, "account.move")
        # Counting invoices avoids reporting a partially paid invoice as zero.
        self.assertEqual(collection.aggregation, "count")
        self.assertEqual(collection.aggregation_2, "count")

        payment_chart = dashboard.item_ids.filtered(
            lambda i: i.name == "By Payment Status"
        )
        self.assertEqual(payment_chart.item_type, "doughnut")
        self.assertEqual(payment_chart.group_by_field_id.name, "payment_state")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Invoices")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("payment_state", column_names)
        self.assertIn("amount_residual", column_names)
        self.assertIn("invoice_date_due", column_names)
