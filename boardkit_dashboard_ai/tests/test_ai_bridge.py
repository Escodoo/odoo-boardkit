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

    def test_prepare_payload_boardkit_from_record(self):
        bridge = self.env.ref("boardkit_dashboard_ai.ai_bridge_boardkit_summary")
        dashboard = self.env["boardkit.dashboard"].create({"name": "Payload Board"})
        payload = bridge._prepare_payload_boardkit(
            record=dashboard,
            snapshot={"name": dashboard.name},
            filters={"date_preset": "none"},
            prompt="Summarize",
            item={"id": 1},
            message="Why?",
            history=[{"role": "user", "content": "Hi"}],
        )
        self.assertEqual(payload["_model"], "boardkit.dashboard")
        self.assertEqual(payload["_id"], dashboard.id)
        self.assertEqual(payload["snapshot"]["name"], "Payload Board")
        self.assertEqual(payload["filters"]["date_preset"], "none")
        self.assertEqual(payload["prompt"], "Summarize")
        self.assertEqual(payload["item"]["id"], 1)
        self.assertEqual(payload["message"], "Why?")
        self.assertEqual(payload["history"][0]["role"], "user")

    def test_prepare_payload_boardkit_aliases_and_defaults(self):
        bridge = self.env.ref("boardkit_dashboard_ai.ai_bridge_boardkit_chat")
        payload = bridge._prepare_payload_boardkit(
            res_model="boardkit.dashboard",
            res_id=0,
        )
        self.assertEqual(payload["_model"], "boardkit.dashboard")
        self.assertEqual(payload["_id"], 0)
        self.assertEqual(payload["snapshot"], {})
        self.assertEqual(payload["filters"], {})
        self.assertFalse(payload["prompt"])
        self.assertFalse(payload["item"])
        self.assertFalse(payload["message"])
        self.assertEqual(payload["history"], [])
        aliased = bridge._prepare_payload_boardkit(model="res.partner", res_id=False)
        self.assertEqual(aliased["_model"], "res.partner")
        self.assertFalse(aliased["_id"])

    def test_process_response_boardkit(self):
        execution = self.env["ai.bridge.execution"].new({})
        empty = execution._process_response_boardkit("not-a-dict")
        self.assertEqual(empty["body"], "")
        self.assertTrue(empty["body_is_html"])
        processed = execution._process_response_boardkit(
            {
                "body": "<p>Hi</p>",
                "body_is_html": True,
                "payload": {"dashboards": []},
                "name": "Board",
                "actions": [{"type": "apply_filters"}],
            }
        )
        self.assertEqual(processed["body"], "<p>Hi</p>")
        self.assertEqual(processed["name"], "Board")
        self.assertEqual(processed["payload"]["dashboards"], [])
        self.assertEqual(len(processed["actions"]), 1)
