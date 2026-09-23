// Copyright 2026 Escodoo
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

// Keep Chart.js 4 as window.BoardkitChart and give window.Chart back to Odoo.
(function () {
    "use strict";
    const current = window.Chart;
    if (current && String(current.version || "").startsWith("4.")) {
        window.BoardkitChart = current;
    }
    const parked = window.__boardkitParkedChart;
    delete window.__boardkitParkedChart;
    if (parked) {
        window.Chart = parked;
    } else if (current === window.BoardkitChart) {
        delete window.Chart;
    }
})();
