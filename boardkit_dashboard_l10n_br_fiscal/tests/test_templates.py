# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestFiscalDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = ("boardkit_dashboard_l10n_br_fiscal.template_fiscal_overview",)

    def test_create_from_template_fiscal_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_l10n_br_fiscal.template_fiscal_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Brazilian Fiscal Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("l10n_br_fiscal.group_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertFalse(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(
                item.model_name == "l10n_br_fiscal.document"
                for item in dashboard.item_ids
            )
        )

        authorized_total = dashboard.item_ids.filtered(
            lambda i: i.name == "Authorized Outbound Total"
        )
        self.assertEqual(authorized_total.aggregation, "sum")
        self.assertEqual(authorized_total.measure_field_id.name, "fiscal_amount_total")
        self.assertEqual(authorized_total.unit_type, "monetary")
        self.assertTrue(authorized_total.compare_previous_period)
        self.assertEqual(authorized_total.date_field_id.name, "document_date")
        # Inbound and outbound amounts must never land in the same total.
        self.assertIn("'out'", authorized_total.domain)

        inbound_total = dashboard.item_ids.filtered(
            lambda i: i.name == "Authorized Inbound Total"
        )
        self.assertIn("'in'", inbound_total.domain)

        drafts = dashboard.item_ids.filtered(lambda i: i.name == "In Digitation")
        self.assertFalse(drafts.date_field_id)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Authorization Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")
        self.assertEqual(rate.model_2_name, "l10n_br_fiscal.document")

        outbound = dashboard.filter_ids.filtered(lambda f: f.name == "Outbound")
        self.assertEqual(outbound.domain, "[('fiscal_operation_type', '=', 'out')]")

        status_chart = dashboard.item_ids.filtered(
            lambda i: i.name == "Documents by e-Doc State"
        )
        self.assertEqual(status_chart.item_type, "doughnut")
        self.assertEqual(status_chart.group_by_field_id.name, "state_edoc")
        self.assertFalse(status_chart.date_field_id)

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Documents")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("fiscal_amount_total", column_names)
        self.assertIn("state_edoc", column_names)
        self.assertIn("document_type_id", column_names)
