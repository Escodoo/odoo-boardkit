// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {Component, useState} from "@odoo/owl";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {_t} from "@web/core/l10n/translation";
import {useDropdownState} from "@web/core/dropdown/dropdown_hooks";
import {useService} from "@web/core/utils/hooks";

const TEXT_OPERATORS = [
    ["ilike", _t("contains")],
    ["not ilike", _t("does not contain")],
    ["=", _t("is")],
    ["!=", _t("is not")],
];
const NUMBER_OPERATORS = [
    ["=", "="],
    ["!=", "\u2260"],
    [">", ">"],
    [">=", "\u2265"],
    ["<", "<"],
    ["<=", "\u2264"],
];
const DATE_OPERATORS = [
    [">=", _t("on or after")],
    ["<=", _t("on or before")],
];

// Mirrors CUSTOM_FILTER_OPERATORS on the backend.
export const OPERATORS_BY_TYPE = {
    char: TEXT_OPERATORS,
    text: TEXT_OPERATORS,
    many2one: TEXT_OPERATORS.slice(0, 2),
    selection: [
        ["=", _t("is")],
        ["!=", _t("is not")],
    ],
    boolean: [
        ["true", _t("is true")],
        ["false", _t("is false")],
    ],
    integer: NUMBER_OPERATORS,
    float: NUMBER_OPERATORS,
    monetary: NUMBER_OPERATORS,
    date: [["=", _t("is")], ...DATE_OPERATORS],
    datetime: DATE_OPERATORS,
};

export class CustomFilters extends Component {
    static template = "boardkit_dashboard.CustomFilters";
    static components = {Dropdown};
    static props = {
        models: Array,
        filters: Array,
        onAdd: Function,
        onRemove: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.dropdown = useDropdownState();
        this.fieldsCache = {};
        this.state = useState({
            model: "",
            fields: [],
            fieldName: "",
            operator: "",
            value: "",
        });
    }

    get selectedField() {
        return this.state.fields.find((field) => field.name === this.state.fieldName);
    }

    get operators() {
        const field = this.selectedField;
        return field ? OPERATORS_BY_TYPE[field.type] || [] : [];
    }

    get valueInputType() {
        const field = this.selectedField;
        if (!field) {
            return "text";
        }
        if (["integer", "float", "monetary"].includes(field.type)) {
            return "number";
        }
        if (["date", "datetime"].includes(field.type)) {
            return "date";
        }
        return "text";
    }

    get needsValue() {
        const field = this.selectedField;
        return Boolean(field) && field.type !== "boolean";
    }

    get canApply() {
        if (!this.selectedField || !this.state.operator) {
            return false;
        }
        return !this.needsValue || this.state.value !== "";
    }

    async onOpened() {
        if (!this.state.model && this.props.models.length) {
            await this.selectModel(this.props.models[0].model);
        }
    }

    async selectModel(model) {
        this.state.model = model;
        this.state.fieldName = "";
        this.state.operator = "";
        this.state.value = "";
        if (!this.fieldsCache[model]) {
            this.fieldsCache[model] = await this.orm.call(
                "boardkit.dashboard",
                "get_custom_filter_fields",
                [model]
            );
        }
        this.state.fields = this.fieldsCache[model];
    }

    onModelChanged(ev) {
        this.selectModel(ev.target.value);
    }

    onFieldChanged(ev) {
        this.state.fieldName = ev.target.value;
        this.state.value = "";
        this.state.operator = this.operators.length ? this.operators[0][0] : "";
    }

    onValueKeydown(ev) {
        if (ev.key === "Enter") {
            ev.stopPropagation();
            this.apply();
        }
    }

    apply() {
        if (!this.canApply) {
            return;
        }
        const field = this.selectedField;
        let operator = this.state.operator;
        let value = this.state.value;
        let valueLabel = value;
        if (field.type === "boolean") {
            value = operator === "true";
            operator = "=";
            valueLabel = "";
        } else if (["integer", "float", "monetary"].includes(field.type)) {
            value = Number(value);
            valueLabel = String(value);
        } else if (field.type === "selection") {
            const option = (field.selection || []).find(([key]) => key === value);
            valueLabel = option ? option[1] : value;
        }
        const operatorEntry = this.operators.find(
            ([key]) => key === this.state.operator
        );
        const modelEntry = this.props.models.find(
            (model) => model.model === this.state.model
        );
        this.props.onAdd({
            model: this.state.model,
            field: field.name,
            operator,
            value,
            label:
                `${field.label} ${operatorEntry ? operatorEntry[1] : operator}` +
                (valueLabel === "" ? "" : ` ${valueLabel}`),
            modelLabel: modelEntry ? modelEntry.label : this.state.model,
        });
        this.state.value = "";
        this.dropdown.close();
    }
}
