# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMrpDashboardTemplates(TransactionCase):
    def test_create_from_template_mrp_overview(self):
        template = self.env.ref("boardkit_dashboard_mrp.template_mrp_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Manufacturing Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("mrp.group_mrp_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "mrp.production" for item in dashboard.item_ids)
        )

        confirmed = dashboard.item_ids.filtered(lambda i: i.name == "Confirmed MOs")
        self.assertFalse(confirmed.date_field_id)

        done = dashboard.item_ids.filtered(lambda i: i.name == "Done MOs")
        self.assertEqual(done.date_field_id.name, "date_finished")
        self.assertTrue(done.compare_previous_period)

        qty = dashboard.item_ids.filtered(lambda i: i.name == "Qty to Produce")
        self.assertEqual(qty.aggregation, "sum")
        self.assertEqual(qty.measure_field_id.name, "product_qty")

        completion = dashboard.item_ids.filtered(lambda i: i.name == "Completion Rate")
        self.assertEqual(completion.kpi_mode, "comparison")
        self.assertEqual(completion.kpi_display, "percent")

        recent = dashboard.item_ids.filtered(
            lambda i: i.name == "Recent Manufacturing Orders"
        )
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("reservation_state", column_names)
        self.assertIn("product_qty", column_names)
        self.assertIn("date_deadline", column_names)
