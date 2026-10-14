# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from .common import BoardkitDashboardCommon


@tagged("post_install", "-at_install")
class TestItemDrill(BoardkitDashboardCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.chart = cls._create_item(
            name="By Country",
            item_type="bar",
            group_by_field_id=cls._field("res.partner", "country_id").id,
        )
        cls.level = cls.env["boardkit.dashboard.item.drill"].create(
            {
                "item_id": cls.chart.id,
                "sequence": 10,
                "group_by_field_id": cls._field("res.partner", "is_company").id,
                "chart_type": "pie",
            }
        )

    def test_get_config_includes_drill_levels(self):
        config = self.chart._get_config()
        self.assertEqual(len(config["drill_levels"]), 1)
        self.assertEqual(config["drill_levels"][0]["id"], self.level.id)
        self.assertEqual(config["drill_levels"][0]["index"], 0)
        self.assertEqual(config["drill_levels"][0]["type"], "pie")
        self.assertEqual(
            config["drill_levels"][0]["group_by_field_id"],
            self._field("res.partner", "is_company").id,
        )
        self.assertTrue(config["drill_levels"][0]["label"])
        self.assertEqual(config["aggregation"], "count")

    def test_get_drill_data_narrows_domain(self):
        brazil_domain = [
            ("id", "in", self.partners.ids),
            ("country_id", "=", self.country_br.id),
        ]
        data = self.chart.get_drill_data(self.level.id, brazil_domain)
        self.assertEqual(data["type"], "chart")
        by_label = dict(zip(data["labels"], data["datasets"][0]["data"], strict=True))
        self.assertEqual(by_label["Yes"], 1)
        self.assertEqual(by_label["No"], 1)
        # Drilldown domains keep the Brazil restriction.
        yes_index = data["labels"].index("Yes")
        self.assertIn(
            ["country_id", "=", self.country_br.id],
            data["datasets"][0]["drilldowns"][yes_index],
        )

    def test_get_drill_data_sort_and_limit(self):
        self.level.write({"chart_sort": "value_desc", "record_limit": 1})
        data = self.chart.get_drill_data(
            self.level.id, [("id", "in", self.partners.ids)]
        )
        self.assertEqual(len(data["labels"]), 1)
        self.assertEqual(data["datasets"][0]["data"], [2])  # companies

    def test_get_drill_data_funnel_forces_descending(self):
        self.level.write({"chart_type": "funnel", "chart_sort": "value_asc"})
        data = self.chart.get_drill_data(
            self.level.id, [("id", "in", self.partners.ids)]
        )
        self.assertEqual(data["type"], "funnel")
        self.assertEqual(data["labels"], ["Yes", "No"])
        self.assertEqual(data["datasets"][0]["data"], [2, 1])

    def test_get_drill_data_rejects_foreign_level(self):
        other = self._create_item(
            name="Other",
            item_type="bar",
            group_by_field_id=self._field("res.partner", "country_id").id,
        )
        with self.assertRaises(ValidationError):
            other.get_drill_data(self.level.id, [])

    def test_get_preview_drill_data_matches_saved_level(self):
        brazil_domain = [
            ("id", "in", self.partners.ids),
            ("country_id", "=", self.country_br.id),
        ]
        snapshot = {
            "item_id": self.chart.id,
            "model": "res.partner",
            "aggregation": "count",
            "measure_field_ids": [],
            "drill_levels": self.chart._get_config()["drill_levels"],
        }
        data = self.env["boardkit.dashboard.item"].get_preview_drill_data(
            snapshot, 0, brazil_domain
        )
        expected = self.chart.get_drill_data(self.level.id, brazil_domain)
        self.assertEqual(data["labels"], expected["labels"])
        self.assertEqual(data["datasets"][0]["data"], expected["datasets"][0]["data"])

    def test_get_preview_drill_data_unsaved_level(self):
        # Virtual item with a not-yet-persisted drill level (form preview).
        item = self.env["boardkit.dashboard.item"].new(
            {
                "name": "Virtual Drill",
                "dashboard_id": self.dashboard.id,
                "item_type": "bar",
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain": self.base_domain,
                "aggregation": "count",
                "group_by_field_id": self._field("res.partner", "country_id").id,
                "drill_level_ids": [
                    (
                        0,
                        0,
                        {
                            "sequence": 10,
                            "group_by_field_id": self._field(
                                "res.partner", "is_company"
                            ).id,
                            "chart_type": "pie",
                        },
                    )
                ],
            }
        )
        config = item._get_config()
        self.assertEqual(config["drill_levels"][0]["id"], 0)
        snapshot = {
            "item_id": 0,
            "model": config["model"],
            "aggregation": config["aggregation"],
            "measure_field_ids": config["measure_field_ids"],
            "drill_levels": config["drill_levels"],
        }
        data = self.env["boardkit.dashboard.item"].get_preview_drill_data(
            snapshot,
            0,
            [("id", "in", self.partners.ids), ("country_id", "=", self.country_br.id)],
        )
        by_label = dict(zip(data["labels"], data["datasets"][0]["data"], strict=True))
        self.assertEqual(by_label["Yes"], 1)
        self.assertEqual(by_label["No"], 1)

    def test_get_preview_drill_data_rejects_bad_index(self):
        snapshot = {
            "item_id": self.chart.id,
            "model": "res.partner",
            "aggregation": "count",
            "measure_field_ids": [],
            "drill_levels": self.chart._get_config()["drill_levels"],
        }
        with self.assertRaises(ValidationError):
            self.env["boardkit.dashboard.item"].get_preview_drill_data(snapshot, 5, [])

    def test_onchange_model_clears_drill_levels(self):
        form = Form(self.chart)
        form.model_id = self.env.ref("base.model_res_users")
        self.assertFalse(form.drill_level_ids)

    def test_export_import_preserves_drill_levels(self):
        payload = self.dashboard.export_config()
        chart_data = next(
            item
            for item in payload["dashboards"][0]["items"]
            if item["item_type"] == "bar"
        )
        self.assertEqual(len(chart_data["drill_levels"]), 1)
        self.assertEqual(
            chart_data["drill_levels"][0]["group_by_field_id"], "is_company"
        )
        self.assertEqual(chart_data["drill_levels"][0]["chart_type"], "pie")

        new_ids = self.env["boardkit.dashboard"].import_config(payload)
        imported = self.env["boardkit.dashboard"].browse(new_ids)
        chart = imported.item_ids.filtered(lambda item: item.item_type == "bar")
        self.assertEqual(len(chart.drill_level_ids), 1)
        self.assertEqual(chart.drill_level_ids.group_by_field_id.name, "is_company")
        self.assertEqual(chart.drill_level_ids.chart_type, "pie")
