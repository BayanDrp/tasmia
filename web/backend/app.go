// The Tasmia web application: routing, the frontend file server and
// response helpers. Lives in the library package so tests can reach
// it (package main cannot be imported).
package backend

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
)

type App struct {
	frontendDir string // where the browser files live
	mux         *http.ServeMux
	ai          *AIClient // the private door to the local Python service
	reader      *Reader   // the local mushaf, independent of the AI service
}

// New builds the whole application from a loaded config. The mushaf is
// loaded once here; a missing or malformed quran.json fails startup.
func New(config *Config) (*App, error) {
	reader, err := LoadReader(config.WebApp.QuranPath)
	if err != nil {
		return nil, fmt.Errorf("load quran: %w", err)
	}

	mux := http.NewServeMux()
	a := &App{
		frontendDir: config.WebApp.FrontendDir,
		mux:         mux,
		ai:          NewAIClient(config.ServerWeb.Host, config.ServerWeb.Port),
		reader:      reader,
	}
	a.routes()
	return a, nil
}

func (a *App) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	log.Printf("%s %s", r.Method, r.URL.Path)
	a.mux.ServeHTTP(w, r)
}

// routes: the table of every door. Patterns are Go 1.22 style
// "METHOD path"; the frontend file server is the catch-all and the
// /api routes win by specificity.
func (a *App) routes() {
	// everything in frontend/ served as-is: index.html at /, css/,
	// js/, assets/ (fonts), and later manifest.json + sw.js
	a.mux.Handle("GET /", http.FileServer(http.Dir(a.frontendDir)))

	a.mux.HandleFunc("GET /recite", a.handleRecitePage)
	a.mux.HandleFunc("GET /recite.html", a.handleRecitePage)
	a.mux.HandleFunc("GET /dashboard", a.handleDashboardPage)
	a.mux.HandleFunc("GET /dashboard.html", a.handleDashboardPage)
	a.mux.HandleFunc("GET /api/health", a.handleHealth)
	a.mux.HandleFunc("GET /api/text", a.handleText)
	a.mux.HandleFunc("POST /api/recite", a.handleRecite)
}

func (a *App) respondJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")

	json.NewEncoder(w).Encode(v)
}
