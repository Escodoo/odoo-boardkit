// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {
    Component,
    onWillStart,
    onWillUnmount,
    useEffect,
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
import {useSetupAction} from "@web/search/action_hook";

const GRID_COLS = 12;
const GRID_ROW_HEIGHT = 56;
const GRID_GAP = 12;
// Auto-scroll while dragging: how close to the scroller edge the pointer must
// be to trigger it, and the top speed in pixels per animation frame.
const DRAG_SCROLL_EDGE = 48;
const DRAG_SCROLL_SPEED = 18;
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
        this.contentRef = useRef("content");
        this.refreshTimer = null;
        this.loadToken = 0;
        this.drag = null;
        this.dragScrollFrame = null;
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
            // Pixel box of the card that follows the pointer while moving.
            dragFloat: null,
            // Grid slot reserved for the drop, shown as a dashed placeholder.
            dragSlot: null,
        });
        this.sharedFilterState = this.readSharedFilterState();
        this.saveFiltersDebounced = useDebounced(
            () => this.savePersonalFilters(),
            FILTER_SAVE_DELAY,
            {execBeforeUnmount: true}
        );
        // Keep the open board across breadcrumb navigation.
        useSetupAction({
            getLocalState: () => ({
                dashboardId: this.state.board?.id,
            }),
        });
        // Persist dashboard_id in the URL so a full page reload reopens the
        // same board (same pattern as spreadsheet_dashboard).
        useEffect(
            () => {
                if (this.state.board?.id) {
                    router.pushState({dashboard_id: this.state.board.id});
                }
            },
            () => [this.state.board?.id]
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

    /**
     * Resolve which board to open: local action state, action/URL params,
     * then fall back to null (caller may search for a default).
     */
    resolveDashboardId() {
        if (this.props.state?.dashboardId) {
            return this.props.state.dashboardId;
        }
        const params = this.props.action?.params || this.props.action?.context?.params;
        const raw = params?.dashboard_id ?? router.current.dashboard_id;
        if (raw === undefined || raw === null || raw === "") {
            return null;
        }
        const id = Number(raw);
        return Number.isFinite(id) && id > 0 ? id : null;
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
    // Publish
    // ------------------------------------------------------------------

    async publishDashboard() {
        if (
            !this.state.board?.id ||
            this.state.board.published ||
            !this.state.board.is_manager
        ) {
            return;
        }
        await this.orm.call("boardkit.dashboard", "action_publish", [
            [this.state.board.id],
        ]);
        this.state.board.published = true;
        this.notification.add(_t("Dashboard published."), {type: "success"});
    }

    async unpublishDashboard() {
        if (
            !this.state.board?.id ||
            !this.state.board.published ||
            !this.state.board.is_manager
        ) {
            return;
        }
        await this.orm.call("boardkit.dashboard", "action_unpublish", [
            [this.state.board.id],
        ]);
        this.state.board.published = false;
        this.notification.add(_t("Dashboard unpublished."), {type: "info"});
    }

    async duplicateDashboard() {
        if (!this.state.board?.id || !this.state.board.is_manager) {
            return;
        }
        const newId = await this.orm.call("boardkit.dashboard", "copy", [
            [this.state.board.id],
        ]);
        this.notification.add(_t("Dashboard duplicated."), {type: "success"});
        await this.actionService.doAction({
            type: "ir.actions.client",
            tag: "boardkit_dashboard",
            name: _t("Dashboard"),
            params: {dashboard_id: newId},
        });
    }

    async deleteDashboard() {
        if (!this.state.board?.id || !this.state.board.is_manager) {
            return;
        }
        const boardId = this.state.board.id;
        const boardName = this.state.board.name;
        this.dialogService.add(ConfirmationDialog, {
            title: _t("Delete Dashboard"),
            body: _t('Are you sure you want to delete "%s"?', boardName),
            confirmLabel: _t("Delete"),
            confirm: async () => {
                await this.orm.unlink("boardkit.dashboard", [boardId]);
                this.notification.add(_t("Dashboard deleted."), {type: "success"});
                await this.actionService.doAction(
                    "boardkit_dashboard.boardkit_dashboard_action",
                    {clearBreadcrumbs: true}
                );
            },
        });
    }

    // ------------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------------

    async loadDashboard() {
        this.state.loading = true;
        let dashboardId = this.resolveDashboardId();
        if (!dashboardId) {
            // Landing / menu entry without a board id: open the first readable one.
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
        const float = this.state.dragFloat;
        if (float && float.id === String(itemId)) {
            // Keep the original pixel size so Chart.js does not rebuild the
            // canvas on every hop. The card is taken out of the grid flow.
            return (
                `position:fixed;` +
                `left:${float.left}px;` +
                `top:${float.top}px;` +
                `width:${float.width}px;` +
                `height:${float.height}px;` +
                `z-index:30;` +
                `margin:0;` +
                `grid-column:auto;` +
                `grid-row:auto;`
            );
        }
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

    getDragSlotStyle() {
        const slot = this.state.dragSlot;
        if (!slot) {
            return "";
        }
        return (
            `grid-column: ${slot.x + 1} / span ${slot.w};` +
            `grid-row: ${slot.y + 1} / span ${slot.h};`
        );
    }

    isDraggingItem(itemId) {
        return Boolean(
            this.state.dragFloat && this.state.dragFloat.id === String(itemId)
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
        const scrollTop = this.contentRef.el?.scrollTop || 0;
        const cell = event.currentTarget?.closest(".o_boardkit_dashboard_cell");
        const cellRect = cell?.getBoundingClientRect();
        this.drag = {
            itemId: String(itemId),
            mode,
            startX: event.clientX,
            startY: event.clientY,
            pointerX: event.clientX,
            pointerY: event.clientY,
            startScrollTop: scrollTop,
            lastScrollTop: scrollTop,
            blockedShift: 0,
            orig: {...this.state.layout[String(itemId)]},
            stepX: (rect.width + GRID_GAP) / GRID_COLS,
        };
        if (mode === "move" && cellRect) {
            this.drag.grabX = event.clientX - cellRect.left;
            this.drag.grabY = event.clientY - cellRect.top;
            this.state.dragFloat = {
                id: String(itemId),
                left: cellRect.left,
                top: cellRect.top,
                width: cellRect.width,
                height: cellRect.height,
            };
            this.state.dragSlot = {...this.drag.orig};
        }
        window.addEventListener("pointermove", this.onDragPointerMove);
        window.addEventListener("pointerup", this.onDragPointerUp);
        this.scheduleDragScroll();
    }

    onDragPointerMove(event) {
        if (!this.drag) {
            return;
        }
        this.drag.pointerX = event.clientX;
        this.drag.pointerY = event.clientY;
        this.applyDragGeometry();
    }

    /**
     * Place the dragged item from the last known pointer position, counting how
     * far the scroller travelled since the drag started: the pointer may stay
     * still while the auto-scroll brings the target row into view.
     */
    applyDragGeometry() {
        const drag = this.drag;
        if (!drag) {
            return;
        }
        const scrollDelta = (this.contentRef.el?.scrollTop || 0) - drag.startScrollTop;
        const deltaX = Math.round((drag.pointerX - drag.startX) / drag.stepX);
        const deltaY = Math.round(
            (drag.pointerY - drag.startY + scrollDelta) / (GRID_ROW_HEIGHT + GRID_GAP)
        );
        const geometry = {...drag.orig};
        if (drag.mode === "move") {
            geometry.x = clamp(drag.orig.x + deltaX, 0, GRID_COLS - geometry.w);
            geometry.y = Math.max(0, drag.orig.y + deltaY);
            // The live card follows the pointer; only the drop slot hops
            // through the grid. Relayouting the card itself would resize the
            // Chart.js canvas and clip funnels/maps mid-drag.
            if (this.state.dragFloat) {
                this.state.dragFloat = {
                    ...this.state.dragFloat,
                    left: drag.pointerX - drag.grabX,
                    top: drag.pointerY - drag.grabY,
                };
            }
            this.state.dragSlot = geometry;
        } else {
            geometry.w = clamp(drag.orig.w + deltaX, 2, GRID_COLS - geometry.x);
            geometry.h = Math.max(2, drag.orig.h + deltaY);
            this.state.layout = {...this.state.layout, [drag.itemId]: geometry};
        }
    }

    scheduleDragScroll() {
        this.dragScrollFrame = browser.requestAnimationFrame(() =>
            this.onDragScrollFrame()
        );
    }

    /**
     * Pixels to scroll on this frame, growing as the pointer gets closer to the
     * scroller edge. Negative scrolls up.
     */
    dragScrollSpeed(rect, pointerY) {
        const overTop = DRAG_SCROLL_EDGE - (pointerY - rect.top);
        if (overTop > 0) {
            return -DRAG_SCROLL_SPEED * clamp(overTop / DRAG_SCROLL_EDGE, 0, 1);
        }
        const overBottom = DRAG_SCROLL_EDGE - (rect.bottom - pointerY);
        if (overBottom > 0) {
            return DRAG_SCROLL_SPEED * clamp(overBottom / DRAG_SCROLL_EDGE, 0, 1);
        }
        return 0;
    }

    /**
     * Scroll the grid while the pointer rests near an edge, so an item can
     * travel further than the visible area without being dropped on the way.
     */
    onDragScrollFrame() {
        this.dragScrollFrame = null;
        const drag = this.drag;
        const scroller = this.contentRef.el;
        if (!drag || !scroller) {
            return;
        }
        const rect = scroller.getBoundingClientRect();
        const speed = this.dragScrollSpeed(rect, drag.pointerY);
        // Also catches wheel scrolling done in the middle of a drag.
        let moved = scroller.scrollTop !== drag.lastScrollTop;
        if (speed) {
            const before = scroller.scrollTop;
            scroller.scrollTop = before + speed;
            moved = moved || scroller.scrollTop !== before;
            // Downwards the grid has no rows left to reveal until the item
            // creates them, so move the grab reference instead. Capped to one
            // viewport to keep a held pointer from pushing the item away.
            const missed = speed - (scroller.scrollTop - before);
            if (missed > 0 && drag.blockedShift < rect.height) {
                const shift = Math.min(missed, rect.height - drag.blockedShift);
                drag.blockedShift += shift;
                drag.startY -= shift;
                moved = true;
            }
        }
        if (moved) {
            this.applyDragGeometry();
        }
        drag.lastScrollTop = scroller.scrollTop;
        this.scheduleDragScroll();
    }

    onDragPointerUp() {
        if (this.drag) {
            if (this.drag.mode === "move" && this.state.dragSlot) {
                this.state.layout = {
                    ...this.state.layout,
                    [this.drag.itemId]: this.state.dragSlot,
                };
            }
            this.resolveCollisions(this.drag.itemId);
        }
        this.state.dragFloat = null;
        this.state.dragSlot = null;
        this.unbindDragListeners();
        this.drag = null;
    }

    unbindDragListeners() {
        window.removeEventListener("pointermove", this.onDragPointerMove);
        window.removeEventListener("pointerup", this.onDragPointerUp);
        if (this.dragScrollFrame) {
            browser.cancelAnimationFrame(this.dragScrollFrame);
            this.dragScrollFrame = null;
        }
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
        this.state.dragFloat = null;
        this.state.dragSlot = null;
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

    openSettings() {
        if (!this.state.board?.id) {
            // Empty state: open the boards catalogue to create one.
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
