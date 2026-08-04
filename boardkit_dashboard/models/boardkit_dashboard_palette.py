# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class BoardkitDashboardPalette(models.Model):
    _name = "boardkit.dashboard.palette"
    _description = "Boardkit Dashboard Color Palette"
    _order = "name"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        help="Leave empty to share the palette across companies.",
    )
    color_ids = fields.One2many(
        comodel_name="boardkit.dashboard.palette.color",
        inverse_name="palette_id",
        string="Colors",
        copy=True,
    )

    # "name" is always present in create vals, so the check also runs when a
    # palette is created without any color line.
    @api.constrains("color_ids", "name")
    def _check_colors(self):
        for rec in self:
            if not rec.color_ids:
                raise ValidationError(
                    _(
                        "Palette %(name)s must define at least one color.",
                        name=rec.name,
                    )
                )

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if not default or "name" not in default:
            for palette, vals in zip(self, vals_list, strict=True):
                vals["name"] = _("%s (copy)", palette.name)
        return vals_list

    def _color_list(self):
        """Return the hex colors ordered by sequence."""
        self.ensure_one()
        # Explicit sort: right after create() the one2many cache keeps the
        # command order instead of the comodel _order.
        return self.color_ids.sorted().mapped("color")


class BoardkitDashboardPaletteColor(models.Model):
    _name = "boardkit.dashboard.palette.color"
    _description = "Boardkit Dashboard Color Palette Color"
    _order = "sequence, id"

    palette_id = fields.Many2one(
        comodel_name="boardkit.dashboard.palette",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    color = fields.Char(required=True, default="#4EA7F2")

    @api.constrains("color")
    def _check_color(self):
        for rec in self:
            if not HEX_COLOR_PATTERN.match(rec.color or ""):
                raise ValidationError(
                    _(
                        "Invalid color %(color)s. Use the #RRGGBB hex format.",
                        color=rec.color,
                    )
                )
