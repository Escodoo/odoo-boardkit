# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMassMailingDashboardTemplates(TransactionCase):
    def test_create_from_template_email_marketing_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_mass_mailing.template_email_marketing_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Email Marketing Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("mass_mailing.group_mass_mailing_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(
                item.model_name in ("mailing.mailing", "mailing.trace")
                for item in dashboard.item_ids
            )
        )

        drafts = dashboard.item_ids.filtered(lambda i: i.name == "Draft Mailings")
        self.assertFalse(drafts.date_field_id)

        sent = dashboard.item_ids.filtered(lambda i: i.name == "Sent Mailings")
        self.assertEqual(sent.date_field_id.name, "sent_date")
        self.assertTrue(sent.compare_previous_period)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Open Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")
        self.assertEqual(rate.model_2_name, "mailing.trace")

        status_chart = dashboard.item_ids.filtered(
            lambda i: i.name == "Traces by Status"
        )
        self.assertEqual(status_chart.item_type, "doughnut")
        self.assertEqual(status_chart.group_by_field_id.name, "trace_status")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Mailings")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("subject", column_names)
        self.assertIn("campaign_id", column_names)
        self.assertIn("sent_date", column_names)
