/** @odoo-module **/
// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {
    click,
    editInput,
    getFixture,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import {createWebClient, doAction} from "@web/../tests/webclient/helpers";
import {BoardkitDashboardAction} from "@boardkit_dashboard/dashboard/dashboard_action";

let target = null;
let action = null;

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
    return (route, args) => {
        if (args.model !== "boardkit.dashboard") {
            return;
        }
        if (args.method === "get_dashboard_data") {
            return makeBoard();
        }
        if (args.method === "save_filters") {
            return true;
        }
        if (args.method === "action_ai_chat") {
            if (chatHandler) {
                return chatHandler(args.args);
            }
            return {
                body: "<p>Mock answer</p>",
                body_is_html: true,
                actions: [],
            };
        }
    };
}

async function mountBoard(chatHandler) {
    const webClient = await createWebClient({mockRPC: mockDashboardRpcs(chatHandler)});
    await doAction(webClient, {
        type: "ir.actions.client",
        tag: "boardkit_dashboard",
        params: {dashboard_id: 1},
    });
    return action;
}

function askAiButton() {
    return [
        ...target.querySelectorAll(".o_boardkit_dashboard_topbar_actions button"),
    ].find((button) => button.textContent.includes("Ask AI"));
}

function messageText(selector) {
    return target.querySelector(`${selector} .o_boardkit_dashboard_ai_content`)
        .textContent;
}

QUnit.module("boardkit_dashboard_ai_agno", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        action = null;
        // The web client owns the action; keep a handle on the component.
        patchWithCleanup(BoardkitDashboardAction.prototype, {
            setup() {
                this._super(...arguments);
                action = this;
            },
        });
    });

    QUnit.test("Ask AI opens the panel and focuses the composer", async (assert) => {
        await mountBoard();
        assert.containsNone(target, ".o_boardkit_dashboard_ai_panel");

        await click(askAiButton());
        assert.containsOnce(target, ".o_boardkit_dashboard_ai_panel");
        assert.strictEqual(
            target
                .querySelector(".o_boardkit_dashboard_ai_panel")
                .getAttribute("aria-label"),
            "Board chat"
        );
        assert.strictEqual(document.activeElement, action.aiDraftInputRef.el);
    });

    QUnit.test(
        "closing the panel keeps the conversation until it is cleared",
        async (assert) => {
            await mountBoard();
            await click(askAiButton());
            await editInput(
                target,
                ".o_boardkit_dashboard_ai_input",
                "Why is overdue high?"
            );
            await click(target, ".o_boardkit_dashboard_ai_composer .btn-primary");
            await nextTick();

            assert.strictEqual(
                messageText(".o_boardkit_dashboard_ai_message_user"),
                "Why is overdue high?"
            );
            assert.strictEqual(
                messageText(".o_boardkit_dashboard_ai_message_assistant"),
                "Mock answer"
            );

            await click(target, ".o_boardkit_dashboard_ai_panel button[title='Close']");
            assert.containsNone(target, ".o_boardkit_dashboard_ai_panel");

            await click(askAiButton());
            assert.strictEqual(
                messageText(".o_boardkit_dashboard_ai_message_user"),
                "Why is overdue high?"
            );

            await click(
                target,
                ".o_boardkit_dashboard_ai_panel button[title='Clear conversation']"
            );
            assert.containsNone(target, ".o_boardkit_dashboard_ai_message");
        }
    );

    QUnit.test("chat RPC receives the last 10 prior turns", async (assert) => {
        let history = null;
        await mountBoard((args) => {
            history = args[3];
            return {
                body: "<p>Current answer</p>",
                body_is_html: true,
                actions: [],
            };
        });
        for (let index = 0; index < 6; index++) {
            action._appendAiMessage("user", `Q${index}`);
            action._appendAiMessage("assistant", `A${index}`);
        }
        await click(askAiButton());
        await editInput(target, ".o_boardkit_dashboard_ai_input", "Current question");
        await click(target, ".o_boardkit_dashboard_ai_composer .btn-primary");
        await nextTick();

        assert.strictEqual(history.length, 10);
        assert.deepEqual(history[0], {role: "user", content: "Q1"});
        assert.deepEqual(history[9], {role: "assistant", content: "A5"});
    });

    QUnit.test("the chat body auto-scrolls to the latest message", async (assert) => {
        await mountBoard();
        action.openAiChat();
        await nextTick();

        const body = action.aiPanelBodyRef.el;
        body.style.maxHeight = "96px";
        for (let index = 0; index < 12; index++) {
            action._appendAiMessage("assistant", `Answer ${index}`);
        }
        await nextTick();

        assert.ok(body.scrollTop > 0);
        assert.ok(body.scrollHeight - body.clientHeight - body.scrollTop < 2);
    });
});
