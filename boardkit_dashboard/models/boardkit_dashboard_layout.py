# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BoardkitDashboardLayout(models.Model):
    _name = "boardkit.dashboard.layout"
    _description = "Boardkit Dashboard Personal Layout"

    dashboard_id = fields.Many2one(
        comodel_name="boardkit.dashboard",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user,
        index=True,
    )
    layout_json = fields.Text(default="{}")
    filters_json = fields.Text(
        default="{}",
        help="Date range, predefined filters and ad-hoc filters this user "
        "last applied on the dashboard.",
    )

    _sql_constraints = [
        (
            "dashboard_user_uniq",
            "unique(dashboard_id, user_id)",
            "A user can only have one personal layout per dashboard.",
        )
    ]
