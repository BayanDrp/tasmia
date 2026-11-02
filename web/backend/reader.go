// reader.go: the local mushaf reader.
//
// The web layer serves Quran text from data/quran/quran.json, not from
// the AI service. The file is loaded once at startup and kept in memory,
// so /api/text keeps working with the Python service stopped.
//
// The word splitter below is a faithful port of core's display_word()
// (core/tasmia_core/normalize.py). The parity test in
// tests/reader_test.go compares every word of every surah against a
// golden file generated from core, so the display and the judge can
// never drift apart.
package backend

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"unicode"
)

// quranFile mirrors the parts of data/quran/quran.json the web layer needs.
type quranFile struct {
	Surahs []quranSurah `json:"surahs"`
}

type quranSurah struct {
	ID          int         `json:"id"`
	Name        string      `json:"name"`
	FullName    string      `json:"full_name"`
	TotalVerses int         `json:"total_verses"`
	Ayahs       []quranAyah `json:"ayahs"`
}

type quranAyah struct {
	Number int    `json:"number"`
	Text   string `json:"text"`
}

// TextWord is one display word in the /api/text response.
type TextWord struct {
	Index int    `json:"index"`
	Ayah  int    `json:"ayah"`
	Text  string `json:"text"`
}

// SurahText is the JSON body of GET /api/text?surah=N.
type SurahText struct {
	Surah       int        `json:"surah"`
	SurahName   string     `json:"surah_name"`
	TotalVerses int        `json:"total_verses"`
	Words       []TextWord `json:"words"`
}

// SurahInfo is one row of the surah list.
type SurahInfo struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	TotalVerses int    `json:"total_verses"`
}

// Reader holds the mushaf in memory, indexed by surah number.
type Reader struct {
	surahs []quranSurah
	byID   map[int]*quranSurah
}

// LoadReader reads quran.json once and indexes it by surah number.
func LoadReader(path string) (*Reader, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read quran file: %w", err)
	}

	var file quranFile
	if err := json.Unmarshal(data, &file); err != nil {
		return nil, fmt.Errorf("parse quran file: %w", err)
	}
	if len(file.Surahs) == 0 {
		return nil, fmt.Errorf("quran file has no surahs")
	}

	byID := make(map[int]*quranSurah, len(file.Surahs))
	for i := range file.Surahs {
		surah := &file.Surahs[i]
		byID[surah.ID] = surah
	}
	return &Reader{surahs: file.Surahs, byID: byID}, nil
}

// Surah returns one surah's display words, 1..114.
func (r *Reader) Surah(n int) (SurahText, error) {
	surah, ok := r.byID[n]
	if !ok {
		return SurahText{}, fmt.Errorf("السورة %d غير موجودة (1..114)", n)
	}

	words := make([]TextWord, 0, surah.TotalVerses*8)
	flat := 0
	for _, ayah := range surah.Ayahs {
		for _, token := range strings.Fields(ayah.Text) {
			word := displayWord(token)
			if word == "" {
				continue
			}
			words = append(words, TextWord{Index: flat, Ayah: ayah.Number, Text: word})
			flat++
		}
	}

	return SurahText{
		Surah:       surah.ID,
		SurahName:   surah.Name,
		TotalVerses: surah.TotalVerses,
		Words:       words,
	}, nil
}

// List returns all surahs in mushaf order.
func (r *Reader) List() []SurahInfo {
	out := make([]SurahInfo, 0, len(r.surahs))
	for _, surah := range r.surahs {
		out = append(out, SurahInfo{
			ID:          surah.ID,
			Name:        surah.Name,
			TotalVerses: surah.TotalVerses,
		})
	}
	return out
}

// displayWord is the Go port of core's display_word(): keep Quranic
// orthography, drop tatweel, annotation marks and punctuation.
func displayWord(word string) string {
	var b strings.Builder
	b.Grow(len(word))

	for _, r := range word {
		if r == '\u0640' { // tatweel
			continue
		}
		if dropDisplayRune(r) {
			continue
		}
		b.WriteRune(r)
	}
	return strings.TrimSpace(b.String())
}

func dropDisplayRune(r rune) bool {
	switch {
	case r >= 0x0610 && r <= 0x061A: // honorifics
		return true
	case r >= 0x06D6 && r <= 0x06E4: // Quranic pause/annotation marks
		return true
	case r >= 0x06E7 && r <= 0x06E9: // small high yeh/noon, sajdah
		return true
	case r == 0x06ED: // small low meem
		return true
	case r >= 0x0897 && r <= 0x089F: // Arabic Extended-B
		return true
	case r >= 0x08CA && r <= 0x08FF: // Arabic Extended-A
		return true
	case r >= 0x10EFC && r <= 0x10EFF: // Arabic Extended-C
		return true
	}

	// Python drops categories P, S, Z and C. In Go, IsGraphic is false
	// for control, format, private use and unassigned runes, which is
	// the C category; P, S and Z are checked explicitly.
	return unicode.IsPunct(r) ||
		unicode.IsSymbol(r) ||
		unicode.IsSpace(r) ||
		!unicode.IsGraphic(r)
}
