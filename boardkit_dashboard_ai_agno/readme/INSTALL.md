This module is not standalone. Besides `boardkit_dashboard`, install and run:

- **[Escodoo/ai](https://github.com/Escodoo/ai)** (`16.0`) — provides
  `ai_oca_bridge`, the only Odoo dependency on 16.0. The Escodoo helpers used
  on 18.0 (`ai_agno_connector`, `ai_oca_bridge_provider`,
  `ai_oca_bridge_request_timeout`) are not needed: the bridge token lookup and
  the request timeout are handled by this module.
- **[agno-odoo](https://github.com/Escodoo/agno-odoo)** — companion Agno
  service that serves the `/bridge/boardkit/*` endpoints used for chat,
  insights, tile explanations and board generation.

Clone both repositories into the addons / services path of the deployment
(Doodba `repos.yaml` / Compose) before installing `boardkit_dashboard_ai_agno`.
