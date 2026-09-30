# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Translate the boards a database already has.

    Template terms are written when a board is created, so databases running
    since before this version keep their boards in English. Link those boards
    to the template that produced them and translate what the user has not
    rewritten.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    dashboard = env["boardkit.dashboard"]
    dashboard._link_boards_to_templates()
    boards = dashboard.with_context(active_test=False).search(
        [("source_template_id", "!=", False)]
    )
    boards._apply_template_translations()
