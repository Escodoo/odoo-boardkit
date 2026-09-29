# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestRmaDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = ("boardkit_dashboard_rma.template_rma_overview",)

    def test_create_from_template_rma_overview(self):
        template = self.env.ref("boardkit_dashboard_rma.template_rma_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "RMA Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("rma.rma_group_user_all"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertFalse(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(all(item.model_name == "rma" for item in dashboard.item_ids))

        drafts = dashboard.item_ids.filtered(lambda i: i.name == "Draft RMAs")
        self.assertFalse(drafts.date_field_id)

        finished = dashboard.item_ids.filtered(lambda i: i.name == "Finished")
        self.assertEqual(finished.date_field_id.name, "date")
        self.assertTrue(finished.compare_previous_period)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Completion Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")
        self.assertEqual(rate.model_2_name, "rma")
        # RMAs still in the pipeline belong to the denominator.
        self.assertEqual(rate.domain_2, "[]")

        status_chart = dashboard.item_ids.filtered(lambda i: i.name == "RMAs by Status")
        self.assertEqual(status_chart.item_type, "doughnut")
        self.assertEqual(status_chart.group_by_field_id.name, "state")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent RMAs")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("operation_id", column_names)
        self.assertIn("partner_id", column_names)
        self.assertIn("product_id", column_names)
