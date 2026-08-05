Open a published dashboard from _All Dashboards > Boards_ (click the card), from
its optional menu entry when _Parent Menu_ is configured, or from the main apps
menu when _Show as App_ is enabled.

Managers can create a board from a template with the _From template_ button in the
Boards toolbar. The new board is unpublished so it can be reviewed before users see
it. Optionally rename it in the wizard; leave the name empty to keep the template
title. When the template has _Allowed Groups_, those groups are copied to the new
board (who can open it / its menu). Tile data still respects the source model's
record rules. Leave the template groups empty to keep the board limited to
Dashboard Users until a manager sets an audience.

Core ships the _Contacts Overview_ template (data-quality tiles, KPIs, country
regions map, location points map on `partner_latitude` / `partner_longitude`,
charts and a recent list). It uses only Contacts (`res.partner`). When the module
is installed with demo data, a published board is created from that same
template (plus a few geolocalized sample partners for the points map).
App-specific overview templates live in the matching `boardkit_dashboard_*`
modules.

In the catalogue (kanban or list), or from the star next to the title when a
dashboard is open, click the star to favorite it. Favorited dashboards appear
first and can be filtered with _My Favorites_ or the search panel _Favorites_
section. Favorites are personal and do not affect other users.

Unpublished boards show a draft style and a _Draft_ ribbon; managers can publish
directly from the card or the card menu. An empty catalogue shows a first-run
hero with featured templates (when the matching template modules are installed).

Catalogue cards show an icon from the board's optional _Icon_ field. Leave it
empty to inherit the first tag icon set in _All Dashboards > Configuration >
Tags_. Rename tags freely; the stored tag icon stays. With neither board nor tag
icon, the catalogue uses a default grid icon.

Dashboards with _Allowed Groups_ can be opened by members of those groups even without
the Dashboard User right (typical for menus under another app). Dashboards without
Allowed Groups stay limited to Dashboard Users. The Boardkit Dashboards app itself still
requires Dashboard User or Manager.

When _Auto Refresh_ is enabled, the server caches each item payload for up to the
refresh interval (capped by the `boardkit_dashboard.data_cache_max_ttl` system
parameter, default 60 seconds). The cache key includes the user, companies, item
configuration and active filters, so access rights stay intact while wall-screen
boards avoid recomputing the same queries on every tick.

If a dashboard is missing or the current user cannot access it (for example a
company-bound dashboard opened as a landing page outside that company), the client
shows an empty state instead of an access error.

On charts and grouped lists, the _Measures_ list adds one series (or one column) per
numeric field. Drag the handle to reorder them: the order of the list is the order the
series are plotted, and it travels with the dashboard JSON export.

When configuring a **Map** item:

- Choose _Regions_ and a Group By field pointing to Countries for a choropleth world map.
- Choose _Points_ and pick the Latitude / Longitude float fields of the source model to
  plot markers (for example `partner_latitude` / `partner_longitude` on contacts, or
  equivalent fields on tickets and field service orders). Records sharing the same
  coordinates are merged into one marker whose size reflects the record count, or the
  sum of the _Measure Field_ when one is configured.
- Optionally set _Focus Country_ to crop the outline and zoom the projection to that
  country (works in both modes). Clicking a point opens the underlying record when
  _Show Records_ is enabled.

- Click the expand icon in the top bar to enter full screen (TV / kiosk mode). The
  Odoo navbar is hidden and the dashboard fills the screen. Press ESC or click the
  compress icon to exit. Auto-refresh keeps running while full screen is active.
- Use the date filter in the top bar to restrict every item that has a _Date Field_
  configured. Choose a preset or a custom range.
- Toggle predefined filters to restrict the items whose model matches the filter model.
- Use _Add Filter_ to build an ad-hoc filter: pick a model, a field, an operator and a
  value. The filter applies to every item based on that model and shows up as a
  removable chip. Text filters on relational fields match the record display name.
- Your date range, predefined filters and ad-hoc filters are remembered between visits.
  Use _Reset My Filters_ in the dashboard menu to go back to the board defaults, or
  _Copy Link_ to share the current filter state with someone who can open the same
  dashboard (the link overrides their saved filters when opened).
- Enable _Compare to Previous Period_ on a tile, KPI, or bar / line / area chart (with a
  _Date Field_ and an active date range) to show how the figure moved versus the previous
  equivalent period. Tiles and KPIs show a delta badge; charts draw a dashed overlay.
- Click on a tile, a KPI, a chart section or a list row to open the underlying records.
  When the item has _Drill Down_ levels configured, the first clicks re-aggregate the
  data inside the card (breadcrumbs let you go back); the click on the last level opens
  the records. The item form live preview supports the same chart-to-chart drill (including
  unsaved levels); opening the record list stays disabled there.

Chart colors come from the item's _Color Palette_ (Appearance tab):

- _Dashboard Default_ (the initial value) follows the _Default Palette_ configured
  on the dashboard form. Changing the dashboard default — or moving the item to
  another dashboard — restyles every item still using it. An empty dashboard
  default means the Odoo preset.
- Pick one of the built-in presets (Odoo, Ocean, Sunset, Electric, Pastel, Vivid,
  Earth, Royal) to override the dashboard default on a single item, or
- Pick _Custom_ and select a palette created in _All Dashboards > Configuration >
  Color Palettes_, where managers define an ordered list of hex colors. Palettes
  used by a dashboard travel inside its JSON export and are recreated on import
  when missing.

Tiles and KPIs are themed by the palette too: with _Background Style_ set to
_From Palette_ (the default) the card uses the darkest palette color as
background with an automatic contrasting font, and the KPI progress bar takes
the first palette color. Switch it to _Manual_ to pick the background and font
colors by hand.

- Use _Export CSV_ / _Export XLSX_ in an item menu to download its data with the
  current filters applied. Lists export all rows, ignoring pagination.
- Any dashboard user can switch to _Edit Layout_ mode to drag and resize items. Managers
  can save the default layout for everyone; regular users save a personal layout and can
  reset it back to the default one.
- Managers can export the dashboard configuration as JSON from the dashboard action menu.
  To bring it back, use the _Import_ button in the _All Dashboards > Boards_ toolbar
  and pick the file. Imported boards arrive unpublished and without a menu entry, so
  review them and set _Parent Menu_ or _Show as App_ before sharing.
