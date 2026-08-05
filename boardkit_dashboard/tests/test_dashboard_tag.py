# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from .common import BoardkitDashboardCommon

KEY_COLOR = "boardkit_dashboard.tag_color0_migrated"
KEY_ICON = "boardkit_dashboard.tag_icon_seeded"


@tagged("post_install", "-at_install")
class TestDashboardTag(BoardkitDashboardCommon):
    def _unset_param(self, key):
        self.env["ir.config_parameter"].sudo().search([("key", "=", key)]).unlink()

    def test_suggested_icon_for_name(self):
        Tag = self.env["boardkit.dashboard.tag"]
        self.assertFalse(Tag.suggested_icon_for_name(False))
        self.assertFalse(Tag.suggested_icon_for_name(""))
        self.assertFalse(Tag.suggested_icon_for_name("Unknown Tag"))
        self.assertEqual(Tag.suggested_icon_for_name("CRM"), "fa-bullseye")
        self.assertEqual(
            Tag.suggested_icon_for_name("  Purchase "), "fa-shopping-basket"
        )

    def test_init_reassigns_legacy_color_zero(self):
        Tag = self.env["boardkit.dashboard.tag"]
        tag = Tag.create({"name": "Legacy Color", "color": 0})
        self._unset_param(KEY_COLOR)
        Tag.init()
        tag.invalidate_recordset(["color"])
        self.assertNotEqual(tag.color, 0)
        self.assertTrue(
            self.env["ir.config_parameter"].sudo().get_param(KEY_COLOR),
        )

    def test_init_skips_color_migration_when_already_done(self):
        Tag = self.env["boardkit.dashboard.tag"]
        self.env["ir.config_parameter"].sudo().set_param(KEY_COLOR, "1")
        tag = Tag.create({"name": "Keep Hidden", "color": 0})
        Tag.init()
        self.assertEqual(tag.color, 0)

    def test_init_seeds_icons_for_known_tag_names(self):
        Tag = self.env["boardkit.dashboard.tag"]
        crm = Tag.create({"name": "CRM", "icon": False})
        custom = Tag.create({"name": "My Custom Domain", "icon": False})
        self._unset_param(KEY_ICON)
        Tag.init()
        self.assertEqual(crm.icon, "fa-bullseye")
        self.assertFalse(custom.icon)
        self.assertTrue(
            self.env["ir.config_parameter"].sudo().get_param(KEY_ICON),
        )

    def test_init_skips_icon_seed_when_already_done(self):
        Tag = self.env["boardkit.dashboard.tag"]
        self.env["ir.config_parameter"].sudo().set_param(KEY_ICON, "1")
        tag = Tag.create({"name": "CRM", "icon": False})
        Tag.init()
        self.assertFalse(tag.icon)
