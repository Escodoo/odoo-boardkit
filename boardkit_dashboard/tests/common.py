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
