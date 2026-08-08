// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {BoardkitDashboardAction} from "@boardkit_dashboard/dashboard/dashboard_action";
import {_t} from "@web/core/l10n/translation";
import {browser} from "@web/core/browser/browser";
import {markup, useEffect} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";

let aiMessageSeq = 0;

function nextAiMessageId() {
    aiMessageSeq += 1;
    return `ai-msg-${aiMessageSeq}`;
}

patch(BoardkitDashboardAction.prototype, {
    setup() {
        super.setup(...arguments);
        Object.assign(this.state, {
            aiPanelOpen: false,
            aiLoading: false,
            aiTitle: _t("Board chat"),
            aiMessages: [],
            aiDraft: "",
            aiContextUpdated: false,
        });
        useEffect(
            () => {
                if (this.state.aiPanelOpen && this.state.aiMessages.length) {
                    this.state.aiContextUpdated = true;
                }
            },
            () => [this.state.filterStamp]
        );
    },

    get canCopyAiBody() {
        return Boolean(!this.state.aiLoading && this.state.aiMessages.length);
    },

    get canSendAiChat() {
        return Boolean(
            this.state.board?.ai_enabled &&
                !this.state.aiLoading &&
                (this.state.aiDraft || "").trim()
        );
    },

    _aiHtmlToPlainText(html) {
        const container = document.createElement("div");
        container.innerHTML = html || "";
        const text = container.innerText || container.textContent || "";
        return text.replace(/\n{3,}/g, "\n\n").trim();
    },

    _appendAiMessage(role, content, {html = false} = {}) {
        const text = (content || "").trim();
        const message = {
            id: nextAiMessageId(),
            role,
            text,
            html: html ? markup(text) : markup(""),
            isHtml: Boolean(html),
        };
        this.state.aiMessages = [...this.state.aiMessages, message];
        return message;
    },

    _buildAiHistoryPayload() {
        return this.state.aiMessages.slice(-10).map((message) => ({
            role: message.role,
            content: message.isHtml
                ? this._aiHtmlToPlainText(message.text)
                : message.text,
        }));
    },

    openAiChat() {
        if (!this.state.board?.id || !this.state.board.ai_enabled) {
            return;
        }
        this.state.aiPanelOpen = true;
        this.state.aiTitle = _t("Board chat");
        this.state.aiContextUpdated = false;
    },

    closeAiPanel() {
        this.state.aiPanelOpen = false;
        this.state.aiLoading = false;
        this.state.aiTitle = _t("Board chat");
        this.state.aiMessages = [];
        this.state.aiDraft = "";
        this.state.aiContextUpdated = false;
    },

    onAiDraftKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendAiChatMessage();
        }
    },

    _aiMessagePlainText(message) {
        if (!message) {
            return "";
        }
        return message.isHtml
            ? this._aiHtmlToPlainText(message.text)
            : (message.text || "").trim();
    },

    async _copyTextToClipboard(text) {
        const value = (text || "").trim();
        if (!value) {
            return;
        }
        try {
            await browser.navigator.clipboard.writeText(value);
            this.notification.add(_t("Copied to clipboard."), {type: "success"});
        } catch {
            this.notification.add(_t("Could not copy to the clipboard."), {
                type: "danger",
            });
        }
    },

    async copyAiMessage(message) {
        await this._copyTextToClipboard(this._aiMessagePlainText(message));
    },

    async copyAiBody() {
        if (!this.canCopyAiBody) {
            return;
        }
        const parts = this.state.aiMessages.map((message) => {
            const label = message.role === "user" ? _t("You") : _t("AI");
            return `${label}:\n${this._aiMessagePlainText(message)}`;
        });
        await this._copyTextToClipboard(parts.join("\n\n"));
    },

    async _applyAiChatActions(actions) {
        if (!Array.isArray(actions) || !actions.length || !this.state.board) {
            return;
        }
        let filtersApplied = false;
        for (const action of actions) {
            if (action?.type !== "apply_filters" || !action.filters) {
                continue;
            }
            this.applyFilterState(action.filters, this.state.board);
            filtersApplied = true;
        }
        if (!filtersApplied) {
            return;
        }
        // Reload cards without persisting personal saved filters from AI.
        this.state.filterStamp += 1;
        this.state.aiContextUpdated = false;
        await this.loadItemsData();
        this.notification.add(_t("Dashboard filters updated."), {type: "info"});
    },

    async sendAiChatMessage() {
        if (!this.canSendAiChat || !this.state.board?.id) {
            return;
        }
        const question = this.state.aiDraft.trim();
        this.state.aiDraft = "";
        this.state.aiPanelOpen = true;
        this.state.aiTitle = _t("Board chat");
        this.state.aiContextUpdated = false;
        this._appendAiMessage("user", question);
        this.state.aiLoading = true;
        try {
            const history = this._buildAiHistoryPayload().slice(0, -1);
            const result = await this.orm.call(
                "boardkit.dashboard",
                "action_ai_chat",
                [[this.state.board.id], this.buildParams(), question, history]
            );
            await this._applyAiChatActions(result?.actions);
            this._appendAiMessage(
                "assistant",
                result?.body || _t("No response was returned."),
                {html: true}
            );
        } catch (error) {
            this.notification.add(
                error.data?.message || error.message || _t("AI request failed."),
                {type: "danger"}
            );
        } finally {
            this.state.aiLoading = false;
        }
    },

    async summarizeWithAi() {
        if (!this.state.board?.id || !this.state.board.ai_enabled || this.state.aiLoading) {
            return;
        }
        this.state.aiPanelOpen = true;
        this.state.aiTitle = _t("Board chat");
        this.state.aiContextUpdated = false;
        this.state.aiLoading = true;
        try {
            const result = await this.orm.call(
                "boardkit.dashboard",
                "action_ai_summarize",
                [[this.state.board.id], this.buildParams()]
            );
            this._appendAiMessage(
                "assistant",
                result?.body || _t("No summary was returned."),
                {html: true}
            );
        } catch (error) {
            this.notification.add(
                error.data?.message || error.message || _t("AI request failed."),
                {type: "danger"}
            );
        } finally {
            this.state.aiLoading = false;
        }
    },

    async explainItemWithAi(itemId) {
        if (!this.state.board?.id || !this.state.board.ai_enabled || this.state.aiLoading) {
            return;
        }
        const item = (this.state.board.items || []).find((entry) => entry.id === itemId);
        this.state.aiPanelOpen = true;
        this.state.aiTitle = _t("Board chat");
        this.state.aiContextUpdated = false;
        if (item?.name) {
            this._appendAiMessage("user", _t("Explain: %s", item.name));
        }
        this.state.aiLoading = true;
        try {
            const result = await this.orm.call(
                "boardkit.dashboard",
                "action_ai_explain_item",
                [[this.state.board.id], itemId, this.buildParams()]
            );
            this._appendAiMessage(
                "assistant",
                result?.body || _t("No explanation was returned."),
                {html: true}
            );
        } catch (error) {
            this.notification.add(
                error.data?.message || error.message || _t("AI request failed."),
                {type: "danger"}
            );
        } finally {
            this.state.aiLoading = false;
        }
    },
});
