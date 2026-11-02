// Client for the local AI service (ai/app/main.py).
//
// The Go backend is the only public server: the browser talks to Go,
// Go forwards the recording to the Python service on localhost and
// hands the session verdict back as JSON. The types below are the Go
// mirror of the Python response contract.
package backend

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

// ReciteRequest carries what the browser told us about the recitation.
// Surah == 0 means: transcribe only, no judging.
type ReciteRequest struct {
	Model    string // "quick", "warsh" or any HF repo id
	Surah    int    // e.g. 94; 0 = transcribe only
	AyahFrom int    // 1 (used when Surah > 0)
	AyahTo   int    // 0 = to the end of the surah
	Mode     string // "remove_tashkeel", "standard", or "warsh"
}

// Session is the Go mirror of the Python response. Missing keys decode
// to zero values, so one struct serves both the plain transcription
// response ({"text", "model"}) and the full judged session.
type Session struct {
	Text           string         `json:"text"`
	Model          string         `json:"model"`
	SchemaVersion  int            `json:"schema_version"`
	Surah          int            `json:"surah"`
	SurahName      string         `json:"surah_name"`
	AyahFrom       int            `json:"ayah_from"`
	AyahTo         *int           `json:"ayah_to"` // null = to the end
	Score          float64        `json:"score"`
	StrictAccuracy float64        `json:"strict_accuracy"`
	Counts         map[string]int `json:"counts"`
	TotalWords     int            `json:"total_words"`
	Words          []WordVerdict  `json:"words"`
	Extras         []ExtraVerdict `json:"extras"`
	LatencyMS      *int           `json:"latency_ms"`
}

// WordVerdict is one expected mushaf word and how it was recited.
type WordVerdict struct {
	Expected    string   `json:"expected"`
	Heard       *string  `json:"heard"` // null when the word was not recited
	Status      string   `json:"status"`
	Ayah        int      `json:"ayah"`
	Index       int      `json:"index"`
	Start       *float64 `json:"start"`
	End         *float64 `json:"end"`
	Probability *float64 `json:"probability"`
	Distance    *int     `json:"distance"`
}

// ExtraVerdict is a heard word that has no place in the mushaf text.
type ExtraVerdict struct {
	Text       string `json:"text"`
	Status     string `json:"status"`
	AfterIndex int    `json:"after_index"`
}

// APIError is a non-success answer from the AI service. It keeps the
// original status and body so handlers can pass them through untouched
// (the thin-proxy rule: a Python 501 must reach the browser as a 501).
type APIError struct {
	Status int
	Body   []byte
}

func (e *APIError) Error() string {
	return fmt.Sprintf("ai service: %s: %s", http.StatusText(e.Status), e.Body)
}

// AIClient talks to the local Python ASR service.
type AIClient struct {
	baseURL string
	http    *http.Client
}

// NewAIClient targets the AI service from config.json, or the full
// TASMIA_AI_URL when set. Render uses the latter for the HF Space URL.
// A bind host of 0.0.0.0 is normalized to 127.0.0.1 (0.0.0.0 is for
// listening, not for dialing).
func NewAIClient(host string, port int) *AIClient {
	if url := strings.TrimRight(os.Getenv("TASMIA_AI_URL"), "/"); url != "" {
		return &AIClient{
			baseURL: url,
			// transcription takes ~35 s on CPU; be generous
			http: &http.Client{Timeout: 300 * time.Second},
		}
	}
	if host == "" || host == "0.0.0.0" {
		host = "127.0.0.1"
	}
	return &AIClient{
		baseURL: fmt.Sprintf("http://%s:%d", host, port),
		// transcription takes ~35 s on CPU; be generous
		http: &http.Client{Timeout: 300 * time.Second},
	}
}

// Recite sends one recording to the AI service and returns the verdict.
func (c *AIClient) Recite(audio []byte, filename string, req ReciteRequest) (*Session, error) {
	var buffer bytes.Buffer
	writer := multipart.NewWriter(&buffer)

	audioPart, err := writer.CreateFormFile("audio", filename)
	if err != nil {
		return nil, fmt.Errorf("create audio form file: %w", err)
	}
	if _, err := audioPart.Write(audio); err != nil {
		return nil, fmt.Errorf("write audio form file: %w", err)
	}
	if err := writer.WriteField("model", req.Model); err != nil {
		return nil, fmt.Errorf("write model form field: %w", err)
	}
	if req.Surah > 0 {
		fields := []struct {
			name  string
			value string
		}{
			{name: "surah", value: strconv.Itoa(req.Surah)},
			{name: "ayah_from", value: strconv.Itoa(req.AyahFrom)},
			{name: "mode", value: req.Mode},
		}
		if req.AyahTo > 0 {
			fields = append(fields, struct {
				name  string
				value string
			}{name: "ayah_to", value: strconv.Itoa(req.AyahTo)})
		}
		for _, field := range fields {
			if err := writer.WriteField(field.name, field.value); err != nil {
				return nil, fmt.Errorf("write %s form field: %w", field.name, err)
			}
		}
	}
	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("close multipart form: %w", err)
	}
	request, err := http.NewRequest("POST", c.baseURL+"/api/transcribe", &buffer)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}

	request.Header.Set("Content-Type", writer.FormDataContentType())
	resp, err := c.http.Do(request)
	if err != nil {
		return nil, fmt.Errorf("send request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, &APIError{Status: resp.StatusCode, Body: body}
	}

	session := Session{}
	if err := json.Unmarshal(body, &session); err != nil {
		return nil, fmt.Errorf("unmarshal response body: %w", err)
	}
	return &session, nil
}
