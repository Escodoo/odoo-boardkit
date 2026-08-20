# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDashboardAiTour(HttpCase):
    def _prepare_tour_dashboard(self):
        dashboard = self.env["boardkit.dashboard"].create(
            {
                "name": "AI Tour Dashboard",
                "published": True,
                "ai_enabled": True,
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

    def test_board_chat_panel_tour(self):
        dashboard = self._prepare_tour_dashboard()

        def _fake_run(xmlid, record=None, **kwargs):
            return {
                "body": "<p>Mock answer</p>",
                "body_is_html": True,
                "actions": [],
            }

        with patch.object(
            type(self.env["boardkit.dashboard"]),
            "_run_boardkit_bridge",
            side_effect=_fake_run,
        ):
            self.start_tour(
                f"/odoo/action-{dashboard.client_action_id.id}",
                "boardkit_dashboard_ai_tour",
                login="admin",
            )
