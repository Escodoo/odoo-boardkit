# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, new_test_user


class BoardkitDashboardCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Force en_US so label assertions do not depend on the language the
        # database was created with (e.g. load_language = pt_BR).
        cls.env["res.lang"]._activate_lang("en_US")
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, tz="UTC", lang="en_US")
        )
        cls.manager = new_test_user(
            cls.env,
            login="dashboard_manager",
            groups="base.group_user,boardkit_dashboard.group_dashboard_manager",
        )
        cls.user = new_test_user(
            cls.env,
            login="dashboard_user",
            groups="base.group_user,boardkit_dashboard.group_dashboard_user",
        )
        cls.country_br = cls.env.ref("base.br")
        cls.country_us = cls.env.ref("base.us")
        cls.partners = cls.env["res.partner"].create(
            [
                {
                    "name": "Dash Partner BR 1",
                    "country_id": cls.country_br.id,
                    "is_company": True,
                    "partner_latitude": 10.0,
                    "partner_longitude": -46.63,
                },
                {
                    "name": "Dash Partner BR 2",
                    "country_id": cls.country_br.id,
                    "is_company": False,
                    "partner_latitude": 20.0,
                    "partner_longitude": -43.17,
                },
                {
                    "name": "Dash Partner US 1",
                    "country_id": cls.country_us.id,
                    "is_company": True,
                    "partner_latitude": 30.0,
                    "partner_longitude": -74.00,
                },
            ]
        )
        cls.dashboard = cls.env["boardkit.dashboard"].create(
            {
                "name": "Test Dashboard",
                "published": True,
                "menu_parent_id": cls.env.ref(
                    "boardkit_dashboard.menu_dashboard_root"
                ).id,
            }
        )
        cls.base_domain = f"[('id', 'in', {cls.partners.ids})]"
        cls.tile = cls.env["boardkit.dashboard.item"].create(
            {
                "name": "Partner Count",
                "dashboard_id": cls.dashboard.id,
                "item_type": "tile",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "domain": cls.base_domain,
                "aggregation": "count",
            }
        )

    @classmethod
    def _create_item(cls, **values):
        vals = {
            "name": "Item",
            "dashboard_id": cls.dashboard.id,
            "model_id": cls.env.ref("base.model_res_partner").id,
            "domain": cls.base_domain,
            "aggregation": "count",
        }
        vals.update(values)
        return cls.env["boardkit.dashboard.item"].create(vals)

    @classmethod
    def _field(cls, model_name, field_name):
        return cls.env["ir.model.fields"]._get(model_name, field_name)


class BoardkitTemplateSmokeMixin:
    """Create every declared template and render all of its items.

    Template payloads are resolved silently: ``_import_prepare_vals`` turns an
    unknown field name into ``False`` instead of raising, and ``get_data``
    traps exceptions in an ``error`` payload. A template pointing at a missing
    or non-stored field therefore installs and creates a board without any
    warning, so each template module declares its records in
    ``template_xmlids`` and this mixin checks both resolution and rendering.
    """

    template_xmlids = ()

    # Odoo's test loader only collects methods declared in the test class
    # itself unless this flag is set.
    allow_inherited_tests_method = True

    # Payload keys holding a field name, resolved by ``_import_prepare_vals``
    # against the item model or the KPI comparison model.
    _SMOKE_FIELD_KEYS = (
        "date_field_id",
        "group_by_field_id",
        "subgroup_by_field_id",
        "measure_field_id",
        "measure_x_field_id",
        "measure_y_field_id",
        "latitude_field_id",
        "longitude_field_id",
        "date_field_2_id",
        "measure_field_2_id",
    )

    def test_template_payload_resolves_and_renders(self):
        self.assertTrue(
            self.template_xmlids,
            "Declare the template xmlids to smoke test.",
        )
        for xmlid in self.template_xmlids:
            template = self.env.ref(xmlid)
            dashboards = self.env["boardkit.dashboard"].browse(
                self.env["boardkit.dashboard"].create_from_template(template.id)
            )
            boards = template.payload["dashboards"]
            self.assertEqual(len(dashboards), len(boards))
            for dashboard, board_data in zip(dashboards, boards, strict=True):
                with self.subTest(template=xmlid, board=dashboard.name):
                    self._assert_items_render(dashboard, board_data)
                    self._assert_filters_evaluate(dashboard, board_data)

    def _assert_items_render(self, dashboard, board_data):
        items_by_name = {item.name: item for item in dashboard.item_ids}
        payload_items = board_data.get("items", [])
        self.assertEqual(len(items_by_name), len(payload_items))
        for item_data in payload_items:
            name = item_data["name"]
            self.assertIn(name, items_by_name)
            item = items_by_name[name]
            self._assert_item_fields_resolved(item, item_data)
            data = item.get_data()
            self.assertNotIn(
                "error",
                data,
                f"{dashboard.name} / {name} failed to render: {data.get('error')}",
            )

    def _assert_item_fields_resolved(self, item, item_data):
        label = f"{item.dashboard_id.name} / {item.name}"
        for key in self._SMOKE_FIELD_KEYS:
            expected = item_data.get(key)
            if expected:
                self.assertEqual(item[key].name, expected, f"{label}: {key}")
        expected_measures = item_data.get("measures") or []
        if expected_measures:
            self.assertEqual(
                item._ordered_measure_fields().mapped("name"),
                expected_measures,
                f"{label}: measures",
            )
        expected_columns = item_data.get("list_columns") or []
        if expected_columns:
            self.assertEqual(
                item.list_column_ids.mapped("field_id.name"),
                expected_columns,
                f"{label}: list_columns",
            )
        expected_sort = item_data.get("sort_field_id")
        if expected_sort:
            self.assertEqual(item.sort_field_id.name, expected_sort, f"{label}: sort")

    def _assert_filters_evaluate(self, dashboard, board_data):
        for filter_data in board_data.get("filters", []):
            name = filter_data["name"]
            record = dashboard.filter_ids.filtered(lambda f, n=name: f.name == n)
            self.assertEqual(len(record), 1, f"{dashboard.name}: filter {name}")
            # Raises when the domain does not evaluate against the filter model.
            dashboard._eval_domain(record.domain, record.model_id.model)
