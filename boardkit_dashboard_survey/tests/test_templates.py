# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSurveyDashboardTemplates(TransactionCase):
    def test_create_from_template_survey_overview(self):
        template = self.env.ref("boardkit_dashboard_survey.template_survey_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Survey Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("survey.group_survey_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(
                item.model_name in ("survey.survey", "survey.user_input")
                for item in dashboard.item_ids
            )
        )

        active = dashboard.item_ids.filtered(lambda i: i.name == "Active Surveys")
        self.assertFalse(active.date_field_id)

        completed = dashboard.item_ids.filtered(lambda i: i.name == "Completed Answers")
        self.assertEqual(completed.date_field_id.name, "end_datetime")
        self.assertTrue(completed.compare_previous_period)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Success Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")
        self.assertEqual(rate.model_2_name, "survey.user_input")

        status_chart = dashboard.item_ids.filtered(
            lambda i: i.name == "Answers by Status"
        )
        self.assertEqual(status_chart.item_type, "doughnut")
        self.assertEqual(status_chart.group_by_field_id.name, "state")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Answers")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("scoring_percentage", column_names)
        self.assertIn("survey_id", column_names)
        self.assertIn("scoring_success", column_names)
