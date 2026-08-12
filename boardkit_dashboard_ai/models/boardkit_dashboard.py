# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.addons.boardkit_dashboard.tools.date_ranges import DATE_RANGE_PRESETS

_logger = logging.getLogger(__name__)

AI_USER_GROUP = "boardkit_dashboard_ai.group_dashboard_ai_user"
MANAGER_GROUP = "boardkit_dashboard.group_dashboard_manager"

# Keep Agno prompts small and focused on readable figures.
_MAX_SERIES_POINTS = 24
_MAX_LIST_ROWS = 10
_MAX_MAP_ENTRIES = 20

_BRIDGE_SUMMARY = "boardkit_dashboard_ai.ai_bridge_boardkit_summary"
_BRIDGE_EXPLAIN = "boardkit_dashboard_ai.ai_bridge_boardkit_explain"
_BRIDGE_GENERATE = "boardkit_dashboard_ai.ai_bridge_boardkit_generate"
_BRIDGE_CHAT = "boardkit_dashboard_ai.ai_bridge_boardkit_chat"

_AI_CHAT_HISTORY_LIMIT = 10
_AI_CHAT_MESSAGE_MAX_LEN = 2000
_AI_CHAT_CUSTOM_FILTER_OPS = frozenset(
    {
        "=",
        "!=",
        ">",
        ">=",
        "<",
        "<=",
        "like",
        "ilike",
        "not like",
        "not ilike",
        "in",
        "not in",
        "child_of",
        "parent_of",
    }
)


class BoardkitDashboard(models.Model):
    _inherit = "boardkit.dashboard"

    ai_enabled = fields.Boolean(
        string="Enable AI",
        default=True,
        help="Allow AI chat, summary and tile explanations on this dashboard "
        "for users with the Use AI on Dashboards right.",
    )

    @api.model
    def get_dashboard_data(self, dashboard_id):
        data = super().get_dashboard_data(dashboard_id)
        if data:
            dashboard = self.browse(dashboard_id)
            data["ai_enabled"] = bool(
                dashboard.ai_enabled and self.env.user.has_group(AI_USER_GROUP)
            )
            data["ai_can_generate"] = self.env.user.has_group(
                AI_USER_GROUP
            ) and self.env.user.has_group(MANAGER_GROUP)
        return data

    def _check_ai_user(self):
        if not self.env.user.has_group(AI_USER_GROUP):
            raise AccessError(_("You are not allowed to use AI on dashboards."))

    def _check_ai_on_dashboard(self):
        """Require group right and per-dashboard AI toggle."""
        self.ensure_one()
        self._check_ai_user()
        if not self.ai_enabled:
            raise UserError(_("AI features are disabled on this dashboard."))

    def _check_ai_manager(self):
        self._check_ai_user()
        if not self.env.user.has_group(MANAGER_GROUP):
            raise AccessError(_("Only dashboard managers can generate boards with AI."))

    def action_ai_summarize(self, params=None):
        """Build a snapshot of the board and return an AI narrative."""
        self.ensure_one()
        self.check_access("read")
        self._check_ai_on_dashboard()
        snapshot = self._prepare_ai_snapshot(params)
        return self._run_boardkit_bridge(
            _BRIDGE_SUMMARY,
            record=self,
            snapshot=snapshot,
            filters=params or {},
        )

    def action_ai_explain_item(self, item_id, params=None):
        """Explain a single tile/KPI/chart with the current filter context."""
        self.ensure_one()
        self.check_access("read")
        self._check_ai_on_dashboard()
        item = self.env["boardkit.dashboard.item"].browse(item_id)
        item.check_access("read")
        if item.dashboard_id != self:
            raise ValidationError(_("The item does not belong to this dashboard."))
        item_snapshot = self._compact_item_payload(item, params)
        board_snapshot = {
            "id": self.id,
            "name": self.name,
            "description": self.description or False,
        }
        return self._run_boardkit_bridge(
            _BRIDGE_EXPLAIN,
            record=self,
            snapshot=board_snapshot,
            item=item_snapshot,
            filters=params or {},
        )

    def action_ai_chat(self, params=None, message=None, history=None):
        """Answer a question about the board using the current filter snapshot."""
        self.ensure_one()
        self.check_access("read")
        self._check_ai_on_dashboard()
        text = (message or "").strip()
        if not text:
            raise UserError(_("Please enter a question about this dashboard."))
        if len(text) > _AI_CHAT_MESSAGE_MAX_LEN:
            text = text[:_AI_CHAT_MESSAGE_MAX_LEN]
        snapshot = self._prepare_ai_snapshot(params)
        result = self._run_boardkit_bridge(
            _BRIDGE_CHAT,
            record=self,
            snapshot=snapshot,
            filters=params or {},
            message=text,
            history=self._normalize_ai_chat_history(history),
        )
        actions = self._sanitize_ai_chat_actions(result.get("actions"))
        return {
            "body": result.get("body") or "",
            "body_is_html": bool(result.get("body_is_html", True)),
            "actions": actions,
        }

    @api.model
    def _normalize_ai_chat_history(self, history):
        """Keep a short, sanitized chat history for the Agno bridge."""
        if not history:
            return []
        if not isinstance(history, list):
            return []
        cleaned = []
        for entry in history[-_AI_CHAT_HISTORY_LIMIT:]:
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            content = (entry.get("content") or "").strip()
            if role not in ("user", "assistant") or not content:
                continue
            if len(content) > _AI_CHAT_MESSAGE_MAX_LEN:
                content = content[:_AI_CHAT_MESSAGE_MAX_LEN]
            cleaned.append({"role": role, "content": content})
        return cleaned

    def _sanitize_ai_chat_actions(self, actions):
        """Validate AI filter actions against this board before OWL runs them."""
        self.ensure_one()
        if not isinstance(actions, list):
            return []
        allowed_presets = dict(DATE_RANGE_PRESETS)
        known_filter_ids = set(self.filter_ids.ids)
        allowed_models = set(self.item_ids.mapped("model_name"))
        cleaned = []
        for entry in actions[:5]:
            if not isinstance(entry, dict) or entry.get("type") != "apply_filters":
                continue
            filters = entry.get("filters")
            if not isinstance(filters, dict):
                continue
            sanitized = {}
            preset = filters.get("date_preset")
            if isinstance(preset, str) and preset in allowed_presets:
                sanitized["date_preset"] = preset
                if preset == "custom":
                    date_from = filters.get("date_from")
                    date_to = filters.get("date_to")
                    if not (
                        isinstance(date_from, str)
                        and isinstance(date_to, str)
                        and date_from
                        and date_to
                    ):
                        # Incomplete custom range: drop the date change.
                        sanitized.pop("date_preset", None)
                    else:
                        sanitized["date_from"] = date_from
                        sanitized["date_to"] = date_to
            if "filter_ids" in filters:
                ids = []
                for value in filters.get("filter_ids") or []:
                    try:
                        filter_id = int(value)
                    except (TypeError, ValueError):
                        continue
                    if filter_id in known_filter_ids:
                        ids.append(filter_id)
                sanitized["filter_ids"] = ids
            if "custom_filters" in filters:
                sanitized["custom_filters"] = self._sanitize_ai_custom_filters(
                    filters.get("custom_filters"), allowed_models
                )
            if sanitized:
                cleaned.append({"type": "apply_filters", "filters": sanitized})
        return cleaned

    @api.model
    def _sanitize_ai_custom_filters(self, custom_filters, allowed_models):
        if not isinstance(custom_filters, list):
            return []
        cleaned = []
        for entry in custom_filters[:10]:
            if not isinstance(entry, dict):
                continue
            model = entry.get("model")
            field_name = entry.get("field")
            operator = entry.get("operator")
            if (
                not isinstance(model, str)
                or model not in allowed_models
                or not isinstance(field_name, str)
                or not field_name
                or operator not in _AI_CHAT_CUSTOM_FILTER_OPS
            ):
                continue
            cleaned.append(
                {
                    "model": model,
                    "field": field_name,
                    "operator": operator,
                    "value": entry.get("value"),
                    "label": entry.get("label") or False,
                    "modelLabel": entry.get("modelLabel")
                    or entry.get("model_label")
                    or False,
                }
            )
        return cleaned

    def export_config(self):
        payload = super().export_config()
        for dashboard, data in zip(self, payload.get("dashboards") or [], strict=False):
            data["ai_enabled"] = bool(dashboard.ai_enabled)
        return payload

    @api.model
    def import_config(self, payload):
        dashboard_ids = super().import_config(payload)
        boards = self.browse(dashboard_ids)
        for dashboard, data in zip(
            boards, payload.get("dashboards") or [], strict=False
        ):
            if isinstance(data, dict) and "ai_enabled" in data:
                dashboard.ai_enabled = bool(data.get("ai_enabled"))
        return dashboard_ids

    @api.model
    def action_ai_generate(self, prompt, example_template_keys=None):
        """Ask Agno for an import_config payload and create unpublished boards."""
        self._check_ai_manager()
        prompt = (prompt or "").strip()
        if not prompt:
            raise UserError(_("Please describe the dashboard you want to create."))
        examples = self._prepare_ai_generate_examples(example_template_keys)
        result = self._run_boardkit_bridge(
            _BRIDGE_GENERATE,
            record=self.browse(),
            prompt=prompt,
            snapshot={"examples": examples},
            filters={},
            res_model="boardkit.dashboard",
            res_id=0,
        )
        payload = result.get("payload")
        if not payload:
            body = (result.get("body") or "").strip()
            if body:
                payload = self._extract_json_payload(body)
        if not payload:
            raise UserError(_("The AI response did not include a valid dashboard."))
        payload = self._normalize_ai_import_payload(payload)
        dashboard_ids = self.import_config(payload)
        return {
            "dashboard_ids": dashboard_ids,
            "body": result.get("body") or "",
            "name": result.get("name") or False,
        }

    def _prepare_ai_snapshot(self, params=None):
        """Compact board + item data for the Boardkit Analyst prompt."""
        self.ensure_one()
        params = params or {}
        items = []
        for item in self.item_ids.sorted("sequence"):
            items.append(self._compact_item_payload(item, params))
        date_presets = [
            {"key": key, "label": label}
            for key, label in self._fields["date_filter"]._description_selection(
                self.env
            )
        ]
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description or False,
            "date_filter": self.date_filter,
            "date_presets": date_presets,
            "filters": [
                {
                    "id": board_filter.id,
                    "name": board_filter.name,
                    "model": board_filter.model_name,
                    "default_enabled": board_filter.default_enabled,
                }
                for board_filter in self.filter_ids
            ],
            "active_filter_ids": params.get("filter_ids") or [],
            "custom_filters": params.get("custom_filters") or [],
            "date_preset": params.get("date_preset") or self.date_filter,
            "items": items,
        }

    def _compact_item_payload(self, item, params=None):
        params = params or {}
        config = {
            "id": item.id,
            "name": item.name,
            "description": item.description or False,
            "item_type": item.item_type,
            "model": item.model_name,
            "domain": item.domain or "[]",
            "aggregation": item.aggregation or False,
            "measure_field": item.measure_field_id.name
            if item.measure_field_id
            else False,
            "group_by_field": item.group_by_field_id.name
            if item.group_by_field_id
            else False,
        }
        data = item.get_data(params)
        config["data"] = self._compact_item_data(data)
        return config

    def _compact_item_data(self, data):
        if not isinstance(data, dict):
            return {"value": data}
        if data.get("error"):
            return {"error": data["error"]}
        compact = {"type": data.get("type") or data.get("item_type")}
        for key in (
            "value",
            "formatted_value",
            "previous_value",
            "variation",
            "variation_percent",
            "target",
            "max_value",
            "min_value",
            "unit",
            "label",
            "count",
        ):
            if key in data:
                compact[key] = data[key]
        if "labels" in data and "datasets" in data:
            labels = list(data.get("labels") or [])[:_MAX_SERIES_POINTS]
            datasets = []
            for dataset in data.get("datasets") or []:
                values = list(dataset.get("data") or [])[:_MAX_SERIES_POINTS]
                datasets.append(
                    {
                        "label": dataset.get("label") or dataset.get("name") or False,
                        "data": values,
                    }
                )
            compact["labels"] = labels
            compact["datasets"] = datasets
        elif "series" in data and isinstance(data["series"], list):
            compact["series"] = data["series"][:_MAX_SERIES_POINTS]
        if "rows" in data and isinstance(data["rows"], list):
            compact["rows"] = data["rows"][:_MAX_LIST_ROWS]
        if "regions" in data and isinstance(data["regions"], list):
            compact["regions"] = data["regions"][:_MAX_MAP_ENTRIES]
        if "points" in data and isinstance(data["points"], list):
            compact["points"] = data["points"][:_MAX_MAP_ENTRIES]
        return compact

    def _prepare_ai_generate_examples(self, example_template_keys=None):
        """Return compact export samples from curated templates (few-shot)."""
        Template = self.env["boardkit.dashboard.template"]
        templates = Template.browse()
        keys = [key for key in (example_template_keys or []) if key]
        if keys:
            templates = Template.search([("key", "in", keys), ("active", "=", True)])
        if not templates:
            templates = Template.search([("active", "=", True)], limit=3, order="id")
        examples = []
        for template in templates:
            payload = template.payload or {}
            dashboards = payload.get("dashboards") or []
            if not dashboards:
                continue
            board = dashboards[0]
            examples.append(
                {
                    "key": template.key,
                    "name": template.name,
                    "sample": {
                        "name": board.get("name"),
                        "items": [
                            {
                                "name": item.get("name"),
                                "item_type": item.get("item_type"),
                                "model": item.get("model"),
                                "aggregation": item.get("aggregation"),
                                "measure_field_id": item.get("measure_field_id"),
                                "group_by_field_id": item.get("group_by_field_id"),
                            }
                            for item in (board.get("items") or [])[:8]
                        ],
                    },
                }
            )
        return examples

    @api.model
    def _normalize_ai_domain(self, domain):
        """Convert AI domains to Python literals safe for ``safe_eval``.

        LLMs often emit JSON-style ``true`` / ``false`` / ``null`` (or Python
        ``None``) inside domain strings. Odoo domains use ``True`` / ``False``;
        empty Many2one / unset checks must use ``False`` (``=`` → is not set,
        ``!=`` → is set). Bare ``None``/``null`` values are invalid in the
        domain selector.
        """
        if domain in (None, False, ""):
            return "[]"
        if isinstance(domain, list | tuple):
            return repr(self._ai_domain_pythonize(domain))
        if not isinstance(domain, str):
            return "[]"
        text = domain.strip() or "[]"
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list | tuple):
            return repr(self._ai_domain_pythonize(parsed))
        # Already a Python-like domain string; still fix bare JSON/Python tokens.
        text = re.sub(r"\btrue\b", "True", text, flags=re.IGNORECASE)
        text = re.sub(r"\bfalse\b", "False", text, flags=re.IGNORECASE)
        # Unset checks: null/None → False (never leave None in domain RHS).
        text = re.sub(r"\bnull\b", "False", text, flags=re.IGNORECASE)
        text = re.sub(r"\bNone\b", "False", text)
        return text

    @api.model
    def _ai_domain_pythonize(self, value):
        """Recursively map JSON-decoded domain values to Python domain terms."""
        if isinstance(value, list):
            return [self._ai_domain_pythonize(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._ai_domain_pythonize(item) for item in value)
        # Odoo empty/unset domain value is False, not None.
        if value is None:
            return False
        return value

    _AI_AGGREGATIONS = frozenset({"count", "sum", "avg"})
    _AI_ITEM_TYPES = frozenset(
        {
            "tile",
            "kpi",
            "bar",
            "bar_horizontal",
            "line",
            "area",
            "pie",
            "doughnut",
            "polar",
            "radar",
            "scatter",
            "funnel",
            "gauge",
            "bullet",
            "map",
            "list",
        }
    )

    @api.model
    def _normalize_ai_item(self, item):
        """Fill required item fields LLMs often omit or null out."""
        item = dict(item or {})
        item_type = item.get("item_type") or "tile"
        if item_type not in self._AI_ITEM_TYPES:
            # Common LLM alias.
            if item_type in ("chart", "graph"):
                item_type = "bar"
            else:
                item_type = "tile"
        item["item_type"] = item_type

        aggregation = item.get("aggregation") or "count"
        if aggregation not in self._AI_AGGREGATIONS:
            aggregation = "count"
        # sum/avg without a measure cannot be created reliably; fall back.
        has_measure = bool(
            item.get("measure_field_id")
            or item.get("measures")
            or item.get("measure_field_ids")
        )
        if aggregation in ("sum", "avg") and not has_measure:
            aggregation = "count"
        item["aggregation"] = aggregation

        aggregation_2 = item.get("aggregation_2")
        if aggregation_2 not in self._AI_AGGREGATIONS:
            item.pop("aggregation_2", None)
        elif aggregation_2 in ("sum", "avg") and not item.get("measure_field_2_id"):
            item["aggregation_2"] = "count"

        item["domain"] = self._normalize_ai_domain(item.get("domain") or "[]")
        if "domain_2" in item:
            item["domain_2"] = self._normalize_ai_domain(item.get("domain_2"))
        if not item.get("name"):
            item["name"] = _("AI Item")
        return item

    @api.model
    def _normalize_ai_import_payload(self, payload):
        """Normalize domains and required item fields before ``import_config``."""
        if not isinstance(payload, dict):
            return payload
        dashboards = []
        for board in payload.get("dashboards") or []:
            if not isinstance(board, dict):
                continue
            board = dict(board)
            items = []
            for item in board.get("items") or []:
                if not isinstance(item, dict):
                    continue
                items.append(self._normalize_ai_item(item))
            board["items"] = items
            filters = []
            for board_filter in board.get("filters") or []:
                if not isinstance(board_filter, dict):
                    continue
                board_filter = dict(board_filter)
                if "domain" in board_filter or board_filter.get("domain") is None:
                    board_filter["domain"] = self._normalize_ai_domain(
                        board_filter.get("domain")
                    )
                filters.append(board_filter)
            board["filters"] = filters
            dashboards.append(board)
        normalized = dict(payload)
        normalized["dashboards"] = dashboards
        return normalized

    @api.model
    def _extract_json_payload(self, text):
        """Best-effort extraction of a JSON object from an LLM body."""
        text = (text or "").strip()
        if not text:
            return False
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                return False
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return False
        if isinstance(data, dict) and "dashboards" in data:
            return data
        if isinstance(data, dict) and "payload" in data:
            nested = data.get("payload")
            if isinstance(nested, dict) and "dashboards" in nested:
                return nested
        return False

    def _run_boardkit_bridge(
        self, xmlid, record=None, res_model=None, res_id=None, **kwargs
    ):
        """Execute a Boardkit AI bridge and return the processed response."""
        bridge = self.env.ref(xmlid, raise_if_not_found=False)
        if not bridge:
            raise UserError(_("The Boardkit AI bridge is not configured."))
        if not bridge.active or (
            bridge.group_ids and not self.env.user.groups_id & bridge.group_ids
        ):
            raise UserError(_("%s is not active.", bridge.name))
        target = record if record is not None else self
        model_name = res_model or (target._name if target else "boardkit.dashboard")
        record_id = res_id if res_id is not None else (target.id if target else 0)
        model = self.env["ir.model"]._get(model_name)
        execution = (
            self.env["ai.bridge.execution"]
            .sudo()
            .create(
                {
                    "ai_bridge_id": bridge.id,
                    "model_id": model.id if model else False,
                    "res_id": record_id or 0,
                }
            )
        )
        # Do not pass record/res_id here: ai.bridge.execution._execute already
        # injects them into _prepare_payload and **kwargs would collide.
        result = execution._execute(**kwargs)
        if execution.state == "error":
            _logger.warning(
                "Boardkit AI bridge %s failed: %s",
                bridge.name,
                execution.error,
            )
            raise UserError(
                _(
                    "The AI request failed. Check the AI Bridge Execution log "
                    "for details."
                )
            )
        return result or {}
