// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {DashboardItemCard} from "@boardkit_dashboard/dashboard/dashboard_item_card";
import {patch} from "@web/core/utils/patch";

patch(DashboardItemCard, {
    props: {
        ...DashboardItemCard.props,
        aiEnabled: {type: Boolean, optional: true},
        onExplainAi: {type: Function, optional: true},
    },
});

patch(DashboardItemCard.prototype, {
    onExplainAi() {
        if (this.props.onExplainAi) {
            this.props.onExplainAi(this.config.id);
        }
    },
});
