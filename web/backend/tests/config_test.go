// Tests for the Tasmia web backend, kept in their own package so they
// only see the public surface of "backend", exactly like outside users.
package tests

import (
	"testing"

	"backend"
)

func TestLoadConfigDefaults(t *testing.T) {
	// go test runs inside tests/, so the repo root is three levels up.
	config, err := backend.LoadConfig("../../../config.json")
	if err != nil {
		t.Fatalf("LoadConfig with default path failed: %v", err)
	}

	if config.ServerWeb.Host != "0.0.0.0" || config.ServerWeb.Port != 7860 {
		t.Errorf("server_web = %s:%d, want 0.0.0.0:7860", config.ServerWeb.Host, config.ServerWeb.Port)
	}

	if config.ServerDocker.Port != 8000 {
		t.Errorf("server_docker port = %d, want 8000", config.ServerDocker.Port)
	}

	if config.Models.Default != "quick" {
		t.Errorf("default model = %q, want %q", config.Models.Default, "quick")
	}

	if config.Models.Aliases["warsh"] == "" {
		t.Error("aliases must contain a warsh entry")
	}

	if !config.Audio.TrimSilence {
		t.Error("audio.trim_silence should be true in the shared config")
	}
}

func TestLoadConfigMissingFile(t *testing.T) {
	_, err := backend.LoadConfig("/nonexistent/config.json")
	if err == nil {
		t.Fatal("expected an error for a missing config file, got nil")
	}
}

func TestLoadConfigAutoDiscovery(t *testing.T) {
	config, err := backend.LoadConfig("")
	if err != nil {
		t.Fatalf("LoadConfig(\"\") failed: %v", err)
	}
	if config.Models.Default != "quick" {
		t.Errorf("default model = %q, want %q", config.Models.Default, "quick")
	}
}
