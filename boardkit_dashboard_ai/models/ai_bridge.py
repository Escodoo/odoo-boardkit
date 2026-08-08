# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import fields, models


class AiBridge(models.Model):
    _inherit = "ai.bridge"

    payload_type = fields.Selection(
        selection_add=[("boardkit", "Boardkit Snapshot")],
        ondelete={"boardkit": "set default"},
    )
    result_type = fields.Selection(
        selection_add=[("boardkit", "Return Boardkit Result")],
        ondelete={"boardkit": "set default"},
    )

    def _prepare_payload_boardkit(
        self,
        record=None,
        snapshot=None,
        filters=None,
        prompt=None,
        item=None,
        message=None,
        history=None,
        res_model=False,
        res_id=False,
        model=False,
        **kwargs,
    ):
        """Prepare a Boardkit-specific payload for the Agno service."""
        self.ensure_one()
        # ai.bridge.execution._execute passes model=/res_id=; keep res_model alias.
        model_name = (
            res_model or model or (record._name if record else False) or False
        )
        record_id = res_id if res_id not in (None, False) else (
            record.id if record else False
        )
        return json.loads(
            json.dumps(
                {
                    "_model": model_name,
                    "_id": record_id,
                    "snapshot": snapshot or {},
                    "filters": filters or {},
                    "prompt": prompt or False,
                    "item": item or False,
                    "message": message or False,
                    "history": history or [],
                },
                default=self.custom_serializer,
            )
        )
