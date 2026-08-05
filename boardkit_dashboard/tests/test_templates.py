# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestDashboardTemplates(BoardkitDashboardCommon):
    def test_create_from_template_unpublished_with_items(self):
        template = self.env.ref("boardkit_dashboard.template_contacts_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(len(dashboard), 1)
        self.assertEqual(dashboard.name, "Contacts Overview")
        self.assertFalse(dashboard.published)
        self.assertFalse(dashboard.menu_id)
        self.assertFalse(dashboard.group_ids)
        self.assertEqual(len(dashboard.item_ids), 13)
        self.assertEqual(len(dashboard.filter_ids), 4)
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "tile"))
        self.assertTrue(dashboard.item_ids.filtered(lambda i: i.item_type == "kpi"))
        maps = dashboard.item_ids.filtered(lambda i: i.item_type == "map")
        self.assertEqual(len(maps), 2)
        regions = maps.filtered(lambda i: i.map_mode == "regions")
        points = maps.filtered(lambda i: i.map_mode == "points")
        self.assertEqual(regions.group_by_field_id.name, "country_id")
        self.assertEqual(points.latitude_field_id.name, "partner_latitude")
        self.assertEqual(points.longitude_field_id.name, "partner_longitude")

    def test_create_from_template_name_override(self):
        template = self.env.ref("boardkit_dashboard.template_contacts_overview")
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(
            template.id, name="My Custom Board"
        )
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(dashboard.name, "My Custom Board")

    def test_create_from_template_copies_allowed_groups(self):
        template = self.env.ref("boardkit_dashboard.template_contacts_overview")
        group = self.env.ref("base.group_system")
        template.group_ids = [(6, 0, group.ids)]
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(template.id)
        dashboard = self.env["boardkit.dashboard"].browse(dashboard_ids)
        self.assertEqual(dashboard.group_ids, group)

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
        template = self.env.ref("boardkit_dashboard.template_contacts_overview")
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
        template = self.env.ref("boardkit_dashboard.template_contacts_overview")
        with self.assertRaises(AccessError):
            self.env["boardkit.dashboard"].with_user(self.user).create_from_template(
                template.id
            )

    def test_user_cannot_use_wizard(self):
        template = self.env.ref("boardkit_dashboard.template_contacts_overview")
        with self.assertRaises(AccessError):
            self.env["boardkit.dashboard.template.wizard"].with_user(self.user).create(
                {"template_id": template.id}
            )

    def test_get_featured_for_catalogue(self):
        from ..models.boardkit_dashboard import FEATURED_TEMPLATE_KEYS

        featured = self.env["boardkit.dashboard.template"].get_featured_for_catalogue()
        keys = [row["key"] for row in featured]
        # Core template shipped with boardkit_dashboard; satellite keys are
        # included only when those modules are installed.
        self.assertIn("contacts_overview", keys)
        self.assertNotIn("partner_starter", keys)
        expected = [key for key in FEATURED_TEMPLATE_KEYS if key in keys]
        self.assertEqual(keys, expected)
        contacts = next(row for row in featured if row["key"] == "contacts_overview")
        self.assertEqual(contacts["name"], "Contacts Overview")
        self.assertIn("id", contacts)

    def test_get_featured_for_catalogue_skips_inactive_templates(self):
        """Missing or inactive featured keys are skipped, not raised."""
        contacts = self.env.ref("boardkit_dashboard.template_contacts_overview")
        contacts.active = False
        featured = self.env["boardkit.dashboard.template"].get_featured_for_catalogue()
        self.assertNotIn("contacts_overview", [row["key"] for row in featured])

    def test_load_demo_from_template_matches_and_configures_menu(self):
        """Demo loader builds a published board from the template with menu."""
        demo = self.env.ref(
            "boardkit_dashboard.dashboard_demo", raise_if_not_found=False
        )
        if demo:
            demo.unlink()
        self.env["boardkit.dashboard"]._load_demo_from_template(
            {
                "template_xmlid": "boardkit_dashboard.template_contacts_overview",
                "demo_xmlid": "boardkit_dashboard.dashboard_demo",
                "menu_parent_xmlid": "contacts.menu_contacts",
                "menu_sequence": -1,
            }
        )
        demo = self.env.ref("boardkit_dashboard.dashboard_demo")
        template = self.env.ref("boardkit_dashboard.template_contacts_overview")
        from_template = self.env["boardkit.dashboard"].browse(
            self.env["boardkit.dashboard"].create_from_template(template.id)
        )
        self.assertTrue(demo.published)
        self.assertFalse(demo.menu_as_app)
        self.assertEqual(demo.menu_sequence, -1)
        self.assertEqual(demo.menu_parent_id, self.env.ref("contacts.menu_contacts"))
        self.assertTrue(demo.menu_id)
        self.assertEqual(demo.menu_id.sequence, -1)
        self.assertEqual(demo.name, from_template.name)
        self.assertEqual(len(demo.item_ids), len(from_template.item_ids))
        self.assertEqual(len(demo.filter_ids), len(from_template.filter_ids))
        self.assertEqual(
            sorted(demo.item_ids.mapped("item_type")),
            sorted(from_template.item_ids.mapped("item_type")),
        )
        # Second call is a no-op when the xmlid already exists.
        board_count = self.env["boardkit.dashboard"].search_count([])
        self.assertTrue(
            self.env["boardkit.dashboard"]._load_demo_from_template(
                {
                    "template_xmlid": "boardkit_dashboard.template_contacts_overview",
                    "demo_xmlid": "boardkit_dashboard.dashboard_demo",
                    "menu_parent_xmlid": "contacts.menu_contacts",
                }
            )
        )
        self.assertEqual(self.env["boardkit.dashboard"].search_count([]), board_count)
        self.assertEqual(self.env.ref("boardkit_dashboard.dashboard_demo"), demo)
        from_template.unlink()

    def test_load_demo_from_template_as_app(self):
        """My Day-style demos can be exposed as a top-level app."""
        xmlid = "boardkit_dashboard.dashboard_demo_as_app_test"
        existing = self.env.ref(xmlid, raise_if_not_found=False)
        if existing:
            existing.unlink()
        self.env["boardkit.dashboard"]._load_demo_from_template(
            {
                "template_xmlid": "boardkit_dashboard.template_contacts_overview",
                "demo_xmlid": xmlid,
                "menu_as_app": True,
                "menu_sequence": -1,
            }
        )
        demo = self.env.ref(xmlid)
        self.assertTrue(demo.published)
        self.assertTrue(demo.menu_as_app)
        self.assertFalse(demo.menu_parent_id)
        self.assertEqual(demo.menu_sequence, -1)
        self.assertTrue(demo.menu_id)
        self.assertFalse(demo.menu_id.parent_id)
        demo.unlink()

    def test_load_demo_from_template_rejects_invalid_config(self):
        Dashboard = self.env["boardkit.dashboard"]
        with self.assertRaises(ValidationError) as error:
            Dashboard._load_demo_from_template("not-a-dict")
        self.assertIn("dictionary", str(error.exception))

        for config in (
            {},
            {"template_xmlid": "boardkit_dashboard.template_contacts_overview"},
            {"demo_xmlid": "boardkit_dashboard.dashboard_demo"},
            {
                "template_xmlid": "boardkit_dashboard.template_contacts_overview",
                "demo_xmlid": "missing_module_prefix",
            },
        ):
            with self.assertRaises(ValidationError) as error:
                Dashboard._load_demo_from_template(config)
            self.assertIn("template_xmlid", str(error.exception))

    def test_load_demo_from_template_skips_missing_parent_menu(self):
        """Unknown parent xmlids leave the board published without a menu."""
        xmlid = "boardkit_dashboard.dashboard_demo_missing_parent_test"
        existing = self.env.ref(xmlid, raise_if_not_found=False)
        if existing:
            existing.unlink()
        self.env["boardkit.dashboard"]._load_demo_from_template(
            {
                "template_xmlid": "boardkit_dashboard.template_contacts_overview",
                "demo_xmlid": xmlid,
                "menu_parent_xmlid": "boardkit_dashboard.menu_does_not_exist",
                "menu_sequence": -1,
            }
        )
        demo = self.env.ref(xmlid)
        self.assertTrue(demo.published)
        self.assertFalse(demo.menu_parent_id)
        self.assertFalse(demo.menu_as_app)
        self.assertFalse(demo.menu_id)
        demo.unlink()

    def test_load_demo_contacts_overview_wrapper(self):
        """Legacy demo entry point still creates the Contacts Overview board."""
        demo = self.env.ref(
            "boardkit_dashboard.dashboard_demo", raise_if_not_found=False
        )
        if demo:
            demo.unlink()
        self.assertTrue(self.env["boardkit.dashboard"]._load_demo_contacts_overview())
        demo = self.env.ref("boardkit_dashboard.dashboard_demo")
        self.assertTrue(demo.published)
        self.assertEqual(demo.menu_parent_id, self.env.ref("contacts.menu_contacts"))
        self.assertEqual(demo.menu_sequence, -1)
        self.assertTrue(demo.menu_id)
        # Wrapper is idempotent through the shared loader.
        self.assertTrue(self.env["boardkit.dashboard"]._load_demo_contacts_overview())
