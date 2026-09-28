/** @odoo-module **/
// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import tour from "web_tour.tour";

// Odoo 16 tour steps click their trigger unless they define a run.
function waitFor() {
    // Only wait for the trigger to be rendered.
}

tour.register("boardkit_dashboard_tour", {test: true}, [
    {
        content: "Wait for the dashboard action to render",
        trigger: ".o_boardkit_dashboard .o_boardkit_dashboard_topbar",
        run: waitFor,
    },
    {
        content: "At least one item card is rendered",
        trigger: ".o_boardkit_dashboard .o_boardkit_dashboard_card",
        run: waitFor,
    },
    {
        content: "The tile value is computed and displayed",
        trigger: ".o_boardkit_dashboard .o_boardkit_dashboard_big_value",
        run: waitFor,
    },
]);
