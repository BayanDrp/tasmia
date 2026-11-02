// Config loading for the Tasmia web backend: the Go twin of
// ai/app/config.py. One shared config.json feeds both stacks.
package backend

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

type Config struct {
	Models struct {
		Default string            `json:"default"`
		Aliases map[string]string `json:"aliases"`
	} `json:"models"`
	Audio struct {
		SampleRate          int     `json:"sample_rate"`
		MaxSeconds          int     `json:"max_seconds"`
		ChunkSeconds        int     `json:"chunk_seconds"`
		ChunkOverlapSeconds int     `json:"chunk_overlap_seconds"`
		SilenceRMS          float64 `json:"silence_rms"`
		TrimSilence         bool    `json:"trim_silence"`
	} `json:"audio"`
	Compute struct {
		Device string `json:"device"`
	} `json:"compute"`
	ServerDocker struct {
		Host string `json:"host"`
		Port int    `json:"port"`
	} `json:"server_docker"`
	ServerWeb struct {
		Host string `json:"host"`
		Port int    `json:"port"`
	} `json:"server_web"`
	WebApp struct {
		Host        string `json:"host"`
		Port        int    `json:"port"`
		FrontendDir string `json:"frontend_dir"`
		QuranPath   string `json:"quran_path"`
	} `json:"web_app"`
	SpaceASR struct {
		Enabled bool   `json:"enabled"`
		Prefer  bool   `json:"prefer"`
		URL     string `json:"url"`
		Timeout int    `json:"timeout_seconds"`
	} `json:"space_asr"`
}

func LoadConfig(path string) (Config, error) {
	// Default: search sensible candidate locations for config.json.
	// TASMIA_CONFIG environment variable overrides all defaults.
	if path == "" {
		if env := os.Getenv("TASMIA_CONFIG"); env != "" {
			path = env
		} else {
			candidates := []string{
				"../../config.json",
				"config.json",
				"../../../config.json",
				"../config.json",
			}
			for _, candidate := range candidates {
				if _, err := os.Stat(candidate); err == nil {
					path = candidate
					break
				}
			}
			if path == "" {
				path = "../../config.json"
			}
		}
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return Config{}, fmt.Errorf("failed to read config: %w", err)
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return Config{}, fmt.Errorf("failed to parse config: %w", err)
	}

	// The Go web server has its own address; server_web belongs to the
	// Python AI service. Two processes, two ports, no fights.
	if config.WebApp.Host == "" {
		config.WebApp.Host = "0.0.0.0"
	}
	if config.WebApp.Port == 0 {
		config.WebApp.Port = 8080
	}
	// Paths in config.json are anchored to the config file's folder, not
	// the current working directory. The server then behaves the same
	// from web/backend, from the repo root, and from a built binary.
	configDir := filepath.Dir(path)

	if config.WebApp.FrontendDir == "" {
		for _, candidate := range []string{"web/frontend", "frontend", "../frontend"} {
			if info, err := os.Stat(resolveFrom(configDir, candidate)); err == nil && info.IsDir() {
				config.WebApp.FrontendDir = candidate
				break
			}
		}
		if config.WebApp.FrontendDir == "" {
			config.WebApp.FrontendDir = "web/frontend"
		}
	}
	config.WebApp.FrontendDir = resolveFrom(configDir, config.WebApp.FrontendDir)

	if config.WebApp.QuranPath == "" {
		for _, candidate := range []string{"data/quran/quran.json", "../data/quran/quran.json"} {
			if info, err := os.Stat(resolveFrom(configDir, candidate)); err == nil && !info.IsDir() {
				config.WebApp.QuranPath = candidate
				break
			}
		}
		if config.WebApp.QuranPath == "" {
			config.WebApp.QuranPath = "data/quran/quran.json"
		}
	}
	config.WebApp.QuranPath = resolveFrom(configDir, config.WebApp.QuranPath)

	return config, nil
}

// resolveFrom anchors a relative config path to the config file's folder.
func resolveFrom(base, path string) string {
	if path == "" || filepath.IsAbs(path) {
		return path
	}
	return filepath.Clean(filepath.Join(base, path))
}
