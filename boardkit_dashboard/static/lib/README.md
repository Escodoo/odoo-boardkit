# Vendored Chart.js extensions

Third-party libraries used by `boardkit_dashboard` advanced chart types.

| File | Package | License | Purpose |
| --- | --- | --- | --- |
| `chartjs-chart-funnel.umd.min.js` | [chartjs-chart-funnel](https://github.com/sgratzl/chartjs-chart-funnel) v4.2.5 | MIT | Funnel chart controller |
| `chartjs-chart-geo.umd.min.js` | [chartjs-chart-geo](https://github.com/sgratzl/chartjs-chart-geo) v4.3.4 | MIT | Choropleth / map chart |
| `countries-110m.json` | [world-atlas](https://github.com/topojson/world-atlas) v2.0.2 | Natural Earth (public domain) | Source topojson |
| `countries_110m.js` | generated from `countries-110m.json` | Natural Earth (public domain) | Runtime topology as `window.ESCODOO_WORLD_TOPOLOGY` |

These scripts expect the global `Chart` object from Odoo `web.chartjs_lib` and are loaded through the lazy bundle `boardkit_dashboard.chartjs_extensions` (only when a funnel or map item is rendered).

`countries_110m.js` is kept out of `web.assets_backend` on purpose: the topology is ~260 KB and would otherwise ship to every backend user. The ChartRenderer reads `ESCODOO_WORLD_TOPOLOGY` after `ensureChartExtensions("map")`.
