# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestRecruitmentDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = (
        "boardkit_dashboard_hr_recruitment.template_recruitment_overview",
    )

    def test_create_from_template_recruitment_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_hr_recruitment.template_recruitment_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Recruitment Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("hr_recruitment.group_hr_recruitment_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertFalse(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "hr.applicant" for item in dashboard.item_ids)
        )

        ongoing = dashboard.item_ids.filtered(
            lambda i: i.name == "Ongoing Applications"
        )
        self.assertFalse(ongoing.date_field_id)

        hired = dashboard.item_ids.filtered(lambda i: i.name == "Hired")
        self.assertEqual(hired.date_field_id.name, "date_closed")
        self.assertTrue(hired.compare_previous_period)

        hire_rate = dashboard.item_ids.filtered(lambda i: i.name == "Hire Rate")
        self.assertEqual(hire_rate.kpi_mode, "comparison")
        self.assertEqual(hire_rate.kpi_display, "percent")
        # Every application received in the period is the denominator.
        self.assertEqual(hire_rate.domain_2, "[]")
        self.assertEqual(hire_rate.date_field_id, hire_rate.date_field_2_id)

        funnel = dashboard.item_ids.filtered(lambda i: i.name == "Pipeline Funnel")
        self.assertEqual(funnel.item_type, "funnel")
        self.assertEqual(funnel.group_by_field_id.name, "stage_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Applications")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("job_id", column_names)
        self.assertIn("stage_id", column_names)
        self.assertIn("source_id", column_names)
        self.assertIn("user_id", column_names)
