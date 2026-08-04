# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDashboardTour(HttpCase):
    def _prepare_tour_dashboard(self):
        dashboard = self.env["boardkit.dashboard"].create(
            {
                "name": "Tour Dashboard",
                "published": True,
                "menu_parent_id": self.env.ref(
                    "boardkit_dashboard.menu_dashboard_root"
                ).id,
            }
        )
        self.env["boardkit.dashboard.item"].create(
            {
                "name": "Tour Tile",
                "dashboard_id": dashboard.id,
                "item_type": "tile",
                "model_id": self.env.ref("base.model_res_partner").id,
                "aggregation": "count",
            }
        )
        return dashboard

    def test_dashboard_rendering_tour(self):
        dashboard = self._prepare_tour_dashboard()
        self.start_tour(
            f"/odoo/action-{dashboard.client_action_id.id}",
            "boardkit_dashboard_tour",
            login="admin",
        )

    def test_dashboard_mobile_rendering_tour(self):
        """Smoke-test that the dashboard renders in a mobile viewport."""
        self.browser_size = "375x800"
        dashboard = self._prepare_tour_dashboard()
        self.start_tour(
            f"/odoo/action-{dashboard.client_action_id.id}",
            "boardkit_dashboard_tour",
            login="admin",
        )
