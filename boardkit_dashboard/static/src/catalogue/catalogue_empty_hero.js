// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {Component, onWillStart, useState} from "@odoo/owl";
import {FileInput} from "@web/core/file_input/file_input";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {user} from "@web/core/user";

const IMPORT_ROUTE = "/boardkit_dashboard/import";

const FEATURED_ICONS = {
    my_day: "fa-sun-o",
    crm_pipeline: "fa-filter",
    contacts_overview: "fa-address-book-o",
    partner_starter: "fa-rocket",
};

/**
 * Empty catalogue hero with curated templates for first-run managers.
 */
export class CatalogueEmptyHero extends Component {
    static template = "boardkit_dashboard.CatalogueEmptyHero";
    static components = {FileInput};
    static props = {
        onFromTemplate: {type: Function, optional: true},
        onCreated: {type: Function, optional: true},
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.importRoute = IMPORT_ROUTE;
        this.state = useState({
            isManager: false,
            featured: [],
            creatingId: null,
        });
        onWillStart(async () => {
            this.state.isManager = await user.hasGroup(
                "boardkit_dashboard.group_dashboard_manager"
            );
            if (!this.state.isManager) {
                return;
            }
            this.state.featured = await this.orm.call(
                "boardkit.dashboard.template",
                "get_featured_for_catalogue",
                []
            );
        });
    }

    templateIcon(template) {
        return FEATURED_ICONS[template.key] || "fa-th-large";
    }

    async onNew() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "boardkit.dashboard",
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onFromTemplate() {
        if (this.props.onFromTemplate) {
            await this.props.onFromTemplate();
            return;
        }
        await this.action.doAction(
            "boardkit_dashboard.boardkit_dashboard_template_wizard_action"
        );
    }

    async onDashboardImported(result) {
        const dashboardIds = result.dashboard_ids || [];
        if (!dashboardIds.length) {
            this.notification.add(_t("No dashboard was found in this file."), {
                type: "warning",
            });
            return;
        }
        this.notification.add(_t("%s dashboard(s) imported.", dashboardIds.length), {
            type: "success",
        });
        if (this.props.onCreated) {
            await this.props.onCreated(dashboardIds);
        }
        if (dashboardIds.length === 1) {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "boardkit.dashboard",
                res_id: dashboardIds[0],
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    async onFeaturedClick(template) {
        if (!template?.id || this.state.creatingId) {
            return;
        }
        this.state.creatingId = template.id;
        try {
            const dashboardIds = await this.orm.call(
                "boardkit.dashboard",
                "create_from_template",
                [template.id]
            );
            if (!dashboardIds?.length) {
                this.notification.add(
                    _t("No dashboard was created from this template."),
                    {
                        type: "warning",
                    }
                );
                return;
            }
            if (this.props.onCreated) {
                await this.props.onCreated(dashboardIds);
            }
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "boardkit.dashboard",
                res_id: dashboardIds[0],
                views: [[false, "form"]],
                target: "current",
            });
        } finally {
            this.state.creatingId = null;
        }
    }
}
