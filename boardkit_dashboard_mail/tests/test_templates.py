# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailDashboardTemplates(TransactionCase):
    def test_create_from_template_my_day(self):
        template = self.env.ref("boardkit_dashboard_mail.template_my_day")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "My Day")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(dashboard.group_ids, self.env.ref("base.group_user"))
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertEqual(len(dashboard.filter_ids), 3)

        models = set(dashboard.item_ids.mapped("model_name"))
        self.assertEqual(
            models,
            {
                "mail.activity",
                "calendar.event",
                "mail.message",
                "discuss.channel",
            },
        )

        overdue = dashboard.item_ids.filtered(lambda i: i.name == "Overdue")
        self.assertEqual(overdue.item_type, "tile")
        self.assertEqual(overdue.model_name, "mail.activity")
        self.assertIn("date_deadline", overdue.domain)
        self.assertIn("context_today()", overdue.domain)

        meetings = dashboard.item_ids.filtered(lambda i: i.name == "Next Meetings")
        self.assertEqual(meetings.item_type, "list")
        self.assertEqual(meetings.model_name, "calendar.event")
        column_names = meetings.list_column_ids.mapped("field_id.name")
        self.assertIn("name", column_names)
        self.assertIn("start", column_names)
        self.assertIn("stop", column_names)
        self.assertIn("location", column_names)

        by_type = dashboard.item_ids.filtered(lambda i: i.name == "Activities by Type")
        self.assertEqual(by_type.item_type, "pie")
        self.assertEqual(by_type.group_by_field_id.name, "activity_type_id")
