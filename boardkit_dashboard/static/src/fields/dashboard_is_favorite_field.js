/** @odoo-module **/
// Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import {BooleanFavoriteField} from "@web/views/fields/boolean_favorite/boolean_favorite_field";
import {registry} from "@web/core/registry";

/**
 * Dashboard Users have no write ACL on boards. On Odoo 16 the standard
 * boolean_favorite already toggles and saves regardless of the readonly
 * record mode, so the dedicated widget only keeps the 18.0 view arch valid.
 */
registry.category("fields").add("boardkit_dashboard_is_favorite", BooleanFavoriteField);
