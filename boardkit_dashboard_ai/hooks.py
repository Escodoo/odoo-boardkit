# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Post-install helpers for Boardkit AI bridges."""

from odoo.addons.ai_agno_connector.token_utils import (
    CONFIG_BRIDGE_AUTH_TOKEN,
    ensure_token,
)

ICP_KEY = "boardkit_dashboard_ai.bridge_auth_token"

_BRIDGE_XMLIDS = (
    "boardkit_dashboard_ai.ai_bridge_boardkit_summary",
    "boardkit_dashboard_ai.ai_bridge_boardkit_explain",
    "boardkit_dashboard_ai.ai_bridge_boardkit_generate",
    "boardkit_dashboard_ai.ai_bridge_boardkit_chat",
)


def apply_auth_token(env, bridge_xmlids=None):
    """Copy token (ICP or odoo.conf) onto bridges with an empty auth_token."""
    token = ensure_token(env, ICP_KEY, CONFIG_BRIDGE_AUTH_TOKEN)
    if not token:
        return
    for xmlid in bridge_xmlids or _BRIDGE_XMLIDS:
        bridge = env.ref(xmlid, raise_if_not_found=False)
        if bridge and not bridge.auth_token:
            bridge.auth_token = token


def post_init_hook(env):
    apply_auth_token(env)
