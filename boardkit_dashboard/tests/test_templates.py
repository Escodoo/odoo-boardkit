# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestDashboardTemplates(BoardkitDashboardCommon):
    def test_create_from_template_unpublished_with_items(self):
        template = self.env.ref("boardkit_dashboard.template_partner_starter")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Partner Starter")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertFalse(dashboard.group_ids)
        self.assertEqual(len(dashboard.item_ids), 3)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "tile"))
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "kpi"))

    def test_create_from_template_name_override(self):
        template = self.env.ref("boardkit_dashboard.template_partner_starter")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(
            template.id, name="My Custom Board"
        )
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(dashboard.name, "My Custom Board")

    def test_create_from_template_copies_allowed_groups(self):
        template = self.env.ref("boardkit_dashboard.template_partner_starter")
        group = self.env.ref("base.group_system")
        template.group_ids = [(6, 0, group.ids)]
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(dashboard.group_ids, group)

    def test_create_from_template_contacts_overview(self):
        template = self.env.ref("boardkit_dashboard.template_contacts_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertFalse(dashboard.group_ids)
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertEqual(len(dashboard.filter_ids), 4)
        maps = dashboard.item_ids.filtered(lambda i: i.item_type == "map")
        self.assertEqual(len(maps), 2)
        regions = maps.filtered(lambda i: i.map_mode == "regions")
        points = maps.filtered(lambda i: i.map_mode == "points")
        self.assertEqual(regions.group_by_field_id.name, "country_id")
        self.assertEqual(points.latitude_field_id.name, "partner_latitude")
        self.assertEqual(points.longitude_field_id.name, "partner_longitude")
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "kpi"))

    def test_create_from_template_invalid_payload(self):
        template = self.env["boardkit.dashboard.template"].create(
            {
                "name": "Broken",
                "key": "broken_template_test",
                "payload": {"version": 1},
            }
        )
        with self.assertRaises(ValidationError):
            self.env["boardkit.dashboard"].create_from_template(template.id)

    def test_wizard_creates_dashboard(self):
        template = self.env.ref("boardkit_dashboard.template_partner_starter")
        wizard = (
            self.env["boardkit.dashboard.template.wizard"]
            .with_user(self.manager)
            .create(
                {
                    "template_id": template.id,
                    "name": "Wizard Board",
                }
            )
        )
        action = wizard.action_create()
        self.assertEqual(action["res_model"], "boardkit.dashboard")
        dashboard = self.env["boardkit.dashboard"].browse(action["res_id"])
        self.assertEqual(dashboard.name, "Wizard Board")
        self.assertFalse(dashboard.published)

    def test_user_cannot_create_from_template(self):
        template = self.env.ref("boardkit_dashboard.template_partner_starter")
        with self.assertRaises(AccessError):
            self.env["boardkit.dashboard"].with_user(self.user).create_from_template(
                template.id
            )

    def test_user_cannot_use_wizard(self):
        template = self.env.ref("boardkit_dashboard.template_partner_starter")
        with self.assertRaises(AccessError):
            self.env["boardkit.dashboard.template.wizard"].with_user(self.user).create(
                {"template_id": template.id}
            )

    def test_get_featured_for_catalogue(self):
        from ..models.boardkit_dashboard import FEATURED_TEMPLATE_KEYS

        featured = self.env["boardkit.dashboard.template"].get_featured_for_catalogue()
        keys = [row["key"] for row in featured]
        # Core templates shipped with boardkit_dashboard; satellite keys are
        # included only when those modules are installed.
        self.assertIn("partner_starter", keys)
        self.assertIn("contacts_overview", keys)
        expected = [key for key in FEATURED_TEMPLATE_KEYS if key in keys]
        self.assertEqual(keys, expected)
        partner = next(row for row in featured if row["key"] == "partner_starter")
        self.assertEqual(partner["name"], "Partner Starter")
        self.assertIn("id", partner)

    def test_get_featured_for_catalogue_skips_inactive_templates(self):
        """Missing or inactive featured keys are skipped, not raised."""
        partner = self.env.ref("boardkit_dashboard.template_partner_starter")
        partner.active = False
        featured = self.env["boardkit.dashboard.template"].get_featured_for_catalogue()
        self.assertNotIn("partner_starter", [row["key"] for row in featured])
        self.assertIn("contacts_overview", [row["key"] for row in featured])
