// Tests for the local mushaf reader: shape, validation, the HTTP door,
// and full parity with core's word splitter.
package tests

import (
	"encoding/json"
	"net/http"
	"os"
	"strconv"
	"testing"

	"backend"
)

const quranPath = "../../../data/quran/quran.json"

func loadReader(t *testing.T) *backend.Reader {
	t.Helper()
	reader, err := backend.LoadReader(quranPath)
	if err != nil {
		t.Fatalf("load reader: %v", err)
	}
	return reader
}

func TestReaderSurah94(t *testing.T) {
	reader := loadReader(t)

	text, err := reader.Surah(94)
	if err != nil {
		t.Fatalf("surah 94: %v", err)
	}
	if text.Surah != 94 || text.SurahName != "الشرح" || text.TotalVerses != 8 {
		t.Fatalf("header = %+v, want surah 94 الشرح with 8 verses", text)
	}
	if len(text.Words) != 27 {
		t.Fatalf("words = %d, want 27", len(text.Words))
	}

	first := text.Words[0]
	if first.Index != 0 || first.Ayah != 1 || first.Text != "اَلَمْ" {
		t.Errorf("first word = %+v, want index 0, ayah 1, اَلَمْ", first)
	}

	last := text.Words[len(text.Words)-1]
	if last.Index != 26 || last.Ayah != 8 || last.Text != "فَارْغَبْ" {
		t.Errorf("last word = %+v, want index 26, ayah 8, فَارْغَبْ", last)
	}
}

func TestReaderRejectsUnknownSurah(t *testing.T) {
	reader := loadReader(t)

	for _, number := range []int{0, -1, 115} {
		if _, err := reader.Surah(number); err == nil {
			t.Errorf("surah %d: expected an error, got nil", number)
		}
	}
}

func TestReaderParityWithCore(t *testing.T) {
	reader := loadReader(t)

	data, err := os.ReadFile("testdata/quran_text_golden.json")
	if err != nil {
		t.Fatalf("read golden: %v", err)
	}

	type goldenWord struct {
		Ayah int    `json:"ayah"`
		Text string `json:"text"`
	}
	var golden map[string][]goldenWord
	if err := json.Unmarshal(data, &golden); err != nil {
		t.Fatalf("parse golden: %v", err)
	}

	for number := 1; number <= 114; number++ {
		text, err := reader.Surah(number)
		if err != nil {
			t.Fatalf("surah %d: %v", number, err)
		}

		want := golden[strconv.Itoa(number)]
		if len(text.Words) != len(want) {
			t.Fatalf("surah %d: %d words, golden has %d", number, len(text.Words), len(want))
		}
		for i := range want {
			got := text.Words[i]
			if got.Text != want[i].Text || got.Ayah != want[i].Ayah {
				t.Fatalf(
					"surah %d word %d: got %q (ayah %d), want %q (ayah %d)",
					number, i, got.Text, got.Ayah, want[i].Text, want[i].Ayah,
				)
			}
		}
	}
}

func TestTextEndpoint(t *testing.T) {
	server := newTestServer(t)

	resp, err := http.Get(server.URL + "/api/text?surah=94")
	if err != nil {
		t.Fatalf("GET /api/text: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200", resp.StatusCode)
	}

	var text backend.SurahText
	if err := json.NewDecoder(resp.Body).Decode(&text); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if text.Surah != 94 || len(text.Words) != 27 {
		t.Errorf("text = surah %d with %d words, want 94 with 27", text.Surah, len(text.Words))
	}

	bad, err := http.Get(server.URL + "/api/text?surah=999")
	if err != nil {
		t.Fatalf("GET bad surah: %v", err)
	}
	defer bad.Body.Close()

	if bad.StatusCode != http.StatusBadRequest {
		t.Errorf("bad surah status = %d, want 400", bad.StatusCode)
	}
}
