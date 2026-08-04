# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .boardkit_dashboard_item import DATE_GRANULARITIES, GROUPABLE_FIELD_DOMAIN

DRILL_CHART_TYPES = [
    ("bar", "Bar Chart"),
    ("bar_horizontal", "Horizontal Bar Chart"),
    ("line", "Line Chart"),
    ("area", "Area Chart"),
    ("pie", "Pie Chart"),
    ("doughnut", "Doughnut Chart"),
    ("funnel", "Funnel Chart"),
]


class BoardkitDashboardItemDrill(models.Model):
    _name = "boardkit.dashboard.item.drill"
    _description = "Boardkit Dashboard Item Drill Level"
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
    group_by_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Group By",
        required=True,
        ondelete="cascade",
        domain=GROUPABLE_FIELD_DOMAIN,
    )
    group_by_ttype = fields.Selection(
        related="group_by_field_id.ttype", string="Group By Type"
    )
    group_by_granularity = fields.Selection(
        selection=DATE_GRANULARITIES,
        default="month",
        help="Used when the Group By field is a date or datetime field.",
    )
    chart_type = fields.Selection(
        selection=DRILL_CHART_TYPES,
        required=True,
        default="bar",
    )
    chart_sort = fields.Selection(
        selection=[
            ("default", "Default Order"),
            ("label_asc", "Label Ascending"),
            ("label_desc", "Label Descending"),
            ("value_asc", "Value Ascending"),
            ("value_desc", "Value Descending"),
        ],
        default="default",
        required=True,
    )
    record_limit = fields.Integer(
        help="Maximum number of groups displayed. 0 means no limit.",
    )

    @api.constrains("group_by_field_id", "model_id")
    def _check_group_by_field_model(self):
        for rec in self:
            if (
                rec.group_by_field_id
                and rec.model_id
                and rec.group_by_field_id.model_id != rec.model_id
            ):
                raise ValidationError(
                    _(
                        "Drill field %(field)s does not belong to model %(model)s.",
                        field=rec.group_by_field_id.name,
                        model=rec.model_id.model,
                    )
                )
