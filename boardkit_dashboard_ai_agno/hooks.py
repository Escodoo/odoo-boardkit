# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Post-install helpers for Boardkit AI bridges."""

from odoo import SUPERUSER_ID, api
from odoo.tools import config as odoo_config

ICP_KEY = "boardkit_dashboard_ai_agno.bridge_auth_token"
# Same odoo.conf key as ai_agno_connector, which only exists for Odoo 18.
CONFIG_BRIDGE_AUTH_TOKEN = "agno_bridge_auth_token"

_BRIDGE_XMLIDS = (
    "boardkit_dashboard_ai_agno.ai_bridge_boardkit_summary",
    "boardkit_dashboard_ai_agno.ai_bridge_boardkit_explain",
    "boardkit_dashboard_ai_agno.ai_bridge_boardkit_generate",
    "boardkit_dashboard_ai_agno.ai_bridge_boardkit_chat",
)


def ensure_token(env, icp_key, config_key):
    """Return a token: ICP override wins, else odoo.conf (Doodba conf.d).

    Does not write secrets into ir.config_parameter.
    """
    value = (env["ir.config_parameter"].sudo().get_param(icp_key) or "").strip()
    if value:
        return value
    return (odoo_config.get(config_key) or "").strip()


def apply_auth_token(env, bridge_xmlids=None):
    """Copy token (ICP or odoo.conf) onto bridges with an empty auth_token."""
    token = ensure_token(env, ICP_KEY, CONFIG_BRIDGE_AUTH_TOKEN)
    if not token:
        return
    for xmlid in bridge_xmlids or _BRIDGE_XMLIDS:
        bridge = env.ref(xmlid, raise_if_not_found=False)
        if bridge and not bridge.auth_token:
            bridge.auth_token = token


def post_init_hook(cr, registry):
    apply_auth_token(api.Environment(cr, SUPERUSER_ID, {}))
