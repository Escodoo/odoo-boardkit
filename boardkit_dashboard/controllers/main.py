# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import codecs
import csv
import io
import json

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import content_disposition, request
from odoo.tools.misc import xlsxwriter

XLSX_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# Spreadsheet apps treat cells starting with these characters as formulas.
FORMULA_PREFIXES = ("=", "+", "-", "@")


class BoardkitDashboardController(http.Controller):
    @http.route(
        "/boardkit_dashboard/export/<int:dashboard_id>", type="http", auth="user"
    )
    def export_dashboard(self, dashboard_id):
        if not request.env.user.has_group("boardkit_dashboard.group_dashboard_manager"):
            raise Forbidden()
        dashboard = request.env["boardkit.dashboard"].browse(dashboard_id).exists()
        if not dashboard:
            raise request.not_found()
        payload = dashboard.export_config()
        filename = f"{dashboard.name or 'dashboard'}.json"
        return request.make_response(
            json.dumps(payload, indent=2, default=str),
            headers=[
                ("Content-Type", "application/json"),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )

    @http.route(
        "/boardkit_dashboard/import", type="http", auth="user", methods=["POST"]
    )
    def import_dashboard(self, ufile=None, **kwargs):
        """Create dashboards from an uploaded export file.

        Errors are reported in the payload instead of raising, so the
        uploader in the catalogue toolbar can surface them to the user.
        """
        if not request.env.user.has_group("boardkit_dashboard.group_dashboard_manager"):
            raise Forbidden()
        if not ufile:
            return request.make_json_response({"error": _("No file was uploaded.")})
        try:
            # Roll back partially imported records when the payload breaks
            # halfway through, since the error is swallowed below.
            with request.env.cr.savepoint():
                payload = json.loads(ufile.read())
                dashboard_ids = request.env["boardkit.dashboard"].import_config(payload)
        except (ValueError, TypeError, UserError) as error:
            return request.make_json_response({"error": str(error)})
        return request.make_json_response({"dashboard_ids": dashboard_ids})

    @http.route(
        "/boardkit_dashboard/item/<int:item_id>/export/<string:export_format>",
        type="http",
        auth="user",
    )
    def export_item_data(self, item_id, export_format, params=None):
        if export_format not in ("csv", "xlsx"):
            raise request.not_found()
        item = request.env["boardkit.dashboard.item"].browse(item_id).exists()
        if not item:
            raise request.not_found()
        try:
            item.check_access("read")
        except AccessError as error:
            # Match the manager-only export/import routes: return a plain 403
            # instead of letting AccessError become an odoo.http WARNING that
            # fails OCA checklog-odoo in CI.
            raise Forbidden() from error
        try:
            runtime_params = json.loads(params) if params else {}
        except ValueError:
            runtime_params = {}
        data = item.get_export_data(runtime_params)
        filename = f"{data['name'] or 'dashboard_item'}.{export_format}"
        if export_format == "csv":
            content, mimetype = self._to_csv(data), "text/csv;charset=utf-8"
        else:
            content, mimetype = self._to_xlsx(data), XLSX_MIMETYPE
        return request.make_response(
            content,
            headers=[
                ("Content-Type", mimetype),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )

    @staticmethod
    def _neutralize_formula(value):
        """Prefix formula-like strings so spreadsheet apps treat them as text."""
        if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
            return f"'{value}"
        return value

    @classmethod
    def _to_csv(cls, data):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([cls._neutralize_formula(header) for header in data["headers"]])
        for row in data["rows"]:
            writer.writerow([cls._neutralize_formula(value) for value in row])
        # BOM so spreadsheet applications detect the UTF-8 encoding.
        return codecs.BOM_UTF8 + buffer.getvalue().encode("utf-8")

    @staticmethod
    def _to_xlsx(data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(
            output, {"in_memory": True, "strings_to_formulas": False}
        )
        sheet = workbook.add_worksheet(data["name"])
        bold = workbook.add_format({"bold": True})
        for column, header in enumerate(data["headers"]):
            sheet.write(0, column, str(header), bold)
        for row_index, row in enumerate(data["rows"], start=1):
            for column, value in enumerate(row):
                sheet.write(row_index, column, value)
        workbook.close()
        return output.getvalue()
