# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestMassMailingDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = (
        "boardkit_dashboard_mass_mailing.template_email_marketing_overview",
    )

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
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertFalse(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
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
        # Bounced messages were never delivered, and both sides count the
        # messages sent in the period.
        self.assertNotIn("bounce", rate.domain_2)
        self.assertEqual(rate.date_field_id.name, "sent_datetime")
        self.assertEqual(rate.date_field_2_id.name, "sent_datetime")

        status_chart = dashboard.item_ids.filtered(
            lambda i: i.name == "Traces by Status"
        )
        self.assertEqual(status_chart.item_type, "doughnut")
        self.assertEqual(status_chart.group_by_field_id.name, "trace_status")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Mailings")
        # Drafts and queued mailings have no send date yet.
        self.assertFalse(recent.date_field_id)
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("subject", column_names)
        self.assertIn("campaign_id", column_names)
        self.assertIn("sent_date", column_names)
