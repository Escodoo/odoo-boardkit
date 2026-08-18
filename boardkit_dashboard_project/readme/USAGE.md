Install this module (it auto-installs when Boardkit Dashboard and Project are
both installed).

As a Dashboard Manager, open _All Dashboards > Boards_, click _From template_,
and choose **Project Overview**. Optionally rename the board in the wizard.

The board opens with the date filter on _This Month_. Open backlog tiles (Open,
High Priority, Overdue, Unassigned, Waiting) ignore that filter so they always
show the current queue. Done metrics use _Ending Date_, which Odoo fills when a
task reaches a folded stage, and follow the date filter; the completion rate
measures the tasks created in the period instead. Use the toggle filters (My
Tasks, Open, Overdue, High Priority) to narrow the other cards.

When installed with demo data, a published board is created from this template and placed first (sequence `-1`) under the related app menu.
