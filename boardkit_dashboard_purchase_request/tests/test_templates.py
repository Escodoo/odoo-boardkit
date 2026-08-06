# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestDashboardTemplates(TransactionCase):
    def test_create_from_template_purchase_request_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_purchase_request.template_purchase_request_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Purchase Request Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("purchase_request.group_purchase_request_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "purchase.request" for item in dashboard.item_ids)
        )

        approved_cost = dashboard.item_ids.filtered(lambda i: i.name == "Approved Cost")
        self.assertEqual(approved_cost.aggregation, "sum")
        self.assertEqual(approved_cost.measure_field_id.name, "estimated_cost")
        self.assertEqual(approved_cost.unit_type, "monetary")
        self.assertTrue(approved_cost.compare_previous_period)
        self.assertEqual(approved_cost.date_field_id.name, "date_start")

        drafts = dashboard.item_ids.filtered(lambda i: i.name == "Draft Requests")
        self.assertFalse(drafts.date_field_id)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Approval Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")
        self.assertEqual(rate.model_2_name, "purchase.request")

        status_chart = dashboard.item_ids.filtered(
            lambda i: i.name == "Requests by Status"
        )
        self.assertEqual(status_chart.item_type, "doughnut")
        self.assertEqual(status_chart.group_by_field_id.name, "state")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Requests")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("estimated_cost", column_names)
        self.assertIn("requested_by", column_names)
        self.assertIn("assigned_to", column_names)
