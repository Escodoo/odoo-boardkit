# Vendored Chart.js extensions

Third-party libraries used by `boardkit_dashboard` advanced chart types.

| File | Package | License | Purpose |
| --- | --- | --- | --- |
| `chartjs/chart.umd.min.js` | [Chart.js](https://github.com/chartjs/Chart.js) v4.4.1 (`dist/chart.umd.js`) | MIT (`chartjs/LICENSE.md`) | Chart engine, same version as Odoo 18 `web.chartjs_lib` |
| `chartjs-chart-funnel.umd.min.js` | [chartjs-chart-funnel](https://github.com/sgratzl/chartjs-chart-funnel) v4.2.5 | MIT | Funnel chart controller |
| `chartjs-chart-geo.umd.min.js` | [chartjs-chart-geo](https://github.com/sgratzl/chartjs-chart-geo) v4.3.4 | MIT | Choropleth / map chart |
| `countries-110m.json` | [world-atlas](https://github.com/topojson/world-atlas) v2.0.2 | Natural Earth (public domain) | Source topojson |
| `countries_110m.js` | generated from `countries-110m.json` | Natural Earth (public domain) | Runtime topology as `window.ESCODOO_WORLD_TOPOLOGY` |

Odoo 16 only ships Chart.js 2.9.4, as the `window.Chart` global of its graph
views. Boardkit therefore vendors Chart.js 4 and loads it lazily through the
`boardkit_dashboard.chartjs_lib` bundle, framed by
`static/src/chartjs_isolation/park_odoo_chart.js` and `restore_odoo_chart.js`:
the Odoo global is parked while Chart.js 4 and the funnel/geo plugins run, then
Chart.js 4 stays available as `window.BoardkitChart` and `window.Chart` goes
back to Odoo. The plugins live in the same bundle because Odoo 16 memoizes
`loadJS` per URL, so the shims could not frame a second bundle in debug mode.

`countries_110m.js` is kept out of `web.assets_backend` and of the Chart.js
bundle on purpose: the topology is ~260 KB and only map items need it. It is
loaded through `boardkit_dashboard.chartjs_extensions`, and the ChartRenderer
reads `ESCODOO_WORLD_TOPOLOGY` after `ensureChartExtensions("map")`.
