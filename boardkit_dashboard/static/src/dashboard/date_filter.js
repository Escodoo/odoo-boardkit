// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {Component, useState} from "@odoo/owl";
import {DateTimeInput} from "@web/core/datetime/datetime_input";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";

export class DateFilter extends Component {
    static template = "boardkit_dashboard.DateFilter";
    static components = {Dropdown, DropdownItem, DateTimeInput};
    static props = {
        presets: Array,
        value: Object,
        onChange: Function,
    };

    setup() {
        this.state = useState({
            customFrom: this.props.value.from || false,
            customTo: this.props.value.to || false,
        });
    }

    get currentLabel() {
        const preset = this.props.value.preset || "none";
        const entry = this.props.presets.find(([key]) => key === preset);
        return entry ? entry[1] : preset;
    }

    get isCustom() {
        return this.props.value.preset === "custom";
    }

    onPresetSelected(preset) {
        if (preset === "custom") {
            this.props.onChange({
                preset,
                from: this.state.customFrom,
                to: this.state.customTo,
                apply: Boolean(this.state.customFrom && this.state.customTo),
            });
        } else {
            this.props.onChange({preset, from: false, to: false, apply: true});
        }
    }

    onApplyCustom() {
        if (!this.state.customFrom || !this.state.customTo) {
            return;
        }
        this.props.onChange({
            preset: "custom",
            from: this.state.customFrom,
            to: this.state.customTo,
            apply: true,
        });
    }
}
