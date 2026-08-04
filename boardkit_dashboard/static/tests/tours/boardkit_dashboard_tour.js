// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("boardkit_dashboard_tour", {
    steps: () => [
        {
            content: "Wait for the dashboard action to render",
            trigger: ".o_boardkit_dashboard .o_boardkit_dashboard_topbar",
        },
        {
            content: "At least one item card is rendered",
            trigger: ".o_boardkit_dashboard .o_boardkit_dashboard_card",
        },
        {
            content: "The tile value is computed and displayed",
            trigger: ".o_boardkit_dashboard .o_boardkit_dashboard_big_value",
        },
    ],
});
