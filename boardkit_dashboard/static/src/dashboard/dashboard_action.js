// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {
    Component,
    onWillStart,
    onWillUnmount,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import {deserializeDateTime, serializeDateTime} from "@web/core/l10n/dates";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {CustomFilters} from "./custom_filters";
import {DashboardItemCard} from "./dashboard_item_card";
import {DateFilter} from "./date_filter";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {_t} from "@web/core/l10n/translation";
import {browser} from "@web/core/browser/browser";
import {defaultItemSize} from "./utils";
import {registry} from "@web/core/registry";
import {router} from "@web/core/browser/router";
import {useDebounced} from "@web/core/utils/timing";
import {useService} from "@web/core/utils/hooks";

const GRID_COLS = 12;
const GRID_ROW_HEIGHT = 56;
const GRID_GAP = 12;
// Matches Odoo ui.isSmall / Bootstrap md breakpoint.
const MOBILE_MAX_WIDTH = 767.98;
const FULLSCREEN_BODY_CLASS = "o_boardkit_dashboard_fullscreen";
// URL parameter carrying the filter state of a shared link.
const FILTER_URL_KEY = "esc_filters";
const FILTER_SAVE_DELAY = 1000;

function clamp(value, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, value));
}

function intersects(a, b) {
    return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}

export class BoardkitDashboardAction extends Component {
    static template = "boardkit_dashboard.DashboardAction";
    static components = {
        CustomFilters,
        DashboardItemCard,
        DateFilter,
        Dropdown,
        DropdownItem,
    };
    static props = {"*": true};

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.gridRef = useRef("grid");
        this.refreshTimer = null;
        this.loadToken = 0;
        this.drag = null;
        this.savedLayout = null;
        this.onDragPointerMove = this.onDragPointerMove.bind(this);
        this.onDragPointerUp = this.onDragPointerUp.bind(this);
        this.state = useState({
            loading: true,
            missing: false,
            board: null,
            itemData: {},
            layout: {},
            editMode: false,
            dateFilter: {preset: "none", from: false, to: false},
            activeFilterIds: [],
            customFilters: [],
            // Bumped when filters change so item cards can reset drill stacks
            // without reacting to every auto-refresh payload replacement.
            filterStamp: 0,
            hasSavedFilters: false,
            isFullscreen: false,
        });
        this.sharedFilterState = this.readSharedFilterState();
        this.saveFiltersDebounced = useDebounced(
            () => this.savePersonalFilters(),
            FILTER_SAVE_DELAY,
            {execBeforeUnmount: true}
        );
        useExternalListener(browser, "fullscreenchange", this.onFullscreenChange);
        onWillStart(() => this.loadDashboard());
        onWillUnmount(() => {
            this.clearAutoRefresh();
            this.unbindDragListeners();
            // Leaving the action (e.g. drilldown) must restore the Odoo navbar.
            this.exitFullscreen();
        });
    }

    // ------------------------------------------------------------------
    // Full screen (TV / kiosk mode)
    // ------------------------------------------------------------------

    get isFullscreenAvailable() {
        return Boolean(document.fullscreenEnabled || document.webkitFullscreenEnabled);
    }

    async toggleFullscreen() {
        if (this.state.isFullscreen) {
            await this.exitFullscreen();
        } else {
            await this.enterFullscreen();
        }
    }

    async enterFullscreen() {
        const el = document.body;
        try {
            if (el.requestFullscreen) {
                await el.requestFullscreen();
            } else if (el.mozRequestFullScreen) {
                await el.mozRequestFullScreen();
            } else if (el.webkitRequestFullscreen) {
                await el.webkitRequestFullscreen();
            }
        } catch {
            this.state.isFullscreen = false;
            document.body.classList.remove(FULLSCREEN_BODY_CLASS);
            this.notification.add(_t("The Fullscreen mode was denied by the browser"), {
                type: "warning",
            });
        }
    }

    async exitFullscreen() {
        const fullscreenElement =
            document.webkitFullscreenElement || document.fullscreenElement;
        if (fullscreenElement) {
            try {
                if (document.exitFullscreen) {
                    await document.exitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    await document.mozCancelFullScreen();
                } else if (document.webkitCancelFullScreen) {
                    await document.webkitCancelFullScreen();
                }
            } catch {
                // Browser may already have left fullscreen (ESC, navigation).
            }
        }
        this.state.isFullscreen = false;
        document.body.classList.remove(FULLSCREEN_BODY_CLASS);
    }

    onFullscreenChange() {
        const isFullscreen = Boolean(
            document.webkitFullscreenElement || document.fullscreenElement
        );
        this.state.isFullscreen = isFullscreen;
        document.body.classList.toggle(FULLSCREEN_BODY_CLASS, isFullscreen);
    }

    // ------------------------------------------------------------------
    // Favorites
    // ------------------------------------------------------------------

    async toggleFavorite() {
        if (!this.state.board?.id) {
            return;
        }
        const isFavorite = await this.orm.call(
            "boardkit.dashboard",
            "toggle_favorite",
            [[this.state.board.id]]
        );
        this.state.board.is_favorite = Boolean(isFavorite);
    }

    // ------------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------------

    async loadDashboard() {
        this.state.loading = true;
        let dashboardId = this.props.action?.params?.dashboard_id;
        if (!dashboardId) {
            const ids = await this.orm.search("boardkit.dashboard", [], {limit: 1});
            dashboardId = ids[0];
        }
        if (!dashboardId) {
            this.state.missing = true;
            this.state.loading = false;
            return;
        }
        const board = await this.orm.call("boardkit.dashboard", "get_dashboard_data", [
            dashboardId,
        ]);
        if (!board) {
            // Inaccessible in the current company/group context (or deleted).
            this.state.missing = true;
            this.state.board = null;
            this.state.loading = false;
            return;
        }
        this.state.missing = false;
        this.state.board = board;
        this.state.dateFilter = {
            preset: board.date_filter || "none",
            from: board.date_from ? deserializeDateTime(board.date_from) : false,
            to: board.date_to ? deserializeDateTime(board.date_to) : false,
        };
        this.state.activeFilterIds = board.filters
            .filter((boardFilter) => boardFilter.default_enabled)
            .map((boardFilter) => boardFilter.id);
        this.state.customFilters = [];
        this.state.hasSavedFilters = Boolean(board.has_saved_filters);
        this.restoreFilters(board);
        this.state.layout = this.normalizeLayout(board.layout, board.items);
        this.state.editMode = false;
        this.state.loading = false;
        this.loadItemsData();
        this.setupAutoRefresh();
    }

    async reloadDashboard() {
        this.clearAutoRefresh();
        this.state.itemData = {};
        await this.loadDashboard();
    }

    buildParams() {
        const {preset, from, to} = this.state.dateFilter;
        const params = {
            date_preset: preset,
            filter_ids: [...this.state.activeFilterIds],
        };
        if (preset === "custom" && from && to) {
            params.date_from = serializeDateTime(from.startOf("day"));
            params.date_to = serializeDateTime(to.endOf("day"));
        }
        if (this.state.customFilters.length) {
            params.custom_filters = this.state.customFilters.map(
                ({model, field, operator, value}) => ({model, field, operator, value})
            );
        }
        return params;
    }

    async loadItemsData() {
        const board = this.state.board;
        if (!board || !board.items.length) {
            return;
        }
        const itemIds = board.items.map((item) => item.id);
        // Keep previous payloads visible while fetching so auto-refresh and
        // filter changes do not flash empty cards or reset open drill stacks.
        const token = ++this.loadToken;
        const data = await this.orm.call("boardkit.dashboard.item", "get_items_data", [
            itemIds,
            this.buildParams(),
        ]);
        if (token !== this.loadToken) {
            return;
        }
        this.state.itemData = data;
    }

    async reloadItem(itemId, extraParams = {}) {
        const params = {...this.buildParams(), ...extraParams};
        const payload = await this.orm.call("boardkit.dashboard.item", "get_data", [
            [itemId],
            params,
        ]);
        this.state.itemData = {...this.state.itemData, [itemId]: payload};
    }

    setupAutoRefresh() {
        this.clearAutoRefresh();
        const interval = this.state.board?.refresh_interval || 0;
        if (interval > 0) {
            this.refreshTimer = browser.setInterval(
                () => this.loadItemsData(),
                interval * 1000
            );
        }
    }

    clearAutoRefresh() {
        if (this.refreshTimer) {
            browser.clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    // ------------------------------------------------------------------
    // Filters
    // ------------------------------------------------------------------

    readSharedFilterState() {
        const raw = router.current[FILTER_URL_KEY];
        if (!raw || typeof raw !== "string") {
            return null;
        }
        try {
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === "object" && !Array.isArray(parsed)
                ? parsed
                : null;
        } catch {
            return null;
        }
    }

    serializeFilterState() {
        const {preset, from, to} = this.state.dateFilter;
        const state = {
            date_preset: preset,
            filter_ids: [...this.state.activeFilterIds],
            custom_filters: this.state.customFilters.map(
                ({model, field, operator, value, label, modelLabel}) => ({
                    model,
                    field,
                    operator,
                    value,
                    label,
                    modelLabel,
                })
            ),
        };
        if (preset === "custom" && from && to) {
            state.date_from = serializeDateTime(from.startOf("day"));
            state.date_to = serializeDateTime(to.endOf("day"));
        }
        return state;
    }

    applyFilterState(source, board) {
        if (!source || typeof source !== "object") {
            return;
        }
        const knownIds = new Set((board.filters || []).map((entry) => entry.id));
        if (typeof source.date_preset === "string") {
            this.state.dateFilter = {
                preset: source.date_preset,
                from:
                    source.date_preset === "custom" && source.date_from
                        ? deserializeDateTime(source.date_from)
                        : false,
                to:
                    source.date_preset === "custom" && source.date_to
                        ? deserializeDateTime(source.date_to)
                        : false,
            };
        }
        if (Array.isArray(source.filter_ids)) {
            this.state.activeFilterIds = source.filter_ids.filter((filterId) =>
                knownIds.has(filterId)
            );
        }
        if (Array.isArray(source.custom_filters)) {
            this.state.customFilters = source.custom_filters
                .filter(
                    (entry) =>
                        entry &&
                        typeof entry === "object" &&
                        entry.model &&
                        entry.field &&
                        entry.operator
                )
                .map((entry) => ({
                    model: entry.model,
                    field: entry.field,
                    operator: entry.operator,
                    value: entry.value,
                    label: entry.label || entry.field,
                    modelLabel: entry.modelLabel || entry.model,
                }));
        }
    }

    restoreFilters(board) {
        // Shared links win over the personal remembered state.
        const source = this.sharedFilterState || board.saved_filters;
        if (!source || !Object.keys(source).length) {
            return;
        }
        this.applyFilterState(source, board);
    }

    onFiltersChanged() {
        // The stamp lets item cards drop their drill stack without reacting
        // to every auto-refresh payload.
        this.state.filterStamp += 1;
        this.loadItemsData();
        this.saveFiltersDebounced();
    }

    onDateFilterChanged(value) {
        this.state.dateFilter = {preset: value.preset, from: value.from, to: value.to};
        if (value.apply) {
            this.onFiltersChanged();
        }
    }

    isFilterActive(filterId) {
        return this.state.activeFilterIds.includes(filterId);
    }

    toggleFilter(filterId) {
        if (this.isFilterActive(filterId)) {
            this.state.activeFilterIds = this.state.activeFilterIds.filter(
                (activeId) => activeId !== filterId
            );
        } else {
            this.state.activeFilterIds = [...this.state.activeFilterIds, filterId];
        }
        this.onFiltersChanged();
    }

    get filterableModels() {
        const seen = new Map();
        for (const item of this.state.board?.items || []) {
            if (item.model && !seen.has(item.model)) {
                seen.set(item.model, {model: item.model, label: item.model_label});
            }
        }
        return [...seen.values()];
    }

    addCustomFilter(spec) {
        this.state.customFilters = [...this.state.customFilters, spec];
        this.onFiltersChanged();
    }

    removeCustomFilter(index) {
        const filters = [...this.state.customFilters];
        filters.splice(index, 1);
        this.state.customFilters = filters;
        this.onFiltersChanged();
    }

    async savePersonalFilters() {
        if (!this.state.board?.id) {
            return;
        }
        await this.orm.call("boardkit.dashboard", "save_filters", [
            this.state.board.id,
            this.serializeFilterState(),
        ]);
        this.state.hasSavedFilters = true;
        if (this.state.board) {
            this.state.board.has_saved_filters = true;
        }
    }

    async resetPersonalFilters() {
        if (!this.state.board?.id) {
            return;
        }
        await this.orm.call("boardkit.dashboard", "reset_personal_filters", [
            this.state.board.id,
        ]);
        this.state.hasSavedFilters = false;
        this.state.board.has_saved_filters = false;
        this.state.dateFilter = {
            preset: this.state.board.date_filter || "none",
            from: this.state.board.date_from
                ? deserializeDateTime(this.state.board.date_from)
                : false,
            to: this.state.board.date_to
                ? deserializeDateTime(this.state.board.date_to)
                : false,
        };
        this.state.activeFilterIds = this.state.board.filters
            .filter((boardFilter) => boardFilter.default_enabled)
            .map((boardFilter) => boardFilter.id);
        this.state.customFilters = [];
        this.state.filterStamp += 1;
        this.loadItemsData();
    }

    async copyShareLink() {
        const href =
            browser.location.origin +
            router.stateToUrl({
                ...router.current,
                [FILTER_URL_KEY]: JSON.stringify(this.serializeFilterState()),
            });
        try {
            await browser.navigator.clipboard.writeText(href);
            this.notification.add(_t("Link copied to clipboard."), {type: "success"});
        } catch {
            this.notification.add(_t("Could not copy the link to the clipboard."), {
                type: "warning",
            });
        }
    }

    // ------------------------------------------------------------------
    // Grid layout
    // ------------------------------------------------------------------

    normalizeLayout(layout, items) {
        const result = {};
        let maxY = 0;
        for (const item of items) {
            const geometry = layout[String(item.id)];
            if (
                geometry &&
                Number.isInteger(geometry.x) &&
                Number.isInteger(geometry.y) &&
                Number.isInteger(geometry.w) &&
                Number.isInteger(geometry.h)
            ) {
                const width = clamp(geometry.w, 2, GRID_COLS);
                const normalized = {
                    x: clamp(geometry.x, 0, GRID_COLS - width),
                    y: Math.max(0, geometry.y),
                    w: width,
                    h: Math.max(2, geometry.h),
                };
                result[String(item.id)] = normalized;
                maxY = Math.max(maxY, normalized.y + normalized.h);
            }
        }
        let cursorX = 0;
        let cursorY = maxY;
        let rowHeight = 0;
        for (const item of items) {
            const key = String(item.id);
            if (result[key]) {
                continue;
            }
            const size = defaultItemSize(item.type);
            if (cursorX + size.w > GRID_COLS) {
                cursorX = 0;
                cursorY += rowHeight;
                rowHeight = 0;
            }
            result[key] = {x: cursorX, y: cursorY, w: size.w, h: size.h};
            cursorX += size.w;
            rowHeight = Math.max(rowHeight, size.h);
        }
        return result;
    }

    getItemStyle(itemId) {
        const geometry = this.state.layout[String(itemId)];
        if (!geometry) {
            return "";
        }
        // Order is ignored on desktop (explicit placement) and drives the
        // reading order when the grid collapses to one column on mobile.
        const readingOrder = geometry.y * (GRID_COLS + 1) + geometry.x;
        return (
            `grid-column: ${geometry.x + 1} / span ${geometry.w};` +
            `grid-row: ${geometry.y + 1} / span ${geometry.h};` +
            `order: ${readingOrder};` +
            `--esc-mobile-h: ${geometry.h};`
        );
    }

    get isMobileViewport() {
        return browser.innerWidth <= MOBILE_MAX_WIDTH;
    }

    onItemPointerDown(event, itemId, mode) {
        if (!this.state.editMode || event.button !== 0 || this.isMobileViewport) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        const rect = this.gridRef.el.getBoundingClientRect();
        this.drag = {
            itemId: String(itemId),
            mode,
            startX: event.clientX,
            startY: event.clientY,
            orig: {...this.state.layout[String(itemId)]},
            stepX: (rect.width + GRID_GAP) / GRID_COLS,
        };
        window.addEventListener("pointermove", this.onDragPointerMove);
        window.addEventListener("pointerup", this.onDragPointerUp);
    }

    onDragPointerMove(event) {
        const drag = this.drag;
        if (!drag) {
            return;
        }
        const deltaX = Math.round((event.clientX - drag.startX) / drag.stepX);
        const deltaY = Math.round(
            (event.clientY - drag.startY) / (GRID_ROW_HEIGHT + GRID_GAP)
        );
        const geometry = {...drag.orig};
        if (drag.mode === "move") {
            geometry.x = clamp(drag.orig.x + deltaX, 0, GRID_COLS - geometry.w);
            geometry.y = Math.max(0, drag.orig.y + deltaY);
        } else {
            geometry.w = clamp(drag.orig.w + deltaX, 2, GRID_COLS - geometry.x);
            geometry.h = Math.max(2, drag.orig.h + deltaY);
        }
        this.state.layout = {...this.state.layout, [drag.itemId]: geometry};
    }

    onDragPointerUp() {
        if (this.drag) {
            this.resolveCollisions(this.drag.itemId);
        }
        this.unbindDragListeners();
        this.drag = null;
    }

    unbindDragListeners() {
        window.removeEventListener("pointermove", this.onDragPointerMove);
        window.removeEventListener("pointerup", this.onDragPointerUp);
    }

    resolveCollisions(movedId) {
        const layout = {...this.state.layout};
        const moved = layout[movedId];
        const otherIds = Object.keys(layout)
            .filter((key) => key !== movedId)
            .sort((a, b) => layout[a].y - layout[b].y || layout[a].x - layout[b].x);
        let changed = true;
        let guard = 0;
        while (changed && guard < 100) {
            changed = false;
            guard += 1;
            for (const key of otherIds) {
                const geometry = layout[key];
                const obstacles = [
                    moved,
                    ...otherIds
                        .filter((other) => other !== key)
                        .map((other) => layout[other]),
                ];
                for (const obstacle of obstacles) {
                    if (obstacle !== geometry && intersects(geometry, obstacle)) {
                        layout[key] = {...geometry, y: obstacle.y + obstacle.h};
                        changed = true;
                        break;
                    }
                }
                if (changed) {
                    break;
                }
            }
        }
        this.state.layout = layout;
    }

    // ------------------------------------------------------------------
    // Edit mode
    // ------------------------------------------------------------------

    enterEditMode() {
        this.savedLayout = JSON.parse(JSON.stringify(this.state.layout));
        this.state.editMode = true;
    }

    cancelEditMode() {
        if (this.savedLayout) {
            this.state.layout = this.savedLayout;
        }
        this.state.editMode = false;
    }

    async saveLayout(personal) {
        await this.orm.call("boardkit.dashboard", "save_layout", [
            this.state.board.id,
            this.state.layout,
            personal,
        ]);
        if (personal) {
            this.state.board.has_personal_layout = true;
        }
        this.state.editMode = false;
        this.notification.add(_t("Dashboard layout saved."), {type: "success"});
    }

    async resetPersonalLayout() {
        await this.orm.call("boardkit.dashboard", "reset_personal_layout", [
            this.state.board.id,
        ]);
        await this.reloadDashboard();
    }

    // ------------------------------------------------------------------
    // Item actions
    // ------------------------------------------------------------------

    addItem() {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("New Dashboard Item"),
                res_model: "boardkit.dashboard.item",
                views: [[false, "form"]],
                target: "new",
                context: {default_dashboard_id: this.state.board.id},
            },
            {onClose: () => this.reloadDashboard()}
        );
    }

    editItem(item) {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: item.name,
                res_model: "boardkit.dashboard.item",
                res_id: item.id,
                views: [[false, "form"]],
                target: "new",
            },
            {onClose: () => this.reloadDashboard()}
        );
    }

    async duplicateItem(item) {
        await this.orm.call("boardkit.dashboard.item", "copy", [[item.id]]);
        await this.reloadDashboard();
    }

    deleteItem(item) {
        this.dialogService.add(ConfirmationDialog, {
            title: _t("Delete Dashboard Item"),
            body: _t('Are you sure you want to delete "%s"?', item.name),
            confirmLabel: _t("Delete"),
            confirm: async () => {
                await this.orm.unlink("boardkit.dashboard.item", [item.id]);
                await this.reloadDashboard();
            },
            cancel: () => {
                // Nothing to do
            },
        });
    }

    async openDrilldown(item, domain, actionName) {
        const action = await this.orm.call(
            "boardkit.dashboard.item",
            "get_drilldown_action",
            [[item.id], domain, actionName]
        );
        this.actionService.doAction(action);
    }

    async fetchDrillData(item, level, domain) {
        return this.orm.call("boardkit.dashboard.item", "get_drill_data", [
            [item.id],
            level.id,
            domain,
        ]);
    }

    openRecord(item, resId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: item.model,
            res_id: resId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    exportDashboard() {
        window.open(`/boardkit_dashboard/export/${this.state.board.id}`, "_blank");
    }

    exportItem(item, format) {
        const params = encodeURIComponent(JSON.stringify(this.buildParams()));
        window.open(
            `/boardkit_dashboard/item/${item.id}/export/${format}?params=${params}`,
            "_blank"
        );
    }

    openConfiguration() {
        if (!this.state.board?.id) {
            // Empty state: open the dashboards list to create one.
            this.actionService.doAction("boardkit_dashboard.boardkit_dashboard_action");
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this.state.board.name,
            res_model: "boardkit.dashboard",
            res_id: this.state.board.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("boardkit_dashboard", BoardkitDashboardAction);
