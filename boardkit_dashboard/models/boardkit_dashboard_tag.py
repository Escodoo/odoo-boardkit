# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from random import randint

from odoo import fields, models


class BoardkitDashboardTag(models.Model):
    _name = "boardkit.dashboard.tag"
    _description = "Boardkit Dashboard Tag"
    _order = "name"

    def _get_default_color(self):
        # Color 0 is treated as "Hide in kanban" by web.KanbanMany2ManyTagsField.
        return randint(1, 11)

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(
        string="Color Index",
        default=_get_default_color,
        help="Transparent tags (color 0) are not visible on dashboard kanban cards.",
    )

    def init(self):
        """One-shot: reassign legacy default color 0 so tags show in kanban.

        Tags created before the random default used color 0, which Odoo hides
        in kanban many2many_tags. Run once via ir.config_parameter guard so
        intentional "hide in kanban" (color 0) is preserved afterwards.
        """
        icp = self.env["ir.config_parameter"].sudo()
        key = "boardkit_dashboard.tag_color0_migrated"
        if icp.get_param(key):
            return
        self.env.cr.execute(
            """
            UPDATE boardkit_dashboard_tag
               SET color = ((id % 11) + 1)
             WHERE color IS NULL OR color = 0
            """
        )
        icp.set_param(key, "1")
