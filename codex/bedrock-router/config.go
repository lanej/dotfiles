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
	source := "embedded config.json"

	if path != "" {
		source = path
		var err error

		data, err = os.ReadFile(path)
		if err != nil {
			return configuration{}, fmt.Errorf("read router configuration: %w", err)
		}
	}

	var cfg configuration
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()

	if err := decoder.Decode(&cfg); err != nil {
		return cfg, fmt.Errorf("decode router configuration %q: %w", source, err)
	}

	if err := decoder.Decode(new(any)); err != io.EOF {
		if err != nil {
			return cfg, fmt.Errorf("read trailing data in router configuration %q: %w", source, err)
		}

		return cfg, fmt.Errorf("router configuration %q: expected one configuration object", source)
	}

	if err := cfg.validate(); err != nil {
		return cfg, fmt.Errorf("router configuration %q: %w", source, err)
	}

	return cfg, nil
}

func (cfg configuration) validate() error {
	if cfg.Port < 1 || cfg.Port > 65535 {
		return fmt.Errorf("port %d must be between 1 and 65535", cfg.Port)
	}

	regionPattern := regexp.MustCompile(`^[a-z]{2}(?:-[a-z0-9]+)+-[0-9]+$`)

	if !regionPattern.MatchString(cfg.DefaultRegion) {
		return fmt.Errorf("invalid default_region %q: expected an AWS region such as us-east-1", cfg.DefaultRegion)
	}

	for model, region := range cfg.ModelRegions {
		if model == "" || !regionPattern.MatchString(region) {
			return fmt.Errorf("invalid model_regions entry %q = %q: model must be nonempty and region must be an AWS region", model, region)
		}
	}

	for region, fallback := range cfg.RegionFallbacks {
		if !regionPattern.MatchString(region) || !regionPattern.MatchString(fallback) || region == fallback {
			return fmt.Errorf("invalid region_fallbacks entry %q = %q: expected distinct AWS regions", region, fallback)
		}
	}

	for name, value := range map[string]string{
		"header_timeout":       cfg.HeaderTimeout,
		"stream_idle_timeout":  cfg.StreamIdleTimeout,
		"client_write_timeout": cfg.ClientWriteTimeout,
	} {
		duration, err := time.ParseDuration(value)
		if err != nil {
			return fmt.Errorf("%s %q must be a positive duration: %w", name, value, err)
		}

		if duration <= 0 {
			return fmt.Errorf("%s %q must be a positive duration", name, value)
		}
	}

	return nil
}
