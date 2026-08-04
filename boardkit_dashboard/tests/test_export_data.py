# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import csv
import io
import json
from unittest.mock import patch
from urllib.parse import quote

from odoo.tests import HttpCase, tagged

from odoo.addons.boardkit_dashboard.controllers.main import BoardkitDashboardController
from odoo.addons.boardkit_dashboard.models.boardkit_dashboard_item import (
    EXPORT_MAX_ROWS,
)

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestItemExportData(BoardkitDashboardCommon):
    def test_export_tile(self):
        data = self.tile.get_export_data()
        self.assertEqual(data["name"], "Partner Count")
        self.assertEqual(len(data["rows"]), 1)
        self.assertEqual(data["rows"][0], ["Partner Count", 3, 3])

    def test_export_kpi_with_target(self):
        item = self._create_item(
            name="KPI",
            item_type="kpi",
            target_enabled=True,
            target_value=10,
        )
        data = item.get_export_data()
        self.assertEqual(data["headers"][2], "Target")
        self.assertEqual(data["rows"][0][1:], [3, 10])

    def test_export_gauge(self):
        item = self._create_item(
            name="Gauge",
            item_type="gauge",
            target_enabled=True,
            target_value=10,
            gauge_max=20,
        )
        data = item.get_export_data()
        self.assertEqual(data["rows"][0], ["Gauge", 3, 10, 20])

    def test_export_chart(self):
        item = self._create_item(
            name="By Country",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        data = item.get_export_data()
        self.assertEqual(data["headers"], ["Country", "Count"])
        by_label = {row[0]: row[1] for row in data["rows"]}
        self.assertEqual(by_label["Brazil"], 2)
        self.assertEqual(by_label["United States"], 1)

    def test_export_map(self):
        item = self._create_item(
            name="Map",
            item_type="map",
            map_mode="regions",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        data = item.get_export_data()
        self.assertEqual(data["headers"], ["Country", "Value"])
        by_label = {row[0]: row[1] for row in data["rows"]}
        self.assertEqual(by_label["Brazil"], 2)

    def test_export_map_points(self):
        item = self._create_item(
            name="Map Points",
            item_type="map",
            map_mode="points",
            latitude_field_id=self._field("res.partner", "partner_latitude").id,
            longitude_field_id=self._field("res.partner", "partner_longitude").id,
        )
        data = item.get_export_data()
        self.assertEqual(
            data["headers"], ["Label", "Latitude", "Longitude", "Records", "Value"]
        )
        self.assertEqual(len(data["rows"]), 3)
        by_label = {row[0]: row for row in data["rows"]}
        self.assertEqual(by_label["Dash Partner BR 1"][1], 10.0)
        self.assertEqual(by_label["Dash Partner BR 1"][2], -46.63)
        self.assertEqual(by_label["Dash Partner BR 1"][3], 1)

    def test_export_scatter(self):
        item = self._create_item(
            name="Scatter",
            item_type="scatter",
            group_by_field_id=self._field("res.partner", "country_id").id,
            measure_x_field_id=self._field("res.partner", "partner_latitude").id,
            measure_y_field_id=self._field("res.partner", "partner_latitude").id,
            aggregation="sum",
        )
        data = item.get_export_data()
        self.assertEqual(len(data["headers"]), 3)
        self.assertEqual(len(data["rows"]), 2)
        by_label = {row[0]: row for row in data["rows"]}
        self.assertEqual(by_label["Brazil"][1], 30.0)
        self.assertEqual(by_label["Brazil"][2], 30.0)

    def test_export_list_ignores_pagination(self):
        item = self._create_item(
            name="Partner List",
            item_type="list",
            page_size=1,
            list_column_ids=[
                (
                    0,
                    0,
                    {"sequence": 10, "field_id": self._field("res.partner", "name").id},
                )
            ],
        )
        data = item.get_export_data()
        self.assertEqual(data["headers"], ["Name"])
        self.assertEqual(len(data["rows"]), 3)

    def test_export_respects_custom_filters(self):
        params = {
            "custom_filters": [
                {
                    "model": "res.partner",
                    "field": "name",
                    "operator": "ilike",
                    "value": "BR",
                }
            ]
        }
        data = self.tile.get_export_data(params)
        self.assertEqual(data["rows"][0][1], 2)

    def test_export_list_respects_row_cap(self):
        item = self._create_item(
            name="Partner List Cap",
            item_type="list",
            list_column_ids=[
                (
                    0,
                    0,
                    {"sequence": 10, "field_id": self._field("res.partner", "name").id},
                )
            ],
        )
        with patch(
            "odoo.addons.boardkit_dashboard.models.boardkit_dashboard_item.EXPORT_MAX_ROWS",
            2,
        ):
            data = item.get_export_data()
        self.assertEqual(len(data["rows"]), 2)
        self.assertEqual(EXPORT_MAX_ROWS, 65000)

    def test_csv_neutralizes_formula_cells(self):
        for value, expected in (
            ("=CMD()", "'=CMD()"),
            ("+1", "'+1"),
            ("-2", "'-2"),
            ("@SUM(A1)", "'@SUM(A1)"),
            ("plain", "plain"),
            (3, 3),
        ):
            self.assertEqual(
                BoardkitDashboardController._neutralize_formula(value), expected
            )
        content = BoardkitDashboardController._to_csv(
            {
                "headers": ["Name", "Value"],
                "rows": [["=CMD()", "safe"]],
            }
        )
        rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
        self.assertEqual(rows[1], ["'=CMD()", "safe"])


@tagged("post_install", "-at_install")
class TestItemExportHttp(HttpCase):
    def setUp(self):
        super().setUp()
        # Export headers use _(); keep admin on en_US so assertions stay stable
        # when the database was created with another load_language (e.g. pt_BR).
        self.env["res.lang"]._activate_lang("en_US")
        self.env.ref("base.user_admin").lang = "en_US"
        dashboard = self.env["boardkit.dashboard"].create({"name": "Export Dashboard"})
        self.item = self.env["boardkit.dashboard.item"].create(
            {
                "name": "Export Tile",
                "dashboard_id": dashboard.id,
                "item_type": "tile",
                "model_id": self.env.ref("base.model_res_partner").id,
                "aggregation": "count",
            }
        )
        self.authenticate("admin", "admin")

    def _export_url(self, export_format, params=None):
        url = f"/boardkit_dashboard/item/{self.item.id}/export/{export_format}"
        if params is not None:
            url += f"?params={quote(json.dumps(params))}"
        return url

    def test_export_csv_http(self):
        response = self.url_open(self._export_url("csv"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["Content-Type"])
        self.assertIn("attachment", response.headers["Content-Disposition"])
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(rows[0], ["Name", "Value", "Records"])
        self.assertEqual(rows[1][0], "Export Tile")

    def test_export_xlsx_http(self):
        response = self.url_open(self._export_url("xlsx"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response.headers["Content-Type"])
        self.assertTrue(response.content.startswith(b"PK"))

    def test_export_with_params(self):
        params = {
            "custom_filters": [
                {
                    "model": "res.partner",
                    "field": "name",
                    "operator": "ilike",
                    "value": "zzz-no-partner-matches-this",
                }
            ]
        }
        response = self.url_open(self._export_url("csv", params))
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(rows[1][1], "0")

    def test_export_unknown_format(self):
        response = self.url_open(self._export_url("pdf"))
        self.assertEqual(response.status_code, 404)

    def test_export_unknown_item(self):
        response = self.url_open("/boardkit_dashboard/item/999999/export/csv")
        self.assertEqual(response.status_code, 404)
