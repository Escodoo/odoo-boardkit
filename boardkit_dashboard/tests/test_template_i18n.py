# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from ..tools.template_i18n import iter_terms, target_languages, translator
from .common import BoardkitDashboardCommon

TEMPLATE = "boardkit_dashboard.template_contacts_overview"


@tagged("post_install", "-at_install")
class TestTemplateTranslations(BoardkitDashboardCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("pt_BR")
        cls.template = cls.env.ref(TEMPLATE)

    def _create_board(self):
        dashboard_ids = self.env["boardkit.dashboard"].create_from_template(
            self.template.id
        )
        return self.env["boardkit.dashboard"].browse(dashboard_ids)

    def _item(self, dashboard, english_name):
        items = dashboard.item_ids.with_context(lang="en_US")
        return items.filtered(lambda item: item.name == english_name)

    def test_board_is_created_in_both_languages(self):
        dashboard = self._create_board()
        self.assertEqual(dashboard.source_template_id, self.template)
        self.assertEqual(dashboard.with_context(lang="en_US").name, "Contacts Overview")
        self.assertEqual(
            dashboard.with_context(lang="pt_BR").name, "Visão Geral de Contatos"
        )

    def test_items_and_filters_are_translated(self):
        dashboard = self._create_board()
        item = self._item(dashboard, "Total Contacts")
        self.assertEqual(item.with_context(lang="pt_BR").name, "Total de Contatos")
        board_filter = dashboard.filter_ids.with_context(lang="en_US").filtered(
            lambda rec: rec.name == "Companies"
        )
        self.assertEqual(board_filter.with_context(lang="pt_BR").name, "Empresas")

    def test_boolean_labels_are_translated(self):
        dashboard = self._create_board()
        item = self._item(dashboard, "Companies vs Individuals")
        self.assertEqual(item.with_context(lang="pt_BR").boolean_true_label, "Empresa")
        self.assertEqual(
            item.with_context(lang="pt_BR").boolean_false_label, "Pessoa Física"
        )

    def test_renamed_records_are_left_alone(self):
        dashboard = self._create_board()
        item = self._item(dashboard, "Total Contacts")
        item.with_context(lang="en_US").name = "Carteira"
        item.with_context(lang="pt_BR").name = "Carteira"
        dashboard._apply_template_translations(langs=["pt_BR"])
        self.assertEqual(item.with_context(lang="pt_BR").name, "Carteira")
        self.assertEqual(item.with_context(lang="en_US").name, "Carteira")

    def test_translation_is_applied_to_an_existing_board(self):
        """What the language install hook does for a database already in use."""
        dashboard = self._create_board()
        item = self._item(dashboard, "Total Contacts")
        # Back to English everywhere, as if the board had been created before
        # Portuguese was installed.
        dashboard.with_context(lang="pt_BR").name = "Contacts Overview"
        item.with_context(lang="pt_BR").name = "Total Contacts"
        dashboard._apply_template_translations(langs=["pt_BR"])
        self.assertEqual(
            dashboard.with_context(lang="pt_BR").name, "Visão Geral de Contatos"
        )
        self.assertEqual(item.with_context(lang="pt_BR").name, "Total de Contatos")

    def test_board_without_template_is_skipped(self):
        dashboard = self.env["boardkit.dashboard"].create({"name": "Sem template"})
        dashboard._apply_template_translations(langs=["pt_BR"])
        self.assertEqual(dashboard.with_context(lang="pt_BR").name, "Sem template")

    def test_older_boards_are_linked_to_their_template(self):
        """What the upgrade does on a database that predates the link."""
        dashboard = self._create_board()
        item = self._item(dashboard, "Total Contacts")
        dashboard.source_template_id = False
        dashboard.with_context(lang="pt_BR").name = "Contacts Overview"
        item.with_context(lang="pt_BR").name = "Total Contacts"

        self.env["boardkit.dashboard"]._link_boards_to_templates()
        self.assertEqual(dashboard.source_template_id, self.template)
        dashboard._apply_template_translations(langs=["pt_BR"])
        self.assertEqual(
            dashboard.with_context(lang="pt_BR").name, "Visão Geral de Contatos"
        )
        self.assertEqual(item.with_context(lang="pt_BR").name, "Total de Contatos")

    def test_menu_entry_is_labelled_in_both_languages(self):
        """A published board shows its menu in the language of the reader."""
        dashboard = self._create_board()
        dashboard.write({"published": True, "menu_as_app": True})
        menu = dashboard.menu_id.sudo()
        self.assertTrue(menu)
        self.assertEqual(menu.with_context(lang="en_US").name, "Contacts Overview")
        self.assertEqual(
            menu.with_context(lang="pt_BR").name, "Visão Geral de Contatos"
        )

    def test_menu_entry_keeps_the_label_the_manager_typed(self):
        dashboard = self._create_board()
        dashboard.write(
            {"published": True, "menu_as_app": True, "menu_name": "Painel do Diretor"}
        )
        menu = dashboard.menu_id.sudo()
        self.assertEqual(menu.with_context(lang="pt_BR").name, "Painel do Diretor")
        self.assertEqual(menu.with_context(lang="en_US").name, "Painel do Diretor")

    def test_active_languages_exclude_english(self):
        self.assertIn("pt_BR", target_languages(self.env))
        self.assertNotIn("en_US", target_languages(self.env))

    def test_every_term_of_the_core_template_is_translated(self):
        translate = translator("boardkit_dashboard", "pt_BR")
        missing = sorted(
            {
                term
                for term in iter_terms(self.template.get_payload())
                if not translate(term)
            }
        )
        self.assertFalse(
            missing,
            "Terms without a pt_BR translation in i18n_extra: %s" % missing,
        )
