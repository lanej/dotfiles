package main

import (
	"bytes"
	"encoding/json"
	"encoding/xml"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"testing"
	"time"

	"github.com/pelletier/go-toml/v2"
)

func TestInstallationStartsServiceAndPreservesConfiguration(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home with spaces")
	root := filepath.Join(home, ".codex")
	dir := filepath.Join(root, "bedrock-router")
	credentials := filepath.Join(home, ".config", "bedrock", "env")
	if err := atomicWrite(credentials, []byte("export AWS_BEARER_TOKEN_BEDROCK=test-only\n"), 0600); err != nil {
		t.Fatal(err)
	}
	original := []byte("# Keep my settings.\nmodel = \"existing-model\"\n[mcp_servers.fixture]\ncommand = \"fixture\"\n")
	if err := atomicWrite(filepath.Join(root, "config.toml"), original, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(dir, 0700); err != nil {
		t.Fatal(err)
	}
	routes, err := openRoutes(filepath.Join(dir, "sessions.sqlite3"))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := routes.db.Exec("INSERT INTO sessions VALUES ('existing-hash', 'us-east-1')"); err != nil {
		t.Fatal(err)
	}
	routes.db.Close()
	cli := os.Getenv("BEDROCK_ROUTER_TEST_BINARY")
	if cli == "" {
		cli = filepath.Join(t.TempDir(), "bedrock-router")
		if output, err := exec.Command("go", "build", "-trimpath", "-o", cli, ".").CombinedOutput(); err != nil {
			t.Fatalf("build installer: %v: %s", err, output)
		}
	}
	cfg, err := loadConfiguration("")
	if err != nil {
		t.Fatal(err)
	}
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	cfg.Port = listener.Addr().(*net.TCPAddr).Port
	listener.Close()
	data, _ := json.Marshal(cfg)
	configPath := filepath.Join(t.TempDir(), "config.json")
	if err := os.WriteFile(configPath, data, 0600); err != nil {
		t.Fatal(err)
	}
	var child *exec.Cmd
	var logs bytes.Buffer
	stop := func() {
		if child != nil {
			_ = child.Process.Signal(syscall.SIGTERM)
			_ = child.Wait()
			child = nil
		}
	}
	t.Cleanup(stop)
	start := func(args []string, cwd string) error {
		stop()
		child = exec.Command(args[0], args[1:]...)
		child.Dir = cwd
		child.Stdout, child.Stderr = &logs, &logs
		if err := child.Start(); err != nil {
			child = nil
			return err
		}
		return nil
	}
	executable := filepath.Join(dir, "bedrock-router")
	env := installEnvironment{home: home, root: root, executable: cli, platform: runtime.GOOS, uid: "test"}
	env.run = func(name string, args ...string) (string, error) {
		if name == "launchctl" {
			switch args[0] {
			case "bootout":
				stop()
			case "bootstrap":
				content, err := os.ReadFile(args[2])
				if err != nil {
					return "", err
				}
				command, cwd, err := launchCommand(content)
				if err != nil {
					return "", err
				}
				if err := start(command, cwd); err != nil {
					return "", err
				}
				return "", errors.New("job was already registered automatically")
			case "print":
				return "program = " + executable + "\n" + filepath.Join(dir, "config.json"), nil
			case "kickstart":
				return "", start([]string{executable, "--config", filepath.Join(dir, "config.json")}, dir)
			}
		} else if name == "systemctl" && args[1] == "restart" {
			content, err := os.ReadFile(filepath.Join(home, ".config", "systemd", "user", "codex-bedrock-router.service"))
			if err != nil {
				return "", err
			}
			fields := make(map[string]string)
			for _, line := range strings.Split(string(content), "\n") {
				if key, value, ok := strings.Cut(line, "="); ok {
					fields[key] = value
				}
			}
			var command []string
			for _, word := range regexp.MustCompile(`"(?:[^"\\]|\\.)*"|\S+`).FindAllString(fields["ExecStart"], -1) {
				if strings.HasPrefix(word, `"`) {
					word, err = strconv.Unquote(word)
					if err != nil {
						return "", err
					}
				}
				command = append(command, strings.ReplaceAll(word, "%%", "%"))
			}
			// systemd 239 treats WorkingDirectory as a literal path.
			return "", start(command, strings.ReplaceAll(fields["WorkingDirectory"], "%%", "%"))
		}
		return "", nil
	}
	// A repeat update must converge while the previous installed binary exists.
	if err := install([]string{"--config", configPath}, env); err != nil {
		stop()
		t.Fatalf("install: %v: %s", err, logs.String())
	}
	if err := install([]string{"--config", configPath}, env); err != nil {
		stop()
		t.Fatalf("repeat install: %v: %s", err, logs.String())
	}
	client := &http.Client{Timeout: 2 * time.Second}
	response, err := client.Get(fmt.Sprintf("http://127.0.0.1:%d/healthz", cfg.Port))
	if err != nil {
		t.Fatal(err)
	}
	var health struct {
		Implementation string `json:"implementation"`
		Pinned         int    `json:"pinned_sessions"`
	}
	err = json.NewDecoder(response.Body).Decode(&health)
	response.Body.Close()
	if err != nil || health.Implementation != "go" || health.Pinned != 1 {
		t.Fatalf("installed service did not preserve pins: %+v, %v", health, err)
	}
	installed, err := os.ReadFile(filepath.Join(root, "config.toml"))
	if err != nil {
		t.Fatal(err)
	}
	var config map[string]any
	if err := toml.Unmarshal(installed, &config); err != nil {
		t.Fatal(err)
	}
	mcp := config["mcp_servers"].(map[string]any)["fixture"].(map[string]any)
	if config["model"] != "existing-model" || mcp["command"] != "fixture" || !bytes.Contains(installed, []byte("# Keep my settings.")) {
		t.Fatal("installation changed existing model, MCP settings, or comments")
	}
	link, err := filepath.EvalSymlinks(filepath.Join(root, ".env"))
	wantLink, wantErr := filepath.EvalSymlinks(credentials)
	if err != nil || wantErr != nil || link != wantLink {
		t.Fatal("private credential link was not preserved")
	}
	// install() ran twice above (a repeat update); the ~/.local/bin symlink
	// must still exist and resolve correctly after that second run, not just
	// error-free on os.Remove + os.Symlink of an already-correct link.
	binLink := filepath.Join(home, ".local", "bin", "bedrock-router")
	binLinkInfo, err := os.Lstat(binLink)
	if err != nil {
		t.Fatal(err)
	}
	if binLinkInfo.Mode()&os.ModeSymlink == 0 {
		t.Fatal("bedrock-router was not installed as a symlink in ~/.local/bin")
	}
	resolvedBinLink, err := filepath.EvalSymlinks(binLink)
	wantBinLink, wantBinLinkErr := filepath.EvalSymlinks(executable)
	if err != nil || wantBinLinkErr != nil || resolvedBinLink != wantBinLink {
		t.Fatalf("bin symlink did not resolve to the installed binary: got %s (err %v), want %s (err %v)", resolvedBinLink, err, wantBinLink, wantBinLinkErr)
	}
}

// TestInstallationFailsFastWhenLaunchdNeverRegistersTheJob reproduces the
// 2026-10-02 outage mode: launchctl bootstrap reports success (does not
// error), but the job never actually appears in launchd — e.g. because
// macOS Background Task Management silently gated the newly-registered
// executable behind a pending Login Items approval. install() must detect
// this via its own post-bootstrap launchd verification and fail fast with a
// specific, actionable error instead of falling through to the generic
// ~10s /healthz timeout.
func TestInstallationFailsFastWhenLaunchdNeverRegistersTheJob(t *testing.T) {
	home := t.TempDir()
	root := filepath.Join(home, ".codex")
	credentials := filepath.Join(home, ".config", "bedrock", "env")
	if err := atomicWrite(credentials, []byte("export AWS_BEARER_TOKEN_BEDROCK=test-only\n"), 0600); err != nil {
		t.Fatal(err)
	}
	executable := filepath.Join(t.TempDir(), "bedrock-router")
	if err := os.WriteFile(executable, []byte("fake binary contents"), 0700); err != nil {
		t.Fatal(err)
	}
	// Use an isolated, never-listening port for this run's config — the
	// embedded default port may collide with a real bedrock-router already
	// running on this machine, which would make the /healthz probe succeed
	// for the wrong reason and mask the launchd-registration failure this
	// test exists to catch.
	cfg, err := loadConfiguration("")
	if err != nil {
		t.Fatal(err)
	}
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	cfg.Port = listener.Addr().(*net.TCPAddr).Port
	listener.Close()
	data, err := json.Marshal(cfg)
	if err != nil {
		t.Fatal(err)
	}
	configPath := filepath.Join(t.TempDir(), "config.json")
	if err := os.WriteFile(configPath, data, 0600); err != nil {
		t.Fatal(err)
	}
	env := installEnvironment{home: home, root: root, executable: executable, platform: "darwin", uid: "test"}
	env.run = func(name string, args ...string) (string, error) {
		if name == "launchctl" {
			switch args[0] {
			case "bootout":
				return "", nil
			case "bootstrap":
				// Reports success without ever actually registering the job.
				return "", nil
			case "print":
				return "", errors.New(`Could not find service "com.joshlane.codex.bedrock-router" in domain for port`)
			}
		}
		return "", nil
	}
	start := time.Now()
	err = install([]string{"--config", configPath}, env)
	elapsed := time.Since(start)
	if err == nil {
		t.Fatal("expected install to fail when launchd never registers the job")
	}
	if !strings.Contains(err.Error(), "did not register") || !strings.Contains(err.Error(), "Login Items") {
		t.Fatalf("expected a specific launchd-registration error, got: %v", err)
	}
	if elapsed >= 10*time.Second {
		t.Fatalf("install took %s; expected the new launchd verification to fail fast instead of falling through to the health check timeout", elapsed)
	}
}

// TestInstallReplacesPreExistingRegularFileAtBinLink confirms the
// ~/.local/bin/bedrock-router symlink step correctly replaces a
// pre-existing REGULAR file at that path (not a stale symlink) — the
// os.Remove + os.Symlink pairing in install() is type-agnostic, but no
// test previously exercised this exact starting shape. Uses --no-start so
// no real launchctl/systemctl calls or /healthz polling are needed: the
// PATH-symlink step in install() runs unconditionally, before the
// noStart-gated service-start block.
func TestInstallReplacesPreExistingRegularFileAtBinLink(t *testing.T) {
	home := t.TempDir()
	root := filepath.Join(home, ".codex")
	credentials := filepath.Join(home, ".config", "bedrock", "env")
	if err := atomicWrite(credentials, []byte("export AWS_BEARER_TOKEN_BEDROCK=test-only\n"), 0600); err != nil {
		t.Fatal(err)
	}
	executable := filepath.Join(t.TempDir(), "bedrock-router")
	if err := os.WriteFile(executable, []byte("fake binary contents"), 0700); err != nil {
		t.Fatal(err)
	}
	cfg, err := loadConfiguration("")
	if err != nil {
		t.Fatal(err)
	}
	data, err := json.Marshal(cfg)
	if err != nil {
		t.Fatal(err)
	}
	configPath := filepath.Join(t.TempDir(), "config.json")
	if err := os.WriteFile(configPath, data, 0600); err != nil {
		t.Fatal(err)
	}

	// Pre-create a REGULAR (non-symlink) file at the install target's
	// ~/.local/bin/bedrock-router path, simulating a user who e.g. manually
	// copied a binary there previously.
	binLink := filepath.Join(home, ".local", "bin", "bedrock-router")
	if err := atomicWrite(binLink, []byte("stale regular file, not a symlink"), 0700); err != nil {
		t.Fatal(err)
	}
	if info, err := os.Lstat(binLink); err != nil || info.Mode()&os.ModeSymlink != 0 {
		t.Fatalf("test setup bug: expected a regular file at %s, got mode %v (err %v)", binLink, info, err)
	}

	env := installEnvironment{home: home, root: root, executable: executable, platform: runtime.GOOS, uid: "test"}
	if err := install([]string{"--config", configPath, "--no-start"}, env); err != nil {
		t.Fatalf("install: %v", err)
	}

	installedExecutable := filepath.Join(root, "bedrock-router", "bedrock-router")
	info, err := os.Lstat(binLink)
	if err != nil {
		t.Fatalf("expected %s to exist after install, got: %v", binLink, err)
	}
	if info.Mode()&os.ModeSymlink == 0 {
		t.Fatalf("expected %s to be replaced with a symlink, still a regular file", binLink)
	}
	resolved, err := filepath.EvalSymlinks(binLink)
	wantResolved, wantErr := filepath.EvalSymlinks(installedExecutable)
	if err != nil || wantErr != nil || resolved != wantResolved {
		t.Fatalf("bin symlink did not resolve to the installed executable: got %s (err %v), want %s (err %v)", resolved, err, wantResolved, wantErr)
	}
}

func launchCommand(data []byte) ([]string, string, error) {
	decoder := xml.NewDecoder(bytes.NewReader(data))
	var key, cwd string
	var args []string
	for {
		token, err := decoder.Token()
		if errors.Is(err, io.EOF) {
			return args, cwd, nil
		}
		if err != nil {
			return nil, "", err
		}
		if start, ok := token.(xml.StartElement); ok {
			switch start.Name.Local {
			case "key":
				if err := decoder.DecodeElement(&key, &start); err != nil {
					return nil, "", err
				}
			case "string":
				var value string
				if err := decoder.DecodeElement(&value, &start); err != nil {
					return nil, "", err
				}
				if key == "WorkingDirectory" {
					cwd = value
				}
			case "array":
				var array struct {
					Values []string `xml:"string"`
				}
				if err := decoder.DecodeElement(&array, &start); err != nil {
					return nil, "", err
				}
				if key == "ProgramArguments" {
					args = array.Values
				}
			}
		}
	}
}
