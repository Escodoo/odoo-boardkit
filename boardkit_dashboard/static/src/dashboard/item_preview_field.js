// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {Component} from "@odoo/owl";
import {DashboardItemCard} from "./dashboard_item_card";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {standardFieldProps} from "@web/views/fields/standard_field_props";

function noop() {
    // Preview cards keep record-list / edit actions disabled.
}

export class DashboardItemPreviewField extends Component {
    static template = "boardkit_dashboard.ItemPreviewField";
    static components = {DashboardItemCard};
    static props = {...standardFieldProps};

    setup() {
        this.orm = useService("orm");
        this.noop = noop;
    }

    get payload() {
        return this.props.record.data[this.props.name] || null;
    }

    // Chart-to-chart drill for the form live preview. Uses a config snapshot
    // so unsaved drill lines (virtual ids) still work. Opening the record
    // list remains a noop in preview.
    async fetchDrillData(level, domain) {
        const config = this.payload?.config;
        if (!config) {
            return null;
        }
        return this.orm.call("boardkit.dashboard.item", "get_preview_drill_data", [
            {
                item_id: config.id || 0,
                model: config.model,
                aggregation: config.aggregation || "count",
                measure_field_ids: config.measure_field_ids || [],
                drill_levels: config.drill_levels || [],
            },
            level.index,
            domain,
        ]);
    }
}

export const dashboardItemPreviewField = {
    component: DashboardItemPreviewField,
    displayName: _t("Dashboard Item Preview"),
    supportedTypes: ["json"],
};

registry
    .category("fields")
    .add("boardkit_dashboard_item_preview", dashboardItemPreviewField);
