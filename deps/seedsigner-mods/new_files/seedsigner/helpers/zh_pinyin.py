"""Chinese (simplified) pinyin INPUT METHOD for BIP-39 seed words.

The user types pinyin and picks the BIP-39 simplified-Chinese character from a
candidate list. The character is an input alias ONLY: `chinese_to_english()`
translates it to the ENGLISH BIP-39 word at the same wordlist index before it is
handed to SeedStorage, so the pending mnemonic, the Seed, and therefore the
PBKDF2 key derivation only ever see the English mnemonic.

Consequence the user must know: the resulting wallet is the one of the ENGLISH
words at those indices (what the device shows when reviewing the seed), not the
"Chinese-mnemonic" wallet another BIP-39 wallet would derive from the same
characters.

Integrity: a wrong index mapping would silently produce a different wallet, so
both wordlists are checked against the canonical bitcoin/bips sha256 before the
first lookup, and any mismatch raises instead of translating.
"""
import hashlib

from embit import bip39

from seedsigner.helpers import zh_pinyin_data as _data


# sha256 of bitcoin/bips bip-0039/{chinese_simplified,english}.txt
# (words joined with "\n", trailing "\n").
CHINESE_SIMPLIFIED_SHA256 = "5c5942792bd8340cb8b27cd592f1015edf56a8c5b26276ee18a482428e7c5726"
ENGLISH_SHA256 = "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"

NEUTRAL_TONE = 5  # sorts after tones 1-4


class PinyinDataError(Exception):
    pass


_char_to_index = None
_entries = None   # (labels, match_keys, values), built once


def _sha256_hex(text):
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return "".join("%02x" % b for b in digest)


def _verify():
    global _char_to_index
    if _char_to_index is not None:
        return

    words = _data.WORDS
    if len(words) != 2048:
        raise PinyinDataError("Chinese wordlist must have 2048 characters")
    if _sha256_hex("\n".join(words) + "\n") != CHINESE_SIMPLIFIED_SHA256:
        raise PinyinDataError("Chinese wordlist does not match BIP-39")

    english = bip39.WORDLIST
    if len(english) != 2048 or _sha256_hex("\n".join(english) + "\n") != ENGLISH_SHA256:
        raise PinyinDataError("English wordlist does not match BIP-39")

    index = {}
    for i, char in enumerate(words):
        index[char] = i
    if len(index) != 2048:
        raise PinyinDataError("Chinese wordlist has duplicates")

    if len(_data.PINYIN.split("\n")) != 2048:
        raise PinyinDataError("pinyin table must have 2048 lines")

    _char_to_index = index


def chinese_to_english(char):
    """Translate one BIP-39 simplified-Chinese word to the English BIP-39 word at
    the same index. Raises ValueError for anything that is not a wordlist entry."""
    _verify()
    i = _char_to_index.get(char)
    if i is None:
        raise ValueError("not a BIP-39 simplified-Chinese word")
    return bip39.WORDLIST[i]


def candidate_entries():
    """Data for the native seed_mnemonic_entry_screen in pinyin mode.

    Returns three parallel lists, one entry per (character, reading):
      labels      shown in the candidate list, e.g. "是 shi4"
      match_keys  toneless pinyin the typed letters are prefix-matched against
      values      the character returned when the entry is chosen (the screen
                  shows each value at most once per candidate list)
    Ordered by pinyin, then tone (1-4, neutral last), then BIP-39 index, so the
    exact syllable typed comes first ("xi" before "xian").
    "v" spells u-umlaut (nv3 = 女); "nu"/"lu" are accepted as aliases for nv/lv.
    """
    global _entries
    if _entries is not None:
        return _entries
    _verify()

    words = _data.WORDS
    rows = []
    for i, readings in enumerate(_data.PINYIN.split("\n")):
        char = words[i]
        seen = []
        for reading in readings.split(","):
            last = reading[-1]
            if "1" <= last <= "4":
                base, tone = reading[:-1], int(last)
            else:
                base, tone = reading, NEUTRAL_TONE
            keys = [base]
            if "v" in base and base[0] in "nl":
                keys.append(base.replace("v", "u"))
            for key in keys:
                if key in seen:
                    continue  # same syllable in another tone: keep the first one
                seen.append(key)
                label_reading = key + (str(tone) if tone != NEUTRAL_TONE else "")
                rows.append((key, tone, i, char + " " + label_reading))

    rows.sort()
    labels = [r[3] for r in rows]
    match_keys = [r[0] for r in rows]
    values = [words[r[2]] for r in rows]
    _entries = (labels, match_keys, values)
    return _entries
