// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("boardkit_dashboard_ai_tour", {
    steps: () => [
        {
            content: "Wait for the dashboard action to render",
            trigger: ".o_boardkit_dashboard .o_boardkit_dashboard_topbar",
        },
        {
            content: "Open the board chat",
            trigger: ".o_boardkit_dashboard_topbar_actions button:contains(Ask AI)",
            run: "click",
        },
        {
            content: "The chat panel is open",
            trigger: ".o_boardkit_dashboard_ai_panel[aria-label='Board chat']",
        },
        {
            content: "Type a question without sending it with Enter",
            trigger: ".o_boardkit_dashboard_ai_input",
            run() {
                this.anchor.value = "Why is overdue high?";
                this.anchor.dispatchEvent(new InputEvent("input", {bubbles: true}));
            },
        },
        {
            content: "Send the question",
            trigger: ".o_boardkit_dashboard_ai_composer .btn-primary:not([disabled])",
            run: "click",
        },
        {
            content: "The user question is shown",
            trigger:
                ".o_boardkit_dashboard_ai_message_user:contains(Why is overdue high?)",
        },
        {
            content: "The mocked assistant answer is shown",
            trigger: ".o_boardkit_dashboard_ai_message_assistant:contains(Mock answer)",
        },
        {
            content: "Close the panel without clearing the thread",
            trigger: ".o_boardkit_dashboard_ai_panel button[title='Close']",
            run: "click",
        },
        {
            content: "The panel is closed",
            trigger: ".o_boardkit_dashboard:not(:has(.o_boardkit_dashboard_ai_panel))",
        },
        {
            content: "Reopen the board chat",
            trigger: ".o_boardkit_dashboard_topbar_actions button:contains(Ask AI)",
            run: "click",
        },
        {
            content: "The previous question is still there",
            trigger:
                ".o_boardkit_dashboard_ai_message_user:contains(Why is overdue high?)",
        },
        {
            content: "Clear the conversation",
            trigger:
                ".o_boardkit_dashboard_ai_panel button[title='Clear conversation']",
            run: "click",
        },
        {
            content: "The thread is empty again",
            trigger:
                ".o_boardkit_dashboard_ai_panel_body:not(:has(.o_boardkit_dashboard_ai_message))",
        },
    ],
});
