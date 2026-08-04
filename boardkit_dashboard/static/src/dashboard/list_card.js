// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {Component} from "@odoo/owl";
import {formatNumber} from "./utils";

export class ListCard extends Component {
    static template = "boardkit_dashboard.ListCard";
    static props = {
        config: Object,
        data: Object,
        onOpenRecord: {type: Function, optional: true},
        onOpenGroup: {type: Function, optional: true},
        onPageChange: {type: Function, optional: true},
    };

    get pageStart() {
        return this.props.data.total ? this.props.data.offset + 1 : 0;
    }

    get pageEnd() {
        return Math.min(
            this.props.data.offset + this.props.data.rows.length,
            this.props.data.total
        );
    }

    formatCell(value, column) {
        if (["integer", "float", "monetary"].includes(column.type)) {
            return formatNumber(value, this.props.config.number_style);
        }
        if (column.type === "boolean") {
            return value ? "✓" : "";
        }
        return value === false || value === null || value === undefined
            ? ""
            : String(value);
    }

    isNumeric(column) {
        return ["integer", "float", "monetary"].includes(column.type);
    }

    isSortable(column) {
        return Boolean(column.sortable) && !this.props.data.grouped;
    }

    isSorted(column) {
        return this.isSortable(column) && this.props.data.sort_field === column.name;
    }

    onHeaderClicked(column) {
        if (!this.isSortable(column)) {
            return;
        }
        const sortDir =
            this.isSorted(column) && this.props.data.sort_dir === "asc"
                ? "desc"
                : "asc";
        this.props.onPageChange?.({
            offset: 0,
            sort_field: column.name,
            sort_dir: sortDir,
        });
    }

    _withSort(params) {
        const {sort_field, sort_dir} = this.props.data;
        if (sort_field) {
            return {...params, sort_field, sort_dir};
        }
        return params;
    }

    onRowClicked(row) {
        if (!this.props.config.show_records) {
            return;
        }
        if (this.props.data.grouped) {
            this.props.onOpenGroup?.(row.domain);
        } else {
            this.props.onOpenRecord?.(row.id);
        }
    }

    onPreviousPage() {
        const offset = Math.max(
            0,
            this.props.data.offset - this.props.config.page_size
        );
        this.props.onPageChange?.(this._withSort({offset}));
    }

    onNextPage() {
        const offset = this.props.data.offset + this.props.config.page_size;
        if (offset < this.props.data.total) {
            this.props.onPageChange?.(this._withSort({offset}));
        }
    }
}
