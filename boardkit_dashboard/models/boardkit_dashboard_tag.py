# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from random import randint

from odoo import api, fields, models

# Suggested Font Awesome class when creating/migrating tags by well-known name.
# Catalogue icons are stored on the tag; this map is seed only.
SUGGESTED_TAG_ICONS = {
    "crm": "fa-bullseye",
    "contacts": "fa-address-book",
    "mail": "fa-envelope",
    "personal": "fa-sun-o",
    "inventory": "fa-cubes",
    "sales": "fa-shopping-cart",
    "sale": "fa-shopping-cart",
    "timesheets": "fa-clock-o",
    "timesheet": "fa-clock-o",
    "hr": "fa-users",
    "employee contracts": "fa-id-card-o",
    "repair": "fa-wrench",
    "purchase": "fa-shopping-basket",
    "project": "fa-tasks",
    "helpdesk": "fa-life-ring",
    "fleet": "fa-car",
    "manufacturing": "fa-cogs",
    "maintenance": "fa-wrench",
    "payroll": "fa-money",
    "recruitment": "fa-user-plus",
    "attendance": "fa-calendar-check-o",
    "expenses": "fa-credit-card",
    "time off": "fa-plane",
    "field service": "fa-map-marker",
    "invoicing": "fa-file-text-o",
    "accounting": "fa-file-text-o",
}

TAG_ICON_SELECTION = [
    ("fa-bullseye", "Target"),
    ("fa-address-book", "Address Book"),
    ("fa-envelope", "Envelope"),
    ("fa-sun-o", "Sun"),
    ("fa-cubes", "Cubes"),
    ("fa-shopping-cart", "Shopping Cart"),
    ("fa-clock-o", "Clock"),
    ("fa-users", "Users"),
    ("fa-id-card-o", "ID Card"),
    ("fa-wrench", "Wrench"),
    ("fa-shopping-basket", "Shopping Basket"),
    ("fa-tasks", "Tasks"),
    ("fa-life-ring", "Life Ring"),
    ("fa-car", "Car"),
    ("fa-cogs", "Cogs"),
    ("fa-money", "Money"),
    ("fa-user-plus", "User Plus"),
    ("fa-calendar-check-o", "Calendar Check"),
    ("fa-credit-card", "Credit Card"),
    ("fa-plane", "Plane"),
    ("fa-map-marker", "Map Marker"),
    ("fa-file-text-o", "File"),
    ("fa-th-large", "Grid"),
]


class BoardkitDashboardTag(models.Model):
    _name = "boardkit.dashboard.tag"
    _description = "Boardkit Dashboard Tag"
    _order = "name"

    def _get_default_color(self):
        # Color 0 is treated as "Hide in kanban" by web.KanbanMany2ManyTagsField.
        return randint(1, 11)

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(
        string="Color Index",
        default=_get_default_color,
        help="Transparent tags (color 0) are not visible on dashboard kanban cards.",
    )
    icon = fields.Selection(
        selection=TAG_ICON_SELECTION,
        help="Default Font Awesome icon for catalogue cards. Boards without "
        "their own Icon inherit the first non-empty icon among their tags.",
    )

    @api.model
    def suggested_icon_for_name(self, name):
        """Return a seed icon class for a well-known tag name, or False."""
        if not name:
            return False
        return SUGGESTED_TAG_ICONS.get(name.strip().lower(), False)

    def init(self):
        """One-shot migrations for legacy tag defaults."""
        icp = self.env["ir.config_parameter"].sudo()
        # Color 0 is hidden in kanban many2many_tags; reassign legacy defaults.
        key_color = "boardkit_dashboard.tag_color0_migrated"
        if not icp.get_param(key_color):
            self.env.cr.execute(
                """
                UPDATE boardkit_dashboard_tag
                   SET color = ((id % 11) + 1)
                 WHERE color IS NULL OR color = 0
                """
            )
            icp.set_param(key_color, "1")

        # Seed icons for well-known template tag names (CRM, Purchase, …).
        key_icon = "boardkit_dashboard.tag_icon_seeded"
        if not icp.get_param(key_icon):
            self.env.cr.execute(
                """
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_name = 'boardkit_dashboard_tag'
                   AND column_name = 'icon'
                """
            )
            if self.env.cr.fetchone():
                for tag in self.search([("icon", "=", False)]):
                    suggested = self.suggested_icon_for_name(tag.name)
                    if suggested:
                        tag.write({"icon": suggested})
                icp.set_param(key_icon, "1")
