# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import traceback
from io import StringIO

import requests

from odoo import models
from odoo.tools import html_sanitize


class AiBridgeExecution(models.Model):
    _inherit = "ai.bridge.execution"

    def _execute(self, **kwargs):
        """Honor the Boardkit request timeout on Odoo 16.

        LLM-backed Agno endpoints routinely answer after the 30 seconds that
        ``ai_oca_bridge`` hardcodes, and ``ai_oca_bridge_request_timeout`` only
        exists for Odoo 18. Boardkit passes the timeout in the context; the
        request below mirrors the upstream ``_execute`` with that timeout.
        """
        self.ensure_one()
        timeout = self.env.context.get("boardkit_request_timeout")
        if not timeout or self.ai_bridge_id.payload_type != "boardkit":
            return super()._execute(**kwargs)
        record = None
        if self.res_id and self.model_id:
            record = self.env[self.sudo().model_id.model].browse(self.res_id)
        payload = self.ai_bridge_id._prepare_payload(
            record=record,
            res_id=self.res_id,
            model=self.sudo().model_id.model,
            **kwargs,
        )
        payload = self._add_extra_payload_fields(payload)
        request_kwargs = self._execute_kwargs(**kwargs)
        request_kwargs.pop("timeout", None)
        try:
            response = requests.post(
                self.ai_bridge_id.url,
                json=payload,
                auth=self._get_auth(),
                headers=self._get_headers(),
                timeout=timeout,
                **request_kwargs,
            )
            self.result = response.content
            response.raise_for_status()
            self.state = "done"
            self.payload = payload
            if self.ai_bridge_id.result_kind == "immediate":
                return self._process_response(response.json())
        except Exception:
            self.state = "error"
            self.payload = payload
            buff = StringIO()
            traceback.print_exc(file=buff)
            self.error = buff.getvalue()
            buff.close()

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
