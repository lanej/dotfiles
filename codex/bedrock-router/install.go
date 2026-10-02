package main

import (
	"bytes"
	"encoding/json"
	"encoding/xml"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"time"

	"github.com/pelletier/go-toml/v2"
)

// launchdLabel and systemdUnitName name the installed background service on
// each platform. Shared between install.go (which registers the service)
// and status.go (which queries it) so the two never drift apart.
const (
	launchdLabel    = "com.joshlane.codex.bedrock-router"
	systemdUnitName = "codex-bedrock-router.service"
)

type installEnvironment struct {
	home, root, executable, platform, uid string
	run                                   func(string, ...string) (string, error)
}

func currentInstallEnvironment() (installEnvironment, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return installEnvironment{}, err
	}

	executable, err := os.Executable()
	if err != nil {
		return installEnvironment{}, err
	}

	root := os.Getenv("CODEX_HOME")

	if root == "" {
		root = filepath.Join(home, ".codex")
	}

	return installEnvironment{
		home: home, root: root, executable: executable,
		platform: runtime.GOOS, uid: strconv.Itoa(os.Getuid()),
		run: func(name string, args ...string) (string, error) {
			output, err := exec.Command(name, args...).CombinedOutput()
			if err != nil {
				return string(output), fmt.Errorf("%s failed: %w: %s", name, err, strings.TrimSpace(string(output)))
			}

			return string(output), nil
		},
	}, nil
}

func atomicWrite(path string, data []byte, mode os.FileMode) error {
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return err
	}

	file, err := os.CreateTemp(filepath.Dir(path), ".bedrock-router-*")
	if err != nil {
		return err
	}

	defer os.Remove(file.Name())

	if err = file.Chmod(mode); err == nil {
		_, err = file.Write(data)
	}

	if err == nil {
		err = file.Sync()
	}

	closeErr := file.Close()

	if err != nil {
		return err
	}

	if closeErr != nil {
		return closeErr
	}

	return os.Rename(file.Name(), path)
}

func updateCodexConfig(text string, cfg configuration) (string, error) {
	var previous map[string]any

	if err := toml.Unmarshal([]byte(text), &previous); err != nil {
		return "", errors.New("existing Codex config is not valid TOML")
	}

	providers, _ := previous["model_providers"].(map[string]any)
	provider, _ := providers["amazon-bedrock"].(map[string]any)
	aws, _ := provider["aws"].(map[string]any)
	for key := range provider {
		if key != "base_url" && key != "aws" {
			return "", errors.New("existing Bedrock provider has additional settings; merge them manually")
		}
	}

	for key := range aws {
		if key != "region" {
			return "", errors.New("existing Bedrock AWS settings require a manual merge")
		}
	}

	index := len(text)

	if match := regexp.MustCompile(`(?m)^[\t ]*\[`).FindStringIndex(text); match != nil {
		index = match[0]
	}

	top, tables := text[:index], text[index:]
	for _, setting := range []struct{ key, value string }{
		{"model_provider", "amazon-bedrock"},
		{"model_reasoning_summary", "none"},
		{"web_search", "cached"},
	} {
		line := setting.key + " = " + strconv.Quote(setting.value)
		pattern := regexp.MustCompile(`(?m)^[\t ]*` + setting.key + `[\t ]*=.*$`)

		if pattern.MatchString(top) {
			top = pattern.ReplaceAllString(top, line)
		} else {
			top = strings.TrimRight(top, "\n \t") + "\n" + line + "\n"
		}
	}

	if _, exists := previous["model"]; !exists {
		top += "model = \"openai.gpt-6.1-sol\"\n"
	}

	var preserved strings.Builder
	skip := false
	for _, line := range strings.SplitAfter(tables, "\n") {
		header := strings.TrimSpace(strings.SplitN(line, "#", 2)[0])

		if strings.HasPrefix(header, "[") {
			skip = header == "[model_providers.amazon-bedrock]" || header == "[model_providers.amazon-bedrock.aws]"
		}

		if !skip {
			preserved.WriteString(line)
		}
	}

	updated := strings.TrimSpace(top) + "\n\n" + strings.TrimSpace(preserved.String()) +
		"\n\n[model_providers.amazon-bedrock]\nbase_url = " +
		strconv.Quote(fmt.Sprintf("http://127.0.0.1:%d/openai/v1", cfg.Port)) +
		"\n\n[model_providers.amazon-bedrock.aws]\nregion = " + strconv.Quote(cfg.DefaultRegion) + "\n"
	var check map[string]any

	if err := toml.Unmarshal([]byte(updated), &check); err != nil {
		return "", errors.New("Codex configuration requires a manual merge")
	}

	return updated, nil
}

func launchAgent(executable, dir string) []byte {
	var out bytes.Buffer
	out.WriteString(`<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>`)
	stringValue := func(value string) {
		out.WriteString("<string>")
		_ = xml.EscapeText(&out, []byte(value))
		out.WriteString("</string>")
	}
	for _, entry := range []struct{ key, value string }{
		{"Label", launchdLabel},
		{"WorkingDirectory", dir},
		{"ProcessType", "Background"},
		{"StandardOutPath", filepath.Join(dir, "router.log")},
		{"StandardErrorPath", filepath.Join(dir, "router.err.log")},
	} {
		fmt.Fprintf(&out, "<key>%s</key>", entry.key)
		stringValue(entry.value)
	}

	out.WriteString("<key>ProgramArguments</key><array>")
	for _, arg := range []string{executable, "--config", filepath.Join(dir, "config.json")} {
		stringValue(arg)
	}

	out.WriteString("</array><key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>5</integer></dict></plist>\n")
	return out.Bytes()
}

func systemdUnit(executable, dir string) []byte {
	escape := func(value string) string { return strings.ReplaceAll(value, "%", "%%") }
	var caLine string
	for _, ca := range []string{"/etc/pki/tls/certs/ca-bundle.crt", "/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/cert.pem"} {
		if _, err := os.Stat(ca); err == nil {
			caLine = "Environment=SSL_CERT_FILE=" + ca + "\n"
			break
		}
	}

	return []byte("[Unit]\nDescription=Codex Bedrock routing by model\n\n[Service]\n" + caLine +
		"ExecStart=" + strconv.Quote(escape(executable)) + " --config " + strconv.Quote(escape(filepath.Join(dir, "config.json"))) + "\n" +
		// systemd 239 treats quotes here as literal path characters.
		"WorkingDirectory=" + escape(dir) + "\n" +
		"Restart=always\nRestartSec=3\nUMask=0077\nNoNewPrivileges=yes\nPrivateTmp=yes\n\n[Install]\nWantedBy=default.target\n")
}

// pollLaunchctlPrint repeatedly runs `launchctl print <target>`, calling
// until with each attempt's output and error, up to attempts times with
// interval between tries. It returns true as soon as until reports a match,
// or false once the attempt budget is exhausted.
func pollLaunchctlPrint(env installEnvironment, target string, attempts int, interval time.Duration, until func(output string, err error) bool) bool {
	for attempt := 0; attempt < attempts; attempt++ {
		output, err := env.run("launchctl", "print", target)

		if until(output, err) {
			return true
		}

		if attempt < attempts-1 {
			time.Sleep(interval)
		}
	}

	return false
}

func install(args []string, env installEnvironment) error {
	flags := flag.NewFlagSet("install", flag.ContinueOnError)
	noStart := flags.Bool("no-start", false, "Write files without starting the service")
	configPath := flags.String("config", "", "Configuration file; defaults are embedded in this binary")

	if err := flags.Parse(args); err != nil {
		return err
	}

	if flags.NArg() != 0 {
		return errors.New("unexpected install arguments")
	}

	if env.platform != "darwin" && env.platform != "linux" {
		return errors.New("installation supports macOS and Linux")
	}

	cfg, err := loadConfiguration(*configPath)
	if err != nil {
		return errors.New("invalid router configuration")
	}

	credentials := filepath.Join(env.home, ".config", "bedrock", "env")
	info, err := os.Stat(credentials)

	if err != nil || !info.Mode().IsRegular() {
		return errors.New("set up your private ~/.config/bedrock/env first")
	}

	if info.Mode().Perm()&0077 != 0 {
		return errors.New("credentials must have permissions 600")
	}

	link := filepath.Join(env.root, ".env")

	if _, err := os.Lstat(link); err == nil {
		destination, linkErr := filepath.EvalSymlinks(link)
		source, sourceErr := filepath.EvalSymlinks(credentials)

		if linkErr != nil || sourceErr != nil || destination != source {
			return errors.New("existing Codex .env uses another source; merge it manually")
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return err
	}

	config := filepath.Join(env.root, "config.toml")
	old, err := os.ReadFile(config)

	if err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}

	updated, err := updateCodexConfig(string(old), cfg)
	if err != nil {
		return err
	}

	binary, err := os.ReadFile(env.executable)
	if err != nil {
		return err
	}

	dir := filepath.Join(env.root, "bedrock-router")
	executable := filepath.Join(dir, "bedrock-router")
	backup := filepath.Join(env.root, "backups", "bedrock-router-"+time.Now().UTC().Format("20060102T150405.000000000Z"), "config.toml")

	if old != nil {
		if err := atomicWrite(backup, old, 0600); err != nil {
			return err
		}
	}

	settings, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}

	for _, file := range []struct {
		path string
		data []byte
		mode os.FileMode
	}{
		{executable, binary, 0700},
		{filepath.Join(dir, "config.json"), append(settings, '\n'), 0600},
		{config, []byte(updated), 0600},
	} {
		if err := atomicWrite(file.path, file.data, file.mode); err != nil {
			return err
		}
	}

	if _, err := os.Lstat(link); errors.Is(err, os.ErrNotExist) {
		if err := os.Symlink(credentials, link); err != nil {
			return err
		}
	}

	if env.platform == "darwin" {
		label := launchdLabel
		service := filepath.Join(env.home, "Library", "LaunchAgents", label+".plist")

		if err := atomicWrite(service, launchAgent(executable, dir), 0600); err != nil {
			return err
		}

		if !*noStart {
			domain := "gui/" + env.uid
			target := domain + "/" + label
			_, _ = env.run("launchctl", "bootout", target)
			// Give a torn-down job a chance to actually clear before
			// re-registering it: bootstrap can otherwise race an in-flight
			// unload. If nothing needed unloading (the common case), print
			// errors immediately and this proceeds without delay.
			pollLaunchctlPrint(env, target, 20, 100*time.Millisecond, func(_ string, err error) bool {
				return err != nil
			})

			_, bootstrapErr := env.run("launchctl", "bootstrap", domain, service)
			if bootstrapErr != nil {
				job, lookupErr := env.run("launchctl", "print", target)

				if lookupErr != nil || !strings.Contains(job, "program = "+executable) || !strings.Contains(job, filepath.Join(dir, "config.json")) {
					return bootstrapErr
				}

				if _, err := env.run("launchctl", "kickstart", "-k", target); err != nil {
					return err
				}
			}

			// A successful bootstrap/kickstart doesn't guarantee the job
			// actually registered with launchd — e.g. macOS Background Task
			// Management can silently gate it behind a pending Login Items
			// approval. Verify before falling through to the generic
			// /healthz poll, which otherwise can't distinguish this from a
			// slow start or port conflict.
			registered := pollLaunchctlPrint(env, target, 10, 200*time.Millisecond, func(output string, err error) bool {
				return err == nil && strings.Contains(output, "program = "+executable) && strings.Contains(output, filepath.Join(dir, "config.json"))
			})

			if !registered {
				return fmt.Errorf("bedrock-router did not register with launchd after bootstrap — check System Settings > General > Login Items & Extensions for a pending 'bedrock-router' approval, then retry install")
			}
		}
	} else {
		service := filepath.Join(env.home, ".config", "systemd", "user", systemdUnitName)

		if err := atomicWrite(service, systemdUnit(executable, dir), 0600); err != nil {
			return err
		}

		if !*noStart {
			for _, args := range [][]string{
				{"--user", "daemon-reload"},
				{"--user", "enable", systemdUnitName},
				{"--user", "restart", systemdUnitName},
			} {
				if _, err := env.run("systemctl", args...); err != nil {
					return err
				}
			}
		}
	}

	// Put the installed binary on PATH, mirroring this repo's own Makefile
	// convention (`ln -fs $(DOTFILES)/bin/* $(HOME)/.local/bin/`) so
	// `bedrock-router status`/`logs` work from any shell without the full
	// ~/.codex/bedrock-router path.
	binDir := filepath.Join(env.home, ".local", "bin")

	if err := os.MkdirAll(binDir, 0700); err != nil {
		return err
	}

	binLink := filepath.Join(binDir, "bedrock-router")

	if err := os.Remove(binLink); err != nil && !os.IsNotExist(err) {
		return err
	}

	if err := os.Symlink(executable, binLink); err != nil {
		return err
	}

	if !*noStart {
		client := &http.Client{Timeout: 2 * time.Second}
		healthy := false
		for attempt := 0; attempt < 40; attempt++ {
			response, err := client.Get(fmt.Sprintf("http://127.0.0.1:%d/healthz", cfg.Port))
			if err == nil {
				var health struct {
					Implementation string            `json:"implementation"`
					DefaultRegion  string            `json:"default_region"`
					ModelRegions   map[string]string `json:"model_regions"`
				}
				err = json.NewDecoder(io.LimitReader(response.Body, 1<<20)).Decode(&health)
				response.Body.Close()

				if err == nil && response.StatusCode == 200 && health.Implementation == "go" && health.DefaultRegion == cfg.DefaultRegion && reflect.DeepEqual(health.ModelRegions, cfg.ModelRegions) {
					healthy = true
					break
				}
			}

			time.Sleep(250 * time.Millisecond)
		}

		if !healthy {
			return errors.New("installed router failed its health check")
		}
	}

	fmt.Printf("Installed Bedrock router. Original Codex config: %s\n", backup)
	return nil
}
