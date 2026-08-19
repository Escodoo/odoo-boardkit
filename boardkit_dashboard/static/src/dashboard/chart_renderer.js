// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {Component, onWillStart, useEffect, useRef, useState} from "@odoo/owl";
import {alpha2ToNumeric, numericToAlpha2} from "./country_codes";
import {formatItemValue, getPaletteColor, hexToRGBA} from "./utils";
import {_t} from "@web/core/l10n/translation";
import {browser} from "@web/core/browser/browser";
import {loadBundle} from "@web/core/assets";

const CHART_TYPE_MAP = {
    bar: "bar",
    bar_horizontal: "bar",
    line: "line",
    area: "line",
    pie: "pie",
    doughnut: "doughnut",
    polar: "polarArea",
    radar: "radar",
    scatter: "scatter",
    funnel: "funnel",
    bullet: "bar",
    gauge: "doughnut",
    map: "choropleth",
};

const PIE_LIKE = ["pie", "doughnut", "polar"];
const CARTESIAN = ["bar", "bar_horizontal", "line", "area", "scatter"];
const TARGET_LINE_TYPES = ["bar", "bar_horizontal", "line", "area"];
const OVERLAY_LINE_TYPES = TARGET_LINE_TYPES;
const EXTENSION_TYPES = ["funnel", "map"];

// The geo projection is fitted to the outline, so 1 is the "whole map" zoom.
const MAP_MIN_ZOOM = 1;
const MAP_MAX_ZOOM = 12;
const MAP_ZOOM_STEP = 1.3;
// Pointer travel (px) above which a press is a pan instead of a drill-down.
const MAP_PAN_THRESHOLD = 3;

let extensionsLoaded = false;

function seriesAverage(values) {
    const nums = values.filter(
        (value) => typeof value === "number" && !Number.isNaN(value)
    );
    if (!nums.length) {
        return null;
    }
    return nums.reduce((sum, value) => sum + value, 0) / nums.length;
}

function seriesTrend(values) {
    // Linear regression of y over index x = 0..n-1 (primary series only).
    const points = [];
    values.forEach((value, index) => {
        if (typeof value === "number" && !Number.isNaN(value)) {
            points.push([index, value]);
        }
    });
    if (points.length < 2) {
        return null;
    }
    const n = points.length;
    let sumX = 0;
    let sumY = 0;
    let sumXY = 0;
    let sumXX = 0;
    for (const [x, y] of points) {
        sumX += x;
        sumY += y;
        sumXY += x * y;
        sumXX += x * x;
    }
    const denominator = n * sumXX - sumX * sumX;
    if (!denominator) {
        return null;
    }
    const slope = (n * sumXY - sumX * sumY) / denominator;
    const intercept = (sumY - slope * sumX) / n;
    return values.map((_, index) => intercept + slope * index);
}

function appendPreviousPeriodDatasets(datasets, config, data) {
    const previous = data.previous_datasets || [];
    if (!OVERLAY_LINE_TYPES.includes(config.type) || !previous.length) {
        return;
    }
    previous.forEach((dataset, index) => {
        const color = getPaletteColor(config, index);
        datasets.push({
            type: "line",
            label: _t("%s (previous)", dataset.label),
            data: dataset.data || [],
            borderColor: hexToRGBA(color, 0.55),
            backgroundColor: hexToRGBA(color, 0.1),
            borderDash: [6, 4],
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            tension: 0.35,
            escOverlay: true,
        });
    });
}

function appendOverlayDatasets(datasets, config, labels, data = {}) {
    const itemType = config.type;
    if (!OVERLAY_LINE_TYPES.includes(itemType) || !labels.length) {
        return;
    }
    appendPreviousPeriodDatasets(datasets, config, data);
    const primaryValues = datasets[0]?.data || [];
    if (config.target_enabled && config.target_value) {
        datasets.push({
            type: "line",
            label: _t("Target"),
            data: labels.map(() => config.target_value),
            borderColor: "#EA6175",
            borderDash: [6, 4],
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            escOverlay: true,
        });
    }
    if (config.show_average_line) {
        const average = seriesAverage(primaryValues);
        if (average !== null) {
            datasets.push({
                type: "line",
                label: _t("Average"),
                data: labels.map(() => average),
                borderColor: "#6B7280",
                borderDash: [8, 4],
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                escOverlay: true,
            });
        }
    }
    if (config.show_trend_line) {
        const trend = seriesTrend(primaryValues);
        if (trend) {
            datasets.push({
                type: "line",
                label: _t("Trend"),
                data: trend,
                borderColor: "#059669",
                borderDash: [4, 4],
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                escOverlay: true,
            });
        }
    }
}

async function ensureChartExtensions(itemType) {
    await loadBundle("web.chartjs_lib");
    if (!EXTENSION_TYPES.includes(itemType) || extensionsLoaded) {
        return;
    }
    await loadBundle("boardkit_dashboard.chartjs_extensions");
    extensionsLoaded = true;
}

function getWorldTopology() {
    // Provided by the lazy countries_110m.js script in chartjs_extensions.
    return window.ESCODOO_WORLD_TOPOLOGY || null;
}

const gaugeCenterPlugin = {
    id: "boardkitGaugeCenter",
    afterDraw(chart, _args, pluginOptions) {
        const {ctx, chartArea} = chart;
        if (!chartArea) {
            return;
        }
        const text = pluginOptions?.text || "";
        if (!text) {
            return;
        }
        const centerX = (chartArea.left + chartArea.right) / 2;
        const targetText = pluginOptions?.targetText || "";
        const valueY = targetText ? chartArea.bottom - 22 : chartArea.bottom - 8;
        ctx.save();
        ctx.fillStyle = pluginOptions?.color || "#111827";
        ctx.font = "600 1.25rem sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText(text, centerX, valueY);
        if (targetText) {
            ctx.fillStyle = pluginOptions?.targetColor || "#EA6175";
            ctx.font = "500 0.75rem sans-serif";
            ctx.fillText(targetText, centerX, chartArea.bottom - 6);
        }
        ctx.restore();
    },
};

const gaugeTargetPlugin = {
    id: "boardkitGaugeTarget",
    afterDatasetsDraw(chart, _args, pluginOptions) {
        const target = pluginOptions?.target;
        const maxValue = pluginOptions?.max;
        if ((target !== 0 && !target) || !maxValue) {
            return;
        }
        const meta = chart.getDatasetMeta(0);
        const arcs = meta?.data || [];
        if (!arcs.length) {
            return;
        }
        const props = arcs[0].getProps(
            ["x", "y", "innerRadius", "outerRadius", "startAngle"],
            true
        );
        if (!props.outerRadius || props.startAngle === undefined) {
            return;
        }
        // Use the first arc's startAngle (Chart.js radians) and the dataset
        // circumference so the marker stays correct even if the remainder
        // segment has zero length.
        const dataset = chart.data.datasets[0] || {};
        const circumferenceDeg = dataset.circumference ?? 180;
        const ratio = Math.min(Math.max(target / maxValue, 0), 1);
        const angle = props.startAngle + ratio * ((circumferenceDeg * Math.PI) / 180);
        const inner = Math.max((props.innerRadius || 0) - 4, 0);
        const outer = props.outerRadius + 6;
        const cos = Math.cos(angle);
        const sin = Math.sin(angle);
        const {ctx} = chart;
        ctx.save();
        ctx.strokeStyle = pluginOptions?.color || "#EA6175";
        ctx.lineWidth = 3;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(props.x + cos * inner, props.y + sin * inner);
        ctx.lineTo(props.x + cos * outer, props.y + sin * outer);
        ctx.stroke();
        ctx.beginPath();
        ctx.fillStyle = pluginOptions?.color || "#EA6175";
        ctx.arc(props.x + cos * outer, props.y + sin * outer, 3.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    },
};

const bulletTargetPlugin = {
    id: "boardkitBulletTarget",
    afterDatasetsDraw(chart, _args, pluginOptions) {
        const target = pluginOptions?.target;
        if (!target && target !== 0) {
            return;
        }
        const {ctx, chartArea, scales} = chart;
        const xScale = scales.x;
        if (!chartArea || !xScale) {
            return;
        }
        const x = xScale.getPixelForValue(target);
        ctx.save();
        ctx.strokeStyle = pluginOptions?.color || "#EA6175";
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 3]);
        ctx.beginPath();
        ctx.moveTo(x, chartArea.top);
        ctx.lineTo(x, chartArea.bottom);
        ctx.stroke();
        ctx.restore();
    },
};

export class ChartRenderer extends Component {
    static template = "boardkit_dashboard.ChartRenderer";
    static props = {
        config: Object,
        data: Object,
        onSectionClicked: {type: Function, optional: true},
        currency: {type: Object, optional: true},
    };

    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;
        this.world = null;
        this.renderToken = 0;
        // Zoom / pan of a map item is a transient view state: it is kept out of
        // the reactive state so panning does not re-render the component, and
        // is reset whenever the chart is rebuilt.
        this.mapView = {scale: MAP_MIN_ZOOM, offset: [0, 0]};
        this.mapViewFrame = null;
        this.mapPan = null;
        this.suppressMapClick = false;
        this.state = useState({mapZoomed: false});
        onWillStart(() => ensureChartExtensions(this.props.config.type));
        useEffect(
            () => {
                this.renderChart();
                return () => this.destroyChart();
            },
            () => [this.props.data, this.props.config]
        );
        useEffect(
            (el, type) => {
                if (!el || type !== "map") {
                    return undefined;
                }
                return this.bindMapInteractions(el);
            },
            () => [this.canvasRef.el, this.props.config.type]
        );
    }

    destroyChart() {
        this.cancelMapViewUpdate();
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }

    async renderChart() {
        // The type can change while the component is mounted (form preview),
        // so the required Chart.js extensions are awaited on every render.
        const token = ++this.renderToken;
        this.destroyChart();
        this.resetMapView(false);
        if (!this.canvasRef.el || !this.props.data) {
            return;
        }
        await ensureChartExtensions(this.props.config.type);
        if (token !== this.renderToken || !this.canvasRef.el) {
            return;
        }
        if (this.props.config.type === "map") {
            this.world = getWorldTopology();
        }
        this.destroyChart();
        const chartConfig = this.buildChartConfig();
        if (!chartConfig) {
            return;
        }
        // eslint-disable-next-line no-undef
        this.chart = new Chart(this.canvasRef.el, chartConfig);
    }

    buildChartConfig() {
        const itemType = this.props.config.type;
        if (itemType === "gauge") {
            return this.buildGaugeConfig();
        }
        if (itemType === "bullet") {
            return this.buildBulletConfig();
        }
        if (itemType === "funnel") {
            return this.buildFunnelConfig();
        }
        if (itemType === "map") {
            return this.buildMapConfig();
        }
        return this.buildStandardConfig();
    }

    buildStandardConfig() {
        const config = this.props.config;
        const data = this.props.data;
        const itemType = config.type;
        const chartType = CHART_TYPE_MAP[itemType] || "bar";
        const labels = data.labels || [];
        const datasets = (data.datasets || []).map((dataset, index) => {
            const color = getPaletteColor(config, index);
            const styled = {
                label: dataset.label,
                data: dataset.data,
            };
            if (PIE_LIKE.includes(itemType)) {
                styled.backgroundColor = labels.map((__, j) =>
                    getPaletteColor(config, j)
                );
                styled.borderColor = "#FFFFFF";
                styled.borderWidth = 1;
            } else if (itemType === "radar" || itemType === "area") {
                styled.backgroundColor = hexToRGBA(color, 0.3);
                styled.borderColor = color;
                styled.borderWidth = 2;
                styled.fill = true;
                styled.pointRadius = 2;
            } else if (itemType === "line") {
                styled.borderColor = color;
                styled.backgroundColor = color;
                styled.borderWidth = 2;
                styled.fill = false;
                styled.pointRadius = 2;
            } else if (itemType === "scatter") {
                styled.backgroundColor = hexToRGBA(color, 0.8);
                styled.borderColor = color;
                styled.pointRadius = 5;
            } else {
                styled.backgroundColor = color;
                styled.borderColor = color;
                styled.borderRadius = 2;
            }
            if (["line", "area"].includes(itemType)) {
                styled.tension = 0.35;
            }
            return styled;
        });
        appendOverlayDatasets(datasets, config, labels, data);
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            animation: {duration: 300},
            plugins: {
                legend: {
                    display: this.props.config.legend_visible,
                    position: "bottom",
                    labels: {boxWidth: 10, usePointStyle: true},
                },
            },
            onClick: (event) => this.onChartClicked(event),
        };
        if (itemType === "bar_horizontal") {
            options.indexAxis = "y";
        }
        if (CARTESIAN.includes(itemType)) {
            options.scales = {
                x: {stacked: config.stacked, grid: {display: false}},
                y: {stacked: config.stacked, beginAtZero: true},
            };
        }
        if (itemType === "scatter") {
            const pointLabels = labels;
            options.plugins.tooltip = {
                callbacks: {
                    label(context) {
                        const label = pointLabels[context.dataIndex] || "";
                        return `${label}: (${context.parsed.x}, ${context.parsed.y})`;
                    },
                },
            };
        }
        if (PIE_LIKE.includes(itemType)) {
            options.plugins.tooltip = {
                callbacks: {
                    label(context) {
                        const value = Number(context.parsed) || 0;
                        const series = context.dataset.data || [];
                        const total = series.reduce(
                            (sum, entry) => sum + (Number(entry) || 0),
                            0
                        );
                        const pct = total ? ((value / total) * 100).toFixed(1) : "0.0";
                        const seriesLabel = context.dataset.label || "";
                        return seriesLabel
                            ? `${seriesLabel}: ${value} (${pct}%)`
                            : `${value} (${pct}%)`;
                    },
                },
            };
        }
        return {type: chartType, data: {labels, datasets}, options};
    }

    buildGaugeConfig() {
        const config = this.props.config;
        const data = this.props.data;
        const value = data.value || 0;
        const maxValue = Math.max(data.max || 0, value, 1);
        const color = getPaletteColor(config, 0);
        const remainder = Math.max(maxValue - value, 0);
        const centerText = formatItemValue(value, config, this.props.currency);
        const hasTarget = data.target !== false && data.target !== undefined;
        const target = hasTarget ? data.target || 0 : null;
        const targetColor = "#EA6175";
        const targetText = hasTarget
            ? _t("Target: %s", formatItemValue(target, config, this.props.currency))
            : "";
        return {
            type: "doughnut",
            data: {
                labels: [_t("Value"), _t("Remaining")],
                datasets: [
                    {
                        data: [value, remainder],
                        backgroundColor: [color, hexToRGBA(color, 0.15)],
                        borderWidth: 0,
                        circumference: 180,
                        rotation: 270,
                        cutout: "70%",
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {display: false},
                    tooltip: {
                        callbacks: {
                            label(context) {
                                return `${context.label}: ${context.parsed}`;
                            },
                        },
                    },
                    boardkitGaugeCenter: {
                        text: centerText,
                        color: config.font_color || "#111827",
                        targetText,
                        targetColor,
                    },
                    boardkitGaugeTarget: {
                        target,
                        max: maxValue,
                        color: targetColor,
                    },
                },
                onClick: () => {
                    if (this.props.onSectionClicked) {
                        this.props.onSectionClicked(0, 0);
                    }
                },
            },
            plugins: [gaugeCenterPlugin, gaugeTargetPlugin],
        };
    }

    buildBulletConfig() {
        const config = this.props.config;
        const data = this.props.data;
        const labels = data.labels || [];
        const values = data.datasets?.[0]?.data || [];
        const color = getPaletteColor(config, 0);
        const target = data.target;
        const trackMax = Math.max(...(values.length ? values : [0]), target || 0, 1);
        return {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: _t("Track"),
                        data: labels.map(() => trackMax),
                        backgroundColor: hexToRGBA(color, 0.12),
                        borderWidth: 0,
                        borderRadius: 4,
                        barPercentage: 0.7,
                        order: 2,
                    },
                    {
                        label: data.datasets?.[0]?.label || _t("Value"),
                        data: values,
                        backgroundColor: color,
                        borderWidth: 0,
                        borderRadius: 4,
                        barPercentage: 0.45,
                        order: 1,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {beginAtZero: true, stacked: false, grid: {display: false}},
                    y: {stacked: false, grid: {display: false}},
                },
                plugins: {
                    legend: {display: false},
                    boardkitBulletTarget: {
                        target: target === false ? null : target,
                        color: "#EA6175",
                    },
                },
                onClick: (event) => this.onChartClicked(event),
            },
            plugins: [bulletTargetPlugin],
        };
    }

    buildFunnelConfig() {
        const config = this.props.config;
        const data = this.props.data;
        const labels = data.labels || [];
        const values = data.datasets?.[0]?.data || [];
        return {
            type: "funnel",
            data: {
                labels,
                datasets: [
                    {
                        label: data.datasets?.[0]?.label || _t("Value"),
                        data: values,
                        backgroundColor: labels.map((__, index) =>
                            getPaletteColor(config, index)
                        ),
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: "y",
                plugins: {
                    legend: {
                        display: config.legend_visible,
                        position: "bottom",
                        labels: {boxWidth: 10, usePointStyle: true},
                    },
                },
                onClick: (event) => this.onChartClicked(event),
            },
        };
    }

    _mapOutlineFeatures() {
        // eslint-disable-next-line no-undef
        const countries = ChartGeo.topojson.feature(
            this.world,
            this.world.objects.countries
        ).features;
        const focusCode = (this.props.config.map_focus_country || "").toUpperCase();
        if (!focusCode) {
            return countries;
        }
        const numeric = alpha2ToNumeric(focusCode);
        if (!numeric) {
            return countries;
        }
        const focused = countries.filter((feature) => {
            const key = String(feature.id || "").padStart(3, "0");
            return key === numeric || String(feature.id) === String(Number(numeric));
        });
        return focused.length ? focused : countries;
    }

    buildMapConfig() {
        if (!this.world) {
            return null;
        }
        const mode = this.props.data.mode || this.props.config.map_mode || "regions";
        if (mode === "points") {
            return this.buildBubbleMapConfig();
        }
        return this.buildChoroplethMapConfig();
    }

    buildChoroplethMapConfig() {
        const config = this.props.config;
        const regions = this.props.data.regions || [];
        const valueByNumeric = {};
        for (const region of regions) {
            const numeric = alpha2ToNumeric(region.code);
            if (numeric) {
                valueByNumeric[numeric] = region.value || 0;
                valueByNumeric[String(Number(numeric))] = region.value || 0;
            }
        }
        const countries = this._mapOutlineFeatures();
        const color = getPaletteColor(config, 0);
        return {
            type: "choropleth",
            data: {
                labels: countries.map((feature) => feature.properties.name),
                datasets: [
                    {
                        label: config.name,
                        outline: countries,
                        data: countries.map((feature) => {
                            const key = String(feature.id || "").padStart(3, "0");
                            return {
                                feature,
                                value:
                                    valueByNumeric[key] ||
                                    valueByNumeric[String(feature.id)] ||
                                    0,
                            };
                        }),
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                showOutline: true,
                showGraticule: false,
                plugins: {
                    legend: {display: false},
                    tooltip: {
                        callbacks: {
                            label(context) {
                                const value = context.raw?.value || 0;
                                const name =
                                    context.raw?.feature?.properties?.name || "";
                                return `${name}: ${value}`;
                            },
                        },
                    },
                },
                scales: {
                    projection: {
                        axis: "x",
                        projection: "equalEarth",
                        ...this.mapProjectionView(),
                    },
                    color: {
                        axis: "x",
                        quantize: 5,
                        legend: {
                            position: "bottom-right",
                            align: "right",
                        },
                        interpolate: (normalized) =>
                            hexToRGBA(color, 0.2 + normalized * 0.8),
                    },
                },
                onClick: (event) => this.onMapClicked(event),
            },
        };
    }

    buildBubbleMapConfig() {
        const config = this.props.config;
        const points = this.props.data.points || [];
        const countries = this._mapOutlineFeatures();
        const color = getPaletteColor(config, 0);
        // With a single value the size scale would expand around it and draw a
        // meaningless legend, so markers keep a fixed radius instead.
        const values = points.map((point) => point.value || 0);
        const uniform =
            values.length < 2 || values.every((value) => value === values[0]);
        return {
            type: "bubbleMap",
            data: {
                labels: points.map((point) => point.label || ""),
                datasets: [
                    {
                        label: config.name,
                        outline: countries,
                        showOutline: true,
                        // Light land fill + stronger borders so outlines remain
                        // readable on the white card (choropleth fills by value).
                        outlineBackgroundColor: hexToRGBA(color, 0.12),
                        outlineBorderColor: "#94A3B8",
                        outlineBorderWidth: 0.75,
                        backgroundColor: hexToRGBA(color, 0.65),
                        borderColor: color,
                        data: points.map((point) => ({
                            latitude: point.latitude,
                            longitude: point.longitude,
                            value: point.value || 0,
                        })),
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                showOutline: true,
                showGraticule: false,
                plugins: {
                    legend: {display: false},
                    tooltip: {
                        mode: "nearest",
                        intersect: true,
                        callbacks: {
                            label(context) {
                                const label =
                                    context.chart.data.labels?.[context.dataIndex] ||
                                    "";
                                const value = context.raw?.value || 0;
                                return label ? `${label}: ${value}` : String(value);
                            },
                        },
                    },
                },
                scales: {
                    projection: {
                        axis: "x",
                        projection: "equalEarth",
                        ...this.mapProjectionView(),
                    },
                    size: {
                        axis: "x",
                        display: !uniform,
                        range: uniform ? [8, 8] : [4, 18],
                        legend: {align: "bottom", position: "bottom-right"},
                    },
                },
                onClick: (event) => this.onBubbleMapClicked(event),
            },
        };
    }

    mapProjectionView() {
        return {
            projectionScale: this.mapView.scale,
            projectionOffset: [...this.mapView.offset],
        };
    }

    bindMapInteractions(canvas) {
        const onWheel = this.onMapWheel.bind(this);
        const onPointerDown = this.onMapPointerDown.bind(this);
        const onPointerMove = this.onMapPointerMove.bind(this);
        const onPointerUp = this.onMapPointerUp.bind(this);
        // Chart.js registers its own passive wheel listener, so stopping the
        // dashboard from scrolling requires an explicit non-passive one.
        canvas.addEventListener("wheel", onWheel, {passive: false});
        canvas.addEventListener("pointerdown", onPointerDown);
        canvas.addEventListener("pointermove", onPointerMove);
        canvas.addEventListener("pointerup", onPointerUp);
        canvas.addEventListener("pointercancel", onPointerUp);
        return () => {
            canvas.removeEventListener("wheel", onWheel);
            canvas.removeEventListener("pointerdown", onPointerDown);
            canvas.removeEventListener("pointermove", onPointerMove);
            canvas.removeEventListener("pointerup", onPointerUp);
            canvas.removeEventListener("pointercancel", onPointerUp);
            this.mapPan = null;
        };
    }

    onMapWheel(event) {
        // A bare wheel keeps scrolling the dashboard; zooming is opt-in with the
        // modifier key so a map never traps the page scroll.
        if (!this.chart || (!event.ctrlKey && !event.metaKey)) {
            return;
        }
        event.preventDefault();
        const rect = this.canvasRef.el.getBoundingClientRect();
        this.zoomMapAt(event.deltaY < 0 ? MAP_ZOOM_STEP : 1 / MAP_ZOOM_STEP, {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
        });
    }

    onMapPointerDown(event) {
        if (!this.chart || event.button !== 0) {
            return;
        }
        this.mapPan = {
            pointerId: event.pointerId,
            x: event.clientX,
            y: event.clientY,
            moved: false,
        };
        this.suppressMapClick = false;
        event.target.setPointerCapture?.(event.pointerId);
    }

    onMapPointerMove(event) {
        const pan = this.mapPan;
        if (!pan || pan.pointerId !== event.pointerId) {
            return;
        }
        const deltaX = event.clientX - pan.x;
        const deltaY = event.clientY - pan.y;
        if (!pan.moved && Math.hypot(deltaX, deltaY) < MAP_PAN_THRESHOLD) {
            return;
        }
        pan.moved = true;
        pan.x = event.clientX;
        pan.y = event.clientY;
        this.mapView.offset = [
            this.mapView.offset[0] + deltaX,
            this.mapView.offset[1] + deltaY,
        ];
        this.applyMapView();
    }

    onMapPointerUp(event) {
        const pan = this.mapPan;
        if (!pan || pan.pointerId !== event.pointerId) {
            return;
        }
        this.mapPan = null;
        event.target.releasePointerCapture?.(event.pointerId);
        // The click event fired right after a drag must not drill down.
        this.suppressMapClick = pan.moved;
    }

    consumeMapClickGuard() {
        const suppressed = this.suppressMapClick;
        this.suppressMapClick = false;
        return suppressed;
    }

    zoomMapAt(factor, anchor) {
        const projection = this.chart?.scales?.projection?.projection;
        if (!projection) {
            return;
        }
        const current = this.mapView.scale;
        const next = Math.min(Math.max(current * factor, MAP_MIN_ZOOM), MAP_MAX_ZOOM);
        if (next === current) {
            return;
        }
        const ratio = next / current;
        const offset = this.mapView.offset;
        // The projection translation already includes the current offset, so
        // removing it gives the auto-fit origin the map is built around. Keeping
        // the anchor point still is then an affine correction of the offset.
        const [translateX, translateY] = projection.translate();
        const originX = translateX - offset[0];
        const originY = translateY - offset[1];
        this.mapView.scale = next;
        this.mapView.offset = [
            (anchor.x - originX) * (1 - ratio) + ratio * offset[0],
            (anchor.y - originY) * (1 - ratio) + ratio * offset[1],
        ];
        this.applyMapView();
    }

    zoomMapBy(factor) {
        const area = this.chart?.chartArea;
        if (!area) {
            return;
        }
        this.zoomMapAt(factor, {
            x: (area.left + area.right) / 2,
            y: (area.top + area.bottom) / 2,
        });
    }

    zoomInMap() {
        this.zoomMapBy(MAP_ZOOM_STEP);
    }

    zoomOutMap() {
        this.zoomMapBy(1 / MAP_ZOOM_STEP);
    }

    resetMapView(apply = true) {
        this.cancelMapViewUpdate();
        this.mapView = {scale: MAP_MIN_ZOOM, offset: [0, 0]};
        if (apply) {
            this.applyMapView();
            return;
        }
        this.state.mapZoomed = false;
    }

    cancelMapViewUpdate() {
        if (this.mapViewFrame) {
            browser.cancelAnimationFrame(this.mapViewFrame);
            this.mapViewFrame = null;
        }
    }

    applyMapView() {
        this.state.mapZoomed =
            this.mapView.scale !== MAP_MIN_ZOOM ||
            this.mapView.offset[0] !== 0 ||
            this.mapView.offset[1] !== 0;
        // Pointer moves fire faster than the geo features can be rasterized, so
        // the projection update is coalesced into the next frame.
        if (this.mapViewFrame) {
            return;
        }
        this.mapViewFrame = browser.requestAnimationFrame(() => {
            this.mapViewFrame = null;
            this._applyMapView();
        });
    }

    _applyMapView() {
        const projectionOptions = this.chart?.options?.scales?.projection;
        if (!projectionOptions) {
            return;
        }
        Object.assign(projectionOptions, this.mapProjectionView());
        // The geo scale only reports changed bounds when the canvas is resized,
        // and the controller relies on that flag to drop the rasterized
        // features. Without an explicit invalidation the map would be redrawn
        // with the previous projection.
        const meta = this.chart.getDatasetMeta(0);
        if (meta?.dataset) {
            meta.dataset.cache = undefined;
        }
        for (const element of meta?.data || []) {
            element.cache = undefined;
        }
        this.chart.update("none");
    }

    onChartClicked(event) {
        if (!this.chart || !this.props.onSectionClicked) {
            return;
        }
        const elements = this.chart.getElementsAtEventForMode(
            event,
            "nearest",
            {intersect: true},
            true
        );
        if (!elements.length) {
            return;
        }
        const {datasetIndex, index} = elements[0];
        // Bullet draws a track dataset first; map clicks to the value series.
        if (this.props.config.type === "bullet") {
            this.props.onSectionClicked(0, index);
            return;
        }
        const dataset = this.chart.data.datasets[datasetIndex];
        // Ignore target / average / trend overlay datasets for drill-down.
        if (dataset?.escOverlay) {
            return;
        }
        this.props.onSectionClicked(datasetIndex, index);
    }

    onMapClicked(event) {
        if (
            this.consumeMapClickGuard() ||
            !this.chart ||
            !this.props.onSectionClicked
        ) {
            return;
        }
        const elements = this.chart.getElementsAtEventForMode(
            event,
            "nearest",
            {intersect: true},
            true
        );
        if (!elements.length) {
            return;
        }
        const {index} = elements[0];
        const point = this.chart.data.datasets[0]?.data?.[index];
        const alpha2 = numericToAlpha2(point?.feature?.id);
        if (!alpha2) {
            return;
        }
        const regions = this.props.data.regions || [];
        const regionIndex = regions.findIndex((region) => region.code === alpha2);
        if (regionIndex >= 0) {
            this.props.onSectionClicked(0, regionIndex);
        }
    }

    onBubbleMapClicked(event) {
        if (
            this.consumeMapClickGuard() ||
            !this.chart ||
            !this.props.onSectionClicked
        ) {
            return;
        }
        const elements = this.chart.getElementsAtEventForMode(
            event,
            "nearest",
            {intersect: true},
            true
        );
        if (!elements.length) {
            return;
        }
        this.props.onSectionClicked(0, elements[0].index);
    }
}
