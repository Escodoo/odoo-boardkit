# Copyright 2026 Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Boardkit Dashboard Brazilian Fiscal",
    "summary": "Brazilian fiscal documents overview dashboard template for Boardkit",
    "category": "Localisation",
    "version": "16.0.1.0.0",
    "website": "https://github.com/Escodoo/odoo-boardkit",
    "author": "Escodoo",
    "maintainers": ["marcelsavegnago"],
    "development_status": "Beta",
    "license": "AGPL-3",
    # On 16.0 the e-doc authorization states come from l10n_br_fiscal_edi.
    "depends": ["boardkit_dashboard", "l10n_br_fiscal_edi"],
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
