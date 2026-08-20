// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {describe, expect, test} from "@odoo/hoot";
import {contains, mountWithCleanup, onRpc} from "@web/../tests/web_test_helpers";
import {BoardkitDashboardAction} from "@boardkit_dashboard/dashboard/dashboard_action";
import {animationFrame} from "@odoo/hoot-mock";

describe.current.tags("desktop");

function makeBoard(overrides = {}) {
    return {
        id: 1,
        name: "AI Test Board",
        is_favorite: false,
        is_manager: true,
        published: true,
        refresh_interval: 0,
        date_filter: "none",
        date_from: false,
        date_to: false,
        date_presets: [
            ["none", "None"],
            ["this_month", "This month"],
        ],
        layout: {},
        has_personal_layout: false,
        saved_filters: {},
        has_saved_filters: false,
        currency: {symbol: "$", position: "before"},
        items: [],
        filters: [],
        ai_enabled: true,
        ...overrides,
    };
}

function mockDashboardRpcs(chatHandler) {
    onRpc("boardkit.dashboard", "get_dashboard_data", () => makeBoard());
    onRpc("boardkit.dashboard", "save_filters", () => true);
    onRpc("boardkit.dashboard", "action_ai_chat", ({args}) => {
        if (chatHandler) {
            return chatHandler(args);
        }
        return {
            body: "<p>Mock answer</p>",
            body_is_html: true,
            actions: [],
        };
    });
}

async function mountBoard() {
    return mountWithCleanup(BoardkitDashboardAction, {
        props: {
            action: {params: {dashboard_id: 1}},
        },
    });
}

test("Ask AI opens the panel and focuses the composer", async () => {
    mockDashboardRpcs();
    const action = await mountBoard();
    expect(".o_boardkit_dashboard_ai_panel").toHaveCount(0);

    await contains("button:contains(Ask AI)").click();
    expect(".o_boardkit_dashboard_ai_panel").toHaveCount(1);
    expect(".o_boardkit_dashboard_ai_panel").toHaveAttribute(
        "aria-label",
        "Board chat"
    );
    expect(document.activeElement).toBe(action.aiDraftInputRef.el);
});

test("closing the panel keeps the conversation until it is cleared", async () => {
    mockDashboardRpcs();
    await mountBoard();
    await contains("button:contains(Ask AI)").click();
    await contains(".o_boardkit_dashboard_ai_input").edit("Why is overdue high?", {
        confirm: false,
    });
    await contains(".o_boardkit_dashboard_ai_composer .btn-primary").click();
    await animationFrame();

    expect(
        ".o_boardkit_dashboard_ai_message_user .o_boardkit_dashboard_ai_content"
    ).toHaveText("Why is overdue high?");
    expect(
        ".o_boardkit_dashboard_ai_message_assistant .o_boardkit_dashboard_ai_content"
    ).toHaveText("Mock answer");

    await contains(".o_boardkit_dashboard_ai_panel button[title='Close']").click();
    expect(".o_boardkit_dashboard_ai_panel").toHaveCount(0);

    await contains("button:contains(Ask AI)").click();
    expect(
        ".o_boardkit_dashboard_ai_message_user .o_boardkit_dashboard_ai_content"
    ).toHaveText("Why is overdue high?");

    await contains(
        ".o_boardkit_dashboard_ai_panel button[title='Clear conversation']"
    ).click();
    expect(".o_boardkit_dashboard_ai_message").toHaveCount(0);
});

test("chat RPC receives the last 10 prior turns", async () => {
    let history = null;
    mockDashboardRpcs((args) => {
        history = args[3];
        return {
            body: "<p>Current answer</p>",
            body_is_html: true,
            actions: [],
        };
    });
    const action = await mountBoard();
    for (let index = 0; index < 6; index++) {
        action._appendAiMessage("user", `Q${index}`);
        action._appendAiMessage("assistant", `A${index}`);
    }
    await contains("button:contains(Ask AI)").click();
    await contains(".o_boardkit_dashboard_ai_input").edit("Current question", {
        confirm: false,
    });
    await contains(".o_boardkit_dashboard_ai_composer .btn-primary").click();
    await animationFrame();

    expect(history).toHaveLength(10);
    expect(history[0]).toEqual({role: "user", content: "Q1"});
    expect(history[9]).toEqual({role: "assistant", content: "A5"});
});

test("the chat body auto-scrolls to the latest message", async () => {
    mockDashboardRpcs();
    const action = await mountBoard();
    action.openAiChat();
    await animationFrame();

    const body = action.aiPanelBodyRef.el;
    body.style.maxHeight = "96px";
    for (let index = 0; index < 12; index++) {
        action._appendAiMessage("assistant", `Answer ${index}`);
    }
    await animationFrame();

    expect(body.scrollTop).toBeGreaterThan(0);
    expect(body.scrollHeight - body.clientHeight - body.scrollTop).toBeLessThan(2);
});
