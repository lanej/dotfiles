package main

import (
	"bytes"
	_ "embed"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"time"
)

//go:embed config.json
var embeddedConfig []byte

// effectiveConfigPath resolves the configuration file path the same way for
// every entrypoint: an explicit flag value wins, otherwise a config.json
// sitting beside the running executable is used if present, otherwise the
// empty string (meaning: fall back to the embedded default).
func effectiveConfigPath(flagValue, executable string) string {
	if flagValue != "" {
		return flagValue
	}
	adjacent := filepath.Join(filepath.Dir(executable), "config.json")
	if _, err := os.Stat(adjacent); !os.IsNotExist(err) {
		return adjacent
	}
	return ""
}

type configuration struct {
	Port               int               `json:"port"`
	DefaultRegion      string            `json:"default_region"`
	ModelRegions       map[string]string `json:"model_regions"`
	RegionFallbacks    map[string]string `json:"region_fallbacks"`
	HeaderTimeout      string            `json:"header_timeout"`
	StreamIdleTimeout  string            `json:"stream_idle_timeout"`
	ClientWriteTimeout string            `json:"client_write_timeout"`
}

func loadConfiguration(path string) (configuration, error) {
	data := embeddedConfig
	if path != "" {
		var err error
		data, err = os.ReadFile(path)
		if err != nil {
			return configuration{}, err
		}
	}
	var cfg configuration
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&cfg); err != nil {
		return cfg, err
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		return cfg, fmt.Errorf("expected one configuration object")
	}
	return cfg, cfg.validate()
}

func (cfg configuration) validate() error {
	if cfg.Port < 1 || cfg.Port > 65535 {
		return fmt.Errorf("port must be between 1 and 65535")
	}
	regionPattern := regexp.MustCompile(`^[a-z]{2}(?:-[a-z0-9]+)+-[0-9]+$`)
	if !regionPattern.MatchString(cfg.DefaultRegion) {
		return fmt.Errorf("invalid default_region")
	}
	for model, region := range cfg.ModelRegions {
		if model == "" || !regionPattern.MatchString(region) {
			return fmt.Errorf("invalid model_regions entry")
		}
	}
	for region, fallback := range cfg.RegionFallbacks {
		if !regionPattern.MatchString(region) || !regionPattern.MatchString(fallback) || region == fallback {
			return fmt.Errorf("invalid region_fallbacks entry")
		}
	}
	for name, value := range map[string]string{
		"header_timeout":       cfg.HeaderTimeout,
		"stream_idle_timeout":  cfg.StreamIdleTimeout,
		"client_write_timeout": cfg.ClientWriteTimeout,
	} {
		duration, err := time.ParseDuration(value)
		if err != nil || duration <= 0 {
			return fmt.Errorf("%s must be a positive duration", name)
		}
	}
	return nil
}
