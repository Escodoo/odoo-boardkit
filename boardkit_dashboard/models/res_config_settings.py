# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from ..tools.palettes import PRESET_PALETTE_SELECTION


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Not related: res.config.settings writes related inverses field-by-field,
    # which trips the company constraint when Custom is saved before the
    # Many2one. Persist both values atomically in set_values instead.
    boardkit_default_color_palette = fields.Selection(
        selection=PRESET_PALETTE_SELECTION + [("custom", "Custom")],
        string="Default Palette",
    )
    boardkit_default_palette_id = fields.Many2one(
        comodel_name="boardkit.dashboard.palette",
        string="Default Custom Palette",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        company = self.env.company
        res.update(
            {
                "boardkit_default_color_palette": (
                    company.boardkit_default_color_palette or False
                ),
                "boardkit_default_palette_id": (
                    company.boardkit_default_palette_id.id or False
                ),
            }
        )
        return res

    @api.onchange("company_id")
    def _onchange_company_id_boardkit_palette(self):
        company = self.company_id
        self.boardkit_default_color_palette = (
            company.boardkit_default_color_palette if company else False
        )
        self.boardkit_default_palette_id = (
            company.boardkit_default_palette_id if company else False
        )

    def set_values(self):
        super().set_values()
        for settings in self:
            palette_key = settings.boardkit_default_color_palette or False
            settings.company_id.write(
                {
                    "boardkit_default_color_palette": palette_key,
                    "boardkit_default_palette_id": (
                        settings.boardkit_default_palette_id.id
                        if palette_key == "custom"
                        else False
                    ),
                }
            )
