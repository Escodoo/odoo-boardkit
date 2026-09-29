# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestContractDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = (
        "boardkit_dashboard_hr_contract.template_employee_contracts_overview",
    )

    def test_create_from_template_employee_contracts_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_hr_contract.template_employee_contracts_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Employee Contracts Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("hr_contract.group_hr_contract_manager"),
        )
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "kpi"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "hr.contract" for item in dashboard.item_ids)
        )

        running = dashboard.item_ids.filtered(lambda i: i.name == "Running Contracts")
        self.assertFalse(running.date_field_id)
        # Offboarded employees keep their contracts, so the workforce figures
        # have to exclude them.
        self.assertIn("employee_id.active", running.domain)

        coverage = dashboard.item_ids.filtered(lambda i: i.name == "Contract Coverage")
        self.assertEqual(coverage.model_2_name, "hr.employee")
        self.assertEqual(coverage.kpi_display, "percent")

        new_contracts = dashboard.item_ids.filtered(lambda i: i.name == "New Contracts")
        self.assertEqual(new_contracts.date_field_id.name, "date_start")
        self.assertTrue(new_contracts.compare_previous_period)

        expired = dashboard.item_ids.filtered(lambda i: i.name == "Expired Contracts")
        self.assertEqual(expired.date_field_id.name, "date_end")

        avg_wage = dashboard.item_ids.filtered(lambda i: i.name == "Avg Wage")
        self.assertEqual(avg_wage.aggregation, "avg")
        self.assertEqual(avg_wage.measure_field_id.name, "wage")
        self.assertEqual(avg_wage.unit_type, "monetary")

        by_dept = dashboard.item_ids.filtered(
            lambda i: i.name == "Running by Department"
        )
        self.assertEqual(by_dept.item_type, "bar_horizontal")
        self.assertEqual(by_dept.group_by_field_id.name, "department_id")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Contracts")
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("employee_id", column_names)
        self.assertIn("state", column_names)
        self.assertIn("wage", column_names)
        self.assertIn("contract_type_id", column_names)
