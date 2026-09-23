# Copyright 2026 Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Odoo 16 bridge for the ``_read_group`` contract of Odoo 17+.

The data engine is shared with the 18.0 branch, where ``_read_group`` returns
one tuple per group holding the raw group values followed by the aggregates:
recordsets for many2one groups and the period start for date/datetime
granularities. Odoo 16 only offers ``read_group``, which returns dicts with
formatted labels, so this helper rebuilds the 17+ shape on top of it.
"""

from odoo import fields


def read_group(model, domain, groupby=(), aggregates=(), offset=0, limit=None):
    """Return ``[(*group_values, *aggregate_values)]`` like Odoo 17+.

    :param groupby: field names, optionally ``field:granularity`` for dates
    :param aggregates: ``__count`` or ``field:function`` specs
    """
    groupby = list(groupby)
    aggregate_specs = []
    columns = []
    for index, spec in enumerate(aggregates):
        if spec == "__count":
            columns.append(("__count", None, None))
            continue
        fname, function = spec.split(":")
        alias = f"boardkit_agg_{index}"
        aggregate_specs.append(f"{alias}:{function}({fname})")
        columns.append((alias, fname, function))
    # An empty field list makes read_group aggregate every stored field.
    groups = model.read_group(
        domain,
        aggregate_specs or ["__count"],
        groupby,
        offset=offset,
        limit=limit,
        lazy=False,
    )
    comodel_ids = _many2one_ids(model, groups, groupby)
    rows = []
    for group in groups:
        row = [_group_value(model, group, spec, comodel_ids) for spec in groupby]
        for alias, fname, function in columns:
            if alias in group:
                row.append(group[alias])
            else:
                # read_group silently skips aggregates on a grouped field.
                row.append(_grouped_field_aggregate(group, fname, function))
        rows.append(tuple(row))
    return rows


def _many2one_ids(model, groups, groupby):
    """Collect the grouped ids per spec so the recordsets share a prefetch."""
    ids = {}
    for spec in groupby:
        if model._fields[spec.split(":")[0]].type == "many2one":
            ids[spec] = tuple(group[spec][0] for group in groups if group.get(spec))
    return ids


def _group_value(model, group, spec, comodel_ids):
    field = model._fields[spec.split(":")[0]]
    value = group.get(spec)
    if field.type == "many2one":
        comodel = model.env[field.comodel_name]
        if not value:
            return comodel
        return comodel.browse(value[0]).with_prefetch(comodel_ids[spec])
    if field.type in ("date", "datetime"):
        period = (group.get("__range") or {}).get(spec)
        if not period:
            return False
        if field.type == "date":
            return fields.Date.to_date(period["from"])
        # Period bounds are already converted back to UTC by read_group.
        return fields.Datetime.to_datetime(period["from"])
    return value


def _grouped_field_aggregate(group, fname, function):
    value = group.get(fname)
    count = group.get("__count") or 0
    if value is False or value is None:
        return 0 if function in ("count", "count_distinct") else None
    if function == "sum":
        return value * count
    if function == "count":
        return count
    if function == "count_distinct":
        return 1
    return value
