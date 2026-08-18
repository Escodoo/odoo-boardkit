# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools import mute_logger


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
        cls.user_ai_only = new_test_user(
            cls.env,
            login="boardkit_ai_only",
            groups=(
                "base.group_user,"
                "boardkit_dashboard.group_dashboard_user,"
                "boardkit_dashboard_ai.group_dashboard_ai_user"
            ),
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
        # String literals must keep words such as "true" / "false" / "null".
        self.assertEqual(
            Dashboard._normalize_ai_domain("[('name', 'ilike', 'true north')]"),
            "[('name', 'ilike', 'true north')]",
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
        self.assertIn("tile", Dashboard._ai_item_types())
        self.assertIn("bar", Dashboard._ai_item_types())
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
        chart = Dashboard._normalize_ai_item({"item_type": "chart"})
        self.assertEqual(chart["item_type"], "bar")
        self.assertEqual(chart["name"], "AI Item")
        graph = Dashboard._normalize_ai_item({"item_type": "graph"})
        self.assertEqual(graph["item_type"], "bar")
        unknown = Dashboard._normalize_ai_item({"item_type": "unknown"})
        self.assertEqual(unknown["item_type"], "tile")
        with_domain_2 = Dashboard._normalize_ai_item(
            {
                "name": "Compare",
                "aggregation_2": "sum",
                "domain_2": '[["active","=",true]]',
            }
        )
        self.assertEqual(with_domain_2["aggregation_2"], "count")
        self.assertEqual(with_domain_2["domain_2"], "[['active', '=', True]]")
        invalid_agg2 = Dashboard._normalize_ai_item({"aggregation_2": "median"})
        self.assertNotIn("aggregation_2", invalid_agg2)

    def test_summarize_and_explain_item(self):
        captured = {}

        def _fake_run(xmlid, record=None, **kwargs):
            captured["xmlid"] = xmlid
            captured["kwargs"] = kwargs
            return {"body": "<p>Summary</p>"}

        with patch.object(
            type(self.env["boardkit.dashboard"]),
            "_run_boardkit_bridge",
            side_effect=_fake_run,
        ):
            summary = self.dashboard.with_user(self.manager).action_ai_summarize(
                {"date_preset": "none"}
            )
            explain = self.dashboard.with_user(self.manager).action_ai_explain_item(
                self.item.id, {"date_preset": "none"}
            )
        self.assertEqual(summary["body"], "<p>Summary</p>")
        self.assertTrue(
            captured["xmlid"].endswith("ai_bridge_boardkit_explain")
            or captured["xmlid"] == "boardkit_dashboard_ai.ai_bridge_boardkit_explain"
        )
        self.assertEqual(explain["body"], "<p>Summary</p>")
        self.assertEqual(captured["kwargs"]["item"]["id"], self.item.id)
        other = (
            self.env["boardkit.dashboard"]
            .with_user(self.manager)
            .create({"name": "Other Board"})
        )
        with self.assertRaises(ValidationError):
            other.with_user(self.manager).action_ai_explain_item(self.item.id, {})

    def test_generate_requires_manager(self):
        with self.assertRaises(AccessError):
            self.env["boardkit.dashboard"].with_user(
                self.user_ai_only
            ).action_ai_generate("Create a board")

    def test_ai_chat_truncates_long_message(self):
        captured = {}

        def _fake_run(xmlid, record=None, **kwargs):
            captured["message"] = kwargs["message"]
            return {"body": "ok", "body_is_html": True, "actions": []}

        long_message = "x" * 2500
        with patch.object(
            type(self.env["boardkit.dashboard"]),
            "_run_boardkit_bridge",
            side_effect=_fake_run,
        ):
            self.dashboard.with_user(self.manager).action_ai_chat({}, long_message, [])
        self.assertEqual(len(captured["message"]), 2000)

    def test_normalize_ai_chat_history_edge_cases(self):
        Dashboard = self.env["boardkit.dashboard"]
        self.assertEqual(Dashboard._normalize_ai_chat_history(None), [])
        self.assertEqual(Dashboard._normalize_ai_chat_history({"role": "user"}), [])
        long_content = "y" * 2500
        history = Dashboard._normalize_ai_chat_history(
            [{"role": "user", "content": long_content}]
        )
        self.assertEqual(len(history[0]["content"]), 2000)

    def test_sanitize_ai_chat_actions_edge_cases(self):
        Dashboard = self.dashboard.with_user(self.manager)
        self.assertEqual(Dashboard._sanitize_ai_chat_actions(None), [])
        self.assertEqual(
            Dashboard._sanitize_ai_chat_actions(
                [{"type": "apply_filters", "filters": "bad"}]
            ),
            [],
        )
        incomplete = Dashboard._sanitize_ai_chat_actions(
            [{"type": "apply_filters", "filters": {"date_preset": "custom"}}]
        )
        self.assertEqual(incomplete, [])
        custom = Dashboard._sanitize_ai_chat_actions(
            [
                {
                    "type": "apply_filters",
                    "filters": {
                        "date_preset": "custom",
                        "date_from": "2026-01-01",
                        "date_to": "2026-01-31",
                        "filter_ids": ["not-an-id"],
                    },
                }
            ]
        )
        self.assertEqual(custom[0]["filters"]["date_from"], "2026-01-01")
        self.assertEqual(custom[0]["filters"]["filter_ids"], [])
        self.assertEqual(
            Dashboard._sanitize_ai_custom_filters("bad", {"res.partner"}), []
        )
        self.assertEqual(
            Dashboard._sanitize_ai_custom_filters(["bad"], {"res.partner"}), []
        )

    def test_compact_item_data_shapes(self):
        Dashboard = self.env["boardkit.dashboard"]
        self.assertEqual(Dashboard._compact_item_data(12), {"value": 12})
        self.assertEqual(
            Dashboard._compact_item_data({"error": "boom"}), {"error": "boom"}
        )
        chart = Dashboard._compact_item_data(
            {
                "type": "bar",
                "value": 3,
                "labels": ["A", "B"],
                "datasets": [{"label": "Qty", "data": [1, 2]}],
            }
        )
        self.assertEqual(chart["labels"], ["A", "B"])
        self.assertEqual(chart["datasets"][0]["data"], [1, 2])
        series = Dashboard._compact_item_data({"series": [1, 2, 3]})
        self.assertEqual(series["series"], [1, 2, 3])
        listing = Dashboard._compact_item_data({"rows": [{"id": 1}]})
        self.assertEqual(listing["rows"], [{"id": 1}])
        mapping = Dashboard._compact_item_data(
            {"regions": [{"id": "BR"}], "points": [{"lat": 1}]}
        )
        self.assertEqual(len(mapping["regions"]), 1)
        self.assertEqual(len(mapping["points"]), 1)

    def test_prepare_ai_generate_examples(self):
        Dashboard = self.env["boardkit.dashboard"].with_user(self.manager)
        examples = Dashboard._prepare_ai_generate_examples(["missing.key"])
        self.assertTrue(isinstance(examples, list))
        examples = Dashboard._prepare_ai_generate_examples([])
        self.assertTrue(isinstance(examples, list))

    def test_normalize_ai_domain_empty_and_tuple(self):
        Dashboard = self.env["boardkit.dashboard"]
        self.assertEqual(Dashboard._normalize_ai_domain(None), "[]")
        self.assertEqual(Dashboard._normalize_ai_domain(""), "[]")
        self.assertEqual(Dashboard._normalize_ai_domain(0), "[]")
        self.assertEqual(
            Dashboard._normalize_ai_domain((("active", "=", True),)),
            "(('active', '=', True),)",
        )
        self.assertEqual(
            Dashboard._ai_domain_pythonize((None, "x")),
            (False, "x"),
        )

    def test_normalize_ai_import_payload_skips_invalid(self):
        Dashboard = self.env["boardkit.dashboard"]
        self.assertEqual(Dashboard._normalize_ai_import_payload("bad"), "bad")
        payload = Dashboard._normalize_ai_import_payload(
            {
                "dashboards": [
                    "skip",
                    {
                        "name": "Ok",
                        "items": ["skip", {"name": "Tile"}],
                        "filters": ["skip", {"name": "F", "domain": None}],
                    },
                ]
            }
        )
        self.assertEqual(len(payload["dashboards"]), 1)
        self.assertEqual(len(payload["dashboards"][0]["items"]), 1)
        self.assertEqual(payload["dashboards"][0]["filters"][0]["domain"], "[]")

    def test_extract_json_payload_nested_and_empty(self):
        Dashboard = self.env["boardkit.dashboard"]
        self.assertFalse(Dashboard._extract_json_payload(""))
        nested = Dashboard._extract_json_payload(
            'prefix {"payload": {"dashboards": [{"name": "Z"}]}} suffix'
        )
        self.assertEqual(nested["dashboards"][0]["name"], "Z")
        self.assertFalse(Dashboard._extract_json_payload('{"name": "no dashboards"}'))

    def test_action_ai_generate_extracts_payload_from_body(self):
        fake_result = {
            "body": (
                '{"version": 1, "dashboards": '
                '[{"name": "From Body", "items": [], "filters": []}]}'
            ),
            "payload": False,
        }
        with patch.object(
            type(self.env["boardkit.dashboard"]),
            "_run_boardkit_bridge",
            return_value=fake_result,
        ):
            result = (
                self.env["boardkit.dashboard"]
                .with_user(self.manager)
                .action_ai_generate("Create from body")
            )
        dashboards = self.env["boardkit.dashboard"].browse(result["dashboard_ids"])
        self.assertEqual(dashboards.name, "From Body")
        with patch.object(
            type(self.env["boardkit.dashboard"]),
            "_run_boardkit_bridge",
            return_value={"body": "no json", "payload": False},
        ):
            with self.assertRaises(UserError):
                self.env["boardkit.dashboard"].with_user(
                    self.manager
                ).action_ai_generate("Create nothing")

    def test_run_boardkit_bridge_errors_and_success(self):
        dashboard = self.dashboard.with_user(self.manager)
        with self.assertRaises(UserError):
            dashboard._run_boardkit_bridge("boardkit_dashboard_ai.missing_bridge")
        bridge = self.env.ref("boardkit_dashboard_ai.ai_bridge_boardkit_summary")
        bridge.active = False
        with self.assertRaises(UserError):
            dashboard._run_boardkit_bridge(
                "boardkit_dashboard_ai.ai_bridge_boardkit_summary"
            )
        bridge.active = True
        execution = MagicMock()
        execution.state = "error"
        execution.error = "timeout"
        execution._execute.return_value = {}
        with (
            mute_logger("odoo.addons.boardkit_dashboard_ai.models.boardkit_dashboard"),
            patch.object(
                type(self.env["ai.bridge.execution"]),
                "create",
                return_value=execution,
            ),
            self.assertRaises(UserError),
        ):
            dashboard._run_boardkit_bridge(
                "boardkit_dashboard_ai.ai_bridge_boardkit_summary"
            )
        execution.state = "done"
        execution._execute.return_value = {"body": "ok"}
        with patch.object(
            type(self.env["ai.bridge.execution"]),
            "create",
            return_value=execution,
        ):
            result = dashboard._run_boardkit_bridge(
                "boardkit_dashboard_ai.ai_bridge_boardkit_summary",
                record=dashboard,
            )
        self.assertEqual(result["body"], "ok")

    def _create_generate_wizard(self, prompt="Create a contacts board"):
        return (
            self.env["boardkit.dashboard.ai.generate.wizard"]
            .with_user(self.manager)
            .create({"prompt": prompt})
        )

    def test_generate_wizard_opens_single_dashboard(self):
        wizard = self._create_generate_wizard()
        fake_result = {
            "dashboard_ids": [self.dashboard.id],
            "body": "<p>Created one board.</p>",
        }
        with patch.object(
            type(self.env["boardkit.dashboard"]),
            "action_ai_generate",
            return_value=fake_result,
        ):
            action = wizard.action_generate()
        self.assertEqual(wizard.dashboard_ids, self.dashboard)
        self.assertEqual(wizard.result_html, "<p>Created one board.</p>")
        self.assertEqual(action["res_model"], "boardkit.dashboard")
        self.assertEqual(action["res_id"], self.dashboard.id)
        self.assertEqual(action["view_mode"], "form")
        open_action = wizard.action_open_dashboards()
        self.assertEqual(open_action["res_id"], self.dashboard.id)

    def test_generate_wizard_stays_open_for_multiple_dashboards(self):
        extra = (
            self.env["boardkit.dashboard"]
            .with_user(self.manager)
            .create({"name": "Second AI Board"})
        )
        wizard = self._create_generate_wizard()
        fake_result = {
            "dashboard_ids": [self.dashboard.id, extra.id],
            "body": False,
        }
        with patch.object(
            type(self.env["boardkit.dashboard"]),
            "action_ai_generate",
            return_value=fake_result,
        ):
            action = wizard.action_generate()
        self.assertEqual(action["res_model"], wizard._name)
        self.assertEqual(action["res_id"], wizard.id)
        self.assertEqual(action["target"], "new")
        self.assertFalse(wizard.result_html)
        open_action = wizard.action_open_dashboards()
        self.assertEqual(open_action["res_model"], "boardkit.dashboard")
        self.assertEqual(open_action["view_mode"], "list,form")
        self.assertEqual(
            open_action["domain"],
            [("id", "in", wizard.dashboard_ids.ids)],
        )
