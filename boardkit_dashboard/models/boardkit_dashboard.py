# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import copy
import json
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from markupsafe import Markup, escape

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL
from odoo.tools.safe_eval import safe_eval

from ..tools.date_ranges import DATE_RANGE_PRESETS, get_date_range
from ..tools.palettes import PRESET_PALETTE_COLORS, PRESET_PALETTE_SELECTION
from .boardkit_dashboard_palette import HEX_COLOR_PATTERN

KANBAN_SUMMARY_LIMIT = 4
KANBAN_PALETTE_LIMIT = 5

USER_GROUP = "boardkit_dashboard.group_dashboard_user"
MANAGER_GROUP = "boardkit_dashboard.group_dashboard_manager"
DEFAULT_MENU_WEB_ICON = "boardkit_dashboard,static/description/icon.png"

# Field types a user can pick when building an ad-hoc filter from the UI.
CUSTOM_FILTER_FIELD_TYPES = (
    "char",
    "text",
    "selection",
    "many2one",
    "boolean",
    "integer",
    "float",
    "monetary",
    "date",
    "datetime",
)

# Caps for the runtime filter state stored per user, so a crafted payload
# cannot grow the personal row without bounds.
SAVED_CUSTOM_FILTERS_LIMIT = 20
SAVED_FILTER_IDS_LIMIT = 50
SAVED_FILTER_STRING_LIMIT = 256


class BoardkitDashboard(models.Model):
    _name = "boardkit.dashboard"
    _description = "Boardkit Dashboard"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    description = fields.Char(
        translate=True,
        help="Short summary shown on the dashboard catalogue.",
    )
    tag_ids = fields.Many2many(
        comodel_name="boardkit.dashboard.tag",
        relation="boardkit_dashboard_tag_rel",
        column1="dashboard_id",
        column2="tag_id",
        string="Tags",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        help="Leave empty to share the dashboard across companies. "
        "Company-specific dashboards cannot have a menu entry.",
    )
    item_ids = fields.One2many(
        comodel_name="boardkit.dashboard.item",
        inverse_name="dashboard_id",
        string="Items",
        copy=False,
    )
    filter_ids = fields.One2many(
        comodel_name="boardkit.dashboard.filter",
        inverse_name="dashboard_id",
        string="Predefined Filters",
        copy=True,
    )
    date_filter = fields.Selection(
        selection=DATE_RANGE_PRESETS,
        string="Default Date Filter",
        required=True,
        default="none",
    )
    date_from = fields.Datetime(string="Start Date")
    date_to = fields.Datetime(string="End Date")
    refresh_interval = fields.Selection(
        selection=[
            ("0", "Disabled"),
            ("15", "15 seconds"),
            ("30", "30 seconds"),
            ("60", "1 minute"),
            ("120", "2 minutes"),
            ("300", "5 minutes"),
            ("600", "10 minutes"),
            ("900", "15 minutes"),
            ("1800", "30 minutes"),
            ("3600", "1 hour"),
        ],
        default="0",
        required=True,
        help="Automatically reload the dashboard data at this interval.",
    )
    default_color_palette = fields.Selection(
        selection=PRESET_PALETTE_SELECTION + [("custom", "Custom")],
        string="Default Palette",
        help="Applied to items whose color palette is set to Dashboard "
        "Default. Leave empty to use the Odoo preset.",
    )
    default_palette_id = fields.Many2one(
        comodel_name="boardkit.dashboard.palette",
        string="Default Custom Palette",
        ondelete="restrict",
    )
    layout_json = fields.Text(
        string="Default Layout",
        default="{}",
        copy=False,
        help="Grid position of the items, managed from the dashboard view.",
    )
    layout_ids = fields.One2many(
        comodel_name="boardkit.dashboard.layout",
        inverse_name="dashboard_id",
        string="Personal Layouts",
        copy=False,
    )
    # Menu integration
    menu_name = fields.Char(
        help="Label of the generated menu entry. Defaults to the dashboard name."
    )
    menu_parent_id = fields.Many2one(
        comodel_name="ir.ui.menu",
        string="Parent Menu",
        domain="['|', ('parent_id', '=', False), ('action', '=', False)]",
        help="Optional parent menu for a generated entry. The menu is only "
        "created while the dashboard is published. Not available when the "
        "dashboard is restricted to a specific company.",
    )
    menu_as_app = fields.Boolean(
        string="Show as App",
        help="Expose the published dashboard as a top-level app in the main "
        "apps menu, using the Boardkit Dashboards module icon. The app is "
        "only visible while the dashboard is published. Not available when "
        "the dashboard is restricted to a specific company.",
    )
    published = fields.Boolean(
        default=False,
        copy=False,
        help="When set, users with access can open the dashboard from the "
        "catalogue (and from its menu entry, if configured). Leave "
        "unchecked while building or reviewing the dashboard.",
    )
    menu_sequence = fields.Integer(default=10)
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Allowed Groups",
        help="Restrict the dashboard and its menu entry to these groups. "
        "Members of these groups can open the dashboard without the "
        "Dashboard User right (useful for menus under other apps). "
        "Leave empty to allow every Dashboard User only. The Boardkit "
        "Dashboards app and configuration still require Dashboard User "
        "or Manager.",
    )
    menu_id = fields.Many2one(comodel_name="ir.ui.menu", readonly=True, copy=False)
    client_action_id = fields.Many2one(
        comodel_name="ir.actions.client", readonly=True, copy=False
    )
    item_count = fields.Integer(compute="_compute_kanban_summary")
    item_type_summary = fields.Char(compute="_compute_kanban_summary")
    model_summary = fields.Char(compute="_compute_kanban_summary")
    item_type_badge_html = fields.Html(
        compute="_compute_kanban_summary", sanitize=False
    )
    palette_strip_html = fields.Html(
        compute="_compute_palette_strip_html", sanitize=False
    )
    favorite_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="boardkit_dashboard_favorite_user_rel",
        column1="dashboard_id",
        column2="user_id",
        string="Favorited by",
        copy=False,
    )
    is_favorite = fields.Boolean(
        compute="_compute_is_favorite",
        readonly=False,
        search="_search_is_favorite",
        compute_sudo=True,
        string="Favorite",
    )

    @api.model
    def _search_is_favorite(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise NotImplementedError(_("Operation not supported"))
        return [
            (
                "favorite_user_ids",
                "in" if (operator == "=") == value else "not in",
                self.env.uid,
            )
        ]

    @api.depends("favorite_user_ids")
    def _compute_is_favorite(self):
        for dashboard in self:
            dashboard.is_favorite = self.env.user in dashboard.favorite_user_ids

    def _set_favorite_user_ids(self, is_favorite):
        # Users can favorite dashboards they can read even without write ACL.
        self.check_access("read")
        self_sudo = self.sudo()
        if is_favorite:
            self_sudo.favorite_user_ids = [Command.link(self.env.uid)]
        else:
            self_sudo.favorite_user_ids = [Command.unlink(self.env.uid)]
        # web_save re-reads is_favorite in the same request; drop the stale cache.
        self.invalidate_recordset(["is_favorite"])

    def _order_field_to_sql(self, alias, field_name, direction, nulls, query):
        if field_name == "is_favorite":
            sql_field = SQL(
                "%s IN ("
                "SELECT dashboard_id FROM boardkit_dashboard_favorite_user_rel "
                "WHERE user_id = %s"
                ")",
                SQL.identifier(alias, "id"),
                self.env.uid,
            )
            return SQL("%s %s %s", sql_field, direction, nulls)
        return super()._order_field_to_sql(alias, field_name, direction, nulls, query)

    @api.depends(
        "item_ids",
        "item_ids.item_type",
        "item_ids.model_id",
        "item_ids.model_id.model",
    )
    def _compute_kanban_summary(self):
        type_labels = dict(
            self.env["boardkit.dashboard.item"]._fields["item_type"].selection
        )
        for rec in self:
            items = rec.item_ids
            rec.item_count = len(items)
            type_keys = list(dict.fromkeys(items.mapped("item_type")))
            model_names = list(
                dict.fromkeys(filter(None, items.mapped("model_id.model")))
            )
            rec.item_type_summary = rec._format_summary_list(
                [type_labels.get(key, key) for key in type_keys]
            )
            rec.model_summary = rec._format_summary_list(model_names)
            shown_types = type_keys[:KANBAN_SUMMARY_LIMIT]
            extra_types = len(type_keys) - len(shown_types)
            badges = [
                Markup(
                    '<span class="badge text-bg-light '
                    'o_boardkit_dashboard_kanban_type">{}</span>'
                ).format(escape(type_labels.get(key, key)))
                for key in shown_types
            ]
            if extra_types > 0:
                badges.append(
                    Markup(
                        '<span class="badge text-bg-secondary '
                        'o_boardkit_dashboard_kanban_type">+{}</span>'
                    ).format(extra_types)
                )
            rec.item_type_badge_html = (
                Markup(
                    '<div class="o_boardkit_dashboard_kanban_types">{}</div>'
                ).format(Markup("").join(badges))
                if badges
                else False
            )

    def init(self):
        """One-shot: mark existing menu-backed dashboards as published.

        Before publishing was a separate flag, visibility was inferred from
        menu_id. Preserve that for boards that already have a menu entry.
        """
        icp = self.env["ir.config_parameter"].sudo()
        key = "boardkit_dashboard.published_from_menu_migrated"
        if icp.get_param(key):
            return
        self.env.cr.execute(
            """
            UPDATE boardkit_dashboard
               SET published = TRUE
             WHERE menu_id IS NOT NULL
               AND COALESCE(published, FALSE) = FALSE
            """
        )
        icp.set_param(key, "1")

    @api.depends(
        "default_color_palette",
        "default_palette_id",
        "default_palette_id.color_ids",
        "default_palette_id.color_ids.color",
        "default_palette_id.color_ids.sequence",
    )
    def _compute_palette_strip_html(self):
        for rec in self:
            colors = rec._get_kanban_palette_colors()[:KANBAN_PALETTE_LIMIT]
            if not colors:
                rec.palette_strip_html = False
                continue
            segments = Markup("").join(
                Markup(
                    '<span class="o_boardkit_dashboard_kanban_strip_segment" '
                    'style="background-color: {};"></span>'
                ).format(escape(color))
                for color in colors
            )
            rec.palette_strip_html = Markup(
                '<div class="o_boardkit_dashboard_kanban_strip">{}</div>'
            ).format(segments)

    @api.model
    def _format_summary_list(self, values):
        if not values:
            return False
        shown = values[:KANBAN_SUMMARY_LIMIT]
        text = ", ".join(shown)
        extra = len(values) - len(shown)
        if extra > 0:
            text = f"{text} (+{extra})"
        return text

    def _get_kanban_palette_colors(self):
        self.ensure_one()
        if self.default_color_palette == "custom" and self.default_palette_id:
            return self.default_palette_id._color_list()
        if self.default_color_palette in PRESET_PALETTE_COLORS:
            return list(PRESET_PALETTE_COLORS[self.default_color_palette])
        return list(PRESET_PALETTE_COLORS["default"])

    @api.constrains("date_filter", "date_from", "date_to")
    def _check_custom_dates(self):
        for rec in self:
            if rec.date_filter != "custom":
                continue
            if not rec.date_from or not rec.date_to:
                raise ValidationError(
                    _("Custom date filter requires both start and end dates.")
                )
            if rec.date_from > rec.date_to:
                raise ValidationError(_("Start date must be before end date."))

    @api.constrains("default_color_palette", "default_palette_id")
    def _check_default_palette(self):
        for rec in self:
            if rec.default_color_palette == "custom" and not rec.default_palette_id:
                raise ValidationError(
                    _(
                        "Select a default custom palette on dashboard "
                        "%(name)s or pick a preset color palette.",
                        name=rec.name,
                    )
                )

    @api.constrains("company_id", "menu_parent_id", "menu_as_app")
    def _check_company_bound_has_no_menu(self):
        for rec in self:
            if rec.company_id and (rec.menu_parent_id or rec.menu_as_app):
                raise ValidationError(
                    _(
                        "Company-specific dashboards cannot have a menu "
                        "entry. Clear the company or the Parent Menu / "
                        "Show as App fields on %(name)s.",
                        name=rec.name,
                    )
                )

    @api.onchange("company_id")
    def _onchange_company_id_clear_menu(self):
        if self.company_id:
            self.menu_parent_id = False
            self.menu_as_app = False

    @api.onchange("menu_as_app")
    def _onchange_menu_as_app(self):
        if self.menu_as_app:
            self.menu_parent_id = False

    @api.onchange("menu_parent_id")
    def _onchange_menu_parent_id(self):
        if self.menu_parent_id:
            self.menu_as_app = False

    # ------------------------------------------------------------------
    # CRUD / menu lifecycle
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.pop("is_favorite", False):
                vals["favorite_user_ids"] = [self.env.uid]
            if vals.get("company_id"):
                vals["menu_parent_id"] = False
                vals["menu_as_app"] = False
            prepared.append(vals)
        records = super().create(prepared)
        records._sync_menu_entry()
        return records

    def write(self, vals):
        vals = dict(vals)
        # Intercept before super() so read-only users can toggle favorites
        # without needing write ACL on the dashboard.
        if "is_favorite" in vals:
            self._set_favorite_user_ids(vals.pop("is_favorite"))
        if not vals:
            return True
        if vals.get("date_filter") and vals["date_filter"] != "custom":
            vals.update({"date_from": False, "date_to": False})
        # Binding a dashboard to a company drops the menu entry: menus are
        # not company-aware and would stay visible for every allowed company.
        if vals.get("company_id"):
            vals["menu_parent_id"] = False
            vals["menu_as_app"] = False
        res = super().write(vals)
        menu_fields = {
            "name",
            "active",
            "published",
            "menu_name",
            "menu_parent_id",
            "menu_as_app",
            "menu_sequence",
            "group_ids",
        }
        if menu_fields & set(vals):
            self._sync_menu_entry()
        return res

    def unlink(self):
        self._remove_menu_entry()
        return super().unlink()

    def copy(self, default=None):
        self.ensure_one()
        default = dict(
            default or {},
            name=_("%s (copy)", self.name),
            menu_parent_id=False,
            menu_as_app=False,
            published=False,
        )
        new = super().copy(default)
        layout = self._parse_json_dict(self.layout_json)
        new_layout = {}
        for item in self.item_ids:
            new_item = item.copy({"dashboard_id": new.id})
            if str(item.id) in layout:
                new_layout[str(new_item.id)] = layout[str(item.id)]
        new.layout_json = json.dumps(new_layout)
        return new

    def action_publish(self):
        self.write({"published": True})
        return True

    def action_unpublish(self):
        self.write({"published": False})
        return True

    def _sync_menu_entry(self):
        for rec in self:
            if not rec.published or not (rec.menu_as_app or rec.menu_parent_id):
                rec._remove_menu_entry()
                continue
            if not rec.client_action_id:
                rec.client_action_id = (
                    self.env["ir.actions.client"]
                    .sudo()
                    .create(
                        {
                            "name": rec.name,
                            "tag": "boardkit_dashboard",
                            "params": {"dashboard_id": rec.id},
                        }
                    )
                )
            else:
                rec.client_action_id.sudo().name = rec.name
            # Menus pointing to client actions are not filtered by model
            # access, so an empty groups_id would expose the menu to every
            # internal user. Fall back to the dashboard user group.
            menu_groups = rec.group_ids or self.env.ref(USER_GROUP)
            menu_vals = {
                "name": rec.menu_name or rec.name,
                "parent_id": False if rec.menu_as_app else rec.menu_parent_id.id,
                "sequence": rec.menu_sequence,
                "action": f"ir.actions.client,{rec.client_action_id.id}",
                "groups_id": [(6, 0, menu_groups.ids)],
                "active": rec.active,
                # Root apps use the module icon; submenu entries have none.
                "web_icon": (DEFAULT_MENU_WEB_ICON if rec.menu_as_app else False),
            }
            if rec.menu_id:
                rec.menu_id.sudo().write(menu_vals)
            else:
                rec.menu_id = self.env["ir.ui.menu"].sudo().create(menu_vals)

    def _remove_menu_entry(self):
        self.menu_id.sudo().unlink()
        self.client_action_id.sudo().unlink()

    def action_open_dashboard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "boardkit_dashboard",
            "name": self.name,
            "params": {"dashboard_id": self.id},
        }

    def action_open_settings(self):
        """Open the dashboard configuration form."""
        self.ensure_one()
        return self.get_formview_action()

    # ------------------------------------------------------------------
    # Client API
    # ------------------------------------------------------------------

    @api.model
    def get_dashboard_data(self, dashboard_id):
        """Return the configuration payload used by the client action.

        Returns ``False`` when the dashboard is missing or not readable in
        the current company/group context (e.g. landing page / deep link),
        so the client can show the empty state instead of an AccessError.
        """
        dashboard = self.browse(dashboard_id)
        try:
            dashboard.check_access("read")
        except AccessError:
            return False
        if not dashboard.exists():
            return False
        is_manager = self.env.user.has_group(MANAGER_GROUP)
        personal = dashboard._get_personal_layout()
        # An empty personal layout means the user only saved filters, so the
        # default layout still applies and there is nothing to reset.
        personal_layout = self._parse_json_dict(personal.layout_json)
        layout = personal_layout or self._parse_json_dict(dashboard.layout_json)
        currency = self.env.company.currency_id
        presets = dashboard._fields["date_filter"]._description_selection(self.env)
        return {
            "id": dashboard.id,
            "name": dashboard.name,
            "is_favorite": dashboard.is_favorite,
            "is_manager": is_manager,
            "refresh_interval": int(dashboard.refresh_interval or "0"),
            "date_filter": dashboard.date_filter,
            "date_from": fields.Datetime.to_string(dashboard.date_from) or False,
            "date_to": fields.Datetime.to_string(dashboard.date_to) or False,
            "date_presets": presets,
            "layout": layout,
            "has_personal_layout": bool(personal_layout),
            "saved_filters": self._parse_json_dict(personal.filters_json),
            "has_saved_filters": bool(self._parse_json_dict(personal.filters_json)),
            "currency": {"symbol": currency.symbol, "position": currency.position},
            "items": [item._get_config() for item in dashboard.item_ids],
            "filters": [
                {
                    "id": f.id,
                    "name": f.name,
                    "model": f.model_name,
                    "model_label": f.model_id.name,
                    "default_enabled": f.default_enabled,
                }
                for f in dashboard.filter_ids
            ],
        }

    def toggle_favorite(self):
        """Toggle the current user's favorite flag; return the new value.

        Available to any user who can read the dashboard (no write ACL needed).
        """
        self.ensure_one()
        new_value = self.env.user not in self.favorite_user_ids
        self._set_favorite_user_ids(new_value)
        return new_value

    @api.model
    def save_layout(self, dashboard_id, layout, personal=True):
        dashboard = self.browse(dashboard_id)
        dashboard.check_access("read")
        layout_json = json.dumps(layout or {})
        if not personal:
            if not self.env.user.has_group(MANAGER_GROUP):
                raise AccessError(
                    _("Only dashboard managers can change the default layout.")
                )
            dashboard.sudo().layout_json = layout_json
            return True
        dashboard._store_personal({"layout_json": layout_json})
        return True

    @api.model
    def save_filters(self, dashboard_id, filters):
        """Remember the filters this user applied on the dashboard."""
        dashboard = self.browse(dashboard_id)
        dashboard.check_access("read")
        state = self._normalize_saved_filters(filters)
        dashboard._store_personal({"filters_json": json.dumps(state)})
        return True

    @api.model
    def reset_personal_filters(self, dashboard_id):
        dashboard = self.browse(dashboard_id)
        dashboard.check_access("read")
        dashboard._drop_personal("filters_json")
        return True

    @api.model
    def get_custom_filter_fields(self, model_name):
        """Return the fields a user can pick to build an ad-hoc filter."""
        if model_name not in self.env:
            return []
        fields_data = self.env[model_name].fields_get(
            attributes=["string", "type", "searchable", "selection"]
        )
        result = []
        for name, description in fields_data.items():
            if name == "id" or not description.get("searchable"):
                continue
            if description["type"] not in CUSTOM_FILTER_FIELD_TYPES:
                continue
            entry = {
                "name": name,
                "label": description["string"],
                "type": description["type"],
            }
            if description["type"] == "selection":
                entry["selection"] = description.get("selection") or []
            result.append(entry)
        result.sort(key=lambda entry: entry["label"] or "")
        return result

    @api.model
    def reset_personal_layout(self, dashboard_id):
        dashboard = self.browse(dashboard_id)
        dashboard.check_access("read")
        dashboard._drop_personal("layout_json")
        return True

    def _get_personal_layout(self):
        self.ensure_one()
        return self.env["boardkit.dashboard.layout"].search(
            [("dashboard_id", "=", self.id), ("user_id", "=", self.env.uid)], limit=1
        )

    def _store_personal(self, values):
        """Write ``values`` on the personal row, creating it when needed."""
        self.ensure_one()
        record = self._get_personal_layout()
        if record:
            record.write(values)
        else:
            self.env["boardkit.dashboard.layout"].create(
                dict(values, dashboard_id=self.id)
            )

    def _drop_personal(self, field_name):
        """Clear one stored preference, dropping the row once it is empty."""
        self.ensure_one()
        record = self._get_personal_layout()
        if not record:
            return
        record[field_name] = "{}"
        if not self._parse_json_dict(record.layout_json) and not self._parse_json_dict(
            record.filters_json
        ):
            record.unlink()

    @api.model
    def _normalize_saved_filters(self, filters):
        """Keep only the runtime filter state the client may store.

        The values are replayed as regular filter parameters later, so they
        go through the usual domain validation; this only guards the shape
        and the size of what lands in the personal row.
        """
        if not isinstance(filters, dict):
            return {}
        preset = filters.get("date_preset")
        if not isinstance(preset, str) or preset not in dict(DATE_RANGE_PRESETS):
            preset = "none"
        state = {
            "date_preset": preset,
            "date_from": self._clip_saved_value(filters.get("date_from")) or False,
            "date_to": self._clip_saved_value(filters.get("date_to")) or False,
            "filter_ids": [
                value
                for value in filters.get("filter_ids") or []
                if isinstance(value, int) and not isinstance(value, bool)
            ][:SAVED_FILTER_IDS_LIMIT],
            "custom_filters": [],
        }
        entries = filters.get("custom_filters") or []
        for entry in entries[:SAVED_CUSTOM_FILTERS_LIMIT]:
            if not isinstance(entry, dict):
                continue
            spec = {
                key: self._clip_saved_value(entry.get(key))
                for key in ("model", "field", "operator", "label", "modelLabel")
            }
            if not (spec["model"] and spec["field"] and spec["operator"]):
                continue
            spec["value"] = self._clip_saved_value(entry.get("value"))
            state["custom_filters"].append(spec)
        return state

    @staticmethod
    def _clip_saved_value(value):
        if isinstance(value, str):
            return value[:SAVED_FILTER_STRING_LIMIT]
        if isinstance(value, bool | int | float):
            return value
        return ""

    @staticmethod
    def _parse_json_dict(layout_json):
        try:
            layout = json.loads(layout_json or "{}")
        except ValueError:
            layout = {}
        return layout if isinstance(layout, dict) else {}

    # ------------------------------------------------------------------
    # Export / import
    # ------------------------------------------------------------------

    def export_config(self):
        """Serialize the dashboards into a portable JSON structure."""
        payload = {"version": 1, "dashboards": []}
        for dashboard in self:
            layout = self._parse_json_dict(dashboard.layout_json)
            items = []
            for index, item in enumerate(dashboard.item_ids):
                item_data = item._export_config()
                item_data["layout"] = layout.get(str(item.id))
                item_data["index"] = index
                items.append(item_data)
            palettes = dashboard._export_palettes()
            payload["dashboards"].append(
                {
                    "name": dashboard.name,
                    "description": dashboard.description or False,
                    "tags": dashboard.tag_ids.mapped("name"),
                    "date_filter": dashboard.date_filter
                    if dashboard.date_filter != "custom"
                    else "none",
                    "refresh_interval": dashboard.refresh_interval,
                    "menu_name": dashboard.menu_name or False,
                    "menu_sequence": dashboard.menu_sequence,
                    "default_color_palette": dashboard.default_color_palette or False,
                    "default_palette": dashboard.default_palette_id.name or False,
                    "palettes": [
                        {"name": palette.name, "colors": palette._color_list()}
                        for palette in palettes
                    ],
                    "items": items,
                    "filters": [
                        {
                            "name": f.name,
                            "sequence": f.sequence,
                            "model": f.model_name,
                            "domain": f.domain,
                            "default_enabled": f.default_enabled,
                        }
                        for f in dashboard.filter_ids
                    ],
                }
            )
        return payload

    def _export_palettes(self):
        """Custom palettes referenced by this dashboard, for portable exports."""
        self.ensure_one()
        return self.item_ids.palette_id | self.default_palette_id

    @api.model
    def _import_palettes(self, palettes_data):
        """Recreate the exported custom palettes that are missing by name."""
        palette_model = self.env["boardkit.dashboard.palette"]
        for palette_data in palettes_data or []:
            if not isinstance(palette_data, dict):
                continue
            name = palette_data.get("name")
            colors = [
                color
                for color in palette_data.get("colors") or []
                if isinstance(color, str) and HEX_COLOR_PATTERN.match(color)
            ]
            if not name or not colors:
                continue
            if palette_model.search_count([("name", "=", name)], limit=1):
                continue
            palette_model.create(
                {
                    "name": name,
                    "color_ids": [
                        (0, 0, {"sequence": (index + 1) * 10, "color": color})
                        for index, color in enumerate(colors)
                    ],
                }
            )

    @api.model
    def _import_tags(self, tag_names):
        """Return tags for the given names, creating any that are missing."""
        tag_model = self.env["boardkit.dashboard.tag"]
        tags = tag_model.browse()
        for name in tag_names or []:
            if not isinstance(name, str) or not name.strip():
                continue
            name = name.strip()
            tag = tag_model.search([("name", "=", name)], limit=1)
            if not tag:
                tag = tag_model.create({"name": name})
            tags |= tag
        return tags

    @api.model
    def create_from_template(self, template_id, name=None):
        """Create unpublished dashboards from a curated template payload.

        Reuses ``import_config`` so templates stay on the same contract as
        JSON export/import. When ``name`` is set, it overrides the first
        dashboard name in the payload.
        """
        template = self.env["boardkit.dashboard.template"].browse(template_id)
        if not template.exists():
            raise ValidationError(_("The selected template no longer exists."))
        template.ensure_one()
        payload = copy.deepcopy(template.get_payload())
        if not isinstance(payload, dict) or "dashboards" not in payload:
            raise ValidationError(
                _("Template %(name)s has an invalid payload.", name=template.name)
            )
        if name:
            for data in payload.get("dashboards") or []:
                if isinstance(data, dict):
                    data["name"] = name
                    break
        return self.import_config(payload)

    @api.model
    def import_config(self, payload):
        """Create dashboards from a structure produced by ``export_config``.

        Imported boards land unpublished and without a menu entry, so the
        manager reviews them before making them visible.
        """
        if not isinstance(payload, dict) or "dashboards" not in payload:
            raise ValidationError(_("The file is not a valid dashboard export."))
        dashboards = self.browse()
        item_model = self.env["boardkit.dashboard.item"]
        for data in payload["dashboards"]:
            self._import_palettes(data.get("palettes"))
            default_key = data.get("default_color_palette") or False
            default_palette = self.env["boardkit.dashboard.palette"]
            if data.get("default_palette"):
                default_palette = default_palette.search(
                    [("name", "=", data["default_palette"])], limit=1
                )
            if default_key == "custom" and not default_palette:
                # The palette could not be resolved on this database.
                default_key = False
            tags = self._import_tags(data.get("tags"))
            dashboard = self.create(
                {
                    "name": data.get("name") or _("Imported Dashboard"),
                    "description": data.get("description") or False,
                    "tag_ids": [(6, 0, tags.ids)],
                    "date_filter": data.get("date_filter") or "none",
                    "refresh_interval": data.get("refresh_interval") or "0",
                    "menu_name": data.get("menu_name") or False,
                    "menu_sequence": data.get("menu_sequence") or 10,
                    "default_color_palette": default_key,
                    "default_palette_id": default_palette.id
                    if default_key == "custom"
                    else False,
                }
            )
            layout = {}
            for item_data in data.get("items", []):
                vals = item_model._import_prepare_vals(item_data, dashboard.id)
                if not vals:
                    continue
                item = item_model.create(vals)
                if item_data.get("layout"):
                    layout[str(item.id)] = item_data["layout"]
            dashboard.layout_json = json.dumps(layout)
            for filter_data in data.get("filters", []):
                model = self.env["ir.model"]._get(filter_data.get("model") or "")
                if not model:
                    continue
                self.env["boardkit.dashboard.filter"].create(
                    {
                        "dashboard_id": dashboard.id,
                        "name": filter_data.get("name") or _("Filter"),
                        "sequence": filter_data.get("sequence") or 10,
                        "model_id": model.id,
                        "domain": filter_data.get("domain") or "[]",
                        "default_enabled": filter_data.get("default_enabled") or False,
                    }
                )
            dashboards |= dashboard
        return dashboards.ids

    # ------------------------------------------------------------------
    # Domain / date helpers shared by items and filters
    # ------------------------------------------------------------------

    def _domain_eval_context(self):
        return {
            "uid": self.env.uid,
            "user": self.env.user,
            "company_id": self.env.company.id,
            "company_ids": self.env.companies.ids,
            "context_today": fields.Date.context_today,
            "datetime": datetime,
            "timedelta": timedelta,
            "relativedelta": relativedelta,
        }

    def _eval_domain(self, domain_str, model_name=None):
        """Evaluate a stored domain string and optionally validate it."""
        if not domain_str:
            return []
        domain = safe_eval(domain_str, self._domain_eval_context())
        if not isinstance(domain, list):
            raise ValidationError(_("A domain must be a list, got: %s", domain_str))
        if model_name:
            # Let the ORM validate field names and operators.
            self.env[model_name].with_user(self.env.user).search_count(domain, limit=1)
        return domain

    @api.model
    def _get_date_range(self, preset, date_from=None, date_to=None):
        """Resolve a preset (or custom bounds) into naive UTC datetimes."""
        if preset == "custom":
            start = fields.Datetime.to_datetime(date_from) if date_from else None
            end = fields.Datetime.to_datetime(date_to) if date_to else None
            # Custom ranges are inclusive: extend the end bound to the next second.
            return (start, end + timedelta(seconds=1) if end else None)
        lang = self.env["res.lang"]._lang_get(self.env.user.lang)
        week_start = int(lang.week_start or 1)
        tz_name = self.env.user.tz or self.env.context.get("tz") or "UTC"
        return get_date_range(preset, tz_name=tz_name, week_start=week_start)
