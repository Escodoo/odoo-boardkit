# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import copy
from datetime import date, datetime, time, timedelta

import babel.dates
import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import babel_locale_parse, format_date, format_datetime, get_lang
from odoo.tools.safe_eval import safe_eval

from ..tools import data_cache
from ..tools.date_ranges import DATE_RANGE_PRESETS
from ..tools.palettes import PRESET_PALETTE_SELECTION

# Default upper bound for the process-local item data cache TTL (seconds).
# Overridable with ir.config_parameter boardkit_dashboard.data_cache_max_ttl.
DEFAULT_DATA_CACHE_MAX_TTL = 60

# Soft cap for unpaginated list exports (CSV/XLSX) to protect memory/time.
EXPORT_MAX_ROWS = 65000

# Framework namespaces that only add noise to the data source selector.
# Abstract models are already ruled out by the access_ids term below, since
# they never own ir.model.access records.
TECHNICAL_MODEL_PREFIXES = (
    "ir.",
    "base_import.",
    "web_editor.",
    "web_tour.",
    "boardkit.dashboard",
)

ITEM_MODEL_DOMAIN = repr(
    [("transient", "=", False), ("access_ids", "!=", False)]
    + [("model", "not like", f"{prefix}%") for prefix in TECHNICAL_MODEL_PREFIXES]
)

GROUPABLE_FIELD_DOMAIN = (
    "[('model_id', '=', model_id), ('name', '!=', 'id'), ('store', '=', True),"
    " ('ttype', 'not in', ['binary', 'one2many', 'many2many', 'html'])]"
)

# Group By domain: charts and lists use the source model; a regions map with a
# relation field uses the related model, so partner_id.country_id can be picked.
GROUP_BY_FIELD_DOMAIN = (
    "[('model_id', '=', group_by_model_id), ('name', '!=', 'id'),"
    " ('store', '=', True),"
    " ('ttype', 'not in', ['binary', 'one2many', 'many2many', 'html'])]"
)

NUMERIC_FIELD_DOMAIN = (
    "[('model_id', '=', model_id), ('name', '!=', 'id'), ('store', '=', True),"
    " ('ttype', 'in', ['integer', 'float', 'monetary'])]"
)

NUMERIC_FIELD_2_DOMAIN = (
    "[('model_id', '=', model_2_id), ('name', '!=', 'id'), ('store', '=', True),"
    " ('ttype', 'in', ['integer', 'float', 'monetary'])]"
)

# Coordinate domain: the map may read its float fields from a related model.
FLOAT_FIELD_DOMAIN = (
    "[('model_id', '=', map_field_model_id), ('name', '!=', 'id'),"
    " ('store', '=', True), ('ttype', '=', 'float')]"
)

MAP_RELATION_FIELD_DOMAIN = (
    "[('model_id', '=', model_id), ('ttype', '=', 'many2one'), ('store', '=', True)]"
)

# Sort By domain: list uses the source model; funnel many2one group-by uses
# the related model so stage.sequence (and similar) can be selected.
SORT_FIELD_DOMAIN = (
    "[('model_id', '=', sort_model_id), ('name', '!=', 'id'),"
    " ('store', '=', True),"
    " ('ttype', 'not in', ['binary', 'one2many', 'many2many', 'html'])]"
)

# Soft cap for the records scanned by a point map, to protect payload size.
MAP_MAX_RECORDS = 1000

# Decimal places used to merge records sharing the same coordinates (~1 m).
MAP_COORD_PRECISION = 5

# Operators a user may combine with each field type in ad-hoc filters.
CUSTOM_FILTER_OPERATORS = {
    "char": ("ilike", "not ilike", "=", "!="),
    "text": ("ilike", "not ilike", "=", "!="),
    "many2one": ("ilike", "not ilike"),
    "selection": ("=", "!="),
    "boolean": ("=",),
    "integer": ("=", "!=", ">", ">=", "<", "<="),
    "float": ("=", "!=", ">", ">=", "<", "<="),
    "monetary": ("=", "!=", ">", ">=", "<", "<="),
    "date": ("=", ">=", "<=", ">", "<"),
    "datetime": (">=", "<=", ">", "<"),
}

CHART_TYPES = (
    "bar",
    "bar_horizontal",
    "line",
    "area",
    "pie",
    "doughnut",
    "polar",
    "radar",
)

# Cartesian charts that can overlay a previous-period series.
PREVIOUS_PERIOD_CHART_TYPES = (
    "bar",
    "bar_horizontal",
    "line",
    "area",
)

DATE_GRANULARITIES = [
    ("hour", "Hour"),
    ("day", "Day"),
    ("week", "Week"),
    ("month", "Month"),
    ("quarter", "Quarter"),
    ("year", "Year"),
]

GRANULARITY_INTERVAL = {
    "hour": relativedelta(hours=1),
    "day": relativedelta(days=1),
    "week": timedelta(days=7),
    "month": relativedelta(months=1),
    "quarter": relativedelta(months=3),
    "year": relativedelta(years=1),
}

GRANULARITY_LABEL_FORMAT = {
    "hour": "dd MMM HH:00",
    "day": "dd MMM yyyy",
    "week": "'W'w yyyy",
    "month": "MMM yyyy",
    "quarter": "QQQ yyyy",
    "year": "yyyy",
}

# Every configuration field involved in _get_config() or _get_data(), so the
# form preview recomputes whenever the user tweaks the item.
PREVIEW_DEPENDS = (
    "action_id",
    "aggregation",
    "aggregation_2",
    "background_color",
    "background_style",
    "boolean_false_label",
    "boolean_true_label",
    "chart_sort",
    "color_palette",
    "compare_previous_period",
    "dashboard_id",
    "dashboard_id.default_color_palette",
    "dashboard_id.default_palette_id",
    "date_field_2_id",
    "date_field_id",
    "date_filter",
    "date_from",
    "date_to",
    "description",
    "domain",
    "domain_2",
    "font_color",
    "gauge_max",
    "group_by_field_id",
    "group_by_granularity",
    "icon",
    "item_type",
    "kpi_display",
    "kpi_mode",
    "legend_visible",
    "list_column_ids.field_id",
    "list_column_ids.sequence",
    "latitude_field_id",
    "list_type",
    "longitude_field_id",
    "drill_level_ids.group_by_field_id",
    "drill_level_ids.chart_type",
    "drill_level_ids.sequence",
    "map_focus_country_id",
    "map_mode",
    "map_relation_field_id",
    "measure_field_2_id",
    "measure_field_id",
    "measure_ids.field_id",
    "measure_ids.sequence",
    "measure_x_field_id",
    "measure_y_field_id",
    "model_2_id",
    "model_id",
    "name",
    "number_style",
    "page_size",
    "palette_id",
    "palette_id.color_ids.color",
    "palette_id.color_ids.sequence",
    "record_limit",
    "show_average_line",
    "show_records",
    "show_trend_line",
    "sort_dir",
    "sort_field_id",
    "stacked",
    "subgroup_by_field_id",
    "subgroup_by_granularity",
    "target_enabled",
    "target_value",
    "unit_type",
    "unit_symbol",
)


class BoardkitDashboardItem(models.Model):
    _name = "boardkit.dashboard.item"
    _description = "Boardkit Dashboard Item"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    dashboard_id = fields.Many2one(
        comodel_name="boardkit.dashboard",
        required=True,
        ondelete="cascade",
        index=True,
    )
    item_type = fields.Selection(
        selection=[
            ("tile", "Tile"),
            ("kpi", "KPI"),
            ("bar", "Bar Chart"),
            ("bar_horizontal", "Horizontal Bar Chart"),
            ("line", "Line Chart"),
            ("area", "Area Chart"),
            ("pie", "Pie Chart"),
            ("doughnut", "Doughnut Chart"),
            ("polar", "Polar Area Chart"),
            ("radar", "Radar Chart"),
            ("scatter", "Scatter Chart"),
            ("funnel", "Funnel Chart"),
            ("gauge", "Gauge"),
            ("bullet", "Bullet Chart"),
            ("map", "Map"),
            ("list", "List"),
        ],
        required=True,
        default="tile",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=ITEM_MODEL_DOMAIN,
        help="Data source used to compute the item values.",
    )
    model_name = fields.Char(related="model_id.model", string="Model Name")
    domain = fields.Char(default="[]", help="Filter applied to the source records.")
    date_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Date Field",
        domain="[('model_id', '=', model_id), ('store', '=', True),"
        " ('ttype', 'in', ['date', 'datetime'])]",
        help="Field used by the dashboard date filter and the item date filter.",
    )
    date_filter = fields.Selection(
        selection=DATE_RANGE_PRESETS,
        string="Item Date Filter",
        required=True,
        default="none",
        help="Applied when the dashboard date filter is set to All Time.",
    )
    date_from = fields.Datetime(string="Start Date")
    date_to = fields.Datetime(string="End Date")

    # Grouping and measures
    group_by_model_id = fields.Many2one(
        comodel_name="ir.model",
        compute="_compute_group_by_model_id",
        help="Technical model that owns the Group By field.",
    )
    group_by_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Group By",
        domain=GROUP_BY_FIELD_DOMAIN,
    )
    group_by_ttype = fields.Selection(
        related="group_by_field_id.ttype", string="Group By Type"
    )
    group_by_granularity = fields.Selection(
        selection=DATE_GRANULARITIES,
        default="month",
        help="Used when the Group By field is a date or datetime field.",
    )
    subgroup_by_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Sub Group By",
        domain=GROUPABLE_FIELD_DOMAIN,
        help="Second dimension, rendered as one dataset per value."
        " Only the first measure is used.",
    )
    subgroup_by_ttype = fields.Selection(
        related="subgroup_by_field_id.ttype", string="Sub Group By Type"
    )
    subgroup_by_granularity = fields.Selection(
        selection=DATE_GRANULARITIES, default="month"
    )
    boolean_true_label = fields.Char(
        string="Label when True",
        translate=True,
        help="Legend label when grouping by a boolean field that is True. "
        "Leave empty to use Yes.",
    )
    boolean_false_label = fields.Char(
        string="Label when False",
        translate=True,
        help="Legend label when grouping by a boolean field that is False. "
        "Leave empty to use No.",
    )
    aggregation = fields.Selection(
        selection=[("count", "Count"), ("sum", "Sum"), ("avg", "Average")],
        required=True,
        default="count",
    )
    measure_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Measure Field",
        domain=NUMERIC_FIELD_DOMAIN,
        help="Numeric field aggregated on tiles and KPIs.",
    )
    measure_ids = fields.One2many(
        comodel_name="boardkit.dashboard.item.measure",
        inverse_name="item_id",
        string="Measures",
        copy=True,
        help="Aggregated fields, in the order they are plotted.",
    )
    measure_x_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Measure X",
        domain=NUMERIC_FIELD_DOMAIN,
    )
    measure_y_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Measure Y",
        domain=NUMERIC_FIELD_DOMAIN,
    )
    record_limit = fields.Integer(
        help="Maximum number of groups displayed. 0 means no limit.",
    )
    chart_sort = fields.Selection(
        selection=[
            ("default", "Default Order"),
            ("label_asc", "Label Ascending"),
            ("label_desc", "Label Descending"),
            ("value_asc", "Value Ascending"),
            ("value_desc", "Value Descending"),
        ],
        default="default",
        required=True,
    )
    stacked = fields.Boolean()
    legend_visible = fields.Boolean(default=True)
    show_average_line = fields.Boolean(
        string="Average Line",
        help="Draw a horizontal line at the average of the primary series.",
    )
    show_trend_line = fields.Boolean(
        string="Trend Line",
        help="Draw a linear trend line over the primary series.",
    )

    # KPI
    kpi_mode = fields.Selection(
        selection=[("target", "Against Target"), ("comparison", "Two Data Sources")],
        default="target",
        required=True,
    )
    kpi_display = fields.Selection(
        selection=[
            ("value", "Both Values"),
            ("sum", "Sum"),
            ("ratio", "Ratio"),
            ("percent", "Percentage"),
        ],
        default="value",
        required=True,
    )
    compare_previous_period = fields.Boolean(
        string="Compare to Previous Period",
        help="Also compute the value over the previous equivalent period. "
        "Tiles and KPIs show a delta badge; bar, horizontal bar, line and "
        "area charts overlay a dashed previous series. Requires a Date Field "
        "and an active date range.",
    )
    model_2_id = fields.Many2one(
        comodel_name="ir.model",
        string="Second Model",
        ondelete="cascade",
        domain=ITEM_MODEL_DOMAIN,
    )
    model_2_name = fields.Char(related="model_2_id.model", string="Second Model Name")
    domain_2 = fields.Char(string="Second Domain", default="[]")
    date_field_2_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Second Date Field",
        domain="[('model_id', '=', model_2_id), ('store', '=', True),"
        " ('ttype', 'in', ['date', 'datetime'])]",
    )
    aggregation_2 = fields.Selection(
        selection=[("count", "Count"), ("sum", "Sum"), ("avg", "Average")],
        string="Second Aggregation",
        default="count",
    )
    measure_field_2_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Second Measure Field",
        domain=NUMERIC_FIELD_2_DOMAIN,
    )

    # Target / gauge
    target_enabled = fields.Boolean(string="Enable Target")
    target_value = fields.Float()
    gauge_max = fields.Float(
        string="Gauge Maximum",
        help="Upper bound of the gauge scale. When empty, a value is derived "
        "from the current value and target.",
    )

    # Map
    map_mode = fields.Selection(
        selection=[
            ("regions", "Regions (Countries)"),
            ("points", "Points (Latitude / Longitude)"),
        ],
        default="regions",
        required=True,
        help="Regions choropleth by country, or one marker per record using "
        "configurable latitude and longitude fields.",
    )
    map_relation_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Coordinates From",
        domain=MAP_RELATION_FIELD_DOMAIN,
        help="Optional many2one on the source model. When set, the map reads "
        "its latitude, longitude and country fields from the related model, "
        "for example partner_id to plot leads on the contact coordinates.",
    )
    map_field_model_id = fields.Many2one(
        comodel_name="ir.model",
        compute="_compute_map_field_model_id",
        help="Technical model that owns the map coordinate fields.",
    )
    latitude_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Latitude Field",
        domain=FLOAT_FIELD_DOMAIN,
        help="Float field used as the marker latitude in Points map mode.",
    )
    longitude_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Longitude Field",
        domain=FLOAT_FIELD_DOMAIN,
        help="Float field used as the marker longitude in Points map mode.",
    )
    map_focus_country_id = fields.Many2one(
        comodel_name="res.country",
        string="Focus Country",
        ondelete="set null",
        help="Optional country used to crop the map outline and zoom the "
        "projection. Applies to both Regions and Points modes.",
    )

    # List
    list_type = fields.Selection(
        selection=[("plain", "Plain"), ("grouped", "Grouped")],
        default="plain",
        required=True,
    )
    list_column_ids = fields.One2many(
        comodel_name="boardkit.dashboard.item.column",
        inverse_name="item_id",
        string="List Columns",
        copy=True,
    )
    page_size = fields.Integer(default=10)
    sort_model_id = fields.Many2one(
        comodel_name="ir.model",
        compute="_compute_sort_model_id",
        help="Technical model that owns the Sort By field.",
    )
    sort_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Sort By",
        domain=SORT_FIELD_DOMAIN,
        help="Field used to order plain list rows, or funnel stages when set. "
        "On funnel charts it overrides Chart Sort; for a many2one group by, "
        "choose a field on the related model (for example stage.sequence).",
    )
    sort_dir = fields.Selection(
        selection=[("asc", "Ascending"), ("desc", "Descending")],
        default="asc",
        required=True,
    )

    # Appearance
    icon = fields.Char(
        default="fa-bar-chart", help="Font Awesome icon class, e.g. fa-line-chart."
    )
    background_style = fields.Selection(
        selection=[("palette", "From Palette"), ("manual", "Manual")],
        default="palette",
        required=True,
        help="From Palette themes tiles and KPIs with the darkest palette "
        "color and an automatic contrasting font.",
    )
    background_color = fields.Char(default="#FFFFFF")
    font_color = fields.Char(default="#111827")
    color_palette = fields.Selection(
        selection=[("dashboard", "Dashboard Default")]
        + PRESET_PALETTE_SELECTION
        + [("custom", "Custom")],
        default="dashboard",
        required=True,
        help="Dashboard Default follows the palette configured on the "
        "dashboard, so items restyle together when it changes.",
    )
    palette_id = fields.Many2one(
        comodel_name="boardkit.dashboard.palette",
        string="Custom Palette",
        ondelete="restrict",
        help="Palette applied when the color palette is set to Custom.",
    )
    number_style = fields.Selection(
        selection=[("compact", "Compact"), ("exact", "Exact")],
        default="compact",
        required=True,
    )
    unit_type = fields.Selection(
        selection=[("none", "None"), ("monetary", "Currency"), ("custom", "Custom")],
        default="none",
        required=True,
    )
    unit_symbol = fields.Char(size=8)

    # Interactions
    show_records = fields.Boolean(
        default=True, help="Open the underlying records when clicking on the item."
    )
    action_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        string="Custom Action",
        domain="[('res_model', '=', model_name)]",
        ondelete="set null",
        help="Open this action instead of the default record list.",
    )
    drill_level_ids = fields.One2many(
        comodel_name="boardkit.dashboard.item.drill",
        inverse_name="item_id",
        string="Drill Down Levels",
        copy=True,
        help="Extra grouping levels applied when the user clicks a section. "
        "The last level opens the underlying records.",
    )

    # Live preview rendered in the item form view.
    preview_json = fields.Json(
        compute="_compute_preview_json",
        help="Configuration and data payload rendered by the form preview.",
    )

    @api.constrains("domain", "domain_2")
    def _check_domains(self):
        for rec in self:
            try:
                rec.dashboard_id._eval_domain(rec.domain, rec.model_name)
                if rec.model_2_name:
                    rec.dashboard_id._eval_domain(rec.domain_2, rec.model_2_name)
            except ValidationError:
                raise
            except Exception as error:
                raise ValidationError(
                    _(
                        "Invalid domain on item %(name)s: %(error)s",
                        name=rec.name,
                        error=error,
                    )
                ) from error

    @api.depends(
        "model_id",
        "item_type",
        "group_by_field_id",
        "group_by_field_id.ttype",
        "group_by_field_id.relation",
    )
    def _compute_sort_model_id(self):
        IrModel = self.env["ir.model"]
        for rec in self:
            group = rec.group_by_field_id
            if (
                rec.item_type == "funnel"
                and group
                and group.ttype == "many2one"
                and group.relation
            ):
                rec.sort_model_id = IrModel._get(group.relation)
            else:
                rec.sort_model_id = rec.model_id

    @api.depends(
        "model_id",
        "item_type",
        "map_relation_field_id",
        "map_relation_field_id.relation",
    )
    def _compute_map_field_model_id(self):
        IrModel = self.env["ir.model"]
        for rec in self:
            relation = rec.map_relation_field_id
            if rec.item_type == "map" and relation and relation.relation:
                rec.map_field_model_id = IrModel._get(relation.relation)
            else:
                rec.map_field_model_id = rec.model_id

    @api.depends("model_id", "item_type", "map_mode", "map_field_model_id")
    def _compute_group_by_model_id(self):
        for rec in self:
            if rec.item_type == "map" and rec.map_mode == "regions":
                rec.group_by_model_id = rec.map_field_model_id
            else:
                rec.group_by_model_id = rec.model_id

    @api.constrains("date_filter", "date_from", "date_to")
    def _check_custom_dates(self):
        for rec in self:
            if (
                rec.date_filter == "custom"
                and rec.date_from
                and rec.date_to
                and rec.date_from > rec.date_to
            ):
                raise ValidationError(_("Start date must be before end date."))

    @api.constrains(
        "model_id",
        "model_2_id",
        "date_field_id",
        "date_field_2_id",
        "group_by_field_id",
        "subgroup_by_field_id",
        "measure_field_id",
        "measure_x_field_id",
        "measure_y_field_id",
        "measure_field_2_id",
        "sort_field_id",
        "latitude_field_id",
        "longitude_field_id",
        "map_relation_field_id",
    )
    def _check_fields_belong_to_model(self):
        for rec in self:
            rec._assert_fields_model(
                rec.model_id,
                [
                    rec.date_field_id,
                    rec.subgroup_by_field_id,
                    rec.measure_field_id,
                    rec.measure_x_field_id,
                    rec.measure_y_field_id,
                    rec.map_relation_field_id,
                ],
            )
            # Coordinates and the regions country may live on the related model.
            rec._assert_fields_model(
                rec.map_field_model_id,
                [rec.latitude_field_id, rec.longitude_field_id],
            )
            if rec.group_by_field_id:
                rec._assert_fields_model(rec.group_by_model_id, [rec.group_by_field_id])
            if rec.sort_field_id:
                rec._assert_fields_model(rec.sort_model_id, [rec.sort_field_id])
            if rec.model_2_id:
                rec._assert_fields_model(
                    rec.model_2_id,
                    [rec.date_field_2_id, rec.measure_field_2_id],
                )

    @api.constrains(
        "item_type",
        "map_mode",
        "latitude_field_id",
        "longitude_field_id",
        "group_by_field_id",
        "map_relation_field_id",
    )
    def _check_map_configuration(self):
        for rec in self:
            if rec.item_type != "map":
                continue
            relation = rec.map_relation_field_id
            if relation and (relation.ttype != "many2one" or not relation.store):
                raise ValidationError(
                    _(
                        "Coordinates From must be a stored many2one field on "
                        "item %(name)s.",
                        name=rec.name,
                    )
                )
            if rec.map_mode == "points":
                if not rec.latitude_field_id or not rec.longitude_field_id:
                    raise ValidationError(
                        _(
                            "Map points mode requires Latitude and Longitude "
                            "fields on item %(name)s.",
                            name=rec.name,
                        )
                    )
                for field, label in (
                    (rec.latitude_field_id, _("Latitude")),
                    (rec.longitude_field_id, _("Longitude")),
                ):
                    if field.ttype != "float":
                        raise ValidationError(
                            _(
                                "%(label)s field must be a float on item %(name)s.",
                                label=label,
                                name=rec.name,
                            )
                        )
            elif rec.group_by_field_id and (
                rec.group_by_field_id.ttype != "many2one"
                or rec.group_by_field_id.relation != "res.country"
            ):
                raise ValidationError(
                    _(
                        "Map regions mode requires a Group By field pointing "
                        "to Countries on item %(name)s.",
                        name=rec.name,
                    )
                )

    @api.constrains("color_palette", "palette_id")
    def _check_custom_palette(self):
        for rec in self:
            if rec.color_palette == "custom" and not rec.palette_id:
                raise ValidationError(
                    _(
                        "Select a custom palette on item %(name)s or pick a "
                        "preset color palette.",
                        name=rec.name,
                    )
                )

    def _assert_fields_model(self, model, field_records):
        """Raise if any ir.model.fields row does not belong to ``model``."""
        self.ensure_one()
        for field in field_records:
            if field and field.model_id != model:
                raise ValidationError(
                    _(
                        "Field %(field)s does not belong to model %(model)s "
                        "on item %(name)s.",
                        field=field.name,
                        model=model.model,
                        name=self.name,
                    )
                )

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.update(
            {
                "domain": "[]",
                "date_field_id": False,
                "group_by_field_id": False,
                "subgroup_by_field_id": False,
                "measure_field_id": False,
                "measure_ids": [(5, 0, 0)],
                "measure_x_field_id": False,
                "measure_y_field_id": False,
                "list_column_ids": [(5, 0, 0)],
                "drill_level_ids": [(5, 0, 0)],
                "sort_field_id": False,
                "action_id": False,
                "map_relation_field_id": False,
                "latitude_field_id": False,
                "longitude_field_id": False,
            }
        )

    @api.onchange("map_relation_field_id", "map_mode", "item_type")
    def _onchange_clear_incompatible_map_fields(self):
        # Coordinates and the regions country follow the resolved map model.
        if self.map_field_model_id:
            for field_name in ("latitude_field_id", "longitude_field_id"):
                field = self[field_name]
                if field and field.model_id != self.map_field_model_id:
                    self[field_name] = False
        if (
            self.group_by_field_id
            and self.group_by_model_id
            and self.group_by_field_id.model_id != self.group_by_model_id
        ):
            self.group_by_field_id = False

    @api.onchange("group_by_field_id", "item_type")
    def _onchange_clear_incompatible_sort_field(self):
        # Sort By may target the related group-by model on funnels.
        if (
            self.sort_field_id
            and self.sort_model_id
            and self.sort_field_id.model_id != self.sort_model_id
        ):
            self.sort_field_id = False

    @api.onchange("model_2_id")
    def _onchange_model_2_id(self):
        self.update(
            {
                "domain_2": "[]",
                "date_field_2_id": False,
                "measure_field_2_id": False,
            }
        )

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if not default or "name" not in default:
            for item, vals in zip(self, vals_list, strict=True):
                vals["name"] = _("%s (copy)", item.name)
        return vals_list

    # ------------------------------------------------------------------
    # Client configuration payload
    # ------------------------------------------------------------------

    def _resolved_palette(self):
        """Return the (palette_key, custom_colors) pair used by the renderer.

        Dashboard Default resolves through the dashboard, so items follow it
        dynamically. Custom palettes resolve to their hex color list; presets
        keep their key and let the client read the colors from its own
        definitions.
        """
        self.ensure_one()
        key, palette = self.color_palette, self.palette_id
        if key == "dashboard":
            key = self.dashboard_id.default_color_palette or "default"
            palette = self.dashboard_id.default_palette_id
        if key == "custom":
            colors = palette._color_list() if palette else []
            return ("custom", colors) if colors else ("default", False)
        return key, False

    def _get_config(self):
        self.ensure_one()
        palette_key, palette_colors = self._resolved_palette()
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description or "",
            "type": self.item_type,
            "model": self.model_name,
            "model_label": self.model_id.name,
            "icon": self.icon or "fa-bar-chart",
            "background_style": self.background_style,
            "background_color": self.background_color or "#FFFFFF",
            "font_color": self.font_color or "#111827",
            "color_palette": palette_key,
            "palette_colors": palette_colors,
            "number_style": self.number_style,
            "legend_visible": self.legend_visible,
            "stacked": self.stacked,
            "show_average_line": self.show_average_line,
            "show_trend_line": self.show_trend_line,
            "page_size": self.page_size or 10,
            "show_records": self.show_records,
            "target_enabled": self.target_enabled,
            "target_value": self.target_value,
            "aggregation": self.aggregation,
            # Used by the form live preview to re-aggregate unsaved drill levels.
            "measure_field_ids": (
                self._ordered_measure_fields() or self.measure_field_id
            ).ids,
            "unit": {"type": self.unit_type, "symbol": self.unit_symbol or ""},
            "compare_previous_period": self.compare_previous_period,
            "kpi": {
                "mode": self.kpi_mode,
                "display": self.kpi_display,
                "compare_previous_period": self.compare_previous_period,
            },
            "map_mode": self.map_mode,
            "map_focus_country": (self.map_focus_country_id.code or "").upper()
            or False,
            "drill_levels": [
                {
                    # Virtual record ids (NewId) are not JSON serializable.
                    "id": getattr(level.id, "origin", level.id) or 0,
                    "index": index,
                    "label": level.group_by_field_id.field_description,
                    "type": level.chart_type,
                    "group_by_field_id": level.group_by_field_id.id,
                    "group_by_granularity": level.group_by_granularity or False,
                    "chart_sort": level.chart_sort,
                    "record_limit": level.record_limit or 0,
                }
                for index, level in enumerate(self.drill_level_ids)
            ],
        }

    # ------------------------------------------------------------------
    # Form preview
    # ------------------------------------------------------------------

    @api.depends(*PREVIEW_DEPENDS)
    def _compute_preview_json(self):
        for item in self:
            item.preview_json = item._get_preview_payload()

    def _get_preview_payload(self):
        """Config and data payload computed on the (possibly virtual) record.

        The compute runs through the onchange machinery, so the preview
        reflects the form values before they are saved. Data errors are
        rendered inside the preview card instead of breaking the form.
        """
        self.ensure_one()
        if not self.item_type or not self.model_id:
            return False
        config = self._get_config()
        # Virtual record ids (NewId) are not JSON serializable.
        config["id"] = getattr(self.id, "origin", self.id) or 0
        try:
            data = self._get_data({})
        except Exception as error:  # noqa: BLE001 - shown in the preview card
            data = {"type": self.item_type, "error": str(error)}
        currency = self.env.company.currency_id
        return {
            "config": config,
            "data": data,
            "currency": {"symbol": currency.symbol, "position": currency.position},
        }

    # ------------------------------------------------------------------
    # Data engine
    # ------------------------------------------------------------------

    @api.model
    def get_items_data(self, item_ids, params=None):
        """Return the data payload of every requested item, keyed by id.

        Errors are isolated per item so a failing item does not break the
        whole dashboard. Access errors are re-raised so group/company rules
        cannot be bypassed by requesting an inaccessible item id.
        """
        items = self.browse(item_ids)
        items.check_access("read")
        result = {}
        for item in items:
            result[item.id] = item.get_data(params)
        return result

    def get_data(self, params=None):
        self.ensure_one()
        # Enforce dashboard item ACLs/record rules before isolating errors from
        # the source model (those must stay per-item payloads).
        self.check_access("read")
        params = params or {}
        ttl = self._data_cache_ttl()
        cache_key = self._data_cache_key(params) if ttl else None
        if cache_key is not None:
            cached = data_cache.cache_get(cache_key)
            if cached is not None:
                return copy.deepcopy(cached)
        try:
            data = self._get_data(params)
        except Exception as error:  # noqa: BLE001 - isolate faulty items
            return {"type": self.item_type, "error": str(error)}
        if cache_key is not None and isinstance(data, dict) and "error" not in data:
            data_cache.cache_set(cache_key, copy.deepcopy(data), ttl)
        return data

    def _data_cache_ttl(self):
        """Seconds to keep a computed payload, or 0 to bypass the cache."""
        interval = int(self.dashboard_id.refresh_interval or 0)
        if interval <= 0:
            return 0
        raw_max = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "boardkit_dashboard.data_cache_max_ttl",
                str(DEFAULT_DATA_CACHE_MAX_TTL),
            )
        )
        try:
            max_ttl = int(raw_max)
        except (TypeError, ValueError):
            max_ttl = DEFAULT_DATA_CACHE_MAX_TTL
        if max_ttl <= 0:
            return 0
        return min(interval, max_ttl)

    def _data_cache_key(self, params):
        """Build a user-scoped cache key for the current filter payload."""
        return (
            "boardkit.dashboard.item.data",
            self.env.uid,
            tuple(sorted(self.env.companies.ids)),
            self.id,
            fields.Datetime.to_string(self.write_date),
            fields.Datetime.to_string(self.dashboard_id.write_date),
            self.env.lang or "",
            self.env.context.get("tz") or self.env.user.tz or "",
            data_cache.fingerprint_params(params),
        )

    def _get_data(self, params):
        if self.item_type == "tile":
            return self._get_tile_data(params)
        if self.item_type == "kpi":
            return self._get_kpi_data(params)
        if self.item_type == "gauge":
            return self._get_gauge_data(params)
        if self.item_type == "funnel":
            return self._get_funnel_data(params)
        if self.item_type == "bullet":
            return self._get_bullet_data(params)
        if self.item_type == "map":
            return self._get_map_data(params)
        if self.item_type == "scatter":
            return self._get_scatter_data(params)
        if self.item_type == "list":
            return self._get_list_data(params)
        return self._get_chart_data(params)

    # ----- shared helpers ---------------------------------------------

    def _effective_date_range(self, params):
        """UI date filter wins; the item filter applies when the UI is on All Time."""
        preset = params.get("date_preset")
        if preset and preset != "none":
            return self.dashboard_id._get_date_range(
                preset, params.get("date_from"), params.get("date_to")
            )
        if self.date_filter == "none":
            return (None, None)
        return self.dashboard_id._get_date_range(
            self.date_filter, self.date_from, self.date_to
        )

    def _date_domain(self, field, date_range):
        start, end = date_range
        if not field or (start is None and end is None):
            return []
        domain = []
        if field.ttype == "date":
            tz_name = self.env.context.get("tz") or self.env.user.tz or "UTC"
            tz = pytz.timezone(tz_name)

            def to_local_date(value, *, ceil_partial_day=False):
                local_dt = pytz.utc.localize(value).astimezone(tz)
                # Presets such as "past" end at "now". For Date fields the
                # exclusive upper bound must move to the next local day so
                # today's records stay included.
                if ceil_partial_day and (
                    local_dt.hour
                    or local_dt.minute
                    or local_dt.second
                    or local_dt.microsecond
                ):
                    local_dt = local_dt + timedelta(days=1)
                return local_dt.date()

            if start is not None:
                domain.append(
                    (field.name, ">=", fields.Date.to_string(to_local_date(start)))
                )
            if end is not None:
                domain.append(
                    (
                        field.name,
                        "<",
                        fields.Date.to_string(
                            to_local_date(end, ceil_partial_day=True)
                        ),
                    )
                )
        else:
            if start is not None:
                domain.append((field.name, ">=", fields.Datetime.to_string(start)))
            if end is not None:
                domain.append((field.name, "<", fields.Datetime.to_string(end)))
        return domain

    def _filters_domain(self, params):
        filter_ids = params.get("filter_ids") or []
        if not filter_ids:
            return []
        domain = []
        filters = self.env["boardkit.dashboard.filter"].browse(filter_ids)
        for dashboard_filter in filters:
            if (
                dashboard_filter.dashboard_id == self.dashboard_id
                and dashboard_filter.model_name == self.model_name
            ):
                domain += self.dashboard_id._eval_domain(dashboard_filter.domain)
        return domain

    def _custom_filters_domain(self, params):
        """Domain leaves for the ad-hoc filters built from the dashboard UI."""
        domain = []
        for spec in params.get("custom_filters") or []:
            if not isinstance(spec, dict) or spec.get("model") != self.model_name:
                continue
            domain.append(self._custom_filter_leaf(spec))
        return domain

    def _custom_filter_leaf(self, spec):
        """Validate a single ``{field, operator, value}`` spec from the client."""
        model = self._source_model()
        field_name = spec.get("field") or ""
        field = model._fields.get(field_name)
        # fields_get also hides fields restricted by field-level groups.
        if not field or not model.fields_get([field_name]):
            raise ValidationError(_("Unknown filter field: %s", field_name))
        operator = spec.get("operator")
        if operator not in CUSTOM_FILTER_OPERATORS.get(field.type, ()):
            raise ValidationError(
                _(
                    "Unsupported filter operator %(operator)s for field %(field)s.",
                    operator=operator,
                    field=field_name,
                )
            )
        value = spec.get("value")
        if field.type == "boolean":
            value = bool(value)
        elif field.type == "integer":
            value = int(value)
        elif field.type in ("float", "monetary"):
            value = float(value)
        elif field.type == "date":
            day = fields.Date.to_date(value)
            if not day:
                raise ValidationError(_("Invalid date value in filter: %s", value))
            value = fields.Date.to_string(day)
        elif field.type == "datetime":
            value, operator = self._custom_filter_datetime(value, operator)
        else:
            value = str(value or "")
        return (field_name, operator, value)

    def _custom_filter_datetime(self, value, operator):
        """Turn a day picked by the user into a UTC datetime bound."""
        day = fields.Date.to_date(value)
        if not day:
            raise ValidationError(_("Invalid date value in filter: %s", value))
        # Day bounds are inclusive: shift ``<=`` / ``>`` to the next day.
        if operator in ("<=", ">"):
            day += timedelta(days=1)
            operator = "<" if operator == "<=" else ">="
        tz_name = self.env.context.get("tz") or self.env.user.tz or "UTC"
        tz = pytz.timezone(tz_name)
        moment = tz.localize(datetime.combine(day, time.min)).astimezone(pytz.utc)
        return fields.Datetime.to_string(moment.replace(tzinfo=None)), operator

    def _build_domain(self, params, secondary=False, date_range=None):
        dashboard = self.dashboard_id
        if secondary:
            domain = dashboard._eval_domain(self.domain_2)
            date_field = self.date_field_2_id
        else:
            domain = dashboard._eval_domain(self.domain)
            date_field = self.date_field_id
            domain += self._filters_domain(params)
            domain += self._custom_filters_domain(params)
        if date_range is None:
            date_range = self._effective_date_range(params)
        domain += self._date_domain(date_field, date_range)
        return domain

    def _previous_date_range(self, params):
        """Return ``((start, end), delta)`` for the period before the current one."""
        start, end = self._effective_date_range(params)
        if start is None or end is None:
            return None, None
        delta = end - start
        return (start - delta, start), delta

    def _source_model(self, secondary=False):
        model_name = self.model_2_name if secondary else self.model_name
        if not model_name or model_name not in self.env:
            raise ValidationError(_("The item data source model is not configured."))
        return self.env[model_name]

    def _aggregate_value(self, params, secondary=False):
        model = self._source_model(secondary)
        domain = self._build_domain(params, secondary)
        aggregation = self.aggregation_2 if secondary else self.aggregation
        measure = self.measure_field_2_id if secondary else self.measure_field_id
        count = model.search_count(domain)
        if aggregation == "count" or not measure:
            return count, count, domain
        rows = model._read_group(domain, [], [f"{measure.name}:{aggregation}"])
        value = rows[0][0] if rows else 0
        return value or 0, count, domain

    @staticmethod
    def _serialize_domain(domain):
        serialized = []
        for leaf in domain:
            if isinstance(leaf, list | tuple):
                field_name, operator, value = leaf
                if isinstance(value, datetime):
                    value = fields.Datetime.to_string(value)
                elif hasattr(value, "isoformat"):
                    value = value.isoformat()
                serialized.append([field_name, operator, value])
            else:
                serialized.append(leaf)
        return serialized

    # ----- tile / kpi --------------------------------------------------

    def _get_tile_data(self, params):
        value, count, domain = self._aggregate_value(params)
        data = {
            "type": "tile",
            "value": value,
            "count": count,
            "domain": self._serialize_domain(domain),
        }
        if self.compare_previous_period:
            previous = self._get_previous_period_value(params)
            if previous is not None:
                data["previous_value"] = previous
        return data

    def _get_gauge_data(self, params):
        value, count, domain = self._aggregate_value(params)
        target = self.target_value if self.target_enabled else 0
        gauge_max = self.gauge_max
        if not gauge_max or gauge_max <= 0:
            gauge_max = max(value or 0, target or 0, 1) * 1.2
        return {
            "type": "gauge",
            "value": value or 0,
            "count": count,
            "target": target if self.target_enabled else False,
            "max": gauge_max,
            "domain": self._serialize_domain(domain),
        }

    def _get_funnel_data(self, params):
        if not self.group_by_field_id:
            raise ValidationError(_("Configure the Group By field for this chart."))
        base_domain = self._build_domain(params)
        # Build unsorted groups first, then apply funnel-specific ordering.
        chart = self._grouped_payload(
            base_domain,
            self.group_by_field_id,
            self.group_by_granularity,
            "default",
            0,
        )
        labels = chart["labels"]
        datasets = chart["datasets"]
        if datasets:
            labels, datasets = self._apply_funnel_ordering(
                labels,
                datasets,
                base_domain,
                chart_sort=self.chart_sort,
                sort_field=self.sort_field_id,
                sort_dir=self.sort_dir,
            )
            if self.record_limit and self.record_limit > 0:
                labels, datasets = self._sort_and_limit_forced(
                    labels, datasets, "default", self.record_limit
                )
        return {
            "type": "funnel",
            "labels": labels,
            "datasets": datasets,
        }

    def _apply_funnel_ordering(
        self, labels, datasets, domain, chart_sort, sort_field, sort_dir
    ):
        """Order funnel stages: Sort By overrides Chart Sort."""
        if sort_field:
            return self._sort_funnel_by_field(
                labels, datasets, domain, sort_field, sort_dir
            )
        chart_sort = chart_sort or "default"
        if chart_sort == "default":
            return self._sort_funnel_by_model_order(labels, datasets)
        if chart_sort == "value_asc":
            # A funnel narrows downwards, so growing stages would draw an
            # upside down cone.
            chart_sort = "value_desc"
        return self._sort_and_limit_forced(labels, datasets, chart_sort, 0)

    def _funnel_group_keys(self, datasets):
        """Extract the grouped values from serialized drilldown domains."""
        group_name = self.group_by_field_id.name
        keys = []
        for leaves in datasets[0].get("drilldowns") or []:
            value = False
            for leaf in leaves or []:
                if (
                    isinstance(leaf, list | tuple)
                    and len(leaf) >= 3
                    and leaf[0] == group_name
                    and leaf[1] == "="
                ):
                    value = leaf[2]
                    break
            keys.append(value)
        return keys

    def _reorder_funnel_datasets(self, labels, datasets, order):
        new_labels = [labels[i] for i in order]
        for dataset in datasets:
            dataset["data"] = [dataset["data"][i] for i in order]
            dataset["drilldowns"] = [dataset["drilldowns"][i] for i in order]
        return new_labels, datasets

    def _sort_funnel_by_model_order(self, labels, datasets):
        """Order groups by the related/selection model's natural order."""
        group_keys = self._funnel_group_keys(datasets)
        group_field = self.group_by_field_id
        if group_field.ttype == "many2one" and group_field.relation:
            Related = self.env[group_field.relation].with_context(active_test=False)
            ids = [key for key in group_keys if key]
            # search() applies the related model's ``_order`` (e.g. stage.sequence).
            ordered_ids = Related.search([("id", "in", ids)]).ids
            rank = {record_id: index for index, record_id in enumerate(ordered_ids)}
            order = sorted(
                range(len(labels)),
                key=lambda index: (
                    group_keys[index] is False or group_keys[index] is None,
                    rank.get(group_keys[index], len(ordered_ids)),
                ),
            )
            return self._reorder_funnel_datasets(labels, datasets, order)
        if group_field.ttype == "selection":
            model_field = self._source_model()._fields[group_field.name]
            selection_keys = [
                key for key, __ in model_field._description_selection(self.env)
            ]
            rank = {key: index for index, key in enumerate(selection_keys)}
            order = sorted(
                range(len(labels)),
                key=lambda index: (
                    group_keys[index] is False or group_keys[index] is None,
                    rank.get(group_keys[index], len(rank)),
                ),
            )
            return self._reorder_funnel_datasets(labels, datasets, order)
        return labels, datasets

    def _funnel_sort_key_values(self, group_keys, domain, sort_field):
        """Resolve comparable sort values for each funnel group key."""
        group_field = self.group_by_field_id
        if (
            group_field.ttype == "many2one"
            and sort_field.model_id.model == group_field.relation
        ):
            Related = self.env[group_field.relation].with_context(active_test=False)
            records = Related.browse([key for key in group_keys if key]).exists()
            value_map = {record.id: record[sort_field.name] for record in records}
            return [value_map.get(key) for key in group_keys]

        model = self._source_model()
        rows = model._read_group(domain, [group_field.name], [f"{sort_field.name}:min"])
        value_map = {}
        for row in rows:
            raw = row[0]
            key = raw.id if hasattr(raw, "id") else raw
            value_map[key] = row[1]
        return [value_map.get(key) for key in group_keys]

    def _sort_funnel_by_field(self, labels, datasets, domain, sort_field, sort_dir):
        """Order funnel stages by Sort By / Sort Dir."""
        group_keys = self._funnel_group_keys(datasets)
        sort_values = self._funnel_sort_key_values(group_keys, domain, sort_field)
        reverse = sort_dir == "desc"
        present = []
        empty = []
        for index, value in enumerate(sort_values):
            if value is False or value is None:
                empty.append(index)
            else:
                present.append(index)
        present.sort(key=lambda index: sort_values[index], reverse=reverse)
        return self._reorder_funnel_datasets(labels, datasets, present + empty)

    def _get_bullet_data(self, params):
        chart = self._get_chart_data(params)
        dataset = (
            chart["datasets"][0]
            if chart["datasets"]
            else {
                "label": _("Value"),
                "data": [],
                "drilldowns": [],
            }
        )
        return {
            "type": "bullet",
            "labels": chart["labels"],
            "datasets": [dataset],
            "target": self.target_value if self.target_enabled else False,
        }

    def _get_map_data(self, params):
        if self.map_mode == "points":
            return self._get_map_points_data(params)
        return self._get_map_regions_data(params)

    def _map_relation_prefix(self):
        """Return the many2one leading to the map fields, or an empty string."""
        self.ensure_one()
        return self.map_relation_field_id.name or ""

    @staticmethod
    def _map_field_path(prefix, name):
        return f"{prefix}.{name}" if prefix else name

    @staticmethod
    def _map_prefix_leaves(prefix, leaves):
        """Rewrite domain leaves so they traverse the relation field."""
        if not prefix:
            return leaves
        return [
            (f"{prefix}.{name}", operator, value) for name, operator, value in leaves
        ]

    def _get_map_regions_data(self, params):
        if not self.group_by_field_id:
            raise ValidationError(_("Configure the Group By field for the map."))
        group_field = self.group_by_field_id
        if group_field.ttype != "many2one" or group_field.relation != "res.country":
            raise ValidationError(
                _("Map regions mode requires a Group By field pointing to Countries.")
            )
        model = self._source_model()
        base_domain = self._build_domain(params)
        prefix = self._map_relation_prefix()
        if prefix:
            totals = self._map_regions_through_relation(
                model, base_domain, prefix, group_field
            )
        else:
            measure_spec, __ = self._chart_measures()[0]
            totals = model._read_group(base_domain, [group_field.name], [measure_spec])
        regions = []
        for raw, value in totals:
            if not raw:
                continue
            label, leaves = self._format_group_value(group_field, None, raw)
            code = (raw.code or "").upper()
            if not code:
                continue
            regions.append(
                {
                    "code": code,
                    "label": label,
                    "value": value or 0,
                    "domain": self._serialize_domain(
                        base_domain + self._map_prefix_leaves(prefix, leaves)
                    ),
                }
            )
        if self.record_limit and self.record_limit > 0:
            regions = sorted(regions, key=lambda r: r["value"], reverse=True)[
                : self.record_limit
            ]
        return {"type": "map", "mode": "regions", "regions": regions}

    def _map_regions_through_relation(self, model, domain, prefix, group_field):
        """Return ``[(country, value)]`` for a regions map behind a relation.

        _read_group cannot group by a path, so the records are aggregated per
        related record and folded per country afterwards.
        """
        aggregates = self._map_regions_aggregates()
        rows = model._read_group(domain, [prefix], aggregates)
        country_by_related = self._map_related_countries(rows, group_field)
        weighted = len(aggregates) > 1
        totals = {}
        for row in rows:
            country_id = country_by_related.get(row[0].id) if row[0] else False
            if not country_id:
                continue
            value, weight = totals.get(country_id, (0, 0))
            totals[country_id] = (
                value + (row[1] or 0),
                weight + ((row[2] or 0) if weighted else 0),
            )
        Country = self.env["res.country"]
        return [
            (
                Country.browse(country_id),
                (value / weight if weight else 0) if weighted else value,
            )
            for country_id, (value, weight) in totals.items()
        ]

    def _map_regions_aggregates(self):
        """Aggregates that can be folded per country.

        Averages are asked as a sum and a count so the fold can compute a
        weighted mean; averaging per-relation averages would skew the result.
        """
        if self.aggregation != "avg":
            return [self._chart_measures()[0][0]]
        measures = self._ordered_measure_fields() or self.measure_field_id
        if not measures:
            raise ValidationError(_("Configure at least one measure for this chart."))
        name = measures[0].name
        return [f"{name}:sum", f"{name}:count"]

    def _map_related_countries(self, rows, group_field):
        """Return ``{related_record_id: country_id}`` for the grouped rows.

        Read with search_read so the comodel record rules drop inaccessible
        records instead of raising and breaking the whole dashboard.
        """
        related_ids = [row[0].id for row in rows if row[0]]
        related_model = self.env[self.map_relation_field_id.relation]
        countries = {}
        for row in related_model.search_read(
            [("id", "in", related_ids)], [group_field.name]
        ):
            country = row.get(group_field.name)
            countries[row["id"]] = country[0] if country else False
        return countries

    def _get_map_points_data(self, params):
        if not self.latitude_field_id or not self.longitude_field_id:
            raise ValidationError(
                _("Configure Latitude and Longitude fields for the map.")
            )
        lat_name = self.latitude_field_id.name
        lon_name = self.longitude_field_id.name
        prefix = self._map_relation_prefix()
        model = self._source_model()
        base_domain = self._build_domain(params)
        # Float fields default to 0.0 when empty; skip the (0, 0) null island.
        domain = base_domain + [
            "|",
            (self._map_field_path(prefix, lat_name), "!=", 0.0),
            (self._map_field_path(prefix, lon_name), "!=", 0.0),
        ]
        measure = self.measure_field_id or self._ordered_measure_fields()[:1]
        fields_to_read = ["display_name"]
        fields_to_read += [prefix] if prefix else [lat_name, lon_name]
        if measure:
            fields_to_read.append(measure.name)
        records = model.search_read(domain, fields_to_read, limit=MAP_MAX_RECORDS)
        coordinates = self._map_point_coordinates(records, prefix, lat_name, lon_name)
        groups = {}
        for record in records:
            latitude, longitude = coordinates.get(record["id"]) or (0.0, 0.0)
            if not latitude and not longitude:
                continue
            # Records sharing coordinates are merged into a single marker, so
            # overlapping bubbles do not hide each other on the map.
            key = (
                round(latitude, MAP_COORD_PRECISION),
                round(longitude, MAP_COORD_PRECISION),
            )
            group = groups.setdefault(
                key,
                {
                    "latitude": key[0],
                    "longitude": key[1],
                    "label": record.get("display_name") or "",
                    "count": 0,
                    "value": 0,
                    "ids": [],
                },
            )
            group["count"] += 1
            group["ids"].append(record["id"])
            group["value"] += (record.get(measure.name) or 0) if measure else 1
        points = []
        for group in groups.values():
            ids = group.pop("ids")
            if group["count"] > 1:
                group["label"] = _(
                    "%(name)s (+%(count)s more)",
                    name=group["label"],
                    count=group["count"] - 1,
                )
            group["domain"] = self._serialize_domain(base_domain + [("id", "in", ids)])
            points.append(group)
        # Biggest markers first, so the smaller ones stay clickable on top.
        points.sort(key=lambda point: point["value"], reverse=True)
        if self.record_limit and self.record_limit > 0:
            points = points[: self.record_limit]
        return {
            "type": "map",
            "mode": "points",
            "points": points,
            "truncated": len(records) >= MAP_MAX_RECORDS,
        }

    def _map_point_coordinates(self, records, prefix, lat_name, lon_name):
        """Return ``{source_record_id: (latitude, longitude)}``.

        Coordinates reached through a relation field cannot be read by
        search_read, which does not traverse paths. They are read with
        search_read on the comodel so its record rules only drop inaccessible
        markers, instead of raising an access error that would take the whole
        dashboard down.
        """
        if not prefix:
            return {
                record["id"]: (
                    record.get(lat_name) or 0.0,
                    record.get(lon_name) or 0.0,
                )
                for record in records
            }
        related_ids = {record[prefix][0] for record in records if record.get(prefix)}
        related_model = self.env[self.map_relation_field_id.relation]
        by_related = {
            row["id"]: (row.get(lat_name) or 0.0, row.get(lon_name) or 0.0)
            for row in related_model.search_read(
                [("id", "in", list(related_ids))], [lat_name, lon_name]
            )
        }
        coordinates = {}
        for record in records:
            related = record.get(prefix)
            if related and related[0] in by_related:
                coordinates[record["id"]] = by_related[related[0]]
        return coordinates

    def _get_kpi_data(self, params):
        value, __, domain = self._aggregate_value(params)
        data = {
            "type": "kpi",
            "value": value,
            "domain": self._serialize_domain(domain),
        }
        if self.kpi_mode == "target":
            if self.target_enabled:
                data["target"] = self.target_value
        elif self.model_2_id:
            value_2, __, domain_2 = self._aggregate_value(params, secondary=True)
            data["value_2"] = value_2
            data["domain_2"] = self._serialize_domain(domain_2)
        if self.compare_previous_period:
            previous = self._get_previous_period_value(params)
            if previous is not None:
                data["previous_value"] = previous
        return data

    def _get_previous_period_value(self, params):
        date_range, __ = self._previous_date_range(params)
        if date_range is None or not self.date_field_id:
            return None
        model = self._source_model()
        domain = self._build_domain(params, date_range=date_range)
        if self.aggregation == "count" or not self.measure_field_id:
            return model.search_count(domain)
        rows = model._read_group(
            domain, [], [f"{self.measure_field_id.name}:{self.aggregation}"]
        )
        return (rows[0][0] if rows else 0) or 0

    @staticmethod
    def _group_raw_key(raw):
        if raw is False or raw is None:
            return False
        if hasattr(raw, "id") and not isinstance(raw, date | datetime):
            return ("m2o", raw.id)
        return ("v", raw)

    def _shift_group_key(self, group_field, key, delta):
        """Map a current bucket key onto the equivalent previous-period key."""
        if not key or group_field.ttype not in ("date", "datetime"):
            return key
        __, raw = key
        if isinstance(raw, datetime):
            return ("v", raw - delta)
        if isinstance(raw, date):
            return ("v", raw - timedelta(days=delta.days))
        return key

    def _previous_period_value_map(self, params, group_field, granularity):
        """Aggregate the previous period keyed like ``_group_raw_key``."""
        date_range, delta = self._previous_date_range(params)
        if date_range is None or not self.date_field_id or delta is None:
            return None, None
        model = self._source_model()
        domain = self._build_domain(params, date_range=date_range)
        groupby = [self._groupby_spec(group_field, granularity)]
        measures = self._chart_measures()
        rows = model._read_group(domain, groupby, [spec for spec, __ in measures])
        value_map = {}
        for row in rows:
            value_map[self._group_raw_key(row[0])] = [(value or 0) for value in row[1:]]
        return value_map, delta

    def _previous_period_datasets(
        self, params, group_field, granularity, group_keys, measure_labels
    ):
        value_map, delta = self._previous_period_value_map(
            params, group_field, granularity
        )
        if value_map is None:
            return None
        datasets = []
        measure_count = len(measure_labels)
        for measure_index, measure_label in enumerate(measure_labels):
            data = []
            for key in group_keys:
                lookup = self._shift_group_key(group_field, key, delta)
                values = value_map.get(lookup) or [0] * measure_count
                data.append(values[measure_index] if measure_index < len(values) else 0)
            datasets.append({"label": measure_label, "data": data})
        return datasets

    # ----- charts -------------------------------------------------------

    def _groupby_spec(self, field, granularity):
        if field.ttype in ("date", "datetime"):
            return f"{field.name}:{granularity or 'month'}"
        return field.name

    def _format_group_value(self, field, granularity, raw):
        """Return ``(label, domain_leaves)`` for one raw group value."""
        name = field.name
        if field.ttype == "boolean":
            if raw:
                label = self.boolean_true_label or _("Yes")
            else:
                label = self.boolean_false_label or _("No")
            return label, [(name, "=", bool(raw))]
        if raw is False or raw is None or (hasattr(raw, "_name") and not raw):
            return _("None"), [(name, "=", False)]
        if field.ttype in ("date", "datetime"):
            granularity = granularity or "month"
            interval = GRANULARITY_INTERVAL[granularity]
            locale = babel_locale_parse(get_lang(self.env).code)
            if field.ttype == "datetime":
                display_value = fields.Datetime.context_timestamp(self, raw)
                label = babel.dates.format_datetime(
                    display_value,
                    format=GRANULARITY_LABEL_FORMAT[granularity],
                    locale=locale,
                )
                leaves = [
                    (name, ">=", fields.Datetime.to_string(raw)),
                    (name, "<", fields.Datetime.to_string(raw + interval)),
                ]
            else:
                label = babel.dates.format_date(
                    raw, format=GRANULARITY_LABEL_FORMAT[granularity], locale=locale
                )
                leaves = [
                    (name, ">=", fields.Date.to_string(raw)),
                    (name, "<", fields.Date.to_string(raw + interval)),
                ]
            return label, leaves
        if field.ttype == "many2one":
            return raw.display_name, [(name, "=", raw.id)]
        if field.ttype == "selection":
            model_field = self._source_model()._fields[name]
            labels = dict(model_field._description_selection(self.env))
            return labels.get(raw, raw), [(name, "=", raw)]
        return str(raw), [(name, "=", raw)]

    def _ordered_measure_fields(self):
        """Measure fields in their configured order.

        Sort explicitly: onchange (form preview) works on virtual records
        whose one2many cache keeps insertion order, not the model _order.
        """
        self.ensure_one()
        return self.measure_ids.sorted("sequence").field_id

    def _chart_measures(self):
        if self.aggregation == "count":
            return [("__count", _("Count"))]
        measures = self._ordered_measure_fields() or self.measure_field_id
        if not measures:
            raise ValidationError(_("Configure at least one measure for this chart."))
        return [
            (f"{field.name}:{self.aggregation}", field.field_description)
            for field in measures
        ]

    def _sort_and_limit(self, labels, datasets):
        return self._sort_and_limit_forced(
            labels, datasets, self.chart_sort, self.record_limit
        )

    def _sort_and_limit_forced(
        self, labels, datasets, chart_sort, record_limit=None, parallel=None
    ):
        order = list(range(len(labels)))
        if chart_sort in ("label_asc", "label_desc"):
            order.sort(
                key=lambda i: (labels[i] or ""), reverse=chart_sort == "label_desc"
            )
        elif chart_sort in ("value_asc", "value_desc"):
            totals = [
                sum(dataset["data"][i] or 0 for dataset in datasets) for i in order
            ]
            order.sort(key=lambda i: totals[i], reverse=chart_sort == "value_desc")
        if record_limit is None:
            record_limit = self.record_limit
        if record_limit and record_limit > 0:
            order = order[:record_limit]
        new_labels = [labels[i] for i in order]
        for dataset in datasets:
            dataset["data"] = [dataset["data"][i] for i in order]
            dataset["drilldowns"] = [dataset["drilldowns"][i] for i in order]
        if parallel is not None:
            return new_labels, datasets, [parallel[i] for i in order]
        return new_labels, datasets

    def _grouped_payload(
        self,
        domain,
        group_field,
        granularity,
        chart_sort,
        record_limit,
        params=None,
        attach_previous=False,
    ):
        """Aggregate one dimension into labels/datasets with drilldown domains."""
        model = self._source_model()
        groupby = [self._groupby_spec(group_field, granularity)]
        measures = self._chart_measures()
        rows = model._read_group(domain, groupby, [spec for spec, __ in measures])

        groups = {}
        labels = []
        group_leaves = []
        group_keys = []
        for row in rows:
            raw = row[0]
            key = raw.id if hasattr(raw, "id") else raw
            if key not in groups:
                label, leaves = self._format_group_value(group_field, granularity, raw)
                groups[key] = len(labels)
                labels.append(label)
                group_leaves.append(leaves)
                group_keys.append(self._group_raw_key(raw))

        datasets = []
        for measure_index, (__, measure_label) in enumerate(measures):
            data = [0] * len(labels)
            drilldowns = [None] * len(labels)
            for row in rows:
                raw = row[0]
                key = raw.id if hasattr(raw, "id") else raw
                index = groups[key]
                data[index] = row[1 + measure_index] or 0
                drilldowns[index] = self._serialize_domain(domain + group_leaves[index])
            datasets.append(
                {"label": measure_label, "data": data, "drilldowns": drilldowns}
            )

        labels, datasets, group_keys = self._sort_and_limit_forced(
            labels, datasets, chart_sort, record_limit, parallel=group_keys
        )
        payload = {"type": "chart", "labels": labels, "datasets": datasets}
        if (
            attach_previous
            and params is not None
            and self.compare_previous_period
            and self.item_type in PREVIOUS_PERIOD_CHART_TYPES
        ):
            previous = self._previous_period_datasets(
                params,
                group_field,
                granularity,
                group_keys,
                [label for __, label in measures],
            )
            if previous:
                payload["previous_datasets"] = previous
        return payload

    def _drill_level_payload(
        self,
        group_field,
        granularity,
        chart_type,
        chart_sort,
        record_limit,
        domain=None,
    ):
        """Re-aggregate ``self`` over ``domain`` for one drill chart type."""
        if not group_field:
            raise ValidationError(
                _("Configure the Group By field for the drill level.")
            )
        if chart_type == "funnel":
            payload = self._grouped_payload(
                domain or [],
                group_field,
                granularity,
                "default",
                0,
            )
            labels = payload["labels"]
            datasets = payload["datasets"]
            if datasets:
                labels, datasets = self._apply_funnel_ordering(
                    labels,
                    datasets,
                    domain or [],
                    chart_sort=chart_sort,
                    sort_field=False,
                    sort_dir="asc",
                )
                if record_limit and record_limit > 0:
                    labels, datasets = self._sort_and_limit_forced(
                        labels, datasets, "default", record_limit
                    )
                payload["labels"] = labels
                payload["datasets"] = datasets
            payload["type"] = "funnel"
            return payload
        return self._grouped_payload(
            domain or [],
            group_field,
            granularity,
            chart_sort,
            record_limit,
        )

    def get_drill_data(self, level_id, domain=None):
        """Re-aggregate the item over ``domain`` using a configured drill level."""
        self.ensure_one()
        self.check_access("read")
        level = self.env["boardkit.dashboard.item.drill"].browse(level_id)
        if not level.exists() or level.item_id != self:
            raise ValidationError(_("Invalid drill level for this dashboard item."))
        return self._drill_level_payload(
            level.group_by_field_id,
            level.group_by_granularity,
            level.chart_type,
            level.chart_sort,
            level.record_limit,
            domain,
        )

    @api.model
    def get_preview_drill_data(self, snapshot, level_index, domain=None):
        """Re-aggregate using a form-preview snapshot (saved or unsaved levels).

        The live preview cannot rely on ``get_drill_data`` alone: new drill
        lines may still be virtual (id 0) and the form values may differ from
        the database. ``snapshot`` is built from the preview config payload.
        """
        if not isinstance(snapshot, dict):
            raise ValidationError(_("Invalid preview drill snapshot."))
        item_id = snapshot.get("item_id") or 0
        if item_id:
            item = self.browse(item_id)
            if not item.exists():
                raise ValidationError(_("Invalid dashboard item."))
            item.check_access("read")
        else:
            # Creating an item in the form: still require dashboard item read.
            self.check_access("read")

        model_name = snapshot.get("model")
        if not model_name or model_name not in self.env:
            raise ValidationError(_("Invalid model for preview drill."))
        self.env[model_name].check_access("read")

        levels = snapshot.get("drill_levels") or []
        if (
            not isinstance(level_index, int)
            or level_index < 0
            or level_index >= len(levels)
        ):
            raise ValidationError(_("Invalid drill level for this dashboard item."))
        level_spec = levels[level_index] or {}
        group_field = self.env["ir.model.fields"].browse(
            level_spec.get("group_by_field_id")
        )
        if not group_field.exists() or group_field.model != model_name:
            raise ValidationError(
                _("Configure the Group By field for the drill level.")
            )

        measure_ids = [
            field_id
            for field_id in snapshot.get("measure_field_ids") or []
            if isinstance(field_id, int)
        ]
        if measure_ids:
            measures = self.env["ir.model.fields"].browse(measure_ids).exists()
            if any(field.model != model_name for field in measures):
                raise ValidationError(_("Invalid measure field for preview drill."))
            measure_ids = measures.ids

        model_rec = self.env["ir.model"]._get(model_name)
        item = self.new(
            {
                "model_id": model_rec.id,
                "aggregation": snapshot.get("aggregation") or "count",
                "measure_ids": [
                    (0, 0, {"sequence": (index + 1) * 10, "field_id": field_id})
                    for index, field_id in enumerate(measure_ids)
                ],
                "item_type": level_spec.get("type") or "bar",
            }
        )
        return item._drill_level_payload(
            group_field,
            level_spec.get("group_by_granularity") or False,
            level_spec.get("type") or "bar",
            level_spec.get("chart_sort") or "default",
            level_spec.get("record_limit") or 0,
            domain,
        )

    def _get_chart_data(self, params):
        if not self.group_by_field_id:
            raise ValidationError(_("Configure the Group By field for this chart."))
        model = self._source_model()
        base_domain = self._build_domain(params)
        group_field = self.group_by_field_id
        subgroup_field = (
            self.subgroup_by_field_id if self.item_type in CHART_TYPES else None
        )
        if not subgroup_field:
            return self._grouped_payload(
                base_domain,
                group_field,
                self.group_by_granularity,
                self.chart_sort,
                self.record_limit,
                params=params,
                attach_previous=True,
            )

        groupby = [
            self._groupby_spec(group_field, self.group_by_granularity),
            self._groupby_spec(subgroup_field, self.subgroup_by_granularity),
        ]
        measures = self._chart_measures()[:1]
        rows = model._read_group(base_domain, groupby, [spec for spec, __ in measures])

        groups = {}
        labels = []
        group_leaves = []
        for row in rows:
            raw = row[0]
            key = raw.id if hasattr(raw, "id") else raw
            if key not in groups:
                label, leaves = self._format_group_value(
                    group_field, self.group_by_granularity, raw
                )
                groups[key] = len(labels)
                labels.append(label)
                group_leaves.append(leaves)

        datasets_map = {}
        for row in rows:
            raw_group, raw_sub = row[0], row[1]
            values = row[2:]
            group_key = raw_group.id if hasattr(raw_group, "id") else raw_group
            sub_key = raw_sub.id if hasattr(raw_sub, "id") else raw_sub
            if sub_key not in datasets_map:
                sub_label, sub_leaves = self._format_group_value(
                    subgroup_field, self.subgroup_by_granularity, raw_sub
                )
                datasets_map[sub_key] = {
                    "label": sub_label,
                    "data": [0] * len(labels),
                    "drilldowns": [None] * len(labels),
                    "_leaves": sub_leaves,
                }
            dataset = datasets_map[sub_key]
            index = groups[group_key]
            dataset["data"][index] = values[0] or 0
            dataset["drilldowns"][index] = self._serialize_domain(
                base_domain + group_leaves[index] + dataset["_leaves"]
            )
        datasets = []
        for dataset in datasets_map.values():
            dataset.pop("_leaves")
            for index, drilldown in enumerate(dataset["drilldowns"]):
                if drilldown is None:
                    dataset["drilldowns"][index] = self._serialize_domain(
                        base_domain + group_leaves[index]
                    )
            datasets.append(dataset)

        labels, datasets = self._sort_and_limit(labels, datasets)
        return {"type": "chart", "labels": labels, "datasets": datasets}

    def _get_scatter_data(self, params):
        if not self.group_by_field_id:
            raise ValidationError(_("Configure the Group By field for this chart."))
        if not self.measure_x_field_id or not self.measure_y_field_id:
            raise ValidationError(
                _("Configure the X and Y measures for the scatter chart.")
            )
        model = self._source_model()
        base_domain = self._build_domain(params)
        group_field = self.group_by_field_id
        aggregation = self.aggregation if self.aggregation != "count" else "sum"
        rows = model._read_group(
            base_domain,
            [self._groupby_spec(group_field, self.group_by_granularity)],
            [
                f"{self.measure_x_field_id.name}:{aggregation}",
                f"{self.measure_y_field_id.name}:{aggregation}",
            ],
        )
        points = []
        point_labels = []
        drilldowns = []
        for raw, value_x, value_y in rows:
            label, leaves = self._format_group_value(
                group_field, self.group_by_granularity, raw
            )
            point_labels.append(label)
            points.append({"x": value_x or 0, "y": value_y or 0})
            drilldowns.append(self._serialize_domain(base_domain + leaves))
        if self.record_limit and self.record_limit > 0:
            points = points[: self.record_limit]
            point_labels = point_labels[: self.record_limit]
            drilldowns = drilldowns[: self.record_limit]
        return {
            "type": "scatter",
            "labels": point_labels,
            "datasets": [
                {
                    "label": f"{self.measure_x_field_id.field_description} /"
                    f" {self.measure_y_field_id.field_description}",
                    "data": points,
                    "drilldowns": drilldowns,
                }
            ],
        }

    # ----- list ---------------------------------------------------------

    def _format_cell(self, record, field):
        value = record[field.name]
        if field.ttype == "many2one":
            return value.display_name if value else ""
        if field.ttype == "selection":
            model_field = record._fields[field.name]
            return (
                dict(model_field._description_selection(self.env)).get(value, "")
                if value
                else ""
            )
        if field.ttype == "datetime":
            return format_datetime(self.env, value) if value else ""
        if field.ttype == "date":
            return format_date(self.env, value) if value else ""
        if field.ttype in ("integer", "float", "monetary"):
            return value
        if field.ttype == "boolean":
            return bool(value)
        return value or ""

    def _get_list_data(self, params):
        if self.list_type == "grouped":
            return self._get_grouped_list_data(params)
        model = self._source_model()
        domain = self._build_domain(params)
        # Sort explicitly: onchange (form preview) works on virtual records
        # whose one2many cache keeps insertion order, not the model _order.
        columns = self.list_column_ids.sorted("sequence").field_id
        if not columns:
            raise ValidationError(_("Configure the columns of this list."))
        offset = int(params.get("offset") or 0)
        if params.get("no_pagination"):
            limit = int(params.get("export_max_rows") or EXPORT_MAX_ROWS)
        else:
            limit = self.page_size or 10
        # Interactive header sort overrides the configured sort, but only for
        # stored fields exposed as columns so arbitrary names are rejected.
        sort_field = params.get("sort_field")
        sort_dir = params.get("sort_dir") if params.get("sort_dir") == "desc" else "asc"
        if sort_field not in columns.filtered("store").mapped("name"):
            sort_field = self.sort_field_id.name if self.sort_field_id else False
            sort_dir = self.sort_dir if self.sort_field_id else "asc"
        order = f"{sort_field} {sort_dir}" if sort_field else None
        records = model.search(domain, offset=offset, limit=limit, order=order)
        return {
            "type": "list",
            "grouped": False,
            "columns": [
                {
                    "name": field.name,
                    "label": field.field_description,
                    "type": field.ttype,
                    "sortable": field.store,
                }
                for field in columns
            ],
            "rows": [
                {
                    "id": record.id,
                    "values": [self._format_cell(record, field) for field in columns],
                }
                for record in records
            ],
            "offset": offset,
            "total": model.search_count(domain),
            "sort_field": sort_field or False,
            "sort_dir": sort_dir,
        }

    def _get_grouped_list_data(self, params):
        if not self.group_by_field_id:
            raise ValidationError(
                _("Configure the Group By field for this grouped list.")
            )
        model = self._source_model()
        base_domain = self._build_domain(params)
        group_field = self.group_by_field_id
        groupby = [self._groupby_spec(group_field, self.group_by_granularity)]
        measures = self._ordered_measure_fields()
        aggregates = ["__count"] + [f"{field.name}:sum" for field in measures]
        offset = int(params.get("offset") or 0)
        if params.get("no_pagination"):
            limit = int(params.get("export_max_rows") or EXPORT_MAX_ROWS)
        else:
            limit = self.page_size or 10
        rows = model._read_group(
            base_domain, groupby, aggregates, offset=offset, limit=limit
        )
        total = len(model._read_group(base_domain, groupby, []))
        columns = [
            {
                "name": group_field.name,
                "label": group_field.field_description,
                "type": "char",
            },
            {"name": "__count", "label": _("Count"), "type": "integer"},
        ] + [
            {"name": field.name, "label": field.field_description, "type": field.ttype}
            for field in measures
        ]
        data_rows = []
        for row in rows:
            label, leaves = self._format_group_value(
                group_field, self.group_by_granularity, row[0]
            )
            data_rows.append(
                {
                    "values": [label] + [value or 0 for value in row[1:]],
                    "domain": self._serialize_domain(base_domain + leaves),
                }
            )
        return {
            "type": "list",
            "grouped": True,
            "columns": columns,
            "rows": data_rows,
            "offset": offset,
            "total": total,
        }

    # ------------------------------------------------------------------
    # Drill down actions
    # ------------------------------------------------------------------

    def get_drilldown_action(self, domain=None, action_name=None):
        """Return the window action opening the records behind a value."""
        self.ensure_one()
        if self.action_id:
            action = self.action_id.sudo().read(["name", "type", "res_model", "views"])[
                0
            ]
            try:
                context = self.dashboard_id._domain_eval_context()
                action["context"] = safe_eval(self.action_id.context or "{}", context)
            except Exception:  # noqa: BLE001 - keep the action usable
                action["context"] = {}
            action["domain"] = domain or []
            action["target"] = "current"
            action.pop("id", None)
            return action
        return {
            "type": "ir.actions.act_window",
            "name": action_name or self.name,
            "res_model": self.model_name,
            "domain": domain or [],
            "views": [[False, "list"], [False, "form"]],
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Data export (CSV / XLSX download)
    # ------------------------------------------------------------------

    def get_export_data(self, params=None):
        """Return the item data as ``headers``/``rows`` for a file download."""
        self.ensure_one()
        self.check_access("read")
        headers, rows = self._get_export_rows(dict(params or {}))
        return {"name": self.name, "headers": headers, "rows": rows}

    def _get_export_rows(self, params):
        if self.item_type == "tile":
            data = self._get_data(params)
            return (
                [_("Name"), _("Value"), _("Records")],
                [[self.name, data["value"], data["count"]]],
            )
        if self.item_type == "kpi":
            data = self._get_data(params)
            headers, row = [_("Name"), _("Value")], [self.name, data["value"]]
            for key, label in (
                ("target", _("Target")),
                ("value_2", _("Second Value")),
                ("previous_value", _("Previous Period")),
            ):
                if key in data:
                    headers.append(label)
                    row.append(data[key])
            return headers, [row]
        if self.item_type == "gauge":
            data = self._get_data(params)
            return (
                [_("Name"), _("Value"), _("Target"), _("Maximum")],
                [[self.name, data["value"], data["target"] or 0, data["max"]]],
            )
        if self.item_type == "map":
            data = self._get_data(params)
            if data.get("mode") == "points":
                return (
                    [
                        _("Label"),
                        _("Latitude"),
                        _("Longitude"),
                        _("Records"),
                        _("Value"),
                    ],
                    [
                        [
                            point["label"],
                            point["latitude"],
                            point["longitude"],
                            point["count"],
                            point["value"],
                        ]
                        for point in data.get("points") or []
                    ],
                )
            return (
                [_("Country"), _("Value")],
                [
                    [region["label"], region["value"]]
                    for region in data.get("regions") or []
                ],
            )
        if self.item_type == "scatter":
            data = self._get_data(params)
            points = data["datasets"][0]["data"]
            return (
                [
                    self.group_by_field_id.field_description or _("Label"),
                    self.measure_x_field_id.field_description,
                    self.measure_y_field_id.field_description,
                ],
                [
                    [label, point["x"], point["y"]]
                    for label, point in zip(data["labels"], points, strict=True)
                ],
            )
        if self.item_type == "list":
            data = self._get_data(
                dict(
                    params,
                    offset=0,
                    no_pagination=True,
                    export_max_rows=EXPORT_MAX_ROWS,
                )
            )
            rows = data["rows"][:EXPORT_MAX_ROWS]
            return (
                [column["label"] for column in data["columns"]],
                [row["values"] for row in rows],
            )
        # Remaining types (bar, line, pie, funnel, bullet, ...) share the
        # labels/datasets payload.
        data = self._get_data(params)
        headers = [self.group_by_field_id.field_description or _("Label")] + [
            dataset["label"] for dataset in data["datasets"]
        ]
        rows = [
            [label] + [dataset["data"][index] for dataset in data["datasets"]]
            for index, label in enumerate(data["labels"])
        ]
        return headers, rows

    # ------------------------------------------------------------------
    # Export / import
    # ------------------------------------------------------------------

    _EXPORT_SIMPLE_FIELDS = [
        "name",
        "description",
        "sequence",
        "item_type",
        "domain",
        "date_filter",
        "date_from",
        "date_to",
        "group_by_granularity",
        "subgroup_by_granularity",
        "boolean_true_label",
        "boolean_false_label",
        "aggregation",
        "record_limit",
        "chart_sort",
        "stacked",
        "legend_visible",
        "show_average_line",
        "show_trend_line",
        "kpi_mode",
        "kpi_display",
        "compare_previous_period",
        "domain_2",
        "aggregation_2",
        "target_enabled",
        "target_value",
        "gauge_max",
        "map_mode",
        "list_type",
        "page_size",
        "sort_dir",
        "icon",
        "background_style",
        "background_color",
        "font_color",
        "color_palette",
        "number_style",
        "unit_type",
        "unit_symbol",
        "show_records",
    ]
    _EXPORT_FIELD_M2O = [
        ("date_field_id", "model_id"),
        ("subgroup_by_field_id", "model_id"),
        ("measure_field_id", "model_id"),
        ("measure_x_field_id", "model_id"),
        ("measure_y_field_id", "model_id"),
        ("map_relation_field_id", "model_id"),
        ("date_field_2_id", "model_2_id"),
        ("measure_field_2_id", "model_2_id"),
    ]
    # Fields that may live on a related model, so the owning model travels
    # with them: the funnel Sort By, and the map coordinates and country.
    _EXPORT_FIELD_M2O_WITH_MODEL = [
        ("sort_field_id", "sort_field_model"),
        ("group_by_field_id", "group_by_field_model"),
        ("latitude_field_id", "map_field_model"),
        ("longitude_field_id", "map_field_model"),
    ]

    def _export_config(self):
        self.ensure_one()
        data = {field: self[field] for field in self._EXPORT_SIMPLE_FIELDS}
        # Datetime fields must serialize as strings for the JSON payload.
        data["date_from"] = fields.Datetime.to_string(self.date_from) or False
        data["date_to"] = fields.Datetime.to_string(self.date_to) or False
        data["model"] = self.model_name
        data["model_2"] = self.model_2_name or False
        for field_name, __ in self._EXPORT_FIELD_M2O:
            data[field_name] = self[field_name].name or False
        data["measures"] = self._ordered_measure_fields().mapped("name")
        data["map_focus_country_id"] = self.map_focus_country_id.code or False
        data["palette"] = self.palette_id.name or False
        for field_name, model_key in self._EXPORT_FIELD_M2O_WITH_MODEL:
            field = self[field_name]
            data[field_name] = field.name or False
            data[model_key] = field.model or data.get(model_key) or False
        data["list_columns"] = self.list_column_ids.mapped("field_id.name")
        data["drill_levels"] = [
            {
                "sequence": level.sequence,
                "group_by_field_id": level.group_by_field_id.name,
                "group_by_granularity": level.group_by_granularity,
                "chart_type": level.chart_type,
                "chart_sort": level.chart_sort,
                "record_limit": level.record_limit,
            }
            for level in self.drill_level_ids
        ]
        return data

    @api.model
    def _import_field_id(self, model_rec, field_name):
        """Resolve an exported field name into an ir.model.fields id."""
        if not model_rec or not field_name:
            return False
        field = self.env["ir.model.fields"]._get(model_rec.model, field_name)
        return field.id if field else False

    @api.model
    def _import_line_commands(self, model_rec, field_names):
        """Build ordered (sequence, field_id) lines out of exported names."""
        commands = []
        for index, name in enumerate(field_names or []):
            field = self._import_field_id(model_rec, name)
            if field:
                commands.append(
                    (0, 0, {"sequence": (index + 1) * 10, "field_id": field})
                )
        return commands

    @api.model
    def _import_drill_commands(self, model_rec, drill_levels):
        commands = []
        for index, level_data in enumerate(drill_levels or []):
            if not isinstance(level_data, dict):
                continue
            field = self._import_field_id(
                model_rec, level_data.get("group_by_field_id")
            )
            if not field:
                continue
            commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": level_data.get("sequence") or (index + 1) * 10,
                        "group_by_field_id": field,
                        "group_by_granularity": level_data.get("group_by_granularity")
                        or "month",
                        "chart_type": level_data.get("chart_type") or "bar",
                        "chart_sort": level_data.get("chart_sort") or "default",
                        "record_limit": level_data.get("record_limit") or 0,
                    },
                )
            )
        return commands

    @api.model
    def _import_prepare_vals(self, data, dashboard_id):
        model = self.env["ir.model"]._get(data.get("model") or "")
        if not model:
            return None
        vals = {
            field: data[field] for field in self._EXPORT_SIMPLE_FIELDS if field in data
        }
        vals.update({"dashboard_id": dashboard_id, "model_id": model.id})
        model_2 = self.env["ir.model"]._get(data.get("model_2") or "")
        vals["model_2_id"] = model_2.id if model_2 else False
        for field_name, model_field in self._EXPORT_FIELD_M2O:
            source = model if model_field == "model_id" else model_2
            vals[field_name] = self._import_field_id(source, data.get(field_name))
        # Older payloads have no owning model, so they resolve on the item model.
        for field_name, model_key in self._EXPORT_FIELD_M2O_WITH_MODEL:
            field_model = self.env["ir.model"]._get(
                data.get(model_key) or data.get("model") or ""
            )
            vals[field_name] = self._import_field_id(field_model, data.get(field_name))
        focus_code = data.get("map_focus_country_id")
        if focus_code:
            country = self.env["res.country"].search(
                [("code", "=", str(focus_code).upper())], limit=1
            )
            vals["map_focus_country_id"] = country.id
        else:
            vals["map_focus_country_id"] = False
        palette_name = data.get("palette")
        palette = (
            self.env["boardkit.dashboard.palette"].search(
                [("name", "=", palette_name)], limit=1
            )
            if palette_name
            else self.env["boardkit.dashboard.palette"]
        )
        vals["palette_id"] = palette.id if palette else False
        if vals.get("color_palette") == "custom" and not vals["palette_id"]:
            # The palette could not be resolved on this database.
            vals["color_palette"] = "default"
        # Prefer the ordered list_columns key; fall back to legacy list_field_ids.
        column_names = data.get("list_columns")
        if column_names is None:
            column_names = data.get("list_field_ids")
        column_commands = self._import_line_commands(model, column_names)
        if column_commands:
            vals["list_column_ids"] = column_commands
        # Prefer the ordered measures key; fall back to the legacy many2many.
        measure_names = data.get("measures")
        if measure_names is None:
            measure_names = data.get("measure_field_ids")
        measure_commands = self._import_line_commands(model, measure_names)
        if measure_commands:
            vals["measure_ids"] = measure_commands
        drill_commands = self._import_drill_commands(model, data.get("drill_levels"))
        if drill_commands:
            vals["drill_level_ids"] = drill_commands
        return vals
