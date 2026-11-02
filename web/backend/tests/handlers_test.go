// Tests for the API doors. No Python service needed: the health and
// recite validation paths are fully Go-side.
package tests

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"backend"
)

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	config, err := backend.LoadConfig("../../../config.json")
	if err != nil {
		t.Fatalf("load config: %v", err)
	}
	app, err := backend.New(&config)
	if err != nil {
		t.Fatalf("build app: %v", err)
	}

	server := httptest.NewServer(app)
	t.Cleanup(server.Close)
	return server
}

func TestHealth(t *testing.T) {
	server := newTestServer(t)

	resp, err := http.Get(server.URL + "/api/health")
	if err != nil {
		t.Fatalf("GET /api/health: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	if !strings.Contains(string(body), `"status":"ok"`) {
		t.Errorf("body = %s, want it to contain %q", body, `"status":"ok"`)
	}
}

func TestUnknownPathIs404(t *testing.T) {
	server := newTestServer(t)

	resp, err := http.Get(server.URL + "/no/such/door")
	if err != nil {
		t.Fatalf("GET /no/such/door: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("status = %d, want 404 (the {$} anchor must not swallow paths)", resp.StatusCode)
	}
}

func TestReciteWithoutAudioIs400(t *testing.T) {
	server := newTestServer(t)

	// A broken multipart body: Go must answer 400 itself, before any
	// Python service is involved.
	resp, err := http.Post(server.URL+"/api/recite",
		"multipart/form-data; boundary=notarealboundary",
		strings.NewReader("this is not multipart data"))
	if err != nil {
		t.Fatalf("POST /api/recite: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("status = %d, want 400", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	if !strings.Contains(string(body), `"detail"`) {
		t.Errorf("body = %s, want it to contain %q", body, `"detail"`)
	}
}
