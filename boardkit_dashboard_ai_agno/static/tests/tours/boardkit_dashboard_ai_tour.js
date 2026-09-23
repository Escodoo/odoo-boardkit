/** @odoo-module **/
// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import tour from "web_tour.tour";

// Odoo 16 tour steps click their trigger unless they define a run.
function waitFor() {
    // Only wait for the trigger to be rendered.
}

tour.register("boardkit_dashboard_ai_tour", {test: true}, [
    {
        content: "Wait for the dashboard action to render",
        trigger: ".o_boardkit_dashboard .o_boardkit_dashboard_topbar",
        run: waitFor,
    },
    {
        content: "Open the board chat",
        trigger: ".o_boardkit_dashboard_topbar_actions button:contains(Ask AI)",
        run: "click",
    },
    {
        content: "The chat panel is open",
        trigger: ".o_boardkit_dashboard_ai_panel[aria-label='Board chat']",
        run: waitFor,
    },
    {
        content: "Type a question without sending it with Enter",
        trigger: ".o_boardkit_dashboard_ai_input",
        run: "text Why is overdue high?",
    },
    {
        content: "Send the question",
        trigger: ".o_boardkit_dashboard_ai_composer .btn-primary",
        // Odoo 16 tours ignore the removal of an empty attribute such as
        // disabled="", so a :not([disabled]) trigger may never be checked
        // again: click as soon as OWL has rendered the typed question.
        run() {
            const button = this.$anchor[0];
            const clickWhenEnabled = () => {
                if (button.disabled) {
                    setTimeout(clickWhenEnabled, 50);
                } else {
                    button.click();
                }
            };
            clickWhenEnabled();
        },
    },
    {
        content: "The user question is shown",
        trigger: ".o_boardkit_dashboard_ai_message_user:contains(Why is overdue high?)",
        run: waitFor,
    },
    {
        content: "The mocked assistant answer is shown",
        trigger: ".o_boardkit_dashboard_ai_message_assistant:contains(Mock answer)",
        run: waitFor,
    },
    {
        content: "Close the panel without clearing the thread",
        trigger: ".o_boardkit_dashboard_ai_panel button[title='Close']",
        run: "click",
    },
    {
        content: "The panel is closed",
        trigger: ".o_boardkit_dashboard:not(:has(.o_boardkit_dashboard_ai_panel))",
        run: waitFor,
    },
    {
        content: "Reopen the board chat",
        trigger: ".o_boardkit_dashboard_topbar_actions button:contains(Ask AI)",
        run: "click",
    },
    {
        content: "The previous question is still there",
        trigger: ".o_boardkit_dashboard_ai_message_user:contains(Why is overdue high?)",
        run: waitFor,
    },
    {
        content: "Clear the conversation",
        trigger: ".o_boardkit_dashboard_ai_panel button[title='Clear conversation']",
        run: "click",
    },
    {
        content: "The thread is empty again",
        trigger:
            ".o_boardkit_dashboard_ai_panel_body:not(:has(.o_boardkit_dashboard_ai_message))",
        run: waitFor,
    },
]);
