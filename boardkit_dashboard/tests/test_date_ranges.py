# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo.tests import BaseCase, tagged

from odoo.addons.boardkit_dashboard.tools.date_ranges import get_date_range

# Wednesday, 2026-07-15 15:30:00 UTC
NOW = datetime(2026, 7, 15, 15, 30, 0)


@tagged("post_install", "-at_install")
class TestDateRanges(BaseCase):
    def test_today(self):
        start, end = get_date_range("today", "UTC", now=NOW)
        self.assertEqual(start, datetime(2026, 7, 15))
        self.assertEqual(end, datetime(2026, 7, 16))

    def test_yesterday_tomorrow(self):
        self.assertEqual(
            get_date_range("yesterday", "UTC", now=NOW),
            (datetime(2026, 7, 14), datetime(2026, 7, 15)),
        )
        self.assertEqual(
            get_date_range("tomorrow", "UTC", now=NOW),
            (datetime(2026, 7, 16), datetime(2026, 7, 17)),
        )

    def test_weeks(self):
        # Week starts on Monday 2026-07-13.
        self.assertEqual(
            get_date_range("this_week", "UTC", now=NOW),
            (datetime(2026, 7, 13), datetime(2026, 7, 20)),
        )
        self.assertEqual(
            get_date_range("last_week", "UTC", now=NOW),
            (datetime(2026, 7, 6), datetime(2026, 7, 13)),
        )
        self.assertEqual(
            get_date_range("next_week", "UTC", now=NOW),
            (datetime(2026, 7, 20), datetime(2026, 7, 27)),
        )
        # Week starting on Sunday (res.lang week_start=7): Sunday 2026-07-12.
        self.assertEqual(
            get_date_range("this_week", "UTC", now=NOW, week_start=7),
            (datetime(2026, 7, 12), datetime(2026, 7, 19)),
        )

    def test_months_quarters_years(self):
        self.assertEqual(
            get_date_range("this_month", "UTC", now=NOW),
            (datetime(2026, 7, 1), datetime(2026, 8, 1)),
        )
        self.assertEqual(
            get_date_range("last_month", "UTC", now=NOW),
            (datetime(2026, 6, 1), datetime(2026, 7, 1)),
        )
        self.assertEqual(
            get_date_range("this_quarter", "UTC", now=NOW),
            (datetime(2026, 7, 1), datetime(2026, 10, 1)),
        )
        self.assertEqual(
            get_date_range("last_quarter", "UTC", now=NOW),
            (datetime(2026, 4, 1), datetime(2026, 7, 1)),
        )
        self.assertEqual(
            get_date_range("this_year", "UTC", now=NOW),
            (datetime(2026, 1, 1), datetime(2027, 1, 1)),
        )
        self.assertEqual(
            get_date_range("next_year", "UTC", now=NOW),
            (datetime(2027, 1, 1), datetime(2028, 1, 1)),
        )

    def test_to_date_ranges(self):
        self.assertEqual(
            get_date_range("month_to_date", "UTC", now=NOW),
            (datetime(2026, 7, 1), datetime(2026, 7, 16)),
        )
        self.assertEqual(
            get_date_range("year_to_date", "UTC", now=NOW),
            (datetime(2026, 1, 1), datetime(2026, 7, 16)),
        )

    def test_rolling_ranges(self):
        self.assertEqual(
            get_date_range("last_7_days", "UTC", now=NOW),
            (datetime(2026, 7, 9), datetime(2026, 7, 16)),
        )
        self.assertEqual(
            get_date_range("last_30_days", "UTC", now=NOW),
            (datetime(2026, 6, 16), datetime(2026, 7, 16)),
        )

    def test_open_ranges(self):
        self.assertEqual(get_date_range("past", "UTC", now=NOW), (None, NOW))
        self.assertEqual(
            get_date_range("past_excluding_today", "UTC", now=NOW),
            (None, datetime(2026, 7, 15)),
        )
        self.assertEqual(get_date_range("future", "UTC", now=NOW), (NOW, None))
        self.assertEqual(
            get_date_range("future_excluding_today", "UTC", now=NOW),
            (datetime(2026, 7, 16), None),
        )

    def test_none_and_unknown(self):
        self.assertEqual(get_date_range("none", "UTC", now=NOW), (None, None))
        self.assertEqual(get_date_range(False, "UTC", now=NOW), (None, None))
        self.assertEqual(get_date_range("custom", "UTC", now=NOW), (None, None))
        self.assertEqual(get_date_range("bogus", "UTC", now=NOW), (None, None))

    def test_timezone_conversion(self):
        # In Sao Paulo (UTC-3), 2026-07-15 15:30 UTC is 12:30 local time.
        # Local "today" is 2026-07-15 00:00 local = 03:00 UTC.
        start, end = get_date_range("today", "America/Sao_Paulo", now=NOW)
        self.assertEqual(start, datetime(2026, 7, 15, 3, 0, 0))
        self.assertEqual(end, datetime(2026, 7, 16, 3, 0, 0))

    def test_timezone_day_shift(self):
        # At 2026-07-15 01:30 UTC it is still 2026-07-14 in Sao Paulo.
        now = datetime(2026, 7, 15, 1, 30, 0)
        start, __ = get_date_range("today", "America/Sao_Paulo", now=now)
        self.assertEqual(start, datetime(2026, 7, 14, 3, 0, 0))
