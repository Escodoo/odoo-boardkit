AI bridge for Boardkit dashboards.

Adds optional Agno-powered features on top of `boardkit_dashboard` without
changing the core module:

- **Board chat** to ask questions about the visible figures and, when requested,
  apply known date presets / board filters on the dashboard
- **Insights** narrative from the same figures shown on the cards
- **Explain this tile** for a single KPI/chart/list
- **Generate with AI** wizard that turns a natural-language description into an
  unpublished board via `import_config`
- **Per-dashboard toggle** (`Enable AI`) so each board can opt in or out

Requires:

- The OCA `ai_oca_bridge` stack
- Escodoo `ai_agno_connector` from
  [ai-addons](https://github.com/Escodoo/ai-addons)
- The companion Agno service from
  [agno-odoo](https://github.com/Escodoo/agno-odoo)
  (`/bridge/boardkit/*` endpoints)
