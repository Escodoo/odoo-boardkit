# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .boardkit_dashboard_item import NUMERIC_FIELD_DOMAIN


class BoardkitDashboardItemMeasure(models.Model):
    _name = "boardkit.dashboard.item.measure"
    _description = "Boardkit Dashboard Item Measure"
    _order = "sequence, id"

    item_id = fields.Many2one(
        comodel_name="boardkit.dashboard.item",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    model_id = fields.Many2one(
        related="item_id.model_id",
        store=True,
        readonly=True,
    )
    field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Measure",
        required=True,
        ondelete="cascade",
        domain=NUMERIC_FIELD_DOMAIN,
    )

    _sql_constraints = [
        (
            "item_field_uniq",
            "unique(item_id, field_id)",
            "Each field can only appear once as a measure.",
        ),
    ]

    @api.constrains("field_id", "model_id")
    def _check_field_belongs_to_item_model(self):
        for rec in self:
            if rec.field_id and rec.model_id and rec.field_id.model_id != rec.model_id:
                raise ValidationError(
                    _(
                        "Measure field %(field)s does not belong to model %(model)s.",
                        field=rec.field_id.name,
                        model=rec.model_id.model,
                    )
                )
