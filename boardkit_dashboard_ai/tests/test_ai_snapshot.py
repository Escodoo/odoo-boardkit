# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestBoardkitAiSnapshot(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.manager = new_test_user(
            cls.env,
            login="boardkit_ai_manager",
            groups=(
                "base.group_user,"
                "boardkit_dashboard.group_dashboard_manager,"
                "boardkit_dashboard_ai.group_dashboard_ai_user"
            ),
        )
        cls.user_no_ai = new_test_user(
            cls.env,
            login="boardkit_no_ai",
            groups="base.group_user,boardkit_dashboard.group_dashboard_user",
        )
        cls.dashboard = (
            cls.env["boardkit.dashboard"]
            .with_user(cls.manager)
            .create(
                {
                    "name": "AI Test Board",
                    "published": True,
                    "menu_parent_id": cls.env.ref(
                        "boardkit_dashboard.menu_dashboard_root"
                    ).id,
                }
            )
        )
        cls.item = (
            cls.env["boardkit.dashboard.item"]
            .with_user(cls.manager)
            .create(
                {
                    "name": "Partner Count",
                    "dashboard_id": cls.dashboard.id,
                    "item_type": "tile",
                    "model_id": cls.env.ref("base.model_res_partner").id,
                    "domain": "[('is_company', '=', True)]",
                    "aggregation": "count",
                }
            )
        )

    def test_prepare_ai_snapshot_includes_item_data(self):
        snapshot = self.dashboard.with_user(self.manager)._prepare_ai_snapshot(
            {"date_preset": "none", "filter_ids": []}
        )
        self.assertEqual(snapshot["name"], "AI Test Board")
        self.assertEqual(len(snapshot["items"]), 1)
        self.assertEqual(snapshot["items"][0]["name"], "Partner Count")
        self.assertIn("data", snapshot["items"][0])
        self.assertIn("value", snapshot["items"][0]["data"])

    def test_get_dashboard_data_ai_flags(self):
        data = (
            self.env["boardkit.dashboard"]
            .with_user(self.manager)
            .get_dashboard_data(self.dashboard.id)
        )
        self.assertTrue(data["ai_enabled"])
        self.assertTrue(data["ai_can_generate"])
        self.dashboard.ai_enabled = False
        data = (
            self.env["boardkit.dashboard"]
            .with_user(self.manager)
            .get_dashboard_data(self.dashboard.id)
        )
        self.assertFalse(data["ai_enabled"])

    def test_summarize_requires_ai_group(self):
        with self.assertRaises(AccessError):
            self.dashboard.with_user(self.user_no_ai).action_ai_summarize({})

    def test_summarize_requires_dashboard_ai_enabled(self):
        self.dashboard.ai_enabled = False
        with self.assertRaises(UserError):
            self.dashboard.with_user(self.manager).action_ai_summarize({})

    def test_ai_chat_requires_ai_group(self):
        with self.assertRaises(AccessError):
            self.dashboard.with_user(self.user_no_ai).action_ai_chat(
                {}, "Why is this high?", []
            )

    def test_ai_chat_rejects_empty_message(self):
        with self.assertRaises(UserError):
            self.dashboard.with_user(self.manager).action_ai_chat({}, "   ", [])

    def test_ai_chat_requires_dashboard_ai_enabled(self):
        self.dashboard.ai_enabled = False
        with self.assertRaises(UserError):
            self.dashboard.with_user(self.manager).action_ai_chat(
                {}, "Why is this high?", []
            )

    def test_ai_chat_sends_message_and_history(self):
        captured = {}

        def _fake_run(xmlid, record=None, **kwargs):
            captured["xmlid"] = xmlid
            captured["kwargs"] = kwargs
            return {"body": "<p>Because overdue rose.</p>", "body_is_html": True}

        with patch.object(
            type(self.env["boardkit.dashboard"]),
            "_run_boardkit_bridge",
            side_effect=_fake_run,
        ):
            result = self.dashboard.with_user(self.manager).action_ai_chat(
                {"date_preset": "none", "filter_ids": []},
                "Why is overdue high?",
                [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "<p>Hi</p>"},
                    {"role": "system", "content": "ignore"},
                ],
            )
        self.assertIn("overdue", result["body"])
        self.assertEqual(result["actions"], [])
        self.assertTrue(
            captured["xmlid"].endswith("ai_bridge_boardkit_chat")
            or captured["xmlid"] == "boardkit_dashboard_ai.ai_bridge_boardkit_chat"
        )
        self.assertEqual(captured["kwargs"]["message"], "Why is overdue high?")
        self.assertEqual(
            captured["kwargs"]["history"],
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "<p>Hi</p>"},
            ],
        )
        self.assertIn("items", captured["kwargs"]["snapshot"])
        self.assertTrue(captured["kwargs"]["snapshot"]["date_presets"])

    def test_ai_chat_sanitizes_filter_actions(self):
        board_filter = (
            self.env["boardkit.dashboard.filter"]
            .with_user(self.manager)
            .create(
                {
                    "name": "Companies",
                    "dashboard_id": self.dashboard.id,
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "domain": "[('is_company', '=', True)]",
                }
            )
        )

        def _fake_run(xmlid, record=None, **kwargs):
            return {
                "body": "<p>Applied this month.</p>",
                "body_is_html": True,
                "actions": [
                    {
                        "type": "apply_filters",
                        "filters": {
                            "date_preset": "this_month",
                            "filter_ids": [board_filter.id, 999999],
                            "custom_filters": [
                                {
                                    "model": "res.partner",
                                    "field": "name",
                                    "operator": "ilike",
                                    "value": "Acme",
                                },
                                {
                                    "model": "sale.order",
                                    "field": "amount_total",
                                    "operator": ">",
                                    "value": 1,
                                },
                                {
                                    "model": "res.partner",
                                    "field": "name",
                                    "operator": "; drop table",
                                    "value": "x",
                                },
                            ],
                        },
                    },
                    {"type": "delete_board", "filters": {}},
                ],
            }

        with patch.object(
            type(self.env["boardkit.dashboard"]),
            "_run_boardkit_bridge",
            side_effect=_fake_run,
        ):
            result = self.dashboard.with_user(self.manager).action_ai_chat(
                {}, "Filter this month and companies", []
            )
        self.assertEqual(len(result["actions"]), 1)
        filters = result["actions"][0]["filters"]
        self.assertEqual(filters["date_preset"], "this_month")
        self.assertEqual(filters["filter_ids"], [board_filter.id])
        self.assertEqual(len(filters["custom_filters"]), 1)
        self.assertEqual(filters["custom_filters"][0]["model"], "res.partner")
        self.assertEqual(filters["custom_filters"][0]["operator"], "ilike")

    def test_normalize_ai_chat_history(self):
        Dashboard = self.env["boardkit.dashboard"]
        history = Dashboard._normalize_ai_chat_history(
            [
                {"role": "user", "content": "A"},
                {"role": "assistant", "content": "B"},
                {"role": "tool", "content": "nope"},
                "bad",
            ]
        )
        self.assertEqual(
            history,
            [
                {"role": "user", "content": "A"},
                {"role": "assistant", "content": "B"},
            ],
        )

    def test_extract_json_payload(self):
        Dashboard = self.env["boardkit.dashboard"]
        payload = Dashboard._extract_json_payload(
            '{"version": 1, "dashboards": [{"name": "X", "items": []}]}'
        )
        self.assertEqual(payload["dashboards"][0]["name"], "X")
        fenced = Dashboard._extract_json_payload(
            '```json\n{"version": 1, "dashboards": [{"name": "Y"}]}\n```'
        )
        self.assertEqual(fenced["dashboards"][0]["name"], "Y")
        self.assertFalse(Dashboard._extract_json_payload("not json"))

    def test_action_ai_generate_imports_payload(self):
        fake_result = {
            "body": "<p>Draft</p>",
            "payload": {
                "version": 1,
                "dashboards": [
                    {
                        "name": "Generated Board",
                        "items": [
                            {
                                "name": "Companies",
                                "item_type": "tile",
                                "model": "res.partner",
                                "domain": "[('is_company', '=', True)]",
                                "aggregation": "count",
                                "layout": {"x": 0, "y": 0, "w": 3, "h": 2},
                            }
                        ],
                        "filters": [],
                    }
                ],
            },
        }
        with patch.object(
            type(self.env["boardkit.dashboard"]),
            "_run_boardkit_bridge",
            return_value=fake_result,
        ):
            result = (
                self.env["boardkit.dashboard"]
                .with_user(self.manager)
                .action_ai_generate("Create a contacts board")
            )
        dashboards = self.env["boardkit.dashboard"].browse(result["dashboard_ids"])
        self.assertEqual(len(dashboards), 1)
        self.assertEqual(dashboards.name, "Generated Board")
        self.assertFalse(dashboards.published)
        self.assertEqual(len(dashboards.item_ids), 1)

    def test_action_ai_generate_rejects_empty_prompt(self):
        with self.assertRaises(UserError):
            self.env["boardkit.dashboard"].with_user(self.manager).action_ai_generate(
                "   "
            )

    def test_normalize_ai_domain_json_booleans(self):
        Dashboard = self.env["boardkit.dashboard"]
        self.assertEqual(
            Dashboard._normalize_ai_domain(
                '[["probability", "=", 0], ["active", "=", true]]'
            ),
            "[['probability', '=', 0], ['active', '=', True]]",
        )
        self.assertEqual(
            Dashboard._normalize_ai_domain([["active", "=", False]]),
            "[['active', '=', False]]",
        )
        # null/None must become False so the domain selector maps to
        # "is set" / "is not set" instead of an invalid None literal.
        self.assertEqual(
            Dashboard._normalize_ai_domain('[["lost_reason_id", "!=", null]]'),
            "[['lost_reason_id', '!=', False]]",
        )
        self.assertEqual(
            Dashboard._normalize_ai_domain("[('lost_reason_id', '=', None)]"),
            "[('lost_reason_id', '=', False)]",
        )
        self.assertEqual(
            Dashboard._normalize_ai_domain([["lost_reason_id", "=", None]]),
            "[['lost_reason_id', '=', False]]",
        )
        normalized = Dashboard._normalize_ai_import_payload(
            {
                "version": 1,
                "dashboards": [
                    {
                        "name": "X",
                        "items": [
                            {
                                "name": "Lost",
                                "domain": '[["active", "=", true]]',
                            }
                        ],
                        "filters": [
                            {"name": "Active", "domain": '[["active","=",false]]'}
                        ],
                    }
                ],
            }
        )
        self.assertEqual(
            normalized["dashboards"][0]["items"][0]["domain"],
            "[['active', '=', True]]",
        )
        self.assertEqual(
            normalized["dashboards"][0]["filters"][0]["domain"],
            "[['active', '=', False]]",
        )

    def test_normalize_ai_item_defaults_aggregation(self):
        Dashboard = self.env["boardkit.dashboard"]
        item = Dashboard._normalize_ai_item(
            {
                "name": "Won",
                "item_type": "tile",
                "model": "crm.lead",
                "aggregation": None,
            }
        )
        self.assertEqual(item["aggregation"], "count")
        item_sum = Dashboard._normalize_ai_item(
            {
                "name": "Revenue",
                "item_type": "kpi",
                "model": "sale.order",
                "aggregation": "sum",
            }
        )
        self.assertEqual(item_sum["aggregation"], "count")
        item_ok = Dashboard._normalize_ai_item(
            {
                "name": "Revenue",
                "aggregation": "sum",
                "measure_field_id": "amount_total",
            }
        )
        self.assertEqual(item_ok["aggregation"], "sum")
