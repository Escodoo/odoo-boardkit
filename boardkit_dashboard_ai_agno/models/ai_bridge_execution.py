# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import html_sanitize


class AiBridgeExecution(models.Model):
    _inherit = "ai.bridge.execution"

    def _process_response_boardkit(self, response):
        """Return the Agno payload to the Boardkit OWL / wizard callers."""
        self.ensure_one()
        if not isinstance(response, dict):
            return {"body": "", "body_is_html": True}
        body = response.get("body") or ""
        body_is_html = bool(response.get("body_is_html", True))
        if body_is_html and body:
            body = html_sanitize(body)
        return {
            "body": body,
            "body_is_html": body_is_html,
            "payload": response.get("payload"),
            "name": response.get("name") or False,
            "actions": response.get("actions") or [],
        }
