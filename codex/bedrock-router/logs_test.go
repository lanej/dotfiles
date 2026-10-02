package main

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"testing"
)

// TestLogCommand covers logCommand's pure argv-building logic: no real OS
// binary is invoked here, only assertions on the returned name/args/err.
func TestLogCommand(t *testing.T) {
	home := filepath.Join("home", "u")
	cases := []struct {
		name       string
		platform   string
		lines      int
		follow     bool
		stderrFlag bool
		wantCmd    string
		wantArgs   []string
		wantErr    string
	}{
		{
			name:     "darwin stdout",
			platform: "darwin",
			lines:    10,
			wantCmd:  "tail",
			wantArgs: []string{"-n", "10", filepath.Join(home, ".codex", "bedrock-router", "router.log")},
		},
		{
			name:       "darwin stderr",
			platform:   "darwin",
			lines:      10,
			stderrFlag: true,
			wantCmd:    "tail",
			wantArgs:   []string{"-n", "10", filepath.Join(home, ".codex", "bedrock-router", "router.err.log")},
		},
		{
			// BSD tail parses flags positionally: a trailing -f after the
			// file path is treated as a second (nonexistent) file, not a
			// flag. -f must come before the path.
			name:     "darwin follow puts -f before the path",
			platform: "darwin",
			lines:    10,
			follow:   true,
			wantCmd:  "tail",
			wantArgs: []string{"-n", "10", "-f", filepath.Join(home, ".codex", "bedrock-router", "router.log")},
		},
		{
			name:     "linux follow",
			platform: "linux",
			lines:    10,
			follow:   true,
			wantCmd:  "journalctl",
			wantArgs: []string{"--user", "-u", systemdUnitName, "-n", "10", "-f"},
		},
		{
			name:       "linux stderr is unsupported",
			platform:   "linux",
			lines:      10,
			stderrFlag: true,
			wantErr:    "--stderr is only meaningful on macOS",
		},
		{
			name:     "unsupported platform",
			platform: "windows",
			lines:    10,
			wantErr:  "logs supports macOS and Linux",
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			gotCmd, gotArgs, err := logCommand(c.platform, home, c.lines, c.follow, c.stderrFlag)
			if c.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), c.wantErr) {
					t.Fatalf("expected error containing %q, got %v", c.wantErr, err)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if gotCmd != c.wantCmd {
				t.Fatalf("expected command %q, got %q", c.wantCmd, gotCmd)
			}
			if !reflect.DeepEqual(gotArgs, c.wantArgs) {
				t.Fatalf("expected args %v, got %v", c.wantArgs, gotArgs)
			}
		})
	}
}

// TestLogsCmdTailsRealFile is the one test that actually shells out to a
// real `tail` binary against a fixture log file, proving path construction
// and the -n argument are wired correctly end to end.
func TestLogsCmdTailsRealFile(t *testing.T) {
	if _, err := exec.LookPath("tail"); err != nil {
		t.Skip("tail not available on this system; skipping real end-to-end tail test")
	}
	home := t.TempDir()
	logDir := filepath.Join(home, ".codex", "bedrock-router")
	if err := os.MkdirAll(logDir, 0700); err != nil {
		t.Fatal(err)
	}
	var lines []string
	for i := 1; i <= 20; i++ {
		lines = append(lines, "line "+strconv.Itoa(i))
	}
	content := strings.Join(lines, "\n") + "\n"
	if err := os.WriteFile(filepath.Join(logDir, "router.log"), []byte(content), 0600); err != nil {
		t.Fatal(err)
	}

	env := installEnvironment{platform: "darwin", home: home}
	var out bytes.Buffer
	if err := logsCmd([]string{"--lines", "3"}, env, &out); err != nil {
		t.Fatalf("logsCmd returned error: %v", err)
	}

	got := strings.Split(strings.TrimRight(out.String(), "\n"), "\n")
	want := []string{"line 18", "line 19", "line 20"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("expected exactly the last 3 lines %v, got %v", want, got)
	}
}

// TestLogsCmdMissingLogFile confirms a missing log file produces a clear,
// interpreted error rather than letting a raw `tail` failure (or a hang)
// leak through.
func TestLogsCmdMissingLogFile(t *testing.T) {
	home := t.TempDir() // no .codex/bedrock-router/router.log created
	env := installEnvironment{platform: "darwin", home: home}
	var out bytes.Buffer
	err := logsCmd(nil, env, &out)
	if err == nil {
		t.Fatalf("expected an error when the log file doesn't exist, got none (output: %q)", out.String())
	}
	if !strings.Contains(err.Error(), "no log file at") {
		t.Fatalf("expected a clear missing-log-file error, got: %v", err)
	}
}

// No test covers --follow actually following (streaming newly appended
// lines): verifying "it kept streaming" needs real concurrency/timing
// control that's disproportionate to the risk for a thin passthrough to
// `tail -f`/`journalctl -f`. The argv-building cases above already prove
// the -f flag is included when requested.
