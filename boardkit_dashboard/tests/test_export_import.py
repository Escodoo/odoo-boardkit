# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestExportImport(BoardkitDashboardCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.chart = cls._create_item(
            name="By Country",
            item_type="bar",
            aggregation="sum",
            group_by_field_id=cls._field("res.partner", "country_id").id,
            measure_ids=[
                (0, 0, {"field_id": cls._field("res.partner", "partner_latitude").id})
            ],
        )
        cls.env["boardkit.dashboard.filter"].create(
            {
                "name": "Companies",
                "dashboard_id": cls.dashboard.id,
                "model_id": cls.env.ref("base.model_res_partner").id,
                "domain": "[('is_company', '=', True)]",
            }
        )
        cls.dashboard.layout_json = json.dumps(
            {str(cls.tile.id): {"x": 0, "y": 0, "w": 3, "h": 2}}
        )

    def test_export_structure(self):
        payload = self.dashboard.export_config()
        self.assertEqual(payload["version"], 1)
        self.assertEqual(len(payload["dashboards"]), 1)
        data = payload["dashboards"][0]
        self.assertEqual(data["name"], "Test Dashboard")
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(len(data["filters"]), 1)
        chart_data = next(item for item in data["items"] if item["item_type"] == "bar")
        self.assertEqual(chart_data["model"], "res.partner")
        self.assertEqual(chart_data["group_by_field_id"], "country_id")
        self.assertEqual(chart_data["measures"], ["partner_latitude"])

    def test_import_round_trip(self):
        payload = self.dashboard.export_config()
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        self.assertEqual(len(imported), 1)
        self.assertEqual(len(imported.item_ids), 2)
        self.assertEqual(len(imported.filter_ids), 1)
        chart = imported.item_ids.filtered(lambda item: item.item_type == "bar")
        self.assertEqual(chart.model_name, "res.partner")
        self.assertEqual(chart.group_by_field_id.name, "country_id")
        self.assertEqual(
            chart.measure_ids.mapped("field_id.name"), ["partner_latitude"]
        )
        # The layout follows the new item ids.
        layout = json.loads(imported.layout_json)
        tile = imported.item_ids.filtered(lambda item: item.item_type == "tile")
        self.assertEqual(layout[str(tile.id)], {"x": 0, "y": 0, "w": 3, "h": 2})
        # Imported data still computes.
        self.assertEqual(tile.get_data()["value"], 3)

    def test_description_and_tags_export_import(self):
        tag = self.env["boardkit.dashboard.tag"].create(
            {"name": "Finance", "icon": "fa-money"}
        )
        self.dashboard.write(
            {
                "description": "Finance KPIs at a glance",
                "tag_ids": [(6, 0, tag.ids)],
            }
        )
        payload = self.dashboard.export_config()
        data = payload["dashboards"][0]
        self.assertEqual(data["description"], "Finance KPIs at a glance")
        self.assertEqual(data["tags"], [{"name": "Finance", "icon": "fa-money"}])

        # Drop the tag so import must recreate it by name.
        tag.unlink()
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        self.assertEqual(imported.description, "Finance KPIs at a glance")
        self.assertEqual(imported.tag_ids.mapped("name"), ["Finance"])
        self.assertEqual(imported.tag_ids.icon, "fa-money")
        self.assertEqual(imported.kanban_icon, "fa-money")

    def test_import_legacy_string_tags_seeds_icon(self):
        """Template-style string tags still create tags and seed known icons."""
        payload = {
            "version": 1,
            "dashboards": [
                {
                    "name": "Legacy Tags Board",
                    "tags": ["CRM"],
                    "items": [],
                }
            ],
        }
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        self.assertEqual(imported.tag_ids.name, "CRM")
        self.assertEqual(imported.tag_ids.icon, "fa-bullseye")
        self.assertEqual(imported.kanban_icon, "fa-bullseye")

    def test_import_does_not_overwrite_existing_tag_icon(self):
        tag = self.env["boardkit.dashboard.tag"].create(
            {"name": "Keep My Icon", "icon": "fa-cogs"}
        )
        payload = {
            "version": 1,
            "dashboards": [
                {
                    "name": "Keep Icon Board",
                    "tags": [{"name": "Keep My Icon", "icon": "fa-bullseye"}],
                    "items": [],
                }
            ],
        }
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        self.assertEqual(imported.tag_ids, tag)
        self.assertEqual(tag.icon, "fa-cogs")

    def test_board_icon_export_import(self):
        tag = self.env["boardkit.dashboard.tag"].create(
            {"name": "Override Domain", "icon": "fa-bullseye"}
        )
        self.dashboard.write(
            {
                "tag_ids": [(6, 0, tag.ids)],
                "icon": "fa-plane",
            }
        )
        payload = self.dashboard.export_config()
        self.assertEqual(payload["dashboards"][0]["icon"], "fa-plane")
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        self.assertEqual(imported.icon, "fa-plane")
        self.assertEqual(imported.kanban_icon, "fa-plane")

    def test_import_leaves_board_hidden(self):
        """Imported boards must be reviewed before users can reach them."""
        payload = self.dashboard.export_config()
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        self.assertFalse(imported.published)
        self.assertFalse(imported.menu_parent_id)
        self.assertFalse(imported.menu_id)

    def test_import_invalid_payload(self):
        with self.assertRaises(ValidationError):
            self.env["boardkit.dashboard"].import_config({"bogus": True})

    def test_import_skips_unknown_model(self):
        payload = self.dashboard.export_config()
        payload["dashboards"][0]["items"].append(
            {"name": "Ghost", "item_type": "tile", "model": "model.that.does.not.exist"}
        )
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        self.assertEqual(len(imported.item_ids), 2)

    def test_chart_overlay_flags_export_import(self):
        item = self._create_item(
            name="Overlay Chart",
            item_type="area",
            group_by_field_id=self._field("res.partner", "country_id").id,
            show_average_line=True,
            show_trend_line=True,
        )
        payload = self.dashboard.export_config()
        exported = next(
            entry
            for entry in payload["dashboards"][0]["items"]
            if entry["name"] == item.name
        )
        self.assertTrue(exported["show_average_line"])
        self.assertTrue(exported["show_trend_line"])
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        imported_item = imported.item_ids.filtered(lambda rec: rec.name == item.name)
        self.assertTrue(imported_item.show_average_line)
        self.assertTrue(imported_item.show_trend_line)

    def test_custom_date_filter_export_import(self):
        item = self._create_item(
            name="Custom Dates",
            item_type="tile",
            date_field_id=self._field("res.partner", "create_date").id,
            date_filter="custom",
            date_from="2026-01-01 00:00:00",
            date_to="2026-12-31 23:59:59",
        )
        payload = self.dashboard.export_config()
        exported = next(
            entry
            for entry in payload["dashboards"][0]["items"]
            if entry["name"] == item.name
        )
        self.assertEqual(exported["date_filter"], "custom")
        self.assertTrue(exported["date_from"])
        self.assertTrue(exported["date_to"])
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        imported_item = imported.item_ids.filtered(lambda rec: rec.name == item.name)
        self.assertEqual(imported_item.date_filter, "custom")
        self.assertEqual(
            fields.Datetime.to_string(imported_item.date_from),
            "2026-01-01 00:00:00",
        )
        self.assertEqual(
            fields.Datetime.to_string(imported_item.date_to),
            "2026-12-31 23:59:59",
        )

    def test_list_columns_export_import_preserves_order(self):
        item = self._create_item(
            name="Ordered List",
            item_type="list",
            list_type="plain",
            list_column_ids=[
                (
                    0,
                    0,
                    {
                        "sequence": 10,
                        "field_id": self._field("res.partner", "country_id").id,
                    },
                ),
                (
                    0,
                    0,
                    {"sequence": 20, "field_id": self._field("res.partner", "name").id},
                ),
                (
                    0,
                    0,
                    {
                        "sequence": 30,
                        "field_id": self._field("res.partner", "email").id,
                    },
                ),
            ],
        )
        payload = self.dashboard.export_config()
        exported = next(
            entry
            for entry in payload["dashboards"][0]["items"]
            if entry["name"] == item.name
        )
        self.assertEqual(exported["list_columns"], ["country_id", "name", "email"])
        self.assertNotIn("list_field_ids", exported)

        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        imported_list = imported.item_ids.filtered(lambda rec: rec.name == item.name)
        self.assertEqual(
            imported_list.list_column_ids.mapped("field_id.name"),
            ["country_id", "name", "email"],
        )
        self.assertEqual(imported_list.list_column_ids.mapped("sequence"), [10, 20, 30])

    def test_import_legacy_list_field_ids(self):
        # Older JSON exports used an unordered many2many key.
        payload = {
            "version": 1,
            "dashboards": [
                {
                    "name": "Legacy List Dashboard",
                    "items": [
                        {
                            "name": "Legacy List",
                            "item_type": "list",
                            "list_type": "plain",
                            "model": "res.partner",
                            "list_field_ids": ["email", "name"],
                        }
                    ],
                }
            ],
        }
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        item = self.env["boardkit.dashboard"].browse(new_ids).item_ids
        self.assertEqual(
            item.list_column_ids.mapped("field_id.name"), ["email", "name"]
        )
        self.assertEqual(item.list_column_ids.mapped("sequence"), [10, 20])

    def test_measures_export_import_preserves_order(self):
        item = self._create_item(
            name="Ordered Measures",
            item_type="bar",
            aggregation="sum",
            group_by_field_id=self._field("res.partner", "country_id").id,
            measure_ids=[
                (
                    0,
                    0,
                    {
                        "sequence": 10,
                        "field_id": self._field("res.partner", "partner_longitude").id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "sequence": 20,
                        "field_id": self._field("res.partner", "partner_latitude").id,
                    },
                ),
            ],
        )
        payload = self.dashboard.export_config()
        exported = next(
            entry
            for entry in payload["dashboards"][0]["items"]
            if entry["name"] == item.name
        )
        self.assertEqual(
            exported["measures"], ["partner_longitude", "partner_latitude"]
        )
        self.assertNotIn("measure_field_ids", exported)

        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        imported_item = imported.item_ids.filtered(lambda rec: rec.name == item.name)
        self.assertEqual(
            imported_item.measure_ids.mapped("field_id.name"),
            ["partner_longitude", "partner_latitude"],
        )
        self.assertEqual(imported_item.measure_ids.mapped("sequence"), [10, 20])

    def test_import_legacy_measure_field_ids(self):
        # Older JSON exports used an unordered many2many key.
        payload = {
            "version": 1,
            "dashboards": [
                {
                    "name": "Legacy Measures Dashboard",
                    "items": [
                        {
                            "name": "Legacy Chart",
                            "item_type": "bar",
                            "aggregation": "sum",
                            "model": "res.partner",
                            "group_by_field_id": "country_id",
                            "measure_field_ids": [
                                "partner_longitude",
                                "partner_latitude",
                            ],
                        }
                    ],
                }
            ],
        }
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        item = self.env["boardkit.dashboard"].browse(new_ids).item_ids
        self.assertEqual(
            item.measure_ids.mapped("field_id.name"),
            ["partner_longitude", "partner_latitude"],
        )
        self.assertEqual(item.measure_ids.mapped("sequence"), [10, 20])

    def test_custom_palette_export_import(self):
        palette = self.env["boardkit.dashboard.palette"].create(
            {
                "name": "Brand Export",
                "color_ids": [
                    (0, 0, {"sequence": 10, "color": "#005B96"}),
                    (0, 0, {"sequence": 20, "color": "#6497B1"}),
                ],
            }
        )
        item = self._create_item(
            name="Palette Chart",
            item_type="pie",
            group_by_field_id=self._field("res.partner", "country_id").id,
            color_palette="custom",
            palette_id=palette.id,
        )
        payload = self.dashboard.export_config()
        data = payload["dashboards"][0]
        self.assertIn(
            {"name": "Brand Export", "colors": ["#005B96", "#6497B1"]},
            data["palettes"],
        )
        exported = next(entry for entry in data["items"] if entry["name"] == item.name)
        self.assertEqual(exported["color_palette"], "custom")
        self.assertEqual(exported["palette"], "Brand Export")
        # Rename the source palette so the import has to recreate it by name.
        palette.name = "Brand Renamed"
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        imported_item = imported.item_ids.filtered(lambda rec: rec.name == item.name)
        self.assertEqual(imported_item.color_palette, "custom")
        self.assertEqual(imported_item.palette_id.name, "Brand Export")
        self.assertNotEqual(imported_item.palette_id, palette)
        self.assertEqual(imported_item.palette_id._color_list(), ["#005B96", "#6497B1"])

    def test_dashboard_default_palette_export_import(self):
        palette = self.env["boardkit.dashboard.palette"].create(
            {
                "name": "Default Export",
                "color_ids": [(0, 0, {"color": "#123456"})],
            }
        )
        self.dashboard.write(
            {
                "default_color_palette": "custom",
                "default_palette_id": palette.id,
            }
        )
        payload = self.dashboard.export_config()
        data = payload["dashboards"][0]
        self.assertEqual(data["default_color_palette"], "custom")
        self.assertEqual(data["default_palette"], "Default Export")
        self.assertIn(
            {"name": "Default Export", "colors": ["#123456"]}, data["palettes"]
        )
        # Rename the source palette so the import has to recreate it by name.
        palette.name = "Default Renamed"
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        self.assertEqual(imported.default_color_palette, "custom")
        self.assertEqual(imported.default_palette_id.name, "Default Export")
        self.assertEqual(imported.default_palette_id._color_list(), ["#123456"])

    def test_dashboard_default_preset_export_import(self):
        self.dashboard.default_color_palette = "earth"
        payload = self.dashboard.export_config()
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        self.assertEqual(imported.default_color_palette, "earth")
        self.assertFalse(imported.default_palette_id)

    def test_background_style_export_import(self):
        manual = self._create_item(
            name="Manual Tile",
            item_type="tile",
            background_style="manual",
            background_color="#123123",
            font_color="#FFFFFF",
        )
        payload = self.dashboard.export_config()
        exported = next(
            entry
            for entry in payload["dashboards"][0]["items"]
            if entry["name"] == manual.name
        )
        self.assertEqual(exported["background_style"], "manual")
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        imported_manual = imported.item_ids.filtered(
            lambda rec: rec.name == manual.name
        )
        self.assertEqual(imported_manual.background_style, "manual")
        self.assertEqual(imported_manual.background_color, "#123123")
        # The setUp tile keeps the palette default through the round trip.
        imported_tile = imported.item_ids.filtered(
            lambda rec: rec.name == self.tile.name
        )
        self.assertEqual(imported_tile.background_style, "palette")

    def test_custom_palette_import_fallback(self):
        payload = {
            "version": 1,
            "dashboards": [
                {
                    "name": "Palette Fallback",
                    "items": [
                        {
                            "name": "Ghost Palette",
                            "item_type": "pie",
                            "model": "res.partner",
                            "group_by_field_id": "country_id",
                            "color_palette": "custom",
                            "palette": "Does Not Exist",
                        }
                    ],
                }
            ],
        }
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        item = self.env["boardkit.dashboard"].browse(new_ids).item_ids
        self.assertEqual(item.color_palette, "default")
        self.assertFalse(item.palette_id)

    def test_map_points_export_import(self):
        item = self._create_item(
            name="Map Points",
            item_type="map",
            map_mode="points",
            latitude_field_id=self._field("res.partner", "partner_latitude").id,
            longitude_field_id=self._field("res.partner", "partner_longitude").id,
            map_focus_country_id=self.country_br.id,
        )
        payload = self.dashboard.export_config()
        exported = next(
            entry
            for entry in payload["dashboards"][0]["items"]
            if entry["name"] == item.name
        )
        self.assertEqual(exported["map_mode"], "points")
        self.assertEqual(exported["latitude_field_id"], "partner_latitude")
        self.assertEqual(exported["longitude_field_id"], "partner_longitude")
        self.assertEqual(exported["map_focus_country_id"], "BR")
        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        imported_item = imported.item_ids.filtered(lambda rec: rec.name == item.name)
        self.assertEqual(imported_item.map_mode, "points")
        self.assertEqual(imported_item.latitude_field_id.name, "partner_latitude")
        self.assertEqual(imported_item.longitude_field_id.name, "partner_longitude")
        self.assertEqual(imported_item.map_focus_country_id, self.country_br)
        data = imported_item.get_data()
        self.assertEqual(data["mode"], "points")
        self.assertEqual(len(data["points"]), 3)


@tagged("post_install", "-at_install")
class TestImportHttp(HttpCase):
    """Cover the uploader behind the Import button of the catalogue toolbar."""

    def setUp(self):
        super().setUp()
        self.dashboard = self.env["boardkit.dashboard"].create(
            {"name": "Import Source", "published": True}
        )
        self.env["boardkit.dashboard.item"].create(
            {
                "name": "Import Tile",
                "dashboard_id": self.dashboard.id,
                "item_type": "tile",
                "model_id": self.env.ref("base.model_res_partner").id,
                "aggregation": "count",
            }
        )
        self.authenticate("admin", "admin")

    def _upload(self, content, filename="dashboards.json"):
        return self.url_open(
            "/boardkit_dashboard/import",
            data={"csrf_token": http.Request.csrf_token(self)},
            files={"ufile": (filename, content, "application/json")},
        )

    def test_import_upload(self):
        payload = json.dumps(self.dashboard.export_config()).encode()
        response = self._upload(payload)
        self.assertEqual(response.status_code, 200)
        dashboard_ids = response.json()["dashboard_ids"]
        self.assertEqual(len(dashboard_ids), 1)
        imported = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(imported.name, "Import Source")
        self.assertEqual(len(imported.item_ids), 1)
        self.assertFalse(imported.menu_parent_id)
        self.assertFalse(imported.menu_id)

    def test_import_upload_multiple_dashboards(self):
        payload = self.dashboard.export_config()
        second = self.env["boardkit.dashboard"].create({"name": "Second Source"})
        payload["dashboards"].append(second.export_config()["dashboards"][0])
        response = self._upload(json.dumps(payload).encode())
        self.assertEqual(len(response.json()["dashboard_ids"]), 2)

    def test_import_upload_invalid_json(self):
        response = self._upload(b"not json at all")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["error"])

    def test_import_upload_invalid_payload(self):
        before = self.env["boardkit.dashboard"].search_count([])
        response = self._upload(json.dumps({"bogus": True}).encode())
        self.assertTrue(response.json()["error"])
        self.assertEqual(self.env["boardkit.dashboard"].search_count([]), before)
