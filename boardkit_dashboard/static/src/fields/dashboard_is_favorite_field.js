// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {booleanFavoriteField} from "@web/views/fields/boolean_favorite/boolean_favorite_field";
import {registry} from "@web/core/registry";

/**
 * Like project.project's favorite widget: Dashboard Users have no write ACL,
 * so the default boolean_favorite becomes readonly and ignores clicks.
 * Only honour an explicit readonly attribute from the view arch.
 */
export const dashboardIsFavoriteField = {
    ...booleanFavoriteField,
    extractProps: (fieldsInfo, dynamicInfo) => ({
        ...booleanFavoriteField.extractProps(fieldsInfo, dynamicInfo),
        readonly: Boolean(fieldsInfo.attrs.readonly),
    }),
};

registry
    .category("fields")
    .add("boardkit_dashboard_is_favorite", dashboardIsFavoriteField);
