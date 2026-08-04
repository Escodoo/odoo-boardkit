# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import http
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, new_test_user, tagged

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestSecurity(BoardkitDashboardCommon):
    def test_user_cannot_configure(self):
        with self.assertRaises(AccessError):
            self.env["boardkit.dashboard"].with_user(self.user).create({"name": "Nope"})
        with self.assertRaises(AccessError):
            self.tile.with_user(self.user).write({"name": "Nope"})
        with self.assertRaises(AccessError):
            self.tile.with_user(self.user).unlink()

    def test_manager_can_configure(self):
        dashboard = (
            self.env["boardkit.dashboard"]
            .with_user(self.manager)
            .create({"name": "Managed"})
        )
        self.assertTrue(dashboard.exists())

    def test_user_can_read_and_fetch_data(self):
        boards = self.env["boardkit.dashboard"].with_user(self.user).search([])
        self.assertIn(self.dashboard, boards)
        data = self.tile.with_user(self.user).get_data()
        self.assertEqual(data["value"], 3)

    def test_unpublished_only_visible_to_manager(self):
        """Unpublished boards stay limited to Dashboard Managers."""
        self.dashboard.action_unpublish()
        self.assertFalse(self.dashboard.published)
        self.assertFalse(self.dashboard.menu_id)

        boards = self.env["boardkit.dashboard"].with_user(self.user).search([])
        self.assertNotIn(self.dashboard, boards)
        self.assertFalse(
            self.env["boardkit.dashboard"]
            .with_user(self.user)
            .get_dashboard_data(self.dashboard.id)
        )
        self.assertFalse(
            self.env["boardkit.dashboard.item"]
            .with_user(self.user)
            .search([("dashboard_id", "=", self.dashboard.id)])
        )

        boards = self.env["boardkit.dashboard"].with_user(self.manager).search([])
        self.assertIn(self.dashboard, boards)
        self.assertEqual(
            self.env["boardkit.dashboard"]
            .with_user(self.manager)
            .get_dashboard_data(self.dashboard.id)["id"],
            self.dashboard.id,
        )

    def test_archived_only_visible_to_manager(self):
        """Inactive boards stay limited to Dashboard Managers."""
        self.dashboard.action_archive()
        self.assertFalse(self.dashboard.active)

        boards = (
            self.env["boardkit.dashboard"]
            .with_user(self.user)
            .with_context(active_test=False)
            .search([("id", "=", self.dashboard.id)])
        )
        self.assertFalse(boards)
        self.assertFalse(
            self.env["boardkit.dashboard"]
            .with_user(self.user)
            .with_context(active_test=False)
            .get_dashboard_data(self.dashboard.id)
        )

        boards = (
            self.env["boardkit.dashboard"]
            .with_user(self.manager)
            .with_context(active_test=False)
            .search([("id", "=", self.dashboard.id)])
        )
        self.assertTrue(boards)
        self.assertEqual(
            self.env["boardkit.dashboard"]
            .with_user(self.manager)
            .with_context(active_test=False)
            .get_dashboard_data(self.dashboard.id)["id"],
            self.dashboard.id,
        )

    def test_user_can_read_field_metadata(self):
        """Opening a dashboard must not fail on ir.model.fields ACL."""
        chart = self._create_item(
            name="By Country",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
            date_field_id=self._field("res.partner", "create_date").id,
        )
        self.env["boardkit.dashboard.item.drill"].create(
            {
                "item_id": chart.id,
                "sequence": 10,
                "group_by_field_id": self._field("res.partner", "is_company").id,
                "chart_type": "pie",
            }
        )
        payload = (
            self.env["boardkit.dashboard"]
            .with_user(self.user)
            .get_dashboard_data(self.dashboard.id)
        )
        self.assertEqual(payload["id"], self.dashboard.id)
        item_config = next(item for item in payload["items"] if item["id"] == chart.id)
        self.assertEqual(len(item_config["drill_levels"]), 1)
        self.assertTrue(item_config["drill_levels"][0]["label"])

        data = chart.with_user(self.user).get_data()
        self.assertNotIn("error", data)
        self.assertIn("labels", data)

    def test_group_access_restriction(self):
        manager_group = self.env.ref("boardkit_dashboard.group_dashboard_manager")
        self.dashboard.group_ids = [(6, 0, manager_group.ids)]
        dash_filter = self.env["boardkit.dashboard.filter"].create(
            {
                "name": "Companies",
                "dashboard_id": self.dashboard.id,
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain": "[('is_company', '=', True)]",
            }
        )
        chart = self._create_item(
            name="By Country",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        drill = self.env["boardkit.dashboard.item.drill"].create(
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
                (0, 0, {"field_id": self._field("res.partner", "name").id}),
            ],
        )
        column = list_item.list_column_ids[:1]

        boards = self.env["boardkit.dashboard"].with_user(self.user).search([])
        self.assertNotIn(self.dashboard, boards)
        # Soft-fail: landing pages get False instead of AccessError.
        self.assertFalse(
            self.env["boardkit.dashboard"]
            .with_user(self.user)
            .get_dashboard_data(self.dashboard.id)
        )
        # Child models must follow the same group restriction.
        items = (
            self.env["boardkit.dashboard.item"]
            .with_user(self.user)
            .search([("dashboard_id", "=", self.dashboard.id)])
        )
        self.assertFalse(items)
        self.assertFalse(
            self.env["boardkit.dashboard.filter"]
            .with_user(self.user)
            .search([("id", "=", dash_filter.id)])
        )
        self.assertFalse(
            self.env["boardkit.dashboard.item.drill"]
            .with_user(self.user)
            .search([("id", "=", drill.id)])
        )
        self.assertFalse(
            self.env["boardkit.dashboard.item.column"]
            .with_user(self.user)
            .search([("id", "=", column.id)])
        )
        with self.assertRaises(AccessError):
            self.tile.with_user(self.user).get_data()
        with self.assertRaises(AccessError):
            self.env["boardkit.dashboard.item"].with_user(self.user).get_items_data(
                [self.tile.id]
            )
        with self.assertRaises(AccessError):
            self.tile.with_user(self.user).get_export_data()
        # Managers still see it.
        boards = self.env["boardkit.dashboard"].with_user(self.manager).search([])
        self.assertIn(self.dashboard, boards)
        self.assertEqual(self.tile.with_user(self.manager).get_data()["value"], 3)
        self.assertIn(
            dash_filter,
            self.env["boardkit.dashboard.filter"].with_user(self.manager).search([]),
        )

    def test_source_model_record_rules_apply(self):
        """Record rules of the source model restrict the computed values."""
        # The manager implies the user group, so restrict a dedicated group
        # to check that source model rules apply per user.
        restricted_group = self.env["res.groups"].create(
            {"name": "Dashboard Restricted Partners"}
        )
        self.user.groups_id = [(4, restricted_group.id)]
        self.env["ir.rule"].create(
            {
                "name": "Hide partners from restricted users",
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain_force": "[('id', '=', 0)]",
                "groups": [(4, restricted_group.id)],
            }
        )
        self.assertEqual(self.tile.with_user(self.user).get_data()["value"], 0)
        # The manager is not in the restricted group, so it sees everything.
        self.assertEqual(self.tile.with_user(self.manager).get_data()["value"], 3)

    def test_source_model_acl_error_is_isolated(self):
        """Items on models the user cannot read return an error payload."""
        item = self._create_item(
            name="Config Parameters",
            model_id=self.env["ir.model"]._get("ir.config_parameter").id,
            domain="[]",
        )
        data = item.with_user(self.user).get_data()
        self.assertIn("error", data)

    def test_personal_layout_isolation(self):
        layout_model = self.env["boardkit.dashboard.layout"]
        layout_user = layout_model.with_user(self.user).create(
            {"dashboard_id": self.dashboard.id, "layout_json": "{}"}
        )
        self.assertEqual(layout_user.user_id, self.user)
        # The other user does not see it.
        other_layouts = layout_model.with_user(self.manager).search(
            [("dashboard_id", "=", self.dashboard.id)]
        )
        self.assertNotIn(layout_user, other_layouts)

    def test_multi_company_rule(self):
        company_2 = self.env["res.company"].create({"name": "Second Company"})
        # Drop the menu first: company-bound dashboards cannot keep a menu.
        self.dashboard.menu_parent_id = False
        self.dashboard.company_id = company_2
        boards = self.env["boardkit.dashboard"].with_user(self.user).search([])
        self.assertNotIn(self.dashboard, boards)
        items = (
            self.env["boardkit.dashboard.item"]
            .with_user(self.user)
            .search([("dashboard_id", "=", self.dashboard.id)])
        )
        self.assertFalse(items)
        self.assertFalse(
            self.env["boardkit.dashboard"]
            .with_user(self.user)
            .get_dashboard_data(self.dashboard.id)
        )

    def test_audience_group_access_without_dashboard_user(self):
        """Users in Allowed Groups can open that board without Dashboard User."""
        audience_group = self.env["res.groups"].create({"name": "Dashboard Audience"})
        other_group = self.env["res.groups"].create({"name": "Other Audience"})
        audience = new_test_user(
            self.env,
            login="dash_audience",
            groups="base.group_user",
        )
        audience.groups_id = [(4, audience_group.id)]

        # Boards without Allowed Groups stay invisible to audience-only users.
        boards = self.env["boardkit.dashboard"].with_user(audience).search([])
        self.assertNotIn(self.dashboard, boards)
        self.assertFalse(
            self.env["boardkit.dashboard"]
            .with_user(audience)
            .get_dashboard_data(self.dashboard.id)
        )

        self.dashboard.group_ids = [(6, 0, audience_group.ids)]
        boards = self.env["boardkit.dashboard"].with_user(audience).search([])
        self.assertIn(self.dashboard, boards)
        payload = (
            self.env["boardkit.dashboard"]
            .with_user(audience)
            .get_dashboard_data(self.dashboard.id)
        )
        self.assertEqual(payload["id"], self.dashboard.id)
        self.assertFalse(payload["is_manager"])
        self.assertEqual(self.tile.with_user(audience).get_data()["value"], 3)

        # A board restricted to another group remains denied.
        other_board = self.env["boardkit.dashboard"].create(
            {
                "name": "Other Audience Board",
                "published": True,
                "group_ids": [(6, 0, other_group.ids)],
            }
        )
        self.assertNotIn(
            other_board,
            self.env["boardkit.dashboard"].with_user(audience).search([]),
        )
        self.assertFalse(
            self.env["boardkit.dashboard"]
            .with_user(audience)
            .get_dashboard_data(other_board.id)
        )

        with self.assertRaises(AccessError):
            self.env["boardkit.dashboard"].with_user(audience).create(
                {"name": "Audience Create"}
            )
        with self.assertRaises(AccessError):
            self.tile.with_user(audience).write({"name": "Nope"})


@tagged("post_install", "-at_install")
class TestSecurityHttp(HttpCase):
    def setUp(self):
        super().setUp()
        self.manager = new_test_user(
            self.env,
            login="dash_sec_manager",
            groups="base.group_user,boardkit_dashboard.group_dashboard_manager",
        )
        self.user = new_test_user(
            self.env,
            login="dash_sec_user",
            groups="base.group_user,boardkit_dashboard.group_dashboard_user",
        )
        self.dashboard = self.env["boardkit.dashboard"].create(
            {"name": "Restricted Export Dashboard"}
        )
        self.item = self.env["boardkit.dashboard.item"].create(
            {
                "name": "Restricted Tile",
                "dashboard_id": self.dashboard.id,
                "item_type": "tile",
                "model_id": self.env.ref("base.model_res_partner").id,
                "aggregation": "count",
            }
        )

    def test_item_export_http_denied_for_restricted_user(self):
        manager_group = self.env.ref("boardkit_dashboard.group_dashboard_manager")
        self.dashboard.group_ids = [(6, 0, manager_group.ids)]
        self.authenticate("dash_sec_user", "dash_sec_user")
        response = self.url_open(
            f"/boardkit_dashboard/item/{self.item.id}/export/csv",
            allow_redirects=False,
        )
        self.assertIn(response.status_code, (403, 404))

    def test_dashboard_export_http_manager_only(self):
        self.authenticate("dash_sec_manager", "dash_sec_manager")
        response = self.url_open(
            f"/boardkit_dashboard/export/{self.dashboard.id}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.authenticate("dash_sec_user", "dash_sec_user")
        response = self.url_open(
            f"/boardkit_dashboard/export/{self.dashboard.id}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 403)

    def test_dashboard_import_http_manager_only(self):
        payload = json.dumps(self.dashboard.export_config()).encode()
        self.authenticate("dash_sec_user", "dash_sec_user")
        response = self.url_open(
            "/boardkit_dashboard/import",
            data={"csrf_token": http.Request.csrf_token(self)},
            files={"ufile": ("dashboards.json", payload, "application/json")},
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 403)
