# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged

from odoo.addons.boardkit_dashboard.tests.common import BoardkitTemplateSmokeMixin


@tagged("post_install", "-at_install")
class TestContractDashboardTemplates(BoardkitTemplateSmokeMixin, TransactionCase):
    template_xmlids = ("boardkit_dashboard_contract.template_contract_overview",)

    def test_create_from_template_contract_overview(self):
        template = self.env.ref(
            "boardkit_dashboard_contract.template_contract_overview"
        )
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Contract Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertEqual(
            dashboard.group_ids,
            self.env.ref("account.group_account_invoice"),
        )
        self.assertEqual(len(dashboard.item_ids), 12)
        self.assertFalse(dashboard.item_ids.filtered(lambda i: i.item_type == "gauge"))
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(
            all(item.model_name == "contract.contract" for item in dashboard.item_ids)
        )

        active = dashboard.item_ids.filtered(lambda i: i.name == "Active Contracts")
        self.assertFalse(active.date_field_id)

        new_contracts = dashboard.item_ids.filtered(lambda i: i.name == "New Contracts")
        self.assertEqual(new_contracts.date_field_id.name, "date_start")
        self.assertTrue(new_contracts.compare_previous_period)

        rate = dashboard.item_ids.filtered(lambda i: i.name == "Active Rate")
        self.assertEqual(rate.kpi_mode, "comparison")
        self.assertEqual(rate.kpi_display, "percent")

        type_chart = dashboard.item_ids.filtered(lambda i: i.name == "Active by Type")
        self.assertEqual(type_chart.item_type, "doughnut")
        self.assertEqual(type_chart.group_by_field_id.name, "contract_type")

        recent = dashboard.item_ids.filtered(lambda i: i.name == "Recent Contracts")
        # A portfolio list cut by the period would hide the running contracts.
        self.assertFalse(recent.date_field_id)
        column_names = recent.list_column_ids.mapped("field_id.name")
        self.assertIn("recurring_next_date", column_names)
        self.assertIn("contract_type", column_names)
        self.assertIn("partner_id", column_names)
