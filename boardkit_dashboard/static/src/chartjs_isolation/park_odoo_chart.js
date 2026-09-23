// Copyright 2026 Escodoo
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

// Odoo 16 exposes Chart.js 2 as window.Chart for its graph views, while
// Boardkit renders with Chart.js 4. Park the Odoo global while the Boardkit
// Chart.js bundle runs, so Chart.js 4 and its plugins bind to each other.
(function () {
    "use strict";
    window.__boardkitParkedChart = window.Chart;
    if (window.BoardkitChart) {
        window.Chart = window.BoardkitChart;
    }
})();
