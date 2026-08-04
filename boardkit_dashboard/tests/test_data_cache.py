# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.boardkit_dashboard.tools import data_cache

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestDashboardDataCache(BoardkitDashboardCommon):
    def setUp(self):
        super().setUp()
        data_cache.cache_clear()

    def tearDown(self):
        data_cache.cache_clear()
        super().tearDown()

    def test_no_cache_when_refresh_disabled(self):
        self.dashboard.refresh_interval = "0"
        calls = {"n": 0}
        original = type(self.tile)._get_data

        def counting_get_data(item, params):
            calls["n"] += 1
            return original(item, params)

        with patch.object(
            type(self.tile), "_get_data", autospec=True, side_effect=counting_get_data
        ):
            self.assertEqual(self.tile.get_data()["value"], 3)
            self.assertEqual(self.tile.get_data()["value"], 3)
        self.assertEqual(calls["n"], 2)

    def test_cache_hit_when_refresh_enabled(self):
        self.dashboard.refresh_interval = "60"
        calls = {"n": 0}
        original = type(self.tile)._get_data

        def counting_get_data(item, params):
            calls["n"] += 1
            return original(item, params)

        with patch.object(
            type(self.tile), "_get_data", autospec=True, side_effect=counting_get_data
        ):
            first = self.tile.get_data({"date_preset": "none"})
            second = self.tile.get_data({"date_preset": "none"})
        self.assertEqual(first["value"], 3)
        self.assertEqual(second["value"], 3)
        self.assertEqual(calls["n"], 1)

    def test_cache_miss_on_different_params(self):
        self.dashboard.refresh_interval = "60"
        calls = {"n": 0}
        original = type(self.tile)._get_data

        def counting_get_data(item, params):
            calls["n"] += 1
            return original(item, params)

        with patch.object(
            type(self.tile), "_get_data", autospec=True, side_effect=counting_get_data
        ):
            self.tile.get_data({"date_preset": "none"})
            self.tile.get_data({"date_preset": "today"})
        self.assertEqual(calls["n"], 2)

    def test_cache_is_scoped_per_user(self):
        self.dashboard.refresh_interval = "60"
        calls = {"n": 0}
        original = type(self.tile)._get_data

        def counting_get_data(item, params):
            calls["n"] += 1
            return original(item, params)

        with patch.object(
            type(self.tile), "_get_data", autospec=True, side_effect=counting_get_data
        ):
            self.tile.with_user(self.user).get_data()
            self.tile.with_user(self.manager).get_data()
            self.tile.with_user(self.user).get_data()
        # user + manager compute once each; second user call hits cache
        self.assertEqual(calls["n"], 2)

    def test_max_ttl_zero_disables_cache(self):
        self.dashboard.refresh_interval = "60"
        self.env["ir.config_parameter"].sudo().set_param(
            "boardkit_dashboard.data_cache_max_ttl", "0"
        )
        calls = {"n": 0}
        original = type(self.tile)._get_data

        def counting_get_data(item, params):
            calls["n"] += 1
            return original(item, params)

        with patch.object(
            type(self.tile), "_get_data", autospec=True, side_effect=counting_get_data
        ):
            self.tile.get_data()
            self.tile.get_data()
        self.assertEqual(calls["n"], 2)
