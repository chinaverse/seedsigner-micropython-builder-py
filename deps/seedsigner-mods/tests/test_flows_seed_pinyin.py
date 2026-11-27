"""Chinese pinyin seed-word input (builder mod, deps/seedsigner-mods).

Run against a mod-applied app tree; see deps/seedsigner-mods/README.md.
"""
from base import FlowTest, FlowStep

from embit import bip39

from seedsigner.helpers import zh_pinyin
from seedsigner.helpers.zh_pinyin_data import WORDS as ZH_WORDS
from seedsigner.models.seed import Seed
from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.views import seed_views
from seedsigner.views.view import MainMenuView


def _zh(english_mnemonic):
    """The BIP-39 simplified-Chinese characters at the same indices."""
    return [ZH_WORDS[bip39.WORDLIST.index(w)] for w in english_mnemonic.split()]


class TestPinyinSeedEntry(FlowTest):

    def setup_method(self):
        super().setup_method()
        Settings.get_instance().set_value(SettingsConstants.SETTING__MNEMONIC_INPUT_METHOD,
                                          SettingsConstants.MNEMONIC_INPUT__CHINESE_PINYIN)

    def teardown_method(self):
        Settings.get_instance().set_value(SettingsConstants.SETTING__MNEMONIC_INPUT_METHOD,
                                          SettingsConstants.MNEMONIC_INPUT__ENGLISH)
        super().teardown_method()


    def test_chinese_words_are_stored_as_english(self):
        """Characters picked via pinyin end up as the ENGLISH mnemonic: same seed,
        same fingerprint as typing the English words."""
        english = "tone flat shed cool census soul paddle boy flight fantasy stem social"
        controller = self.controller

        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, is_redirect=True),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD),
        ]
        for char in _zh(english):
            sequence.append(FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=char))
        sequence += [
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView),
        ]
        self.run_sequence(sequence)

        seed = controller.storage.seeds[-1]
        assert seed.mnemonic_list == english.split()
        assert seed.wordlist_language_code == SettingsConstants.WORDLIST_LANGUAGE__ENGLISH
        assert seed.seed_bytes == Seed(english.split()).seed_bytes


    def test_back_out_of_first_word(self):
        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, is_redirect=True),
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD),
            FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=1000),  # RET_CODE__BACK_BUTTON
            FlowStep(seed_views.LoadSeedView),
        ]
        self.run_sequence(sequence)


def test_translation_table_is_index_aligned():
    for i, char in enumerate(ZH_WORDS):
        assert zh_pinyin.chinese_to_english(char) == bip39.WORDLIST[i]


def test_non_wordlist_input_is_rejected():
    for bad in ["abandon", "", "的的", "A"]:
        try:
            zh_pinyin.chinese_to_english(bad)
        except ValueError:
            continue
        raise AssertionError("accepted %r" % bad)


def test_candidates():
    labels, keys, values = zh_pinyin.candidate_entries()
    assert len(labels) == len(keys) == len(values)
    assert set(values) == set(ZH_WORDS)                # every character is reachable
    assert all(k.isalpha() and k.islower() and k.isascii() for k in keys)
    shi = [v for k, v in zip(keys, values) if k == "shi"]
    assert "是" in shi and "十" in shi
    # exact syllable sorts before longer ones sharing the prefix
    xi_first = next(k for k in keys if k.startswith("xi"))
    assert xi_first == "xi"
    # u-umlaut typed as v, with nu/lu aliases
    assert "女" in [v for k, v in zip(keys, values) if k == "nv"]
    assert "女" in [v for k, v in zip(keys, values) if k == "nu"]


def test_view_passes_pinyin_cfg_to_native_screen():
    """The native screen gets match_keys/values/cjk_candidates, not the English list."""
    from unittest.mock import patch
    from seedsigner.controller import Controller

    Settings.get_instance().set_value(SettingsConstants.SETTING__MNEMONIC_INPUT_METHOD,
                                      SettingsConstants.MNEMONIC_INPUT__CHINESE_PINYIN)
    try:
        controller = Controller.get_instance()
        controller.storage.init_pending_mnemonic(12)
        with patch("seedsigner.views.view.View.run_screen", autospec=True, return_value="的") as run:
            seed_views.SeedMnemonicEntryView(cur_word_index=0).run()
        kwargs = run.call_args.kwargs
        assert kwargs["cjk_candidates"] is True
        assert kwargs["initial_letters"] == []
        assert len(kwargs["match_keys"]) == len(kwargs["wordlist"]) == len(kwargs["values"])
        assert controller.storage.get_pending_mnemonic_word(0) == "abandon"
    finally:
        controller.storage.discard_pending_mnemonic()
        Settings.get_instance().set_value(SettingsConstants.SETTING__MNEMONIC_INPUT_METHOD,
                                          SettingsConstants.MNEMONIC_INPUT__ENGLISH)
