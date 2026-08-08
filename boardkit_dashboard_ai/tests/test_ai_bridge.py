# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..hooks import ICP_KEY, apply_auth_token, post_init_hook


@tagged("post_install", "-at_install")
class TestBoardkitAiBridges(TransactionCase):
    def test_bridges_configured(self):
        summary = self.env.ref("boardkit_dashboard_ai.ai_bridge_boardkit_summary")
        explain = self.env.ref("boardkit_dashboard_ai.ai_bridge_boardkit_explain")
        generate = self.env.ref("boardkit_dashboard_ai.ai_bridge_boardkit_generate")
        chat = self.env.ref("boardkit_dashboard_ai.ai_bridge_boardkit_chat")
        for bridge, path in (
            (summary, "/bridge/boardkit/summary"),
            (explain, "/bridge/boardkit/explain"),
            (generate, "/bridge/boardkit/generate"),
            (chat, "/bridge/boardkit/chat"),
        ):
            self.assertEqual(bridge.usage, "none")
            self.assertEqual(bridge.payload_type, "boardkit")
            self.assertEqual(bridge.result_type, "boardkit")
            self.assertEqual(bridge.provider, "agno")
            self.assertTrue(bridge.url.endswith(path))

    def test_apply_auth_token(self):
        bridge = self.env.ref("boardkit_dashboard_ai.ai_bridge_boardkit_summary")
        bridge.auth_token = False
        self.env["ir.config_parameter"].sudo().set_param(ICP_KEY, "boardkit-token")
        apply_auth_token(self.env)
        self.assertEqual(bridge.auth_token, "boardkit-token")
        post_init_hook(self.env)
        self.assertEqual(bridge.auth_token, "boardkit-token")
