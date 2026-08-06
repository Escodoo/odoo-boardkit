# Copyright 2026 Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Boardkit Dashboard",
    "summary": "Configurable analytic dashboards with tiles, KPIs, charts and lists",
    "category": "Productivity",
    "version": "18.0.1.0.0",
    "website": "https://github.com/Escodoo/odoo-boardkit",
    "author": "Escodoo",
    "maintainers": ["marcelsavegnago"],
    "development_status": "Beta",
    "license": "AGPL-3",
    "depends": ["web", "web_tour", "contacts"],
    "data": [
        "security/boardkit_dashboard_security.xml",
        "security/ir.model.access.csv",
        "data/boardkit_dashboard_templates.xml",
        "views/boardkit_dashboard_item_views.xml",
        "views/boardkit_dashboard_palette_views.xml",
        "views/boardkit_dashboard_tag_views.xml",
        "views/boardkit_dashboard_template_views.xml",
        "views/boardkit_dashboard_views.xml",
        "views/res_config_settings_views.xml",
        "views/boardkit_dashboard_menus.xml",
    ],
    "demo": ["demo/boardkit_dashboard_demo.xml"],
    "assets": {
        "web.assets_backend": [
            "boardkit_dashboard/static/src/catalogue/**/*",
            "boardkit_dashboard/static/src/dashboard/**/*",
            "boardkit_dashboard/static/src/fields/**/*",
        ],
        "boardkit_dashboard.chartjs_extensions": [
            "boardkit_dashboard/static/lib/chartjs-chart-funnel.umd.min.js",
            "boardkit_dashboard/static/lib/chartjs-chart-geo.umd.min.js",
            "boardkit_dashboard/static/lib/countries_110m.js",
        ],
        "web.assets_tests": [
            "boardkit_dashboard/static/tests/tours/**/*",
        ],
    },
    "images": [
        "static/description/banner.png",
    ],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
