package main

import (
	"bytes"
	"net"
	"net/http"
	"path/filepath"
	"strings"
	"testing"
)

// fakeStatusEnv builds an installEnvironment whose env.run is faked the same
// way install_test.go fakes launchctl/systemctl calls — no new mocking
// infrastructure, just a different canned response.
func fakeStatusEnv(t *testing.T, platform, runOutput string, runErr error) installEnvironment {
	t.Helper()
	return installEnvironment{
		platform:   platform,
		uid:        "501",
		executable: filepath.Join(t.TempDir(), "bedrock-router"),
		run: func(name string, args ...string) (string, error) {
			return runOutput, runErr
		},
	}
}

func portOf(t *testing.T, url string) string {
	t.Helper()
	port := strings.TrimPrefix(url, "http://127.0.0.1:")
	if port == url {
		t.Fatalf("unexpected server URL shape: %s", url)
	}
	return port
}

func TestStatusReportsLiveHealthAndRunningService(t *testing.T) {
	_, srv, _ := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	// Issue one real request through the fixture router first so
	// completed_requests is provably 1, not 0 — the assertion below is tied
	// to genuinely observed state, not just the HTTP call shape.
	drain(t, call(t, srv.Client(), srv.URL, "openai.gpt-6-astra", "status-check-session", ""), 200)

	// Shape matches real `launchctl print` output observed on this machine:
	// the top-level job state is a single-tab-indented "state = running"
	// (no "job" prefix), while an unrelated nested dict two tabs deep
	// repeats the bare word "state" for something else entirely. The
	// parser must anchor on indentation, not just the field name.
	env := fakeStatusEnv(t, "darwin", "\tpid = 4242\n\tstate = running\n\n\tresource coalition = {\n\t\tstate = active\n\t}\n", nil)

	var out bytes.Buffer
	code, err := statusCmd([]string{"--port", portOf(t, srv.URL)}, env, &out)
	if err != nil {
		t.Fatalf("statusCmd returned error: %v", err)
	}
	if code != 0 {
		t.Fatalf("expected exit code 0 for a healthy router, got %d (output: %s)", code, out.String())
	}
	output := out.String()
	for _, want := range []string{"status: healthy", "completed=1", "uptime", "service: running (pid 4242)"} {
		if !strings.Contains(output, want) {
			t.Fatalf("output missing %q:\n%s", want, output)
		}
	}

	var quietOut bytes.Buffer
	code, err = statusCmd([]string{"--port", portOf(t, srv.URL), "--quiet"}, env, &quietOut)
	if err != nil {
		t.Fatalf("statusCmd (quiet) returned error: %v", err)
	}
	if code != 0 {
		t.Fatalf("expected exit code 0 in quiet mode for a healthy router, got %d", code)
	}
	if quietOut.Len() != 0 {
		t.Fatalf("--quiet must suppress all stdout output, got: %q", quietOut.String())
	}
}

func TestStatusUnreachableRouterNeverHangsOrPanics(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := portOf(t, "http://"+listener.Addr().String())
	listener.Close() // port is now free but dead: nothing answers it

	// Shape matches real `launchctl print` output observed on this machine:
	// the top-level job state is a single-tab-indented "state = running"
	// (no "job" prefix), while an unrelated nested dict two tabs deep
	// repeats the bare word "state" for something else entirely. The
	// parser must anchor on indentation, not just the field name.
	env := fakeStatusEnv(t, "darwin", "\tpid = 4242\n\tstate = running\n\n\tresource coalition = {\n\t\tstate = active\n\t}\n", nil)

	var out bytes.Buffer
	code, err := statusCmd([]string{"--port", port, "-q"}, env, &out)
	if err != nil {
		t.Fatalf("statusCmd returned error for an unreachable router: %v", err)
	}
	if code != 1 {
		t.Fatalf("expected exit code 1 for an unreachable router, got %d", code)
	}
	if out.Len() != 0 {
		t.Fatalf("-q must suppress all stdout output, got: %q", out.String())
	}
}

func TestStatusConsultsBothHealthzAndServiceState(t *testing.T) {
	_, srv, _ := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	// /healthz is healthy, but the service manager reports the job isn't
	// running — overall status must reflect unhealthy, proving both
	// signals are consulted rather than /healthz alone.
	env := fakeStatusEnv(t, "darwin", "\tpid = 0\n\tstate = not running\n", nil)

	var out bytes.Buffer
	code, err := statusCmd([]string{"--port", portOf(t, srv.URL), "--quiet"}, env, &out)
	if err != nil {
		t.Fatalf("statusCmd returned error: %v", err)
	}
	if code != 1 {
		t.Fatalf("expected exit code 1 when the service isn't running even though healthz is ok, got %d", code)
	}

	var verboseOut bytes.Buffer
	if _, err := statusCmd([]string{"--port", portOf(t, srv.URL)}, env, &verboseOut); err != nil {
		t.Fatalf("statusCmd returned error: %v", err)
	}
	if !strings.Contains(verboseOut.String(), "status: unhealthy") {
		t.Fatalf("expected unhealthy status in output, got:\n%s", verboseOut.String())
	}
	if !strings.Contains(verboseOut.String(), "service: not running") {
		t.Fatalf("expected the not-running service state in output, got:\n%s", verboseOut.String())
	}
}

func TestStatusDarwinNotRegistered(t *testing.T) {
	env := fakeStatusEnv(t, "darwin", "", &exitError{})

	status := queryServiceStatus(env)
	if status.state != "not registered with launchd" {
		t.Fatalf("expected 'not registered with launchd', got %q", status.state)
	}
}

// exitError is a minimal error stand-in for launchctl's nonzero exit when a
// job isn't found.
type exitError struct{}

func (*exitError) Error() string { return "exit status 1" }
