1. Assign users to the proper group in _Settings > Users_:
   - _Dashboard / User_: can open the Boardkit Dashboards app and any dashboard without
     an Allowed Groups restriction, and keep a personal layout.
   - _Dashboard / Manager_: can create and configure dashboards and items.
2. Go to _All Dashboards > Boards_ and create a dashboard (managers), or use
   _From template_ in the toolbar to start from a curated board (also managers only).
   Template boards and blank boards both start unpublished so only managers can see
   them while building. Use _Publish_ when the board is ready for users. Optionally
   set _Parent Menu_ to also expose a menu entry, or enable _Show as App_ to expose
   the dashboard as a top-level app in the main apps menu (using the Boardkit
   Dashboards module icon). Both entries exist only while the board is published.
   Restrict visibility with _Allowed Groups_: users in those groups can open that
   dashboard (for example under Helpdesk) without needing Dashboard User. Leave
   Allowed Groups empty so only Dashboard Users see it. Unpublished or archived
   dashboards are visible only to Dashboard Managers. Dashboards limited to a
   specific company cannot have a menu entry (open them from _All Dashboards_ or a
   landing-page action instead).
3. Add items from the dashboard form or directly from the dashboard view with the _Add
   Item_ button (managers only). The item form shows a live preview that updates as you
   change the configuration, before saving.
4. To reuse a board from another database, use the _Import_ button in the
   _All Dashboards > Boards_ toolbar (managers only) and select the JSON file
   exported from the dashboard action menu. Imported boards arrive unpublished and
   without a menu entry, so review them before publishing. Managers can also inspect
   or edit template payloads under _All Dashboards > Configuration > Templates_.
   On each template, set _Allowed Groups_ to the lowest app group that should open
   boards created from it (managers already inherit implied user groups). Leave
   empty for generic templates that stay limited to Dashboard Users.
