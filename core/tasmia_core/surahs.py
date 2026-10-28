"""Load Quran data and build the expected word list for a recitation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import Word
from .normalize import display_tokens, normalize_word


DEFAULT_QURAN_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "quran" / "quran.json"
)


class QuranDataError(ValueError):
    """Raised when the Quran data file is malformed."""


@dataclass(frozen=True, slots=True)
class Ayah:
    number: int
    text: str
    juz: int
    hizb: int
    rub: int
    page: int
    number_in_hafs: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Surah:
    id: int
    name: str
    full_name: str
    total_verses: int
    basmala_before_surah: bool
    ayahs: tuple[Ayah, ...]


@dataclass(frozen=True, slots=True)
class Hizb:
    number: int
    juz: int
    start: tuple[int, int]  # (surah, ayah)
    end: tuple[int, int]


def _require_int(mapping: dict, key: str, context: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise QuranDataError(f"{context}: '{key}' must be an integer")
    return value


def _parse_ref(raw_ref: object, context: str) -> tuple[int, int]:
    if not isinstance(raw_ref, dict):
        raise QuranDataError(f"{context} must be an object")
    return (
        _require_int(raw_ref, "surah", context),
        _require_int(raw_ref, "ayah", context),
    )


class QuranRepository:
    """Read only access to the Quran data used by the rest of the core."""

    def __init__(self, data: dict, *, source_path: Path | None = None) -> None:
        if not isinstance(data, dict):
            raise QuranDataError("Quran data must be a JSON object")

        raw_basmala = data.get("basmala")
        if not isinstance(raw_basmala, str) or not raw_basmala.strip():
            raise QuranDataError("Quran data is missing a non-empty 'basmala'")

        self.source_path = source_path
        self.basmala = raw_basmala.strip()
        self._surahs = self._parse_surahs(data.get("surahs"))
        self._surahs_by_id = {surah.id: surah for surah in self._surahs}
        self._hizbs = self._parse_hizbs(data.get("hizbs"))
        self._hizbs_by_number = {hizb.number: hizb for hizb in self._hizbs}
        self._validate()

    @classmethod
    def load(cls, path: str | Path | None = None) -> "QuranRepository":
        """Load the Quran JSON file, or the project default file."""
        data_path = Path(path) if path is not None else DEFAULT_QURAN_PATH
        try:
            raw = json.loads(data_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise QuranDataError(f"Invalid JSON in {data_path}: {exc}") from exc
        return cls(raw, source_path=data_path)

    @classmethod
    def from_dict(cls, data: dict) -> "QuranRepository":
        """Build a repository from an already parsed JSON object."""
        return cls(data)

    @staticmethod
    def _parse_surahs(raw_surahs: object) -> tuple[Surah, ...]:
        if not isinstance(raw_surahs, list) or not raw_surahs:
            raise QuranDataError(
                "Quran data must contain a non-empty 'surahs' list"
            )

        result: list[Surah] = []
        seen_ids: set[int] = set()

        for raw_surah in raw_surahs:
            if not isinstance(raw_surah, dict):
                raise QuranDataError("Each surah must be an object")

            surah_id = _require_int(raw_surah, "id", "surah")
            if surah_id in seen_ids:
                raise QuranDataError(f"Duplicate surah id: {surah_id}")
            seen_ids.add(surah_id)

            name = raw_surah.get("name")
            if not isinstance(name, str) or not name.strip():
                raise QuranDataError(f"Surah {surah_id} has no name")
            full_name = raw_surah.get("full_name", name)
            if not isinstance(full_name, str) or not full_name.strip():
                raise QuranDataError(f"Surah {surah_id} has no full_name")

            basmala_before_surah = raw_surah.get("basmala_before_surah")
            if not isinstance(basmala_before_surah, bool):
                raise QuranDataError(
                    f"Surah {surah_id}: 'basmala_before_surah' must be a boolean"
                )

            raw_ayahs = raw_surah.get("ayahs")
            if not isinstance(raw_ayahs, list) or not raw_ayahs:
                raise QuranDataError(f"Surah {surah_id} has no ayahs")

            total_verses = _require_int(
                raw_surah, "total_verses", f"Surah {surah_id}"
            )
            if total_verses != len(raw_ayahs):
                raise QuranDataError(
                    f"Surah {surah_id}: total_verses is {total_verses}, "
                    f"but there are {len(raw_ayahs)} ayahs"
                )

            ayahs: list[Ayah] = []
            for expected_number, raw_ayah in enumerate(raw_ayahs, start=1):
                if not isinstance(raw_ayah, dict):
                    raise QuranDataError(
                        f"Surah {surah_id}, ayah {expected_number}: "
                        "ayah must be an object"
                    )

                context = f"Surah {surah_id}, ayah {expected_number}"
                number = _require_int(raw_ayah, "number", context)
                if number != expected_number:
                    raise QuranDataError(
                        f"{context}: expected ayah number {expected_number}, "
                        f"got {number}"
                    )

                text = raw_ayah.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise QuranDataError(f"{context}: text must be non-empty")

                raw_hafs = raw_ayah.get("number_in_hafs", [])
                if not isinstance(raw_hafs, list) or any(
                    not isinstance(value, int) or isinstance(value, bool)
                    for value in raw_hafs
                ):
                    raise QuranDataError(
                        f"{context}: 'number_in_hafs' must be a list of integers"
                    )

                ayahs.append(
                    Ayah(
                        number=number,
                        text=text.strip(),
                        juz=_require_int(raw_ayah, "juz", context),
                        hizb=_require_int(raw_ayah, "hizb", context),
                        rub=_require_int(raw_ayah, "rub", context),
                        page=_require_int(raw_ayah, "page", context),
                        number_in_hafs=tuple(raw_hafs),
                    )
                )

            result.append(
                Surah(
                    id=surah_id,
                    name=name.strip(),
                    full_name=full_name.strip(),
                    total_verses=total_verses,
                    basmala_before_surah=basmala_before_surah,
                    ayahs=tuple(ayahs),
                )
            )

        return tuple(result)

    @staticmethod
    def _parse_hizbs(raw_hizbs: object) -> tuple[Hizb, ...]:
        if not isinstance(raw_hizbs, list) or not raw_hizbs:
            raise QuranDataError(
                "Quran data must contain a non-empty 'hizbs' list"
            )

        result: list[Hizb] = []
        for expected_number, raw_hizb in enumerate(raw_hizbs, start=1):
            if not isinstance(raw_hizb, dict):
                raise QuranDataError("Each hizb must be an object")

            context = f"Hizb {expected_number}"
            number = _require_int(raw_hizb, "number", context)
            if number != expected_number:
                raise QuranDataError(
                    f"{context}: expected hizb number {expected_number}, "
                    f"got {number}"
                )

            result.append(
                Hizb(
                    number=number,
                    juz=_require_int(raw_hizb, "juz", context),
                    start=_parse_ref(raw_hizb.get("start"), f"{context} start"),
                    end=_parse_ref(raw_hizb.get("end"), f"{context} end"),
                )
            )

        return tuple(result)

    def _validate(self) -> None:
        expected_ids = list(range(1, 115))
        actual_ids = [surah.id for surah in self._surahs]
        if actual_ids != expected_ids:
            raise QuranDataError("Surah IDs must be exactly 1..114 in order")

        if [hizb.number for hizb in self._hizbs] != list(range(1, 61)):
            raise QuranDataError("Hizb numbers must be exactly 1..60 in order")

        for surah in self._surahs:
            if surah.total_verses != len(surah.ayahs):
                raise QuranDataError(
                    f"Surah {surah.id}: total_verses does not match ayahs"
                )

            for expected_number, ayah in enumerate(surah.ayahs, start=1):
                context = f"Surah {surah.id}, ayah {ayah.number}"
                if ayah.number != expected_number:
                    raise QuranDataError(
                        f"{context}: ayah numbers must be sequential"
                    )
                if not 1 <= ayah.juz <= 30:
                    raise QuranDataError(f"{context}: juz must be 1..30")
                if not 1 <= ayah.hizb <= 60:
                    raise QuranDataError(f"{context}: hizb must be 1..60")
                if not 1 <= ayah.rub <= 240:
                    raise QuranDataError(f"{context}: rub must be 1..240")
                if ayah.hizb != (ayah.rub - 1) // 4 + 1:
                    raise QuranDataError(
                        f"{context}: hizb does not match rub"
                    )
                if ayah.juz != (ayah.hizb - 1) // 2 + 1:
                    raise QuranDataError(
                        f"{context}: juz does not match hizb"
                    )

                hizb = self._hizbs_by_number.get(ayah.hizb)
                if hizb is None:
                    raise QuranDataError(f"{context}: unknown hizb")
                ref = (surah.id, ayah.number)
                if not hizb.start <= ref <= hizb.end:
                    raise QuranDataError(
                        f"{context}: ayah is outside the hizb range"
                    )

        present_hizbs = {
            ayah.hizb for surah in self._surahs for ayah in surah.ayahs
        }
        if present_hizbs != set(range(1, 61)):
            raise QuranDataError("All 60 hizbs must contain at least one ayah")

        present_juz = {
            ayah.juz for surah in self._surahs for ayah in surah.ayahs
        }
        if present_juz != set(range(1, 31)):
            raise QuranDataError("All 30 juz must contain at least one ayah")

        for hizb in self._hizbs:
            if hizb.juz != (hizb.number - 1) // 2 + 1:
                raise QuranDataError(
                    f"Hizb {hizb.number}: juz does not match hizb"
                )
            if hizb.start > hizb.end:
                raise QuranDataError(f"Hizb {hizb.number}: start is after end")

            start_surah = self._surahs_by_id.get(hizb.start[0])
            if start_surah is None:
                raise QuranDataError(
                    f"Hizb {hizb.number}: unknown start surah"
                )
            if not 1 <= hizb.start[1] <= start_surah.total_verses:
                raise QuranDataError(
                    f"Hizb {hizb.number}: start ayah is out of range"
                )
            if start_surah.ayahs[hizb.start[1] - 1].hizb != hizb.number:
                raise QuranDataError(
                    f"Hizb {hizb.number}: start ayah has a different hizb"
                )

            end_surah = self._surahs_by_id.get(hizb.end[0])
            if end_surah is None:
                raise QuranDataError(f"Hizb {hizb.number}: unknown end surah")
            if not 1 <= hizb.end[1] <= end_surah.total_verses:
                raise QuranDataError(
                    f"Hizb {hizb.number}: end ayah is out of range"
                )
            if end_surah.ayahs[hizb.end[1] - 1].hizb != hizb.number:
                raise QuranDataError(
                    f"Hizb {hizb.number}: end ayah has a different hizb"
                )

    def get_surah(self, surah_id: int) -> Surah:
        """Get a Surah by its ID."""
        try:
            return self._surahs_by_id[surah_id]
        except KeyError:
            raise ValueError(f"Unknown surah: {surah_id}") from None

    def get_ayah(self, surah_id: int, ayah_number: int) -> Ayah:
        """Get an Ayah by its number."""
        surah = self.get_surah(surah_id)
        if (
            not isinstance(ayah_number, int)
            or isinstance(ayah_number, bool)
            or not 1 <= ayah_number <= surah.total_verses
        ):
            raise ValueError(
                f"Invalid ayah {ayah_number} for surah {surah_id} "
                f"(1..{surah.total_verses})"
            )
        return surah.ayahs[ayah_number - 1]

    def get_hizb(self, hizb_number: int) -> Hizb:
        """Get a Hizb by its number."""
        try:
            return self._hizbs_by_number[hizb_number]
        except KeyError:
            raise ValueError(f"Unknown hizb: {hizb_number}") from None

    def list_surahs(self) -> list[Surah]:
        """List all Surahs."""
        return list(self._surahs)

    def list_hizbs(self) -> list[Hizb]:
        """List all Hizbs."""
        return list(self._hizbs)

    def _basmala_words(self, surah_id: int) -> list[Word]:
        return [
            Word(
                text=text,
                normalized=normalize_word(text),
                surah=surah_id,
                ayah=0,
                index=index,
            )
            for index, text in enumerate(display_tokens(self.basmala), start=1)
        ]

    def expected_words(
        self,
        surah: int,
        ayah_from: int = 1,
        ayah_to: int | None = None,
        include_basmala: bool = True,
    ) -> list[Word]:
        """Get the expected words for a range of ayahs in a surah."""
        surah_data = self.get_surah(surah)

        if ayah_to is None:
            ayah_to = surah_data.total_verses

        if (
            not isinstance(ayah_from, int)
            or isinstance(ayah_from, bool)
            or not isinstance(ayah_to, int)
            or isinstance(ayah_to, bool)
        ):
            raise ValueError("ayah_from and ayah_to must be integers")

        if not 1 <= ayah_from <= ayah_to <= surah_data.total_verses:
            raise ValueError(
                f"Invalid ayah range {ayah_from}..{ayah_to} for surah "
                f"{surah_data.id} (1..{surah_data.total_verses})"
            )

        words: list[Word] = []

        if include_basmala and ayah_from == 1 and surah_data.basmala_before_surah:
            words.extend(self._basmala_words(surah_data.id))

        for ayah in surah_data.ayahs[ayah_from - 1 : ayah_to]:
            for index, text in enumerate(display_tokens(ayah.text), start=1):
                words.append(
                    Word(
                        text=text,
                        normalized=normalize_word(text),
                        surah=surah_data.id,
                        ayah=ayah.number,
                        index=index,
                    )
                )

        return words


__all__ = [
    "Ayah",
    "DEFAULT_QURAN_PATH",
    "Hizb",
    "QuranDataError",
    "QuranRepository",
    "Surah",
]
