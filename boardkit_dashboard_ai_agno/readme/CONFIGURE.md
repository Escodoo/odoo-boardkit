1. Install `boardkit_dashboard_ai_agno` together with its AI dependencies from
   [ai-addons](https://github.com/Escodoo/ai-addons) (`ai_agno_connector` and
   the OCA `ai_oca_bridge` stack it depends on).
2. Deploy and run the companion Agno service from
   [agno-odoo](https://github.com/Escodoo/agno-odoo). It must be reachable at
   the bridge URLs (default `http://agno:8000`) and expose
   `/bridge/boardkit/*`.
3. Set the bridge auth token:
   - Prefer `agno_bridge_auth_token` in Odoo conf (expanded from Doodba env), or
   - Set ICP `boardkit_dashboard_ai_agno.bridge_auth_token`.
4. Grant **Dashboard / Use AI on Dashboards** to users who may chat, summarize or
   explain boards. Dashboard managers inherit this group and can also open
   **Generate with AI**.
5. On each board form, enable **Enable AI** when chat/insights/explain should be
   available on that dashboard (on by default). Users still need the AI group.
6. Configure a chat LLM (env `LLM_*` on Agno and/or Odoo Settings → Agno AI BYOK).
7. Upgrade the module after pulling so the Boardkit Chat bridge
   (`/bridge/boardkit/chat`) is created and receives the auth token.
8. The Boardkit bridges use a `request_timeout` of 120–180 seconds. Raise
   Odoo's `limit_time_real` (and the HTTP proxy timeout, if any) above that
   value so a long LLM call is not killed before the bridge answers.
