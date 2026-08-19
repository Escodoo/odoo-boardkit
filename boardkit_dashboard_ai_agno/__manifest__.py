# Copyright 2026 Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Boardkit Dashboard AI (Agno)",
    "summary": "Board chat, insights, tile explanations and NL generation via Agno",
    "category": "Productivity",
    "version": "18.0.1.0.0",
    "website": "https://github.com/Escodoo/odoo-boardkit",
    "author": "Escodoo",
    "maintainers": ["marcelsavegnago"],
    "development_status": "Beta",
    "license": "AGPL-3",
    "depends": [
        "boardkit_dashboard",
        "ai_oca_bridge",
        "ai_oca_bridge_provider",
        "ai_oca_bridge_request_timeout",
        "ai_agno_connector",
    ],
    "data": [
        "security/boardkit_dashboard_ai_agno_security.xml",
        "security/ir.model.access.csv",
        "data/ai_bridge_data.xml",
        "views/boardkit_dashboard_views.xml",
        "views/boardkit_dashboard_ai_generate_wizard_views.xml",
        "views/boardkit_dashboard_ai_agno_menus.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "assets": {
        "web.assets_backend": [
            "boardkit_dashboard_ai_agno/static/src/dashboard/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
}
