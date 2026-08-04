# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import Form, tagged

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestItemPreview(BoardkitDashboardCommon):
    def test_preview_payload_saved_record(self):
        payload = self.tile.preview_json
        self.assertEqual(payload["config"]["type"], "tile")
        self.assertEqual(payload["config"]["id"], self.tile.id)
        self.assertEqual(payload["data"]["value"], 3)
        self.assertIn("symbol", payload["currency"])

    def test_preview_payload_virtual_record(self):
        item = self.env["boardkit.dashboard.item"].new(
            {
                "name": "Virtual",
                "dashboard_id": self.dashboard.id,
                "item_type": "tile",
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain": self.base_domain,
                "aggregation": "count",
            }
        )
        payload = item.preview_json
        self.assertEqual(payload["config"]["id"], 0)
        self.assertEqual(payload["data"]["value"], 3)

    def test_preview_incomplete_config(self):
        item = self.env["boardkit.dashboard.item"].new({"item_type": "tile"})
        self.assertFalse(item.preview_json)

    def test_preview_error_rendered_in_card(self):
        # A bar chart without Group By must show the error in the preview
        # instead of raising in the form onchange.
        item = self._create_item(name="Broken Chart", item_type="bar")
        payload = item.preview_json
        self.assertEqual(payload["config"]["type"], "bar")
        self.assertIn("error", payload["data"])

    def test_preview_chart_payload(self):
        item = self._create_item(
            name="By Country",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        payload = item.preview_json
        self.assertEqual(payload["data"]["type"], "chart")
        self.assertEqual(set(payload["data"]["labels"]), {"Brazil", "United States"})

    def test_preview_depends_on_overlay_flags(self):
        item = self._create_item(
            name="Overlay Preview",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        self.assertFalse(item.preview_json["config"]["show_average_line"])
        self.assertFalse(item.preview_json["config"]["show_trend_line"])
        item.write({"show_average_line": True, "show_trend_line": True})
        config = item.preview_json["config"]
        self.assertTrue(config["show_average_line"])
        self.assertTrue(config["show_trend_line"])

    def test_preview_updates_in_form(self):
        form = Form(
            self.env["boardkit.dashboard.item"].with_context(
                default_dashboard_id=self.dashboard.id
            )
        )
        form.name = "Form Preview"
        form.model_id = self.env.ref("base.model_res_partner")
        payload = form.preview_json
        self.assertEqual(payload["config"]["type"], "tile")
        self.assertGreaterEqual(payload["data"]["value"], 3)
        # Narrowing the domain refreshes the preview data.
        form.domain = self.base_domain
        self.assertEqual(form.preview_json["data"]["value"], 3)

    def test_preview_reflects_column_resequence(self):
        item = self._create_item(
            name="Preview Column Order",
            item_type="list",
            list_type="plain",
            list_column_ids=[
                (
                    0,
                    0,
                    {
                        "sequence": 10,
                        "field_id": self._field("res.partner", "name").id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "sequence": 20,
                        "field_id": self._field("res.partner", "country_id").id,
                    },
                ),
            ],
        )
        columns = [c["name"] for c in item.preview_json["data"]["columns"]]
        self.assertEqual(columns, ["name", "country_id"])
        with Form(item) as item_form:
            # Move the name column after country, like the handle drag does.
            with item_form.list_column_ids.edit(0) as line:
                line.sequence = 30
            columns = [
                column["name"] for column in item_form.preview_json["data"]["columns"]
            ]
            self.assertEqual(columns, ["country_id", "name"])
