# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BoardkitDashboardItemColumn(models.Model):
    _name = "boardkit.dashboard.item.column"
    _description = "Boardkit Dashboard Item List Column"
    _order = "sequence, id"

    item_id = fields.Many2one(
        comodel_name="boardkit.dashboard.item",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Column",
        required=True,
        ondelete="cascade",
    )

    _sql_constraints = [
        (
            "item_field_uniq",
            "unique(item_id, field_id)",
            "Each field can only appear once as a list column.",
        ),
    ]

    @api.constrains("field_id", "item_id")
    def _check_field_belongs_to_item_model(self):
        for rec in self:
            model = rec.item_id.model_id
            if rec.field_id and model and rec.field_id.model_id != model:
                raise ValidationError(
                    _(
                        "Column field %(field)s does not belong to model %(model)s.",
                        field=rec.field_id.name,
                        model=model.model,
                    )
                )
