# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Translation of curated template payloads.

Template content lives in a JSON payload, which Odoo's translation exporter
does not read: only records with an xmlid and translatable fields reach the
``.pot``. The user visible terms of every payload are therefore shipped as
code translations in ``<addon>/i18n_extra/<lang>.po`` and applied to the
records right after a board is created from the template.

``i18n_extra`` is read by ``odoo.tools.translate.CodeTranslations`` together
with ``i18n``, and is left alone by the bot that regenerates the ``.pot``
files on every push, so the terms are never flagged obsolete.

``tools/boardkit_template_terms.py`` in the repository root generates and
updates those ``.po`` files from the payloads.
"""

# Payload keys holding text shown to the user. Everything else in a payload is
# technical: model names, field names, domains, layout and selection values.
TRANSLATABLE_KEYS = (
    "name",
    "description",
    "boolean_true_label",
    "boolean_false_label",
)

# Payload sections that are not shown on the board: palettes carry brand names
# ("Boardkit Brand") and tags are shared records with their own translations.
SKIPPED_SECTIONS = ("palettes", "tags")


def iter_terms(payload):
    """Yield every translatable term of a payload, in reading order.

    Used by the ``.po`` generator, by the tests that guard translation
    coverage and by the board translation itself.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in SKIPPED_SECTIONS:
                continue
            if key in TRANSLATABLE_KEYS and isinstance(value, str) and value.strip():
                yield value
            else:
                yield from iter_terms(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from iter_terms(value)


def translator(module, lang):
    """Return ``term -> translation`` for a module, or None when untranslated.

    The import is local so this file stays usable outside a running Odoo, as
    the ``.po`` generator does.
    """
    from odoo.tools.translate import code_translations

    translations = code_translations.get_python_translations(module, lang)

    def translate(term):
        if not term:
            return None
        # A term can read the same in both languages ("KPI", "Templates"):
        # what matters is that the .po carries it, not that it differs.
        return translations.get(term) or None

    return translate


def target_languages(env):
    """Active languages that need a translation pass, English excluded."""
    langs = env["res.lang"].sudo().search([("active", "=", True)])
    return [lang.code for lang in langs if lang.code != "en_US"]
