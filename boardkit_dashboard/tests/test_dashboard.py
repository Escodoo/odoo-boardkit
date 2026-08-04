# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestDashboard(BoardkitDashboardCommon):
    def test_menu_lifecycle(self):
        """A menu and a client action are created, kept in sync and removed."""
        dashboard = self.dashboard
        self.assertTrue(dashboard.menu_id)
        self.assertTrue(dashboard.client_action_id)
        self.assertEqual(dashboard.menu_id.name, "Test Dashboard")
        self.assertEqual(dashboard.client_action_id.tag, "boardkit_dashboard")
        # Without explicit groups the menu must stay restricted to dashboard
        # users instead of being visible to every internal user.
        user_group = self.env.ref("boardkit_dashboard.group_dashboard_user")
        self.assertEqual(dashboard.menu_id.groups_id, user_group)

        dashboard.write({"menu_name": "Renamed Menu", "menu_sequence": 5})
        self.assertEqual(dashboard.menu_id.name, "Renamed Menu")
        self.assertEqual(dashboard.menu_id.sequence, 5)

        group = self.env.ref("boardkit_dashboard.group_dashboard_manager")
        dashboard.write({"group_ids": [(6, 0, group.ids)]})
        self.assertEqual(dashboard.menu_id.groups_id, group)

        dashboard.write({"group_ids": [(5, 0, 0)]})
        self.assertEqual(dashboard.menu_id.groups_id, user_group)

        dashboard.action_archive()
        self.assertFalse(dashboard.menu_id.active)
        dashboard.action_unarchive()
        self.assertTrue(dashboard.menu_id.active)

        menu = dashboard.menu_id
        action = dashboard.client_action_id
        dashboard.unlink()
        self.assertFalse(menu.exists())
        self.assertFalse(action.exists())

    def test_menu_removed_when_parent_cleared(self):
        self.dashboard.menu_parent_id = False
        self.assertFalse(self.dashboard.menu_id)
        self.assertFalse(self.dashboard.client_action_id)

    def test_menu_as_app_lifecycle(self):
        """Show as App creates a root menu with the module icon and follows publish."""
        module_icon = "boardkit_dashboard,static/description/icon.png"
        dashboard = self.dashboard
        dashboard.write({"menu_parent_id": False, "menu_as_app": True})
        menu = dashboard.menu_id
        self.assertTrue(menu)
        self.assertFalse(menu.parent_id)
        self.assertEqual(menu.web_icon, module_icon)
        self.assertTrue(menu.web_icon_data)

        # The app follows the published flag like any menu entry.
        dashboard.action_unpublish()
        self.assertFalse(dashboard.menu_id)
        dashboard.action_publish()
        self.assertTrue(dashboard.menu_id)
        self.assertFalse(dashboard.menu_id.parent_id)
        self.assertEqual(dashboard.menu_id.web_icon, module_icon)

        # Moving back under a parent menu drops the icon.
        parent = self.env.ref("boardkit_dashboard.menu_dashboard_root")
        dashboard.write({"menu_as_app": False, "menu_parent_id": parent.id})
        self.assertEqual(dashboard.menu_id.parent_id, parent)
        self.assertFalse(dashboard.menu_id.web_icon_data)

    def test_company_bound_dashboard_cannot_be_app(self):
        company_2 = self.env["res.company"].create({"name": "App Company"})
        self.dashboard.write({"menu_parent_id": False, "menu_as_app": True})
        # Setting a company clears the app flag and removes the entry.
        self.dashboard.company_id = company_2
        self.assertFalse(self.dashboard.menu_as_app)
        self.assertFalse(self.dashboard.menu_id)
        with self.assertRaises(ValidationError):
            self.dashboard.menu_as_app = True
        # Create path also refuses the app flag when a company is set.
        dashboard = self.env["boardkit.dashboard"].create(
            {
                "name": "Company Bound App",
                "company_id": company_2.id,
                "menu_as_app": True,
                "published": True,
            }
        )
        self.assertFalse(dashboard.menu_as_app)
        self.assertFalse(dashboard.menu_id)

    def test_company_bound_dashboard_cannot_have_menu(self):
        company_2 = self.env["res.company"].create({"name": "Menu Company"})
        parent = self.env.ref("boardkit_dashboard.menu_dashboard_root")
        # Setting a company clears the parent menu and removes the entry.
        self.dashboard.company_id = company_2
        self.assertFalse(self.dashboard.menu_parent_id)
        self.assertFalse(self.dashboard.menu_id)
        with self.assertRaises(ValidationError):
            self.dashboard.menu_parent_id = parent
        # Create path also refuses a menu when a company is set.
        dashboard = self.env["boardkit.dashboard"].create(
            {
                "name": "Company Bound",
                "company_id": company_2.id,
                "menu_parent_id": parent.id,
            }
        )
        self.assertFalse(dashboard.menu_parent_id)
        self.assertFalse(dashboard.menu_id)

    def test_custom_date_validation(self):
        with self.assertRaises(ValidationError):
            self.dashboard.write(
                {
                    "date_filter": "custom",
                    "date_from": "2026-02-01 00:00:00",
                    "date_to": "2026-01-01 00:00:00",
                }
            )

    def test_favorite_dashboard(self):
        """Read-only users can toggle favorites; favorites stay per-user."""
        Dashboard = self.env["boardkit.dashboard"]
        other = Dashboard.create({"name": "Other Dashboard", "published": True})
        dashboard = self.dashboard

        # A dashboard user (no write ACL) can favorite without AccessError.
        dashboard.with_user(self.user).write({"is_favorite": True})
        self.assertIn(self.user, dashboard.favorite_user_ids)
        # compute_sudo shares the transaction cache; invalidate like project does.
        dashboard.invalidate_recordset(["is_favorite"])
        self.assertTrue(dashboard.with_user(self.user).is_favorite)

        # Favorites are per user: another user does not see it as favorited.
        dashboard.invalidate_recordset(["is_favorite"])
        self.assertFalse(dashboard.with_user(self.manager).is_favorite)
        favorites = Dashboard.with_user(self.user).search([("is_favorite", "=", True)])
        self.assertEqual(favorites, dashboard)
        self.assertFalse(
            Dashboard.with_user(self.manager).search([("is_favorite", "=", True)])
        )

        # Toggle off removes the relation.
        dashboard.with_user(self.user).write({"is_favorite": False})
        self.assertNotIn(self.user, dashboard.favorite_user_ids)
        dashboard.invalidate_recordset(["is_favorite"])
        self.assertFalse(dashboard.with_user(self.user).is_favorite)

        # Favorites are not copied.
        dashboard.with_user(self.user).write({"is_favorite": True})
        copy = dashboard.copy()
        self.assertFalse(copy.favorite_user_ids)

        # Ordering by is_favorite puts favorited dashboards first.
        other.with_user(self.user).write({"is_favorite": False})
        ordered = Dashboard.with_user(self.user).search(
            [("id", "in", (dashboard.id, other.id))],
            order="is_favorite desc, name",
        )
        self.assertEqual(ordered[0], dashboard)

    def test_copy_remaps_layout(self):
        self.dashboard.layout_json = json.dumps(
            {str(self.tile.id): {"x": 3, "y": 1, "w": 4, "h": 2}}
        )
        copy = self.dashboard.copy()
        self.assertEqual(len(copy.item_ids), 1)
        self.assertNotEqual(copy.item_ids.id, self.tile.id)
        layout = json.loads(copy.layout_json)
        self.assertEqual(
            layout[str(copy.item_ids.id)], {"x": 3, "y": 1, "w": 4, "h": 2}
        )

    def test_copy_preserves_columns_and_drill_levels(self):
        chart = self._create_item(
            name="By Country",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        self.env["boardkit.dashboard.item.drill"].create(
            {
                "item_id": chart.id,
                "sequence": 10,
                "group_by_field_id": self._field("res.partner", "is_company").id,
                "chart_type": "pie",
            }
        )
        list_item = self._create_item(
            name="Partner List",
            item_type="list",
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
                        "field_id": self._field("res.partner", "email").id,
                    },
                ),
            ],
        )
        copy = self.dashboard.copy()
        # Item.copy() suffixes names with " (copy)".
        copied_chart = copy.item_ids.filtered(lambda item: item.item_type == "bar")
        copied_list = copy.item_ids.filtered(lambda item: item.item_type == "list")
        self.assertEqual(len(copied_chart), 1)
        self.assertEqual(len(copied_list), 1)
        self.assertEqual(len(copied_chart.drill_level_ids), 1)
        self.assertEqual(
            copied_chart.drill_level_ids.group_by_field_id.name, "is_company"
        )
        self.assertNotEqual(copied_chart.drill_level_ids.id, chart.drill_level_ids.id)
        self.assertEqual(
            copied_list.list_column_ids.mapped("field_id.name"),
            ["name", "email"],
        )
        self.assertNotEqual(
            copied_list.list_column_ids.ids, list_item.list_column_ids.ids
        )

    def test_get_dashboard_data(self):
        data = (
            self.env["boardkit.dashboard"]
            .with_user(self.user)
            .get_dashboard_data(self.dashboard.id)
        )
        self.assertEqual(data["name"], "Test Dashboard")
        self.assertFalse(data["is_manager"])
        self.assertFalse(data["is_favorite"])
        self.assertEqual([item["id"] for item in data["items"]], [self.tile.id])
        self.assertIn(
            ["today", "Today"], [list(preset) for preset in data["date_presets"]]
        )
        manager_data = (
            self.env["boardkit.dashboard"]
            .with_user(self.manager)
            .get_dashboard_data(self.dashboard.id)
        )
        self.assertTrue(manager_data["is_manager"])

    def test_toggle_favorite_from_client_action(self):
        """Client action can toggle favorites for read-only dashboard users."""
        dashboard = self.dashboard.with_user(self.user)
        self.assertTrue(dashboard.toggle_favorite())
        self.assertIn(self.user, self.dashboard.favorite_user_ids)
        data = (
            self.env["boardkit.dashboard"]
            .with_user(self.user)
            .get_dashboard_data(self.dashboard.id)
        )
        self.assertTrue(data["is_favorite"])
        self.assertFalse(dashboard.toggle_favorite())
        self.assertNotIn(self.user, self.dashboard.favorite_user_ids)

    def test_save_layout_personal_and_default(self):
        layout = {str(self.tile.id): {"x": 0, "y": 0, "w": 6, "h": 3}}
        board_model_user = self.env["boardkit.dashboard"].with_user(self.user)
        board_model_user.save_layout(self.dashboard.id, layout, True)
        data = board_model_user.get_dashboard_data(self.dashboard.id)
        self.assertTrue(data["has_personal_layout"])
        self.assertEqual(data["layout"], layout)
        # The default layout is untouched.
        self.assertEqual(self.dashboard.layout_json, "{}")

        # Regular users cannot save the default layout.
        with self.assertRaises(AccessError):
            board_model_user.save_layout(self.dashboard.id, layout, False)

        # Managers can.
        self.env["boardkit.dashboard"].with_user(self.manager).save_layout(
            self.dashboard.id, layout, False
        )
        self.assertEqual(json.loads(self.dashboard.layout_json), layout)

        # Reset removes the personal layout.
        board_model_user.reset_personal_layout(self.dashboard.id)
        data = board_model_user.get_dashboard_data(self.dashboard.id)
        self.assertFalse(data["has_personal_layout"])

    def test_save_and_reset_personal_filters(self):
        board = self.env["boardkit.dashboard"].with_user(self.user)
        board_filter = self.env["boardkit.dashboard.filter"].create(
            {
                "name": "Companies",
                "dashboard_id": self.dashboard.id,
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain": "[('is_company', '=', True)]",
                "default_enabled": False,
            }
        )
        filters = {
            "date_preset": "last_30_days",
            "filter_ids": [board_filter.id],
            "custom_filters": [
                {
                    "model": "res.partner",
                    "field": "name",
                    "operator": "ilike",
                    "value": "Dash",
                    "label": "Name contains Dash",
                    "modelLabel": "Contact",
                }
            ],
        }
        board.save_filters(self.dashboard.id, filters)
        data = board.get_dashboard_data(self.dashboard.id)
        self.assertTrue(data["has_saved_filters"])
        self.assertEqual(data["saved_filters"]["date_preset"], "last_30_days")
        self.assertEqual(data["saved_filters"]["filter_ids"], [board_filter.id])
        self.assertEqual(
            data["saved_filters"]["custom_filters"][0]["field"],
            "name",
        )
        # Saving filters alone must not look like a personal layout.
        self.assertFalse(data["has_personal_layout"])

        board.reset_personal_filters(self.dashboard.id)
        data = board.get_dashboard_data(self.dashboard.id)
        self.assertFalse(data["has_saved_filters"])
        self.assertEqual(data["saved_filters"], {})

    def test_normalize_saved_filters_rejects_noise(self):
        Board = self.env["boardkit.dashboard"]
        state = Board._normalize_saved_filters(
            {
                "date_preset": "not-a-preset",
                "filter_ids": [1, "x", True, 2],
                "custom_filters": [
                    {"model": "res.partner", "field": "name", "operator": "ilike"},
                    {"model": "", "field": "name", "operator": "="},
                    "skip-me",
                ],
                "injected": {"sudo": True},
            }
        )
        self.assertEqual(state["date_preset"], "none")
        self.assertEqual(state["filter_ids"], [1, 2])
        self.assertEqual(len(state["custom_filters"]), 1)
        self.assertNotIn("injected", state)

    def test_personal_layout_and_filters_independent_reset(self):
        layout = {str(self.tile.id): {"x": 0, "y": 0, "w": 4, "h": 3}}
        board = self.env["boardkit.dashboard"].with_user(self.user)
        board.save_layout(self.dashboard.id, layout, True)
        board.save_filters(self.dashboard.id, {"date_preset": "today"})
        board.reset_personal_layout(self.dashboard.id)
        data = board.get_dashboard_data(self.dashboard.id)
        self.assertFalse(data["has_personal_layout"])
        self.assertTrue(data["has_saved_filters"])
        self.assertEqual(data["saved_filters"]["date_preset"], "today")
        board.reset_personal_filters(self.dashboard.id)
        data = board.get_dashboard_data(self.dashboard.id)
        self.assertFalse(data["has_saved_filters"])
        # Both preferences cleared: the personal row is gone.
        self.assertFalse(
            self.env["boardkit.dashboard.layout"]
            .sudo()
            .search(
                [
                    ("dashboard_id", "=", self.dashboard.id),
                    ("user_id", "=", self.user.id),
                ]
            )
        )

    def test_open_dashboard_action(self):
        action = self.dashboard.action_open_dashboard()
        self.assertEqual(action["tag"], "boardkit_dashboard")
        self.assertEqual(action["params"]["dashboard_id"], self.dashboard.id)

    def test_open_settings_action(self):
        action = self.dashboard.action_open_settings()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "boardkit.dashboard")
        self.assertEqual(action["res_id"], self.dashboard.id)

    def test_description_and_tags(self):
        sales = self.env["boardkit.dashboard.tag"].create({"name": "Sales", "color": 1})
        hr = self.env["boardkit.dashboard.tag"].create({"name": "HR", "color": 2})
        self.dashboard.write(
            {
                "description": "Overview of sales KPIs",
                "tag_ids": [(6, 0, (sales | hr).ids)],
            }
        )
        self.assertEqual(self.dashboard.description, "Overview of sales KPIs")
        self.assertEqual(self.dashboard.tag_ids, sales | hr)

    def test_tag_default_color_visible_in_kanban(self):
        # Color 0 is filtered out by kanban.many2many_tags ("Hide in kanban").
        tag = self.env["boardkit.dashboard.tag"].create({"name": "Visible"})
        self.assertTrue(tag.color)
        self.assertNotEqual(tag.color, 0)

    def test_kanban_summary_fields(self):
        self.dashboard.default_color_palette = "pastel"
        self._create_item(
            name="By Country",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        self.dashboard.invalidate_recordset()
        self.assertEqual(self.dashboard.item_count, 2)
        self.assertTrue(self.dashboard.published)
        self.assertIn("Tile", self.dashboard.item_type_summary)
        self.assertIn("Bar Chart", self.dashboard.item_type_summary)
        self.assertEqual(self.dashboard.model_summary, "res.partner")
        self.assertIn(
            "o_boardkit_dashboard_kanban_type",
            self.dashboard.item_type_badge_html,
        )
        self.assertIn(
            "o_boardkit_dashboard_kanban_strip",
            self.dashboard.palette_strip_html,
        )
        self.assertIn("#7EB5E8", self.dashboard.palette_strip_html)

    def test_publish_without_menu_visible_to_user(self):
        """Published boards are available in the catalogue even without a menu."""
        self.dashboard.menu_parent_id = False
        self.assertTrue(self.dashboard.published)
        self.assertFalse(self.dashboard.menu_id)
        boards = self.env["boardkit.dashboard"].with_user(self.user).search([])
        self.assertIn(self.dashboard, boards)

    def test_unpublish_removes_menu_and_republish_restores_it(self):
        parent = self.env.ref("boardkit_dashboard.menu_dashboard_root")
        self.assertTrue(self.dashboard.menu_id)
        self.dashboard.action_unpublish()
        self.assertFalse(self.dashboard.published)
        self.assertFalse(self.dashboard.menu_id)
        self.assertFalse(self.dashboard.client_action_id)

        self.dashboard.write({"menu_parent_id": parent.id})
        self.dashboard.action_publish()
        self.assertTrue(self.dashboard.published)
        self.assertTrue(self.dashboard.menu_id)
        self.assertTrue(self.dashboard.client_action_id)
        self.assertEqual(self.dashboard.menu_id.parent_id, parent)

    def test_copy_starts_unpublished(self):
        copy = self.dashboard.copy()
        self.assertFalse(copy.published)
        self.assertFalse(copy.menu_parent_id)
        self.assertFalse(copy.menu_id)

    def test_kanban_custom_palette_strip(self):
        palette = self.env["boardkit.dashboard.palette"].create(
            {
                "name": "Kanban Palette",
                "color_ids": [
                    (0, 0, {"sequence": 10, "color": "#112233"}),
                    (0, 0, {"sequence": 20, "color": "#445566"}),
                ],
            }
        )
        self.dashboard.write(
            {
                "default_color_palette": "custom",
                "default_palette_id": palette.id,
            }
        )
        self.assertIn("#112233", self.dashboard.palette_strip_html)
        self.assertIn("#445566", self.dashboard.palette_strip_html)

    def test_filter_domain_validation(self):
        with self.assertRaises(ValidationError):
            self.env["boardkit.dashboard.filter"].create(
                {
                    "name": "Broken",
                    "dashboard_id": self.dashboard.id,
                    "model_id": self.env.ref("base.model_res_partner").id,
                    "domain": "[('not_a_field', '=', 1)]",
                }
            )

    def test_item_domain_validation(self):
        with self.assertRaises(ValidationError):
            self._create_item(name="Broken", domain="[('nope', '=', 1)]")
