# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestPalette(BoardkitDashboardCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.palette = cls.env["boardkit.dashboard.palette"].create(
            {
                "name": "Brand",
                "color_ids": [
                    (0, 0, {"sequence": 20, "color": "#222222"}),
                    (0, 0, {"sequence": 10, "color": "#111111"}),
                    (0, 0, {"sequence": 30, "color": "#333333"}),
                ],
            }
        )

    def test_color_list_ordered_by_sequence(self):
        self.assertEqual(self.palette._color_list(), ["#111111", "#222222", "#333333"])

    def test_invalid_color_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["boardkit.dashboard.palette"].create(
                {
                    "name": "Broken",
                    "color_ids": [(0, 0, {"color": "not-a-color"})],
                }
            )

    def test_palette_requires_colors(self):
        with self.assertRaises(ValidationError):
            self.env["boardkit.dashboard.palette"].create({"name": "Empty"})

    def test_palette_copy_renames(self):
        copy = self.palette.copy()
        self.assertEqual(copy.name, "Brand (copy)")
        self.assertEqual(copy._color_list(), self.palette._color_list())

    def test_item_custom_palette_config(self):
        item = self._create_item(
            name="Custom Colors",
            item_type="pie",
            group_by_field_id=self._field("res.partner", "country_id").id,
            color_palette="custom",
            palette_id=self.palette.id,
        )
        config = item._get_config()
        self.assertEqual(config["color_palette"], "custom")
        self.assertEqual(config["palette_colors"], ["#111111", "#222222", "#333333"])

    def test_item_preset_palette_config(self):
        item = self._create_item(
            name="Preset Colors",
            item_type="pie",
            group_by_field_id=self._field("res.partner", "country_id").id,
            color_palette="pastel",
        )
        config = item._get_config()
        self.assertEqual(config["color_palette"], "pastel")
        self.assertFalse(config["palette_colors"])

    def test_item_custom_requires_palette(self):
        with self.assertRaises(ValidationError):
            self._create_item(
                name="Custom Without Palette",
                item_type="pie",
                group_by_field_id=self._field("res.partner", "country_id").id,
                color_palette="custom",
            )

    def test_palette_in_use_cannot_be_deleted(self):
        self._create_item(
            name="Uses Palette",
            item_type="pie",
            group_by_field_id=self._field("res.partner", "country_id").id,
            color_palette="custom",
            palette_id=self.palette.id,
        )
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.palette.unlink()

    def test_new_item_defaults_to_dashboard_palette(self):
        item = self._create_item(
            name="Field Default",
            item_type="pie",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        self.assertEqual(item.color_palette, "dashboard")
        # Without a dashboard default the Odoo preset applies.
        config = item._get_config()
        self.assertEqual(config["color_palette"], "default")
        self.assertFalse(config["palette_colors"])

    def test_item_follows_dashboard_default_preset(self):
        self.dashboard.default_color_palette = "sunset"
        item = self._create_item(
            name="Follows Preset",
            item_type="pie",
            group_by_field_id=self._field("res.partner", "country_id").id,
            color_palette="dashboard",
        )
        config = item._get_config()
        self.assertEqual(config["color_palette"], "sunset")
        self.assertFalse(config["palette_colors"])

    def test_item_follows_dashboard_default_custom(self):
        self.dashboard.write(
            {
                "default_color_palette": "custom",
                "default_palette_id": self.palette.id,
            }
        )
        item = self._create_item(
            name="Follows Custom",
            item_type="pie",
            group_by_field_id=self._field("res.partner", "country_id").id,
            color_palette="dashboard",
        )
        config = item._get_config()
        self.assertEqual(config["color_palette"], "custom")
        self.assertEqual(config["palette_colors"], ["#111111", "#222222", "#333333"])

    def test_item_explicit_palette_overrides_dashboard_default(self):
        self.dashboard.default_color_palette = "sunset"
        item = self._create_item(
            name="Explicit Preset",
            item_type="pie",
            group_by_field_id=self._field("res.partner", "country_id").id,
            color_palette="electric",
        )
        self.assertEqual(item._get_config()["color_palette"], "electric")

    def test_item_follows_new_dashboard_after_move(self):
        other_palette = self.env["boardkit.dashboard.palette"].create(
            {
                "name": "Alt Brand",
                "color_ids": [(0, 0, {"color": "#ABCDEF"})],
            }
        )
        other_dashboard = self.env["boardkit.dashboard"].create(
            {
                "name": "Other Dashboard",
                "default_color_palette": "custom",
                "default_palette_id": other_palette.id,
            }
        )
        item = self._create_item(
            name="Moved Item",
            item_type="pie",
            group_by_field_id=self._field("res.partner", "country_id").id,
            color_palette="dashboard",
        )
        self.assertEqual(item._get_config()["color_palette"], "default")
        item.dashboard_id = other_dashboard
        config = item._get_config()
        self.assertEqual(config["color_palette"], "custom")
        self.assertEqual(config["palette_colors"], ["#ABCDEF"])

    def test_dashboard_default_custom_requires_palette(self):
        with self.assertRaises(ValidationError):
            self.dashboard.default_color_palette = "custom"

    def test_background_style_defaults_to_palette(self):
        item = self._create_item(name="Themed Tile", item_type="tile")
        self.assertEqual(item.background_style, "palette")
        self.assertEqual(item._get_config()["background_style"], "palette")

    def test_background_style_manual_in_config(self):
        item = self._create_item(
            name="Manual Tile",
            item_type="tile",
            background_style="manual",
            background_color="#123123",
        )
        config = item._get_config()
        self.assertEqual(config["background_style"], "manual")
        self.assertEqual(config["background_color"], "#123123")

    def test_company_default_palette_applied_on_create(self):
        self.env.company.boardkit_default_color_palette = "ocean"
        dashboard = self.env["boardkit.dashboard"].create(
            {"name": "Inherits Company Default"}
        )
        self.assertEqual(dashboard.default_color_palette, "ocean")
        self.assertFalse(dashboard.default_palette_id)

    def test_company_default_custom_palette_applied_on_create(self):
        self.env.company.write(
            {
                "boardkit_default_color_palette": "custom",
                "boardkit_default_palette_id": self.palette.id,
            }
        )
        dashboard = self.env["boardkit.dashboard"].create(
            {"name": "Inherits Company Custom"}
        )
        self.assertEqual(dashboard.default_color_palette, "custom")
        self.assertEqual(dashboard.default_palette_id, self.palette)

    def test_explicit_palette_overrides_company_default(self):
        self.env.company.boardkit_default_color_palette = "ocean"
        dashboard = self.env["boardkit.dashboard"].create(
            {
                "name": "Explicit Palette",
                "default_color_palette": "pastel",
            }
        )
        self.assertEqual(dashboard.default_color_palette, "pastel")

    def test_company_default_change_does_not_update_existing(self):
        self.env.company.boardkit_default_color_palette = "ocean"
        dashboard = self.env["boardkit.dashboard"].create(
            {"name": "Snapshot Palette"}
        )
        self.assertEqual(dashboard.default_color_palette, "ocean")
        self.env.company.boardkit_default_color_palette = "sunset"
        self.assertEqual(dashboard.default_color_palette, "ocean")

    def test_copy_keeps_source_palette_not_company_default(self):
        self.env.company.boardkit_default_color_palette = "ocean"
        source = self.env["boardkit.dashboard"].create(
            {
                "name": "Source Palette",
                "default_color_palette": "pastel",
            }
        )
        self.env.company.boardkit_default_color_palette = "sunset"
        copy = source.copy()
        self.assertEqual(copy.default_color_palette, "pastel")

    def test_company_default_custom_requires_palette(self):
        with self.assertRaises(ValidationError):
            self.env.company.boardkit_default_color_palette = "custom"

    def test_default_get_uses_company_default_palette(self):
        self.env.company.write(
            {
                "boardkit_default_color_palette": "custom",
                "boardkit_default_palette_id": self.palette.id,
            }
        )
        defaults = self.env["boardkit.dashboard"].default_get(
            ["default_color_palette", "default_palette_id"]
        )
        self.assertEqual(defaults.get("default_color_palette"), "custom")
        self.assertEqual(defaults.get("default_palette_id"), self.palette.id)

    def test_settings_save_custom_palette_atomically(self):
        """Settings must write palette key + Many2one together.

        Related inverses update company field-by-field and trip the company
        constraint when Custom is stored before the palette id.
        """
        settings = self.env["res.config.settings"].create(
            {
                "boardkit_default_color_palette": "custom",
                "boardkit_default_palette_id": self.palette.id,
            }
        )
        settings.set_values()
        self.assertEqual(self.env.company.boardkit_default_color_palette, "custom")
        self.assertEqual(self.env.company.boardkit_default_palette_id, self.palette)
