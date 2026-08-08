1. Install `boardkit_dashboard_ai` (and its AI dependencies).
2. Ensure the Agno service is running and reachable at the bridge URLs
   (default `http://agno:8000`).
3. Set the bridge auth token:
   - Prefer `agno_bridge_auth_token` in Odoo conf (expanded from Doodba env), or
   - Set ICP `boardkit_dashboard_ai.bridge_auth_token`.
4. Grant **Dashboard / Use AI on Dashboards** to users who may chat, summarize or
   explain boards. Dashboard managers inherit this group and can also open
   **Generate with AI**.
5. On each board form, enable **Enable AI** when chat/insights/explain should be
   available on that dashboard (on by default). Users still need the AI group.
6. Configure a chat LLM (env `LLM_*` on Agno and/or Odoo Settings → Agno AI BYOK).
7. Upgrade the module after pulling so the Boardkit Chat bridge
   (`/bridge/boardkit/chat`) is created and receives the auth token.
