package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
)

func TestBrowsingToolReturnsResearchFromSeparateModel(t *testing.T) {
	var requests atomic.Int32
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		var body map[string]any
		if err := json.NewDecoder(req.Body).Decode(&body); err != nil {
			t.Error(err)
		}

		if req.URL.Path != "/openai/v1/responses" || req.Header.Get("Authorization") != "Bearer test-only" ||
			body["model"] != "openai.gpt-5.6-luna" || body["store"] != false ||
			!strings.Contains(body["input"].(string), "Find the official memory documentation") {
			t.Errorf("unexpected delegated request: %s, %v", req.URL.Path, body)
		}

		tools, _ := body["tools"].([]any)
		if len(tools) != 1 || tools[0].(map[string]any)["type"] != "web_search" {
			t.Error("request did not enable web browsing")
		}

		if requests.Add(1) == 2 {
			w.Header().Set("X-Amzn-Requestid", "browse-rejection-123")
			w.WriteHeader(http.StatusForbidden)
			io.WriteString(w, `{"error":{"message":"test-only private research task"}}`)
			return
		}

		io.WriteString(w, `{"status":"completed","output":[{"type":"web_search_call","status":"completed"},{"type":"message","content":[{"text":"Official memory documentation.","annotations":[{"url":"https://developers.openai.com/codex/memories"}]}]}]}`)
	}))
	defer upstream.Close()

	input := strings.NewReader(
		"{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\"}}\n" +
			"{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n" +
			"{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}\n" +
			"{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"bedrock_browse\",\"arguments\":{\"task\":\"Find the official memory documentation\"}}}\n" +
			"{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"bedrock_browse\",\"arguments\":{\"task\":\"Find the official memory documentation\"}}}\n")
	var output bytes.Buffer

	err := serveBrowse(input, &output, browser{
		client: upstream.Client(), endpoint: upstream.URL, model: "openai.gpt-5.6-luna", region: "us-west-2", token: "test-only",
	})
	if err != nil {
		t.Fatal(err)
	}

	decoder := json.NewDecoder(&output)

	var initialized, listed, called struct {
		ID     int            `json:"id"`
		Result map[string]any `json:"result"`
	}
	if decoder.Decode(&initialized) != nil || decoder.Decode(&listed) != nil || decoder.Decode(&called) != nil {
		t.Fatal("missing MCP workflow response")
	}

	if initialized.Result["protocolVersion"] != "2025-06-18" ||
		listed.Result["tools"].([]any)[0].(map[string]any)["name"] != "bedrock_browse" ||
		called.ID != 3 || called.Result["isError"] != false {
		t.Fatal("MCP workflow failed")
	}

	text := called.Result["content"].([]any)[0].(map[string]any)["text"].(string)

	var research struct {
		Answer  string   `json:"answer"`
		Sources []string `json:"sources"`
		Model   string   `json:"model"`
		Region  string   `json:"region"`
	}
	if json.Unmarshal([]byte(text), &research) != nil || research.Answer != "Official memory documentation." ||
		len(research.Sources) != 1 || research.Sources[0] != "https://developers.openai.com/codex/memories" ||
		research.Model != "openai.gpt-5.6-luna" || research.Region != "us-west-2" {
		t.Fatalf("missing research result: %s", text)
	}

	if strings.Contains(text, "test-only") {
		t.Fatal("credential leaked in tool result")
	}

	var rejected struct {
		Result struct {
			IsError bool `json:"isError"`
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if decoder.Decode(&rejected) != nil || !rejected.Result.IsError || len(rejected.Result.Content) != 1 {
		t.Fatal("missing browsing rejection")
	}

	detail := rejected.Result.Content[0].Text
	if !strings.Contains(detail, "403 Forbidden") || !strings.Contains(detail, "openai.gpt-5.6-luna") ||
		!strings.Contains(detail, "us-west-2") || !strings.Contains(detail, "browse-rejection-123") ||
		strings.Contains(detail, "test-only") || strings.Contains(detail, "private research task") {
		t.Fatalf("browsing rejection lacks safe diagnostic context: %s", detail)
	}
}
