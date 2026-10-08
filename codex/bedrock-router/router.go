package main

import (
	"bytes"
	"compress/gzip"
	"context"
	"crypto/sha256"
	"crypto/tls"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	_ "modernc.org/sqlite"
)

const maxBodyBytes = 128 << 20

type sessionGate struct {
	token chan struct{}
	users int
}

type routes struct {
	db    *sql.DB
	mu    sync.Mutex
	gates map[string]*sessionGate
}

func openRoutes(path string) (*routes, error) {
	if path != ":memory:" {
		f, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0600)
		if err != nil {
			return nil, err
		}

		if err = f.Chmod(0600); err != nil {
			f.Close()
			return nil, err
		}

		f.Close()
	}

	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}

	db.SetMaxOpenConns(1)
	for _, stmt := range []string{
		"PRAGMA busy_timeout=5000",
		"PRAGMA journal_mode=WAL",
		"CREATE TABLE IF NOT EXISTS sessions (session_hash TEXT PRIMARY KEY, region TEXT NOT NULL)",
	} {
		if _, err = db.Exec(stmt); err != nil {
			db.Close()
			return nil, err
		}
	}

	return &routes{db: db, gates: make(map[string]*sessionGate)}, nil
}

func (s *routes) lookup(ctx context.Context, key string) (string, error) {
	var region string
	err := s.db.QueryRowContext(ctx, "SELECT region FROM sessions WHERE session_hash = ?", key).Scan(&region)

	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}

	return region, err
}

// Only region discovery holds gates. Existing sessions bypass them entirely.
// References include waiters, so gates can be removed without splitting a lock.
func (s *routes) acquire(ctx context.Context, keys []string) (func(), error) {
	keys = append([]string(nil), keys...)
	sort.Strings(keys)
	var held []*sessionGate
	var referenced []*sessionGate
	release := sync.OnceFunc(func() {
		for _, g := range held {
			g.token <- struct{}{}
		}

		s.mu.Lock()
		defer s.mu.Unlock()
		for i, g := range referenced {
			g.users--

			if g.users == 0 {
				delete(s.gates, keys[i])
			}
		}
	})
	for _, key := range keys {
		s.mu.Lock()
		g := s.gates[key]

		if g == nil {
			g = &sessionGate{token: make(chan struct{}, 1)}
			g.token <- struct{}{}
			s.gates[key] = g
		}

		g.users++
		referenced = append(referenced, g)
		s.mu.Unlock()
		select {
		case <-g.token:
			held = append(held, g)
		case <-ctx.Done():
			release()
			return nil, ctx.Err()
		}
	}

	return release, nil
}

func sessionKeys(h http.Header) []string {
	var metadata map[string]any
	_ = json.Unmarshal([]byte(h.Get("X-Codex-Turn-Metadata")), &metadata)
	value := func(names ...string) string {
		for _, name := range names {
			if v, ok := metadata[name].(string); ok && v != "" {
				return v
			}
		}

		return ""
	}
	first := func(values ...string) string {
		for _, v := range values {
			if v != "" {
				return v
			}
		}

		return ""
	}
	session := first(h.Get("Thread-Id"), value("thread_id", "session_id"), h.Get("Session-Id"))
	parent := first(h.Get("X-Codex-Parent-Thread-Id"), value("parent_thread_id", "forked_from_thread_id"))
	var keys []string
	for _, id := range []string{session, parent} {
		if id != "" {
			hash := sha256.Sum256([]byte(id))
			key := hex.EncodeToString(hash[:])

			if len(keys) == 0 || keys[0] != key {
				keys = append(keys, key)
			}
		}
	}

	return keys
}

type measurements struct {
	sync.Mutex
	Active, Streams, Requests, Bytes, Failures, Incomplete, Canceled, Retries uint64
	Regions                                                                   map[string]uint64
	Statuses                                                                  map[int]uint64
	Duration                                                                  time.Duration
}

type router struct {
	config    configuration
	routes    *routes
	transport http.RoundTripper
	endpoint  func(string) string
	log       *slog.Logger
	stats     measurements
	sequence  atomic.Uint64
	started   time.Time
	writeIdle time.Duration
	recovery  webRecovery
}

func newRouter(state string, transport http.RoundTripper, log *slog.Logger, cfg configuration) (*router, error) {
	if err := cfg.validate(); err != nil {
		return nil, err
	}

	s, err := openRoutes(state)
	if err != nil {
		return nil, err
	}

	writeIdle, _ := time.ParseDuration(cfg.ClientWriteTimeout)
	return &router{
		config: cfg,
		routes: s, transport: transport, log: log, started: time.Now(),
		writeIdle: writeIdle,
		endpoint:  func(region string) string { return "https://bedrock-mantle." + region + ".api.aws" },
		stats:     measurements{Regions: make(map[string]uint64), Statuses: make(map[int]uint64)},
	}, nil
}

func sendError(w http.ResponseWriter, status int, code, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{"error": map[string]string{"code": code, "message": message}})
}

func stripHopHeaders(h http.Header) {
	for _, field := range strings.Split(h.Get("Connection"), ",") {
		h.Del(strings.TrimSpace(field))
	}

	for _, field := range []string{"Connection", "Keep-Alive", "Proxy-Authenticate", "Proxy-Authorization", "Te", "Trailer", "Transfer-Encoding", "Upgrade"} {
		h.Del(field)
	}
}

func requestModel(body []byte, encoding string) (string, error) {
	var reader io.Reader = bytes.NewReader(body)
	switch strings.ToLower(encoding) {
	case "", "identity":
	case "gzip":
		gz, err := gzip.NewReader(reader)
		if err != nil {
			return "", fmt.Errorf("decode gzip request body: %w", err)
		}

		defer gz.Close()
		reader = gz
	default:
		return "", fmt.Errorf("unsupported Content-Encoding %q; use identity or gzip", encoding)
	}

	data, err := io.ReadAll(io.LimitReader(reader, maxBodyBytes+1))
	if err != nil {
		return "", fmt.Errorf("read decoded request body: %w", err)
	}

	if len(data) > maxBodyBytes {
		return "", fmt.Errorf("decoded request body exceeds %d bytes", maxBodyBytes)
	}

	if len(data) == 0 {
		return "", nil
	}

	var object map[string]json.RawMessage

	if err = json.Unmarshal(data, &object); err != nil {
		return "", fmt.Errorf("expected a JSON request object: %w", err)
	}

	if object == nil {
		return "", errors.New("expected a JSON request object, got null")
	}

	var model string

	if raw := object["model"]; raw != nil {
		if err = json.Unmarshal(raw, &model); err != nil {
			return "", fmt.Errorf("model must be a JSON string: %w", err)
		}
	}

	return model, nil
}

func errorKind(err error, ctx context.Context) string {
	if ctx.Err() != nil {
		return "client_canceled"
	}

	var ne net.Error

	if errors.As(err, &ne) && ne.Timeout() {
		return "timeout"
	}

	var dns *net.DNSError

	if errors.As(err, &dns) {
		return "dns_error"
	}

	var cert *tls.CertificateVerificationError

	if errors.As(err, &cert) {
		return "tls_verification_error"
	}

	if errors.Is(err, syscall.ECONNREFUSED) {
		return "connection_refused"
	}

	if errors.Is(err, syscall.ECONNRESET) {
		return "connection_reset"
	}

	if errors.Is(err, io.ErrUnexpectedEOF) {
		return "unexpected_eof"
	}

	if errors.Is(err, io.EOF) {
		return "upstream_closed"
	}

	return "connection_error"
}

func safeModel(model string) string {
	if len(model) > 128 || strings.ContainsAny(model, "\r\n\t ") {
		return "other"
	}

	return model
}

// Collection actions route by model; stored response operations require the
// originating session's region. Response IDs are opaque, not region hints.
func responseResource(path string) bool {
	const prefix = "/openai/v1/responses/"

	if !strings.HasPrefix(path, prefix) {
		return false
	}

	action := strings.TrimPrefix(path, prefix)
	return action != "" && action != "compact" && action != "input_tokens"
}

func (r *router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	if req.Method == http.MethodGet && (req.URL.Path == "/healthz" || req.URL.Path == "/metrics") {
		r.monitor(w, req)
		return
	}

	start := time.Now()
	id := fmt.Sprintf("%x-%x", r.started.UnixNano(), r.sequence.Add(1))
	log := r.log.With("request_id", id, "method", req.Method)
	status, outcome, region, model := 0, "complete", "", ""
	var transferred int64
	r.stats.Lock()
	r.stats.Active++
	r.stats.Unlock()
	w.Header().Set("X-Router-Request-Id", id)
	log.Info("request_started")
	defer func() {
		r.stats.Lock()
		r.stats.Active--
		r.stats.Requests++
		r.stats.Duration += time.Since(start)
		r.stats.Statuses[status]++

		if region != "" {
			r.stats.Regions[region]++
		}

		if outcome == "client_canceled" {
			r.stats.Canceled++
		} else if outcome != "complete" || status >= 500 {
			r.stats.Failures++
		}

		if outcome == "incomplete_stream" {
			r.stats.Incomplete++
		}

		r.stats.Unlock()
		log.Info("request_finished", "region", region, "model", safeModel(model),
			"status", status, "outcome", outcome, "bytes", transferred,
			"duration_ms", time.Since(start).Milliseconds())
	}()
	fail := func(code int, kind, message string, causes ...error) {
		if req.Context().Err() != nil {
			status, outcome = 499, "client_canceled"
			return
		}

		status, outcome = code, kind
		details := []any{"status", status, "error_kind", kind, "region", region, "model", safeModel(model)}

		if len(causes) > 0 {
			message += ": " + causes[0].Error()
			details = append(details, "cause", causes[0].Error())
		}

		log.Warn("request_rejected", details...)
		sendError(w, code, kind, message+" (router request "+id+")")
	}

	if req.URL.IsAbs() || !strings.HasPrefix(req.URL.Path, "/openai/v1/") {
		fail(404, "unknown_endpoint", "Unknown router endpoint")
		return
	}

	if !strings.HasPrefix(req.Header.Get("Authorization"), "Bearer ") {
		fail(401, "missing_auth", "Bearer token required")
		return
	}

	body, err := io.ReadAll(http.MaxBytesReader(w, req.Body, maxBodyBytes))
	if err != nil {
		fail(400, "invalid_body", "Unable to read request body", err)
		return
	}

	model, err = requestModel(body, req.Header.Get("Content-Encoding"))
	if err != nil {
		fail(400, "invalid_body", "Invalid request body", err)
		return
	}

	keys := sessionKeys(req.Header)

	if len(keys) > 0 {
		log = log.With("session", keys[0][:12])
	}

	pinned := ""

	if len(keys) > 0 {
		pinned, err = r.routes.lookup(req.Context(), keys[0])
	}

	if err != nil {
		fail(503, "state_unavailable", "Unable to read session region", err)
		return
	}

	if responseResource(req.URL.Path) && pinned == "" {
		fail(409, "region_unknown", "Stored response operations require the originating session's pinned region. Supply its session header.")
		return
	}

	release := func() {}

	if pinned == "" && len(keys) > 0 {
		discoveryKeys := keys[:1]

		if len(keys) > 1 {
			parentRegion, lookupErr := r.routes.lookup(req.Context(), keys[1])
			if lookupErr != nil {
				fail(503, "state_unavailable", "Unable to read parent session region", lookupErr)
				return
			}

			// An established parent's pin is immutable. Locking it while
			// this new child waits for headers would serialize every fork.
			if parentRegion == "" {
				discoveryKeys = keys
			}
		}

		wait := time.Now()
		log.Info("session_wait_started")

		release, err = r.routes.acquire(req.Context(), discoveryKeys)
		if err != nil {
			status, outcome = 499, "client_canceled"
			return
		}

		defer release()
		log.Info("session_acquired", "wait_ms", time.Since(wait).Milliseconds())

		pinned, err = r.routes.lookup(req.Context(), keys[0])
		if err != nil {
			fail(503, "state_unavailable", "Unable to read session region after waiting for discovery", err)
			return
		}
	}

	confirmed := pinned != ""
	region = pinned
	regionSource := "session"

	if region == "" && len(keys) > 1 {
		region, err = r.routes.lookup(req.Context(), keys[1])
		if err != nil {
			fail(503, "state_unavailable", "Unable to read parent session region", err)
			return
		}

		regionSource = "parent"
	}

	if region == "" {
		region = r.config.ModelRegions[model]
		regionSource = "model_override"

		if region == "" {
			region = r.config.DefaultRegion
			regionSource = "default"
		}
	}

	log = log.With("region_source", regionSource)

	if required := r.config.ModelRegions[model]; required != "" && region != required {
		identity := keys[0][:12]
		if regionSource == "parent" {
			identity = keys[1][:12]
		}

		fail(409, "region_conflict", fmt.Sprintf("Routing uses the saved %s pin %s in %s, but %s requires %s. Existing encrypted history cannot move regions. Start a new independent session with this model; if an auxiliary model runs first, default_region must also be %s.", regionSource, identity, region, model, required, required))
		return
	}

	if confirmed {
		release()
	}

	if req.Method == http.MethodPost && req.URL.Path == "/openai/v1/responses" && len(keys) > 0 &&
		r.recovery.take(keys[0]) {
		if recovered, recoveryErr := addWebRecoveryHint(body, req.Header.Get("Content-Encoding")); recoveryErr == nil {
			body = recovered
			log.Info("web_search_recovery_hint")
		}
	}

	upstreamCtx, cancelUpstream := context.WithCancel(req.Context())
	defer cancelUpstream()
	headerWait, _ := time.ParseDuration(r.config.HeaderTimeout)
	forward := func(target string) (*http.Response, error) {
		up, err := http.NewRequestWithContext(upstreamCtx, req.Method, r.endpoint(target)+req.URL.RequestURI(), bytes.NewReader(body))
		if err != nil {
			return nil, err
		}

		up.Header = req.Header.Clone()
		// Disable transport-level request replay even if the caller supplied
		// an idempotency header. Region validation is our only explicit retry.
		up.GetBody = nil
		stripHopHeaders(up.Header)
		up.Header.Del("Content-Length")
		up.Header.Del("X-Router-Request-Id")
		// Bound connection setup and upload as well as header receipt. Stop
		// the timer once headers arrive so active streams have no total limit.
		expired := make(chan struct{})
		timer := time.AfterFunc(headerWait, func() {
			cancelUpstream()
			close(expired)
		})
		response, err := r.transport.RoundTrip(up)
		if !timer.Stop() {
			// Wait for cancellation to finish before reporting the timeout.
			<-expired
			if response != nil {
				response.Body.Close()
			}
			return nil, context.DeadlineExceeded
		}
		return response, err
	}

	response, err := forward(region)
	if err != nil {
		kind := errorKind(err, req.Context())
		log.Warn("upstream_failed", "region", region, "error_kind", kind)

		if kind == "client_canceled" {
			status, outcome = 499, kind
		} else {
			code := 502

			if kind == "timeout" {
				code = 504
			}

			fail(code, kind, fmt.Sprintf("Bedrock upstream connection failed in %s (%s)", region, kind), err)
		}

		return
	}

	// Only retry an explicit regional validation rejection; a generation or
	// partial stream is never replayed, including HTTP 500 and transport errors.
	if response.StatusCode == 400 {
		prefix, readErr := io.ReadAll(io.LimitReader(response.Body, (1<<20)+1))
		if readErr != nil {
			response.Body.Close()
			fail(502, errorKind(readErr, req.Context()), "Unable to read Bedrock error response", readErr)
			return
		}

		response.Body = &prefixedBody{Reader: io.MultiReader(bytes.NewReader(prefix), response.Body), Closer: response.Body}
		var data struct {
			Error struct {
				Code, Message string
			}
		}
		alternate := r.config.RegionFallbacks[region]
		regionMismatch := len(prefix) <= 1<<20 && json.Unmarshal(prefix, &data) == nil &&
			data.Error.Code == "validation_error" &&
			strings.Contains(data.Error.Message, "Encrypted content cannot be used in a different region")
		log.Warn("upstream_rejected", "region", region, "status", response.StatusCode, "encrypted_region_mismatch", regionMismatch)

		if alternate != "" && !confirmed && r.config.ModelRegions[model] == "" && readErr == nil && len(prefix) <= 1<<20 &&
			regionMismatch {
			r.stats.Lock()
			r.stats.Retries++
			r.stats.Unlock()

			other, retryErr := forward(alternate)
			if retryErr == nil {
				log.Info("discover_context_region", "region", alternate, "status", other.StatusCode)

				if other.StatusCode >= 200 && other.StatusCode < 300 {
					response.Body.Close()
					response, region = other, alternate
				} else {
					rejection, readErr := io.ReadAll(io.LimitReader(other.Body, (1<<20)+1))
					data.Error.Code, data.Error.Message = "", ""
					mismatch := readErr == nil && len(rejection) <= 1<<20 &&
						json.Unmarshal(rejection, &data) == nil && data.Error.Code == "validation_error" &&
						strings.Contains(data.Error.Message, "Encrypted content cannot be used in a different region")
					log.Warn("region_discovery_rejected", "region", alternate, "status", other.StatusCode,
						"encrypted_region_mismatch", mismatch)
					other.Body.Close()
				}
			} else {
				log.Warn("region_discovery_failed", "region", alternate, "error_kind", errorKind(retryErr, req.Context()))
			}
		}
	}

	defer response.Body.Close()

	if model != "" && len(keys) > 0 && response.StatusCode >= 200 && response.StatusCode < 300 {
		if _, err = r.routes.db.ExecContext(req.Context(), "INSERT OR IGNORE INTO sessions VALUES (?, ?)", keys[0], region); err != nil {
			fail(503, "state_unavailable", "Unable to persist session region", err)
			return
		}
	}

	release()
	status = response.StatusCode

	if status >= 400 {
		outcome = "upstream_http_error"
	}

	log.Info("upstream_headers", "region", region, "status", status,
		"headers_ms", time.Since(start).Milliseconds(), "upstream_request_id", safeModel(response.Header.Get("X-Amzn-Requestid")))

	if status >= 400 {
		log.Warn("upstream_http_error", "region", region, "status", status)
	}

	stream := strings.HasPrefix(strings.ToLower(response.Header.Get("Content-Type")), "text/event-stream")

	if stream {
		// A fixed length could make a truncated SSE stream look complete
		// to the caller before we have checked its terminal event.
		response.Header.Del("Content-Length")
	}

	stripHopHeaders(response.Header)
	for key, values := range response.Header {
		if strings.EqualFold(key, "X-Router-Request-Id") {
			continue
		}

		w.Header()[key] = values
	}

	control := http.NewResponseController(w)
	_ = control.SetWriteDeadline(time.Now().Add(r.writeIdle))
	w.WriteHeader(status)
	if err := control.Flush(); err != nil {
		outcome = "client_write_error"
		if req.Context().Err() != nil {
			outcome = "client_canceled"
		}
		log.Warn("stream_failed", "side", "client", "error_kind", outcome)
		return
	}

	if stream {
		r.stats.Lock()
		r.stats.Streams++
		r.stats.Unlock()
		defer func() {
			r.stats.Lock()
			r.stats.Streams--
			r.stats.Unlock()
		}()
	}

	var tracker terminalTracker
	defer func() {
		if tracker.webDenied && len(keys) > 0 {
			r.recovery.record(keys[0])
			log.Warn("web_search_denied")
		}
	}()
	buf := make([]byte, 32<<10)
	for {
		n, readErr := response.Body.Read(buf)

		if n > 0 {
			if transferred == 0 {
				log.Info("first_response_bytes", "first_byte_ms", time.Since(start).Milliseconds())
			}

			if stream {
				tracker.observe(buf[:n])
			}

			_ = control.SetWriteDeadline(time.Now().Add(r.writeIdle))
			written, writeErr := w.Write(buf[:n])
			transferred += int64(written)
			r.stats.Lock()
			r.stats.Bytes += uint64(written)
			r.stats.Unlock()

			if writeErr == nil {
				writeErr = control.Flush()
			}

			if writeErr != nil {
				outcome = "client_write_error"

				if req.Context().Err() != nil {
					outcome = "client_canceled"
				}

				log.Warn("stream_failed", "side", "client", "error_kind", outcome)
				return
			}
		}

		if readErr != nil {
			if !errors.Is(readErr, io.EOF) {
				outcome = errorKind(readErr, req.Context())
				log.Warn("stream_failed", "side", "upstream", "error_kind", outcome)
			} else if stream && !tracker.terminal {
				outcome = "incomplete_stream"
				log.Warn("stream_failed", "side", "upstream", "error_kind", outcome)
				// Abort HTTP framing so the caller can distinguish truncation
				// from a successful EOF. Deferred accounting still runs.
				panic(http.ErrAbortHandler)
			} else if tracker.failed {
				outcome = "upstream_stream_error"
			}

			if !errors.Is(readErr, io.EOF) {
				panic(http.ErrAbortHandler)
			}

			return
		}
	}
}

type prefixedBody struct {
	io.Reader
	io.Closer
}

// Inspect only bounded SSE lines; never retain or log prompt/output payloads.
type terminalTracker struct {
	line      []byte
	overflow  bool
	terminal  bool
	failed    bool
	webDenied bool
	eventType string
}

func (t *terminalTracker) observe(chunk []byte) {
	for _, b := range chunk {
		if b == '\n' {
			if !t.overflow {
				line := strings.TrimSpace(string(t.line))

				if strings.HasPrefix(line, "event:") {
					t.eventType = strings.TrimSpace(strings.TrimPrefix(line, "event:"))
					t.event(t.eventType)
				} else if strings.HasPrefix(line, "data:") {
					data := strings.TrimSpace(strings.TrimPrefix(line, "data:"))

					if data == "[DONE]" {
						t.terminal = true
					} else {
						var event struct {
							Type     string
							Error    struct{ Message string }
							Response struct {
								Error struct{ Message string }
							}
						}

						if json.Unmarshal([]byte(data), &event) == nil {
							t.event(event.Type)

							if event.Type == "response.failed" || event.Type == "error" {
								const denial = "Access denied: web search is not authorized for this identity."
								t.webDenied = t.webDenied || event.Error.Message == denial ||
									event.Response.Error.Message == denial
							}
						}
					}
				} else if line == "" {
					t.eventType = ""
				}
			}

			t.line, t.overflow = t.line[:0], false
		} else {
			limit := 64 << 10
			// Failed responses may include the generated output before the
			// error object. Keep that inspection bounded too.
			if t.eventType == "response.failed" || t.eventType == "error" {
				limit = 1 << 20
			}

			if len(t.line) < limit {
				t.line = append(t.line, b)
			} else {
				t.overflow = true
			}
		}
	}
}

func (t *terminalTracker) event(event string) {
	switch event {
	case "response.completed":
		t.terminal = true
	case "response.failed", "response.incomplete", "error":
		t.terminal, t.failed = true, true
	}
}

func (r *router) monitor(w http.ResponseWriter, req *http.Request) {
	r.stats.Lock()
	defer r.stats.Unlock()
	var pinned int

	if err := r.routes.db.QueryRowContext(req.Context(), "SELECT count(*) FROM sessions").Scan(&pinned); err != nil {
		r.log.Warn("monitor_failed", "message", err.Error())
		sendError(w, 503, "state_unavailable", "Unable to count pinned sessions: "+err.Error())
		return
	}

	if req.URL.Path == "/healthz" {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"status": "ok", "implementation": "go", "default_region": r.config.DefaultRegion, "model_regions": r.config.ModelRegions, "region_fallbacks": r.config.RegionFallbacks, "session_affinity": true, "pinned_sessions": pinned, "requests_by_region": r.stats.Regions, "active_requests": r.stats.Active, "active_streams": r.stats.Streams, "completed_requests": r.stats.Requests, "response_bytes": r.stats.Bytes, "failures": r.stats.Failures, "incomplete_streams": r.stats.Incomplete, "canceled_requests": r.stats.Canceled, "uptime_seconds": time.Since(r.started).Seconds(),
		})
		return
	}

	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	for _, metric := range []struct {
		name, kind string
		value      uint64
	}{
		{"active_requests", "gauge", r.stats.Active}, {"active_streams", "gauge", r.stats.Streams},
		{"requests_total", "counter", r.stats.Requests}, {"response_bytes_total", "counter", r.stats.Bytes},
		{"failures_total", "counter", r.stats.Failures}, {"incomplete_streams_total", "counter", r.stats.Incomplete},
		{"canceled_requests_total", "counter", r.stats.Canceled}, {"region_discovery_total", "counter", r.stats.Retries},
		{"pinned_sessions", "gauge", uint64(pinned)},
	} {
		fmt.Fprintf(w, "# TYPE bedrock_router_%s %s\nbedrock_router_%s %d\n", metric.name, metric.kind, metric.name, metric.value)
	}

	fmt.Fprintf(w, "# TYPE bedrock_router_request_duration_seconds summary\nbedrock_router_request_duration_seconds_sum %f\nbedrock_router_request_duration_seconds_count %d\n",
		r.stats.Duration.Seconds(), r.stats.Requests)
	fmt.Fprintln(w, "# TYPE bedrock_router_region_requests_total counter")
	for region, count := range r.stats.Regions {
		fmt.Fprintf(w, "bedrock_router_region_requests_total{region=%q} %d\n", region, count)
	}

	fmt.Fprintln(w, "# TYPE bedrock_router_status_requests_total counter")
	for status, count := range r.stats.Statuses {
		fmt.Fprintf(w, "bedrock_router_status_requests_total{status=%q} %d\n", fmt.Sprint(status), count)
	}
}
