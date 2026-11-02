// The API doors the browser knocks on.
package backend

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"path/filepath"
	"strconv"
)

// maxAudioBytes caps one upload (a phone webm take is 1-2 MB).
const maxAudioBytes = 20 << 20 // 20 MB

// handleRecite: THE door. Browser multipart in, session JSON out.
//
//	browser --POST /api/recite--> Go --multipart--> Python
//	   ▲                             |                    |
//	   └--------- session JSON ------┴-- session JSON ----┘
//
// Stages: 0 size guard, 1 parse form, 2 audio part, 3 form fields,
// 4 the call, 5 map the outcome.
func (a *App) handleRecite(w http.ResponseWriter, r *http.Request) {
	// Stage 0: the bouncer. Cap the body before touching it.
	r.Body = http.MaxBytesReader(w, r.Body, maxAudioBytes)

	// Stage 1: parse the multipart form (8 MB in memory, rest on disk).
	if err := r.ParseMultipartForm(8 << 20); err != nil {
		respondError(w, http.StatusBadRequest, "الطلب غير صالح: التسجيل مفقود أو أكبر من الحد")
		return
	}

	// Stage 2: the file part. "audio" is a contract string: app.js must
	// append its FormData under exactly this name.
	file, header, err := r.FormFile("audio")
	if err != nil {
		respondError(w, http.StatusBadRequest, "لم يتم العثور على الملف الصوتي")
		return
	}
	defer file.Close()
	audio, err := io.ReadAll(file)
	if err != nil {
		respondError(w, http.StatusBadRequest, "تعذر قراءة الملف الصوتي")
		return
	}

	// Stage 3: the five form fields. On the wire everything is a string,
	// so integers are parsed here. Empty or malformed values fall back
	// to the same defaults the Python service uses (Form(0), Form(1)).
	req := ReciteRequest{
		Model:    r.FormValue("model"),
		Surah:    atoiDefault(r.FormValue("surah"), 0),
		AyahFrom: atoiDefault(r.FormValue("ayah_from"), 1),
		AyahTo:   atoiDefault(r.FormValue("ayah_to"), 0),
		Mode:     r.FormValue("mode"),
	}

	// Stage 4: the call to the local AI service.
	session, err := a.ai.Recite(audio, header.Filename, req)

	// Stage 5: three doors out.
	var apiErr *APIError
	switch {
	case errors.As(err, &apiErr):
		// The AI service answered with a real status (400, 501, ...):
		// pass status and body through untouched. One source of truth.
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(apiErr.Status)
		w.Write(apiErr.Body)
	case err != nil:
		// Unreachable service (connection refused, timeout, ...).
		respondError(w, http.StatusBadGateway, "خدمة الذكاء غير متاحة")
	default:
		a.respondJSON(w, session)
	}
}

// handleText serves one surah from the local mushaf. Read-only and
// independent of the AI service: the text lives in data/quran/quran.json.
func (a *App) handleText(w http.ResponseWriter, r *http.Request) {
	surah, err := strconv.Atoi(r.URL.Query().Get("surah"))
	if err != nil {
		respondError(w, http.StatusBadRequest, "رقم السورة غير صالح")
		return
	}

	text, err := a.reader.Surah(surah)
	if err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}
	a.respondJSON(w, text)
}

// handleRecitePage serves the recitation tool page.
func (a *App) handleRecitePage(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, filepath.Join(a.frontendDir, "recite.html"))
}

// handleDashboardPage serves the recitation history and statistics page.
func (a *App) handleDashboardPage(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, filepath.Join(a.frontendDir, "dashboard.html"))
}

// handleHealth: a tiny door for demos, monitors and tests.
func (a *App) handleHealth(w http.ResponseWriter, r *http.Request) {
	a.respondJSON(w, map[string]string{"status": "ok"})
}

// respondError writes a JSON {"detail": ...} body, mirroring the error
// shape of the Python service.
func respondError(w http.ResponseWriter, status int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]string{"detail": message})
}

// atoiDefault parses a form integer; empty or malformed values fall
// back to def (the Go twin of FastAPI's Form(default)).
func atoiDefault(s string, def int) int {
	if s == "" {
		return def
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return def
	}
	return n
}
