# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class BoardkitDashboardAiGenerateWizard(models.TransientModel):
    _name = "boardkit.dashboard.ai.generate.wizard"
    _description = "Generate Dashboard with AI"

    prompt = fields.Text(
        string="Description",
        required=True,
        help="Describe the dashboard you want to create in plain language.",
    )
    result_html = fields.Html(string="AI Notes", readonly=True)
    dashboard_ids = fields.Many2many(
        comodel_name="boardkit.dashboard",
        string="Created Dashboards",
        readonly=True,
    )

    def action_generate(self):
        self.ensure_one()
        result = self.env["boardkit.dashboard"].action_ai_generate(self.prompt)
        dashboards = self.env["boardkit.dashboard"].browse(result.get("dashboard_ids"))
        self.write(
            {
                "dashboard_ids": [(6, 0, dashboards.ids)],
                "result_html": result.get("body") or False,
            }
        )
        if len(dashboards) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Dashboard"),
                "res_model": "boardkit.dashboard",
                "res_id": dashboards.id,
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Generate Dashboard with AI"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_dashboards(self):
        self.ensure_one()
        if len(self.dashboard_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Dashboard"),
                "res_model": "boardkit.dashboard",
                "res_id": self.dashboard_ids.id,
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Dashboards"),
            "res_model": "boardkit.dashboard",
            "domain": [("id", "in", self.dashboard_ids.ids)],
            "view_mode": "list,form",
            "target": "current",
        }
