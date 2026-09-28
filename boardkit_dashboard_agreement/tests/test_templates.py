# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestAgreementDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = ("boardkit_dashboard_agreement.template_agreement_overview",)

    def test_create_from_template_agreement_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_agreement.template_agreement_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Agreement Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("base.group_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertFalse(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "agreement" for item in dashboard.item_ids)
        )

        active = dashboard.item_ids.filtered(lambda i: i.name == "Active Agreements")
        self.assertFalse(active.date_field_id)

        signatures = dashboard.item_ids.filtered(lambda i: i.name == "New Signatures")
        self.assertEqual(signatures.date_field_id.name, "signature_date")
        self.assertTrue(signatures.compare_previous_period)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Active Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")

        domain_chart = dashboard.item_ids.filtered(
            lambda i: i.name == "Active by Domain"
        )
        self.assertEqual(domain_chart.item_type, "doughnut")
        self.assertEqual(domain_chart.group_by_field_id.name, "domain")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Agreements")
        # Unsigned agreements have no signature date and would never show up.
        self.assertFalse(recent.date_field_id)
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("agreement_type_id", column_names)
        self.assertIn("signature_date", column_names)
        self.assertIn("partner_id", column_names)
