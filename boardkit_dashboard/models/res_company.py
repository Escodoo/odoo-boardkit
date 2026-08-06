# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..tools.palettes import PRESET_PALETTE_SELECTION


class ResCompany(models.Model):
    _inherit = "res.company"

    boardkit_default_color_palette = fields.Selection(
        selection=PRESET_PALETTE_SELECTION + [("custom", "Custom")],
        string="Boardkit Default Palette",
        help="Applied as the default color palette when a new Boardkit "
        "dashboard is created. Existing dashboards are not updated when "
        "this setting changes.",
    )
    boardkit_default_palette_id = fields.Many2one(
        comodel_name="boardkit.dashboard.palette",
        string="Boardkit Default Custom Palette",
        ondelete="restrict",
    )

    @api.constrains("boardkit_default_color_palette", "boardkit_default_palette_id")
    def _check_boardkit_default_palette(self):
        for company in self:
            if (
                company.boardkit_default_color_palette == "custom"
                and not company.boardkit_default_palette_id
            ):
                raise ValidationError(
                    _(
                        "Select a default custom palette for company "
                        "%(name)s or pick a preset color palette.",
                        name=company.name,
                    )
                )
