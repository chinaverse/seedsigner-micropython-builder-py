# Builder-side app mods: Chinese pinyin seed-word input

中文拼音助记词输入（拼音 → BIP-39 简体中文字 → **先翻译成英文助记词**，再派生私钥）。

## What it does

Settings → **Seed word input** → `Chinese pinyin`. When entering a seed word by word
(Seeds → Enter 12/24-word seed, and Tools → Calc final word), the keyboard takes pinyin
and the candidate list shows the BIP-39 simplified-Chinese characters (`是 shi4`).

The chosen character is translated **immediately**, in `SeedMnemonicEntryView`, to the
English BIP-39 word at the same wordlist index (`seedsigner.helpers.zh_pinyin.
chinese_to_english`). Only the English word is stored, so `SeedStorage`, `Seed`, the
BIP-39 checksum and the PBKDF2 key derivation only ever see the English mnemonic; the
wordlist-language setting stays English.

> The wallet is therefore the one of the **English** words at those indices — the words
> the device shows when you review the seed. Another wallet that imports the *Chinese
> characters* as a Chinese BIP-39 mnemonic derives a **different** wallet. Back up the
> English words (or the SeedQR).

Safety: both wordlists are checked against the canonical bitcoin/bips sha256 before the
first translation (`zh_pinyin._verify`); anything that is not a wordlist character
raises instead of being translated.

## Layout

| Path | What |
|---|---|
| `deps/seedsigner-mods/new_files/` | new app modules, overlaid onto `frozen_app/` |
| `deps/seedsigner-mods/patches/` | app patches (paths relative to the app's `src/`) |
| `deps/seedsigner-mods/data/` | wordlist + pinyin source data (generator input) |
| `deps/seedsigner-mods/tests/` | flow tests, run against a mod-applied app tree |
| `deps/seedsigner-lvgl-screens-mods/` | native screen patch + Noto Sans SC subset font |
| `tools/zh_pinyin/gen_assets.py` | regenerates `zh_pinyin_data.py` + the font `.inc` |

Applied by `tools/stage_frozen_app.py` (app, into `frozen_app/` only — the submodule
checkout is never touched) and `scripts/apply_screens_mods.sh` (called from
`scripts/ci_build.sh`; idempotent). The submodule pins are unchanged, so the patches
must be refreshed when `deps/seedsigner` or `deps/seedsigner-lvgl-screens` is bumped.

The mods only reach the device through the **frozen** app (`make docker-build-all`
locally, or the CI dist build: push to `main`, or a manual *Run workflow* with
`builder_ref` set to the branch). A VFS dev deploy of an unmodified app tree via
`tools/deploy_app.py` does not include them.

## Native screen (seed_mnemonic_entry_screen) cfg added

`match_keys` (prefix-match against these instead of `wordlist`), `values` (returned on
accept, de-duplicated per candidate list), `cjk_candidates` (chain the 2048-glyph Noto
Sans SC subset under the candidate font via lv_tiny_ttf). Without them the screen
behaves exactly as before.

## Tests

```
# app checkout at the pinned commit, with LF line endings
git -C <app> apply --directory=src deps/seedsigner-mods/patches/*.patch
cp -R deps/seedsigner-mods/new_files/. <app>/src/
cp deps/seedsigner-mods/tests/*.py <app>/tests/
cd <app> && PYTHONPATH=src:<embit>/src:tests pytest tests/test_flows_seed_pinyin.py
```

Sources: pinyin data from chinaverse/seedsigner-chinese (`chinese-pinyin` branch,
pypinyin TONE3); font: Noto Sans SC, SIL OFL 1.1 (`NotoSansSC-OFL.txt`).
