#!/usr/bin/env python3
# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Keep the template translations of every addon in sync.

Two files per addon and language:

``i18n_extra/<lang>.po``
    Terms of the JSON payload of the templates (card names, filter names,
    boolean labels). Odoo's exporter does not read text inside JSON, so these
    ship as code translations. ``i18n_extra`` is read by Odoo together with
    ``i18n`` and is left alone by the bot that regenerates the ``.pot``.

``i18n/<lang>.po``
    Name and description of the template and of the demo board. Those are
    plain records with an xmlid, so they are already in the ``.pot`` and
    belong in the standard file. The msgid is copied from the ``.pot``, so it
    matches what Odoo exported, whitespace included.

    A file written by hand keeps its entries: only the occurrences it does
    not carry yet are added, reusing the wording it already has for the term.

    python3 tools/boardkit_template_terms.py                 # update pt_BR
    python3 tools/boardkit_template_terms.py --lang es_ES    # another language
    python3 tools/boardkit_template_terms.py --check         # CI / pre-commit

Existing translations are preserved, new terms are added with an empty
``msgstr`` and terms dropped from a payload are removed.
"""

# The script reports on the terminal, so pylint_odoo must allow print().
# pylint: disable=print-used

import argparse
import importlib.util
import json
import os
import re
import sys
import textwrap
import xml.etree.ElementTree as ElementTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAYLOAD_FILE = os.path.join("data", "boardkit_dashboard_templates.xml")
# Record fields that carry template wording, as the .pot spells them out.
RECORD_FIELDS = (
    "model:boardkit.dashboard.template,name:",
    "model:boardkit.dashboard.template,description:",
    "model:boardkit.dashboard,name:",
    "model:boardkit.dashboard,description:",
)
HEADER = """# Translation of Odoo Server.
# This file contains the translation of the following modules:
# \t* {module}
#
{note}msgid ""
msgstr ""
"Project-Id-Version: Odoo Server 16.0\\n"
"Report-Msgid-Bugs-To: \\n"
"Last-Translator: \\n"
"Language-Team: \\n"
"Language: {lang}\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: \\n"
"""
PAYLOAD_NOTE = (
    "# Terms of the curated template payloads, which the standard exporter does not\n"
    "# read. Update with tools/boardkit_template_terms.py.\n"
    "#\n"
)
ENTRY = """
#. module: {module}
#. odoo-python
#: code:addons/{module}/data/boardkit_dashboard_templates.xml:0
#, python-format
msgid "{source}"
msgstr "{value}"
"""


def load_iter_terms():
    """Reuse the term walker of the addon, so both stay on one definition."""
    path = os.path.join(ROOT, "boardkit_dashboard", "tools", "template_i18n.py")
    spec = importlib.util.spec_from_file_location("boardkit_template_i18n", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.iter_terms


def payload_terms(addon, iter_terms):
    """Distinct terms of an addon's templates, in reading order."""
    path = os.path.join(ROOT, addon, PAYLOAD_FILE)
    if not os.path.exists(path):
        return []
    terms = []
    for field in ElementTree.parse(path).getroot().iter("field"):
        if field.get("name") != "payload" or not field.text:
            continue
        for term in iter_terms(json.loads(field.text)):
            if term not in terms:
                terms.append(term)
    return terms


def escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def unescape(text):
    return text.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")


def literal_text(lines):
    """Text of a ``msgid``/``msgstr`` literal, continuation lines included."""
    quoted = re.findall(r'"((?:[^"\\]|\\.)*)"', "\n".join(lines))
    return unescape("".join(quoted))


def po_value(value):
    """Render a ``msgstr`` value, wrapped the way gettext tools wrap it."""
    escaped = escape(value)
    if len(escaped) <= 70 and "\\n" not in escaped:
        return 'msgstr "%s"' % escaped
    chunks = textwrap.wrap(
        value, width=76, break_long_words=False, break_on_hyphens=False
    )
    lines = ['msgstr ""']
    for index, chunk in enumerate(chunks):
        space = "" if index == len(chunks) - 1 else " "
        lines.append('"%s%s"' % (escape(chunk), space))
    return "\n".join(lines)


def read_po(path):
    """Return ``{msgid: msgstr}`` of an existing file, header excluded."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        content = handle.read()
    entries = {}
    pattern = re.compile(
        r'^msgid\s+((?:"(?:[^"\\]|\\.)*"\s*)+)^msgstr\s+((?:"(?:[^"\\]|\\.)*"\s*)+)',
        re.MULTILINE,
    )
    for raw_id, raw_str in pattern.findall(content):
        source = unescape("".join(re.findall(r'"((?:[^"\\]|\\.)*)"', raw_id)))
        value = unescape("".join(re.findall(r'"((?:[^"\\]|\\.)*)"', raw_str)))
        if source:
            entries[source] = value
    return entries


def write_payload_po(path, module, lang, terms, known):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = ""
    for term in terms:
        body += ENTRY.format(
            module=module, source=escape(term), value=escape(known.get(term, ""))
        )
    header = HEADER.format(module=module, lang=lang, note=PAYLOAD_NOTE)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(header + body)


def record_entries(addon):
    """``(term, msgid lines, occurrence lines)`` of the template records."""
    path = os.path.join(ROOT, addon, "i18n", f"{addon}.pot")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as handle:
        content = handle.read()
    entries = []
    for block in content.split("\n\n"):
        lines = block.splitlines()
        occurrences = [
            line
            for line in lines
            if line.startswith("#: ") and line[3:].startswith(RECORD_FIELDS)
        ]
        if not occurrences:
            continue
        start = next(i for i, line in enumerate(lines) if line.startswith("msgid "))
        end = next(i for i, line in enumerate(lines) if line.startswith("msgstr"))
        entries.append((literal_text(lines[start:end]), lines[start:end], occurrences))
    return entries


def render_record_entry(module, msgid_lines, occurrences, value):
    return "\n".join(
        ["#. module: %s" % module] + occurrences + msgid_lines + [po_value(value)]
    )


def merge_record_entries(content, module, pending):
    """Add the occurrences the file lacks, leaving its own entries untouched."""
    blocks = [block.strip("\n") for block in content.split("\n\n") if block.strip()]
    for term, msgid_lines, occurrences, value in pending:
        for index, block in enumerate(blocks):
            lines = block.splitlines()
            at = next(
                (i for i, line in enumerate(lines) if line.startswith("msgid ")), None
            )
            stop = next(
                (i for i, line in enumerate(lines) if line.startswith("msgstr")),
                len(lines),
            )
            if at is None or at >= stop or literal_text(lines[at:stop]) != term:
                continue
            # The term is already translated here: only point the existing
            # entry at the record it does not mention yet.
            lines[at:at] = occurrences
            blocks[index] = "\n".join(lines)
            break
        else:
            blocks.append(render_record_entry(module, msgid_lines, occurrences, value))
    return "\n\n".join(blocks) + "\n"


def sync_record_po(addon, lang, entries, fallback, check):
    """Translate the template and demo board records in the standard file.

    Returns the terms still without a translation and how many occurrences
    were added.
    """
    path = os.path.join(ROOT, addon, "i18n", f"{lang}.po")
    content = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
    known = read_po(path)
    missing = []
    pending = []
    for term, msgid_lines, occurrences in entries:
        value = known.get(term) or fallback.get(term, "")
        if not value:
            missing.append(term)
        absent = [line for line in occurrences if line not in content]
        if absent:
            pending.append((term, msgid_lines, absent, value))
    if check or not pending:
        return missing, len(pending)
    if content:
        content = merge_record_entries(content, addon, pending)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        body = "\n" + "\n\n".join(
            render_record_entry(addon, msgid_lines, occurrences, value)
            for _term, msgid_lines, occurrences, value in pending
        )
        content = HEADER.format(module=addon, lang=lang, note="") + body + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return missing, len(pending)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", default="pt_BR", help="language code (default pt_BR)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report missing or untranslated terms and exit non-zero",
    )
    args = parser.parse_args()

    iter_terms = load_iter_terms()
    addons = sorted(
        name
        for name in os.listdir(ROOT)
        if name.startswith("boardkit_dashboard")
        and os.path.exists(os.path.join(ROOT, name, PAYLOAD_FILE))
    )
    problems = []
    seen = {}
    for addon in addons:
        terms = payload_terms(addon, iter_terms)
        if not terms:
            continue
        path = os.path.join(ROOT, addon, "i18n_extra", f"{args.lang}.po")
        known = read_po(path)
        missing = [term for term in terms if not known.get(term)]
        if not args.check:
            write_payload_po(path, addon, args.lang, terms, known)
        records, added = sync_record_po(
            addon, args.lang, record_entries(addon), known, args.check
        )
        if args.check and (missing or records):
            problems.append(
                "%s: %d payload term(s) and %d record(s) without translation"
                % (addon, len(missing), len(records))
            )
        for term in terms:
            value = known.get(term)
            if value:
                seen.setdefault(term, {}).setdefault(value, []).append(addon)
        print(
            "%-38s %3d terms, %3d untranslated, %d record(s) %s"
            % (
                addon,
                len(terms),
                len(missing) + len(records),
                added,
                "to add" if args.check else "added",
            )
        )

    for term, values in sorted(seen.items()):
        if len(values) > 1:
            joined = " | ".join(
                f"{value} ({', '.join(addons)})" for value, addons in values.items()
            )
            # Divergence is legitimate: "Overdue" reads "Vencidas" on invoices
            # and "Atrasadas" on tasks. Report it, never fail on it.
            print(f'note: term "{term}" reads differently per module: {joined}')

    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
