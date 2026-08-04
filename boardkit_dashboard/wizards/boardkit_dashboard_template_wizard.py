# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class BoardkitDashboardTemplateWizard(models.TransientModel):
    _name = "boardkit.dashboard.template.wizard"
    _description = "Create Dashboard from Template"

    template_id = fields.Many2one(
        comodel_name="boardkit.dashboard.template",
        string="Template",
        required=True,
        domain=[("active", "=", True)],
    )
    name = fields.Char(
        string="Dashboard Name",
        help="Optional name for the new board. Leave empty to keep the template name.",
    )

    def action_create(self):
        self.ensure_one()
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(
            self.template_id.id,
            name=self.name or None,
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Dashboard"),
            "res_model": "boardkit.dashboard",
            "res_id": dashboard_ids[0],
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
