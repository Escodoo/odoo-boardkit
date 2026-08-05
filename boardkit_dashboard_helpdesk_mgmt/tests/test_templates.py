# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHelpdeskDashboardTemplates(TransactionCase):
    def test_create_from_template_helpdesk_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_helpdesk_mgmt.template_helpdesk_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Helpdesk Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("helpdesk_mgmt.group_helpdesk_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "helpdesk.ticket" for item in dashboard.item_ids)
        )

        open_tickets = dashboard.item_ids.filtered(lambda i: i.name == "Open Tickets")
        self.assertFalse(open_tickets.date_field_id)

        closed = dashboard.item_ids.filtered(lambda i: i.name == "Closed Tickets")
        self.assertEqual(closed.date_field_id.name, "closed_date")
        self.assertTrue(closed.compare_previous_period)

        closure = dashboard.item_ids.filtered(lambda i: i.name == "Closure Rate")
        self.assertEqual(closure.kpi_mode, "comparison")
        self.assertEqual(closure.kpi_display, "percent")

        funnel = dashboard.item_ids.filtered(lambda i: i.name == "Pipeline Funnel")
        self.assertEqual(funnel.item_type, "funnel")
        self.assertEqual(funnel.group_by_field_id.name, "stage_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Tickets")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("team_id", column_names)
        self.assertIn("stage_id", column_names)
        self.assertIn("priority", column_names)
        self.assertIn("user_id", column_names)
