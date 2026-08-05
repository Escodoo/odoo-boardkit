# Copyright 2026 Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Boardkit Dashboard Time Off",
    "summary": "Time Off overview dashboard template for Boardkit",
    "category": "Human Resources/Time Off",
    "version": "18.0.1.0.0",
    "website": "https://github.com/Escodoo/odoo-boardkit",
    "author": "Escodoo",
    "maintainers": ["marcelsavegnago"],
    "development_status": "Beta",
    "license": "AGPL-3",
    "depends": ["boardkit_dashboard", "hr_holidays"],
    "data": [
        "data/boardkit_dashboard_templates.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "auto_install": True,
    "installable": True,
}
