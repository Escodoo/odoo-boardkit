// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {formatFloat, humanNumber} from "@web/core/utils/numbers";

export const PALETTES = {
    default: [
        "#4EA7F2",
        "#EA6175",
        "#43C5B1",
        "#F4A261",
        "#8481DD",
        "#FFD86D",
        "#3188E6",
        "#CE4257",
        "#00A78D",
        "#F48935",
        "#5752D1",
        "#FFBC2C",
    ],
    ocean: [
        "#056BD9",
        "#3188E6",
        "#4EA7F2",
        "#00A78D",
        "#43C5B1",
        "#0E8270",
        "#5752D1",
        "#8481DD",
        "#7F4295",
        "#A76DBC",
    ],
    sunset: [
        "#CE4257",
        "#EA6175",
        "#F48935",
        "#F4A261",
        "#FFBC2C",
        "#FFD86D",
        "#982738",
        "#BE5D10",
        "#C08A16",
        "#A76DBC",
    ],
    electric: [
        "#00E5FF",
        "#FF3D71",
        "#00FFAB",
        "#FFD500",
        "#B388FF",
        "#FF9E00",
        "#00B8D9",
        "#F050F8",
        "#7CFF4F",
        "#FF6D00",
    ],
    pastel: [
        "#7EB5E8",
        "#F4A0B0",
        "#8FD8C8",
        "#F8C99B",
        "#B3B1E8",
        "#FBE39B",
        "#A8D8F0",
        "#E8B4D8",
        "#C8E6A0",
        "#F6B8A0",
    ],
    vivid: [
        "#1E88E5",
        "#E53935",
        "#00897B",
        "#FB8C00",
        "#8E24AA",
        "#FDD835",
        "#039BE5",
        "#D81B60",
        "#43A047",
        "#F4511E",
    ],
    earth: [
        "#B08968",
        "#606C38",
        "#D4A373",
        "#7F5539",
        "#A3B18A",
        "#BC6C25",
        "#588157",
        "#9C6644",
        "#CCD5AE",
        "#6C584C",
    ],
    royal: [
        "#2C3E90",
        "#922B5B",
        "#14746F",
        "#B68A00",
        "#5E3A98",
        "#A63D40",
        "#1B6CA8",
        "#6D2E77",
        "#2F7D4F",
        "#C05B17",
    ],
};

export function paletteColors(config) {
    const custom = config.palette_colors;
    return (
        (custom && custom.length ? custom : PALETTES[config.color_palette]) ||
        PALETTES.default
    );
}

export function getPaletteColor(config, index) {
    const colors = paletteColors(config);
    return colors[index % colors.length];
}

function luminance(hex) {
    // YIQ perceived brightness in the 0-255 range.
    const value = hex.replace("#", "");
    if (value.length !== 6) {
        return 255;
    }
    const red = parseInt(value.slice(0, 2), 16);
    const green = parseInt(value.slice(2, 4), 16);
    const blue = parseInt(value.slice(4, 6), 16);
    return 0.299 * red + 0.587 * green + 0.114 * blue;
}

export function darkestPaletteColor(config) {
    return paletteColors(config).reduce((darkest, color) =>
        luminance(color) < luminance(darkest) ? color : darkest
    );
}

export function contrastFontColor(hex) {
    return luminance(hex) > 140 ? "#111827" : "#FFFFFF";
}

/**
 * Pick the palette color with the strongest luminance contrast against
 * ``againstHex``. Falls back to black/white when no swatch is different
 * enough (e.g. mono-luminance pastel palettes).
 */
export function contrastingPaletteColor(config, againstHex, minDelta = 80) {
    const against = luminance(againstHex);
    let best = null;
    let bestDelta = -1;
    for (const color of paletteColors(config)) {
        const delta = Math.abs(luminance(color) - against);
        if (delta > bestDelta) {
            best = color;
            bestDelta = delta;
        }
    }
    if (best && bestDelta >= minDelta) {
        return best;
    }
    return contrastFontColor(againstHex);
}

export function hexToRGBA(hex, alpha) {
    const value = hex.replace("#", "");
    if (value.length !== 6) {
        return hex;
    }
    const red = parseInt(value.slice(0, 2), 16);
    const green = parseInt(value.slice(2, 4), 16);
    const blue = parseInt(value.slice(4, 6), 16);
    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

export function formatNumber(value, numberStyle) {
    const number = value || 0;
    if (numberStyle === "exact") {
        return formatFloat(number, {digits: [16, Number.isInteger(number) ? 0 : 2]});
    }
    return humanNumber(number, {decimals: 2, minDigits: 1});
}

export function formatItemValue(value, config, currency) {
    const formatted = formatNumber(value, config.number_style);
    const unit = config.unit || {type: "none"};
    if (unit.type === "monetary" && currency) {
        return currency.position === "before"
            ? `${currency.symbol} ${formatted}`
            : `${formatted} ${currency.symbol}`;
    }
    if (unit.type === "custom" && unit.symbol) {
        return `${formatted} ${unit.symbol}`;
    }
    return formatted;
}

export const DEFAULT_ITEM_SIZE = {
    tile: {w: 3, h: 2},
    kpi: {w: 3, h: 2},
    gauge: {w: 3, h: 3},
    bullet: {w: 4, h: 4},
    funnel: {w: 4, h: 5},
    map: {w: 6, h: 6},
    list: {w: 6, h: 5},
    chart: {w: 6, h: 5},
};

export function defaultItemSize(itemType) {
    return DEFAULT_ITEM_SIZE[itemType] || DEFAULT_ITEM_SIZE.chart;
}
