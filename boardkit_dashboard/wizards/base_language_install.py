# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class BaseLanguageInstall(models.TransientModel):
    _inherit = "base.language.install"

    def lang_install(self):
        """Translate boards created from templates into the new languages.

        Template terms are applied when the board is created, so a database
        that installs a language later would keep its boards in English. The
        pass below covers those boards and skips whatever the user renamed.
        """
        result = super().lang_install()
        langs = [code for code in self.lang_ids.mapped("code") if code != "en_US"]
        if langs:
            self.env["boardkit.dashboard"]._link_boards_to_templates()
            boards = (
                self.env["boardkit.dashboard"]
                .sudo()
                .with_context(active_test=False)
                .search([("source_template_id", "!=", False)])
            )
            boards._apply_template_translations(langs=langs)
        return result
