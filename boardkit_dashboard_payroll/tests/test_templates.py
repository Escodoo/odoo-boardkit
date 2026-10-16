# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestPayrollDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = ("boardkit_dashboard_payroll.template_payroll_overview",)

    def test_create_from_template_payroll_overview(self):
        template = self.env.ref("boardkit_dashboard_payroll.template_payroll_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Payroll Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("payroll.group_payroll_user"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertFalse(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "hr.payslip" for item in dashboard.item_ids)
        )

        draft = dashboard.item_ids.filtered(lambda i: i.name == "Draft Payslips")
        self.assertFalse(draft.date_field_id)

        done = dashboard.item_ids.filtered(lambda i: i.name == "Done Payslips")
        self.assertEqual(done.date_field_id.name, "date_from")
        self.assertTrue(done.compare_previous_period)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Done Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")
        # Payslips still waiting belong to the denominator too.
        self.assertEqual(rate.domain_2, "[]")

        by_struct = dashboard.item_ids.filtered(lambda i: i.name == "Done by Structure")
        self.assertEqual(by_struct.item_type, "bar_horizontal")
        self.assertEqual(by_struct.group_by_field_id.name, "struct_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Payslips")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("employee_id", column_names)
        self.assertIn("state", column_names)
        self.assertIn("struct_id", column_names)
        self.assertIn("payslip_run_id", column_names)
