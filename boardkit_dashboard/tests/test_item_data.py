# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestItemData(BoardkitDashboardCommon):
    def test_tile_count_sum_avg(self):
        data = self.tile.get_data()
        self.assertEqual(data["type"], "tile")
        self.assertEqual(data["value"], 3)
        self.assertEqual(data["count"], 3)

        self.tile.write(
            {
                "aggregation": "sum",
                "measure_field_id": self._field("res.partner", "partner_latitude").id,
            }
        )
        self.assertEqual(self.tile.get_data()["value"], 60.0)

        self.tile.aggregation = "avg"
        self.assertEqual(self.tile.get_data()["value"], 20.0)

    def test_chart_group_by_many2one(self):
        item = self._create_item(
            name="By Country",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        data = item.get_data()
        self.assertEqual(data["type"], "chart")
        self.assertEqual(set(data["labels"]), {"Brazil", "United States"})
        dataset = data["datasets"][0]
        by_label = dict(zip(data["labels"], dataset["data"], strict=True))
        self.assertEqual(by_label["Brazil"], 2)
        self.assertEqual(by_label["United States"], 1)
        # Drilldown domain of the Brazil group targets the Brazil records.
        drilldown = dataset["drilldowns"][data["labels"].index("Brazil")]
        self.assertIn(["country_id", "=", self.country_br.id], drilldown)

    def test_chart_overlay_flags_in_config(self):
        item = self._create_item(
            name="Overlays Config",
            item_type="line",
            group_by_field_id=self._field("res.partner", "country_id").id,
            show_average_line=True,
            show_trend_line=True,
        )
        config = item._get_config()
        self.assertTrue(config["show_average_line"])
        self.assertTrue(config["show_trend_line"])
        item.write({"show_average_line": False, "show_trend_line": False})
        config = item._get_config()
        self.assertFalse(config["show_average_line"])
        self.assertFalse(config["show_trend_line"])

    def test_chart_measures_and_sum(self):
        item = self._create_item(
            name="Latitude by Country",
            item_type="bar",
            aggregation="sum",
            group_by_field_id=self._field("res.partner", "country_id").id,
            measure_ids=[
                (0, 0, {"field_id": self._field("res.partner", "partner_latitude").id})
            ],
        )
        data = item.get_data()
        by_label = dict(zip(data["labels"], data["datasets"][0]["data"], strict=True))
        self.assertEqual(by_label["Brazil"], 30.0)
        self.assertEqual(by_label["United States"], 30.0)

    def test_chart_measure_order_respects_sequence(self):
        # Sequences reverse alphabetical order (longitude before latitude).
        item = self._create_item(
            name="Coordinates by Country",
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
        data = item.get_data()
        self.assertEqual(
            [dataset["label"] for dataset in data["datasets"]],
            ["Geo Longitude", "Geo Latitude"],
        )
        item.measure_ids[0].sequence = 30
        data = item.get_data()
        self.assertEqual(
            [dataset["label"] for dataset in data["datasets"]],
            ["Geo Latitude", "Geo Longitude"],
        )

    def test_chart_subgroup(self):
        item = self._create_item(
            name="Country by Type",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
            subgroup_by_field_id=self._field("res.partner", "is_company").id,
        )
        data = item.get_data()
        self.assertEqual(set(data["labels"]), {"Brazil", "United States"})
        self.assertEqual(
            {dataset["label"] for dataset in data["datasets"]}, {"Yes", "No"}
        )
        yes_dataset = next(d for d in data["datasets"] if d["label"] == "Yes")
        by_label = dict(zip(data["labels"], yes_dataset["data"], strict=True))
        self.assertEqual(by_label["Brazil"], 1)
        self.assertEqual(by_label["United States"], 1)

    def test_chart_boolean_custom_labels(self):
        item = self._create_item(
            name="Companies vs Individuals",
            item_type="pie",
            group_by_field_id=self._field("res.partner", "is_company").id,
            boolean_true_label="Company",
            boolean_false_label="Individual",
        )
        data = item.get_data()
        self.assertEqual(set(data["labels"]), {"Company", "Individual"})
        by_label = dict(zip(data["labels"], data["datasets"][0]["data"], strict=True))
        self.assertEqual(by_label["Company"], 2)
        self.assertEqual(by_label["Individual"], 1)
        company_idx = data["labels"].index("Company")
        self.assertIn(
            ["is_company", "=", True], data["datasets"][0]["drilldowns"][company_idx]
        )

    def test_chart_date_granularity(self):
        item = self._create_item(
            name="By Month",
            item_type="line",
            group_by_field_id=self._field("res.partner", "create_date").id,
            group_by_granularity="month",
        )
        data = item.get_data()
        self.assertEqual(len(data["labels"]), 1)
        month_label = fields.Datetime.now().strftime("%b %Y")
        self.assertEqual(data["labels"][0], month_label)
        self.assertEqual(data["datasets"][0]["data"], [3])
        drilldown = data["datasets"][0]["drilldowns"][0]
        operators = [leaf[1] for leaf in drilldown if leaf[0] == "create_date"]
        self.assertEqual(sorted(operators), ["<", ">="])

    def test_chart_sort_and_limit(self):
        item = self._create_item(
            name="Top Country",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
            chart_sort="value_desc",
            record_limit=1,
        )
        data = item.get_data()
        self.assertEqual(data["labels"], ["Brazil"])
        self.assertEqual(data["datasets"][0]["data"], [2])

    def test_chart_missing_group_by_returns_error(self):
        item = self._create_item(name="Broken Chart", item_type="bar")
        data = item.get_data()
        self.assertIn("error", data)

    def test_scatter(self):
        item = self._create_item(
            name="Scatter",
            item_type="scatter",
            group_by_field_id=self._field("res.partner", "country_id").id,
            measure_x_field_id=self._field("res.partner", "partner_latitude").id,
            measure_y_field_id=self._field("res.partner", "partner_latitude").id,
        )
        data = item.get_data()
        self.assertEqual(data["type"], "scatter")
        points = data["datasets"][0]["data"]
        self.assertEqual(len(points), 2)
        self.assertEqual({point["x"] for point in points}, {30.0})

    def test_kpi_target_and_previous_period(self):
        item = self._create_item(
            name="KPI",
            item_type="kpi",
            kpi_mode="target",
            target_enabled=True,
            target_value=5.0,
            date_field_id=self._field("res.partner", "create_date").id,
        )
        data = item.get_data({"date_preset": "today"})
        self.assertEqual(data["value"], 3)
        self.assertEqual(data["target"], 5.0)

        item.compare_previous_period = True
        data = item.get_data({"date_preset": "today"})
        self.assertEqual(data["previous_value"], 0)

    def test_tile_previous_period(self):
        item = self._create_item(
            name="Tile Previous",
            item_type="tile",
            date_field_id=self._field("res.partner", "create_date").id,
            compare_previous_period=True,
        )
        data = item.get_data({"date_preset": "today"})
        self.assertEqual(data["value"], 3)
        self.assertEqual(data["previous_value"], 0)

    def test_chart_previous_period_datasets(self):
        item = self._create_item(
            name="Bar Previous",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
            date_field_id=self._field("res.partner", "create_date").id,
            compare_previous_period=True,
        )
        data = item.get_data({"date_preset": "today"})
        self.assertEqual(data["type"], "chart")
        self.assertTrue(data["labels"])
        self.assertIn("previous_datasets", data)
        previous = data["previous_datasets"]
        self.assertEqual(len(previous), 1)
        self.assertEqual(len(previous[0]["data"]), len(data["labels"]))
        # Partners were created today, so the previous period is empty.
        self.assertEqual(previous[0]["data"], [0] * len(data["labels"]))

    def test_kpi_comparison(self):
        item = self._create_item(
            name="KPI Compare",
            item_type="kpi",
            kpi_mode="comparison",
            kpi_display="percent",
            model_2_id=self.env.ref("base.model_res_partner").id,
            domain_2=f"[('id', 'in', {self.partners[:1].ids})]",
        )
        data = item.get_data()
        self.assertEqual(data["value"], 3)
        self.assertEqual(data["value_2"], 1)

    def test_list_plain_with_pagination(self):
        item = self._create_item(
            name="Partner List",
            item_type="list",
            list_type="plain",
            page_size=2,
            list_column_ids=[
                (
                    0,
                    0,
                    {"sequence": 10, "field_id": self._field("res.partner", "name").id},
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
            sort_field_id=self._field("res.partner", "name").id,
            sort_dir="asc",
        )
        data = item.get_data()
        self.assertEqual(data["type"], "list")
        self.assertFalse(data["grouped"])
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["rows"]), 2)
        self.assertEqual(data["rows"][0]["values"][0], "Dash Partner BR 1")
        self.assertEqual(data["rows"][0]["values"][1], "Brazil")

        page_2 = item.get_data({"offset": 2})
        self.assertEqual(len(page_2["rows"]), 1)
        self.assertEqual(page_2["rows"][0]["values"][0], "Dash Partner US 1")

    def test_list_plain_interactive_sort(self):
        item = self._create_item(
            name="Sortable List",
            item_type="list",
            list_type="plain",
            list_column_ids=[
                (
                    0,
                    0,
                    {"sequence": 10, "field_id": self._field("res.partner", "name").id},
                ),
            ],
            sort_field_id=self._field("res.partner", "name").id,
            sort_dir="asc",
        )
        data = item.get_data()
        self.assertEqual(data["sort_field"], "name")
        self.assertEqual(data["sort_dir"], "asc")
        self.assertTrue(data["columns"][0]["sortable"])
        self.assertEqual(data["rows"][0]["values"][0], "Dash Partner BR 1")

        # Header click override reverses the configured order.
        data = item.get_data({"sort_field": "name", "sort_dir": "desc"})
        self.assertEqual(data["sort_field"], "name")
        self.assertEqual(data["sort_dir"], "desc")
        self.assertEqual(data["rows"][0]["values"][0], "Dash Partner US 1")

        # Fields that are not list columns fall back to the item config.
        data = item.get_data({"sort_field": "country_id", "sort_dir": "desc"})
        self.assertEqual(data["sort_field"], "name")
        self.assertEqual(data["sort_dir"], "asc")
        self.assertEqual(data["rows"][0]["values"][0], "Dash Partner BR 1")

    def test_list_column_order_respects_sequence(self):
        # Sequences reverse alphabetical order (country before name).
        item = self._create_item(
            name="Ordered Columns",
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
            ],
        )
        data = item.get_data()
        self.assertEqual(
            [column["name"] for column in data["columns"]], ["country_id", "name"]
        )
        self.assertEqual(data["rows"][0]["values"][0], "Brazil")

    def test_list_grouped(self):
        item = self._create_item(
            name="Grouped List",
            item_type="list",
            list_type="grouped",
            group_by_field_id=self._field("res.partner", "country_id").id,
            measure_ids=[
                (0, 0, {"field_id": self._field("res.partner", "partner_latitude").id})
            ],
        )
        data = item.get_data()
        self.assertTrue(data["grouped"])
        self.assertEqual(data["total"], 2)
        rows = {row["values"][0]: row["values"][1:] for row in data["rows"]}
        self.assertEqual(rows["Brazil"], [2, 30.0])
        self.assertEqual(rows["United States"], [1, 30.0])

    def test_date_filter_precedence(self):
        self.tile.write(
            {
                "date_field_id": self._field("res.partner", "create_date").id,
                "date_filter": "today",
            }
        )
        # Item filter applies when the UI filter is All Time.
        self.assertEqual(self.tile.get_data({"date_preset": "none"})["value"], 3)
        # The UI filter overrides the item filter.
        self.assertEqual(self.tile.get_data({"date_preset": "yesterday"})["value"], 0)

    def test_custom_date_range_param(self):
        self.tile.date_field_id = self._field("res.partner", "create_date").id
        now = datetime.now()
        params = {
            "date_preset": "custom",
            "date_from": fields.Datetime.to_string(now - timedelta(hours=1)),
            "date_to": fields.Datetime.to_string(now + timedelta(hours=1)),
        }
        self.assertEqual(self.tile.get_data(params)["value"], 3)
        params = {
            "date_preset": "custom",
            "date_from": fields.Datetime.to_string(now - timedelta(days=2)),
            "date_to": fields.Datetime.to_string(now - timedelta(days=1)),
        }
        self.assertEqual(self.tile.get_data(params)["value"], 0)

    def test_predefined_filter_param(self):
        dashboard_filter = self.env["boardkit.dashboard.filter"].create(
            {
                "name": "Companies",
                "dashboard_id": self.dashboard.id,
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain": "[('is_company', '=', True)]",
            }
        )
        data = self.tile.get_data({"filter_ids": [dashboard_filter.id]})
        self.assertEqual(data["value"], 2)

    def test_domain_placeholders(self):
        domain = self.dashboard._eval_domain("[('create_uid', '=', uid)]")
        self.assertEqual(domain, [("create_uid", "=", self.env.uid)])
        domain = self.dashboard._eval_domain("[('company_id', 'in', company_ids)]")
        self.assertEqual(domain, [("company_id", "in", self.env.companies.ids)])

    def test_get_items_data_isolates_errors(self):
        broken = self._create_item(name="Broken Chart", item_type="bar")
        result = self.env["boardkit.dashboard.item"].get_items_data(
            [self.tile.id, broken.id]
        )
        self.assertEqual(result[self.tile.id]["value"], 3)
        self.assertIn("error", result[broken.id])

    def test_drilldown_action(self):
        action = self.tile.get_drilldown_action(
            [("id", "in", self.partners.ids)], "Details"
        )
        self.assertEqual(action["res_model"], "res.partner")
        self.assertEqual(action["name"], "Details")
        self.assertEqual(action["domain"], [("id", "in", self.partners.ids)])

    def test_funnel_default_uses_related_model_order(self):
        item = self._create_item(
            name="Funnel",
            item_type="funnel",
            group_by_field_id=self._field("res.partner", "country_id").id,
            chart_sort="default",
        )
        data = item.get_data()
        self.assertEqual(data["type"], "funnel")
        # res.country is ordered by name: Brazil before United States.
        self.assertEqual(data["labels"], ["Brazil", "United States"])
        self.assertEqual(data["datasets"][0]["data"], [2, 1])

    def test_funnel_chart_sort_value_desc(self):
        item = self._create_item(
            name="Funnel Value Desc",
            item_type="funnel",
            group_by_field_id=self._field("res.partner", "country_id").id,
            chart_sort="value_desc",
        )
        data = item.get_data()
        self.assertEqual(data["labels"], ["Brazil", "United States"])
        self.assertEqual(data["datasets"][0]["data"], [2, 1])

    def test_funnel_value_asc_falls_back_to_descending(self):
        item = self._create_item(
            name="Funnel Value Asc",
            item_type="funnel",
            group_by_field_id=self._field("res.partner", "country_id").id,
            chart_sort="value_asc",
        )
        data = item.get_data()
        self.assertEqual(data["labels"], ["Brazil", "United States"])
        self.assertEqual(data["datasets"][0]["data"], [2, 1])

    def test_funnel_sort_by_related_field(self):
        item = self._create_item(
            name="Funnel By Code",
            item_type="funnel",
            group_by_field_id=self._field("res.partner", "country_id").id,
            chart_sort="value_desc",
            sort_field_id=self._field("res.country", "code").id,
            sort_dir="asc",
        )
        data = item.get_data()
        # Sort By overrides Chart Sort: BR before US by country code.
        self.assertEqual(data["labels"], ["Brazil", "United States"])
        self.assertEqual(data["datasets"][0]["data"], [2, 1])

        item.sort_dir = "desc"
        data = item.get_data()
        self.assertEqual(data["labels"], ["United States", "Brazil"])
        self.assertEqual(data["datasets"][0]["data"], [1, 2])

    def test_funnel_requires_group_by(self):
        item = self._create_item(name="Funnel Broken", item_type="funnel")
        data = item.get_data()
        self.assertIn("error", data)

    def test_gauge_value_target_max(self):
        item = self._create_item(
            name="Gauge",
            item_type="gauge",
            target_enabled=True,
            target_value=10,
            gauge_max=20,
        )
        data = item.get_data()
        self.assertEqual(data["type"], "gauge")
        self.assertEqual(data["value"], 3)
        self.assertEqual(data["target"], 10)
        self.assertEqual(data["max"], 20)

    def test_gauge_max_fallback(self):
        item = self._create_item(
            name="Gauge Fallback",
            item_type="gauge",
            target_enabled=True,
            target_value=10,
        )
        data = item.get_data()
        self.assertEqual(data["max"], 12.0)  # max(3, 10) * 1.2

    def test_bullet_with_target(self):
        item = self._create_item(
            name="Bullet",
            item_type="bullet",
            group_by_field_id=self._field("res.partner", "country_id").id,
            target_enabled=True,
            target_value=5,
        )
        data = item.get_data()
        self.assertEqual(data["type"], "bullet")
        self.assertEqual(data["target"], 5)
        self.assertEqual(set(data["labels"]), {"Brazil", "United States"})
        self.assertEqual(len(data["datasets"]), 1)

    def test_map_by_country(self):
        item = self._create_item(
            name="Map",
            item_type="map",
            map_mode="regions",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        data = item.get_data()
        self.assertEqual(data["type"], "map")
        self.assertEqual(data["mode"], "regions")
        by_code = {region["code"]: region["value"] for region in data["regions"]}
        self.assertEqual(by_code["BR"], 2)
        self.assertEqual(by_code["US"], 1)
        brazil = next(region for region in data["regions"] if region["code"] == "BR")
        self.assertIn(["country_id", "=", self.country_br.id], brazil["domain"])
        config = item._get_config()
        self.assertEqual(config["map_mode"], "regions")
        self.assertFalse(config["map_focus_country"])

    def test_map_requires_country_group_by(self):
        with self.assertRaises(ValidationError) as error:
            self._create_item(
                name="Map Broken",
                item_type="map",
                map_mode="regions",
                group_by_field_id=self._field("res.partner", "is_company").id,
            )
        self.assertIn("Countries", str(error.exception))

    def test_map_points_payload(self):
        item = self._create_item(
            name="Map Points",
            item_type="map",
            map_mode="points",
            latitude_field_id=self._field("res.partner", "partner_latitude").id,
            longitude_field_id=self._field("res.partner", "partner_longitude").id,
            map_focus_country_id=self.country_br.id,
        )
        data = item.get_data()
        self.assertEqual(data["type"], "map")
        self.assertEqual(data["mode"], "points")
        self.assertFalse(data["truncated"])
        self.assertEqual(len(data["points"]), 3)
        by_label = {point["label"]: point for point in data["points"]}
        self.assertAlmostEqual(by_label["Dash Partner BR 1"]["latitude"], 10.0)
        self.assertAlmostEqual(by_label["Dash Partner BR 1"]["longitude"], -46.63)
        self.assertEqual(by_label["Dash Partner BR 1"]["value"], 1)
        self.assertEqual(by_label["Dash Partner BR 1"]["count"], 1)
        self.assertIn(
            ["id", "in", [self.partners[0].id]],
            by_label["Dash Partner BR 1"]["domain"],
        )
        config = item._get_config()
        self.assertEqual(config["map_mode"], "points")
        self.assertEqual(config["map_focus_country"], "BR")

    def test_map_points_merges_shared_coordinates(self):
        twin = self.env["res.partner"].create(
            {
                "name": "Dash Partner BR 1 Twin",
                "country_id": self.country_br.id,
                "partner_latitude": 10.0,
                "partner_longitude": -46.63,
            }
        )
        item = self._create_item(
            name="Map Points Merge",
            item_type="map",
            map_mode="points",
            domain=f"[('id', 'in', {(self.partners | twin).ids})]",
            latitude_field_id=self._field("res.partner", "partner_latitude").id,
            longitude_field_id=self._field("res.partner", "partner_longitude").id,
        )
        data = item.get_data()
        # Four records, but two of them share the same coordinates.
        self.assertEqual(len(data["points"]), 3)
        merged = max(data["points"], key=lambda point: point["count"])
        self.assertEqual(merged["count"], 2)
        self.assertEqual(merged["value"], 2)
        self.assertIn("+1 more", merged["label"])
        # The marker leaf is appended after the item domain, which also filters on id.
        merged_ids = [
            leaf[2] for leaf in merged["domain"] if leaf[0] == "id" and leaf[1] == "in"
        ][-1]
        self.assertEqual(set(merged_ids), {self.partners[0].id, twin.id})
        # The biggest marker comes first so smaller ones stay clickable.
        self.assertEqual(data["points"][0]["count"], 2)

    def test_map_points_measure_sums_per_coordinate(self):
        twin = self.env["res.partner"].create(
            {
                "name": "Dash Partner BR 1 Twin",
                "country_id": self.country_br.id,
                "partner_latitude": 10.0,
                "partner_longitude": -46.63,
            }
        )
        item = self._create_item(
            name="Map Points Measure",
            item_type="map",
            map_mode="points",
            aggregation="sum",
            domain=f"[('id', 'in', {(self.partners | twin).ids})]",
            measure_field_id=self._field("res.partner", "partner_latitude").id,
            latitude_field_id=self._field("res.partner", "partner_latitude").id,
            longitude_field_id=self._field("res.partner", "partner_longitude").id,
        )
        data = item.get_data()
        merged = max(data["points"], key=lambda point: point["count"])
        self.assertEqual(merged["count"], 2)
        self.assertAlmostEqual(merged["value"], 20.0)

    def test_map_points_skips_missing_coordinates(self):
        blank = self.env["res.partner"].create(
            {
                "name": "Dash Partner No Geo",
                "country_id": self.country_br.id,
                "partner_latitude": 0.0,
                "partner_longitude": 0.0,
            }
        )
        item = self._create_item(
            name="Map Points Filter",
            item_type="map",
            map_mode="points",
            domain=f"[('id', 'in', {(self.partners | blank).ids})]",
            latitude_field_id=self._field("res.partner", "partner_latitude").id,
            longitude_field_id=self._field("res.partner", "partner_longitude").id,
        )
        data = item.get_data()
        labels = {point["label"] for point in data["points"]}
        self.assertNotIn("Dash Partner No Geo", labels)
        self.assertEqual(len(data["points"]), 3)

    def test_map_points_respects_record_limit(self):
        item = self._create_item(
            name="Map Points Limit",
            item_type="map",
            map_mode="points",
            record_limit=2,
            latitude_field_id=self._field("res.partner", "partner_latitude").id,
            longitude_field_id=self._field("res.partner", "partner_longitude").id,
        )
        data = item.get_data()
        self.assertEqual(len(data["points"]), 2)

    def test_map_points_requires_lat_long(self):
        with self.assertRaises(ValidationError) as error:
            self._create_item(
                name="Map Points Broken",
                item_type="map",
                map_mode="points",
            )
        self.assertIn("Latitude", str(error.exception))

    def _create_children(self, values):
        """Contacts whose parent holds the geolocation.

        The invoice type keeps the address sync from overwriting the country,
        so the parent country is the only one a relation map can report.
        """
        return self.env["res.partner"].create(
            [dict(vals, type="invoice") for vals in values]
        )

    def test_map_points_through_relation(self):
        self.manager.partner_id.write(
            {"partner_latitude": 12.5, "partner_longitude": -45.5}
        )
        item = self._create_item(
            name="Map Points Relation",
            model_id=self.env.ref("base.model_res_users").id,
            item_type="map",
            map_mode="points",
            domain=f"[('id', 'in', {[self.manager.id, self.user.id]})]",
            map_relation_field_id=self._field("res.users", "partner_id").id,
            latitude_field_id=self._field("res.partner", "partner_latitude").id,
            longitude_field_id=self._field("res.partner", "partner_longitude").id,
        )
        data = item.get_data()
        self.assertEqual(data["mode"], "points")
        # The other user has no coordinates on its partner.
        self.assertEqual(len(data["points"]), 1)
        point = data["points"][0]
        self.assertAlmostEqual(point["latitude"], 12.5)
        self.assertAlmostEqual(point["longitude"], -45.5)
        self.assertEqual(point["count"], 1)
        self.assertIn(["id", "in", [self.manager.id]], point["domain"])

    def test_map_points_through_relation_merges_shared_parent(self):
        children = self._create_children(
            [
                {"name": "Dash Child BR A", "parent_id": self.partners[0].id},
                {"name": "Dash Child BR B", "parent_id": self.partners[0].id},
                {"name": "Dash Child US", "parent_id": self.partners[2].id},
            ]
        )
        item = self._create_item(
            name="Map Points Relation Merge",
            item_type="map",
            map_mode="points",
            domain=f"[('id', 'in', {children.ids})]",
            map_relation_field_id=self._field("res.partner", "parent_id").id,
            latitude_field_id=self._field("res.partner", "partner_latitude").id,
            longitude_field_id=self._field("res.partner", "partner_longitude").id,
        )
        data = item.get_data()
        self.assertEqual(len(data["points"]), 2)
        merged = max(data["points"], key=lambda point: point["count"])
        self.assertEqual(merged["count"], 2)
        self.assertAlmostEqual(merged["latitude"], 10.0)
        self.assertAlmostEqual(merged["longitude"], -46.63)
        merged_ids = [
            leaf[2] for leaf in merged["domain"] if leaf[0] == "id" and leaf[1] == "in"
        ][-1]
        self.assertEqual(set(merged_ids), set(children[:2].ids))

    def test_map_regions_through_relation(self):
        country_ar = self.env.ref("base.ar")
        children = self._create_children(
            [
                {
                    "name": "Dash Child BR A",
                    "parent_id": self.partners[0].id,
                    "country_id": country_ar.id,
                },
                {
                    "name": "Dash Child BR B",
                    "parent_id": self.partners[1].id,
                    "country_id": country_ar.id,
                },
                {
                    "name": "Dash Child US",
                    "parent_id": self.partners[2].id,
                    "country_id": country_ar.id,
                },
            ]
        )
        item = self._create_item(
            name="Map Regions Relation",
            item_type="map",
            map_mode="regions",
            domain=f"[('id', 'in', {children.ids})]",
            map_relation_field_id=self._field("res.partner", "parent_id").id,
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        data = item.get_data()
        self.assertEqual(data["mode"], "regions")
        by_code = {region["code"]: region["value"] for region in data["regions"]}
        # The countries come from the parents, not from the contacts themselves.
        self.assertEqual(by_code, {"BR": 2, "US": 1})
        brazil = next(region for region in data["regions"] if region["code"] == "BR")
        self.assertIn(
            ["parent_id.country_id", "=", self.country_br.id], brazil["domain"]
        )

    def test_map_regions_through_relation_average_is_weighted(self):
        children = self._create_children(
            [
                {
                    "name": "Dash Child BR A",
                    "parent_id": self.partners[0].id,
                    "partner_latitude": 10.0,
                },
                {
                    "name": "Dash Child BR B",
                    "parent_id": self.partners[1].id,
                    "partner_latitude": 20.0,
                },
                {
                    "name": "Dash Child BR C",
                    "parent_id": self.partners[1].id,
                    "partner_latitude": 30.0,
                },
            ]
        )
        item = self._create_item(
            name="Map Regions Relation Average",
            item_type="map",
            map_mode="regions",
            aggregation="avg",
            domain=f"[('id', 'in', {children.ids})]",
            map_relation_field_id=self._field("res.partner", "parent_id").id,
            group_by_field_id=self._field("res.partner", "country_id").id,
            measure_ids=[
                (0, 0, {"field_id": self._field("res.partner", "partner_latitude").id})
            ],
        )
        data = item.get_data()
        brazil = next(region for region in data["regions"] if region["code"] == "BR")
        # Mean of the three contacts, not the mean of the two parent averages.
        self.assertAlmostEqual(brazil["value"], 20.0)

    def test_map_relation_rejects_field_from_other_model(self):
        parent_field = self._field("res.partner", "parent_id")
        with self.assertRaises(ValidationError) as error:
            self._create_item(
                name="Map Relation Broken Coordinates",
                item_type="map",
                map_mode="points",
                map_relation_field_id=parent_field.id,
                latitude_field_id=self._field("res.currency", "rounding").id,
                longitude_field_id=self._field("res.partner", "partner_longitude").id,
            )
        self.assertIn("rounding", str(error.exception))
        with self.assertRaises(ValidationError) as error:
            self._create_item(
                name="Map Relation Broken Country",
                model_id=self.env.ref("base.model_res_users").id,
                item_type="map",
                map_mode="regions",
                map_relation_field_id=self._field("res.users", "partner_id").id,
                group_by_field_id=self._field("res.users", "country_id").id,
            )
        self.assertIn("country_id", str(error.exception))

    @staticmethod
    def _custom_params(field, operator, value, model="res.partner"):
        return {
            "custom_filters": [
                {"model": model, "field": field, "operator": operator, "value": value}
            ]
        }

    def test_custom_filter_char(self):
        params = self._custom_params("name", "ilike", "BR")
        self.assertEqual(self.tile.get_data(params)["value"], 2)
        params = self._custom_params("name", "not ilike", "BR")
        self.assertEqual(self.tile.get_data(params)["value"], 1)

    def test_custom_filter_number(self):
        params = self._custom_params("partner_latitude", ">", 15)
        self.assertEqual(self.tile.get_data(params)["value"], 2)
        params = self._custom_params("partner_latitude", "<=", "10")
        self.assertEqual(self.tile.get_data(params)["value"], 1)

    def test_custom_filter_float(self):
        params = self._custom_params("partner_latitude", ">=", 20.0)
        self.assertEqual(self.tile.get_data(params)["value"], 2)

    def test_custom_filter_selection(self):
        params = self._custom_params("type", "=", "contact")
        self.assertEqual(self.tile.get_data(params)["value"], 3)
        params = self._custom_params("type", "!=", "contact")
        self.assertEqual(self.tile.get_data(params)["value"], 0)

    def test_custom_filter_boolean(self):
        params = self._custom_params("is_company", "=", True)
        self.assertEqual(self.tile.get_data(params)["value"], 2)
        params = self._custom_params("is_company", "=", False)
        self.assertEqual(self.tile.get_data(params)["value"], 1)

    def test_custom_filter_many2one(self):
        params = self._custom_params("country_id", "ilike", "Braz")
        self.assertEqual(self.tile.get_data(params)["value"], 2)

    def test_custom_filter_date(self):
        # res.partner has no stored Date field in Odoo 18; currency rates do.
        Rate = self.env["res.currency.rate"]
        today = fields.Date.context_today(self.tile)
        rate = Rate.create(
            {
                "name": today,
                "currency_id": self.env.ref("base.USD").id,
                "company_rate": 1.0,
            }
        )
        item = self._create_item(
            name="Rates",
            item_type="tile",
            model_id=self.env["ir.model"]._get("res.currency.rate").id,
            domain=f"[('id', '=', {rate.id})]",
        )
        params = self._custom_params(
            "name", "=", fields.Date.to_string(today), model="res.currency.rate"
        )
        self.assertEqual(item.get_data(params)["value"], 1)
        params = self._custom_params(
            "name",
            "=",
            fields.Date.to_string(today - timedelta(days=1)),
            model="res.currency.rate",
        )
        self.assertEqual(item.get_data(params)["value"], 0)

    def test_custom_filter_empty_date_rejected(self):
        item = self._create_item(
            name="Rates Empty Date",
            item_type="tile",
            model_id=self.env["ir.model"]._get("res.currency.rate").id,
            domain="[]",
        )
        params = self._custom_params("name", "=", "", model="res.currency.rate")
        self.assertIn("error", item.get_data(params))

    def test_custom_filter_datetime_day_bounds(self):
        # Derive the day from a stored timestamp so the assertion stays valid
        # when the user timezone is ahead of UTC (e.g. Europe/Brussels).
        create_dt = fields.Datetime.to_datetime(self.partners[0].create_date)
        local_day = fields.Datetime.context_timestamp(self.tile, create_dt).date()
        day = fields.Date.to_string(local_day)
        leaf = self.tile._custom_filter_leaf(
            {
                "model": "res.partner",
                "field": "create_date",
                "operator": "<=",
                "value": day,
            }
        )
        self.assertEqual(leaf[0], "create_date")
        self.assertEqual(leaf[1], "<")
        # Inclusive day bound must cover the records created that local day.
        params = self._custom_params("create_date", "<=", day)
        self.assertEqual(self.tile.get_data(params)["value"], 3)
        params = self._custom_params("create_date", ">", day)
        self.assertEqual(self.tile.get_data(params)["value"], 0)

    def test_past_preset_includes_today_on_date_fields(self):
        """Date fields must ceil partial-day upper bounds (e.g. preset past)."""
        from types import SimpleNamespace

        field = SimpleNamespace(name="demo_date", ttype="date")
        # Force UTC so the expected calendar day does not depend on user.tz.
        item = self.tile.with_context(tz="UTC")
        # Mid-day exclusive end must become tomorrow so today stays included.
        domain = item._date_domain(field, (None, datetime(2026, 7, 15, 15, 30, 0)))
        self.assertEqual(domain, [("demo_date", "<", "2026-07-16")])
        # Midnight exclusive end keeps the calendar day unchanged.
        domain = item._date_domain(field, (None, datetime(2026, 7, 15, 0, 0, 0)))
        self.assertEqual(domain, [("demo_date", "<", "2026-07-15")])

    def test_fields_must_belong_to_item_model(self):
        with self.assertRaises(ValidationError):
            self._create_item(
                name="Wrong Field",
                item_type="bar",
                group_by_field_id=self._field("res.users", "login").id,
            )
        with self.assertRaises(ValidationError):
            self.env["boardkit.dashboard.item.column"].create(
                {
                    "item_id": self.tile.id,
                    "field_id": self._field("res.users", "login").id,
                }
            )

    def test_custom_filter_other_model_ignored(self):
        params = self._custom_params("name", "ilike", "BR", model="res.users")
        self.assertEqual(self.tile.get_data(params)["value"], 3)

    def test_custom_filter_invalid_field(self):
        params = self._custom_params("not_a_field", "=", 1)
        self.assertIn("error", self.tile.get_data(params))

    def test_custom_filter_invalid_operator(self):
        params = self._custom_params("name", "child_of", 1)
        self.assertIn("error", self.tile.get_data(params))

    def test_custom_filter_combined_with_item_domain(self):
        # The custom filter narrows the item domain instead of replacing it.
        params = self._custom_params("name", "ilike", "Dash Partner")
        self.assertEqual(self.tile.get_data(params)["value"], 3)

    def test_get_custom_filter_fields(self):
        entries = self.env["boardkit.dashboard"].get_custom_filter_fields("res.partner")
        by_name = {entry["name"]: entry for entry in entries}
        self.assertIn("name", by_name)
        self.assertEqual(by_name["country_id"]["type"], "many2one")
        self.assertTrue(by_name["lang"]["selection"])
        self.assertNotIn("id", by_name)
        self.assertNotIn("image_1920", by_name)  # Binary fields are excluded.
        labels = [entry["label"] for entry in entries]
        self.assertEqual(labels, sorted(labels))

    def test_get_custom_filter_fields_unknown_model(self):
        self.assertEqual(
            self.env["boardkit.dashboard"].get_custom_filter_fields("no.such.model"),
            [],
        )
