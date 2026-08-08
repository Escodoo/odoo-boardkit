AI bridge for Boardkit dashboards.

Adds optional Agno-powered features on top of `boardkit_dashboard` without
changing the core module:

- **Board chat** to ask questions about the visible figures and active filters
- **Insights** narrative from the same figures shown on the cards
- **Explain this tile** for a single KPI/chart/list
- **Generate with AI** wizard that turns a natural-language description into an
  unpublished board via `import_config`
- **Per-dashboard toggle** (`Enable AI`) so each board can opt in or out

Requires the OCA `ai_oca_bridge` stack, Escodoo `ai_agno_connector`, and the
companion Agno service (`/bridge/boardkit/*` endpoints).
