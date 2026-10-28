# Quran data sources

## `quran.json`, Warsh, full Quran

- **Text:** Mushaf Warsh (Warsh ʿan Nafiʿ), KFGQPC print, via Quranpedia.net
- **Provider:** [Quranpedia.net](https://quranpedia.net)
- **Mushaf ID:** 4
- **Dump:** `mushafs-4.json.gz`
- **Dump URL:** <https://api.quranpedia.net/dumps/mushafs-4.json.gz>
- **Dump version:** 2026-10-23
- **Retrieved:** 2026-10-23
- **Download SHA-256:** `60c888d5bab92372bc15397ad07b2ad5771eb29d97308c5b1885758a223363c0`
- **Download size:** 422,507 bytes (gzip)
- **Generated JSON SHA-256:** `ff3194f404f381521750dc89df44d67cc33f16009a852f86b3ea699c16dd6401`
- **Generated JSON size:** 2,728,935 bytes

### License

- **License:** Quranpedia.net Data License
- **License URL:** <https://api.quranpedia.net/dumps/LICENSE.md>
- **License page version:** 2026-10-22
- **Dump version stated by the license:** 2026-10-23
- **Attribution:** Quranpedia.net, <https://quranpedia.net>, dump 2026-10-23

The license says:

> Republishing this data, in full or in part, as a downloadable database or
> dataset requires: (1) crediting Quranpedia.net as the source with a link, and
> (2) stating this dump's version.

The attribution and dump version are also stored inside `quran.json` under
`source.license`.

The content is continuously corrected. Keep this copy current via:

```text
https://quranpedia.net/api/v1/changes?since=2026-10-23
```

### What is included

- 114 surahs
- 6,214 ayahs using Warsh verse numbering
- 30 juz
- 60 hizb
- 240 rub (quarter-hizb)

Warsh verse numbering is not the same as Hafs. For example, Warsh has 6,214
ayahs while Hafs has 6,236. Do not compare ayah numbers across readings without
using the `number_in_hafs` field.

### Basmala

The Warsh Basmala is stored separately at the top level:

```json
"basmala": "بِسْمِ اِ۬للَّهِ اِ۬لرَّحْمَٰنِ اِ۬لرَّحِيمِ"
```

It is not counted as an ayah. Al Fatiha ayah 1 is `اِ۬لْحَمْدُ لِلهِ...`.
Every surah has `basmala_before_surah`; it is `false` only for Surah 9
(At Tawbah).

### Processing

- Quranic text is preserved verbatim from the dump; only outer whitespace was
  stripped.
- The source field named `hizb` is a 1-240 rub (quarter-hizb) index. It is
  stored as `rub`.
- `hizb` (1-60) and `juz` (1-30) are derived from `rub`.
- 26 ayahs had missing juz/hizb values in the source. Their values were
  forward-filled and marked `"location_inferred": true`.
- `number_in_hafs` is retained for cross-reference only.
- No Quranic word was rewritten.

### Display and matching notes

Warsh uses Quranic marks that are not only pause marks. In particular:

- `U+06EA` (empty centre low stop)
- `U+06EC` (rounded high stop with filled centre)
- `U+06E5` / `U+06E6` (small waw / small yeh)

`display_word()` keeps these marks. It removes only pause, sajdah, rub el hizb,
and other annotation marks.

For matching, `normalize_word()` removes all diacritics. `weak_letter_key()` and
`word_match()` provide a second, weaker match that ignores `ا`, `و`, and `ي`,
so Warsh forms such as `الْعَٰلَمِينَ` can match an ASR transcript written as
`العالمين`.
