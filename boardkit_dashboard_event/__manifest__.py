# Copyright 2026 Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Boardkit Dashboard Event",
    "summary": "Events overview dashboard template for Boardkit",
    "category": "Marketing/Events",
    "version": "18.0.1.0.0",
    "website": "https://github.com/Escodoo/odoo-boardkit",
    "author": "Escodoo",
    "maintainers": ["marcelsavegnago"],
    "development_status": "Beta",
    "license": "AGPL-3",
    "depends": ["boardkit_dashboard", "event"],
    "data": [
        "data/boardkit_dashboard_templates.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "demo": ["demo/boardkit_dashboard_demo.xml"],
    "auto_install": True,
    "installable": True,
}
