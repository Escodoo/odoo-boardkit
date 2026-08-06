# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEventDashboardTemplates(TransactionCase):
    def test_create_from_template_event_overview(self):
        template = self.env.ref("boardkit_dashboard_event.template_event_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Event Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("event.group_event_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(
                item.model_name in ("event.event", "event.registration")
                for item in dashboard.item_ids
            )
        )

        upcoming = dashboard.item_ids.filtered(lambda i: i.name == "Upcoming Events")
        self.assertFalse(upcoming.date_field_id)

        finished = dashboard.item_ids.filtered(lambda i: i.name == "Finished Events")
        self.assertEqual(finished.date_field_id.name, "date_end")
        self.assertTrue(finished.compare_previous_period)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Attendance Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")
        self.assertEqual(rate.model_2_name, "event.registration")

        stage_chart = dashboard.item_ids.filtered(lambda i: i.name == "Events by Stage")
        self.assertEqual(stage_chart.item_type, "doughnut")
        self.assertEqual(stage_chart.group_by_field_id.name, "stage_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Events")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("stage_id", column_names)
        self.assertIn("date_begin", column_names)
        self.assertIn("organizer_id", column_names)
