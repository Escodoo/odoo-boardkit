# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .boardkit_dashboard import FEATURED_TEMPLATE_KEYS


class BoardkitDashboardTemplate(models.Model):
    _name = "boardkit.dashboard.template"
    _description = "Boardkit Dashboard Template"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    key = fields.Char(
        required=True,
        copy=False,
        help="Stable technical identifier used in data and tests.",
    )
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="boardkit_dashboard_template_group_rel",
        column1="template_id",
        column2="group_id",
        string="Allowed Groups",
        help="Copied to boards created from this template. Restrict who can "
        "open the dashboard and its menu entry. Leave empty to allow every "
        "Dashboard User only. Prefer the lowest app group that matches the "
        "template KPIs; managers already inherit implied user groups.",
    )
    payload = fields.Json(
        string="Payload Data",
        required=True,
        help="Dashboard export structure (version + dashboards) used by import_config.",
    )
    # Json fields have no default form widget in web; expose a Text editor so
    # managers can inspect and edit the curated export payload.
    payload_text = fields.Text(
        string="Payload",
        compute="_compute_payload_text",
        inverse="_inverse_payload_text",
        help="JSON export structure shown for editing. Must stay a valid object "
        "with a dashboards list.",
    )

    _sql_constraints = [
        ("key_uniq", "unique(key)", "Template key must be unique."),
    ]

    @api.model
    def _normalize_payload(self, payload):
        """Accept dicts or JSON strings (XML data files store text)."""
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as error:
                raise ValidationError(
                    _("Template payload is not valid JSON: %s", error)
                ) from error
        return payload

    @api.depends("payload")
    def _compute_payload_text(self):
        for template in self:
            payload = template._normalize_payload(template.payload)
            template.payload_text = (
                json.dumps(payload, indent=2, ensure_ascii=False) if payload else ""
            )

    def _inverse_payload_text(self):
        for template in self:
            template.payload = template._normalize_payload(
                template.payload_text or "{}"
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "payload" in vals:
                vals["payload"] = self._normalize_payload(vals["payload"])
        return super().create(vals_list)

    def write(self, vals):
        if "payload" in vals:
            vals = dict(vals, payload=self._normalize_payload(vals["payload"]))
        return super().write(vals)

    def get_payload(self):
        """Return a deep-copy-ready dict payload for import_config."""
        self.ensure_one()
        return self._normalize_payload(self.payload)

    @api.model
    def get_featured_for_catalogue(self):
        """Return curated templates for the empty catalogue hero."""
        templates = self.search(
            [("active", "=", True), ("key", "in", list(FEATURED_TEMPLATE_KEYS))]
        )
        by_key = {template.key: template for template in templates}
        featured = []
        for key in FEATURED_TEMPLATE_KEYS:
            template = by_key.get(key)
            if not template:
                continue
            featured.append(
                {
                    "id": template.id,
                    "key": template.key,
                    "name": template.name,
                    "description": template.description or "",
                }
            )
        return featured
