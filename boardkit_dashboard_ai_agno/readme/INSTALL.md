This module is not standalone. Besides `boardkit_dashboard`, install and run:

- **[ai-addons](https://github.com/Escodoo/ai-addons)** — Odoo addons, at least
  `ai_agno_connector` (which pulls the OCA `ai_oca_bridge` stack and Escodoo
  helpers such as `ai_oca_bridge_provider` and `ai_oca_bridge_request_timeout`).
- **[agno-odoo](https://github.com/Escodoo/agno-odoo)** — companion Agno
  service that serves the `/bridge/boardkit/*` endpoints used for chat,
  insights, tile explanations and board generation.

Clone both repositories into the addons / services path of the deployment
(Doodba `repos.yaml` / Compose) before installing `boardkit_dashboard_ai_agno`.
