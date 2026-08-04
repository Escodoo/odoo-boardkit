// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {Component, onWillUpdateProps, useState} from "@odoo/owl";
import {
    contrastFontColor,
    contrastingPaletteColor,
    darkestPaletteColor,
    formatItemValue,
    formatNumber,
    hexToRGBA,
} from "./utils";
import {ChartRenderer} from "./chart_renderer";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {ListCard} from "./list_card";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";

export class DashboardItemCard extends Component {
    static template = "boardkit_dashboard.ItemCard";
    static components = {ChartRenderer, ListCard, Dropdown, DropdownItem};
    static props = {
        config: Object,
        data: {type: [Object, {value: null}], optional: true},
        filterStamp: {type: Number, optional: true},
        currency: {type: Object, optional: true},
        editable: Boolean,
        isManager: Boolean,
        preview: {type: Boolean, optional: true},
        onDrill: Function,
        onDrillData: {type: Function, optional: true},
        onOpenRecord: Function,
        onPageChange: Function,
        onEdit: Function,
        onDuplicate: Function,
        onDelete: Function,
        onExport: Function,
        onDragStart: Function,
        onResizeStart: Function,
    };

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            drillStack: [],
            drilling: false,
        });
        onWillUpdateProps((nextProps) => {
            if (
                nextProps.filterStamp !== this.props.filterStamp ||
                nextProps.config !== this.props.config
            ) {
                this.state.drillStack = [];
                this.state.drilling = false;
            }
        });
    }

    get config() {
        return this.props.config;
    }

    get data() {
        return this.displayData;
    }

    get displayData() {
        const stack = this.state.drillStack;
        if (stack.length) {
            return stack[stack.length - 1].data;
        }
        return this.props.data;
    }

    get displayConfig() {
        const stack = this.state.drillStack;
        if (!stack.length) {
            return this.config;
        }
        return stack[stack.length - 1].config || this.config;
    }

    get isDrilled() {
        return this.state.drillStack.length > 0;
    }

    get themedColors() {
        // Palette-driven theming only applies to tiles and KPIs; other item
        // types render their data with the palette already.
        if (
            this.config.background_style === "palette" &&
            ["tile", "kpi"].includes(this.config.type)
        ) {
            const background = darkestPaletteColor(this.config);
            return {background, color: contrastFontColor(background)};
        }
        return {
            background: this.config.background_color || "#FFFFFF",
            color: this.config.font_color || "#111827",
        };
    }

    get cardStyle() {
        const {background, color} = this.themedColors;
        // Expose the background as a CSS variable so inner sticky elements
        // (e.g. list headers) can stay opaque with the same color.
        return `background-color: ${background}; color: ${color}; --esc-card-bg: ${background};`;
    }

    get tileIconStyle() {
        const color = this.themedColors.color;
        return `background-color: ${hexToRGBA(color, 0.12)}; color: ${color};`;
    }

    get kpiProgressTrackStyle() {
        let style = "height: 8px;";
        if (this.config.background_style === "palette") {
            // Semi-transparent font color so the empty track stays visible
            // on both dark and light themed cards.
            style += ` background-color: ${hexToRGBA(this.themedColors.color, 0.25)};`;
        }
        return style;
    }

    get kpiProgressStyle() {
        let style = `width: ${this.targetProgress || 0}%;`;
        if (this.config.background_style === "palette") {
            // Prefer a palette swatch that contrasts with the card background;
            // never reuse the darkest color (which is the background itself).
            style += ` background-color: ${contrastingPaletteColor(
                this.config,
                this.themedColors.background
            )};`;
        }
        return style;
    }

    get formattedValue() {
        return formatItemValue(this.data?.value, this.config, this.props.currency);
    }

    get aggregationLabel() {
        const labels = {
            count: _t("Count"),
            sum: _t("Sum"),
            avg: _t("Average"),
        };
        return labels[this.config.aggregation] || "";
    }

    get formattedValue2() {
        return formatItemValue(this.data?.value_2, this.config, this.props.currency);
    }

    get formattedTarget() {
        return formatItemValue(this.data?.target, this.config, this.props.currency);
    }

    get targetProgress() {
        if (this.data?.target === undefined || this.data?.target === null) {
            return null;
        }
        const target = Number(this.data.target);
        if (!target) {
            return 0;
        }
        return Math.min(100, Math.max(0, (this.data.value / target) * 100));
    }

    get kpiComparison() {
        const data = this.data || {};
        const display = this.config.kpi.display;
        if (data.value_2 === undefined) {
            return null;
        }
        if (display === "sum") {
            return formatItemValue(
                data.value + data.value_2,
                this.config,
                this.props.currency
            );
        }
        if (display === "ratio") {
            return data.value_2
                ? formatNumber(data.value / data.value_2, "exact")
                : "-";
        }
        if (display === "percent") {
            return data.value_2
                ? `${formatNumber((data.value / data.value_2) * 100, "exact")}%`
                : "-";
        }
        return null;
    }

    get previousDelta() {
        const data = this.data || {};
        if (data.previous_value === undefined || !data.previous_value) {
            return null;
        }
        const delta =
            ((data.value - data.previous_value) / Math.abs(data.previous_value)) * 100;
        return {
            value: `${formatNumber(Math.abs(delta), "exact")}%`,
            positive: delta >= 0,
        };
    }

    async handleDrill(domain, label) {
        if (this.props.editable || this.state.drilling) {
            return;
        }
        const levels = this.config.drill_levels || [];
        const depth = this.state.drillStack.length;
        // Chart-to-chart levels work on the dashboard and in the form preview.
        if (depth < levels.length && this.props.onDrillData) {
            const level = levels[depth];
            const stackBefore = this.state.drillStack;
            this.state.drilling = true;
            try {
                const data = await this.props.onDrillData(level, domain);
                // Discard the result if the user navigated the stack meanwhile.
                if (this.state.drillStack !== stackBefore) {
                    return;
                }
                this.state.drillStack = [
                    ...stackBefore,
                    {
                        label,
                        data,
                        config: {...this.config, type: level.type},
                    },
                ];
            } catch (error) {
                this.notification.add(
                    error.data?.message || error.message || _t("Drill down failed."),
                    {type: "danger"}
                );
            } finally {
                this.state.drilling = false;
            }
            return;
        }
        // Opening the record list is dashboard-only.
        if (this.props.preview || !this.config.show_records) {
            return;
        }
        this.props.onDrill(domain, label || this.config.name);
    }

    goToDrillLevel(index) {
        // Index -1 returns to the root item data.
        if (index < 0) {
            this.state.drillStack = [];
            return;
        }
        this.state.drillStack = this.state.drillStack.slice(0, index + 1);
    }

    onBodyClicked() {
        if (this.isDrilled) {
            return;
        }
        if (["tile", "kpi"].includes(this.config.type) && this.data?.domain) {
            this.handleDrill(this.data.domain, this.config.name);
        }
    }

    _mapDrillTarget(index) {
        const data = this.displayData;
        if ((data?.mode || this.displayConfig.map_mode) === "points") {
            const point = data?.points?.[index];
            return point?.domain ? [point.domain, point.label || ""] : null;
        }
        const region = data?.regions?.[index];
        return region?.domain ? [region.domain, region.label] : null;
    }

    _datasetDrillTarget(datasetIndex, index) {
        const data = this.displayData;
        const dataset = data?.datasets?.[datasetIndex];
        const domain = dataset?.drilldowns?.[index];
        return domain ? [domain, data.labels?.[index] || dataset.label || ""] : null;
    }

    _sectionDrillTarget(datasetIndex, index) {
        const type = this.displayConfig.type;
        if (type === "gauge") {
            return this.displayData?.domain
                ? [this.displayData.domain, this.config.name]
                : null;
        }
        if (type === "map") {
            return this._mapDrillTarget(index);
        }
        return this._datasetDrillTarget(datasetIndex, index);
    }

    onChartSectionClicked(datasetIndex, index) {
        if (this.props.editable) {
            return;
        }
        const levels = this.config.drill_levels || [];
        const depth = this.state.drillStack.length;
        const canChartDrill = depth < levels.length && this.props.onDrillData;
        const canOpenRecords = !this.props.preview && this.config.show_records;
        if (!canChartDrill && !canOpenRecords) {
            return;
        }
        const target = this._sectionDrillTarget(datasetIndex, index);
        if (target) {
            this.handleDrill(...target);
        }
    }
}
