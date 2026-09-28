# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

import pytz
from dateutil.relativedelta import relativedelta

DATE_RANGE_PRESETS = [
    ("none", "All Time"),
    ("today", "Today"),
    ("yesterday", "Yesterday"),
    ("tomorrow", "Tomorrow"),
    ("this_week", "This Week"),
    ("this_month", "This Month"),
    ("this_quarter", "This Quarter"),
    ("this_year", "This Year"),
    ("last_week", "Last Week"),
    ("last_month", "Last Month"),
    ("last_quarter", "Last Quarter"),
    ("last_year", "Last Year"),
    ("next_week", "Next Week"),
    ("next_month", "Next Month"),
    ("next_quarter", "Next Quarter"),
    ("next_year", "Next Year"),
    ("week_to_date", "Week to Date"),
    ("month_to_date", "Month to Date"),
    ("quarter_to_date", "Quarter to Date"),
    ("year_to_date", "Year to Date"),
    ("last_7_days", "Last 7 Days"),
    ("last_30_days", "Last 30 Days"),
    ("last_90_days", "Last 90 Days"),
    ("last_365_days", "Last 365 Days"),
    ("past", "Until Now"),
    ("past_excluding_today", "Before Today"),
    ("future", "From Now"),
    ("future_excluding_today", "From Tomorrow"),
    ("custom", "Custom Range"),
]


def _start_of_week(day, week_start):
    """Return the first day of the week containing ``day``.

    ``week_start`` follows res.lang convention: 1 = Monday .. 7 = Sunday.
    """
    delta = (day.weekday() - (week_start - 1)) % 7
    return day - timedelta(days=delta)


def _start_of_quarter(day):
    return day.replace(month=3 * ((day.month - 1) // 3) + 1, day=1)


def get_date_range(preset, tz_name="UTC", now=None, week_start=1):
    """Compute the UTC datetime range for a date filter preset.

    :param preset: one of the DATE_RANGE_PRESETS keys (except ``custom``)
    :param tz_name: user timezone used to compute local day boundaries
    :param now: naive UTC reference datetime (defaults to current time)
    :param week_start: first weekday, res.lang convention (1 = Monday)
    :return: tuple ``(start, end)`` of naive UTC datetimes; ``end`` is
        exclusive and either bound may be ``None`` (open range)
    """
    if not preset or preset in ("none", "custom"):
        return (None, None)
    tz = pytz.timezone(tz_name or "UTC")
    now = now or datetime.utcnow()
    local_now = pytz.utc.localize(now).astimezone(tz).replace(tzinfo=None)
    today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

    day = timedelta(days=1)
    week = timedelta(days=7)
    this_week = _start_of_week(today, week_start)
    this_month = today.replace(day=1)
    this_quarter = _start_of_quarter(today)
    this_year = today.replace(month=1, day=1)

    ranges = {
        "today": (today, today + day),
        "yesterday": (today - day, today),
        "tomorrow": (today + day, today + 2 * day),
        "this_week": (this_week, this_week + week),
        "this_month": (this_month, this_month + relativedelta(months=1)),
        "this_quarter": (this_quarter, this_quarter + relativedelta(months=3)),
        "this_year": (this_year, this_year + relativedelta(years=1)),
        "last_week": (this_week - week, this_week),
        "last_month": (this_month - relativedelta(months=1), this_month),
        "last_quarter": (this_quarter - relativedelta(months=3), this_quarter),
        "last_year": (this_year - relativedelta(years=1), this_year),
        "next_week": (this_week + week, this_week + 2 * week),
        "next_month": (
            this_month + relativedelta(months=1),
            this_month + relativedelta(months=2),
        ),
        "next_quarter": (
            this_quarter + relativedelta(months=3),
            this_quarter + relativedelta(months=6),
        ),
        "next_year": (
            this_year + relativedelta(years=1),
            this_year + relativedelta(years=2),
        ),
        "week_to_date": (this_week, today + day),
        "month_to_date": (this_month, today + day),
        "quarter_to_date": (this_quarter, today + day),
        "year_to_date": (this_year, today + day),
        "last_7_days": (today - timedelta(days=6), today + day),
        "last_30_days": (today - timedelta(days=29), today + day),
        "last_90_days": (today - timedelta(days=89), today + day),
        "last_365_days": (today - timedelta(days=364), today + day),
        "past": (None, local_now),
        "past_excluding_today": (None, today),
        "future": (local_now, None),
        "future_excluding_today": (today + day, None),
    }
    if preset not in ranges:
        return (None, None)
    start, end = ranges[preset]

    def to_utc(value):
        if value is None:
            return None
        return tz.localize(value).astimezone(pytz.utc).replace(tzinfo=None)

    return (to_utc(start), to_utc(end))
