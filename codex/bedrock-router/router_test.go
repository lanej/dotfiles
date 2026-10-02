package main

import (
	"bytes"
	"compress/gzip"
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func fixture(t *testing.T, upstream http.Handler) (*router, *httptest.Server, *bytes.Buffer) {
	t.Helper()

	cfg, err := loadConfiguration("")
	if err != nil {
		t.Fatal(err)
	}

	return fixtureConfig(t, upstream, cfg)
}

func fixtureConfig(t *testing.T, upstream http.Handler, cfg configuration) (*router, *httptest.Server, *bytes.Buffer) {
	t.Helper()
	up := httptest.NewServer(upstream)
	t.Cleanup(up.Close)
	logs := new(bytes.Buffer)

	r, err := newRouter(filepath.Join(t.TempDir(), "sessions.sqlite3"), up.Client().Transport, slog.New(slog.NewJSONHandler(logs, nil)), cfg)
	if err != nil {
		t.Fatal(err)
	}

	r.endpoint = func(string) string { return up.URL }
	srv := httptest.NewServer(r)
	t.Cleanup(func() { srv.Close(); r.routes.db.Close() })
	return r, srv, logs
}

func call(t *testing.T, client *http.Client, url, model, session, parent string) *http.Response {
	t.Helper()
	body, _ := json.Marshal(map[string]any{"model": model, "input": "private-prompt"})
	req, _ := http.NewRequest("POST", url+"/openai/v1/responses", bytes.NewReader(body))
	req.Header.Set("Authorization", "Bearer private-token")
	req.Header.Set("Thread-Id", session)
	req.Header.Set("X-Codex-Parent-Thread-Id", parent)

	resp, err := client.Do(req)
	if err != nil {
		t.Fatal(err)
	}

	t.Cleanup(func() { resp.Body.Close() })
	return resp
}

func drain(t *testing.T, response *http.Response, status int) []byte {
	t.Helper()
	body, err := io.ReadAll(response.Body)
	response.Body.Close()

	if err != nil || response.StatusCode != status {
		t.Fatalf("status=%d, body=%s, error=%v", response.StatusCode, body, err)
	}

	return body
}

func TestSessionAffinityThroughConcurrentStreamsAndRestart(t *testing.T) {
	release := make(chan struct{})
	var releaseOnce sync.Once
	unblock := func() { releaseOnce.Do(func() { close(release) }) }
	defer unblock()
	slowStarted := make(chan struct{})
	r, server, _ := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		io.Copy(io.Discard, req.Body)

		if req.Header.Get("Thread-Id") == "discovery-slow" {
			close(slowStarted)
			select {
			case <-release:
			case <-req.Context().Done():
				return
			}
		}

		w.Header().Set("Content-Type", "text/event-stream")
		io.WriteString(w, "data: first\n\n")
		w.(http.Flusher).Flush()

		if strings.HasPrefix(req.Header.Get("Thread-Id"), "load-") {
			select {
			case <-release:
			case <-req.Context().Done():
				return
			}
		}

		io.WriteString(w, "data: [DONE]\n\n")
	}))
	client := &http.Client{Timeout: 5 * time.Second}
	drain(t, call(t, client, server.URL, "openai.gpt-6.1-sol", "east-parent", ""), 200)
	drain(t, call(t, client, server.URL, "openai.gpt-6-astra", "west-parent", ""), 200)
	drain(t, call(t, client, server.URL, "openai.gpt-6.1-sol", "west-parent", ""), 409)
	drain(t, call(t, client, server.URL, "openai.gpt-5.6-luna", "child", "east-parent"), 200)
	key := sessionKeys(http.Header{"Thread-Id": {"child"}})[0]

	if region, err := r.routes.lookup(context.Background(), key); region != "us-east-1" || err != nil {
		t.Fatalf("child region=%s, err=%v", region, err)
	}

	slowFinished := make(chan error, 1)
	go func() {
		req, _ := http.NewRequest("POST", server.URL+"/openai/v1/responses", strings.NewReader(`{"model":"openai.gpt-5.6-luna"}`))
		req.Header.Set("Authorization", "Bearer private-token")
		req.Header.Set("Thread-Id", "discovery-slow")
		req.Header.Set("X-Codex-Parent-Thread-Id", "east-parent")

		resp, err := client.Do(req)
		if err == nil {
			_, err = io.Copy(io.Discard, resp.Body)
			resp.Body.Close()
		}

		slowFinished <- err
	}()
	select {
	case <-slowStarted:
	case <-time.After(2 * time.Second):
		t.Fatal("slow discovery never reached upstream")
	}

	// A new child waiting on upstream headers must not block sibling forks
	// of an already pinned parent.
	drain(t, call(t, client, server.URL, "openai.gpt-5.6-luna", "quick-sibling", "east-parent"), 200)
	// Hold many independent sessions open, including simultaneous requests
	// within one established session. Every first event must arrive before
	// any stream is released.
	const concurrent = 32
	results := make(chan error, concurrent)
	var wg sync.WaitGroup
	for i := range concurrent {
		wg.Add(1)
		go func() {
			defer wg.Done()
			body := strings.NewReader(`{"model":"openai.gpt-5.6-luna"}`)
			req, _ := http.NewRequest("POST", server.URL+"/openai/v1/responses", body)
			req.Header.Set("Authorization", "Bearer private-token")
			session := "load-" + strconv.Itoa(i)

			if i%2 == 0 {
				session = "load-established"
			}

			req.Header.Set("Thread-Id", session)
			req.Header.Set("X-Codex-Parent-Thread-Id", "east-parent")

			resp, err := client.Do(req)
			if err == nil {
				first := make([]byte, len("data: first\n\n"))
				_, err = io.ReadFull(resp.Body, first)

				if err == nil && string(first) != "data: first\n\n" {
					err = io.ErrUnexpectedEOF
				}

				results <- err
				io.Copy(io.Discard, resp.Body)
				resp.Body.Close()
			} else {
				results <- err
			}
		}()
	}

	for range concurrent {
		select {
		case err := <-results:
			if err != nil {
				unblock()
				t.Fatal(err)
			}
		case <-time.After(5 * time.Second):
			unblock()
			t.Fatal("concurrent sessions blocked before first event")
		}
	}

	r.stats.Lock()
	active := r.stats.Streams
	r.stats.Unlock()

	if active != concurrent {
		t.Fatalf("active streams=%d, want %d", active, concurrent)
	}

	unblock()
	wg.Wait()

	if err := <-slowFinished; err != nil {
		t.Fatal(err)
	}

	server.Close()
	// Reopen the same SQLite file through the real service entrypoint.
	var dbPath string

	rows, err := r.routes.db.Query("PRAGMA database_list")
	if err != nil {
		t.Fatal(err)
	}

	for rows.Next() {
		var seq int
		var name string

		if err := rows.Scan(&seq, &name, &dbPath); err != nil {
			t.Fatal(err)
		}
	}

	rows.Close()
	r.routes.db.Close()

	restarted, err := newRouter(dbPath, r.transport, r.log, r.config)
	if err != nil {
		t.Fatal(err)
	}

	restarted.endpoint = r.endpoint
	defer restarted.routes.db.Close()
	second := httptest.NewServer(restarted)
	defer second.Close()
	drain(t, call(t, client, second.URL, "openai.gpt-6-astra", "child", ""), 200)

	if region, _ := restarted.routes.lookup(context.Background(), key); region != "us-east-1" {
		t.Fatalf("region changed on restart: %s", region)
	}

	restarted.routes.mu.Lock()
	defer restarted.routes.mu.Unlock()

	if len(restarted.routes.gates) != 0 {
		t.Fatal("session gates leaked")
	}
}

func TestRegionRecoveryPreservesCompressedChunkedPayload(t *testing.T) {
	payload := []byte(`{"model":"openai.gpt-5.6-luna","input":[{"type":"reasoning","encrypted_content":"private-ciphertext"}]}`)
	var compressed bytes.Buffer
	gz := gzip.NewWriter(&compressed)
	gz.Write(payload)
	gz.Close()
	var mu sync.Mutex
	var seen [][]byte
	r, server, _ := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		body, _ := io.ReadAll(req.Body)

		if !bytes.Equal(body, compressed.Bytes()) || req.Header.Get("Authorization") != "Bearer private-token" ||
			req.Header.Get("Content-Encoding") != "gzip" {
			t.Error("request payload or credentials changed")
		}

		mu.Lock()
		seen = append(seen, body)
		mu.Unlock()

		if !strings.HasPrefix(req.URL.Path, "/regions/us-east-1/") {
			w.WriteHeader(400)
			io.WriteString(w, `{"error":{"code":"validation_error","message":"Encrypted content cannot be used in a different region"}}`)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		io.WriteString(w, "data: [DONE]\n\n")
	}))
	base := r.endpoint("")
	r.endpoint = func(region string) string { return base + "/regions/" + region }
	req, _ := http.NewRequest("POST", server.URL+"/openai/v1/responses", io.NopCloser(bytes.NewReader(compressed.Bytes())))
	req.ContentLength = -1
	req.Header.Set("Authorization", "Bearer private-token")
	req.Header.Set("Content-Encoding", "gzip")
	req.Header.Set("Thread-Id", "legacy")

	resp, err := server.Client().Do(req)
	if err != nil {
		t.Fatal(err)
	}

	drain(t, resp, 200)
	key := sessionKeys(req.Header)[0]

	if region, _ := r.routes.lookup(context.Background(), key); region != "us-east-1" {
		t.Fatalf("discovered region=%s", region)
	}

	mu.Lock()
	defer mu.Unlock()

	if len(seen) != 2 {
		t.Fatalf("attempts=%d, want 2", len(seen))
	}
}

func TestMixedRegionHistoryIsReportedWithoutChangingHistory(t *testing.T) {
	rejection := `{"error":{"code":"validation_error","message":"Encrypted content cannot be used in a different region from the one that created it."}}`
	r, server, logs := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		w.WriteHeader(400)
		io.WriteString(w, rejection)
	}))
	resp := call(t, server.Client(), server.URL, "openai.gpt-6-astra", "mixed-history", "")

	if body := drain(t, resp, 400); string(body) != rejection {
		t.Fatalf("upstream rejection changed: %s", body)
	}

	health, err := server.Client().Get(server.URL + "/healthz")
	if err != nil {
		t.Fatal(err)
	}

	var snapshot map[string]any
	json.NewDecoder(health.Body).Decode(&snapshot)
	health.Body.Close()

	if snapshot["failures"] != float64(1) {
		t.Fatalf("rejection missing from monitoring: %v", snapshot)
	}

	header := http.Header{"Thread-Id": []string{"mixed-history"}}

	if region, err := r.routes.lookup(context.Background(), sessionKeys(header)[0]); err != nil || region != "" {
		t.Fatalf("rejected history acquired a pin: %q, %v", region, err)
	}

	if !strings.Contains(logs.String(), `"event":"region_discovery_rejected"`) &&
		!strings.Contains(logs.String(), `"msg":"region_discovery_rejected"`) {
		t.Fatalf("alternate rejection missing from logs: %s", logs)
	}

	if !strings.Contains(logs.String(), `"encrypted_region_mismatch":true`) ||
		!strings.Contains(logs.String(), `"outcome":"upstream_http_error"`) ||
		strings.Contains(logs.String(), "private-") {
		t.Fatalf("unsafe or incomplete rejection logs: %s", logs)
	}
}

func TestIncompleteStreamIsReportedAndNeverReplayed(t *testing.T) {
	_, server, logs := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		io.WriteString(w, "data: first\n\n")
	}))
	resp := call(t, server.Client(), server.URL, "openai.gpt-6-astra", "broken", "")
	data, err := io.ReadAll(resp.Body)
	resp.Body.Close()

	if err == nil || string(data) != "data: first\n\n" {
		t.Fatalf("truncation not observable: data=%s err=%v", data, err)
	}

	health, err := server.Client().Get(server.URL + "/healthz")
	if err != nil {
		t.Fatal(err)
	}

	var snapshot map[string]any
	json.NewDecoder(health.Body).Decode(&snapshot)
	health.Body.Close()

	if snapshot["incomplete_streams"] != float64(1) || snapshot["completed_requests"] != float64(1) {
		t.Fatalf("bad monitoring snapshot: %v", snapshot)
	}

	server.Close()

	if !strings.Contains(logs.String(), `"outcome":"incomplete_stream"`) ||
		strings.Contains(logs.String(), "private-token") || strings.Contains(logs.String(), "private-prompt") {
		t.Fatalf("missing stream outcome or leaked private content")
	}
}

func TestWebSearchDenialGuidesNextAttemptWithoutDisablingSearch(t *testing.T) {
	failure := "event: response.failed\ndata: {\"type\":\"response.failed\",\"response\":{\"id\":\"resp_denied\",\"output\":\"" +
		strings.Repeat("x", 70<<10) + "\",\"error\":{\"message\":\"Access denied: web search is not authorized for this identity.\"}}}\n\n"
	const completed = "event: response.completed\ndata: {\"type\":\"response.completed\",\"response\":{\"id\":\"resp_ok\"}}\n\n"
	const original = `{"model":"openai.gpt-6-astra","tools":[{"type":"web_search","external_web_access":true}],"input":[{"type":"reasoning","encrypted_content":"opaque-history"},{"role":"user","content":"look up a page"}],"unknown":{"preserve":true}}`
	requests := make(chan []byte, 4)
	var calls atomic.Int32
	_, server, logs := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		if req.Header.Get("Content-Encoding") != "gzip" {
			t.Error("recovery changed request encoding")
		}

		reader, err := gzip.NewReader(req.Body)
		if err != nil {
			t.Error(err)
			return
		}

		body, err := io.ReadAll(reader)
		reader.Close()

		if err != nil {
			t.Error(err)
			return
		}

		requests <- body
		w.Header().Set("Content-Type", "text/event-stream")

		if calls.Add(1) == 1 {
			// Split the error payload across reads, as a real stream may do.
			io.WriteString(w, failure[:len(failure)/2])
			w.(http.Flusher).Flush()
			io.WriteString(w, failure[len(failure)/2:])
		} else {
			io.WriteString(w, completed)
		}
	}))
	send := func(session string) string {
		t.Helper()
		var compressed bytes.Buffer
		writer := gzip.NewWriter(&compressed)
		writer.Write([]byte(original))
		writer.Close()
		req, _ := http.NewRequest("POST", server.URL+"/openai/v1/responses", &compressed)
		req.Header.Set("Authorization", "Bearer private-token")
		req.Header.Set("Thread-Id", session)
		req.Header.Set("Content-Encoding", "gzip")

		resp, err := server.Client().Do(req)
		if err != nil {
			t.Fatal(err)
		}

		return string(drain(t, resp, http.StatusOK))
	}

	if got := send("denied-session"); got != failure {
		t.Fatalf("failure was hidden or rewritten: %s", got)
	}

	if got := <-requests; string(got) != original {
		t.Fatal("initial request was changed")
	}

	send("unrelated-session")

	if got := <-requests; string(got) != original {
		t.Fatal("web denial affected another session")
	}

	if got := send("denied-session"); got != completed {
		t.Fatal("retry did not complete")
	}

	var recovered, unchanged map[string]json.RawMessage
	if err := json.Unmarshal(<-requests, &recovered); err != nil {
		t.Fatal(err)
	}

	json.Unmarshal([]byte(original), &unchanged)
	var input []json.RawMessage
	json.Unmarshal(recovered["input"], &input)
	var previousInput []json.RawMessage
	json.Unmarshal(unchanged["input"], &previousInput)

	if len(input) != 3 || !bytes.Equal(input[0], previousInput[0]) || !bytes.Equal(input[1], previousInput[1]) {
		t.Fatal("recovery lost original history")
	}

	var hint struct{ Role, Content string }
	json.Unmarshal(input[2], &hint)

	if hint.Role != "developer" || hint.Content != webRecoveryHint ||
		!bytes.Equal(recovered["tools"], unchanged["tools"]) ||
		!bytes.Equal(recovered["unknown"], unchanged["unknown"]) {
		t.Fatal("recovery missing guidance or changed web-search tools/unknown fields")
	}

	send("denied-session")

	if got := <-requests; string(got) != original || calls.Load() != 4 {
		t.Fatal("recovery hint persisted or router replayed a generation")
	}

	server.Close()

	if !strings.Contains(logs.String(), `"msg":"web_search_denied"`) ||
		!strings.Contains(logs.String(), `"msg":"web_search_recovery_hint"`) ||
		strings.Contains(logs.String(), "opaque-history") {
		t.Fatal("recovery metadata missing or private history logged")
	}
}

func TestUpstreamHeaderTimeoutReturnsGatewayTimeout(t *testing.T) {
	r, server, _ := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		io.Copy(io.Discard, req.Body)
		<-req.Context().Done()
	}))
	transport := &http.Transport{ResponseHeaderTimeout: 50 * time.Millisecond}
	defer transport.CloseIdleConnections()
	r.transport = transport
	resp := call(t, &http.Client{Timeout: time.Second}, server.URL, "openai.gpt-6-astra", "slow", "")
	body := drain(t, resp, 504)

	if !bytes.Contains(body, []byte(`"code":"timeout"`)) {
		t.Fatalf("missing timeout diagnosis: %s", body)
	}

	metrics, err := server.Client().Get(server.URL + "/metrics")
	if err != nil {
		t.Fatal(err)
	}

	data := drain(t, metrics, 200)

	if !bytes.Contains(data, []byte("bedrock_router_failures_total 1")) {
		t.Fatalf("timeout absent from metrics: %s", data)
	}
}

func TestUpstreamSilenceTimeoutResetsOnActivity(t *testing.T) {
	r, server, _ := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		io.Copy(io.Discard, req.Body)
		w.Header().Set("Content-Type", "text/event-stream")

		if req.Header.Get("Thread-Id") == "silent" {
			io.WriteString(w, "data: first\n\n")
			w.(http.Flusher).Flush()
			<-req.Context().Done()
			return
		}

		for range 5 {
			time.Sleep(100 * time.Millisecond)

			if _, err := io.WriteString(w, "data: progress\n\n"); err != nil {
				return
			}

			w.(http.Flusher).Flush()
		}

		io.WriteString(w, "data: [DONE]\n\n")
	}))
	transport := &http.Transport{
		DialContext: func(ctx context.Context, network, address string) (net.Conn, error) {
			conn, err := (&net.Dialer{}).DialContext(ctx, network, address)
			if err != nil {
				return nil, err
			}

			return &idleConn{Conn: conn, idle: 300 * time.Millisecond}, nil
		},
	}
	defer transport.CloseIdleConnections()
	r.transport = transport
	client := &http.Client{Timeout: 3 * time.Second}
	resp := call(t, client, server.URL, "openai.gpt-6-astra", "steady", "")

	if body := drain(t, resp, 200); !bytes.Contains(body, []byte("[DONE]")) {
		t.Fatal("healthy stream lost its completion")
	}

	resp = call(t, client, server.URL, "openai.gpt-6-astra", "silent", "")
	body, err := io.ReadAll(resp.Body)
	resp.Body.Close()

	if err == nil || string(body) != "data: first\n\n" {
		t.Fatalf("silent stream did not fail visibly: body=%s error=%v", body, err)
	}

	r.stats.Lock()
	defer r.stats.Unlock()

	if r.stats.Failures != 1 {
		t.Fatalf("silent stream failures=%d", r.stats.Failures)
	}
}

func TestClientCancellationReleasesSessionDiscovery(t *testing.T) {
	started, canceled := make(chan struct{}), make(chan struct{})
	r, server, _ := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		io.Copy(io.Discard, req.Body)

		if req.Header.Get("X-Test-Wait") != "" {
			close(started)
			<-req.Context().Done()
			close(canceled)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		io.WriteString(w, "data: [DONE]\n\n")
	}))
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	req, _ := http.NewRequestWithContext(ctx, "POST", server.URL+"/openai/v1/responses", strings.NewReader(`{"model":"openai.gpt-6-astra"}`))
	req.Header.Set("Authorization", "Bearer private-token")
	req.Header.Set("Thread-Id", "cancel-session")
	req.Header.Set("X-Test-Wait", "1")
	done := make(chan error, 1)
	go func() {
		resp, err := server.Client().Do(req)

		if resp != nil {
			resp.Body.Close()
		}

		done <- err
	}()
	select {
	case <-started:
	case <-time.After(2 * time.Second):
		t.Fatal("upstream request never started")
	}

	waitCtx, waitCancel := context.WithTimeout(context.Background(), 80*time.Millisecond)
	defer waitCancel()
	waiter := req.Clone(waitCtx)
	waiter.Body = io.NopCloser(strings.NewReader(`{"model":"openai.gpt-6-astra"}`))
	resp, err := server.Client().Do(waiter)

	if resp != nil {
		resp.Body.Close()
	}

	if err == nil {
		t.Fatal("waiting request ignored cancellation")
	}

	cancel()
	select {
	case <-canceled:
	case <-time.After(2 * time.Second):
		t.Fatal("client cancellation did not cancel upstream")
	}

	if err := <-done; err == nil {
		t.Fatal("canceled request unexpectedly succeeded")
	}

	drain(t, call(t, &http.Client{Timeout: 2 * time.Second}, server.URL, "openai.gpt-6-astra", "cancel-session", ""), 200)
	server.Close()
	r.routes.mu.Lock()
	defer r.routes.mu.Unlock()

	if len(r.routes.gates) != 0 {
		t.Fatal("canceled requests left discovery locks")
	}
}

func TestLocalGuardRejectsUnauthorizedProxying(t *testing.T) {
	var requests atomic.Int32
	_, server, _ := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		requests.Add(1)
		w.Header().Set("Content-Type", "text/event-stream")
		io.WriteString(w, "data: [DONE]\n\n")
	}))

	resp, err := server.Client().Post(server.URL+"/openai/v1/responses", "application/json", strings.NewReader(`{}`))
	if err != nil {
		t.Fatal(err)
	}

	drain(t, resp, 401)
	req, _ := http.NewRequest("POST", server.URL+"/unrelated", strings.NewReader(`{}`))
	req.Header.Set("Authorization", "Bearer private-token")

	resp, err = server.Client().Do(req)
	if err != nil {
		t.Fatal(err)
	}

	drain(t, resp, 404)
	drain(t, call(t, server.Client(), server.URL, "openai.gpt-6-astra", "", ""), 200)

	if requests.Load() != 1 {
		t.Fatal("a rejected request reached upstream")
	}
}

func TestStoredResponseLifecycleUsesSessionRegion(t *testing.T) {
	var requests atomic.Int32
	payload := `{"model":"openai.gpt-6.1-sol","input":"hello","future_field":{"opaque":true}}`
	_, server, _ := fixture(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		step := requests.Add(1)
		body, _ := io.ReadAll(req.Body)
		switch step {
		case 1:
			if req.Method != "POST" || req.URL.Path != "/openai/v1/responses" || string(body) != payload {
				t.Errorf("creation changed: %s %s %s", req.Method, req.URL, body)
			}
		case 2:
			if req.Method != "GET" || req.URL.RequestURI() != "/openai/v1/responses/resp_opaque?include=usage" || len(body) != 0 {
				t.Errorf("retrieval changed: %s %s %s", req.Method, req.URL, body)
			}
		case 3:
			if req.Method != "POST" || req.URL.Path != "/openai/v1/responses/resp_opaque/cancel" || string(body) != "{}" {
				t.Errorf("cancellation changed: %s %s %s", req.Method, req.URL, body)
			}
		case 4:
			if req.Method != "DELETE" || req.URL.Path != "/openai/v1/responses/resp_opaque" || len(body) != 0 {
				t.Errorf("deletion changed: %s %s %s", req.Method, req.URL, body)
			}
		default:
			t.Errorf("unexpected upstream request")
		}

		io.WriteString(w, `{"id":"resp_opaque","future_field":true}`)
	}))
	// Observe the target selected before the fixture redirects to its server.
	r := server.Config.Handler.(*router)
	upstream := r.endpoint
	r.endpoint = func(region string) string {
		if region != "us-east-1" {
			t.Errorf("stored response routed to %s", region)
		}

		return upstream(region)
	}
	do := func(method, path, body, session string, status int) {
		t.Helper()
		req, _ := http.NewRequest(method, server.URL+path, strings.NewReader(body))
		req.Header.Set("Authorization", "Bearer private-token")
		req.Header.Set("Thread-Id", session)

		resp, err := server.Client().Do(req)
		if err != nil {
			t.Fatal(err)
		}

		got := drain(t, resp, status)

		if status == 200 && string(got) != `{"id":"resp_opaque","future_field":true}` {
			t.Fatalf("response changed: %s", got)
		}

		if status == 409 && !bytes.Contains(got, []byte(`"region_unknown"`)) {
			t.Fatalf("missing routing error: %s", got)
		}
	}
	do("POST", "/openai/v1/responses", payload, "origin", 200)
	do("GET", "/openai/v1/responses/resp_opaque?include=usage", "", "origin", 200)
	do("POST", "/openai/v1/responses/resp_opaque/cancel", "{}", "origin", 200)
	do("DELETE", "/openai/v1/responses/resp_opaque", "", "origin", 200)
	do("GET", "/openai/v1/responses/resp_opaque", "", "unrecorded", 409)

	if requests.Load() != 4 {
		t.Fatal("unroutable resource request reached upstream")
	}
}

func TestConfigurationFileControlsRegionalRouting(t *testing.T) {
	cfg, err := loadConfiguration("")
	if err != nil {
		t.Fatal(err)
	}

	cfg.DefaultRegion = "us-east-1"
	cfg.ModelRegions = map[string]string{"custom-model": "us-west-2"}
	data, _ := json.Marshal(cfg)
	path := filepath.Join(t.TempDir(), "config.json")

	if err := os.WriteFile(path, data, 0600); err != nil {
		t.Fatal(err)
	}

	loaded, err := loadConfiguration(path)
	if err != nil {
		t.Fatal(err)
	}

	r, server, _ := fixtureConfig(t, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		w.Header().Set("X-Upstream-Region", strings.Split(req.URL.Path, "/")[2])
		w.Header().Set("Content-Type", "text/event-stream")
		io.WriteString(w, "data: [DONE]\n\n")
	}), loaded)
	base := r.endpoint("")
	r.endpoint = func(region string) string { return base + "/regions/" + region }
	resp := call(t, server.Client(), server.URL, "custom-model", "configured-session", "")

	if resp.Header.Get("X-Upstream-Region") != "us-west-2" {
		t.Fatalf("configured model routed to %q", resp.Header.Get("X-Upstream-Region"))
	}

	drain(t, resp, 200)

	health, err := server.Client().Get(server.URL + "/healthz")
	if err != nil {
		t.Fatal(err)
	}

	var snapshot struct {
		DefaultRegion string `json:"default_region"`
	}

	if err := json.NewDecoder(health.Body).Decode(&snapshot); err != nil {
		t.Fatal(err)
	}

	health.Body.Close()

	if snapshot.DefaultRegion != "us-east-1" {
		t.Fatal("configuration file did not control the default region")
	}
}
