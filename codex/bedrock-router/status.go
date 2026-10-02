package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"sort"
	"strings"
	"time"
)

// healthSnapshot mirrors the /healthz JSON shape returned by monitor() in
// router.go. Keep the field tags in sync with that handler.
type healthSnapshot struct {
	Status            string            `json:"status"`
	Implementation    string            `json:"implementation"`
	DefaultRegion     string            `json:"default_region"`
	ModelRegions      map[string]string `json:"model_regions"`
	RegionFallbacks   map[string]string `json:"region_fallbacks"`
	SessionAffinity   bool              `json:"session_affinity"`
	PinnedSessions    int               `json:"pinned_sessions"`
	RequestsByRegion  map[string]uint64 `json:"requests_by_region"`
	ActiveRequests    uint64            `json:"active_requests"`
	ActiveStreams     uint64            `json:"active_streams"`
	CompletedRequests uint64            `json:"completed_requests"`
	ResponseBytes     uint64            `json:"response_bytes"`
	Failures          uint64            `json:"failures"`
	IncompleteStreams uint64            `json:"incomplete_streams"`
	CanceledRequests  uint64            `json:"canceled_requests"`
	UptimeSeconds     float64           `json:"uptime_seconds"`
}

// serviceStatus describes what the OS service manager reports about the
// installed background service, independent of whether it's answering
// HTTP requests.
type serviceStatus struct {
	state string // e.g. "running"/"active", "not running"/"inactive", "not registered with launchd", "unsupported platform"
	pid   string // empty when not available
}

func (s serviceStatus) running() bool {
	switch s.state {
	case "running", "active":
		return true
	default:
		return false
	}
}

func (s serviceStatus) String() string {
	switch {
	case s.state == "":
		return "unknown"
	case s.pid != "":
		return fmt.Sprintf("%s (pid %s)", s.state, s.pid)
	default:
		return s.state
	}
}

// launchdJobStatePattern anchors on a line indented by exactly one tab, not
// on the field name alone: observed `launchctl print` output on this
// machine (Darwin 25.6.0) names the top-level job state field just "state ="
// (no "job" prefix), while nested dicts (e.g. "resource coalition",
// "jetsam coalition") repeat an unrelated "state = active" two tabs deep.
// Matching "(?:job )?state" keeps compatibility with any launchctl version
// that does print the "job state" wording, while the single leading tab
// excludes every deeper, irrelevant occurrence.
var (
	launchdJobStatePattern = regexp.MustCompile(`(?m)^\t(?:job )?state = (.+)$`)
	launchdPIDPattern      = regexp.MustCompile(`(?m)^\tpid = (\d+)$`)
)

// queryServiceStatus asks the OS service manager about the installed
// background service via env.run — the same injectable function install.go
// and install_test.go already use, so this is testable with no new mocking.
func queryServiceStatus(env installEnvironment) serviceStatus {
	switch env.platform {
	case "darwin":
		target := "gui/" + env.uid + "/" + launchdLabel
		output, _ := env.run("launchctl", "print", target)
		// launchctl exits non-zero when the job isn't found, but the output
		// may still carry useful text — ignore the error and parse the text.
		match := launchdJobStatePattern.FindStringSubmatch(output)
		if match == nil {
			return serviceStatus{state: "not registered with launchd"}
		}
		status := serviceStatus{state: strings.TrimSpace(match[1])}
		if pid := launchdPIDPattern.FindStringSubmatch(output); pid != nil && strings.TrimSpace(pid[1]) != "0" {
			status.pid = pid[1]
		}
		return status
	case "linux":
		active, _ := env.run("systemctl", "--user", "is-active", systemdUnitName)
		status := serviceStatus{state: strings.TrimSpace(active)}
		if pid, _ := env.run("systemctl", "--user", "show", systemdUnitName, "--property=MainPID", "--value"); strings.TrimSpace(pid) != "0" {
			status.pid = strings.TrimSpace(pid)
		}
		return status
	default:
		return serviceStatus{state: "unsupported platform"}
	}
}

// fetchHealth queries the router's /healthz endpoint. A transport error,
// non-200 response, or decode failure is a normal "router is unreachable"
// outcome, not a program bug — the caller reflects it in the exit code and
// formatted output rather than treating it as fatal.
func fetchHealth(baseURL string) (*healthSnapshot, error) {
	client := &http.Client{Timeout: 2 * time.Second}
	response, err := client.Get(baseURL + "/healthz")
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status %d", response.StatusCode)
	}
	var snapshot healthSnapshot
	if err := json.NewDecoder(io.LimitReader(response.Body, 1<<20)).Decode(&snapshot); err != nil {
		return nil, err
	}
	return &snapshot, nil
}

// formatStatus is pure formatting logic — no I/O — so it's unit-testable
// without any HTTP or exec involved.
func formatStatus(health *healthSnapshot, healthErr error, service serviceStatus) string {
	var b strings.Builder
	healthy := healthErr == nil && health != nil && health.Status == "ok"
	overall := "unhealthy"
	if healthy && service.running() {
		overall = "healthy"
	}
	fmt.Fprintf(&b, "status: %s\n", overall)
	if !healthy {
		if healthErr != nil {
			fmt.Fprintf(&b, "healthz: unreachable (%v)\n", healthErr)
		} else {
			fmt.Fprintln(&b, "healthz: unreachable")
		}
	} else {
		fmt.Fprintf(&b, "healthz: %s (uptime %.1fs)\n", health.Status, health.UptimeSeconds)
		fmt.Fprintf(&b, "requests: active=%d completed=%d failures=%d canceled=%d incomplete_streams=%d\n",
			health.ActiveRequests, health.CompletedRequests, health.Failures, health.CanceledRequests, health.IncompleteStreams)
		fmt.Fprintf(&b, "pinned_sessions: %d\n", health.PinnedSessions)
		if len(health.RequestsByRegion) > 0 {
			regions := make([]string, 0, len(health.RequestsByRegion))
			for region := range health.RequestsByRegion {
				regions = append(regions, region)
			}
			sort.Strings(regions)
			fmt.Fprint(&b, "requests_by_region:")
			for _, region := range regions {
				fmt.Fprintf(&b, " %s=%d", region, health.RequestsByRegion[region])
			}
			fmt.Fprintln(&b)
		}
	}
	fmt.Fprintf(&b, "service: %s\n", service.String())
	return b.String()
}

// statusCmd implements `bedrock-router status`. A non-nil error return is
// reserved for genuine usage/configuration problems that prevent the check
// from running at all (bad flags, unreadable config) — an unhealthy or
// unreachable router is a normal outcome, reported via the int exit code.
func statusCmd(args []string, env installEnvironment, stdout io.Writer) (int, error) {
	flags := flag.NewFlagSet("status", flag.ContinueOnError)
	configPath := flags.String("config", "", "Configuration file (default: config.json beside the binary, then embedded defaults)")
	port := flags.Int("port", 0, "Override the configured loopback port")
	var quiet bool
	flags.BoolVar(&quiet, "quiet", false, "Suppress output; only set the exit code")
	flags.BoolVar(&quiet, "q", false, "Suppress output; only set the exit code")
	if err := flags.Parse(args); err != nil {
		return 1, err
	}
	if flags.NArg() != 0 {
		return 1, fmt.Errorf("unexpected status arguments")
	}
	var portSet bool
	flags.Visit(func(f *flag.Flag) {
		if f.Name == "port" {
			portSet = true
		}
	})
	if portSet && *port == 0 {
		return 1, fmt.Errorf("--port 0 is not a valid port")
	}
	path := effectiveConfigPath(*configPath, env.executable)
	cfg, err := loadConfiguration(path)
	if err != nil {
		return 1, fmt.Errorf("invalid router configuration: %w", err)
	}
	if portSet {
		cfg.Port = *port
	}
	health, healthErr := fetchHealth(fmt.Sprintf("http://127.0.0.1:%d", cfg.Port))
	service := queryServiceStatus(env)
	if !quiet {
		fmt.Fprint(stdout, formatStatus(health, healthErr, service))
	}
	if healthErr == nil && health != nil && health.Status == "ok" && service.running() {
		return 0, nil
	}
	return 1, nil
}
