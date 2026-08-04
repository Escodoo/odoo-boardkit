

# Odoo BoardKit Dashboard
<!-- /!\ Non OCA Context : Set here the badge of your runbot / runboat instance. -->
[![Pre-commit Status](https://github.com/Escodoo/odoo-boardkit/actions/workflows/pre-commit.yml/badge.svg?branch=18.0)](https://github.com/Escodoo/odoo-boardkit/actions/workflows/pre-commit.yml?query=branch%3A18.0)
[![Build Status](https://github.com/Escodoo/odoo-boardkit/actions/workflows/test.yml/badge.svg?branch=18.0)](https://github.com/Escodoo/odoo-boardkit/actions/workflows/test.yml?query=branch%3A18.0)
[![codecov](https://codecov.io/gh/Escodoo/odoo-boardkit/branch/18.0/graph/badge.svg)](https://codecov.io/gh/Escodoo/odoo-boardkit)
<!-- /!\ Non OCA Context : Set here the badge of your translation instance. -->

<!-- /!\ do not modify above this line -->

BoardKit for Odoo — an open source framework for building dynamic dashboards.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

Available addons
----------------
addon | version | maintainers | summary
--- | --- | --- | ---
[boardkit_dashboard](boardkit_dashboard/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Configurable analytic dashboards with tiles, KPIs, charts and lists
[boardkit_dashboard_account](boardkit_dashboard_account/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Invoicing dashboard template for Boardkit
[boardkit_dashboard_crm](boardkit_dashboard_crm/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | CRM pipeline dashboard template for Boardkit
[boardkit_dashboard_fieldservice](boardkit_dashboard_fieldservice/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Field Service overview dashboard template for Boardkit
[boardkit_dashboard_fleet](boardkit_dashboard_fleet/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Fleet overview dashboard template for Boardkit
[boardkit_dashboard_helpdesk_mgmt](boardkit_dashboard_helpdesk_mgmt/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Helpdesk overview dashboard template for Boardkit
[boardkit_dashboard_hr](boardkit_dashboard_hr/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Employees overview dashboard template for Boardkit
[boardkit_dashboard_hr_attendance](boardkit_dashboard_hr_attendance/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Attendance overview dashboard template for Boardkit
[boardkit_dashboard_hr_contract](boardkit_dashboard_hr_contract/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Employee contracts overview dashboard template for Boardkit
[boardkit_dashboard_hr_expense](boardkit_dashboard_hr_expense/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Expenses overview dashboard template for Boardkit
[boardkit_dashboard_hr_holidays](boardkit_dashboard_hr_holidays/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Time Off overview dashboard template for Boardkit
[boardkit_dashboard_hr_recruitment](boardkit_dashboard_hr_recruitment/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Recruitment overview dashboard template for Boardkit
[boardkit_dashboard_hr_timesheet](boardkit_dashboard_hr_timesheet/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Timesheet overview dashboard template for Boardkit
[boardkit_dashboard_maintenance](boardkit_dashboard_maintenance/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Maintenance overview dashboard template for Boardkit
[boardkit_dashboard_mrp](boardkit_dashboard_mrp/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Manufacturing overview dashboard template for Boardkit
[boardkit_dashboard_payroll](boardkit_dashboard_payroll/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Payroll overview dashboard template for Boardkit
[boardkit_dashboard_project](boardkit_dashboard_project/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Project tasks overview dashboard template for Boardkit
[boardkit_dashboard_purchase](boardkit_dashboard_purchase/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Purchase overview dashboard template for Boardkit
[boardkit_dashboard_repair](boardkit_dashboard_repair/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Repair overview dashboard template for Boardkit
[boardkit_dashboard_sale](boardkit_dashboard_sale/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Sales overview dashboard template for Boardkit
[boardkit_dashboard_stock](boardkit_dashboard_stock/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Inventory overview dashboard template for Boardkit

[//]: # (end addons)

<!-- prettier-ignore-end -->

## Licenses

This repository is licensed under [AGPL-3.0](LICENSE).

However, each module can have a totally different license, as long as they adhere to Escodoo
policy. Consult each module's `__manifest__.py` file, which contains a `license` key
that explains its license.

----
<!-- /!\ Non OCA Context : Set here the full description of your organization. -->
