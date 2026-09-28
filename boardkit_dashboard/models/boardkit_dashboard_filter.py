# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .boardkit_dashboard_item import ITEM_MODEL_DOMAIN


class BoardkitDashboardFilter(models.Model):
    _name = "boardkit.dashboard.filter"
    _description = "Boardkit Dashboard Predefined Filter"
    _order = "sequence, id"

    name = fields.Char(string="Filter Label", required=True, translate=True)
    sequence = fields.Integer(default=10)
    dashboard_id = fields.Many2one(
        comodel_name="boardkit.dashboard",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=ITEM_MODEL_DOMAIN,
        help="The filter is applied to every dashboard item based on this model.",
    )
    model_name = fields.Char(related="model_id.model", string="Model Name")
    domain = fields.Char(required=True, default="[]")
    default_enabled = fields.Boolean(
        string="Enabled by Default",
        help="Apply this filter automatically when the dashboard is opened.",
    )

    @api.constrains("domain", "model_id")
    def _check_domain(self):
        for rec in self:
            try:
                rec.dashboard_id._eval_domain(rec.domain, rec.model_name)
            except Exception as error:
                raise ValidationError(
                    _(
                        "Invalid domain on filter %(name)s: %(error)s",
                        name=rec.name,
                        error=error,
                    )
                ) from error
