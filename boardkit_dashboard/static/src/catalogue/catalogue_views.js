// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {onWillStart, useState} from "@odoo/owl";
import {FileInput} from "@web/core/file_input/file_input";
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {ListController} from "@web/views/list/list_controller";
import {_t} from "@web/core/l10n/translation";
import {kanbanView} from "@web/views/kanban/kanban_view";
import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {user} from "@web/core/user";

export const IMPORT_ROUTE = "/boardkit_dashboard/import";

/**
 * Adds the dashboard file uploader to the catalogue control panel, so
 * importing is a toolbar action on the board list instead of a separate
 * configuration screen.
 */
export const DashboardImport = (Controller) =>
    class extends Controller {
        static components = {...Controller.components, FileInput};

        setup() {
            super.setup();
            this.action = useService("action");
            this.notification = useService("notification");
            this.importRoute = IMPORT_ROUTE;
            this.importState = useState({isManager: false});
            onWillStart(async () => {
                this.importState.isManager = await user.hasGroup(
                    "boardkit_dashboard.group_dashboard_manager"
                );
            });
        }

        async onDashboardImported(result) {
            const dashboardIds = result.dashboard_ids || [];
            if (!dashboardIds.length) {
                this.notification.add(_t("No dashboard was found in this file."), {
                    type: "warning",
                });
                return;
            }
            this.notification.add(
                _t("%s dashboard(s) imported.", dashboardIds.length),
                {type: "success"}
            );
            // A single board opens its settings so the manager can review and
            // publish it; bulk imports just refresh the catalogue.
            if (dashboardIds.length === 1) {
                await this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "boardkit.dashboard",
                    res_id: dashboardIds[0],
                    views: [[false, "form"]],
                });
                return;
            }
            await this.model.root.load();
            this.render(true);
        }

        async onFromTemplate() {
            await this.action.doAction(
                "boardkit_dashboard.boardkit_dashboard_template_wizard_action",
                {
                    onClose: async () => {
                        if (this.model?.root?.load) {
                            await this.model.root.load();
                            this.render(true);
                        }
                    },
                }
            );
        }
    };

export class DashboardCatalogueKanbanController extends DashboardImport(
    KanbanController
) {
    static template = "boardkit_dashboard.CatalogueKanbanView";
}

export class DashboardCatalogueListController extends DashboardImport(ListController) {
    static template = "boardkit_dashboard.CatalogueListView";
}

registry.category("views").add("boardkit_dashboard_catalogue_kanban", {
    ...kanbanView,
    Controller: DashboardCatalogueKanbanController,
});

registry.category("views").add("boardkit_dashboard_catalogue_list", {
    ...listView,
    Controller: DashboardCatalogueListController,
});
