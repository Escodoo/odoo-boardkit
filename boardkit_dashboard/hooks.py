# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def uninstall_hook(cr, registry):
    """Remove client actions and menus created at runtime for dashboards."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    actions = env["ir.actions.client"].search([("tag", "=", "boardkit_dashboard")])
    menus = env["ir.ui.menu"].search(
        [("action", "in", [f"ir.actions.client,{a.id}" for a in actions])]
    )
    menus.unlink()
    actions.unlink()
